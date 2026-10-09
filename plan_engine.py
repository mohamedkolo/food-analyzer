# -*- coding: utf-8 -*-
"""How a plan gets built: exclusions, the weekly plan, guidance, and the PDF.

This is the domain logic -- given a client's data it decides what they eat,
what they are told, and what the PDF says. No routes, no request handling, so
it can be exercised directly from a test without a browser or a session.

The safety filtering itself lives in meal_database.filter_by_conditions; this
module calls it and layers the client's own exclusions and diet pattern on
top.
"""

import io as _io
import random
import re
from datetime import datetime
import datetime as dt

from flask import session

import meal_extra
from core import (
    ENGLISH_DAYS, WEIGHT_LOSS, _CULTURE_EN, _GENDER_EN, t,
    filter_by_conditions, get_diet_plan_info, get_meal_pool,
    get_nutrient_boost_notes, get_snacks_for_goal,
    translate_boost_note, translate_guidance, translate_meal,
)

def _has(symptoms, keywords):
    for s in symptoms:
        s_low = str(s).lower().strip()
        for k in keywords:
            if k.lower() in s_low: return True
    return False


# ═══════════════════════════════════════════════
# USER EXCLUSIONS PARSING
# ═══════════════════════════════════════════════

ALLERGY_KEYWORDS = {
    "اللاكتوز": ["حليب", "لبن", "زبادي", "جبن", "قشدة", "كريمة", "لبنة", "حلوم", "فيتا", "موزاريلا", "بارميزان", "ايس كريم", "بوظة", "كاكاو بحليب"],
    "الجلوتين": ["قمح", "خبز", "مكرونة", "برغل", "كسكس", "سميد", "شعير", "فريكة", "بسكويت", "كرواسون", "توست", "فطير"],
    "المكسرات": ["لوز", "كاجو", "بندق", "فستق", "جوز", "مكسرات", "بقان"],
    "البيض": ["بيض", "اومليت", "عجة", "شكشوكة", "بيضة", "بيضتين"],
    "الأسماك": ["سمك", "سلمون", "تونة", "بلطي", "هامور", "ماكريل", "سردين"],
    "الفول السوداني": ["فول سوداني", "زبدة فول"],
    "الصويا": ["صويا", "توفو", "تمبيه", "ادامامي"],
    "المحار": ["جمبري", "محار", "كركند", "اسكالوب", "اخطبوط"],
    "السمسم": ["سمسم", "طحينة", "حلاوة طحينية"],
}

def parse_user_exclusions(notes_text, disliked_foods, allergies):
    """يحوّل الملحوظات والحساسية والأكلات اللي مش بيحبها إلى قايمة كلمات تتشال من الوجبات."""
    exclusions = set()

    if disliked_foods:
        for item in disliked_foods.replace("،", ",").replace(";", ",").split(","):
            item = item.strip()
            if len(item) > 1:
                exclusions.add(item)

    if allergies:
        for allergy in allergies:
            for key, kws in ALLERGY_KEYWORDS.items():
                if key in allergy:
                    exclusions.update(kws)

    if notes_text:
        text = notes_text.strip()
        triggers = ["اشيل", "شيل", "بدون", "تجنب", "مش بحب", "مش باكل",
                    "ما بحب", "لا اكل", "حساسية من", "remove", "no ", "avoid",
                    "without", "allergic to"]
        for trigger in triggers:
            idx = 0
            while True:
                pos = text.find(trigger, idx)
                if pos == -1:
                    break
                rest = text[pos + len(trigger):pos + len(trigger) + 60]
                rest = rest.replace("،", ".").replace(",", ".").replace(" و ", ".").replace("\n", ".")
                first_chunk = rest.split(".")[0].strip()
                if first_chunk:
                    words = first_chunk.split()[:3]
                    for w in words:
                        w = w.strip(":،.,!؟")
                        if len(w) > 2:
                            exclusions.add(w)
                idx = pos + 1

    return list(exclusions)


def filter_meals_by_exclusions(meals, exclusions):
    """شيل أي وجبة فيها كلمة من الـ exclusions. لو شلنا كل الوجبات نرجّع الأصلية."""
    if not exclusions:
        return meals
    result = []
    for meal in meals:
        meal_text = meal.get("meal", "") if isinstance(meal, dict) else str(meal)
        if not any(ex in meal_text for ex in exclusions):
            result.append(meal)
    return result if result else meals


LOW_CARB_WORDS = ["ارز", "أرز", " رز", "خبز", "عيش", "رغيف", "مكرونة", "معكرونة",
                  "كسكس", "برغل", "بطاطا", "بطاطس", "شوفان", "تورتيلا", "توست",
                  "بان كيك", "بانكيك", "جرانولا", "بليلة", "نودلز", "بسكويت",
                  "كورن", "فطير", "معجنات", "نشا", "مسمن", "بغرير", "حرشة", "سفنج", "كيك"]
KETO_EXTRA_WORDS = ["فول", "حمص", "عدس", "فاصوليا", "لوبيا", "بقول",
                    "موز", "تفاح", "تمر", "عسل", "مانجو", "عنب", "برتقال", "مربى", "دبس"]

def _meal_text(m):
    return m.get("meal", "") if isinstance(m, dict) else str(m)

def filter_carbs(meals, keto=False):
    """بيشيل الوجبات اللي فيها نشويات. لو شال كله بيرجّع الأصل عشان مايفضّاش."""
    words = LOW_CARB_WORDS + (KETO_EXTRA_WORDS if keto else [])
    res = [m for m in meals if not any(w in _meal_text(m) for w in words)]
    return res if len(res) >= 3 else meals

def _rank_by_condition(meals, cond_keys):
    """يرتّب الوجبات: المفيد للحالة الأول، المحايد، والمتجنّب آخراً."""
    if not cond_keys:
        return meals
    try:
        from meal_extra import tag_meal
    except Exception:
        return meals
    good, neutral, bad = [], [], []
    for m in meals:
        tags = tag_meal(_meal_text(m))
        statuses = [tags.get(c) for c in cond_keys if c in tags]
        if "bad" in statuses:
            bad.append(m)
        elif "good" in statuses:
            good.append(m)
        else:
            neutral.append(m)
    return good + neutral + bad

def _defer_repeats(meals, avoid):
    """يحط الوجبات اللي العميل أكلها المرة اللي فاتت في آخر اللستة.

    الترتيب هو اللي بيحدد إيه اللي هيتاخد (الاختيار بـ i % len)، فتأخيرها
    معناه إنها مش هتتشاف غير لو الجديد خلص."""
    if not avoid:
        return meals
    fresh, repeats = [], []
    for m in meals:
        (repeats if _meal_text(m).strip() in avoid else fresh).append(m)
    return fresh + repeats


def _apply_clinical_safety_caps(data):
    """يظبط هدف السعرات تلقائياً لحالات حساسة (حصوات المرارة، اضطرابات الأكل)، ويضيف ملاحظات تغذوية
    للحالات اللي محتاجة تأكيد على عناصر معيّنة (هشاشة العظام، نقص الحديد...)، قبل توليد الخطة."""
    symptoms = data.get("symptoms", []) or []
    flags = get_nutrient_boost_notes(symptoms)

    # سن النمو مش حالة مرضية تتعلّم، فبتتطلق من العمر نفسه. الحد الأدنى 4 لأن
    # دي بداية الفئة في التوصيات؛ أقل من كده تغذية أطفال وليها قواعد تانية.
    try:
        _age = int(float(data.get("age") or 0))
    except (TypeError, ValueError):
        _age = 0
    if 4 <= _age <= 18:
        flags += get_nutrient_boost_notes(["عمر 4-18"])

    # ‏أنظمة مش للأطفال. طلعت من قياس خطة نورة (١٠ سنين): نظام ١٨/٦
    # بيديها ١٨٣ جم بروتين -- ٣٣٪ من الطاقة، فوق النطاق المنشور --
    # وده مش عيب في الحصص، ده عيب في إن النظام نفسه وجبتين بس،
    # والاتنين من أطباق الغدا. وقبل ما نظبط حصص، الأصل إن الصيام
    # المتقطع والكيتو مش أدوات تخسيس لطفل في سن النمو: الصيام
    # بيضغط على وجبات يوم بيحتاج فيه نمو، والكيتو علاج طبي (صرع)
    # بإشراف، مش نظام رجيم.
    _child_plan = {
        "intermittent_16_8": "صيام متقطع",
        "intermittent_18_6": "صيام متقطع",
        "keto": "كيتو",
        "chemical": "الدايت الكيميائي",
    }.get(data.get("diet_plan_type") or "")
    if 0 < _age < 18 and _child_plan:
        flags.append("⚠️ سن %d سنة: %s مش نظام موصى بيه في سن النمو. "
                     "الأنسب نظام متوازن بوجبات موزّعة، والقرار قرارك."
                     % (_age, _child_plan))

    try:
        tdee_val = float(data.get("tdee", 0) or 0)
        goal_cal_val = float(data.get("goal_cal", 0) or 0)
    except (TypeError, ValueError):
        tdee_val = goal_cal_val = 0

    if tdee_val and goal_cal_val:
        if "حصوات المرارة" in symptoms:
            max_safe_deficit = 750  # أقصى عجز سعرات آمن يومياً (فقدان 0.5-1 كجم أسبوعياً)
            min_safe_cal = tdee_val - max_safe_deficit
            if goal_cal_val < min_safe_cal:
                data["goal_cal"] = str(int(min_safe_cal))
                goal_cal_val = min_safe_cal
                flags.append(f"⚠️ حصوات المرارة: السعرات المستهدفة اتظبطت تلقائياً لـ {int(min_safe_cal)} kcal "
                            f"(أقصى عجز {max_safe_deficit} kcal/يوم) لأن فقدان الوزن السريع بيزود خطر تكوّن الحصوات.")

        if "اضطراب في الأكل" in symptoms:
            if goal_cal_val < tdee_val:
                data["goal_cal"] = str(int(tdee_val))
            flags.append("⚠️ اضطراب أكل مسجل: الخطة اتظبطت على سعرات المحافظة (من غير عجز) بدل التخسيس — "
                         "الحالة دي لازم متابعة طبيب نفسي/طبيب مصاحبة للتغذية.")

    if flags:
        existing_notes = data.get("notes", "") or ""
        data["notes"] = " | ".join(flags) + (" | " + existing_notes if existing_notes else "")


# ‏المكوّن الأساسي في وجبة الفطار. الترتيب مهم: "عجة بالسبانخ" بيض، مش سبانخ.
_BF_BASE = (
    ("بيض", ("بيض", "عجة", "أومليت", "اومليت", "شكشوكة", "Frittata", "فريتاتا")),
    ("زبادي", ("زبادي",)),
    ("جبن", ("جبن", "قريش", "لبنة", "حلوم", "فيتا")),
    ("شوفان", ("شوفان", "كورن فليكس", "جرانولا", "كينوا")),
    ("فول", ("فول مدمس", "طعمية", "فلافل", "حمص")),
    ("خبز", ("توست", "خبز", "رقاق", "مناقيش", "بان كيك", "بانكيك")),
    ("بطاطا", ("بطاطا", "بطاطس")),
    ("فاكهة", ("تفاح", "موز", "كمثرى", "فراولة", "بطيخ", "تمر", "بلح")),
)


def _bf_base(text):
    """‏المكوّن الأساسي: بيتقرا من أول عنصر في الوجبة، مش من أي كلمة فيها.

    الوجبات مكتوبة والنجم بدري: "فول مدمس + بيضة مسلوقة + خبز" فولها هو
    الأساس، و"بيض مسلوق + خبز اسمر + جرجير" بيضها. لو بصينا على أي كلمة،
    الاتنين يطلعوا "بيض" -- والتوزيع يفضل يحسبهم نفس الحاجة ويكرّر الفطار.
    """
    head = str(text).split(" + ")[0]
    for name, tokens in _BF_BASE:
        if any(t in head for t in tokens):
            return name
    for name, tokens in _BF_BASE:
        if any(t in str(text) for t in tokens):
            return name
    return "غير ذلك"


# ‏الأساس في الغدا والعشا = مصدر البروتين. سبع أيام دجاج مش خطة.
_MAIN_BASE = (
    ("دجاج", ("دجاج", "فراخ", "شيش طاووق", "شاورما دجاج")),
    ("ديك رومي", ("ديك رومي", "تركي")),
    ("سمك", ("سمك", "سلمون", "تونة", "سردين", "هامور", "بلطي", "فيليه")),
    ("جمبري", ("جمبري", "روبيان", "مأكولات بحرية")),
    ("لحم", ("لحم", "كفتة لحم", "بفتيك", "ستيك")),
    ("بيض", ("بيض", "عجة", "أومليت", "شكشوكة")),
    ("بقوليات", ("عدس", "فول", "حمص", "فاصوليا", "لوبيا", "كشري")),
    ("جبن", ("جبن", "قريش", "لبنة", "حلوم")),
)


def _main_base(text):
    head = str(text).split(" + ")[0]
    for name, tokens in _MAIN_BASE:
        if any(t in head for t in tokens):
            return name
    for name, tokens in _MAIN_BASE:
        if any(t in str(text) for t in tokens):
            return name
    return "غير ذلك"


def _spread_by_base(meals, take=7, cap=3, base=None):
    """‏يوزّع أول `take` وجبة بحيث مايتكرّرش نفس المكوّن أكتر من `cap`.

    قايمة الفطار فيها بيض كتير، وده مقصود: الفطار اللي يعدّي الجلوتين
    واللاكتوز والبقوليات مع بعض، البيض تقريباً مصدر البروتين الوحيد اللي
    فاضل. بس العميل اللي مالوش قيود مايستحقّش خمس أيام بيض من سبعة -- ده
    اللي كان بيحصل، لأن الاختيار بياخد أول ٧ من قايمة مرتّبة بالبروتين.

    ترتيب مش حذف: لو القيود سابت بيض بس، الوجبات بترجع زي ما هي بدل
    ما الأسبوع يطلع ناقص.
    """
    if len(meals) <= take:
        return meals
    base_of = base or _bf_base
    picked, rest, counts = [], [], {}
    for meal in meals:
        name = base_of(_meal_text(meal))
        if len(picked) < take and counts.get(name, 0) < cap:
            picked.append(meal)
            counts[name] = counts.get(name, 0) + 1
        else:
            rest.append(meal)
    # ‏لو القيود مسمحتش نكمّل السبعة، نكمّل من الباقي بترتيبه
    while len(picked) < take and rest:
        picked.append(rest.pop(0))
    return picked + rest


def generate_weekly_plan(data):
    _apply_clinical_safety_caps(data)

    # تدوير السعرات — لازم يتحسب بعد الـ safety caps لأنها ممكن تكون غيّرت goal_cal
    try:
        from zigzag import zigzag_from_data
        data["zigzag"] = zigzag_from_data(data)
    except Exception as _e:
        print(f"zigzag error: {_e}")
        data["zigzag"] = None
    zz_days = (data.get("zigzag") or {}).get("days") or []

    symptoms = data.get("symptoms", [])
    goal = data.get("goal_type", "weight_loss")
    is_cutting = (goal == "cutting")
    if is_cutting: goal = "weight_loss"  # وجبات العجز + هنفضّل البروتين تحت
    culture = data.get("culture", "مصري")
    diet_type = data.get("diet_plan_type", "standard")

    try:
        user_id = data.get("user_id") or session.get("uid", 0) or 0
    except: user_id = 0
    seed_val = ((user_id or 1) * 1000007 + int(datetime.now().timestamp() * 1000)) % (2**32)
    random.seed(seed_val)

    notes = data.get("notes", "")
    disliked = data.get("disliked_foods", "")
    allergies = data.get("allergies", []) if isinstance(data.get("allergies"), list) else []
    user_exclusions = parse_user_exclusions(notes, disliked, allergies)

    # ‏برامج التغذية الـ11 (diet_programs): كل برنامج جدول سبعة أيام
    # بأكله هو، على شكل ورقة العيادة اللي الدكتور بعتها. الأكل نفسه هو
    # البرنامج، مش خانات بتتملّي من مجموعة وجبات الهدف -- فبيرجع في
    # وحدته زي الكيميائي والتكميم.
    #
    # ‏الفرق عنهم إنه **بياخد هدف السعرات**: الجدول بيحدّد الأكل
    # والترتيب، وdiet_programs بيظبّط الحصص على (الهدف ÷ مجموع اليوم).
    # فورقة واحدة بتخدم اللي هدفه 1400 واللي هدفه 2600.
    try:
        from diet_programs import PROGRAMS as _PROGRAMS
    except Exception:
        _PROGRAMS = {}
    if diet_type in _PROGRAMS:
        from diet_programs import build_program_plan
        try:
            _target = float(data.get("goal_cal") or 0)
        except (TypeError, ValueError):
            _target = 0.0
        prog_days, prog_warnings = build_program_plan(
            diet_type, target_cal=_target, symptoms=symptoms,
            exclusions=user_exclusions, gender=data.get("gender"),
            goal_type=data.get("goal_type"),
            # ‏الوزن لازم لـOpti-tect: رصيد النقاط كله بيتحسب منه
            weight=data.get("weight"))
        if prog_warnings:
            existing = data.get("notes", "") or ""
            # ‏نفس معالجة الكيميائي والتكميم: أزواج (عربي، إنجليزي) عشان
            # الـPDF الإنجليزي مايطلعش عربي -- الأسطر فيها أرقام وأسماء
            # أيام متغيرة، والترجمة من خريطة ثابتة مش بتعرف تمسكها.
            pairs = list(dict.fromkeys(
                ("⚠️ " + w["reason"], "⚠️ " + w["reason_en"])
                for w in prog_warnings))
            data["chemical_note_pairs"] = pairs
            data["notes"] = (" | ".join(ar for ar, _ in pairs)
                             + (" | " + existing if existing else ""))
        data["program_warnings"] = prog_warnings
        return prog_days

    # النظام الكيميائي دورة ثابتة 6 أيام: اليوم نفسه هو المحتوى (خضار، فاكهة،
    # سمك...) مش خانات بتتملي من مجموعة وجبات، والترتيب جزء من البروتوكول.
    # فبيتبني في وحدته وبيرجع من غير ما يعدي على منطق الأسبوع -- ولا على
    # تدوير السعرات، لأن سعراته هي الأكل نفسه مش رقم مستهدف.
    if diet_type == "chemical":
        from chemical_diet import build_chemical_plan
        chem_days, chem_warnings = build_chemical_plan(
            symptoms, user_exclusions, data.get("gender"))
        # نفس مسار عرض الملاحظات الطبية اللي فوق -- الأخصائي لازم يشوف
        # اليوم اللي مقدرناش نأمّنه قبل ما يبعت الخطة.
        if chem_warnings:
            existing = data.get("notes", "") or ""
            floor_hits = [w for w in chem_warnings if w["kind"] == "below_floor"]
            # نفس التنبيه بيتكرر على أكتر من يوم (تنبيه السكري على يومي
            # الفاكهة مثلاً)، وتكراره حرفياً في الملاحظات مش بيضيف حاجة.
            # بيتشال هنا بس، وبيفضل على كل يوم في المعاينة.
            # الأسطر بتتبنى أزواج (عربي، إنجليزي). الـ PDF بيترجم الملاحظات
            # من خريطة ثابتة، وهي مش بتعرف تترجم النصوص دي لأن فيها أرقام
            # وأسماء أيام متغيرة -- فمن غير الإنجليزي جنبها كانت بتطلع عربي
            # على PDF إنجليزي.
            pairs = list(dict.fromkeys(
                ("⚠️ " + w["reason"], "⚠️ " + w["reason_en"])
                for w in chem_warnings if w["kind"] != "below_floor"))
            # أيام الدورة كلها تحت الحد، فستة أسطر شبه بعضها كانت هتغرق
            # الملاحظات وتخفي اللي بيحتاج قراية فعلاً. سطر واحد بالعدد وأقل
            # يوم هنا، والتفصيل على كل يوم في المعاينة.
            if floor_hits:
                lowest = min(floor_hits, key=lambda w: w["kcal"])
                pairs.append((
                    f"⚠️ {len(floor_hits)} من {len(chem_days)} أيام تحت الحد الآمن "
                    f"({lowest['floor']} kcal) — أقلها {lowest['kcal']} kcal في "
                    f"{lowest['day']}. الدورة قصيرة بطبيعتها، والالتزام بيها محتاج "
                    f"إشراف ومدة محدودة.",
                    f"⚠️ {len(floor_hits)} of {len(chem_days)} days fall under the "
                    f"{lowest['floor']} kcal floor — the lowest is "
                    f"{lowest['kcal']} kcal on {lowest['day_en']}. The cycle is "
                    f"short by design, but following it needs supervision and a "
                    f"limited duration.",
                ))
            # الأزواج بتتخزّن عشان build_pdf يلاقي الإنجليزي لكل سطر
            data["chemical_note_pairs"] = pairs
            data["notes"] = (" | ".join(ar for ar, _ in pairs)
                             + (" | " + existing if existing else ""))
        data["chemical_warnings"] = chem_warnings
        return chem_days

    # ‏بروتوكول ما بعد التكميم: المرحلة هي المحتوى، واللي بيحددها عدد الأسابيع
    # بعد العملية. زي الكيميائي بيرجع في وحدته من غير ما يعدي على تدوير
    # السعرات -- سعراته هي طبيعة المرحلة مش رقم مستهدف، وأول مرحلتين أصلاً
    # تحت أي حد وده صح.
    if diet_type == "sleeve":
        from sleeve_diet import build_sleeve_plan
        weeks = data.get("sleeve_weeks")
        sl_days, sl_warnings = build_sleeve_plan(
            weeks, symptoms, user_exclusions, data.get("gender"))
        if sl_warnings:
            existing = data.get("notes", "") or ""
            # ‏نفس معالجة الكيميائي: أزواج (عربي، إنجليزي) عشان الـPDF
            # الإنجليزي مايطلعش عربي -- الأسطر فيها أرقام وأسماء مراحل
            # متغيرة، والترجمة من خريطة ثابتة مش بتعرف تمسكها.
            pairs = list(dict.fromkeys(
                ("⚠️ " + w["reason"], "⚠️ " + w["reason_en"]) for w in sl_warnings))
            data["chemical_note_pairs"] = pairs
            data["notes"] = (" | ".join(ar for ar, _ in pairs)
                             + (" | " + existing if existing else ""))
        data["sleeve_warnings"] = sl_warnings
        return sl_days

    pool = get_meal_pool(goal, culture)
    breakfasts = list(pool.get("breakfast", []))
    lunches = list(pool.get("lunch", []))
    dinners = list(pool.get("dinner", []))
    if len(breakfasts) < 7: breakfasts = list(WEIGHT_LOSS["مصري"]["breakfast"])
    if len(lunches) < 7: lunches = list(WEIGHT_LOSS["مصري"]["lunch"])
    if len(dinners) < 7: dinners = list(WEIGHT_LOSS["مصري"]["dinner"])
    # ‏اسم الخانة بيتبعت مع الفلترة عشان لما الطابور يفضى تماماً (عميل
    # مختار كذا حالة مع بعض) البديل يتجاب من بدايل **الفطار** مش من قايمة
    # عامة فيها أطباق غدا -- اللي كانت بتطلّع "دجاج وأرز" في خانة الفطار.
    breakfasts = filter_by_conditions(breakfasts, symptoms, "breakfast")
    lunches = filter_by_conditions(lunches, symptoms, "lunch")
    dinners = filter_by_conditions(dinners, symptoms, "dinner")

    breakfasts = filter_meals_by_exclusions(breakfasts, user_exclusions)
    lunches = filter_meals_by_exclusions(lunches, user_exclusions)
    dinners = filter_meals_by_exclusions(dinners, user_exclusions)

    # متابعة: الوجبات اللي كانت في خطة الزيارة اللي فاتت تتأخّر لآخر الطابور،
    # عشان العميل الراجع بعد شهر ياخد أسبوع جديد مش نفس الأكل تاني. تأخير مش
    # حذف -- لو الفلترة الطبية سابت وجبات قليلة، الأفضل يتكرر أكل على إن
    # الخطة تطلع ناقصة.
    avoid = set(data.get("avoid_meals") or [])
    if avoid:
        breakfasts = _defer_repeats(breakfasts, avoid)
        lunches = _defer_repeats(lunches, avoid)
        dinners = _defer_repeats(dinners, avoid)

    # كيتو: وجبات كيتو حقيقية | لو-كارب: تقليل النشويات
    if diet_type == "keto":
        try:
            from meal_extra import KETO_MEALS
            kb = list(KETO_MEALS.get("breakfast", []))
            kl = list(KETO_MEALS.get("lunch", []))
            kd = list(KETO_MEALS.get("dinner", []))
            if kb and kl and kd:
                breakfasts = filter_meals_by_exclusions(filter_by_conditions(kb, symptoms, "breakfast"), user_exclusions) or kb
                lunches = filter_meals_by_exclusions(filter_by_conditions(kl, symptoms, "lunch"), user_exclusions) or kl
                dinners = filter_meals_by_exclusions(filter_by_conditions(kd, symptoms, "dinner"), user_exclusions) or kd
            else:
                breakfasts = filter_carbs(breakfasts, True)
                lunches = filter_carbs(lunches, True)
                dinners = filter_carbs(dinners, True)
        except Exception as _e:
            print(f"keto meals error: {_e}")
            breakfasts = filter_carbs(breakfasts, True)
            lunches = filter_carbs(lunches, True)
            dinners = filter_carbs(dinners, True)
    elif diet_type == "low_carb":
        breakfasts = filter_carbs(breakfasts, False)
        lunches = filter_carbs(lunches, False)
        dinners = filter_carbs(dinners, False)

    snacks = get_snacks_for_goal(goal)
    pool_snacks = pool.get("snack", [])
    if pool_snacks: snacks = pool_snacks[:10]
    while len(snacks) < 7: snacks.append("فاكهة + مكسرات (120 kcal)")

    snacks = [s for s in snacks if not any(ex in (s if isinstance(s, str) else s.get("meal","")) for ex in user_exclusions)] or snacks
    if avoid:
        snacks = _defer_repeats(snacks, avoid)

    if diet_type == "keto":
        try:
            from meal_extra import KETO_SNACKS
            if KETO_SNACKS:
                snacks = list(KETO_SNACKS)
        except Exception:
            pass
    elif diet_type == "low_carb":
        _fs = [s for s in snacks if not any(w in (s if isinstance(s, str) else s.get("meal", "")) for w in LOW_CARB_WORDS)]
        snacks = _fs if _fs else snacks

    days = ["الاحد","الاثنين","الثلاثاء","الاربعاء","الخميس","الجمعة","السبت"]
    plan_info = get_diet_plan_info(diet_type)
    random.shuffle(breakfasts)
    random.shuffle(lunches)
    random.shuffle(dinners)

    # ‏هدف السعرات اليومي: اللي الدكتور كتبه. لو مكتوبش، الحصص تفضل زي ما هي
    # بدل ما نخمّن رقم ونكبّر عليه.
    try:
        _base_target = float(data.get("goal_cal") or 0)
    except (TypeError, ValueError):
        _base_target = 0.0

    SNK_P = 8  # تقدير بروتين السناك الواحد

    # ── البروتين المستهدف، ودوال الزيادة ──
    #
    # ‏نفس حساب الورقة: وزن العميل × جرام/كجم. الورقة بتطبعه كوصفة،
    # والأكل لازم يوصله -- وإلا الورقة بتكدّب نفسها.
    import protein_fix
    PROTEIN_FACTORS = {"sedentary": 1.0, "light": 1.3, "regular": 1.6,
                       "athlete": 2.0}
    try:
        _pf_w = float(data.get("weight") or 0)
    except (TypeError, ValueError):
        _pf_w = 0.0
    try:
        _pf_ppk = float(data.get("protein_per_kg")
                        or PROTEIN_FACTORS.get(data.get("activity_level")
                                               or "regular", 1.6))
    except (TypeError, ValueError):
        _pf_ppk = 1.6
    # ‏الهدف مش دايماً وزن العميل × جرام/كجم. ورقة نورة (١٠ سنين،
    # ١٠٨.٨ كجم، طول ١٥٢) كانت بتطبع ١٤١ جم بروتين -- تلات أضعاف
    # توصية سنها -- وزيادة البروتين كانت بتشتغل عشان توصّلها. التفاصيل
    # والحساب في protein_need.
    import protein_need
    _target_p, _pf_basis, _pf_why, _pf_used_rate = protein_need.target_grams(
        _pf_w, data.get("height"), data.get("age"), _pf_ppk)
    data["protein_basis"] = {"grams": _target_p, "weight": _pf_basis,
                             "why": _pf_why, "per_kg": _pf_used_rate}

    # تفضيل البروتين العالي للأهداف اللي محتاجة بروتين أكتر
    _prefer_protein = (goal in ("muscle_gain", "bulking")) or is_cutting or (data.get("activity_level") == "athlete")
    # ‏والطفل بالعكس تماماً. ورقة نورة (١٠ سنين، ١٠٨.٨ كجم) هدفها ٥٠ جم
    # بروتين والأكل كان بيديها بين ٧٦ و**١٨٣**. السبب اتنين مع بعض:
    # الترتيب فوق بيطلّع أعلى الأطباق بروتين (لأن التخسيس is_cutting)،
    # والمعامل اللي بيوصّل اليوم لسعراته بيضرب البروتين مع السعرات --
    # فطبق جمبري ٤٥ جم بروتين بقى ٢٩٠جم جمبري و٩٠ جم بروتين.
    #
    # ‏فالاختيار نفسه بيبقى على **كثافة البروتين** (جم لكل سعر) القريبة
    # من كثافة احتياجه، مش على أعلى بروتين. والقاعدة فيها الأطباق دي
    # فعلاً: يوم الجمعة في نفس الأسبوع طلع ٧٦ جم من غير أي تدخّل.
    _child = protein_need.is_child(data.get("age"))
    _want_density = 0.0
    if _child and _target_p > 0 and _base_target > 0:
        _want_density = _target_p / _base_target
    if _want_density > 0:
        def _density_gap(meal):
            _c = float(meal.get("cal") or 0)
            if _c <= 0:
                return 9.9
            return abs(float(meal.get("p") or 0) / _c - _want_density)
        breakfasts = sorted(breakfasts, key=_density_gap)
        lunches = sorted(lunches, key=_density_gap)
        dinners = sorted(dinners, key=_density_gap)
    elif _prefer_protein:
        breakfasts = sorted(breakfasts, key=lambda m: m.get("p", 0), reverse=True)
        lunches = sorted(lunches, key=lambda m: m.get("p", 0), reverse=True)
        dinners = sorted(dinners, key=lambda m: m.get("p", 0), reverse=True)

    # ترتيب حسب الحالة المرضية: المفيد للحالة الأول، المتجنّب آخراً
    _cond_keys = []
    try:
        from meal_extra import conditions_to_keys
        _cond_keys = conditions_to_keys(symptoms)
    except Exception:
        _cond_keys = []
    if _cond_keys:
        breakfasts = _rank_by_condition(breakfasts, _cond_keys)
        lunches = _rank_by_condition(lunches, _cond_keys)
        dinners = _rank_by_condition(dinners, _cond_keys)

    # ‏آخر خطوة قبل الاختيار: مايتكرّرش نفس المكوّن أكتر من ٣ أيام في الفطار.
    # لازم تبقى بعد الترتيب بالبروتين والحالة، عشان متغيّرش أولوياتهم -- هي
    # بتوزّع اللي هما رتّبوه.
    breakfasts = _spread_by_base(breakfasts, take=7, cap=3)
    # ‏والغدا والعشا بمصدر البروتين: سبع أيام دجاج مش خطة، وده كان بيحصل
    # لأن الترتيب بالبروتين بيطلّع الدجاج فوق.
    lunches = _spread_by_base(lunches, take=7, cap=3, base=_main_base)
    dinners = _spread_by_base(dinners, take=7, cap=3, base=_main_base)

    from portion_scale import scale_meal

    def _pf_safe(text):
        """‏الزيادة لازم تعدّي حالات العميل وممنوعاته زي أي أكل تاني."""
        from meal_database import safe_for_all, unsafe_keys_for
        if any(ex and ex in text for ex in user_exclusions):
            return False
        return safe_for_all(text, unsafe_keys_for(symptoms))

    def _pf_slot_for(info):
        """‏الزيادة بتتحط في أكبر وجبة -- هي اللي بتستحمل صنف زيادة."""
        for _k in ("lunch", "dinner", "meal2", "iftar", "breakfast", "meal1"):
            if _k in info["meal_labels"]:
                return _k
        labels = list(info["meal_labels"])
        return labels[0] if labels else "lunch"

    # ‏كل مصدر بروتين موجود في كام يوم من **أكل الأسبوع نفسه**، قبل
    # أي زيادة. من غير ده الزيادة كانت بتدفع صنف من تلات أيام لأربعة
    # (وده حد توزيع الوجبات)، فاختبار التكرار كان بيفشل مرة من تلاتة.
    _pf_used = {}
    try:
        # ‏العدّ على **الخانة اللي الزيادة هتقع فيها بس**، وبنفس دالة
        # التوزيع اللي الأسبوع بيتقاس بيها.
        #
        # ‏نسختين غلط قبل كده:
        #   ١) توكن من عندي ("تونة") -- والدالة بتحوّلها "سمك"، فالعدّ
        #      ماشافش أطباق السمك في الطابور.
        #   ٢) العدّ على اليوم كله -- فالبيض في الفطار ٥ أيام كان
        #      بياكل حصة بياض البيض في الغدا، والتلات مصادر بيطلعوا
        #      "مستهلكين" فالحد بيتجاهل والزيادة تدفع صنف لـ٥.
        #
        # ‏والصح إن الاختبار بيقيس التكرار جوه الخانة الواحدة، فالعدّ
        # لازم يبقى على نفس الخانة.
        _pf_slot = _pf_slot_for(plan_info)
        _pf_pool = {"breakfast": breakfasts, "lunch": lunches,
                    "dinner": dinners}.get(_pf_slot)
        _pf_base = _bf_base if _pf_slot == "breakfast" else _main_base
        if _pf_pool:
            _pf_bases = {_s["ar"]: _pf_base(_s["ar"])
                         for _s in protein_fix.SOURCES}
            for _j in range(7):
                _b = _pf_base(_pf_pool[_j % len(_pf_pool)].get("meal", ""))
                for _name, _want in _pf_bases.items():
                    if _b == _want:
                        _pf_used[_name] = _pf_used.get(_name, 0) + 1
    except Exception:
        _pf_used = {}
    plan = []
    for i in range(7):
        day_plan = {"day": days[i], "diet_type": diet_type,
                    "meal_labels": plan_info["meal_labels"], "meal_emojis": plan_info["meal_emojis"]}
        # ‏سعرات وبروتين كل خانة لوحدها: المجموع بيتحسب منها، وكل خانة
        # بتتكبّر بنفس المعامل تحت، فلازم نعرف نصيبها.
        _slot_cals, _slot_ps = {}, {}
        if diet_type in ("standard", "keto", "low_carb"):
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["breakfast"] = b["meal"]
            day_plan["lunch"] = l["meal"]
            day_plan["dinner"] = d["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            _slot_cals = {"breakfast": b.get("cal",300), "lunch": l.get("cal",400),
                          "dinner": d.get("cal",300), "snack": 150}
            _slot_ps = {"breakfast": b.get("p",20), "lunch": l.get("p",30),
                        "dinner": d.get("p",20), "snack": SNK_P}
        elif diet_type == "two_meals":
            # وجبتين بس: الفطار والغداء، والسعرات كلها بينهم. مفيش عشاء،
            # فالحصة الواحدة أكبر من نظام التلات وجبات.
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            day_plan["breakfast"] = b["meal"]
            day_plan["lunch"] = l["meal"]
            _slot_cals = {"breakfast": b.get("cal",450), "lunch": l.get("cal",550)}
            _slot_ps = {"breakfast": b.get("p",25), "lunch": l.get("p",35)}
        elif diet_type == "five_meals":
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["breakfast"] = b["meal"]
            day_plan["snack1"] = snacks[i % len(snacks)]
            day_plan["lunch"] = l["meal"]
            day_plan["snack2"] = snacks[(i+3) % len(snacks)]
            day_plan["dinner"] = d["meal"]
            _slot_cals = {"breakfast": b.get("cal",300), "lunch": l.get("cal",400),
                          "dinner": d.get("cal",300), "snack1": 150, "snack2": 150}
            _slot_ps = {"breakfast": b.get("p",20), "lunch": l.get("p",30),
                        "dinner": d.get("p",20), "snack1": SNK_P, "snack2": SNK_P}
        elif diet_type == "intermittent_16_8":
            b = breakfasts[i % len(breakfasts)]
            d = dinners[i % len(dinners)]
            day_plan["meal1"] = b["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            day_plan["meal2"] = d["meal"]
            _slot_cals = {"meal1": b.get("cal",350), "meal2": d.get("cal",450),
                          "snack": 150}
            _slot_ps = {"meal1": b.get("p",25), "meal2": d.get("p",30),
                        "snack": SNK_P}
        elif diet_type == "intermittent_18_6":
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["meal1"] = l["meal"]
            day_plan["meal2"] = d["meal"]
            _slot_cals = {"meal1": l.get("cal",400), "meal2": d.get("cal",400)}
            _slot_ps = {"meal1": l.get("p",30), "meal2": d.get("p",30)}
        elif diet_type == "ramadan":
            l = lunches[i % len(lunches)]
            b = breakfasts[i % len(breakfasts)]
            day_plan["iftar"] = l["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            day_plan["suhoor"] = b["meal"]
            _slot_cals = {"iftar": l.get("cal",400), "suhoor": b.get("cal",300),
                          "snack": 150}
            _slot_ps = {"iftar": l.get("p",30), "suhoor": b.get("p",20),
                        "snack": SNK_P}
        elif diet_type == "workout":
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["pre_workout"] = "موزة 1 + زبدة فول سوداني 15جم + قهوة"
            day_plan["breakfast"] = b["meal"]
            day_plan["post_workout"] = "بروتين شيك 30جم + موز 1 + لوز 15جم"
            day_plan["lunch"] = l["meal"]
            day_plan["dinner"] = d["meal"]
            _slot_cals = {"pre_workout": 200, "breakfast": b.get("cal",300),
                          "post_workout": 250, "lunch": l.get("cal",400),
                          "dinner": d.get("cal",300)}
            _slot_ps = {"pre_workout": 2, "breakfast": b.get("p",20),
                        "post_workout": 31, "lunch": l.get("p",30),
                        "dinner": d.get("p",20)}
        total_cal = sum(_slot_cals.values())
        total_p = sum(_slot_ps.values())

        # ── الحصص تتظبط على هدف اليوم ──────────────────────────────────
        #
        # وجبات القاعدة حصصها ثابتة لكل هدف، وهدف العميل رقم متغيّر بيتحسب
        # من وزنه وطوله وسنه ونشاطه. فالمجموع كان بيتحط جنب الهدف والرقمين
        # مش نفس الرقم -- بفرق ١٤٪ في أحسن حالة و٥٦٪ في أسوأها. وأسوأها
        # كانت الأنظمة اللي وجباتها أقل: بتشيل وجبة وتسيب حصص الباقي زي ما
        # هي، فمريض نظام الوجبتين كان بياخد نص سعراته.
        #
        # المعامل بيتحسب على هدف **اليوم** مش الأسبوع، فأيام التدوير العالية
        # حصصها أكبر فعلاً. والمعامل الفعلي (بعد تقريب الجرامات) هو اللي
        # السعرات بتتحسب بيه، عشان الرقم المكتوب يكون رقم الطبق.
        # ‏تمريرتين: التقريب لأقرب ٥ أو ١٠ جرام بيسيب باقي، والتمريرة
        # التانية بتاكل أغلبه. أكتر من كده مابيقرّبش حاجة وبيخلي الأرقام
        # غريبة، فبنوقف عند ٣٪.
        _day_target = zz_days[i]["kcal"] if i < len(zz_days) else _base_target
        _cur_cals = dict(_slot_cals)
        _cur_ps = dict(_slot_ps)
        _cum = {}          # ‏المعامل المتراكم لكل وجبة من حصتها الأساسية
        # ‏فيه وجبات مابتتحركش: "٢ بيض" مش بيبقى "١.٨ بيضة"، و"سلطة خضراء
        # حرة" مالهاش كمية تتضرب. المعامل الموحّد كان بيتطلب منها تتحرك،
        # هي مابتتحركش، والباقي بيضيع -- وفي نظام وجبتين الوجبة الواحدة
        # نص اليوم، فاليوم كان بيبعد ١٢٪ عن هدفه (١٢٠٠ يطلع ١٣٤٠ أو ١٠٧٤).
        #
        # ‏فبنعمل زي ما التدوير بيعمل مع الحد الأدنى: نثبّت اللي مش بيتحرك،
        # ونرد الباقي على اللي بيتحرك. وبنقفل على الوجبة اللي طلبنا منها
        # تتحرك ومااتحركتش، عشان مانلفّش عليها تاني.
        _stuck = set()
        for _pass in range(5):
            _now = sum(_cur_cals.values())
            if not (_day_target and _now > 0):
                break
            if abs(float(_day_target) / float(_now) - 1.0) < 0.03:
                break
            _movable = [_k for _k in plan_info["meal_labels"]
                        if day_plan.get(_k) and _cur_cals.get(_k, 0) > 0
                        and _k not in _stuck]
            if not _movable:
                break
            _held = sum(_c for _k, _c in _cur_cals.items() if _k not in _movable)
            _free = sum(_cur_cals[_k] for _k in _movable)
            _want = float(_day_target) - _held
            if _free <= 0 or _want <= 0:
                break
            _factor = _want / _free
            # ‏وبرضه الطبق لازم يفضل طبق: حصة أكبر من ٣ أضعاف الأساس أو أقل
            # من تلته بتبقى رقم على الورق مش أكل، فبنقف عند الحد ونسيب
            # الفرق ظاهر بدل ما نكتب حصة مش معقولة.
            for _key in _movable:
                _cap_hi = 3.0 / max(_cum.get(_key, 1.0), 0.01)
                _cap_lo = 0.34 / max(_cum.get(_key, 1.0), 0.01)
                _use = min(max(_factor, _cap_lo), _cap_hi)
                if abs(_use - 1.0) < 0.01:
                    _stuck.add(_key)
                    continue
                _new, _eff = scale_meal(day_plan[_key], _use)
                day_plan[_key] = _new
                _cur_cals[_key] = _cur_cals.get(_key, 0) * _eff
                _cur_ps[_key] = _cur_ps.get(_key, 0) * _eff
                _cum[_key] = _cum.get(_key, 1.0) * _eff
                if abs(_eff - 1.0) < 0.01:
                    # ‏طلبنا منها تتحرك ومااتحركتش -- يبقى مالهاش كمية
                    # تتضرب (عدد أو حصة حرة). مش هتتحرك في تمريرة تانية.
                    _stuck.add(_key)
        # ── بروتين اليوم يوصل للمستهدف ───────────────────────────────
        #
        # ‏المعامل فوق بيشد السعرات والبروتين مع بعض، فيوم التدوير
        # المنخفض بروتينه بينزل معاه. قِسْتها: أنثى ٩٥ كجم هدفها ١٥٢ جم
        # كان أسبوعها بين ٧٨ و١٤٤ -- ناقص ٤٩٪. ويوم الـ٧٨ في عجز هو
        # بالظبط اللي العميل بيفقد فيه عضل، والورقة بتقول ١٥٢.
        #
        # ‏الخانة بتتسد بزيادة بروتين مقابلها نقص سعرات من أقل خانة
        # كثافة بروتين (وهي النشوية). الحسبة في protein_fix، ومعاها
        # ليه الترتيب لوحده مش حل.
        if _target_p > 0 and day_plan.get(_pf_slot_for(plan_info)):
            _slots = {_k: (_cur_cals.get(_k, 0), _cur_ps.get(_k, 0))
                      for _k in plan_info["meal_labels"]
                      if day_plan.get(_k) and _cur_cals.get(_k, 0) > 0}
            _top = protein_fix.plan_topup(
                sum(_cur_ps.values()), _target_p, _slots, _pf_safe,
                turn=i, used=_pf_used)
            if _top:
                # ── القطع الأول، والزيادة بقدر اللي اتحرّر فعلاً ──
                #
                # ‏الترتيب ده مش تفصيلة. فيه أطباق مابتتحركش ("٢ بيض"
                # مش بيبقى "١.٨ بيضة"، والسلطة الحرة مالهاش كمية)،
                # فالقطع ممكن يطلب سعرات ومايحرّرش ولا واحدة. وأنا
                # كنت بزوّد الأول وأفترض إن القطع هيدفع -- فاليوم كان
                # بيكسب سعرات ببلاش، والطقم مسكها: أيام في نظام الخمس
                # وجبات بعدت ١١-١٥٪ عن هدفها.
                #
                # ‏دلوقتي القطع بيتعمل ويتقاس، والزيادة بتتسقّف على
                # المقاس. ولو مااتحرّرش حاجة، مافيش زيادة خالص.
                _freed = 0.0
                for _tk, _take in _top["trims"]:
                    if _cur_cals.get(_tk, 0) <= 0 or _take <= 0:
                        continue
                    _before = _cur_cals[_tk]
                    _shrink = max(0.2, 1.0 - _take / _before)
                    _new, _eff = scale_meal(day_plan[_tk], _shrink)
                    day_plan[_tk] = _new
                    _cur_cals[_tk] *= _eff
                    _cur_ps[_tk] *= _eff
                    _freed += _before - _cur_cals[_tk]

                _src = _top["source"]
                _per_g = _src["cal"] / 100.0
                _grams = int(round(min(_top["grams"],
                                       _freed / _per_g if _per_g else 0)
                                   / 5.0) * 5)
                if _grams > 0:
                    _slot = _pf_slot_for(plan_info)
                    _add = dict(_top, grams=_grams)
                    day_plan[_slot] = (day_plan[_slot] + " + "
                                       + protein_fix.line(_add))
                    _cur_cals[_slot] = (_cur_cals.get(_slot, 0)
                                        + _grams * _per_g)
                    _cur_ps[_slot] = (_cur_ps.get(_slot, 0)
                                      + _grams * _src["p"] / 100.0)
                    _pf_used[_src["ar"]] = _pf_used.get(_src["ar"], 0) + 1
                    day_plan["protein_topup"] = {
                        "grams": _grams,
                        "source_ar": _src["ar"],
                        "source_en": _src["en"],
                        "slot": _slot,
                        "trim": _top["trims"][0][0] if _top["trims"] else "",
                        "closed": bool(_top["closed"]
                                       and _grams >= _top["grams"]),
                    }

        if sum(_cur_cals.values()) > 0:
            total_cal = int(round(sum(_cur_cals.values())))
            total_p = int(round(sum(_cur_ps.values())))

        day_plan["total_cal"] = total_cal
        day_plan["total_p"] = total_p
        if i < len(zz_days):
            zd = zz_days[i]
            day_plan["target_cal"] = zd["kcal"]
            day_plan["zigzag_pct"] = zd["pct"]
            day_plan["zigzag_level"] = zd["level"]
            day_plan["target_p"] = zd["protein_g"]
            day_plan["target_c"] = zd["carb_g"]
            day_plan["target_f"] = zd["fat_g"]
        plan.append(day_plan)
    return plan

def get_allowed_forbidden(symptoms, goal="weight_loss"):
    from meal_database import unsafe_keys_for, _contains_unsafe
    has_g6pd = _has(symptoms, ["g6pd","g6bd","فافيزم"])
    has_thal = _has(symptoms, ["ثلاسيميا","thalassemia"])
    has_colon = _has(symptoms, ["قولون عصبي","ibs"])
    has_lactose = _has(symptoms, ["لاكتوز","lactose"])
    needs_d3 = _has(symptoms, ["نقص فيتامين d","نقص d3"])
    needs_fe = _has(symptoms, ["نقص الحديد","فقر دم"])
    if goal in ["muscle_gain","bulking"]:
        allowed = ["مصادر بروتين عالية: دجاج + لحم + سمك + بيض","كاربوهيدرات معقدة: ارز بني + شوفان + بطاطا",
                   "مكسرات + افوكادو + زيت زيتون","حليب كامل + زبادي يوناني","بروتين شيك بعد التمرين"]
        forbidden = ["الأكل المقلي الزائد","السكريات المضافة","المشروبات الغازية","الوجبات السريعة"]
    else:
        allowed = ["دجاج مشوي أو فرن + بيض","شوفان + خبز أسمر + أرز بني",
                   "زبادي يوناني سادة + جبن قريش","ملوخية + كوسة + خضار مطبوخة",
                   "زيت زيتون (ملعقة) + فاكهة طازجة","شاي أخضر + ماء بالليمون"]
        forbidden = ["الخبز الأبيض","الأكل المقلي + السمن","المشروبات الغازية","الحلويات والسكريات"]
    if has_g6pd:
        forbidden = ["الفول بكل أنواعه","الحمص والبقوليات الحمراء"] + forbidden
        allowed = ["عدس أصفر بكميات محدودة"] + allowed
    else:
        if goal in ["weight_loss","maintenance"]:
            allowed = ["فول مدمس + عدس + شوربات + سمك مشوي"] + allowed
    if has_thal:
        forbidden = ["الكبدة والأعضاء الداخلية","اللحوم الحمراء بإفراط"] + forbidden
        allowed = ["شاي مع الوجبات"] + allowed
    if has_colon:
        forbidden.append("التوابل الحارة")
        forbidden.append("الكافيين الزائد")
    if has_lactose:
        forbidden = ["الحليب والألبان كاملة الدسم","الجبن الطازج","الايس كريم"] + forbidden
        allowed = ["حليب اللوز / الصويا / جوز الهند","جبن معتق بكميات قليلة"] + allowed
    if needs_d3:
        allowed = ["أسماك دهنية: سلمون","صفار البيض + الفطر","تعرض للشمس 15 دقيقة"] + allowed
    if needs_fe and not has_thal:
        allowed = ["لحوم حمراء + كبدة","سبانخ + عدس"] + allowed

    # ── حالات إضافية ──
    has_diabetes = _has(symptoms, ["سكري","سكر","diabet"])
    has_hyper = _has(symptoms, ["ضغط","hypertension"])
    has_kidney = _has(symptoms, ["كلى","كلي","كلوي","kidney"])
    has_heart = _has(symptoms, ["قلب","heart","شريان"])
    has_preg = _has(symptoms, ["حمل","رضاع","حامل","pregnan"])
    has_obesity = _has(symptoms, ["سمنة","obes"])
    has_constip = _has(symptoms, ["امساك","إمساك","constip"])
    if has_diabetes:
        forbidden = ["السكر المضاف + العصائر + المشروبات الغازية","الأرز الأبيض والخبز الأبيض","الحلويات والمعجنات"] + forbidden
        allowed = ["كارب معقّد بكميات محسوبة: شوفان + أرز بني","خضار غير نشوية + بروتين في كل وجبة","قياس السكر قبل الأكل وبعده بساعتين"] + allowed
    if has_hyper:
        forbidden = ["الملح الزائد + المخللات + المعلبات","الصوصات الجاهزة + اللحوم المصنّعة"] + forbidden
        allowed = ["أكل قليل الملح + خضار ورقية","تقليل الكافيين + مياه كافية"] + allowed
    if has_kidney:
        forbidden = ["البوتاسيوم العالي: موز/طماطم/بطاطا بكثرة","البروتين والفوسفور الزائد","الملح والمعلبات"] + forbidden
        allowed = ["بروتين معتدل حسب تعليمات الطبيب","كمية المياه حسب إرشاد الطبيب"] + allowed
    if has_heart:
        forbidden = ["الدهون المشبعة + المقليات","اللحوم المصنّعة + السمن"] + forbidden
        allowed = ["أوميجا 3: سمك مرتين أسبوعياً","زيت زيتون + أفوكادو + مكسرات"] + allowed
    if has_preg:
        forbidden = ["الكبدة + الأسماك عالية الزئبق","الأطعمة النيئة وغير المبسترة","الكافيين الزائد"] + forbidden
        allowed = ["حمض فوليك: خضار ورقية + بقوليات","كالسيوم: ألبان مبسترة","حديد وبروتين كافي"] + allowed
    if has_obesity:
        forbidden = ["الوجبات السريعة + السعرات الفارغة","المشروبات السكرية"] + forbidden
        allowed = ["عجز سعري معتدل + بروتين عالي","خضار كتير + مشي يومي"] + allowed
    if has_constip:
        allowed = ["ألياف: خضار + فاكهة بقشرها + شوفان","مياه كافية (8 أكواب)","زبادي / بروبيوتيك"] + allowed

    # ── أمراض إضافية ──
    has_hypothyroid = _has(symptoms, ["خمول الغدة","hypothyroid","قصور الغدة"])
    has_hyperthyroid = _has(symptoms, ["نشاط الغدة","hyperthyroid","فرط الغدة","فرط نشاط"])
    has_gout = _has(symptoms, ["نقرس","gout","حمض اليوريك","يوريك"])
    has_fatty_liver = _has(symptoms, ["كبد دهني","الكبد الدهني","fatty liver","دهون الكبد"])
    has_chol = _has(symptoms, ["كوليسترول","cholesterol","دهون الدم"])
    has_uc = _has(symptoms, ["القولون التقرحي","تقرحي","ulcerative","كرون","crohn"])
    has_t1d = _has(symptoms, ["النوع الاول","النوع الأول","type 1","نوع اول"])

    if has_hypothyroid:
        forbidden = ["الجلوتين (خصوصاً مع هاشيموتو)","الصويا بكثرة","الكرنب/القرنبيط النيء بكثرة","الأكل المصنّع والسكريات"] + forbidden
        allowed = ["يود: سمك + بيض","سيلينيوم: مكسرات برازيلي","زنك + بروتين كافي","خضار مطبوخة"] + allowed
    if has_hyperthyroid:
        forbidden = ["اليود الزائد (ملح اليود + أعشاب بحرية)","الكافيين والمنبّهات"] + forbidden
        allowed = ["سعرات وبروتين أعلى (الحرق عالي)","كالسيوم + فيتامين D لحماية العظم","وجبات متكررة"] + allowed
    if has_gout:
        forbidden = ["اللحوم الحمراء + الأعضاء (كبدة/كلاوي)","مأكولات بحرية عالية البيورين","الفركتوز والمشروبات السكرية","الكحول"] + forbidden
        allowed = ["مياه كثيرة (2-3 لتر)","ألبان قليلة الدسم","كرز + فيتامين C","بروتين نباتي معتدل"] + allowed
    if has_fatty_liver:
        forbidden = ["السكر والفركتوز والعصائر","المقليات والدهون المشبعة","الأكل المصنّع","الكحول"] + forbidden
        allowed = ["نزول 10% من الوزن","ألياف 25جم يومياً على الأقل","دهون أقل من 25% من السعرات",
                   "خضار ورقية + بروكلي + كرنب","حبوب كاملة: أرز بني وشوفان وكينوا","بروتين قليل الدهن + أوميجا 3",
                   "رياضة 30 دقيقة يومياً"] + allowed
    if has_chol:
        forbidden = ["الدهون المشبعة والمتحولة","المقليات + السمن + المعجنات","صفار البيض بكثرة"] + forbidden
        allowed = ["ألياف ذائبة: شوفان + بقوليات","أوميجا 3: سمك دهني","زيت زيتون + مكسرات + أفوكادو"] + allowed
    if has_uc:
        forbidden = ["الألياف الخشنة وقت النوبة","البهارات الحارة + الدهون العالية","الألبان لو فيه حساسية","الكحول والكافيين"] + forbidden
        allowed = ["أكل سهل الهضم وقت النوبة","بروتين قليل الدهن + أوميجا 3","سوائل كافية","بروبيوتيك حسب التحمّل"] + allowed
    if has_t1d:
        forbidden = ["السكريات السريعة المنفردة","العصائر والمشروبات الغازية"] + forbidden
        allowed = ["حساب الكارب لكل وجبة (carb counting)","توزيع الكارب مع جرعة الأنسولين","كارب معقّد + ألياف","سناك لتجنب هبوط السكر"] + allowed

    # ‏آخر خطوة: القايمة تتعرض على نفس قوايم المنع اللي الوجبات بتتفلتر بيها.
    #
    # القوايم فوق مكتوبة بإيد وبفرع لكل حالة (_has)، فأي حالة مالهاش فرع
    # بتاخد القايمة العامة. النتيجة إن ورقة مريض سيلياك كانت بتقول له إن
    # **"شوفان + خبز أسمر + أرز بني" مسموح** -- والفلترة في نفس الوقت شايلة
    # كل وجبة فيها خبز من جدوله. يعني الجدول صح والنصيحة اللي جنبه غلط.
    # نفس الحاجة في G6PD: "عدس أصفر بكميات محدودة" مكتوبة مسموح، والعدس في
    # قايمة منعه.
    #
    # الفلترة بتحصل على مستوى الصنف مش السطر: "شوفان + خبز أسمر + أرز بني"
    # بيفضل "شوفان + أرز بني" -- لو شلنا السطر كله كنا هنمنع الشوفان والأرز
    # البني بلا سبب. واللي بيتشال بيتحوّل للممنوع، عشان المريض يشوف السبب.
    keys = unsafe_keys_for(symptoms)
    if keys:
        def _banned(item):
            return any(_contains_unsafe(item, k) for k in keys)

        kept, dropped = [], []
        for line in allowed:
            parts = [x.strip() for x in str(line).split(" + ") if x.strip()]
            safe = [x for x in parts if not _banned(x)]
            dropped += [x for x in parts if _banned(x)]
            if safe:
                kept.append(" + ".join(safe))
        allowed = kept
        for item in dropped:
            if item not in forbidden:
                forbidden.append(item)

    return allowed[:8], forbidden[:8]

# ‏نطاقات الإيموجي اللي بتظهر في نصوص الوجبات: الأكل والرموز والأسهم
# والعلامات. بنشيلها من الورقة المطبوعة بس -- الشاشة بتفضل زي ما هي.
_EMOJI_RX = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0001F000-\U0001F2FF\U0000FE00-\U0000FE0F\U00002190-\U000021FF"
    "\U00002700-\U000027BF\U0000200D]+")


def _protein_target(data, weight, per_kg):
    """‏هدف البروتين زي ما المحرّك حسبه بالظبط.

    ‏الورقة والمحرّك لازم يكونوا على نفس الرقم. كانوا اتنين: المحرّك
    على protein_need والورقة على weight × per_kg، فورقة نورة (١٠
    سنين) طبعت ١٤١ جم والجدول اللي تحتها متبني على ٥٠.
    """
    try:
        import protein_need
        grams, _basis, _why, _used = protein_need.target_grams(
            weight, data.get("height"), data.get("age"), per_kg)
        return grams
    except Exception:
        return round(float(weight or 0) * float(per_kg or 0))


def plan_html(data, plan=None, clean=False):
    """‏صفحة الجدول كـHTML. build_pdf تحتها بتحوّلها لـPDF.

    مفصولة عن التحويل لسببين: الاختبار يقرا HTML مباشرة بدل ما يستخرج نص من
    PDF (استخراج العربي بيلغبط الحروف فالاختبار عليه مش دليل)، والصفحة دي
    تنفع تتعرض أو تتطبع زي ما هي بعدين.

    clean=True يشيل هوية العيادة: اسمها، اسم المُعِد، ورقم الملف. الدكتور
    بيشتغل في أكتر من مكان، ومايصحّش يسلّم عميل في عيادة تانية ورقة مكتوب
    عليها اسم عيادة غيرها. الكلام الطبي كله بيفضل زي ما هو: البيانات،
    الجدول، المسموح والممنوع، والماء. اللي بيتشال هوية، مش محتوى.
    """
    import datetime as dt
    if plan is None: plan = generate_weekly_plan(data)

    # The PDF is the artefact the client keeps, so it follows the language the
    # plan was produced in. Meal text is stored in Arabic (the condition filters
    # match on it) and translated on the way into the document.
    _pdf_ar = session.get("lang", "ar") == "ar"

    def _L(ar, en):
        return ar if _pdf_ar else en

    def _meal(txt):
        return txt if _pdf_ar else translate_meal(txt)

    symptoms = data.get("symptoms", [])
    goal = data.get("goal_type", "weight_loss")
    diet_type = data.get("diet_plan_type", "standard")
    plan_info = get_diet_plan_info(diet_type)
    allowed, forbidden = get_allowed_forbidden(symptoms, goal)
    try:
        tdee = float(data.get("tdee", 0) or 0)
        target = float(data.get("goal_cal", 0) or 0)
        deficit = int(tdee - target) if tdee and target else 0
    except: deficit = 0
    notes_parts = []
    if symptoms: notes_parts.append(" - ".join(symptoms))
    allergies_data = data.get("allergies", [])
    if allergies_data: notes_parts.append(_L("حساسية: ", "Allergies: ") + " - ".join(allergies_data))
    if data.get("disliked_foods"): notes_parts.append(_L("لا يأكل: ", "Does not eat: ") + data.get("disliked_foods"))
    if data.get("notes"):
        # guidance notes are stored in Arabic; render them in the reader's language
        _n = data.get("notes")
        if not _pdf_ar:
            # translate_boost_note works off a fixed map, so it cannot touch a
            # line carrying live numbers or a day name. The chemical-diet lines
            # ship their own English, keyed by the exact Arabic that went into
            # the notes.
            _own_en = {ar: en for ar, en in (data.get("chemical_note_pairs") or [])}
            _n = " | ".join(
                _own_en.get(part.strip()) or translate_boost_note(part.strip())
                for part in _n.split("|"))
        notes_parts.append(_n)
        notes_rendered = _n
    else:
        notes_rendered = ""
    clinical_notes = " | ".join(notes_parts) if notes_parts else _L("لا توجد ملاحظات", "No notes")
    uid = session.get("uid", 0)
    file_num = f"NX-{dt.datetime.now().year}-{uid:03d}"
    goal_labels = ({"weight_loss":"خطة تخسيس","muscle_gain":"خطة زيادة عضل","bulking":"خطة تضخيم","cutting":"خطة تنشيف","maintenance":"خطة مكتنز"}
                   if _pdf_ar else
                   {"weight_loss":"Weight Loss Plan","muscle_gain":"Muscle Gain Plan","bulking":"Bulking Plan","cutting":"Cutting Plan","maintenance":"Maintenance Plan"})
    plan_title = goal_labels.get(goal, _L("خطة غذائية", "Meal Plan"))
    pdf_days = []
    for d in plan:
        meals_html = []
        for meal_key in plan_info["meals"]:
            _labels = plan_info["meal_labels"] if _pdf_ar else (plan_info.get("meal_labels_en") or plan_info["meal_labels"])
            label = _labels.get(meal_key, meal_key)
            emoji = plan_info["meal_emojis"].get(meal_key, "-")
            meal_text = d.get(meal_key, "")
            if meal_text:
                meals_html.append({"label": label, "emoji": emoji, "text": _meal(meal_text)})
        pdf_days.append({"name": d["day"] if _pdf_ar else ENGLISH_DAYS.get(d["day"], d["day"]),
                         "total_kcal": d["total_cal"], "total_p": d.get("total_p", 0),
                         "target_kcal": d.get("target_cal"), "zigzag_pct": d.get("zigzag_pct"),
                         "meals": meals_html,
                         "breakfast": _meal(d.get("breakfast","")), "lunch": _meal(d.get("lunch","")),
                         "dinner": _meal(d.get("dinner","")), "snack": _meal(d.get("snack",""))})
    template_data = {
        'file_number': file_num, 'date': dt.date.today().strftime('%d/%m/%Y'),
        'plan_title': plan_title,
        'diet_plan_name': plan_info["name"] if _pdf_ar else (plan_info.get("name_en") or plan_info["name"]),
        'culture': _CULTURE_EN.get(data.get("culture"), data.get("culture", "-")) if not _pdf_ar else data.get("culture","مصري"),
        'client': {'name': (data.get('name') or '').strip(), 'age': data.get('age','-'),
            'gender': data.get('gender','-'), 'height': data.get('height','-'),
            'weight': data.get('weight','-'), 'bmi': data.get('bmi','-'),
            'body_fat': data.get('fat_pct','-'), 'tdee': data.get('tdee','-'),
            'target_kcal': data.get('goal_cal','-'), 'deficit': deficit},
        'conditions': symptoms if symptoms else [_L("لا توجد حالات مسجلة", "No conditions recorded")],
        'clinical_notes': clinical_notes,
        'allowed': allowed, 'forbidden': forbidden, 'days': pdf_days,
        'tips': {
            'water': ['كوب ماء دافئ + نصف ليمونة فور الاستيقاظ','8 أكواب ماء يومياً',
                      'كوب ماء قبل كل وجبة بـ 30 دقيقة','تجنب الماء البارد جداً']
                     if _pdf_ar else
                     ['A glass of warm water with half a lemon on waking',
                      '8 glasses of water a day',
                      'A glass of water 30 minutes before each meal',
                      'Avoid very cold water'],
            'habits': ['مضغ بطيء - الشبع بعد 20 دقيقة','لا تأكل أمام الشاشة',
                       'نوم 7-8 ساعات','تعرض للشمس يومياً']
                      if _pdf_ar else
                      ['Chew slowly -- fullness registers after 20 minutes',
                       'Do not eat in front of a screen',
                       'Sleep 7-8 hours', 'Get daily sun exposure'],
            'metabolism': ((['بروتين في كل وجبة','توابل آمنة: كركم + قرفة + زنجبيل',
                             'مشي 30 دقيقة بعد الغداء','قم وتحرك 5 دقائق كل ساعة']
                            if goal in ["weight_loss","maintenance"] else
                            ['بروتين في كل وجبة (1.6-2.2 جم/كجم)','كارب حول التمرين',
                             'تدريب مقاومة 4-5 مرات أسبوعياً','نوم 7-9 ساعات'])
                           if _pdf_ar else
                           (['Protein at every meal',
                             'Safe spices: turmeric, cinnamon, ginger',
                             'A 30-minute walk after lunch',
                             'Stand and move for 5 minutes every hour']
                            if goal in ["weight_loss","maintenance"] else
                            ['Protein at every meal (1.6-2.2 g/kg)',
                             'Carbs around training',
                             'Resistance training 4-5 times a week',
                             'Sleep 7-9 hours'])),
            'warnings': ['لا تخفض السعرات أكثر من المحدد','لو جعت: ماء أولاً ثم فاكهة',
                         'راجع مع أخصائي التغذية كل 4 أسابيع','أي أعراض غير عادية - راجع طبيبك']
                        if _pdf_ar else
                        ['Do not cut calories below the target',
                         'If hungry: water first, then fruit',
                         'Review with your dietitian every 4 weeks',
                         'Any unusual symptoms -- see your doctor'],
        },
        'clinic_name': 'NutraX Clinical Nutrition',
        'author': _L('إعداد د. محمد - أخصائي التغذية الإكلينيكية',
                     'Prepared by Dr. Mohamed - Clinical Dietitian'),
        'review_weeks': 4,
    }
    # ═══════ توليد PDF: صفحة واحدة، الأيام صفوف والوجبات أعمدة ═══════
    def _esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    def _plain(s):
        """‏نص الوجبة من غير إيموجي.

        الوجبة متخزّنة بإيموجي عشان الشاشة، والشاشة مكان مناسب لها. الورقة
        اللي بتتسلّم للعميل لأ: ٤ إيموجي في الخانة × ٢٨ خانة = ١١٢ رسمة
        ملوّنة على ورقة واحدة، وهي أول حاجة العين بتشوفها قبل الأكل نفسه.
        الداتا مابتتغيّرش -- ده رسم الورقة بس.
        """
        out = _EMOJI_RX.sub("", str(s)).replace("  ", " ").strip()
        if _pdf_ar:
            # ‏"kcal" كلمة لاتينية جوّه سطر عربي، والترتيب الثنائي بيقلبها
            # مع الرقم اللي قبلها: "تفاح 300جم - 80 kcal" كانت بتتطبع
            # "نفاحة (300جمkcal 80 - )" على الورقة. صوّرت الـPDF وشفتها.
            # الكلمة العربية بتتخلص من المشكلة من أصلها.
            out = re.sub(r"(?<![a-zA-Z])kcal(?![a-zA-Z])", "سعرة", out)
        return out

    def _fmt_cell(text):
        if not text:
            return "-"
        parts = [p.strip() for p in _plain(text).split(" + ") if p.strip()]
        out = []
        for p in parts:
            p = _esc(p)
            # units appear in Arabic or English depending on the PDF language
            p = re.sub(r'(\d+[\.\d]*\s*(?:جم|مل|كوب|ملعقة|ملاعق|قطع|قطعة|حبات|شريحتين|ثمرة'
                       r'|g|ml|cup|tbsp|pcs?|slices?|piece)?)',
                       r'<b>\1</b>', p, count=1)
            out.append(f'<span class="it">{p}</span>')
        return "".join(out)

    td = template_data
    cl = td['client']
    pdays = td['days']
    # ‏هوية العيادة: سطر تحت العنوان، رقم الملف، والتوقيع تحت. التلاتة بيختفوا
    # مع بعض في الوضع النضيف -- لو واحد فضل، الورقة لسه بتقول إنها من هنا.
    _by_line = ("" if clean else
                f'<div class="s">{_esc(td["clinic_name"])} • {_esc(td["author"])}</div>')
    _file_line = ("" if clean else
                  f'{_L("ملف", "File")}: {_esc(td["file_number"])}<br>')
    _sig_by = "" if clean else f' — {_esc(td["author"])}'
    # أعمدة الوجبات (من أول يوم - تنفع لأي نظام)
    columns = [m['label'] for m in pdays[0]['meals']] if pdays else []
    # ‏عَرضية دايماً. كانت بتتقرر من عدد الأعمدة (عرضية لو ٥ أو أكتر،
    # وإلا طولية)، بس ورقة الشركة عَرضية -- والشكل بقى عليها، فالاتجاه
    # بقى واحد. ولا أقل عدد أعمدة (يوم + وجبتين + سعرات + بروتين = ٥)
    # بيضيق في العَرضية.
    orientation = "landscape"

    # رأس الجدول
    _zz = data.get("zigzag") or None
    head_cells = f'<th class="dcol">{_L("اليوم", "Day")}</th>'
    for c in columns:
        head_cells += f'<th>{_esc(c)}</th>'
    if _zz:
        head_cells += f'<th class="kcol">{_L("هدف اليوم", "Day target")}</th>'
    head_cells += (f'<th class="kcol">{_L("سعرات", "kcal")}</th>'
                   f'<th class="kcol">{_L("بروتين", "Protein")}</th>')

    # صفوف الأيام
    body_rows = ""
    _sum_cal = 0
    _sum_p = 0
    for d in pdays:
        cells = f'<td class="dcell">{_esc(d["name"])}</td>'
        by_label = {m['label']: m['text'] for m in d['meals']}
        for c in columns:
            cells += f'<td>{_fmt_cell(by_label.get(c, "-"))}</td>'
        if _zz:
            _tk = d.get("target_kcal")
            _tp = d.get("zigzag_pct") or 0
            # النسبة في سطر لوحدها وبـ nowrap، عشان الـ "%" ما ينزلش لسطر تالت في عمود ضيّق
            _sfx = (f'<br><span style="white-space:nowrap;font-size:9px">'
                    f'{"+" if _tp > 0 else ""}{_tp}%</span>') if _tp else ""
            cells += f'<td class="kcell">{_esc(_tk) if _tk else "-"}{_sfx}</td>'
        cells += f'<td class="kcell">{_esc(d["total_kcal"])}</td>'
        cells += f'<td class="kcell">{_esc(d.get("total_p", 0))} {_L("جم", "g")}</td>'
        body_rows += f'<tr>{cells}</tr>'
        _sum_cal += d.get("total_kcal", 0) or 0
        _sum_p += d.get("total_p", 0) or 0

    _n = max(len(pdays), 1)
    _avg_cal = round(_sum_cal / _n)
    _avg_p = round(_sum_p / _n)

    # ── سطر المتابعة ── الأرقام اللي تقول للعميل إن حاجة اتغيّرت من آخر زيارة
    _fu = data.get("followup") or None
    if _fu:
        _dir = _L("نزل", "down") if _fu["delta"] < 0 else (
            _L("زاد", "up") if _fu["delta"] > 0 else _L("ثابت", "unchanged"))
        _amount = f" {abs(_fu['delta'])} {_L('كجم', 'kg')}" if _fu["delta"] else ""
        _rate = (f" ({_fu['rate']} {_L('كجم/أسبوع', 'kg/wk')})") if _fu["rate"] else ""
        _fu_line = (
            f'<div class="meta" style="background:#eef4f1">'
            f'<span><b>{_L("متابعة رقم", "Follow-up visit")}:</b> {_esc(data.get("visit_no", 2))}</span>'
            f'<span><b>{_L("الوزن", "Weight")}:</b> {_fu["old_weight"]} &rarr; {_fu["new_weight"]} '
            f'{_L("كجم", "kg")}</span>'
            f'<span><b>{_esc(_dir)}{_esc(_amount)}</b> {_L("في", "over")} {_fu["days"]} '
            f'{_L("يوم", "days")}{_esc(_rate)}</span>'
            + (f'<span><b>{_L("TDEE الجديد", "New TDEE")}:</b> {_fu["new_tdee"]} kcal</span>'
               if _fu.get("new_tdee") else "")
            + f'</div>'
            f'<div class="fu-note">{_esc(_fu["note_ar"] if _pdf_ar else _fu["note_en"])}</div>')
    else:
        _fu_line = ""

    # سطر التدوير جنب السعرات المستهدفة، ومعاه المدى عشان القارئ يفهم إن اليوم بيتغيّر
    if _zz:
        # ‏اسم النمط نفسه بيبدأ بكلمة "تدوير" ("تدوير كلاسيكي (±٢٠٪)")،
        # فالبادئة كانت بتطبع "تدوير تدوير كلاسيكي" على الورقة.
        _zz_meta = (f" — {_esc(_zz['mode_ar'] if _pdf_ar else _zz['mode_en'])} "
                    f"({_zz['low']}–{_zz['high']} {_L('سعرة', 'kcal')})")
    else:
        _zz_meta = ""

    def _g(x):
        return x if _pdf_ar else translate_guidance(x)

    # clinical_notes كانت بتتحسب وتتبعت للقالب وماحدش بيعرضها، فالتحذيرات
    # (الأيام تحت الحد الآمن، تنبيهات الحالات، حساسية العميل) كانت توصل
    # للأخصائي في المعاينة وبس، والعميل ياخد الجدول من غيرها. صف كامل مش
    # عمود جوه .foot لأن النصوص دي جُمل مش عناصر قصيرة.
    _notes_items = [n.strip() for n in notes_rendered.split("|") if n.strip()]
    if _notes_items:
        notes_html = ('<div class="notes"><h4>'
                      + _L("ملاحظات طبية", "Clinical notes") + "</h4><ul>"
                      + "".join(f"<li>{_esc(n)}</li>" for n in _notes_items)
                      + "</ul></div>")
    else:
        notes_html = ""

    allowed_html = "".join(f"<li>{_esc(_plain(_g(x)))}</li>" for x in td['allowed'][:5])
    forbidden_html = "".join(f"<li>{_esc(_plain(_g(x)))}</li>" for x in td['forbidden'][:5])
    water_tips = "".join(f"<li>{_esc(_plain(x))}</li>" for x in td['tips']['water'][:3])

    # حساب الماكروز: بروتين بالوزن، دهون % من السعرات، الكارب الباقي
    PROTEIN_FACTORS = {"sedentary": 1.0, "light": 1.3, "regular": 1.6, "athlete": 2.0}
    ACTIVITY_LABELS = ({"sedentary": "قليل الحركة", "light": "نشاط خفيف",
                        "regular": "تمارين منتظمة / تخسيس", "athlete": "رياضي / بناء عضل"}
                       if _pdf_ar else
                       {"sedentary": "Sedentary", "light": "Lightly active",
                        "regular": "Trains regularly / weight loss",
                        "athlete": "Athlete / muscle building"})
    _act = (data.get("activity_level") or "regular")
    try:
        _ppk = float(data.get("protein_per_kg") or PROTEIN_FACTORS.get(_act, 1.6))
    except Exception:
        _ppk = PROTEIN_FACTORS.get(_act, 1.6)
    try:
        _fatp = float(data.get("fat_pct_cal") or 30)
    except Exception:
        _fatp = 30
    try:
        _w = float(data.get("weight") or 0)
    except Exception:
        _w = 0
    try:
        _kcal = float(data.get("goal_cal") or 0)
    except Exception:
        _kcal = 0
    _act_label = ACTIVITY_LABELS.get(_act, _L("تمارين منتظمة / تخسيس",
                                              "Trains regularly / weight loss"))
    macro_meta = ""
    if _w > 0 and _kcal > 0:
        # ‏نفس الحساب اللي المحرّك بيبني بيه، مش حساب تاني. كان
        # round(_w * _ppk) هنا و protein_need في المحرّك، فالورقة
        # تطبع ١٤١ لنورة والجدول متبني على ٥٠ -- الورقة بتناقض
        # الأكل اللي جوّاها.
        _pg = _protein_target(data, _w, _ppk)
        # ‏لطفل الورقة بتقول نطاق مش رقم: التوصية أرضية والـAMDR سقف.
        # ‏الدكتور كان شايف "٥٠ جم" وتحتيها جدول بيدي ١١٦، فيفتكرها
        # غلطة. هي مش غلطة -- هي رقمين مختلفين: أقل كمية مطلوبة،
        # وأكتر كمية مقبولة.
        _p_range = ""
        try:
            import protein_need as _pn_meta
            _bnd = _pn_meta.band(_w, data.get("height"), data.get("age"),
                                 _ppk, _kcal)
            if _bnd:
                _p_range = (" &mdash; %s %d-%d"
                            % (_L("النطاق المقبول", "accepted range"),
                               _bnd[0], _bnd[1]))
        except Exception:
            _p_range = ""
        _fg = round(_kcal * _fatp / 100 / 9)
        _cc = _kcal - (_pg * 4) - (_fg * 9)
        _cg = round(max(_cc, 0) / 4)
        macro_meta = (
            f'<span><b>{_L("مستوى النشاط", "Activity level")}:</b> {_esc(_act_label)}</span>'
            f'<span><b>{_L("بروتين مستهدف", "Protein target")}:</b> {_esc(_pg)} {_L("جم", "g")} ({_ppk} {_L("جم/كجم", "g/kg")}){_p_range}</span>'
            # ‏"مُقدّر": الرقمين دول محسوبين من **الهدف** مش من الأكل --
            # السعرات × النسبة ÷ ٩ للدهون، والباقي كارب. قِسْت إمكانية
            # حسابهم من مكوّنات الوجبات (meal_macros) والنتيجة إن ٧
            # وجبات بس من ٥٩٧ أصنافها كلها بجرامات مكتوبة. فلحد ما
            # الوجبات نفسها تحمل أرقامها، الورقة بتقول إنهم تقدير بدل
            # ما تقدّمهم كأنهم الأكل.
            f'<span><b>{_L("دهون (مُقدّرة)", "Fat (estimated)")}:</b> {_esc(_fg)} {_L("جم", "g")} ({int(_fatp)}%)</span>'
            f'<span><b>{_L("كارب (مُقدّر)", "Carbs (estimated)")}:</b> {_esc(_cg)} {_L("جم", "g")}</span>'
        )
        # ── سكري النوع الأول: توزيع الكارب على عدد الوجبات لعدّ الكارب، وحساب ICR/CF لو الجرعة اليومية متوفرة ──
        _is_t1d = any(("النوع الاول" in s or "النوع الأول" in s or "type 1" in s.lower()) for s in (symptoms or []))
        if _is_t1d:
            _meal_count = max(len(plan_info.get("meals", []) or []), 1)
            _carb_per_meal = round(_cg / _meal_count)
            macro_meta += (
                f'<span><b>🩸 {_L("كارب/وجبة (نوع 1)", "Carbs per meal (type 1)")}:</b> '
                f'~{_esc(_carb_per_meal)} {_L("جم", "g")} × {_meal_count} {_L("وجبات", "meals")}</span>'
            )
            try:
                _tdd = float(data.get("insulin_tdd") or 0)
            except (TypeError, ValueError):
                _tdd = 0
            if _tdd > 0:
                _icr = round(500 / _tdd, 1)
                _cf = round(1800 / _tdd)
                macro_meta += (
                    f'<span><b>{_L("نسبة الأنسولين للكارب", "Insulin-to-carb ratio")} (500 Rule):</b> '
                    f'1 {_L("وحدة", "unit")} / {_esc(_icr)} {_L("جم كارب", "g carbs")}</span>'
                    f'<span><b>{_L("معامل التصحيح", "Correction factor")} (1800 Rule):</b> '
                    f'1 {_L("وحدة تخفّض", "unit lowers")} ~{_esc(_cf)} {_L("مجم/دل", "mg/dL")}</span>'
                    f'<span style="font-size:11px;color:#991b1b">⚠️ '
                    f'{_L("دي قواعد بداية تقديرية معيارية — لازم تأكيد وضبط من طبيب الغدد الصماء حسب استجابة المريض الفعلية", "These are standard estimated starting rules -- they must be confirmed and adjusted by an endocrinologist against the patient s actual response")}</span>'
                )
            else:
                macro_meta += (
                    f'<span style="font-size:11px;color:#991b1b">'
                    f'{_L("نسبة الأنسولين للكارب ومعامل التصحيح: محتاجين إجمالي جرعة الأنسولين اليومية من الطبيب — لسه متدخلش", "Insulin-to-carb ratio and correction factor need the total daily insulin dose from the doctor -- not entered yet")}</span>'
                )

    _tcal = int(_kcal) if _kcal > 0 else None
    _tp = _protein_target(data, _w, _ppk) if _w > 0 else None
    # ── شكل ورقة الشركة. على **كل** نسخة، مش النضيفة بس ──
    #
    # ‏الدكتور بعت ورقة الشركة (IR Formula) وقال الأول: عايزه زيها في
    # الشكل لما أسلّمه للناس اللي متابعة معايا. فحطّيته على النسخة اللي
    # بتتسلّم بره العيادة بس. وبعدها قال: «الورقة اللي بعتها دي هي اللي
    # بديها للعميل -- طبّق عليها شكل كل جدول». فالشكل بقى على الاتنين:
    # اللي عليها اسم العيادة واللي من غيره. الفرق بينهم هوية، مش رسم.
    #
    # ‏والأرقام دي مقيسة من الـdocx نفسها، مش مقرّبة بالعين:
    #
    #   الأعمدة    ٧٤٥ / ٢٦٢٣ / ٤٤٢٥ / ٢٩٧٠ twip  =  ٧٪ / ٢٤٪ / ٤١٪ / ٢٨٪
    #   الإطار     TableGrid: single sz=4  =  نص بوينت أسود على كل خانة
    #   الرأس      خلفية F2F2F2، Calibri غامق ١٦pt، في النص
    #   عمود اليوم خلفية F2F2F2، غامق ١٢pt، في نص الخانة طولاً وعرضاً
    #   الخانات    بيضاء، النص في النص، غامق ١٢pt، كل صنف في سطر
    #   الصفحة     عَرضية
    #
    # ‏حاجة واحدة في ورقة الشركة مش منقولة: عمود اليوم عندها **مكتوب
    # طولاً** (textDirection=tbRl). جرّبت الطريقتين في WeasyPrint:
    # writing-mode بيتجاهله خالص، وtransform:rotate جوّه خانة بيطلّع
    # الحروف مركّبة على بعضها (صوّرت الناتج وشفته). فعمود اليوم أفقي
    # وعريض شوية عشان يتقرا -- باقي الشكل زي الورقة.
    #
    # ‏وجملة التنبيه اللي تحت ورقة الشركة **مش منقولة بالقصد**: هي
    # بتقول "مخصصة للأشخاص الأصحاء فقط"، وورقة الدكتور دي بتتبني على
    # حالات مرضية. نفس الجملة على ورقة فيها كلام إكلينيكي بتكدّب نفسها.
    _company_css = """
@page { margin: 9mm 11mm; }
body { color:#000; font-size:10.5px; }
.hdr { border-bottom:0 !important; padding-bottom:2px; margin-bottom:5px; }
.hdr .t { font-size:15.5px; font-weight:700; }
.meta { margin-bottom:6px !important; line-height:1.65 !important; }
table { border-collapse:collapse; }
th, td { border:0.5pt solid #000 !important; padding:3px !important;
         text-align:center !important; vertical-align:middle !important;
         font-weight:700 !important; font-size:9.5px !important;
         line-height:1.38 !important; }
th { background:#F2F2F2 !important; color:#000 !important;
     font-size:12px !important; letter-spacing:0 !important;
     padding:4px 3px !important; }
td { background:#fff !important; }
tr:nth-child(even) td { background:#fff !important; }
td.dcell { background:#F2F2F2 !important; font-size:10.5px !important; }
.dcol { width:50px; }
td .it { display:block; padding:0; }
td b { font-weight:700; }
/* ‏الأعمدة الرقمية: عناوينها كانت بتتقطّع نص كلمة ("سعرا/ت"،
   "بروتي/ن") لأن القاعدة العامة فيها word-wrap:break-word، وهي لازمة
   لخانات الأكل الطويلة. فالعمود الرقمي بس هو اللي بيلغيها. */
.kcol, .kcell { width:54px; }
th.kcol, td.kcell { white-space:normal !important;
                    word-wrap:normal !important;
                    overflow-wrap:normal !important; }
td.kcell { background:#F2F2F2 !important; font-size:9.5px !important; }
.summary { border-top:0.5pt solid #000; padding-top:5px; margin-top:0;
           font-size:9.5px; }
/* ‏المسموح والممنوع والماء كانوا بيزحّفوا لصفحة تانية لوحدهم -- صفحة
   كاملة لتلات لستات قصيرة، والعميل بياخد ورقتين. ورقة الشركة ورقة
   واحدة، فالمساحات هنا مضغوطة عشان الكل يدخل في الأولى. */
.foot { margin-top:6px !important; gap:10px !important; font-size:8px !important; }
.foot .fbox { border-top:0.5pt solid #000; padding-top:4px; }
.foot .fbox h4 { font-size:8.5px !important; color:#000 !important;
                 margin-bottom:2px !important; }
.foot .fbox li { margin-bottom:0 !important; }
.notes { margin-top:6px !important; font-size:8px !important;
         border-top:0.5pt solid #000; padding-top:4px; }
.notes h4 { color:#000 !important; }
.sig { margin-top:5px !important; font-size:8px !important; }
"""

    # ── الورقة ما تقولش رقم والأكل يدي غيره ──
    #
    # ‏سطر الماكروز فوق **وصفة**: وزن العميل × جرام/كجم. والأكل بيدي
    # حاجة تانية، وقِسْتها قبل الإصلاح: أنثى ٩٥ كجم هدفها ١٥٢ جم كان
    # أسبوعها بين ٧٨ و١٤٤. الزيادة في protein_fix قرّبت المسافة، بس
    # مش دايماً بتسدّها (حصة الزيادة لها حد، والنشوية اللي بنقطع منها
    # لها حد).
    #
    # ‏فالورقة بقت بتقول الاتنين: المستهدف، والفعلي، والفرق لو كبير.
    # الدكتور لازم يشوف الفرق ده قبل ما يسلّم الورقة -- مش يكتشفه من
    # عميل مابينزلش.
    # ‏التحذير بيضرب على حاجتين **إكلينيكيتين**، مش على نسبة مئوية:
    #
    #   ١) المتوسط الأسبوعي بعيد عن المستهدف. البروتين بيتحسب على
    #      الأسبوع مش على اليوم، فده الرقم اللي بيحكم على الخطة.
    #
    #   ٢) فيه يوم تحت أرضية الجرام/كجم. ده اللي بيحمي الكتلة العضلية
    #      في العجز، وقبل الإصلاح أنثى ٩٥ كجم نزلت ٠.٨٢ جم/كجم.
    #
    # ‏أول نسخة كانت بتضرب كمان على "أي يوم بعيد ٢٠٪ في أي اتجاه"،
    # والشرط ده كان بيضرب على ورقة متوسطها مظبوط بسبب يوم **زايد**
    # بروتين -- وزيادة البروتين في يوم مش مشكلة. فكان بيطلّع تحذير
    # على ورقة سليمة، والاختبار بقى متقلقل (فشل ٣ مرات من ١٠).
    # ‏سطر حساب البروتين لو اتغيّر عن "وزن × جرام/كجم" (طفل). لازم
    # يبان: الدكتور شايف "بروتين مستهدف ٥٠ جم" لطفلة ١٠٨ كجم، ولازم
    # يعرف الرقم جه منين.
    _p_warn_basis = ""
    if (data.get("protein_basis") or {}).get("why"):
        try:
            import protein_need
            _bn = protein_need.note(data.get("age"), data.get("height"),
                                    data.get("weight"),
                                    data.get("protein_per_kg") or _ppk,
                                    is_ar=_pdf_ar)
        except Exception:
            _bn = None
        if _bn:
            _p_warn_basis = ('<div class="pnote" style="color:#13394d;'
                             'background:#eef4f8;border-color:#1B6E80">ℹ️ '
                             + _esc(_bn.replace("**", "")) + '</div>')

    # ‏الطفل: نطاق مش رقم واحد.
    #
    # ‏التوصية (RDA) أرضية -- أقل كمية تمنع النقص -- ومش سقف. وقاعدة
    # الأكل أطباق بالغين: أقل كثافة بروتين في الغدا ٠.٠٤٤ جم/سعر،
    # وكثافة احتياج نورة ٠.٠٢٦. يعني مافيش أسبوع من القاعدة دي
    # بيوقف على ٥٠ جم بالظبط، ولو قارنّا بالرقم لوحده الورقة هتفضل
    # مكتوب عليها تحذير للأبد من غير ما يكون فيه غلط إكلينيكي.
    #
    # ‏فالمقارنة بقت على النطاق المنشور (AMDR): ١٠-٣٠٪ من سعرات
    # اليوم، أرضيته مابتنزلش تحت التوصية. والتحذير بيضرب لما الأكل
    # يخرج منه فعلاً -- وده اللي كان بيحصل قبل ترتيب الكثافة: يوم
    # ١٦٥ جم على ١٦٢١ سعرة = ٤١٪ من الطاقة، برّه النطاق بوضوح.
    _band = None
    try:
        import protein_need as _pn_band
        _band = _pn_band.band(_w, data.get("height"), data.get("age"),
                              _ppk, _kcal or _avg_cal)
    except Exception:
        _band = None

    _p_warn = ""
    if _band and _avg_p:
        _blo, _bhi = _band
        # ‏كل يوم على سعرات **نفسه**: النطاق نسبة من الطاقة، ويوم
        # التدوير العالي (٢٢٠٠) نطاقه أوسع من يوم الـ١٥٣٠. لو اتقاسوا
        # كلهم على هدف اليوم المتوسط، يوم عالي سليم بيطلع "برّه".
        _out = []
        for _d in pdays:
            _dband = None
            try:
                _dband = _pn_band.band(_w, data.get("height"),
                                       data.get("age"), _ppk,
                                       _d.get("total_kcal") or _d.get("total_cal") or 0)
            except Exception:
                _dband = None
            _dlo, _dhi = _dband or (_blo, _bhi)
            if not (_dlo <= (_d.get("total_p") or 0) <= _dhi):
                _out.append(_d)
        if _avg_p > _bhi or _avg_p < _blo or len(_out) >= 2:
            _dir_ar = "تحت" if _avg_p < _blo else "فوق"
            _dir_en = "below" if _avg_p < _blo else "above"
            _p_warn = (
                f'<div class="pnote">⚠️ '
                f'{_L("بروتين الأكل في الجدول", "The protein in this plan")} '
                f'({_avg_p} {_L("جم/يوم بالمتوسط", "g/day on average")}) '
                f'{_L(_dir_ar, _dir_en)} '
                f'{_L("النطاق المقبول لسن الطفل", "the accepted range for this child")} '
                f'({_blo}-{_bhi} {_L("جم", "g")}). '
                f'{_L("راجع الحصص قبل التسليم.", "Review the portions before handing this over.")}'
                f'</div>')
    elif _tp and _avg_p:
        _off = abs(_avg_p - _tp) / float(_tp)
        # ‏يوم تحت الأرضية، **أو** يوم ناقص ربع وصفته. التاني لازم:
        # هدف ١.٦ جم/كجم ناقص ٣٦٪ لسه فوق الأرضية (١.٠٢)، فاليوم ده
        # كان بيعدّي من غير تحذير -- والدكتور مايشوفوش. والفحص على
        # الناقص بس، لأن يوم زايد بروتين مش مشكلة.
        _low = [d for d in pdays
                if (_w > 0 and (d.get("total_p") or 0) / _w < 0.95)
                or (d.get("total_p") or 0) < _tp * 0.75]
        if _off > 0.12 or _low:
            _dir_ar = "أقل من" if _avg_p < _tp else "أعلى من"
            _dir_en = "below" if _avg_p < _tp else "above"
            _why_ar = (" ويوم أو أكتر بروتينه تحت ٠.٩٥ جم/كجم"
                       if _low else "")
            _why_en = (" and at least one day is below 0.95 g/kg"
                       if _low else "")
            _p_warn = (
                f'<div class="pnote">⚠️ '
                f'{_L("بروتين الأكل في الجدول", "The protein in this plan")} '
                f'({_avg_p} {_L("جم/يوم بالمتوسط", "g/day on average")}) '
                f'{_L(_dir_ar, _dir_en)} '
                f'{_L("المستهدف", "the target")} ({_tp} {_L("جم", "g")})'
                f'{_L(_why_ar, _why_en)}. '
                f'{_L("ظبّط جرام/كجم أو زوّد بروتين في الوجبات قبل التسليم.", "Adjust the g/kg or add protein to the meals before handing this over.")}'
                f'</div>')

    summary_box = (_p_warn_basis + _p_warn + f'<div class="summary"><span><b>{_L("المتوسط الفعلي/يوم", "Actual average per day")}:</b> '
                   f'{_avg_cal} {_L("سعرة", "kcal")} • {_avg_p} {_L("جم بروتين", "g protein")}</span>'
                   f'<span><b>{_L("الهدف", "Target")}:</b> {_tcal if _tcal else "-"} {_L("سعرة", "kcal")} • '
                   f'{_tp if _tp else "-"} {_L("جم بروتين", "g protein")}</span></div>')

    html_string = f"""<!DOCTYPE html><html lang="{_L("ar", "en")}"><head><meta charset="utf-8">
<style>
@page {{ size: A4 {orientation}; margin: 9mm 10mm; }}
* {{ box-sizing: border-box; }}
/* ‏الورقة دي بتتسلّم لعميل. الشاشة تحتمل ألوان وإيموجي، الورقة لأ:
   شريط أخضر غامق + شبكة خطوط غامقة + ١١٢ إيموجي كانت بتخلي الأكل نفسه
   آخر حاجة العين تشوفها. بقى لون واحد للنص، خطوط شعر رمادية، ومساحة
   تفصل بدل ما الخطوط تفصل. */
body {{ font-family: 'Cairo','Amiri','DejaVu Sans',sans-serif;
        direction: {_L('rtl', 'ltr')}; color:#22292b; margin:0;
        font-size:10px; line-height:1.5; }}
.hdr {{ display:flex; justify-content:space-between; align-items:baseline;
        border-bottom:1px solid #d6dbd9; padding-bottom:6px; margin-bottom:9px; }}
.hdr .t {{ font-size:15px; font-weight:700; color:#22292b; letter-spacing:-0.2px; }}
.hdr .s {{ font-size:9.5px; color:#8a9391; font-weight:400; }}
/* ‏flex gap مش مضمون في WeasyPrint -- الخانات كانت بتطلع ملزوقة في بعضها
   ("الاسم: ريمالنوع: انثى"). span عادي بمسافة وفاصل بيتقرا في الحالتين. */
.meta {{ font-size:9px; color:#5c6663; margin-bottom:9px; line-height:1.8; }}
.meta span {{ margin-inline-end:7px; }}
.meta span::after {{ content:"·"; color:#c9d0cd; margin-inline-start:7px; }}
.meta span:last-child::after {{ content:""; }}
.meta b {{ color:#22292b; font-weight:600; }}
table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
th,td {{ padding:4px 7px; font-size:8.8px; vertical-align:top;
         word-wrap:break-word; line-height:1.5; text-align:start;
         border:0; border-bottom:1px solid #e8ecea; }}
th {{ background:transparent; color:#8a9391; font-weight:600; font-size:8.5px;
      letter-spacing:0.3px; border-bottom:1px solid #c9d0cd;
      padding-bottom:5px; }}
td .it {{ display:block; padding:1px 0; }}
td b {{ color:#22292b; font-weight:600; }}
td.dcell {{ font-weight:700; color:#22292b; font-size:10px; text-align:center;
            background:transparent; }}
.dcol {{ width:58px; }}
.kcol,.kcell {{ width:56px; text-align:center; }}
.kcol {{ white-space:nowrap; }}
.kcell {{ font-weight:600; color:#5c6663; }}
tr:nth-child(even) td {{ background:#fbfcfb; }}
.foot {{ display:flex; gap:16px; margin-top:9px; font-size:8.5px;
         page-break-inside:avoid; }}
.fbox {{ flex:1; border:0; border-top:1px solid #d6dbd9; padding:6px 0 0; }}
.fbox h4 {{ margin:0 0 4px; font-size:9px; color:#8a9391; font-weight:600;
            letter-spacing:0.3px; }}
.fbox ul {{ margin:0; padding-inline-start:13px; color:#3f4744; }}
.fbox li {{ margin-bottom:2px; }}
.notes {{ margin-top:9px; border:0; border-top:1px solid #d6dbd9;
          background:transparent; padding:6px 0 0; font-size:8.5px; }}
.notes h4 {{ margin:0 0 4px; font-size:9px; color:#8a9391; font-weight:600; }}
.notes ul {{ margin:0; padding-inline-start:13px; color:#3f4744; }}
.notes li {{ margin-bottom:2px; }}
/* ‏سطر المراجعة كان بيزحّف لصفحة تانية لوحده -- صفحة كاملة لسطر. */
.sig {{ margin-top:7px; text-align:end; font-size:8.5px; color:#a3aaa8;
        page-break-before:avoid; }}
.summary {{ display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;
            background:transparent; border:0; border-top:1px solid #c9d0cd;
            padding:7px 0 0; margin-top:2px; font-size:9.5px; color:#5c6663; }}
.summary b {{ color:#22292b; font-weight:600; }}
.fu-note {{ font-size:9px; color:#5c6663; margin:0 0 10px; }}
.pnote {{ font-size:9px; color:#7c2d12; background:#fff7ed;
          border:0.5pt solid #ea580c; border-radius:3px;
          padding:4px 6px; margin:4px 0 0; }}
{_company_css}
</style></head><body>
<div class="hdr">
  <div><div class="t">{_esc(td['plan_title'])} — {_esc(td['diet_plan_name'])}</div>
  {_by_line}</div>
  <div class="s">{_file_line}{_esc(td['date'])}</div>
</div>
<div class="meta">
  {f'<span><b>{_L("الاسم", "Name")}:</b> {_esc(cl["name"])}</span>' if cl.get('name') else ''}
  <span><b>{_L("النوع", "Sex")}:</b> {_esc(_GENDER_EN.get(cl['gender'], cl['gender']) if not _pdf_ar else cl['gender'])}</span>
  <span><b>{_L("العمر", "Age")}:</b> {_esc(cl['age'])}</span>
  <span><b>{_L("الوزن", "Weight")}:</b> {_esc(cl['weight'])} {_L("كجم", "kg")}</span>
  <span><b>{_L("الطول", "Height")}:</b> {_esc(cl['height'])} {_L("سم", "cm")}</span>
  <span><b>BMI:</b> {_esc(cl['bmi'])}</span>
  <span><b>{_L("السعرات المستهدفة", "Target calories")}:</b> {_esc(cl['target_kcal'])} kcal{_zz_meta}</span>
  <span><b>{_L("المطبخ", "Cuisine")}:</b> {_esc(td['culture'])}</span>
  {macro_meta}
</div>
{_fu_line}
<table><thead><tr>{head_cells}</tr></thead><tbody>{body_rows}</tbody></table>
{summary_box}
<div class="foot">
  <div class="fbox ok"><h4>{_L("مسموح", "Allowed")}</h4><ul>{allowed_html}</ul></div>
  <div class="fbox no"><h4>{_L("ممنوع", "Avoid")}</h4><ul>{forbidden_html}</ul></div>
  <div class="fbox wt"><h4>{_L("الماء", "Water")}</h4><ul>{water_tips}</ul></div>
</div>
{notes_html}
<div class="sig">{_L("المراجعة بعد", "Review in")} {_esc(td['review_weeks'])} {_L("أسابيع", "weeks")}{_sig_by}</div>
</body></html>"""

    return html_string


def build_pdf(data, plan=None, clean=False):
    """‏نفس الصفحة، مطبوعة PDF."""
    from weasyprint import HTML
    return HTML(string=plan_html(data, plan, clean)).write_pdf()

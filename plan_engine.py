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

    pool = get_meal_pool(goal, culture)
    breakfasts = list(pool.get("breakfast", []))
    lunches = list(pool.get("lunch", []))
    dinners = list(pool.get("dinner", []))
    if len(breakfasts) < 7: breakfasts = list(WEIGHT_LOSS["مصري"]["breakfast"])
    if len(lunches) < 7: lunches = list(WEIGHT_LOSS["مصري"]["lunch"])
    if len(dinners) < 7: dinners = list(WEIGHT_LOSS["مصري"]["dinner"])
    breakfasts = filter_by_conditions(breakfasts, symptoms)
    lunches = filter_by_conditions(lunches, symptoms)
    dinners = filter_by_conditions(dinners, symptoms)

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
                breakfasts = filter_meals_by_exclusions(filter_by_conditions(kb, symptoms), user_exclusions) or kb
                lunches = filter_meals_by_exclusions(filter_by_conditions(kl, symptoms), user_exclusions) or kl
                dinners = filter_meals_by_exclusions(filter_by_conditions(kd, symptoms), user_exclusions) or kd
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

    # تفضيل البروتين العالي للأهداف اللي محتاجة بروتين أكتر
    _prefer_protein = (goal in ("muscle_gain", "bulking")) or is_cutting or (data.get("activity_level") == "athlete")
    if _prefer_protein:
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

    SNK_P = 8  # تقدير بروتين السناك الواحد
    plan = []
    for i in range(7):
        day_plan = {"day": days[i], "diet_type": diet_type,
                    "meal_labels": plan_info["meal_labels"], "meal_emojis": plan_info["meal_emojis"]}
        total_cal = 0
        total_p = 0
        if diet_type in ("standard", "keto", "low_carb"):
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["breakfast"] = b["meal"]
            day_plan["lunch"] = l["meal"]
            day_plan["dinner"] = d["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            total_cal = b.get("cal",300) + l.get("cal",400) + d.get("cal",300) + 150
            total_p = b.get("p",20) + l.get("p",30) + d.get("p",20) + SNK_P
        elif diet_type == "five_meals":
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["breakfast"] = b["meal"]
            day_plan["snack1"] = snacks[i % len(snacks)]
            day_plan["lunch"] = l["meal"]
            day_plan["snack2"] = snacks[(i+3) % len(snacks)]
            day_plan["dinner"] = d["meal"]
            total_cal = b.get("cal",300) + l.get("cal",400) + d.get("cal",300) + 300
            total_p = b.get("p",20) + l.get("p",30) + d.get("p",20) + SNK_P*2
        elif diet_type == "intermittent_16_8":
            b = breakfasts[i % len(breakfasts)]
            d = dinners[i % len(dinners)]
            day_plan["meal1"] = b["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            day_plan["meal2"] = d["meal"]
            total_cal = b.get("cal",350) + d.get("cal",450) + 150
            total_p = b.get("p",25) + d.get("p",30) + SNK_P
        elif diet_type == "intermittent_18_6":
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["meal1"] = l["meal"]
            day_plan["meal2"] = d["meal"]
            total_cal = l.get("cal",400) + d.get("cal",400)
            total_p = l.get("p",30) + d.get("p",30)
        elif diet_type == "ramadan":
            l = lunches[i % len(lunches)]
            b = breakfasts[i % len(breakfasts)]
            day_plan["iftar"] = l["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            day_plan["suhoor"] = b["meal"]
            total_cal = l.get("cal",400) + b.get("cal",300) + 150
            total_p = l.get("p",30) + b.get("p",20) + SNK_P
        elif diet_type == "workout":
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["pre_workout"] = "موزة + زبدة فول سوداني + قهوة"
            day_plan["breakfast"] = b["meal"]
            day_plan["post_workout"] = "بروتين شيك + موز + لوز"
            day_plan["lunch"] = l["meal"]
            day_plan["dinner"] = d["meal"]
            total_cal = 200 + b.get("cal",300) + 250 + l.get("cal",400) + d.get("cal",300)
            total_p = b.get("p",20) + l.get("p",30) + d.get("p",20) + 33
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
        allowed = ["نزول وزن تدريجي","ألياف + خضار + بروتين قليل الدهن","أوميجا 3","قهوة بدون سكر باعتدال"] + allowed
    if has_chol:
        forbidden = ["الدهون المشبعة والمتحولة","المقليات + السمن + المعجنات","صفار البيض بكثرة"] + forbidden
        allowed = ["ألياف ذائبة: شوفان + بقوليات","أوميجا 3: سمك دهني","زيت زيتون + مكسرات + أفوكادو"] + allowed
    if has_uc:
        forbidden = ["الألياف الخشنة وقت النوبة","البهارات الحارة + الدهون العالية","الألبان لو فيه حساسية","الكحول والكافيين"] + forbidden
        allowed = ["أكل سهل الهضم وقت النوبة","بروتين قليل الدهن + أوميجا 3","سوائل كافية","بروبيوتيك حسب التحمّل"] + allowed
    if has_t1d:
        forbidden = ["السكريات السريعة المنفردة","العصائر والمشروبات الغازية"] + forbidden
        allowed = ["حساب الكارب لكل وجبة (carb counting)","توزيع الكارب مع جرعة الأنسولين","كارب معقّد + ألياف","سناك لتجنب هبوط السكر"] + allowed

    return allowed[:8], forbidden[:8]

def build_pdf(data, plan=None):
    from weasyprint import HTML
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
            _n = " | ".join(translate_boost_note(part.strip())
                            for part in _n.split("|"))
        notes_parts.append(_n)
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
        'client': {'name': data.get('name','-'), 'age': data.get('age','-'),
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

    def _fmt_cell(text):
        if not text:
            return "-"
        parts = [p.strip() for p in str(text).split(" + ") if p.strip()]
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
    # أعمدة الوجبات (من أول يوم - تنفع لأي نظام)
    columns = [m['label'] for m in pdays[0]['meals']] if pdays else []
    ncols = len(columns)
    orientation = "landscape" if ncols >= 5 else "portrait"
    if (data.get("zigzag") or None) and ncols >= 4:
        orientation = "landscape"  # عمود "هدف اليوم" الزيادة محتاج عرض

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
        _zz_meta = (f" — {_L('تدوير', 'cycled')} "
                    f"{_esc(_zz['mode_ar'] if _pdf_ar else _zz['mode_en'])} "
                    f"({_zz['low']}–{_zz['high']} kcal)")
    else:
        _zz_meta = ""

    def _g(x):
        return x if _pdf_ar else translate_guidance(x)

    allowed_html = "".join(f"<li>{_esc(_g(x))}</li>" for x in td['allowed'][:6])
    forbidden_html = "".join(f"<li>{_esc(_g(x))}</li>" for x in td['forbidden'][:6])
    water_tips = "".join(f"<li>{_esc(x)}</li>" for x in td['tips']['water'][:3])

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
        _pg = round(_w * _ppk)
        _fg = round(_kcal * _fatp / 100 / 9)
        _cc = _kcal - (_pg * 4) - (_fg * 9)
        _cg = round(max(_cc, 0) / 4)
        macro_meta = (
            f'<span><b>{_L("مستوى النشاط", "Activity level")}:</b> {_esc(_act_label)}</span>'
            f'<span><b>{_L("بروتين", "Protein")}:</b> {_esc(_pg)} {_L("جم", "g")} ({_ppk} {_L("جم/كجم", "g/kg")})</span>'
            f'<span><b>{_L("دهون", "Fat")}:</b> {_esc(_fg)} {_L("جم", "g")} ({int(_fatp)}%)</span>'
            f'<span><b>{_L("كارب", "Carbs")}:</b> {_esc(_cg)} {_L("جم", "g")}</span>'
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
    _tp = round(_w * _ppk) if _w > 0 else None
    summary_box = (f'<div class="summary"><span>📊 <b>{_L("المتوسط الفعلي/يوم", "Actual average per day")}:</b> '
                   f'{_avg_cal} {_L("سعرة", "kcal")} • {_avg_p} {_L("جم بروتين", "g protein")}</span>'
                   f'<span><b>{_L("الهدف", "Target")}:</b> {_tcal if _tcal else "-"} {_L("سعرة", "kcal")} • '
                   f'{_tp if _tp else "-"} {_L("جم بروتين", "g protein")}</span></div>')

    html_string = f"""<!DOCTYPE html><html lang="{_L("ar", "en")}"><head><meta charset="utf-8">
<style>
@page {{ size: A4 {orientation}; margin: 8mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: 'Cairo','Amiri','DejaVu Sans',sans-serif; direction: {_L('rtl', 'ltr')}; color:#1b2d24; margin:0; }}
.hdr {{ display:flex; justify-content:space-between; align-items:center;
        border-bottom:3px solid #14332b; padding-bottom:6px; margin-bottom:8px; }}
.hdr .t {{ font-size:18px; font-weight:800; color:#14332b; }}
.hdr .s {{ font-size:11px; color:#52796f; }}
.meta {{ display:flex; flex-wrap:wrap; gap:6px 16px; font-size:11px;
         background:#f0f7f4; border:1px solid #cfe3d9; border-radius:6px;
         padding:7px 10px; margin-bottom:8px; }}
.meta b {{ color:#14332b; }}
table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
th,td {{ border:1px solid #2d5a44; padding:6px 6px; font-size:9.5px;
         vertical-align:top; word-wrap:break-word; line-height:1.5; text-align:start; }}
td .it {{ display:block; padding:2px 0; border-bottom:1px dashed #dcebe4; }}
td .it:last-child {{ border-bottom:none; }}
td b {{ color:#14332b; font-weight:700; }}
th {{ background:#14332b; color:#fff; font-weight:700; }}
td.dcell {{ background:#e8f3ee; font-weight:800; color:#14332b; font-size:11px; text-align:center; }}
.dcol {{ width:62px; }} .kcol,.kcell {{ width:48px; text-align:center; }}
.kcell {{ font-weight:700; color:#2d5a44; }}
tr:nth-child(even) td {{ background:#fafdfb; }}
tr:nth-child(even) td.dcell {{ background:#e8f3ee; }}
.foot {{ display:flex; gap:10px; margin-top:9px; font-size:9.5px; }}
.fbox {{ flex:1; border:1px solid #cfe3d9; border-radius:6px; padding:6px 9px; }}
.fbox h4 {{ margin:0 0 3px; font-size:11px; }}
.fbox ul {{ margin:0; padding-inline-start:15px; }}
.fbox li {{ margin-bottom:1px; }}
.ok h4 {{ color:#2d7d46; }} .no h4 {{ color:#c0392b; }} .wt h4 {{ color:#1d6fa5; }}
.sig {{ margin-top:8px; text-align:end; font-size:10px; color:#52796f; }}
.summary {{ display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;
            background:#eef4f1; border:1px solid #cfe3d9; border-radius:6px;
            padding:7px 12px; margin-top:8px; font-size:11px; }}
.summary b {{ color:#14332b; }}
.fu-note {{ font-size:10.5px; color:#2d4a3e; margin-top:3px; padding:0 3px; }}
</style></head><body>
<div class="hdr">
  <div><div class="t">{_esc(td['plan_title'])} — {_esc(td['diet_plan_name'])}</div>
  <div class="s">{_esc(td['clinic_name'])} • {_esc(td['author'])}</div></div>
  <div class="s">{_L("ملف", "File")}: {_esc(td['file_number'])}<br>{_esc(td['date'])}</div>
</div>
<div class="meta">
  <span><b>{_L("الاسم", "Name")}:</b> {_esc(cl['name'])}</span>
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
  <div class="fbox ok"><h4>✅ {_L("مسموح", "Allowed")}</h4><ul>{allowed_html}</ul></div>
  <div class="fbox no"><h4>🚫 {_L("ممنوع", "Avoid")}</h4><ul>{forbidden_html}</ul></div>
  <div class="fbox wt"><h4>💧 {_L("الماء", "Water")}</h4><ul>{water_tips}</ul></div>
</div>
<div class="sig">{_L("المراجعة بعد", "Review in")} {_esc(td['review_weeks'])} {_L("أسابيع", "weeks")} — {_esc(td['author'])}</div>
</body></html>"""

    pdf_bytes = HTML(string=html_string).write_pdf()
    return pdf_bytes

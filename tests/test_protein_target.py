# -*- coding: utf-8 -*-
"""‏بروتين الأكل لازم يوصل للرقم المكتوب على الورقة.

الدكتور سأل عن نقاط ضعف الموقع، وده كان أولها: الورقة بتطبع "بروتين
١٦٢ جم (١.٨ جم/كجم)" -- ده **وصفة** محسوبة من وزن العميل -- والأكل
اللي في الجدول بيدي حاجة تانية. قِسْتها على أربع حالات حقيقية قبل
الإصلاح:

    ذكر ٩٠ كجم،  هدف ١٦٢ جم  ->  الأسبوع ١٠٨-١٧٣   ناقص ٣٣٪
    أنثى ٨٢ كجم،  هدف ١٣١ جم  ->  الأسبوع  ٨٦-١٤٨   ناقص ٣٤٪
    أنثى ٩٥ كجم،  هدف ١٥٢ جم  ->  الأسبوع  ٧٨-١٤٤   ناقص ٤٩٪
    ذكر ٧٠ كجم عضل، هدف ١٤٠   ->  الأسبوع ٢١١-٢٥٧   زايد ٨٤٪

ويوم الـ٧٨ جم في عجز هو بالظبط اليوم اللي العميل بيفقد فيه عضل،
والورقة بتقول ١٥٢.

Run with:  python3 tests/test_protein_target.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_protein_test.db"

import app as A            # noqa: E402
import plan_engine         # noqa: E402
import protein_fix         # noqa: E402
import zigzag              # noqa: E402

_BASE = {"name": "", "culture": "مصري", "diet_plan_type": "standard",
         "fat_pct_cal": "30", "symptoms": [], "allergies": [],
         "goal_type": "weight_loss"}

CASES = [
    ("ذكر 90 تخسيس ريفيد",
     {"age": "30", "gender": "ذكر", "height": "175", "weight": "90",
      "tdee": "2400", "goal_cal": "1800", "protein_per_kg": "1.8",
      "zigzag_mode": "refeed"}),
    ("أنثى 82 تخسيس كلاسيكي",
     {"age": "34", "gender": "انثى", "height": "163", "weight": "82",
      "tdee": "1950", "goal_cal": "1450", "protein_per_kg": "1.6",
      "zigzag_mode": "classic"}),
    ("أنثى 95 تخسيس قوي",
     {"age": "45", "gender": "انثى", "height": "160", "weight": "95",
      "tdee": "2050", "goal_cal": "1500", "protein_per_kg": "1.6",
      "zigzag_mode": "strong"}),
]

# ‏المقياسين دول إكلينيكيين، مش نسب مئوية مخترعة:
#
#   ‏المتوسط الأسبوعي: البروتين بيتحسب على الأسبوع مش على اليوم، فده
#   الرقم اللي بيحكم على الخطة. المقيس بعد الإصلاح: ٣٪ و٦٪ و٨٪ في
#   ١٢ تشغيل (الوجبات بتتخلط عشوائي فالرقم بيتغير).
#
#   ‏أرضية اليوم الواحد بالجرام/كجم: ده اللي بيحمي الكتلة العضلية في
#   العجز. قبل الإصلاح أنثى ٩٥ كجم نزلت ٧٨ جم = ٠.٨٢ جم/كجم. بعده
#   أقل يوم في ١٢ تشغيل كان ١.٠٠ و١.١٧ و١.٢٩.
#   ‏والفحص **مش متماثل**، وده مقصود. النقص هو الخطر الإكلينيكي:
#   في العجز، اللي بيتفقد هو العضل. أما الزيادة فوق الهدف فمش ضرر
#   بنفس المعنى -- وبقت بتحصل بعد ما بروتين السمنة اتحسب على الكتلة
#   الخالية من الدهن: الهدف نزل، وأطباق القاعدة بتوصّل أعلى منه.
#   فالأرضية بتتحرس بـ١٢٪، والسقف بيتحرس بالحد الآمن المنشور
#   (DELIVERED_MAX_PER_KG في protein_need) مش بنفس النسبة.
WEEKLY_TOL = 0.12
DAY_FLOOR_PER_KG = 0.95


def _target_for(data):
    """‏الهدف من **نفس المصدر** اللي المحرّك بيقرا منه.

    ‏كان مكتوب هنا بالإيد: الوزن × الجرام/كجم. وده بقى غلط لما البروتين
    في السمنة اتحوّل للكتلة الخالية من الدهن (أو الوزن المعدّل): أنثى
    ٩٥ كجم / ١٦٠ سم هدفها ١١٥ مش ١٥٢، والاختبار كان بيقارن بالرقم
    القديم.

    ‏والدرس أقدم من كده: صيغتين لنفس الرقم في مكانين = واحدة فيهم هتبقى
    قديمة. فالاختبار بيسأل المصدر بدل ما يحسب.
    """
    import protein_need
    grams, _basis, _why, _used = protein_need.target_grams(
        data.get("weight"), data.get("height"), data.get("age"),
        data.get("protein_per_kg"), data.get("fat_pct"))
    return grams


def _week(extra):
    data = dict(_BASE)
    data.update(extra)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    target = _target_for(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
    return data, plan, target


def test_no_deficit_day_starves_the_client_of_protein():
    """‏أهم اختبار في الملف.

    ‏في عجز، اليوم الناقص بروتين هو اللي بتتفقد فيه الكتلة العضلية.
    قبل الإصلاح: أنثى ٩٥ كجم هدفها ١٥٢ جم كان عندها يوم **٧٨ جم** --
    يعني ٠.٨٢ جم/كجم، تحت أي حد بيحمي العضل في عجز. والورقة بتقول
    ١٥٢.

    ‏المقياس هنا بالجرام/كجم مش بالنسبة المئوية: النسبة بتتغير مع
    الهدف، والعضل مابيهمّوش الهدف -- بيهمه الجرام لكل كيلو وزن.
    """
    bad = []
    for name, extra in CASES:
        data, plan, target = _week(extra)
        weight = float(data["weight"])
        for day in plan:
            got = day.get("total_p", 0)
            per_kg = got / weight
            if per_kg < DAY_FLOOR_PER_KG:
                bad.append("%s / %s: %d جم = %.2f جم/كجم (الهدف %d)"
                           % (name, day["day"], got, per_kg, target))
    assert not bad, (
        "‏أيام بروتينها تحت %.2f جم/كجم:\n  " % DAY_FLOOR_PER_KG
        + "\n  ".join(bad))


def test_the_week_delivers_the_protein_it_promises():
    """‏البروتين بيتحسب على الأسبوع، فالمتوسط هو اللي بيحكم.

    ‏قبل الإصلاح المتوسط كان بعيد عن الهدف لأن الأيام المنخفضة بتسحبه
    لتحت. المقيس بعده: ٣٪ و٦٪ و٨٪.
    """
    import protein_need
    off = []
    for name, extra in CASES:
        data, plan, target = _week(extra)
        avg = sum(day.get("total_p", 0) for day in plan) / float(len(plan))
        if avg < target * (1 - WEEKLY_TOL):
            off.append("%s: المتوسط %.0f جم تحت هدف %d"
                       % (name, avg, target))
        ceiling = float(data["weight"]) * protein_need.DELIVERED_MAX_PER_KG
        if avg > ceiling:
            off.append("%s: المتوسط %.0f جم فوق الحد الآمن %.0f"
                       % (name, avg, ceiling))
    assert not off, "‏المتوسط الأسبوعي:\n  " + "\n  ".join(off)


def test_the_added_protein_is_safe_for_the_clients_conditions():
    """‏الزيادة أكل، فبتمشي على نفس فحص السلامة زي أي أكل تاني.

    ‏زيادة بروتين فيها تونة لمريض نقرس، أو دجاج لنباتي، بتبوّظ الورقة
    كلها -- والـ٤٥١ اختبار اللي حاميين الفلترة مابيشوفوش الزيادة دي
    لو مامرّتش من نفس الباب.
    """
    from meal_database import CONDITION_MAP, safe_for_all, unsafe_keys_for

    # ‏التلات مصادر لازم يعدّوا الـ٤٠ مفتاح، وإلا مافيش ضمان إن فيه
    # مصدر لأي تركيبة حالات
    all_keys = sorted(set(CONDITION_MAP.values()))
    clean = [s for s in protein_fix.SOURCES
             if safe_for_all(s["ar"], all_keys)]
    assert clean, "‏مافيش مصدر بروتين بيعدّي كل الحالات"

    # ‏وفي خطة حقيقية لعميل بكل الحالات، الزيادة لازم تبقى آمنة
    data = dict(_BASE, age="40", gender="ذكر", height="170", weight="95",
                tdee="2300", goal_cal="1700", protein_per_kg="1.8",
                zigzag_mode="classic", symptoms=list(CONDITION_MAP.keys()))
    data["zigzag"] = zigzag.zigzag_from_data(data)
    keys = unsafe_keys_for(data["symptoms"])
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
    for day in plan:
        tu = day.get("protein_topup")
        if not tu:
            continue
        assert safe_for_all(tu["source_ar"], keys), (
            "‏%s: زيادة بروتين (%s) بتتصادم مع حالة"
            % (day["day"], tu["source_ar"]))


def test_the_added_protein_respects_what_the_client_does_not_eat():
    """‏"لا يأكل: تونة" لازم تمنع الزيادة من التونة."""
    data = dict(_BASE, age="30", gender="ذكر", height="175", weight="90",
                tdee="2400", goal_cal="1700", protein_per_kg="1.8",
                zigzag_mode="classic", disliked_foods="تونة")
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
    for day in plan:
        tu = day.get("protein_topup")
        if tu:
            assert "تونة" not in tu["source_ar"], day["day"]


def test_the_top_up_pays_for_itself_in_calories():
    """‏الزيادة سعراتها بتخرج من مكان تاني، وإلا اليوم بيعدّي هدفه.

    ‏الحساب في protein_fix: الزيادة بتاخد من أقل خانة كثافة بروتين
    (وهي النشوية بالتعريف)، والصافي بيحسب اللي بيضيع من المقتطع.
    """
    for name, extra in CASES:
        data, plan, _target = _week(extra)
        for day in plan:
            if not day.get("protein_topup"):
                continue
            want = day.get("target_cal") or int(float(data["goal_cal"]))
            got = day.get("total_cal", 0)
            off = abs(got - want) / float(want)
            assert off <= 0.15, (
                "‏%s / %s: %d سعرة على هدف %d (%.0f%%) -- الزيادة مادفعتش"
                % (name, day["day"], got, want, off * 100))


def test_the_maths_behind_the_top_up():
    """‏الصافي = G × (1 - dS/dP). الزيادة بتخسر جزء منها في المقتطع."""
    source = {"ar": "بياض بيض", "en": "egg whites", "cal": 52, "p": 11}
    # ‏خانة نشوية: ٤٠٠ سعرة و١٥ جم بروتين -> كثافة ٠.٠٣٧٥
    grams, add_cal, net = protein_fix.grams_needed(20.0, source, 15.0 / 400.0)
    assert grams > 0 and net >= 19.0, (grams, add_cal, net)
    # ‏ولو المقتطع كثافته أعلى من المصدر، الزيادة بتضر -- فمابتحصلش
    grams2, _c2, net2 = protein_fix.grams_needed(20.0, source, 0.9)
    assert grams2 == 0 and net2 == 0.0, (grams2, net2)


def test_a_day_that_is_already_on_target_is_left_alone():
    """‏مابنلمسش يوم مظبوط. التغيير بلا سبب بيلخبط الورقة."""
    assert protein_fix.shortfall(160, 162) == 0.0
    assert protein_fix.shortfall(200, 162) == 0.0      # زايد
    assert protein_fix.shortfall(100, 162) > 0
    slots = {"lunch": (400, 15), "dinner": (300, 20)}
    assert protein_fix.plan_topup(160, 162, slots, lambda t: True) is None


def test_the_paper_says_when_the_food_misses_the_target():
    """‏الزيادة مش دايماً بتسد الفرق (حصة الزيادة لها حد، والنشوية
    اللي بنقطع منها لها حد). فالورقة لازم تقول الفرق بدل ما تطبع
    وصفة الأكل بيناقضها."""
    import re

    # ‏تضخيم: الأكل بيدي بروتين أعلى من الوصفة، ومينفعش نشيل أكل من
    # خطة تضخيم -- فالورقة بتقول الرقمين
    data = dict(_BASE, age="25", gender="ذكر", height="178", weight="70",
                tdee="2600", goal_cal="2900", protein_per_kg="2.0",
                zigzag_mode="off", goal_type="muscle_gain")
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
        html = plan_engine.plan_html(data, plan)
    # ‏التحذير بقى عند الأخصائي في المعاينة، مش على ورقة العميل.
    joined = " ".join(n["short"] for n in (data.get("sheet_notes") or []))
    assert joined, "‏الأكل بعيد عن الوصفة ومافيش ولا ملاحظة"
    assert "المستهدف" in joined, joined

    # ‏والعكس: ورقة متسقة مافيهاش تحذير -- وإلا التحذير بيبقى ضوضاء
    # والدكتور بيتعلّم يتجاهله.
    #
    # ‏الاختبار بيقيس **الاستنتاج** مش حالة معيّنة: جرّبت أثبّت حالة
    # "متسقة" مرتين والاتنين طلعوا مش متسقين (الأكل بيدي ١٦٤ جم على
    # هدف ١٠٥)، والاختبار بقى متقلقل. فبنمشي على كذا حالة، وكل ورقة
    # نحكم عليها بنفس الشرطين اللي الكود بيحكم بيهم: لو الورقة متسقة
    # فعلاً، لازم تكون ساكتة.
    seen_quiet = False
    for extra in ({"age": "30", "gender": "ذكر", "height": "178",
                   "weight": "75", "tdee": "2400", "goal_cal": "2400",
                   "protein_per_kg": "2.4", "zigzag_mode": "off",
                   "goal_type": "maintenance"},
                  {"age": "28", "gender": "ذكر", "height": "180",
                   "weight": "80", "tdee": "2500", "goal_cal": "2500",
                   "protein_per_kg": "2.2", "zigzag_mode": "off",
                   "goal_type": "maintenance"},
                  {"age": "35", "gender": "انثى", "height": "165",
                   "weight": "65", "tdee": "1900", "goal_cal": "1900",
                   "protein_per_kg": "2.2", "zigzag_mode": "off",
                   "goal_type": "maintenance"}):
        ok_data = dict(_BASE)
        ok_data.update(extra)
        ok_data["zigzag"] = zigzag.zigzag_from_data(ok_data)
        weight = float(ok_data["weight"])
        tgt = round(weight * float(ok_data["protein_per_kg"]))
        with A.app.test_request_context("/"):
            ok_plan = plan_engine.generate_weekly_plan(ok_data)
            ok_html = plan_engine.plan_html(ok_data, ok_plan)
        ps = [d.get("total_p") or 0 for d in ok_plan]
        avg = sum(ps) / float(len(ps))
        consistent = (abs(avg - tgt) / tgt <= 0.12
                      and all(p / weight >= 0.95 and p >= tgt * 0.75
                              for p in ps))
        if not consistent:
            continue
        seen_quiet = True
        # ‏التحذير اتنقل من الورقة للمعاينة (sheet_notes) لما الورقة
        # بقت جدول وممنوع/مسموح وبس. الضمانة زي ما هي -- مكانها بس
        # اللي اتغيّر، فالفحص بيدوّر هناك.
        warns = [n for n in (ok_data.get("sheet_notes") or [])
                 if n.get("kind") == "warn"]
        assert not warns, (
            "‏تحذير على ورقة متسقة: هدف %d، الأيام %s — %s"
            % (tgt, ps, [n["short"] for n in warns]))
    assert seen_quiet, "‏مالقيتش ولا ورقة متسقة أقيس عليها السكوت"


def test_a_day_a_quarter_short_of_its_protein_is_flagged():
    """‏هدف ١.٦ جم/كجم ناقص ٣٦٪ لسه فوق أرضية الـ٠.٩٥، فاليوم ده كان
    بيعدّي من غير تحذير -- والدكتور يسلّم ورقة فيها يوم ناقص ربع
    بروتينه وهو مش شايفه."""
    import re

    data = dict(_BASE, age="45", gender="انثى", height="160", weight="95",
                tdee="2050", goal_cal="1500", protein_per_kg="1.6",
                zigzag_mode="strong")
    data["zigzag"] = zigzag.zigzag_from_data(data)
    target = _target_for(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
        html = plan_engine.plan_html(data, plan)
    short = [d for d in plan if (d.get("total_p") or 0) < target * 0.75]
    if short:
        # ‏زي فوق: التحذير بقى في sheet_notes مش على الورقة المطبوعة.
        #
        # ‏الفحص ده جوّه if، فماكانش بيتنفّذ غير لما الخطة العشوائية
        # تطلّع يوم ناقص فعلاً -- وعشان كده فضل ساكت بعد ما الورقة
        # اتغيّرت، وبان في تشغيلة واحدة من كل كام تشغيلة.
        assert any(n.get("kind") == "warn"
                   for n in (data.get("sheet_notes") or [])), (
            "‏يوم ناقص ربع بروتينه (%s) والمعاينة ساكتة"
            % [d.get("total_p") for d in short])


def test_the_protein_line_does_not_claim_to_be_the_food():
    """‏سطر الماكروز وصفة، فلازم يقول إنه مستهدف."""
    data, plan, _target = _week(CASES[0][1])
    with A.app.test_request_context("/"):
        plan_engine.plan_html(data, plan)
    joined = " ".join(n["short"] for n in (data.get("sheet_notes") or []))
    assert "بروتين مستهدف" in joined, "‏السطر لسه بيقدّم الوصفة كأنها الأكل"


def test_the_added_protein_reads_in_english_too():
    """‏الزيادة بتتكتب في نص الوجبة، فلازم تترجم زي أي أكل."""
    from meal_i18n import untranslated_terms

    for source in protein_fix.SOURCES:
        line = protein_fix.line({"source": source, "grams": 150})
        missing = untranslated_terms(line)
        assert not missing, "‏%s: %s" % (source["ar"], missing)


# ── السمنة المفرطة: البروتين على إيه بيتحسب ─────────────────────────
#
# ‏الجرام/كجم على الوزن الفعلي بيدّي أرقام مالهاش معنى: عميل ١٥٠ كجم
# × ٢ جم = **٣٠٠ جم بروتين**. ده مش وصفة -- ده ١٢٠٠ سعرة من خطة ٢٠٠٠،
# والماكروز كلها بتتلخبط وراه. والسبب إن الدهن الزيادة مش نسيج بيطلب
# بروتين.

def test_a_very_heavy_client_does_not_get_an_absurd_protein_number():
    import protein_need as PN
    grams, basis, why, _ = PN.target_grams(150, 170, 40, 2.0, 45)
    assert why == "ffm", why
    assert 140 <= grams <= 190, grams
    assert abs(basis - 82.5) < 1, basis


def test_without_body_fat_it_uses_the_adjusted_weight_not_the_whole_one():
    import protein_need as PN
    grams, basis, why, _ = PN.target_grams(150, 170, 40, 2.0)
    assert why == "adjusted", why
    assert grams < 300, grams
    assert basis > 150 * 0.5, basis       # ‏مش بيقصّ أكتر من اللازم


def test_a_client_who_is_not_obese_is_untouched():
    """‏التغيير للسمنة بس. رياضي ٨٠ كجم بـ١٢٪ دهون مالوش علاقة."""
    import protein_need as PN
    grams, basis, why, _ = PN.target_grams(80, 178, 24, 2.0, 12)
    assert why is None, why
    assert grams == 160, grams
    assert basis == 80.0, basis


def test_a_growing_child_still_follows_the_growth_rules():
    """‏مسار الطفل ماتلمسش: التوصية والسقف والوزن المرجعي زي ما هم."""
    import protein_need as PN
    grams, _basis, why, used = PN.target_grams(52, 160, 16, 3.0, 24)
    assert used <= PN.CHILD_MAX_PER_KG, used
    assert why is None or "rate" in why or "reference" in why, why


def test_the_sheet_says_what_the_number_was_built_on():
    """‏مافيش رقم بيتغيّر في صمت."""
    import protein_need as PN
    ar = PN.note(40, 170, 150, 2.0, True, 45)
    assert ar and "الكتلة الخالية من الدهن" in ar, ar
    assert "82.5" in ar, ar
    en = PN.note(40, 170, 150, 2.0, False, 45)
    assert en and "fat-free mass" in en, en


def test_without_body_fat_the_note_asks_for_it():
    """‏الوزن المعدّل تقدير. لو نسبة الدهون اتسجّلت الحساب بيبقى أدق،
    فالسطر بيطلبها."""
    ar = __import__("protein_need").note(40, 170, 150, 2.0, True)
    assert ar and "الوزن المعدّل" in ar, ar
    assert "نسبة الدهون" in ar, ar


def test_the_injection_floor_beats_the_obesity_reduction():
    """‏الأرضية دي موجودة **عشان تحمي العضل**: على إبر GLP-1 من ٢٠ لـ٤٠٪
    من الوزن النازل عضل، والأكل نفسه قليل. تخفيض الهدف هنا بيلغي الغرض
    منها -- فالحساب بيفضل على الوزن الفعلي.
    """
    import protein_need as PN
    low, _b1, why1, _ = PN.target_grams(95, 160, 45, 1.5, 38)
    full, _b2, why2, _ = PN.target_grams(95, 160, 45, 1.5, 38,
                                         protect_lean=True)
    assert why1 == "ffm", why1
    assert why2 is None, why2
    assert full > low, (full, low)
    assert full == round(95 * 1.5), full


def test_the_plan_itself_uses_the_corrected_number():
    """‏الحساب مالوش قيمة لو الجدول متبني على غيره."""
    import zigzag
    data = {"name": "ع", "gender": "ذكر", "age": "40", "height": "170",
            "weight": "150", "fat_pct": "45", "culture": "مصري",
            "diet_plan_type": "standard", "goal_type": "weight_loss",
            "activity_level": "light", "tdee": "2600", "goal_cal": "2100",
            "protein_per_kg": "2.0", "fat_pct_cal": "30", "allergies": [],
            "symptoms": [], "zigzag_mode": "off"}
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data, seed="pb")
    assert data["protein_basis"]["grams"] < 250, data["protein_basis"]
    assert data["protein_basis"]["why"] == "ffm", data["protein_basis"]


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

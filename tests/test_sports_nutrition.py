# -*- coding: utf-8 -*-
"""‏أهداف الرياضي: الأرقام منقولة، والفروق مقصودة.

‏اللي كان موجود قبل كده مش تغذية رياضيين -- ده تغذية عادية برقم بروتين
أعلى: مافيش فرق بين يوم تمرين ويوم راحة، ومافيش نوع رياضة، وخانة قبل
التمرين سطر ثابت مكتوب في الكود.

‏المصادر:
  الكارب      ACSM / Academy of Nutrition and Dietetics / Dietitians
              of Canada، البيان المشترك ٢٠١٦
              ٣-٥ خفيف · ٥-٧ متوسط · ٦-١٠ تحمّل · ٨-١٢ متطرف
  البروتين    ISSN 2017: ١.٤-٢.٠ لمعظم اللي بيتمرنوا،
              و٢.٣-٣.١ لمدرَّبي المقاومة في عجز سعري
  النزال      ISSN 2025: الكارب مايقلّش عن ٣-٤، والبروتين ١.٢-٢.٢ في عجز

Run with:  python3 tests/test_sports_nutrition.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sports_nutrition as SN   # noqa: E402

W = 80.0   # ‏رياضي ٨٠ كجم، عشان الحساب يتقرا بالعين


# ── الأرقام زي المنشور ───────────────────────────────────────────────

def test_the_carb_tiers_match_the_published_table():
    """‏لو رقم اتغيّر هنا، يبقى اتغيّر عن المصدر."""
    assert SN.CARB_BY_LOAD["light"] == (3, 5)
    assert SN.CARB_BY_LOAD["moderate"] == (5, 7)
    assert SN.CARB_BY_LOAD["high"] == (6, 10)
    assert SN.CARB_BY_LOAD["very_high"] == (8, 12)


def test_the_protein_ranges_match_the_published_stand():
    assert SN.PROTEIN_RANGE == (1.4, 2.0)
    assert SN.PROTEIN_CUT_RESISTANCE == (2.3, 3.1)
    assert SN.PROTEIN_COMBAT_CUT == (1.2, 2.2)


def test_everything_is_a_range_never_a_single_number():
    """‏البيانات نفسها بتقول نطاق. رقم واحد بيدّعي دقة مش موجودة."""
    t = SN.targets(W, "endurance", "high")
    for key in ("carb_g", "protein_g", "carb_per_kg", "protein_per_kg"):
        assert isinstance(t[key], tuple) and len(t[key]) == 2, (key, t[key])
        assert t[key][0] < t[key][1], (key, t[key])


# ── نوع الرياضة بيفرق ───────────────────────────────────────────────

def test_a_lifter_and_a_runner_do_not_get_the_same_carbs():
    """‏دي الغلطة اللي كانت موجودة: جدول واحد للاتنين."""
    lifter = SN.targets(W, "strength", "high")
    runner = SN.targets(W, "endurance", "high")
    assert lifter["carb_g"] != runner["carb_g"], (lifter, runner)
    assert runner["carb_g"][1] > lifter["carb_g"][1], (
        "‏العدّاء المفروض كاربه أعلى: %s مقابل %s"
        % (runner["carb_g"], lifter["carb_g"]))


def test_a_strength_athlete_keeps_their_own_range_whatever_the_load():
    """‏لاعب حديد بيتمرن ساعتين مش محتاج كارب عدّاء بيجري ساعتين."""
    for load in SN.CARB_BY_LOAD:
        assert SN.carb_range("strength", load) == SN.STRENGTH_CARB, load


def test_every_sport_in_the_list_produces_a_target():
    for sport in SN.SPORTS:
        t = SN.targets(W, sport, "moderate")
        assert t and t["carb_g"][0] > 0 and t["protein_g"][0] > 0, sport


# ── يوم تمرين مقابل يوم راحة ────────────────────────────────────────

def test_a_rest_day_carries_less_carbohydrate():
    """‏الكارب وقود التمرين. يوم الراحة مافيهوش تمرين يستهلكه."""
    train = SN.targets(W, "endurance", "high", training_day=True)
    rest = SN.targets(W, "endurance", "high", training_day=False)
    assert rest["carb_g"][1] < train["carb_g"][1], (train, rest)


def test_a_rest_day_is_not_a_fasting_day():
    """‏الجليكوجين بيتعوّض في الراحة -- دي نص شغل يوم الراحة."""
    train = SN.targets(W, "endurance", "high", training_day=True)
    rest = SN.targets(W, "endurance", "high", training_day=False)
    assert rest["carb_g"][0] >= train["carb_g"][0] * 0.5, (train, rest)


def test_protein_does_not_drop_on_a_rest_day():
    """‏بناء العضل بيحصل في الراحة مش في التمرين. تقليل البروتين يوم
    الراحة بيضرب اللي التمرين عمله."""
    train = SN.targets(W, "strength", "moderate", training_day=True)
    rest = SN.targets(W, "strength", "moderate", training_day=False)
    assert rest["protein_g"] == train["protein_g"], (train, rest)


# ── العجز السعري ────────────────────────────────────────────────────

def test_protein_rises_in_a_deficit_not_falls():
    """‏ده اللي البيان بيقوله: في العجز البروتين بيرتفع للحفاظ على العضل."""
    normal = SN.targets(W, "strength", "moderate", in_deficit=False)
    cutting = SN.targets(W, "strength", "moderate", in_deficit=True)
    assert cutting["protein_g"][0] > normal["protein_g"][1], (normal, cutting)


def test_the_cut_protein_goes_above_the_general_app_ceiling_on_purpose():
    """‏سقف البرنامج العام ٣.٠ جم/كجم (protein_need)، والبيان بيقول ٣.١
    لمدرَّب المقاومة في عجز. الزيادة دي **استثناء موثّق** مش كسر للسقف:
    لازم تفضل مربوطة بالحالة دي بالاسم، عشان ماتتسربش لباقي الناس.
    """
    import protein_need
    assert SN.PROTEIN_CUT_RESISTANCE[1] > protein_need.DELIVERED_MAX_PER_KG
    # ‏وماتنطبقش على غير الحالة دي
    assert SN.protein_range("endurance", in_deficit=True)[1] <= \
        protein_need.DELIVERED_MAX_PER_KG
    assert SN.protein_range("strength", in_deficit=False)[1] <= \
        protein_need.DELIVERED_MAX_PER_KG


def test_a_fighter_cutting_weight_still_gets_a_carb_floor():
    """‏أكتر سياق بيحصل فيه تجويع فعلي. البيان حاطط أرضية."""
    t = SN.targets(60, "combat", "moderate", in_deficit=True,
                   training_day=False)
    per_kg = t["carb_g"][0] / 60.0
    assert per_kg >= SN.COMBAT_CARB_FLOOR - 0.05, (t, per_kg)


# ── الأسبوع ─────────────────────────────────────────────────────────

def test_the_week_has_the_training_days_asked_for():
    for n in range(8):
        wk = SN.week(W, "mixed", "moderate", training_days=n)
        assert wk["training_days"] == n, (n, wk["training_days"])


def test_rest_days_are_spread_not_stacked_at_the_end():
    """‏تلات أيام راحة ورا بعض مش برنامج."""
    wk = SN.week(W, "mixed", "moderate", training_days=4)
    flags = [d["training_day"] for d in wk["days"]]
    runs, cur = [], 0
    for f in flags:
        cur = cur + 1 if not f else 0
        runs.append(cur)
    assert max(runs) <= 2, "‏أيام راحة متراصة: %s" % flags


def test_the_week_average_stays_inside_the_published_range():
    """‏الأيام بتختلف، بس متوسط الأسبوع لازم يفضل في النطاق -- وإلا
    يبقى التنويع بياخدنا بره التوصية."""
    wk = SN.week(W, "endurance", "high", training_days=5)
    lo, hi = SN.CARB_BY_LOAD["high"]
    avg_lo, avg_hi = wk["avg_carb_g"]
    assert avg_lo >= lo * W * 0.75, (avg_lo, lo * W)
    assert avg_hi <= hi * W, (avg_hi, hi * W)


# ── الحدود ──────────────────────────────────────────────────────────

def test_no_weight_means_no_invented_numbers():
    for bad in (0, -5, None, "", "abc"):
        assert SN.targets(bad) is None, bad


def test_an_unknown_load_falls_back_to_moderate_not_to_zero():
    assert SN.carb_range("endurance", "nonsense") == SN.CARB_BY_LOAD["moderate"]
    assert SN.carb_range("endurance", None) == SN.CARB_BY_LOAD["moderate"]


def test_the_labels_cover_every_key():
    """‏مفتاح من غير اسم معناه خانة فاضية في الواجهة."""
    assert set(SN.LOAD_LABELS) == set(SN.CARB_BY_LOAD)
    for ar, en in list(SN.LOAD_LABELS.values()) + list(SN.SPORTS.values()):
        assert ar and en and ar != en, (ar, en)


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
            print(f"  FAIL  {name}\n        {str(e)[:300]}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

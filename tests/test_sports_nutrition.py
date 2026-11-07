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


# ── توفّر الطاقة ومخاطر REDs ────────────────────────────────────────
#
# ‏بيان اللجنة الأولمبية ٢٠٢٣. وأهم حاجة فيه إن الحد **متنازع عليه
# والبيان نفسه بيقول كده**: ربط الـ٣٠ بالنتايج في الستات محل جدل، وحد
# الرجالة أقل (~٩-٢٥). فاللي بيتطبع لازم يبقى مؤشر بيفتح سؤال مش
# تشخيص بيتقفل بيه كلام.

def test_the_fat_free_mass_is_never_guessed():
    """‏المعادلة كلها بتتقسم على الرقم ده. لو اتخمّن، النتيجة بتبان
    دقيقة وهي مبنية على فرضية -- وبعدها بيتقال للرياضي "عندك نقص
    طاقة" على أساسها."""
    assert SN.fat_free_mass(80, None) is None
    assert SN.fat_free_mass(80, 0) is None
    assert SN.fat_free_mass(80, "") is None
    assert SN.fat_free_mass(80, 95) is None, "‏نسبة دهون ٩٥٪ عدّت"
    assert SN.fat_free_mass(80, 15) == 68.0


def test_energy_availability_needs_every_input_and_says_no_otherwise():
    assert SN.energy_availability(2500, 80, None) is None
    assert SN.energy_availability(0, 80, 15) is None
    assert SN.energy_availability(2500, 0, 15) is None
    assert SN.energy_availability(2500, 80, 15, hours_per_day=0) is None


def test_an_underfuelled_athlete_is_flagged():
    """‏عدّاء ٦٠ كجم، دهون ١٠٪، بيجري ساعتين، وبياكل ٢٠٠٠ سعرة."""
    r = SN.energy_availability(2000, 60, 10, "endurance", 2.0, "انثى")
    assert r, "‏مارجّعش حاجة"
    assert r["level"] == "low", r
    note = SN.ea_note(r)
    assert note and "مؤشر مش تشخيص" in note, note


def test_a_well_fuelled_athlete_is_not_flagged():
    r = SN.energy_availability(3800, 60, 10, "endurance", 2.0, "انثى")
    assert r["level"] == "ok", r
    assert SN.ea_note(r) is None, "‏حذّر من غير سبب"


def test_the_verdict_uses_the_whole_range_not_its_middle():
    """‏شدّة التمرين مش معروفة، فالناتج نطاق. الحكم على النطاق كله:
    لو طرفه الأعلى لسه تحت الحد يبقى خطر واضح، ولو على الحدين يبقى
    محتمل ومحتاج قياس أدق."""
    r = SN.energy_availability(2600, 60, 10, "endurance", 2.0, "انثى")
    assert r["level"] == "borderline", r
    note = SN.ea_note(r)
    assert "شدّة التمرين مش معروفة" in note, note


def test_the_men_threshold_is_lower_because_the_statement_says_so():
    """‏البيان بيقول حد الرجالة أقل (~٩-٢٥)، فنفس الأرقام ممكن تبقى
    خطر لست ومش خطر لراجل."""
    assert SN.LEA_MALE_WATCH < SN.LEA_RISK
    kw = dict(weight=70, fat_pct=12, sport="endurance", hours_per_day=1.5)
    woman = SN.energy_availability(2300, gender="انثى", **kw)
    man = SN.energy_availability(2300, gender="ذكر", **kw)
    assert woman["threshold"] == SN.LEA_RISK
    assert man["threshold"] == SN.LEA_MALE_WATCH
    assert woman["ea"] == man["ea"], "‏الحساب نفسه المفروض واحد"


def test_the_note_never_reads_as_a_diagnosis():
    """‏RED-S متلازمة إكلينيكية مش نتيجة تحليل. والرقم ده مؤشر خطر بس."""
    r = SN.energy_availability(1800, 60, 10, "endurance", 2.0, "انثى")
    for lang_ar in (True, False):
        note = SN.ea_note(r, is_ar=lang_ar)
        low = note.lower()
        for banned in ("تشخيص مؤكد", "مصاب", "diagnosed", "has reds",
                       "confirmed"):
            assert banned not in low, (banned, note)
    assert "مؤشر" in SN.ea_note(r, True)
    assert "indicator" in SN.ea_note(r, False).lower()


def test_the_optimal_45_figure_is_not_in_the_code():
    """‏الرقم ده بيتكرر في الحاسبات على النت، ومش مكتوب في البيان نفسه
    فيما قرأنا. فمالوش مكان في كود بيطلّع أرقام لورقة رياضي."""
    import inspect
    src = inspect.getsource(SN)
    assert "= 45" not in src and "45  #" not in src, (
        "‏رقم الـ٤٥ دخل الكود من غير مصدر")


def test_the_exercise_estimate_is_a_range_per_sport():
    """‏جري هادي ٨ وجري سريع ١١ -- والفرق بيغيّر توفّر الطاقة كله."""
    for sport in SN.MET_BY_SPORT:
        ex = SN.exercise_kcal(70, sport, 1.0)
        assert ex[0] < ex[1], (sport, ex)
    assert set(SN.MET_BY_SPORT) == set(SN.SPORTS), (
        set(SN.MET_BY_SPORT) ^ set(SN.SPORTS))


# ── الوصلة ──────────────────────────────────────────────────────────
#
# ‏الملف ده عاش فترة بـ٢٧ اختبار وهو **مش متوصّل بحاجة**: محدش بيستورده،
# فمفيش سطر منه بيوصل لورقة ولا لمعاينة. والاختبارات كلها كانت بتعدّي،
# لأنها بتختبر الحساب مش وصوله.
#
# ‏واللي كشفها مراجعة خارجية للمشروع: قرت الملف وكتبت "حسابات REDs
# وACSM وISSN" في **نقاط القوة**. ميزة موجودة في الريبو ومش موجودة في
# المنتج.
#
# ‏فالاختبارات دي بتختبر **الوصلة** مش الحساب.

def _app():
    os.environ.setdefault("SECRET_KEY", "test-only")
    os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
    os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_sports_test.db")
    import app as A
    return A


def _notes(**over):
    """‏ملاحظات المعاينة لخطة كاملة."""
    import plan_engine
    import zigzag
    A = _app()
    data = {"name": "ع", "gender": "ذكر", "age": "24", "height": "178",
            "weight": "80", "fat_pct": "12", "culture": "مصري",
            "diet_plan_type": "five_meals", "goal_type": "muscle_gain",
            "activity_level": "high", "tdee": "3000", "goal_cal": "2600",
            "protein_per_kg": "1.8", "fat_pct_cal": "30",
            "allergies": [], "symptoms": [], "zigzag_mode": "off"}
    data.update(over)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data, seed="sp")
        plan_engine.plan_html(data, plan)
    return [n["full"] or n["short"] for n in (data.get("sheet_notes") or [])]


def test_the_module_is_actually_imported_by_the_app():
    """‏الحارس الأساسي: ملف مالوش مستورد = كود ميت، والاختبارات بتعدّي
    عليه وهو مش بيشتغل."""
    import glob
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    users = []
    for path in glob.glob(os.path.join(here, "*.py")):
        if os.path.basename(path) == "sports_nutrition.py":
            continue
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        if "import sports_nutrition" in body:
            users.append(os.path.basename(path))
    assert users, "‏مفيش ملف في المشروع بيستورد sports_nutrition"


def test_an_athlete_gets_the_published_targets_in_the_preview():
    notes = " ".join(_notes(sport="endurance", training_load="high",
                            training_days="5", training_hours="2"))
    assert "تحمّل" in notes, notes[:200]
    assert "يوم التمرين" in notes, notes[:200]
    assert "جم/كجم" in notes, notes[:200]


def test_the_rest_day_is_in_the_same_note():
    """‏الفرق بين يوم التمرين ويوم الراحة هو نص فايدة الحساب."""
    notes = " ".join(_notes(sport="strength", training_load="moderate"))
    assert "يوم الراحة" in notes, notes[:200]


def test_the_weekly_average_follows_his_own_training_days():
    few = " ".join(_notes(sport="endurance", training_days="2"))
    many = " ".join(_notes(sport="endurance", training_days="6"))
    assert "2 أيام تمرين" in few, few[:200]
    assert "6 أيام تمرين" in many, many[:200]


def test_a_client_who_is_not_an_athlete_sees_none_of_it():
    """‏أغلب العملاء مش رياضيين، والورقة مالهاش تتلخبط بأرقام مالهاش
    لازمة."""
    notes = " ".join(_notes())
    assert "يوم التمرين" not in notes, notes[:200]
    assert "توفّر الطاقة" not in notes, notes[:200]


def test_the_energy_availability_marker_reaches_the_preview():
    """‏ده أهم رقم في الملف: الرياضي اللي بياكل أقل من حرقه مابيبانش
    في الميزان."""
    notes = " ".join(_notes(sport="endurance", training_load="high",
                            training_hours="3", goal_cal="2200"))
    assert "توفّر الطاقة" in notes, notes[:300]


def test_without_body_fat_it_says_nothing_instead_of_guessing():
    """‏الكتلة الخالية من الدهن محتاجة نسبة الدهون. من غيرها مفيش رقم."""
    notes = " ".join(_notes(sport="endurance", fat_pct="",
                            training_load="high", training_hours="3"))
    assert "توفّر الطاقة" not in notes, notes[:300]


def test_the_form_asks_for_what_the_calculation_needs():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "templates", "generate.html"),
              encoding="utf-8") as fh:
        page = fh.read()
    for field in ("sport", "training_load", "training_days", "training_hours"):
        assert 'name="%s"' % field in page, "‏خانة %s مش في الفورم" % field
    assert 'id="spFold"' in page, "‏الخانات مش مطوية -- بتكبّر الصفحة لكل عميل"


def test_cycling_without_a_sport_says_why_it_may_not_belong():
    """‏مبرّر التدوير استهلاك الجليكوجين في التمرين. العميل اللي مش
    رياضي مالوش الطلب ده، فالتدوير بيبقى تعقيد زيادة على خطة لسه
    بادئة -- والاختيار فضل مفتوح بطلب الدكتور، فالسطر عشان يقرّر وهو
    شايف."""
    notes = " ".join(_notes(zigzag_mode="classic"))
    assert "مش مسجّل كرياضي" in notes, notes[:300]


def test_an_athlete_cycling_is_not_second_guessed():
    notes = " ".join(_notes(zigzag_mode="classic", sport="strength",
                            training_days="4"))
    assert "مش مسجّل كرياضي" not in notes, notes[:300]


def test_no_cycling_no_note():
    notes = " ".join(_notes(zigzag_mode="off"))
    assert "مش مسجّل كرياضي" not in notes, notes[:300]


# ── الجدول نفسه بيتبع أيام تمرينه ───────────────────────────────────# ── الجدول نفسه بيتبع أيام تمرينه ───────────────────────────────────

def _zz(**over):
    import zigzag
    data = {"zigzag_mode": "training", "gender": "ذكر", "weight": "80",
            "goal_cal": "3200", "tdee": "3000", "protein_per_kg": "1.8",
            "fat_pct_cal": "30", "sport": "endurance",
            "training_load": "high", "training_days": "5"}
    data.update(over)
    return zigzag.zigzag_from_data(data)


def test_the_week_follows_his_training_days_not_fixed_ones():
    """‏نمط "حسب أيام التمرين" الجاهز شغّال على الأحد والثلاثاء والخميس
    -- تلات أيام ثابتة. والعميل اللي بيتمرن خمسة كان بياخد جدول مبني
    على تلاتة."""
    z = _zz(training_days="5")
    kcal = [d["kcal"] for d in z["days"]]
    high = [k for k in kcal if k > z["target"]]
    assert len(high) == 5, "‏%d يوم عالي، والمفروض ٥: %s" % (len(high), kcal)

    z2 = _zz(training_days="3")
    high2 = [d["kcal"] for d in z2["days"] if d["kcal"] > z2["target"]]
    assert len(high2) == 3, [d["kcal"] for d in z2["days"]]


def test_the_weekly_total_does_not_move():
    """‏التدوير بيوزّع، مابيزوّدش. اللي بيتزوّد في أيام التمرين هو اللي
    بيتشال من أيام الراحة."""
    z = _zz()
    assert abs(z["avg"] - z["target"]) <= 2, (z["avg"], z["target"])


def test_the_gap_is_the_carb_difference_not_a_made_up_number():
    """‏الفرق بين اليوم العالي والواطي = فرق الكارب × ٤، مش نسبة
    مخترعة."""
    import zigzag
    data = {"sport": "endurance", "training_load": "high",
            "training_days": "5", "weight": "80", "goal_cal": "3200",
            "tdee": "3000"}
    train = SN.targets(80, "endurance", "high", False, True)
    rest = SN.targets(80, "endurance", "high", False, False)
    delta = (sum(train["carb_g"]) / 2.0 - sum(rest["carb_g"]) / 2.0) * 4
    pat = zigzag.training_pattern(data)
    spread = (max(pat) - min(pat)) / 100.0 * 3200
    assert abs(spread - delta) < 15, "‏الفرق %d والكارب بيقول %d" % (spread, delta)


def test_training_every_day_or_none_means_no_cycling():
    """‏سبع أيام تمرين = مفيش يوم راحة يتشال منه."""
    import zigzag
    for n in ("0", "7"):
        assert zigzag.training_pattern(
            {"sport": "endurance", "training_days": n, "weight": "80",
             "goal_cal": "3200"}) is None, n


def test_a_client_who_is_not_an_athlete_keeps_the_old_pattern():
    """‏اللي مختار النمط ده من غير ما يسجّل رياضة لازم ياخد اللي كان
    بياخده -- التغيير إضافة مش استبدال."""
    import zigzag
    z = _zz(sport="")
    fixed = zigzag.ZIGZAG_MODES["training"]["pattern"]
    high = len([p for p in fixed if p > 0])
    got = len([d for d in z["days"] if d["kcal"] > z["target"]])
    assert got == high, (got, high)


def test_the_name_he_picked_is_the_name_he_sees():
    """‏النمط بيتبني كـcustom جوّه، والاسم كان بيطلع "مخصّص" -- فالدكتور
    بيدوّر على اللي اختاره ومايلاقيهوش."""
    z = _zz()
    assert z["mode"] == "training", z["mode"]
    assert "التمرين" in z["mode_ar"], z["mode_ar"]
    assert "5" in z["desc_ar"], z["desc_ar"]


def test_the_plan_days_really_carry_the_difference():
    """‏النمط مالوش قيمة لو الأكل نفسه مااتغيّرش."""
    plan_cals = []
    import plan_engine
    import zigzag
    A = _app()
    data = {"name": "ع", "gender": "ذكر", "age": "24", "height": "178",
            "weight": "80", "fat_pct": "12", "culture": "مصري",
            "diet_plan_type": "five_meals", "goal_type": "muscle_gain",
            "activity_level": "high", "tdee": "3000", "goal_cal": "3200",
            "protein_per_kg": "1.8", "fat_pct_cal": "30", "allergies": [],
            "symptoms": [], "zigzag_mode": "training", "sport": "endurance",
            "training_load": "high", "training_days": "5",
            "training_hours": "2"}
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data, seed="tr")
    plan_cals = [d["total_cal"] for d in plan]
    high = [c for c in plan_cals if c > 3200]
    assert len(high) == 5, plan_cals
    assert max(plan_cals) - min(plan_cals) > 400, plan_cals


def test_the_page_renders_without_the_route_handing_it_the_lists():
    """‏القوايم اتبعتت الأول من راوت /generate لوحده، فأول حد تاني عرض
    نفس القالب (اختبار في ملف تاني) وقع على UndefinedError جوه الـfor
    -- والملف كله وقف في نصه.

    ‏القالب مالوش يعتمد على اللي ناداه في حاجة ثابتة زي دي."""
    from flask import render_template
    from meal_database import DIET_PLAN_TYPES
    from zigzag import ZIGZAG_MODES
    A = _app()
    with A.app.test_request_context("/"):
        html = render_template("generate.html",
                               user={"name": "t", "role": "admin"}, lang="ar",
                               diet_plans=DIET_PLAN_TYPES,
                               zigzag_modes=ZIGZAG_MODES, prev={})
    assert 'name="sport"' in html
    assert 'value="endurance"' in html, "‏قايمة الرياضات طلعت فاضية"


def test_the_server_reads_those_fields():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "routes_plans.py"), encoding="utf-8") as fh:
        src = fh.read()
    for field in ("sport", "training_load", "training_days", "training_hours"):
        assert 'request.form.get("%s"' % field in src, (
            "‏السيرفر مش بيقرا %s -- الخانة بتتبعت وبتتضيع" % field)


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

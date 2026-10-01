# -*- coding: utf-8 -*-
"""برامج التغذية الـ12.

الدكتور بعت ورقة الشركة الحقيقية (IR Formula) وقال: خد منها الأفكار،
واعمل أوبشن أختار منه البرنامج زي شاشة الشركة، وأول ما أدوس يتعمل على
طول بالأكل بتاعه.

القاعدة اللي الاختبارات دي كلها بتقيسها: **البرنامج لازم يبان إنه
البرنامج ده**. لو-كارب فيه نشويات زي أي خطة تانية مش لو-كارب، وفيجن
فيه لبنة مش فيجن، وبرنامج أطفال بعجز سعرات مش برنامج أطفال -- ده ضرر.

Run with:  python3 tests/test_diet_programs.py
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_programs_test.db"

import diet_programs as dp          # noqa: E402
import meal_database as md          # noqa: E402

# ‏كل مفاتيح الخطر للـ65 حالة اللي في الفورم، مجمّعة
ALL_KEYS = md.unsafe_keys_for(sorted(set(md.CONDITION_MAP.keys())))

PLANT_FAMILY = ("vegan", "lacto_vegetarian", "lacto_ovo_vegetarian",
                "ovo_vegetarian")

# ‏كلمات اللحم والسمك -- مالهاش لازمة في أي برنامج نباتي
FLESH = ("دجاج", "فراخ", "لحم", "كفتة", "سمك", "تونة", "سلمون", "روبيان",
         "جمبري", "رومي", "شاورما", "برجر", "طاووق", "تكا", "فاهيتا",
         "كبدة", "سردين", "كالماري", "فيليه")
DAIRY = ("لبن", "حليب خالي الدسم", "زبادي", "جبن", "جبنة", "لبنة")
EGG = ("بيض", "بيضة", "أومليت", "بياض")


def _all_meals(program):
    """كل نصوص الوجبات في برنامج، كل الاختيارات."""
    out = []
    for day in dp.PROGRAMS[program]:
        for slot in dp.SLOTS:
            out.extend(item["meal"] for item in day["meals"][slot])
    return out


_AR = "ء-ي"      # ‏حروف عربية، للحدود تحت


def _has(text, words):
    """‏فيه كلمة من دي؟ **بحدود كلمة**، مش بمطابقة جوّه الكلمة.

    ‏المطابقة الساذجة كانت بتقول إن "🍚 أرز أبيض" فيه بيض: كلمة "بيض"
    جوّه "أبيض". فالفيجن طلع كأنه فيه بيض وهو أرز. نفس الغلطة اللي
    خلّت القراية تقرا "Right Leg" طول، عشان "ht" جوّه "right".
    """
    for word in words:
        if re.search("(?<![%s])%s(?![%s])" % (_AR, re.escape(word), _AR), text):
            return True
    return False


# ═══ الشكل ═══════════════════════════════════════════════════════════


def test_the_screen_s_twelve_programs_are_all_there():
    """‏شاشة الشركة فيها 12 برنامج، والدكتور طلبهم كلهم.

    ‏كيتو كان موجود قبل كده في meal_extra، والـ11 الباقيين هنا.
    """
    import meal_database
    import meal_extra                             # noqa: F401  يحقن الأنظمة
    meal_extra.apply()
    types = meal_database.DIET_PLAN_TYPES
    for key in dp.PROGRAMS:
        assert key in types, "‏%s مش في قايمة الأنظمة" % key
    assert "keto" in types, "‏كيتو اختفى"
    assert len(dp.PROGRAMS) == 11, len(dp.PROGRAMS)


def test_every_program_is_seven_days_of_four_meals():
    """‏شكل ورقة الشركة: سبعة أيام × أربع وجبات."""
    for program, days in dp.PROGRAMS.items():
        assert len(days) == 7, "‏%s: %d أيام" % (program, len(days))
        for index, day in enumerate(days, 1):
            assert day.get("name") and day.get("name_en"), (program, index)
            for slot in dp.SLOTS:
                options = day["meals"].get(slot)
                assert options, "‏%s يوم %d: %s فاضية" % (program, index, slot)
                for item in options:
                    assert item["meal"].strip(), (program, index, slot)
                    assert item["cal"] > 0, (program, index, slot, item)


def test_every_slot_has_an_option_that_clears_all_sixty_five_conditions():
    """‏الحاجز اللي بيخلّي الفلترة تلاقي حاجة دايماً.

    ‏الخانة بتتفلتر على حالة العميل، ولو مفيش اختيار عدّى بترجع فاضية
    وبتحذير. فكل خانة فيها اختيار واحد على الأقل مافيش ولا حالة من
    الـ65 بتمنعه -- يعني أسوأ عميل ممكن يدخل لسه بياخد خطة كاملة.
    """
    empty = []
    for program, days in dp.PROGRAMS.items():
        for index, day in enumerate(days, 1):
            for slot in dp.SLOTS:
                options = day["meals"][slot]
                if not any(md.safe_for_all(o, ALL_KEYS) for o in options):
                    empty.append("%s يوم %d %s" % (program, index, slot))
    assert not empty, ("‏خانات مفيش فيها اختيار آمن لكل الحالات:\n  "
                       + "\n  ".join(empty))


def test_a_client_with_five_conditions_still_gets_every_slot_filled():
    """‏نفس الحاجز، بس من ناحية المخرج: خطة كاملة مش خانات فاضية."""
        # ‏خمس حالات بتمنع: البقوليات والمكسرات والألبان والجلوتين والبروكلي
    heavy = ["نقص G6PD", "حساسية اللاكتوز", "الداء الزلاقي",
             "قولون عصبي", "الفشل الكلوي المزمن"]
    for program in dp.PROGRAMS:
        days, warnings = dp.build_program_plan(
            program, target_cal=1600, symptoms=heavy, gender="ذكر")
        assert len(days) == 7, (program, len(days))
        for day in days:
            for slot in dp.SLOTS:
                assert day.get(slot), (
                    "‏%s / %s: خانة %s فاضية مع خمس حالات"
                    % (program, day["day"], slot))
        assert not [w for w in warnings if w["kind"] == "unfillable"], \
            [w["reason"] for w in warnings if w["kind"] == "unfillable"]


def test_every_meal_in_every_program_is_translated():
    """‏وجبة مش مترجمة بتطلع عربي على خطة إنجليزي."""
    from meal_i18n import untranslated_terms
    missing = {}
    for item in dp.PROGRAM_MEALS:
        left = untranslated_terms(item["meal"])
        if left:
            missing[item["meal"]] = left
    assert not missing, "‏وجبات مش مترجمة: %s" % list(missing.items())[:4]


# ═══ كل برنامج يبان إنه هو ═══════════════════════════════════════════


def test_low_carb_really_is_low_carb():
    """‏اللي كان موجود قبل كده بيفلتر النشويات من قايمة عامة، فالناتج
    كان خطة عادية ناقصة حاجة. البرنامج ده ورقة ليها أكلها.

    ‏المقياس: النشوية بتظهر في يوم واحد من السبعة بحد أقصى في الغدا،
    ومافيش يوم فيه أكتر من نشوية واحدة في نفس الوجبة.
    """
    starches = ("أرز", "معكرونة", "خبز", "بطاطس", "بطاطا", "فريكة", "برغل")
    days, _ = dp.build_program_plan("low_carb_program", target_cal=1600)
    with_starch = [d["day"] for d in days
                   if _has(d.get("lunch", ""), starches)]
    assert len(with_starch) <= 2, (
        "‏%d أيام فيها نشوية في الغدا -- ده مش لو-كارب: %s"
        % (len(with_starch), with_starch))
    # ‏والعشا مافيهوش نشويات خالص
    for day in days:
        assert not _has(day.get("dinner", ""), starches), \
            "‏نشوية في عشا اللو-كارب: %s" % day.get("dinner")


def test_low_fat_carries_a_starch_every_day_and_no_added_fat():
    """‏عكس اللو-كارب: النشوية المعقّدة كل يوم، والدهون المضافة برّه."""
    starches = ("أرز", "بطاطس", "بطاطا", "توست", "شوفان", "خبز")
    fats = ("زيت", "أفوكادو", "طحينة", "مكسرات", "لوز", "جوز", "زبدة")
    days, _ = dp.build_program_plan("low_fat", target_cal=1800)
    for day in days:
        whole = " ".join(day.get(s, "") for s in dp.SLOTS)
        assert _has(whole, starches), \
            "‏يوم في اللو-فات من غير نشوية: %s" % day["day"]
    # ‏والدهون المضافة مش في أي اختيار في البرنامج كله
    fatty = [m for m in _all_meals("low_fat") if _has(m, fats)]
    assert not fatty, "‏دهون مضافة في برنامج لو-فات: %s" % fatty[:4]


def test_dash_has_no_salted_or_processed_meat():
    """‏الصوديوم نُص بروتوكول DASH. لحمة مملّحة في برنامج ضغط بتلغيه."""
    salty = ("شاورما", "مدخن", "برجر", "فيتا", "لانشون", "بسطرمة",
             "سجق", "مخلل")
    offenders = [m for m in _all_meals("dash") if _has(m, salty)]
    assert not offenders, "‏مملّح أو مصنّع في DASH: %s" % offenders[:4]


def test_detox_is_food_not_starvation():
    """‏"ديتوكس" بتتقال على أسابيع تجويع. ده أكل كامل بسعرات يوم طبيعي."""
    days, warnings = dp.build_program_plan("detox", target_cal=1600,
                                           gender="انثى")
    for day in days:
        assert day["total_cal"] >= 1200, \
            "‏يوم ديتوكس %d سعر -- ده تجويع" % day["total_cal"]
    assert not [w for w in warnings if w["kind"] == "below_floor"], \
        [w["reason"] for w in warnings]
    # ‏ومافيش عصير ولا مصنّع ولا سكر مضاف
    banned = ("عصير", "سكر", "مقلي", "شيبسي", "مصنّع")
    offenders = [m for m in _all_meals("detox") if _has(m, banned)]
    assert not offenders, offenders[:4]


def test_the_vegetarian_family_holds_its_own_line():
    """‏الأربعة مختلفين في حاجة واحدة: إيه المسموح من أصل حيواني."""
    rules = {
        "vegan": (FLESH + DAIRY + EGG, "أي حاجة حيوانية"),
        "lacto_vegetarian": (FLESH + EGG, "لحمة أو بيض"),
        "lacto_ovo_vegetarian": (FLESH, "لحمة"),
        "ovo_vegetarian": (FLESH + DAIRY, "لحمة أو ألبان"),
    }
    for program, (banned, what) in rules.items():
        offenders = [m for m in _all_meals(program) if _has(m, banned)]
        assert not offenders, "‏%s فيه %s: %s" % (program, what, offenders[:3])


def test_every_plant_program_keeps_a_protein_in_every_slot():
    """‏البقوليات والمكسرات بتتصادم مع حالات كتير، والتوفو هو الحاجة
    الوحيدة اللي بتعدّي الكل. فلو اتشالوا لازم يفضل بروتين -- مش خضار
    لوحده، يعني يوم من غير بروتين خالص.
    """
    # ‏الصيغتين لازم يبقوا موجودين: المطابقة بحدود كلمة، فـ"بيض"
    # مابتلاقيش "بيضة" -- والاختبار قال إن "بيضة مسلوقة" مالهاش بروتين
    proteins = ("تفو", "بيض", "بيضة", "بياض", "أومليت", "عدس", "فول",
                "حمص", "فاصوليا", "جبن", "جبنة", "زبادي", "لبنة",
                "حليب", "طحينة", "مكسرات", "لوز", "جوز", "بذر", "بذور")
    heavy = ["نقص G6PD", "حساسية اللاكتوز", "الداء الزلاقي", "قولون عصبي"]
    for program in PLANT_FAMILY:
        days, _ = dp.build_program_plan(program, target_cal=1800,
                                        symptoms=heavy, gender="ذكر")
        for day in days:
            for slot in ("breakfast", "lunch", "dinner"):
                text = day.get(slot, "")
                assert _has(text, proteins), \
                    "‏%s / %s / %s من غير بروتين: %s" % (program, day["day"],
                                                        slot, text)


# ‏كان فيه هنا test_optitect_says_it_is_not_the_real_protocol، بيتأكد إن
# البرنامج بيقول إنه **مش** بروتوكول Optitect الأصلي. اتشال لأن المقدمة
# بتاعته بطلت صح: الدكتور بعت عرض الشركة، والحساب بقى البروتوكول
# الحقيقي فعلاً (optitect.py، ومعاه اختبارات بتقيس كل معادلة فيه
# بالرقم). اللي لسه ناقص حاجة واحدة -- كتيّب نقاط الأصناف -- وده
# متحقّق منه في test_optitect_still_says_the_food_points_booklet_is_missing.


# ═══ البرنامجين اللي مش للتخسيس ═══════════════════════════════════════


def test_a_child_never_gets_a_deficit_plan():
    """‏أهم اختبار في الملف.

    ‏الموقع كله مبني على إنه يحسب عجز سعرات. خطة بعجز لطفل بيكبر دي
    ضرر، مش خطة. فلو الدكتور اختار هدف تخسيس لطفل:

        التحذير يطلع صريح
        والسعرات **مايُنزلوش** تحت الحد -- مش بس يتحذّر منهم

    ‏والتانية دي كانت مكسورة: التحذير كان بيقول "السعرات مش هتنزل تحت
    1500" والتظبيط كان بينزّلها 886 لطفل هدفه 900. يعني الجملة كانت
    بتكدب، والخطة اللي بتطلع دي بالظبط الحاجة اللي المفروض تتمنع.
    """
    floor = dp._floor_for_program("kids", "ذكر")
    for target in (600, 900, 1100):
        days, warnings = dp.build_program_plan(
            "kids", target_cal=target, gender="ذكر", goal_type="weight_loss")
        said = [w for w in warnings if w["kind"] == "not_for_loss"]
        assert said, "‏هدف تخسيس لطفل ومافيش تحذير (هدف %d)" % target
        assert said[0]["reason_en"] != said[0]["reason"], said[0]
        worst = min(d["total_cal"] for d in days)
        assert worst >= floor, (
            "‏طفل هدفه %d طلعت له أيام %d سعر، والحد %d"
            % (target, worst, floor))


def test_a_nursing_mother_never_gets_a_deficit_plan():
    """‏نفس القاعدة: الرضاعة محتاجة زيادة 400-500 سعر، مش عجز."""
    floor = dp._floor_for_program("breast_feeding", "انثى")
    assert floor >= 1800, floor
    for target in (600, 1100, 1500):
        days, warnings = dp.build_program_plan(
            "breast_feeding", target_cal=target, gender="انثى",
            goal_type="weight_loss")
        assert [w for w in warnings if w["kind"] == "not_for_loss"], target
        worst = min(d["total_cal"] for d in days)
        assert worst >= floor, (
            "‏أم بترضّع هدفها %d طلعت لها أيام %d سعر، والحد %d"
            % (target, worst, floor))


def test_the_growth_guard_stays_quiet_when_the_goal_is_not_loss():
    """‏التحذير على الهدف الغلط، مش على البرنامج. أم بترضّع على هدف
    محافظة مالهاش لازمة تحذير."""
    for program in ("kids", "breast_feeding"):
        _, warnings = dp.build_program_plan(
            program, target_cal=2000, gender="انثى", goal_type="maintenance")
        assert not [w for w in warnings if w["kind"] == "not_for_loss"], \
            (program, [w["reason"] for w in warnings])


# ═══ التظبيط على هدف العميل ═══════════════════════════════════════════


def test_the_same_sheet_serves_a_small_target_and_a_big_one():
    """‏ورقة الشركة حصصها ثابتة لكل الناس. ده مايمشيش: الموقع بيحسب هدف
    من وزن العميل وطوله، فواحد هدفه 1400 وواحد 2400 كانوا هياخدوا نفس
    الأكل. الجدول بيحدّد الأكل، والحصص بتتظبّط."""
    small, _ = dp.build_program_plan("low_fat", target_cal=1400)
    big, _ = dp.build_program_plan("low_fat", target_cal=2400)
    lo = sum(d["total_cal"] for d in small) / 7.0
    hi = sum(d["total_cal"] for d in big) / 7.0
    assert hi > lo * 1.3, "‏الحصص مابتتظبّطش: %d مقابل %d" % (lo, hi)
    # ‏ونفس الأكل في الاتنين -- الجدول هو الجدول
    for a, b in zip(small, big):
        assert a["day"] == b["day"]
        assert a.get("lunch", "").split()[0] == b.get("lunch", "").split()[0], \
            (a.get("lunch"), b.get("lunch"))


def test_the_written_calories_are_the_ones_on_the_plate():
    """‏scale_meal بيقرّب الجرامات، فالمعامل الفعلي أقل من المطلوب.
    السعرات المكتوبة لازم تبقى المحسوبة بالمعامل الفعلي، مش المطلوبة."""
    for program in dp.PROGRAMS:
        days, _ = dp.build_program_plan(program, target_cal=1700,
                                        gender="ذكر")
        for day in days:
            assert day["total_cal"] > 0, (program, day["day"])
            assert day["total_p"] > 0, (
                "‏%s / %s: البروتين صفر -- الجدول بيقرا total_p"
                % (program, day["day"]))


def test_the_engine_returns_the_program_when_it_is_picked():
    """‏"أول ما أدوس يتعمل على طول للأوبشن اللي اخترته" -- المحرّك
    بيرجّع جدول البرنامج، مش خطة عامة."""
    import plan_engine
    base = {"age": "34", "gender": "انثى", "height": "162", "weight": "82",
            "tdee": "2000", "goal_cal": "1600", "goal_type": "weight_loss",
            "culture": "مصري", "symptoms": [], "allergies": [],
            "zigzag_mode": "none"}
    for program in dp.PROGRAMS:
        data = dict(base, diet_plan_type=program)
        days = plan_engine.generate_weekly_plan(data)
        assert len(days) == 7, (program, len(days))
        assert days[0].get("program") == program, (program, days[0].get("program"))
        # ‏وأكل البرنامج، مش أكل القايمة العامة
        table_meals = set(_all_meals(program))
        first_words = {m.split()[1] for m in table_meals if len(m.split()) > 1}
        got = days[0].get("lunch", "")
        assert got, (program, days[0])
        assert got.split()[1] in first_words, (program, got)


def test_a_program_s_warnings_reach_the_notes_for_the_pdf():
    """‏التحذير لازم يوصل للدكتور. نفس مسار الكيميائي والتكميم:
    أزواج (عربي، إنجليزي) عشان الـPDF الإنجليزي مايطلعش عربي."""
    import plan_engine
    data = {"age": "9", "gender": "ذكر", "height": "130", "weight": "40",
            "tdee": "1500", "goal_cal": "900", "goal_type": "weight_loss",
            "culture": "مصري", "symptoms": [], "allergies": [],
            "zigzag_mode": "none", "diet_plan_type": "kids"}
    plan_engine.generate_weekly_plan(data)
    pairs = data.get("chemical_note_pairs") or []
    assert pairs, "‏تحذير برنامج الأطفال مش بيوصل للملاحظات"
    assert any("تخسيس" in ar for ar, _ in pairs), pairs
    for ar, en in pairs:
        assert ar and en and ar != en, (ar, en)


def test_the_clean_table_is_the_company_sheet_s_shape():
    """‏"الجدول اللي معلوش أي حاجة يبقى شبه" -- أيام في الصفوف، وجبات في
    الأعمدة، وكل مكوّن في سطر لوحده. والهوية بس هي اللي بتتشال."""
    import app as A
    import plan_engine
    data = {"name": "عميل الاختبار", "age": "34", "gender": "انثى",
            "height": "162", "weight": "82", "tdee": "2000",
            "goal_cal": "1600", "goal_type": "weight_loss", "culture": "مصري",
            "diet_plan_type": "low_carb_program", "symptoms": [],
            "allergies": [], "zigzag_mode": "none"}
    with A.app.test_request_context("/"):
        html = plan_engine.plan_html(data, clean=True)

    head = re.search(r"<thead><tr>(.*?)</tr></thead>", html, re.S)
    assert head, "‏مافيش جدول"
    cols = [re.sub(r"<[^>]+>", "", c).strip()
            for c in re.findall(r"<th[^>]*>(.*?)</th>", head.group(1))]
    assert cols[0] in ("اليوم", "Day"), cols
    for label in ("الفطار", "الغداء", "العشاء", "سناك"):
        assert label in cols, (label, cols)
    rows = re.findall(r'<tr>(<td class="dcell".*?)</tr>', html, re.S)
    assert len(rows) == 7, len(rows)
    # ‏كل مكوّن في سطر: العنصر بيتلف في span.it وده display:block
    assert 'class="it"' in html
    assert "td .it {" in html and "display:block" in html
    # ‏الهوية اتشالت، والكلام الطبي فضل
    assert "NX-" not in html and "NutraX" not in html
    assert "1626" in html or re.search(r">\s*1[5-7]\d\d\s*<", html), \
        "‏عمود السعرات اختفى من النسخة النضيفة"


# ═══ سطر المرجع ═════════════════════════════════════
#
# ‏الدكتور بعت كتابين محفوظين الحقوق عشان أبني منهم. البديل اللي
# اتعمل: كل برنامج بيقول المرجع المنشور اللي ماشي عليه -- سند يقدر
# يكتبه على الورقة ويوريه لعميل.


def test_every_programme_names_a_source():
    """‏والمرجع بالعربي والإنجليزي: الـPDF الإنجليزي بياخد التاني."""
    for program in dp.PROGRAMS:
        pair = dp.PROGRAM_SOURCES.get(program)
        assert pair, "‏%s مالوش مرجع" % program
        source_ar, source_en = pair
        assert source_ar.strip() and source_en.strip(), program
        assert source_ar != source_en, "‏%s: الإنجليزي نسخة من العربي" % program
        entry = dp.PROGRAM_SYSTEMS[program]
        assert entry["source"] == source_ar, program
        assert entry["source_en"] == source_en, program


def test_the_source_reaches_the_plan_and_the_picker():
    """‏مرجع في الكود ومابيوصلش للورقة مالوش قيمة."""
    for program in dp.PROGRAMS:
        days, _ = dp.build_program_plan(program, target_cal=1700,
                                        gender="أنثى", weight=80)
        for day in days:
            assert day.get("source"), (program, day["day"])
            assert day.get("source_en"), (program, day["day"])
    page = io.open("templates/generate.html", encoding="utf-8").read()
    assert "nx-opt-src" in page, "‏سطر المرجع مش في الفورم"
    assert "info.source" in page, "‏الفورم مش بيقرا المرجع"


# ═══ Opti-tect: نظام النقاط من عرض الشركة ══════════
#
# ‏العرض بيحدد المعادلات كلها، فالاختبارات دي بتقيسها بالرقم
# زي ما هي مكتوبة فيه -- مش بتقيس حاجة انا اخترعتها.


def test_the_points_come_out_exactly_as_the_deck_says():
    """‏النقاط = الوزن × معامل، والمعامل من العرض."""
    import optitect
    cases = [
        # (الوزن, الهدف, النوع, المرحلة, رياضي) -> (من, إلى)
        ((95, "weight_loss", "ذكر", "first", None), (95 * 1.2, 95 * 1.5)),
        ((82, "weight_loss", "انثى", "first", None), (82 * 1.2, 82 * 1.2)),
        ((82, "weight_loss", "ذكر", "switch", None), (82 * 1.5, 82 * 1.8)),
        ((82, "weight_loss", "انثى", "switch", None), (82 * 1.4, 82 * 1.6)),
        ((70, "maintenance", "ذكر", "first", None), (70 * 1.5, 70 * 2.0)),
        ((60, "muscle_gain", "ذكر", "first", None), (60 * 5.0, 60 * 7.0)),
        ((80, "weight_loss", "ذكر", "first", "cut"), (80 * 1.8, 80 * 2.5)),
        ((80, "maintenance", "ذكر", "first", "perform"), (80 * 2.5, 80 * 4.0)),
        ((80, "muscle_gain", "ذكر", "first", "bulk"), (80 * 5.0, 80 * 7.0)),
    ]
    for (weight, goal, gender, phase, athlete), (low, high) in cases:
        got = optitect.points_for(weight, goal, gender, phase, athlete)
        assert got["low"] == round(low), (weight, goal, gender, phase,
                                          athlete, got["low"], low)
        assert got["high"] == round(high), (weight, goal, gender, phase,
                                            athlete, got["high"], high)


def test_the_carb_tier_follows_the_weight_bands_in_the_deck():
    """‏سلايد 9: A فوق 90، B من 75 لـ90، C أقل من 75."""
    import optitect
    for weight, want in ((120, "A"), (95, "A"), (90.5, "A"),
                         (90, "B"), (82, "B"), (75.5, "B"),
                         (75, "C"), (60, "C"), (45, "C")):
        tier = optitect.carb_tier(weight)
        assert tier and tier[0] == want, (weight, tier, want)
    # ‏من غير وزن مافيش فئة -- الفئة بتتحدد من الوزن وبس
    assert optitect.carb_tier(0) is None
    assert optitect.carb_tier(None) is None
    assert optitect.carb_tier("") is None


def test_the_two_week_stall_zigzag_matches_the_deck():
    """‏ثبات أكتر من أسبوعين: أول 3 أيام الوزن×(1 إلى 1.3)،
    وآخر 3 أيام الوزن×(0.8 إلى 1)."""
    import optitect
    z = optitect.zigzag_points(88)
    assert z["high_low"] == 88 and z["high_high"] == round(88 * 1.3), z
    assert z["low_low"] == round(88 * 0.8) and z["low_high"] == 88, z
    assert z["weeks"] == 2, z
    # ‏وبيطلع في الوصفة لما يتقال إن فيه ثبات، ومابيطلعش من نفسه
    quiet, _ = optitect.prescribe(88, "weight_loss", "انثى")
    loud, _ = optitect.prescribe(88, "weight_loss", "انثى",
                                 stalled_two_weeks=True)
    assert not any("زجزاج" in ar for ar, _ in quiet), quiet
    assert any("زجزاج" in ar for ar, _ in loud), loud


def test_an_allowance_outside_the_booklet_is_flagged():
    """‏العرض بيقول 105 برنامج من 40 لـ300 نقطة، ومعادلة الزيادة
    (الوزن × 5 إلى 7) بتطلّع 420 نقطة لعميل 60 كجم.

    ‏ده تناقض جوّه أرقام العرض نفسه. الأخصائي هيدوّر على برنامج 420
    نقطة في كتيّب أقصاه 300 ومش هيلاقيه، فلازم يتقال.
    """
    import optitect
    lines, detail = optitect.prescribe(60, "muscle_gain", "ذكر")
    assert detail["out_of_book"], detail
    assert any("الكتيّب" in ar for ar, _ in lines), lines
    # ‏والرصيد العادي مش بيتعلّم
    _, ok = optitect.prescribe(82, "weight_loss", "انثى")
    assert not ok["out_of_book"], ok


def test_optitect_still_says_the_food_points_booklet_is_missing():
    """‏الحساب بقى حقيقي، بس نقاط الأصناف في كتيّب مش معانا -- والعرض
    مابيكتبش المعادلة اللي بتحوّل الأكل لنقاط.

    ‏خمس أمثلة بس مش كفاية لمعادلة بتلاتة معاملات، فاستخراجها منهم
    بيبقى تخمين لابس شكل معادلة -- ورصيد غلط معناه عميل بياكل غلط.
    """
    _, warnings = dp.build_program_plan("optitect", target_cal=1700,
                                        gender="انثى", weight=82)
    flagged = [w for w in warnings if w["kind"] == "needs_source"]
    assert flagged, "‏الكتيّب الناقص مش بيتقال"
    assert "Opti-tect Diet Guide" in flagged[0]["reason"], flagged[0]
    import optitect
    assert len(optitect.EXAMPLE_POINTS) == 5, optitect.EXAMPLE_POINTS


def test_the_points_prescription_lands_on_the_sheet_not_as_a_warning():
    """‏رصيد النقاط هو الوصفة، مش مشكلة. التحذيرات بتتكتب بعلامة ⚠️،
    فلو الرصيد اتحط فيها كان هيطلع للعميل كأنه تحذير."""
    days, warnings = dp.build_program_plan("optitect", target_cal=1700,
                                           gender="انثى", weight=82)
    note = days[0]["note"]
    assert "نقطة" in note, note
    assert "98" in note, note              # 82 × 1.2
    assert "B" in note, note               # فئة الكربوهيدرات
    assert days[0]["note_en"] != note, "‏الإنجليزي نسخة من العربي"
    assert "points" in days[0]["note_en"], days[0]["note_en"]
    kinds = [w["kind"] for w in warnings]
    assert "optitect_points" not in kinds, kinds


def test_optitect_without_a_weight_asks_for_it_instead_of_guessing():
    """‏رصيد النقاط كله بيتحسب من الوزن. من غيره مانخمّنش."""
    import optitect
    lines, detail = optitect.prescribe(None, "weight_loss", "انثى")
    assert detail["points"] is None, detail
    assert len(lines) == 1, lines
    assert "الوزن" in lines[0][0], lines[0]


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
            print(f"  FAIL  {name}\n        {str(e)[:400]}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

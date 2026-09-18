# -*- coding: utf-8 -*-
"""بروتوكول التكميم خطره مختلف عن أي نظام تاني في الموقع.

باقي الأنظمة لو غلطت تطلع خطة مش مثالية. هنا لو غلطت المرحلة، تطلع خطة
المريض مايقدرش يبلعها أصلاً (أكل لين لمريض في أسبوعه الأول)، أو خطة بتجوّعه
(سوائل صافية لمريض في شهره السادس -- 90 kcal في اليوم).

فاللي بيتثبّت هنا:

  * المرحلة بتتحدد صح من عدد الأسابيع، والحدود بين المراحل مضبوطة.
  * من غير الرقم مافيش تخمين -- عرض للبروتوكول وتحذير، مش خطة أسبوع.
  * التحذير بتاع "تحت الحد الآمن" مكتوب بصيغة "متوقع" في المراحل الأولى.
    لو اتكتب بصيغة خطر، الأخصائي هيتعلّم يتجاهله، ووقتها التحذير الحقيقي
    (اللي بعد ستة شهور) بيضيع معاه.
  * القواعد الدايمة موجودة على كل أسبوع.
  * كل نص وجبة مترجم، وكل مرحلة خاناتها بتتملي لمريض عنده حالات مرضية.

Run with:  python3 tests/test_sleeve_diet.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meal_database as md  # noqa: E402
import sleeve_diet as sl  # noqa: E402


def test_the_phase_boundaries_are_where_the_protocol_puts_them():
    expected = {
        1: "clear_liquids",
        2: "full_liquids",
        3: "pureed", 4: "pureed",
        5: "soft", 6: "soft",
        7: "regular", 12: "regular", 52: "regular", 200: "regular",
    }
    for week, key in expected.items():
        got = sl.phase_for_week(week)
        assert got is not None, "‏أسبوع %d مالوش مرحلة" % week
        assert got["key"] == key, (
            "‏أسبوع %d المفروض %s وطلع %s" % (week, key, got["key"]))


def test_a_nonsense_week_is_refused_rather_than_guessed():
    """‏تخمين المرحلة هو الخطر نفسه، فالرقم الغلط لازم يرجّع None."""
    for bad in (None, "", 0, -3, "abc", "  "):
        assert sl.phase_for_week(bad) is None, "‏%r اتخمّن له مرحلة" % (bad,)


def test_without_the_week_it_shows_the_protocol_and_says_so():
    days, warnings = sl.build_sleeve_plan(None, gender="أنثى")
    kinds = [w["kind"] for w in warnings]
    assert "needs_weeks" in kinds, "‏مفيش تحذير إن الرقم ناقص"
    assert len(days) == len(sl.SLEEVE_PHASES), (
        "‏المفروض يعرض كل مرحلة مرة، طلع %d" % len(days))
    note = [w for w in warnings if w["kind"] == "needs_weeks"][0]
    assert "مش خطة أسبوع" in note["reason"], "‏التحذير مش بيوضح إن ده مش خطة"
    assert "not a week's plan" in note["reason_en"], "‏الإنجليزي مش بيوضح"


def test_a_known_week_builds_seven_days_in_one_phase():
    for week in (1, 2, 4, 6, 9):
        days, _ = sl.build_sleeve_plan(week, gender="ذكر")
        assert len(days) == 7, "‏أسبوع %d طلع %d يوم" % (week, len(days))
        keys = {d["phase_key"] for d in days}
        assert len(keys) == 1, "‏الأسبوع الواحد لازم يكون مرحلة واحدة: %s" % keys


def test_the_week_is_not_seven_identical_days():
    """‏المرحلة واحدة، بس اليوم مايتكررش بالحرف سبع مرات."""
    days, _ = sl.build_sleeve_plan(4, gender="أنثى")
    for slot in sl.SLOTS:
        served = {d.get(slot) for d in days}
        assert len(served) > 1, "‏%s نفسه في السبع أيام" % slot


def test_the_early_phases_say_the_low_calories_are_expected():
    """‏أهم اختبار في الملف.

    أسبوع السوائل الصافية حوالي 90 kcal. ده صح مش غلط -- المعدة بتلتئم.
    لو التحذير اتكتب بصيغة خطر، الأخصائي هيتعلّم يتجاهل تحذيرات النظام كله.
    """
    for week in (1, 2, 4, 6):
        _, warnings = sl.build_sleeve_plan(week, gender="أنثى")
        floor = [w for w in warnings if w["kind"] == "below_floor"]
        assert floor, "‏أسبوع %d المفروض يبقى تحت الحد ومفيش تحذير" % week
        w = floor[0]
        assert w["expected"] is True, "‏أسبوع %d اتكتب كخطر مش كمتوقع" % week
        assert "متوقع" in w["reason"], "‏كلمة متوقع ناقصة في أسبوع %d" % week
        assert "EXPECTED" in w["reason_en"], "‏الإنجليزي مش بيقول متوقع"


def test_after_six_months_low_calories_stop_being_expected():
    """‏نفس الرقم، معنى مختلف: 800 kcal في أسبوع 7 طبيعي، وبعد سنة لأ."""
    _, early = sl.build_sleeve_plan(9, gender="أنثى")
    _, late = sl.build_sleeve_plan(52, gender="أنثى")
    e = [w for w in early if w["kind"] == "below_floor"]
    l = [w for w in late if w["kind"] == "below_floor"]
    assert e and e[0]["expected"] is True, "‏أسبوع 9 المفروض متوقع"
    assert l and l[0]["expected"] is False, "‏أسبوع 52 مش المفروض يبقى متوقع"
    assert "راجع الكميات" in l[0]["reason"], "‏مفيش طلب مراجعة بعد سنة"


def test_the_last_week_of_a_phase_announces_the_next_one():
    """‏الأخصائي محتاج يعرف إن الأسبوع الجاي مرحلة تانية قبل ما يبعت الخطة."""
    for week in (1, 2, 4, 6):
        _, warnings = sl.build_sleeve_plan(week, gender="أنثى")
        trans = [w for w in warnings if w["kind"] == "transition"]
        assert trans, "‏أسبوع %d آخر أسبوع في مرحلته ومفيش إشعار" % week
    # ‏المرحلة المفتوحة مالهاش انتقال
    _, warnings = sl.build_sleeve_plan(20, gender="أنثى")
    assert not [w for w in warnings if w["kind"] == "transition"], (
        "‏المرحلة الأخيرة مفتوحة، مايصحش يطلع إشعار انتقال")


def test_the_permanent_rules_ride_on_every_week():
    """‏مفيش غازيات، ومفيش شرب مع الأكل، والفيتامينات مدى الحياة -- دي مش مرحلة."""
    for week in (1, 4, 9, 60):
        days, _ = sl.build_sleeve_plan(week, gender="ذكر")
        for d in days:
            rules = d.get("permanent_rules") or []
            assert len(rules) == len(sl.PERMANENT_RULES), (
                "‏أسبوع %d ناقصه قواعد دايمة" % week)
        joined = " ".join(days[0]["permanent_rules"])
        for needed in ("غازية", "شاليموه", "الفيتامينات", "البروتين"):
            assert needed in joined, "‏قاعدة %s ناقصة" % needed


def test_every_slot_fills_in_every_phase_for_a_patient_with_conditions():
    """‏خانة فاضية في بروتوكول التكميم معناها المريض مالوش أكل في الوقت ده."""
    for symptoms in ([], ["سكري النوع الثاني"], ["حساسية اللاكتوز"],
                     ["الفشل الكلوي المزمن"], ["ضغط الدم المرتفع"]):
        for week in (1, 2, 4, 6, 9):
            days, warnings = sl.build_sleeve_plan(week, symptoms=symptoms,
                                                  gender="أنثى")
            unfillable = [w for w in warnings if w["kind"] == "unfillable"]
            assert not unfillable, (
                "‏أسبوع %d مع %s: خانة فاضية -> %s"
                % (week, symptoms, [w["slot"] for w in unfillable]))


def test_a_diabetic_is_not_denied_the_sugar_free_option():
    """‏"سكر" بتمسك "بدون سكر" كـsubstring.

    قبل الحماية، مريض السكري كان ممنوع من الشاي بدون سكر والجيلي بدون سكر --
    يعني فطاره في الأسبوع الأول كان بيطلع فاضي. والحماية دي بتصلح كمان باگ
    أقدم: مريض المرارة كان ممنوع من الفراخ المشوية "بدون جلد".
    """
    assert md.safe_for_all({"meal": "🍵 شاي اعشاب خفيف بدون سكر"}, ["سكري"]), \
        "‏الشاي بدون سكر لسه ممنوع على مريض السكري"
    assert md.safe_for_all({"meal": "🍗 دجاج مشوي (بدون جلد) + 🍚 ارز"}, ["مرارة"]), \
        "‏الفراخ بدون جلد لسه ممنوعة على مريض المرارة"
    # ‏والنفي مايفكّش المنع الحقيقي
    assert not md.safe_for_all({"meal": "🍰 كيك بالسكر"}, ["سكري"]), \
        "‏الكيك بالسكر بقى مسموح -- الحماية فكّت المنع"
    assert not md.safe_for_all({"meal": "🍗 دجاج بالجلد مقلي"}, ["مرارة"]), \
        "‏الفراخ بالجلد بقت مسموحة"
    # ‏و"بدون زيت" مايعتبرش نفي لليمون اللي بعده
    assert not md.safe_for_all({"meal": "🥗 سلطة بدون زيت + 🍋 ليمون"}, ["ارتجاع"]), \
        "‏بدون زيت اتحسبت نفي لليمون"


def test_the_protocols_own_forbidden_list_is_never_served():
    """‏كل مرحلة ليها ممنوعات، ومايصحش تقدّم واحد منها."""
    for week in (1, 2, 4, 6, 9):
        days, _ = sl.build_sleeve_plan(week, gender="أنثى")
        phase = sl.phase_for_week(week)
        for d in days:
            for slot in sl.SLOTS:
                meal = d.get(slot)
                if not meal:
                    continue
                text = md.normalize_ar(meal)
                for token in phase["forbidden"]:
                    idx = text.find(md.normalize_ar(token))
                    if idx < 0:
                        continue
                    assert md._is_negated(text, idx), (
                        "‏%s فيه %r وهو ممنوع في %s"
                        % (meal, token, phase["name"]))


def test_the_system_is_offered_as_an_eating_system():
    import os as _os
    _os.environ.setdefault("SECRET_KEY", "test-only")
    import app  # noqa: F401  بيسجّل الأنظمة
    from meal_database import DIET_PLAN_TYPES
    assert "sleeve" in DIET_PLAN_TYPES, "‏النظام مش مسجّل في أنظمة الأكل"
    info = DIET_PLAN_TYPES["sleeve"]
    assert info["name_en"], "‏مفيش اسم إنجليزي"
    assert len(info["meals"]) == 4, "‏عدد الخانات اتغير"


def test_the_form_asks_for_the_weeks():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html = open(os.path.join(here, "templates", "generate.html"),
                encoding="utf-8").read()
    assert 'name="sleeve_weeks"' in html, "‏الفورم مش بيسأل عن عدد الأسابيع"
    assert "sleeveWeeksBox" in html, "‏الخانة مش بتظهر/تختفي مع النظام"
    routes = open(os.path.join(here, "routes_plans.py"), encoding="utf-8").read()
    assert 'request.form.get("sleeve_weeks"' in routes, \
        "‏الراوت مش بياخد الرقم من الفورم، فالمرحلة هتتحسب غلط"


def test_every_phase_meal_is_translated():
    from meal_i18n import untranslated_terms
    missing = {}
    for item in sl.SLEEVE_MEALS:
        left = untranslated_terms(item["meal"])
        if left:
            missing[item["meal"]] = left
    assert not missing, "‏وجبات مش مترجمة: %s" % list(missing.items())[:4]


def test_the_phase_note_and_its_english_are_both_real():
    for phase in sl.SLEEVE_PHASES:
        assert phase["note"] and phase["note_en"], "‏%s ناقص ملاحظة" % phase["key"]
        assert phase["note"] != phase["note_en"], (
            "‏%s الإنجليزي نسخة من العربي" % phase["key"])
        assert phase["forbidden"] and phase["forbidden_en"], (
            "‏%s ناقص قايمة ممنوعات" % phase["key"])
        assert len(phase["forbidden"]) == len(phase["forbidden_en"]), (
            "‏%s قايمة الممنوع الإنجليزي طولها مختلف" % phase["key"])


def test_protein_is_real_from_the_liquid_phase_onward():
    """‏الهدف 60-80 جم بروتين. السوائل الصافية مستحيل توصله، بس اللي بعدها لأ."""
    for week, floor in ((2, 40), (4, 40), (6, 50), (9, 60)):
        days, _ = sl.build_sleeve_plan(week, gender="أنثى")
        worst = min(d["total_p"] for d in days)
        assert worst >= floor, (
            "‏أسبوع %d أقل يوم فيه %d جم بروتين، والمفروض %d على الأقل"
            % (week, worst, floor))


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

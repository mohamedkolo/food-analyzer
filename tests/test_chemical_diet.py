# -*- coding: utf-8 -*-
"""The chemical diet is a fixed cycle, and that is exactly what makes it risky.

Every other system fills meal slots from a pool of hundreds, so a meal the
client cannot eat is simply never drawn. Here the category IS the day: day two
is fruit and nothing else. Filtering can only choose within the day, which
means the two ordinary safety mechanisms both misbehave on it --
filter_by_conditions substitutes from SAFE_ALTERNATIVES and turns a fruit day
into eggs and white bread, and filter_meals_by_exclusions returns the
unfiltered list when everything is excluded, handing back the very food the ban
exists to stop.

So these lock in three things: the protocol survives (six days, in order, each
inside its own category), the patient survives it (a kidney patient never sees
the spinach, oranges or kiwi on the kidney list), and when a day cannot be made
safe it is reported rather than quietly filled.

Run with:  python3 tests/test_chemical_diet.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chemical_diet as cd  # noqa: E402
from meal_database import UNSAFE_FOODS, safe_for_all, unsafe_keys_for  # noqa: E402

KIDNEY = ["الفشل الكلوي المزمن"]
ARABIC = re.compile(r"[\u0600-\u06ff]")


def _meals_of(day):
    return [day[s] for s in cd.SLOTS if day.get(s)]


def _all_meals(days):
    return [m for d in days for m in _meals_of(d)]


def test_the_cycle_is_six_days_in_the_protocol_order():
    days, _ = cd.build_chemical_plan()
    assert len(days) == cd.CYCLE_LENGTH == 6, f"got {len(days)} days, not 6"
    assert [d["cycle_key"] for d in days] == [
        "vegetables", "fruit", "fish", "chicken", "green", "single_fruit"
    ], "the days came back out of protocol order"


def test_each_day_stays_inside_its_own_category():
    # the point of the protocol: a fruit day may not quietly acquire chicken
    off_category = {
        "vegetables": ["دجاج", "سمك", "تونة", "تفاح", "برتقال"],
        "fruit": ["دجاج", "سمك", "تونة", "بيض", "خبز"],
        "fish": ["دجاج", "تفاح", "برتقال", "خبز"],
        "chicken": ["سمك", "تونة", "تفاح", "خبز"],
        "green": ["دجاج", "سمك", "بيض", "خبز"],
        "single_fruit": ["دجاج", "سمك", "بيض", "خبز", "خضار"],
    }
    days, _ = cd.build_chemical_plan()
    for day in days:
        for meal in _meals_of(day):
            for word in off_category[day["cycle_key"]]:
                assert word not in meal, (
                    f"{day['day']} served '{meal}', which is outside its category")


def test_the_single_fruit_day_serves_one_fruit_all_day():
    days, _ = cd.build_chemical_plan()
    last = days[-1]
    fruits = {m.split()[0] for m in _meals_of(last)}
    assert len(fruits) == 1, f"the single-fruit day served {fruits}"


def test_the_protocols_own_bans_are_never_served():
    days, _ = cd.build_chemical_plan()
    for day in days:
        for meal in _meals_of(day):
            for banned in day["forbidden"]:
                assert banned not in meal, (
                    f"{day['day']} forbids {banned} but served '{meal}'")


def test_a_kidney_patient_never_gets_what_the_ban_exists_for():
    keys = unsafe_keys_for(KIDNEY)
    assert keys == ["كلوي"], f"the condition did not resolve: {keys}"
    days, _ = cd.build_chemical_plan(KIDNEY)
    for meal in _all_meals(days):
        assert safe_for_all({"meal": meal}, keys), (
            f"a kidney patient was served '{meal}'")
    # the collisions that motivated all this, named outright
    joined = " ".join(_all_meals(days))
    for food in ("سبانخ", "برتقال", "كيوي"):
        assert food not in joined, f"{food} survived the kidney filter"
        assert food in " ".join(UNSAFE_FOODS["كلوي"]), (
            f"{food} is no longer on the kidney list -- this test is now checking nothing")


def test_filtering_narrows_a_day_instead_of_leaving_its_category():
    # the failure this replaced: SAFE_ALTERNATIVES swapped the fruit day for
    # "eggs and white bread" -- safe, but no longer the protocol
    days, _ = cd.build_chemical_plan(KIDNEY)
    fruit_day = next(d for d in days if d["cycle_key"] == "fruit")
    meals = _meals_of(fruit_day)
    assert meals, "the fruit day came back empty for a kidney patient"
    for meal in meals:
        assert any(f in meal for f in ("تفاح", "فراولة", "بطيخ")), (
            f"the fruit day served '{meal}', which is not fruit")


def test_an_unfillable_slot_is_reported_rather_than_filled():
    # empty out day five's breakfast entirely
    days, warnings = cd.build_chemical_plan([], ["سموذي", "عصير"])
    green = next(d for d in days if d["cycle_key"] == "green")
    assert "breakfast" not in green, (
        f"an excluded slot was filled anyway with '{green.get('breakfast')}'")
    assert any(w["slot"] == "breakfast" and w["day"] == green["day"] for w in warnings), (
        f"the emptied slot was not reported: {warnings}")


def test_a_diabetic_is_cautioned_on_both_fruit_days():
    # whole fruit is not on the سكري list and must not be put there -- that
    # list is global. The open-ended fruit days get a caution instead.
    for condition in ("سكري النوع الثاني", "سكري النوع الاول"):
        days, warnings = cd.build_chemical_plan([condition])
        cautions = [w for w in warnings if w["kind"] == "caution"]
        cautioned = {w["day"] for w in cautions}
        fruit_days = {d["day"] for d in days
                      if d["cycle_key"] in ("fruit", "single_fruit")}
        assert cautioned == fruit_days, (
            f"{condition}: cautioned {cautioned}, expected {fruit_days}")
        # and the day carries it too, so it shows where it applies
        for day in days:
            expected = 1 if day["cycle_key"] in ("fruit", "single_fruit") else 0
            assert len(day["cautions"]) == expected, (
                f"{condition}: {day['day']} carries {day['cautions']}")


def test_a_caution_is_not_a_ban():
    # the day still gets built -- a caution must not empty it
    days, _ = cd.build_chemical_plan(["سكري النوع الثاني"])
    for day in days:
        assert _meals_of(day), f"{day['day']} came back empty"


def test_no_caution_fires_for_an_unrelated_condition():
    _, warnings = cd.build_chemical_plan(KIDNEY)
    assert [w for w in warnings if w["kind"] == "caution"] == [], (
        "the kidney condition raised a diabetes caution")


def test_every_caution_reads_in_both_languages():
    for day in cd.CHEMICAL_DAYS:
        for cond_key, text in (day.get("cautions") or {}).items():
            assert cond_key in UNSAFE_FOODS, (
                f"{day['key']} cautions on {cond_key!r}, which is not a condition key")
            assert text.get("ar") and text.get("en"), f"{day['key']}/{cond_key} is half-written"
            assert not ARABIC.search(text["en"]), (
                f"{day['key']}/{cond_key} English still contains Arabic")


def test_a_clean_plan_reports_nothing():
    _, warnings = cd.build_chemical_plan()
    assert warnings == [], f"an unrestricted plan raised warnings: {warnings}"


def test_the_generator_returns_the_cycle_and_surfaces_its_warnings():
    os.environ.setdefault("SECRET_KEY", "test-key")
    from core import app  # noqa: E402
    from plan_engine import generate_weekly_plan  # noqa: E402

    data = {
        "name": "تست", "age": "30", "gender": "ذكر", "height": "175", "weight": "85",
        "tdee": "2400", "goal_cal": "1900", "goal_type": "weight_loss",
        "culture": "مصري", "diet_plan_type": "chemical",
        "symptoms": ["سكري النوع الثاني"], "allergies": [], "notes": "", "user_id": 1,
        "disliked_foods": "سموذي, عصير",
    }
    with app.test_request_context("/"):
        plan = generate_weekly_plan(data)

    assert len(plan) == 6, f"the generator returned {len(plan)} days, not 6"
    kinds = {w["kind"] for w in data["chemical_warnings"]}
    assert kinds == {"unfillable", "caution"}, f"only {kinds} reached the caller"
    assert data["chemical_warnings"], "the unfillable slot never reached the caller"
    # the dietitian has to see it before sending the plan
    assert "⚠️" in data["notes"], f"the warning is not on the notes: {data['notes']!r}"


def test_the_system_is_offered_in_the_plan_form():
    os.environ.setdefault("SECRET_KEY", "test-key")
    import core  # noqa: F401,E402  -- applies meal_extra
    from meal_database import DIET_PLAN_TYPES  # noqa: E402

    assert "chemical" in DIET_PLAN_TYPES, "the system never reached DIET_PLAN_TYPES"
    entry = DIET_PLAN_TYPES["chemical"]
    for key in ("name", "name_en", "meals", "meal_labels", "meal_labels_en",
                "description", "description_en"):
        assert entry.get(key), f"the form entry is missing {key}"


def test_the_day_rules_carry_english_that_is_actually_english():
    # preview.html shows each day's rule and falls back to the Arabic when the
    # _en field is missing, so a gap here surfaces as Arabic on an English page
    for day in cd.CHEMICAL_DAYS:
        for field in ("name_en", "note_en"):
            assert day.get(field), f"{day['key']} has no {field}"
            assert not ARABIC.search(day[field]), (
                f"{day['key']}.{field} still contains Arabic: {day[field]!r}")
        assert len(day["forbidden_en"]) == len(day["forbidden"]), (
            f"{day['key']}: forbidden and forbidden_en are different lengths")
        for item in day["forbidden_en"]:
            assert not ARABIC.search(item), f"{day['key']} forbids {item!r} in Arabic"

    # and the built days carry them through to the template
    days, _ = cd.build_chemical_plan()
    for d in days:
        assert d.get("note_en") and d.get("forbidden_en") is not None


def test_the_option_renders_in_the_eating_system_section():
    # not just present in DIET_PLAN_TYPES -- actually drawn as a choice, in
    # both forms and both languages
    os.environ.setdefault("SECRET_KEY", "test-key")
    import json  # noqa: E402
    from core import app  # noqa: E402
    from flask import render_template, session  # noqa: E402
    from meal_database import DIET_PLAN_TYPES  # noqa: E402
    from zigzag import ZIGZAG_MODES  # noqa: E402

    entry = DIET_PLAN_TYPES["chemical"]
    for template in ("generate.html", "request_plan.html"):
        for lang, expected in (("ar", entry["name"]), ("en", entry["name_en"])):
            with app.test_request_context("/"):
                session["lang"] = lang
                html = render_template(
                    template, user={"name": "tst", "role": "admin"}, lang=lang,
                    diet_plans=DIET_PLAN_TYPES, zigzag_modes=ZIGZAG_MODES,
                    zigzag_json=json.dumps(ZIGZAG_MODES, ensure_ascii=False),
                    prev={})
            assert 'value="chemical"' in html, (
                f"{template}/{lang}: the option is not in the form")
            assert expected in html, (
                f"{template}/{lang}: the option renders without {expected!r}")


def test_every_day_name_has_an_english_rendering():
    os.environ.setdefault("SECRET_KEY", "test-key")
    from core import ENGLISH_DAYS  # noqa: E402

    for day in cd.CHEMICAL_DAYS:
        assert ENGLISH_DAYS.get(day["name"]) == day["name_en"], (
            f"{day['name']} would render in Arabic in English mode")


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

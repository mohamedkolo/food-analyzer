# -*- coding: utf-8 -*-
"""A day's calories next to what its foods add up to.

The stored day total is the library's written meal labels scaled toward the
target. It is not the sum of the listed foods. plan_engine.day_calc computes that
sum with meal_macros; the plan pages show it, or say plainly that the day is an
estimate. Run with:  python3 tests/test_day_calc.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")

import app as A  # noqa: E402
import core  # noqa: E402
import plan_engine  # noqa: E402

DATA = {"name": "عميل تجربة", "age": "32", "gender": "ذكر", "height": "176", "weight": "95",
        "tdee": "2350", "goal_cal": "1750", "goal_type": "weight_loss", "culture": "مصري",
        "diet_plan_type": "standard", "symptoms": []}
EXPLICIT = {"day": "الاحد", "breakfast": "2 بيضة", "lunch": "200 جم دجاج مشوى + 150 جم أرز مطبوخ",
            "dinner": "150 جم زبادي خالي الدسم", "snack": "100 جم تفاح", "total_cal": 1750}
VAGUE = {"day": "الاحد", "breakfast": "بيض مسلوق 2", "lunch": "دجاج مشوي + ارز",
         "dinner": "زبادي", "snack": "تفاحة", "total_cal": 1750}


def test_explicit_day_is_computed_from_its_foods():
    c = plan_engine.day_calc(dict(EXPLICIT))
    assert c["basis"] == "items" and not c["incomplete_slots"], c
    assert 800 < c["computed_cal"] < 1000, c      # nowhere near the stored 1750


def test_a_default_portion_is_not_a_stated_amount():
    c = plan_engine.day_calc(dict(VAGUE))
    assert c["basis"] == "label", c
    assert "lunch" in c["incomplete_slots"], c


def test_the_plan_link_page_says_when_a_day_is_an_estimate():
    with A.app.test_request_context("/"):
        token = core.create_plan_link(1, DATA, [dict(VAGUE)])
    body = A.app.test_client().get(f"/p/{token}").get_data(as_text=True)
    assert 'data-basis="label"' in body and "تقدير" in body, "estimate note missing"


def test_the_plan_link_page_shows_the_computed_total_for_a_computed_day():
    with A.app.test_request_context("/"):
        token = core.create_plan_link(1, DATA, [dict(EXPLICIT)])
    body = A.app.test_client().get(f"/p/{token}").get_data(as_text=True)
    c = plan_engine.day_calc(dict(EXPLICIT))
    assert 'data-basis="items"' in body and f"{c['computed_cal']} kcal" in body, "computed total missing"


def test_a_generated_plan_carries_the_calc_on_every_day():
    from zigzag import zigzag_from_data
    data = dict(DATA, user_id=1, allergies=[], notes="", zigzag=None)
    data["zigzag"] = zigzag_from_data(dict(data))
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(dict(data))
    assert plan and all("calc" in d and d["calc"]["basis"] in ("items", "label") for d in plan)


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

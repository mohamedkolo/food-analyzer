# -*- coding: utf-8 -*-
"""Quantity, identity and provenance are separate flags, and a generic bridge
("جبنة" -> cottage cheese, "لحم" -> lean beef, "لبن" -> laban rayeb, bare
"زبادي" -> fat-free yoghurt) is never counted as a calculation from the actual
meal. The table value may still be shown as an estimate.
Run with:  python3 tests/test_three_flags.py
"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "k")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meal_macros as MM
import plan_engine
import plan_tools as PT
import day_progress

EXACT = "200 جم دجاج مشوى + 150 جم أرز مطبوخ"
BRIDGED = "30 جم جبنة + 120 جم لحم"
DAY_EXACT = {"day": "x", "breakfast": "2 بيضة", "lunch": EXACT, "dinner": "150 جم سمك بلطى مشوى او بالفرن",  # salmon row = USDA raw row, not a cooked-weight row (basis gate)
             "total_cal": 1700, "total_p": 100}
DAY_BRIDGED = dict(DAY_EXACT, dinner=BRIDGED)


def test_flags_are_independent_per_item():
    r = MM.macros("30 جم جبنة")
    i = r["items"][0]
    assert i["explicit_quantity"] and not i["exact_identity"], i
    assert r["complete"] and not r["exact"], r         # priced as an estimate, not exact
    r = MM.macros("جبنة قريش")                          # exact name, no quantity
    i = r["items"][0]
    assert i["exact_identity"] and not i["explicit_quantity"] and not r["exact"], r
    r = MM.macros("200 مل حليب كامل")
    assert r["exact"] and r["all_sourced"], r           # exact + stated + USDA row
    r = MM.macros("200 جم دجاج مشوى")
    assert r["exact"] and not r["all_sourced"], r       # table calculation, not source-verified


def test_generic_bridges_are_not_exact():
    for t in ("30 جم جبنة", "120 جم لحم", "240 مل لبن", "150 جم زبادي", "200 جم بطاطس", "12 جم مكسرات"):
        r = MM.macros(t)
        assert not r["exact"], (t, r)


def test_a_bridged_day_is_a_label_estimate_everywhere():
    c = plan_engine.day_calc(dict(DAY_EXACT))
    assert c["basis"] == "items", c
    c = plan_engine.day_calc(dict(DAY_BRIDGED))
    assert c["basis"] == "label" and "dinner" in c["incomplete_slots"], c
    # "لحم" bridges to the lean-beef row, whose name states no preparation: now unresolved by
    # basis (before the cooked-weight rule it was a generic identity). Either way it is not exact.
    sl = c["slots"]["dinner"]
    assert sl["generic_identity"] or sl["unresolved"], c
    assert plan_engine.computed_meal(BRIDGED) is None   # never feeds computed scaling


def test_stored_totals_and_edit_refresh_do_not_become_computed_from_a_bridge():
    day = dict(DAY_EXACT)
    plan_engine.refresh_day_totals(day)
    assert day["calc"]["basis"] == "items"
    day2 = dict(DAY_EXACT)
    st = PT.apply_change({}, day2, DAY_EXACT["dinner"], BRIDGED)
    assert st["estimated"] is True, st
    assert (day2.get("calc") or {}).get("basis") != "items", day2.get("calc")


def test_client_progress_and_snack_numbers_do_not_use_a_bridge():
    keys = ["breakfast", "lunch", "dinner"]
    r = day_progress.build(DAY_BRIDGED, keys, set(), set(), {k: k for k in keys})
    assert r["basis"] == "even_split", r
    import routes_plans
    assert routes_plans._meal_incomplete(BRIDGED) and not routes_plans._meal_incomplete(EXACT)


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

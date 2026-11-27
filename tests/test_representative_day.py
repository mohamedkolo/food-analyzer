# -*- coding: utf-8 -*-
"""A representative explicit day (eggs, dairy, rice, chicken, fish, legumes, vegetables, fruit, oil) calculated
under DEFAULT settings and checked against an INDEPENDENT calculation: the USDA SR Legacy values below are copied
from the USDA CSV (not from the app's table), grams/100 times the USDA row, summed per macro.
Verified totals and partial totals are kept apart.
Run with:  ADMIN_PASSWORD=pw123456 python3 tests/test_representative_day.py"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "k")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meal_macros as MM
import plan_engine

# text -> (USDA FDC id, grams, USDA kcal/protein/carbs/fat per 100 g) copied from the USDA CSV
DAY = {
    "breakfast": [("100 جم بيض مسلوق صلب (USDA 173424)", 173424, 100, (155.0, 12.58, 1.12, 10.61)),
                  ("200 جم حليب كامل الدسم", 172217, 200, (61.0, 3.15, 4.78, 3.27)),
                  ("100 جم موز", 173944, 100, (89.0, 1.09, 22.84, 0.33))],
    "lunch": [("150 جم صدر دجاج بالجلد مطبوخ أو مشوى", 171075, 150, (197.0, 29.8, 0.0, 7.78)),
              ("200 جم أرز أبيض مطبوخ", 168878, 200, (130.0, 2.69, 28.17, 0.28)),
              ("100 جم خيار", 168409, 100, (15.0, 0.65, 3.63, 0.11)),
              ("100 جم طماطم", 170457, 100, (18.0, 0.88, 3.89, 0.2)),
              ("10 جم زيت زيتون", 171413, 10, (884.0, 0.0, 0.0, 100.0))],
    "dinner": [("150 جم زبادي كامل الدسم", 171284, 150, (61.0, 3.47, 4.66, 3.25)),
               ("100 جم عدس", 172421, 100, (116.0, 9.02, 20.13, 0.38)),
               ("150 جم سمك أبيض مطبوخ", 174246, 150, (172.0, 24.47, 0.0, 7.51))],
}
TEXT = {k: " + ".join(t for t, *_ in v) for k, v in DAY.items()}
TOL = (1.5, 0.5, 0.6, 0.3)          # per 100 g, the review rule; scaled by grams/100 per item


def _expected(entries):
    exp = [0.0] * 4
    tol = [0.0] * 4
    for _t, _f, g, v in entries:
        for j in range(4):
            exp[j] += v[j] * g / 100.0
            tol[j] += max(TOL[j], 0.5) * g / 100.0     # whole-number library values get half a unit
    return exp, tol


def test_every_item_is_exact_explicit_and_sourced():
    for slot, entries in DAY.items():
        r = MM.macros(TEXT[slot])
        assert r["complete"] and r["exact"] and r["all_sourced"], (slot, r, [i for i in r["items"] if not i.get("sourced")])
        assert len(r["items"]) == len(entries)


def test_every_meal_and_the_day_match_the_independent_usda_calculation_on_all_four_macros():
    day_exp = [0.0] * 4
    day_tol = [0.0] * 4
    for slot, entries in DAY.items():
        r = MM.macros(TEXT[slot])
        exp, tol = _expected(entries)
        got = [r["cal"], r["p"], r["c"], r["f"]]
        for j, name in enumerate(("kcal", "protein", "carbs", "fat")):
            assert abs(got[j] - exp[j]) <= tol[j] + 0.5, (slot, name, got[j], round(exp[j], 2), round(tol[j], 2))
            day_exp[j] += exp[j]; day_tol[j] += tol[j]
    c = plan_engine.day_calc(dict(TEXT, total_cal=1800, total_p=100))
    assert c["basis"] == "items", c
    assert all(s["all_sourced"] for s in c["slots"].values()), c
    got = [c["computed_cal"], c["computed_p"], c["computed_c"], c["computed_f"]]
    for j, name in enumerate(("kcal", "protein", "carbs", "fat")):
        assert abs(got[j] - day_exp[j]) <= day_tol[j] + 1.5, (name, got[j], round(day_exp[j], 2), round(day_tol[j], 2))
    print("        day total app %s vs independent USDA %s" % (got, [round(x, 1) for x in day_exp]))


def test_a_total_with_one_unverified_item_is_complete_but_not_all_sourced():
    r = MM.macros("100 جم بيضة كاملة + 200 جم أرز أبيض مطبوخ")       # eggs: raw vs boiled is not stated in the row
    assert r["complete"] and not r["all_sourced"], r


def test_a_total_with_an_unresolved_item_is_partial():
    r = MM.macros("150 جم صدر دجاج + 200 جم أرز أبيض مطبوخ")         # chicken breast row names no preparation
    assert not r["complete"] and not r["exact"], r
    c = plan_engine.day_calc({"breakfast": "150 جم صدر دجاج", "lunch": "x", "dinner": "y", "total_cal": 1700, "total_p": 100})
    assert c["basis"] == "label", c


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn(); print(f"  PASS  {name}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}"); failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

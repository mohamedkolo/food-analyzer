# -*- coding: utf-8 -*-
"""Source-backed food rows and the plain mismatches they fix.

Values are copied from USDA FoodData Central SR Legacy (April 2018), per 100 g.
Run with:  python3 tests/test_meal_sources.py
"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "k")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meal_macros as MM
import meal_food_sources as S

USDA = {  # fdc_id: (kcal, protein, fat, carb)
    171265: (61.0, 3.15, 3.25, 4.8),
    170899: (410.0, 24.25, 33.82, 2.13),
    173687: (117.0, 18.28, 4.32, 0.0),
    171956: (105.0, 22.83, 0.86, 0.0),
}


def _first(text):
    r = MM.macros(text)
    return r["items"][0]


def test_every_sourced_row_equals_its_usda_record():
    for f in S.SOURCED_FOODS:
        assert f["fdc"] in USDA, f["n"]
        assert (f["cal"], f["p"], f["f"], f["c"]) == USDA[f["fdc"]], f["n"]
        assert f["safe"] == [], "sourced rows must carry no clinical safe flags"


def test_sourced_rows_are_not_in_the_public_food_table():
    import food_data
    names = {f["n"] for f in food_data.FOODS}
    for f in S.SOURCED_FOODS:
        assert f["n"] not in names or f["n"] in ("حليب كامل",), f["n"]


def test_whole_milk_is_whole_milk():
    for t in ("🥛 حليب كامل 200مل", "🥛 حليب كامل الدسم 200مل"):
        it = _first(t)
        assert it["food"] in ("حليب كامل", "حليب كامل الدسم"), it
        assert 120 <= it["cal"] <= 125, it  # 200 g x 61 kcal


def test_cheddar_is_not_cottage_cheese():
    it = _first("🧀 جبن شيدر 30جم")
    assert it["food"] == "جبن شيدر" and it["cal"] == round(0.3 * 410), it


def test_smoked_salmon_is_not_plain_salmon():
    it = _first("🐟 سلمون مدخن 80جم")
    assert it["food"] == "سلمون مدخن" and it["cal"] == round(0.8 * 117), it


def test_peanut_butter_is_not_butter():
    it = _first("🥜 زبدة فول 15جم")
    assert it["food"] == "زبدة فول سوداني", it
    assert _first("🧈 زبدة 10جم")["food"] == "زبدة"


def test_almond_milk_is_not_cow_milk_or_the_nut():
    it = _first("🥛 لبن لوز 200مل")
    assert "لوز" in it["food"] and it["cal"] < 60, it


def test_protein_is_not_a_fig():
    for t in ("💪 بروتين 30جم", "💪 بروتين"):
        assert _first(t)["food"] != "تين", t
    assert _first("🍇 تين 100جم")["food"] == "تين"


def test_prefixes_still_read():
    assert _first("🥣 شوفان بالحليب كامل الدسم 200مل") is not None
    assert MM.find_food("🥛 بحليب كامل 200مل") is not None


def test_cod_is_cod():
    it = _first("🐟 Baked Cod 150جم")
    assert it["food"] == "Baked Cod" and it["cal"] == round(1.5 * 105), it


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

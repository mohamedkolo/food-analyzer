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
    173414: (403.0, 22.87, 33.31, 3.37),
    173687: (117.0, 18.28, 4.32, 0.0),
    171956: (105.0, 22.83, 0.86, 0.0),
    168877: (365.0, 7.13, 0.66, 80.0),   # rice, white, long-grain, raw, enriched (FDC API 2026-11-27)
    169736: (371.0, 13.0, 1.51, 74.7),   # pasta, dry, enriched (FDC API 2026-11-27)
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
        assert it["cal"] == round(200 * 1.0314 * 0.61), it  # 244 g per US cup (USDA 01077)


def test_cheddar_is_not_cottage_cheese():
    it = _first("🧀 جبن شيدر 30جم")
    assert it["food"] == "جبن شيدر" and it["cal"] == round(0.3 * 403), it


def test_smoked_salmon_is_not_plain_salmon():
    it = _first("🐟 سلمون مدخن 80جم")
    assert it["food"] == "سلمون مدخن" and it["cal"] == round(0.8 * 117), it


def test_peanut_butter_is_not_butter():
    it = _first("🥜 زبدة فول 15جم")
    assert it["food"] == "زبدة فول سوداني", it
    assert _first("🧈 زبدة 10جم")["food"] == "زبدة"


def test_almond_milk_variant_is_not_guessed():
    r = MM.macros("🥛 لبن لوز 200مل")
    assert not r["complete"] and r["items"][0]["unresolved"].startswith("variant"), r
    r = MM.macros("🥛 لبن لوز غير محلى 200مل")
    assert r["complete"] and r["cal"] < 60, r


def test_incomplete_meal_is_never_trusted_as_a_total():
    text = "🥣 شوفان 80جم + 💪 بروتين 30جم + 🥛 لبن لوز 200مل"
    r = MM.macros(text)
    assert not r["complete"] and len(r["unresolved"]) == 2, r
    assert MM.trusted(text, MM.macros(text)["cal"]) is None


def test_fish_and_vegetables_title_is_not_resolved_as_cod_alone():
    r = MM.macros("🐟 Baked Cod & Veggies (سمك 150جم)")
    assert not r["complete"], r
    assert MM.macros("🐟 Baked Cod 150جم")["complete"]


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

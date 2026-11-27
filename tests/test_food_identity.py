# -*- coding: utf-8 -*-
"""Food identity, raw/cooked and unit guards in meal_macros.

Each case is a defect found by running meal_macros.macros() on ordinary
phrases (2026-11-27). A phrase either resolves to the right food and weight,
or is marked unresolved. It is never silently matched to a different food.
Run with:  python3 tests/test_food_identity.py
"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "k")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meal_macros as MM


def _one(text):
    r = MM.macros(text)
    return r, r["items"][0]


def test_raw_rice_is_not_cooked_rice():
    r, i = _one("100 جم أرز نيء")
    assert i["food"] == "أرز أبيض نيء" and r["cal"] == 365 and r["complete"], r
    r, i = _one("100 جم رز خام")
    assert r["cal"] == 365, r


def test_raw_pasta_is_not_cooked_pasta():
    r, i = _one("100 جم معكرونة نيئة")
    assert r["cal"] == 371 and r["complete"], r


def test_raw_form_of_a_food_without_a_raw_row_is_unresolved():
    r, i = _one("100 جم لحم بقري مشوي نيء")
    # unresolved either way; the identity check (state word missing from the row) may
    # fire before the raw/cooked guard, both leave the item unpriced
    assert (i.get("unresolved") or "").split(":")[0] in ("raw/cooked", "identity") and not r["complete"], r


def test_cooked_rice_still_resolves():
    r, i = _one("100 جم أرز مطبوخ")
    assert r["complete"] and 125 <= r["cal"] <= 135, r


def test_salmon_is_not_tilapia():
    r, i = _one("150 جم سمك سلمون مشوي")
    assert i["food"] == "سلمون", r


def test_unknown_fish_species_is_not_tilapia():
    r, i = _one("200 جم سمك بوري")
    assert (i.get("unresolved") or "").startswith(("variant:fish species", "identity:")) and not r["complete"], r


def test_named_tilapia_still_resolves():
    # the plain "سمك بلطي" row names no preparation, so under the cooked-weight rule it is
    # unresolved (with a reason), not priced; the cooked-named tilapia row is priced
    r, i = _one("150 جم سمك بلطي")
    assert i["food"] == "سمك بلطي" and (i.get("unresolved") or "").startswith("basis:"), r
    r, i = _one("150 جم سمك بلطى مشوى او بالفرن")
    assert r["complete"] and r["exact"], r


def test_toast_slice_is_not_a_loaf():
    r, i = _one("2 شريحة توست")
    assert i["grams"] == 50, r
    r, i = _one("شريحة خبز توست")
    assert (i.get("unresolved") or "").startswith(("unit", "identity:")) and not r["complete"], r


def test_sugar_in_tea_is_not_dropped():
    r, i = _one("شاي بسكر ملعقة")
    assert not r["complete"], r


def test_plain_milk_without_fat_level_is_unresolved():
    for text in ("كوب حليب", "200 مل حليب", "كوب لبن قليل الدسم"):
        r, i = _one(text)
        assert not r["complete"], (text, r)


def test_milk_with_a_stated_fat_level_uses_the_milk_rows():
    r, i = _one("كوب لبن كامل")
    assert i["food"] == "حليب كامل الدسم" and 140 <= r["cal"] <= 150, r
    r, i = _one("كوب لبن خالي الدسم")
    assert i["food"] == "حليب خالي الدسم", r


def test_a_qualified_dish_is_not_the_generic_row_it_starts_with():
    """Regression: "كفتة دجاج مشوية" was priced as the generic grilled kofta row
    (250 kcal, 18 g protein per 100 g) and counted as computed."""
    for text in ("🍗 كفتة دجاج مشوية 230جم", "🧀 جبن حلوم مشوي 50جم", "🍲 طاجين دجاج بالزيتون 150جم",
                 "🍗 شاورما دجاج 150جم", "🐟 سمك هامور 150جم"):
        r, i = _one(text)
        assert not r["complete"] and (i.get("unresolved") or "").split(":")[0] in ("identity", "dish"), (text, r)
    # the plain names still resolve
    for text in ("🍗 دجاج مشوى 150جم", "🥩 كفتة مشوية 150جم", "🍗 فروج مشوي 150جم", "🥗 سلطة كبيرة 150جم"):
        r, i = _one(text)
        assert r["complete"], (text, r)


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

# -*- coding: utf-8 -*-
"""The proposed-variant layer is a separate review layer: off by default, never original,
never exact, never verified. Run with:  python3 tests/test_proposed_layer.py
"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "k")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meal_macros as MM


def _with(flag, fn):
    old = os.environ.get("NX_PROPOSED_VARIANTS")
    if flag:
        os.environ["NX_PROPOSED_VARIANTS"] = "1"
    else:
        os.environ.pop("NX_PROPOSED_VARIANTS", None)
    try:
        return fn()
    finally:
        if old is None:
            os.environ.pop("NX_PROPOSED_VARIANTS", None)
        else:
            os.environ["NX_PROPOSED_VARIANTS"] = old


def test_off_by_default_nothing_changes():
    r = _with(False, lambda: MM.macros("30 جم جبنة"))
    i = r["items"][0]
    assert i["food"] == "جبن قريش" and not i.get("proposed") and not r["has_proposed"], r
    assert not r["exact"] and not r["exact_if_proposed"], r


def test_proposed_is_flagged_and_never_exact():
    r = _with(True, lambda: MM.macros("30 جم جبنة"))
    i = r["items"][0]
    assert i["proposed"] and i["original_food"] == "جبن قريش" and i["food"] == "جبن قريش كريمي (USDA cottage creamed)", i
    assert r["has_proposed"] and r["exact_if_proposed"] and not r["exact"], r
    assert i["cal"] == round(98.0 * 0.3), i                    # USDA 172182 value, copied


def test_a_missing_quantity_gets_the_usda_portion_labeled_proposed():
    r = _with(True, lambda: MM.macros("حمص مسلوق"))
    i = r["items"][0]
    assert i["proposed_qty"] and i["how"] == "proposed_default" and i["grams"] == 164.0, i
    assert not i["explicit_quantity"] and r["exact_if_proposed"] and not r["exact"], r


def test_original_exact_items_are_untouched_by_the_layer():
    for t in ("150 جم جبنة قريش", "2 بيضة", "200 جم دجاج مشوى"):
        a = _with(False, lambda: MM.macros(t))
        b = _with(True, lambda: MM.macros(t))
        assert (a["cal"], a["p"], a["exact"]) == (b["cal"], b["p"], b["exact"]) and not b["has_proposed"], t


def test_unresolved_items_stay_unresolved_under_the_layer():
    r = _with(True, lambda: MM.macros("150 جم طاجين دجاج بالزيتون"))
    assert not r["complete"] and not r["has_proposed"], r


def test_the_chicken_kofta_proxy_is_labeled_a_proxy_and_never_exact():
    r = _with(True, lambda: MM.macros("150 جم كفتة دجاج مشوية"))
    i = r["items"][0]
    assert i["proposed"] and i["proposed_kind"] == "proxy" and "بديل تقريبي" in i["food"], r
    # a proxy is in no source-matched level
    assert not r["exact"] and not r["exact_if_proposed"] and not r["exact_if_proposed_recipe"] and r["has_proxy"], r
    assert not _with(False, lambda: MM.macros("150 جم كفتة دجاج مشوية"))["complete"]


def test_the_salad_is_a_new_recipe_not_the_original_salad():
    r = _with(True, lambda: MM.macros("150 جم سلطة"))
    i = r["items"][0]
    assert i["proposed_kind"] == "new_recipe" and r["has_new_recipe"], r
    assert not r["exact"] and not r["exact_if_proposed"] and r["exact_if_proposed_recipe"], r


def test_generator_levels_are_flag_gated_and_exclude_proxies():
    import plan_engine
    env = dict(os.environ)
    try:
        os.environ.pop("NX_PROPOSED_VARIANTS", None)
        os.environ["NX_PROPOSED_LEVEL"] = "B"                # level alone does nothing without the flag
        assert plan_engine.computed_meal("150 جم سلطة") is None
        os.environ["NX_PROPOSED_VARIANTS"] = "1"
        os.environ["NX_PROPOSED_LEVEL"] = "A"
        assert plan_engine.computed_meal("150 جم سلطة") is None          # new recipe is not in level A
        assert plan_engine.computed_meal("150 جم جبنة") is not None      # source-matched variant is
        os.environ["NX_PROPOSED_LEVEL"] = "B"
        assert plan_engine.computed_meal("150 جم سلطة") is not None
        assert plan_engine.computed_meal("150 جم كفتة دجاج مشوية") is None   # proxy never
    finally:
        os.environ.clear()
        os.environ.update(env)


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

# -*- coding: utf-8 -*-
"""Exact generation: item arithmetic is the truth for NEW plans.

Acceptance criteria (these are the real checks, nothing looser is claimed):
  * every returned day is within 5% of ITS OWN kcal target (the cycling day
    target when cycling is on, otherwise the engine day total ~ goal_cal);
  * a week that cannot reach that is redrawn, then refused (TargetNotReachable);
  * every meal of a returned plan is complete (no unresolved item) and its
    item sum matches the written meal kcal (calc_check), keto included;
  * protein is steered to the existing protein_need basis (adjusted weight is
    preserved); protein within 15% is reported per day, not enforced;
  * unusable coverage gives a message through safe_generate, never a crash.

Run with:  python3 tests/test_exact_generation.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "k")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_exact_gen_test.db")

import app as A  # noqa: E402
import meal_macros  # noqa: E402
import plan_engine  # noqa: E402
import zigzag  # noqa: E402

BASE = {"name": "x", "age": "34", "gender": "ذكر", "height": "178",
        "weight": "93", "tdee": "2500", "goal_cal": "1800",
        "goal_type": "weight_loss", "culture": "مصري",
        "diet_plan_type": "standard", "symptoms": [], "allergies": [],
        "notes": "", "disliked_foods": "", "protein_per_kg": "1.6",
        "fat_pct_cal": "30", "zigzag_mode": "off", "user_id": 1,
        "activity": "1.55"}


def _plan(**over):
    d = dict(BASE, **over)
    d["zigzag"] = zigzag.zigzag_from_data(d)
    with A.app.test_request_context("/"):
        return d, plan_engine.generate_weekly_plan(d)


def _check_days(plan):
    for day in plan:
        ex = day["exact"]
        assert abs(ex["cal_dev_pct"]) <= 5, ex
        assert ex["within_tolerance"], ex
        cc = day["calc_check"]
        assert cc["complete"] and not cc["incomplete"], cc
        for slot, m in cc["meals"].items():
            assert m["complete"] and m["items_sum_ok"], (slot, m)


def test_standard_week_meets_tolerance_and_is_complete():
    _d, plan = _plan()
    _check_days(plan)


def test_keto_cannot_bypass_the_checks():
    _d, plan = _plan(diet_plan_type="keto")
    _check_days(plan)


def test_cycling_day_lands_on_its_own_target_not_the_engine_total():
    """Regression: finalize used the pre-finalize total, so a cycling day
    (target 3900) landed at 2317 while the old test allowance hid it."""
    _d, plan = _plan(goal_type="weight_loss", tdee="2200", goal_cal="1600",
                     zigzag_mode="strong")
    _check_days(plan)
    targets = {day["exact"]["target_cal"] for day in plan}
    assert len(targets) > 1, "cycling days should have different targets"
    assert any("cycling" in d["exact"]["kcal_target_source"] for d in plan)


def test_restrictions_still_give_checked_plan():
    _d, plan = _plan(disliked_foods="دجاج، سمك", goal_cal="2000")
    _check_days(plan)


def test_adjusted_weight_protein_basis_is_preserved():
    d, plan = _plan(weight="110", tdee="3000", goal_cal="2200",
                    symptoms=["سكري النوع الثاني"])
    basis = d["protein_basis"]
    assert basis.get("why") == "adjusted", basis
    assert basis["grams"] < 1.6 * 110 - 10, basis
    for day in plan:
        assert day["exact"]["target_p"] == int(round(basis["grams"]))
        assert "adjusted" in day["exact"]["protein_target_source"]


def test_excluded_foods_never_appear_in_a_returned_plan():
    """Minimal restriction regression: an excluded food is absent from every meal."""
    _d, plan = _plan(disliked_foods="دجاج، سمك", goal_cal="2000")
    for day in plan:
        for k in [k for k in day["meal_labels"] if isinstance(day.get(k), str)]:
            for w in ("دجاج", "سمك"):   # exclusion is by the written keyword (tuna/salmon are not synonyms in the engine)
                assert w not in day[k], (w, day[k])


def test_embedded_kcal_labels_are_not_stale():
    import re
    import exact_plan
    _d, plan = _plan()
    seen = 0
    for day in plan:
        for k in [k for k in day["meal_labels"] if isinstance(day.get(k), str)]:
            text = day[k]
            whole = exact_plan._totals({"m": text})["cal"]
            for seg in text.split(" + "):
                m = re.search(r"(\d+)\s*kcal", seg)
                if not m:
                    continue
                seen += 1
                it = exact_plan._item(seg)
                ok = abs(int(m.group(1)) - whole) <= 8 or (
                    it and abs(int(m.group(1)) - it["cal"]) <= 8)
                assert ok, (seg, whole)


def test_a_qualified_food_is_not_matched_to_a_nearest_food():
    for txt in ("🧀 جبن شيدر 40جم", "🥛 حليب كامل 200مل", "🍳 3 بيض مقلي بالزبدة",
                "🥬 محشي كوسة 6 قطع"):
        assert not meal_macros.macros(txt)["complete"], txt


def test_unreachable_or_uncovered_gives_a_message_not_a_crash():
    orig = meal_macros.verified_only

    def boom(meals, slot="", minimum=3):
        raise meal_macros.InsufficientVerifiedMeals(slot or "lunch", 1, 3)
    meal_macros.verified_only = boom
    try:
        with A.app.test_request_context("/"):
            plan, err = plan_engine.safe_generate(dict(BASE))
    finally:
        meal_macros.verified_only = orig
    assert plan is None and err, (plan, err)


def test_an_ambiguous_bread_count_is_never_resolved():
    r = meal_macros.macros("2 خبز أسمر")
    assert not r.get("complete", False) or r.get("unresolved"), r


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print("  PASS  " + name)
            passed += 1
        except Exception as e:  # noqa: BLE001
            print("  FAIL  %s\n        %s: %s" % (name, type(e).__name__, str(e)[:300]))
            failed += 1
    print("\n%d passed, %d failed" % (passed, failed))
    raise SystemExit(1 if failed else 0)

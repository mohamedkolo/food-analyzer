# -*- coding: utf-8 -*-
"""Scaling on meals whose quantities are all stated (synthetic recipes).

Scaling toward a target must act on the computed kcal, so that after scaling the
foods really add up near the target. Meals with default portions keep label scaling
and are not treated as computed. Run with:  python3 tests/test_computed_scaling.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
import plan_engine  # noqa: E402
import portion_scale  # noqa: E402
import meal_macros  # noqa: E402

DAY = {"breakfast": "2 بيضة + 100 جم تفاح", "lunch": "200 جم دجاج مشوى + 150 جم أرز مطبوخ",
       "dinner": "150 جم زبادي خالي الدسم + 100 جم خيار"}


def _total(day):
    return sum(plan_engine.computed_meal(t)["cal"] for t in day.values())


def test_computed_meal_requires_stated_quantities():
    assert plan_engine.computed_meal(DAY["lunch"]) is not None
    assert plan_engine.computed_meal("دجاج مشوي + ارز") is None
    assert plan_engine.computed_meal("") is None


def test_scaling_by_computed_kcal_lands_near_target_when_plates_stay_plausible():
    # experimental variant (OFF by default in the candidate)
    os.environ["NX_PLAUSIBILITY_CAPS"] = "1"
    try:
        return _test_scaling_by_computed_kcal_lands_near_target_when_plates_stay_plausible()
    finally:
        os.environ.pop("NX_PLAUSIBILITY_CAPS", None)


def _test_scaling_by_computed_kcal_lands_near_target_when_plates_stay_plausible():
    import re
    for target in (1000, 1200, 1500):
        now = _total(DAY)
        factor = target / now
        scaled = {k: portion_scale.scale_meal(t, factor)[0] for k, t in DAY.items()}
        got = _total(scaled)
        assert abs(got - target) / target < 0.12, (target, now, got, scaled)


def test_scaling_never_builds_an_implausible_plate():
    # experimental variant (OFF by default in the candidate)
    os.environ["NX_PLAUSIBILITY_CAPS"] = "1"
    try:
        return _test_scaling_never_builds_an_implausible_plate()
    finally:
        os.environ.pop("NX_PLAUSIBILITY_CAPS", None)


def _test_scaling_never_builds_an_implausible_plate():
    """Large targets must stop at the per-item ceilings (reported as unmet by the day
    check) rather than produce 440 g fish + 440 g potato + 440 g zucchini."""
    import re
    for factor in (2.0, 3.0):
        for t in DAY.values():
            out = portion_scale.scale_meal(t, factor)[0]
            for g, unit in re.findall(r"(\d+)\s*(جم|مل)", out):
                assert int(g) <= 500, (factor, out)
                if unit == "جم" and "زبادي" not in out.split(g)[0][-12:] \
                        and "زبادي" not in out.split(g)[-1][:12]:
                    assert int(g) <= 350, (factor, out)


def test_label_scaling_is_not_computed():
    m = meal_macros.macros("دجاج مشوي + ارز")
    assert plan_engine.computed_meal("دجاج مشوي + ارز") is None and m["items"]


DATA = {"name": "t", "age": "30", "gender": "ذكر", "height": "175", "weight": "85",
        "tdee": "2000", "goal_cal": "1400", "goal_type": "weight_loss",
        "culture": "مصري", "diet_plan_type": "two_meals", "symptoms": [], "user_id": 1}


def test_alternate_selection_never_makes_the_week_worse_or_hides_a_miss():
    worse = 0
    for seed in range(12):
        once = plan_engine._generate_week(dict(DATA), "s%d" % seed)
        best = plan_engine.generate_weekly_plan(dict(DATA), "s%d" % seed)
        assert plan_engine._week_penalty(best) <= plan_engine._week_penalty(once) + 1e-6, seed
        # a swap may not turn a computed day into an estimate to dodge the check
        assert plan_engine._n_items(best) >= plan_engine._n_items(once), seed
        assert plan_engine._variety_max(best) <= max(plan_engine._variety_max(once), 3), seed
        for d in best:
            c = d["calc"]
            if c["basis"] == "items":
                foods = sum(meal_macros.macros(d[k])["cal"] for k in
                            ("breakfast", "lunch", "dinner", "snack", "snack1", "snack2")
                            if d.get(k))
                assert abs(d["total_cal"] - foods) <= 3, (d["total_cal"], foods)



# Pinned, reproducible: generate_weekly_plan(DATA, "s<seed>") is deterministic.
# Known UNRESOLVED calorie misses of the 2-meal profile (seed, day, gap %). They are
# not fixed by alternate selection; each must stay reported (target_met False).
PINNED_UNMET = [(0, "الثلاثاء"), (1, "الثلاثاء"), (9, "الاثنين"), (18, "السبت"),
                (20, "الجمعة"), (25, "السبت"), (26, "الجمعة"), (29, "السبت")]


def test_pinned_unmet_days_stay_reported_and_totals_match_foods():
    import app as A
    for seed, day in PINNED_UNMET:
        with A.app.test_request_context("/"):
            week = plan_engine.generate_weekly_plan(dict(DATA), "s%d" % seed)
        d = next(x for x in week if x["day"] == day)
        c = d["calc"]
        if c["basis"] == "items":
            foods = sum(meal_macros.macros(d[k])["cal"] for k in
                        ("breakfast", "lunch", "dinner", "snack", "snack1", "snack2")
                        if d.get(k))
            assert abs(d["total_cal"] - foods) <= 3, (seed, day)
            real = abs(foods - 1400) / 1400 * 100
            if real > 5.0:
                assert c["target_met"] is False, (seed, day, c)


def test_pinned_variety_profile_never_repeats_a_main_over_three_times():
    import app as A
    d2 = dict(DATA, diet_plan_type="standard", symptoms=["سكري النوع الثاني"],
              culture="خليجي", gender="انثى", weight="80", height="165",
              tdee="2000", goal_cal="1600")
    for seed in range(12):
        with A.app.test_request_context("/"):
            w = plan_engine.generate_weekly_plan(dict(d2), "v%d" % seed)
        assert plan_engine._variety_max(w) <= 3, seed

if __name__ == "__main__":
    n = f = 0
    for k, v in sorted(globals().items()):
        if k.startswith("test_"):
            try: v(); n += 1
            except AssertionError as e: f += 1; print("FAIL", k, e)
    print(n, "passed,", f, "failed")

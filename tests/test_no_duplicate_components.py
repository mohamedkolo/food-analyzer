# -*- coding: utf-8 -*-
"""A meal must not get a protein top-up of the same food it already contains.
Pinned seeds, deterministic. Run with:  python3 tests/test_no_duplicate_components.py"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
import app as A  # noqa: E402
import plan_engine  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_computed_scaling as T  # noqa: E402

KEYS = ("دجاج", "تونة", "بياض", "سمك", "لحم")


def test_topup_never_repeats_a_protein_already_in_the_meal():
    for seed in range(15):
        for diet in ("standard", "two_meals"):
            data = dict(T.DATA, diet_plan_type=diet, goal_cal="1500", weight="95",
                        gender="انثى", zigzag_mode="strong")
            with A.app.test_request_context("/"):
                week = plan_engine.generate_weekly_plan(data, "d%d" % seed)
            for d in week:
                tu = d.get("protein_topup")
                if not tu:
                    continue
                text = d.get(tu["slot"]) or ""
                head, _, tail = text.rpartition(" + ")
                for k in KEYS:
                    if k in tu["source_ar"]:
                        assert k not in head, (seed, diet, d["day"], text)


def test_alternate_selection_never_repeats_a_whole_day_menu():
    """Regression: unmet-day alternates once produced identical Sunday/Tuesday menus."""
    for seed in range(30):
        with A.app.test_request_context("/"):
            week = plan_engine.generate_weekly_plan(dict(T.DATA), "d%d" % seed)
        assert plan_engine._repeated_days(week) == 0, seed


if __name__ == "__main__":
    n = f = 0
    for k, v in sorted(globals().items()):
        if k.startswith("test_"):
            try: v(); n += 1
            except AssertionError as e: f += 1; print("FAIL", k, e)
    print(n, "passed,", f, "failed")

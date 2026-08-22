# -*- coding: utf-8 -*-
"""A returning client is a second visit, not a first one.

The plan builder used to have no memory of anyone. These lock in the three
things that changed, and the bug the first version of them had.

FU-1  TDEE follows weight down. The activity factor is derived from the
      PREVIOUS visit's own numbers (the TDEE the doctor worked from, divided
      by the BMR of the weight they had then), not from the dropdown on the
      form. The first version used the dropdown, and because the doctor can
      type over the auto-calculated TDEE, it reported a HIGHER burn for a
      client who had just lost 4 kg -- telling the doctor the exact opposite
      of what happened.

FU-2  The same person spelled two ways is the same file. "أحمد على" and
      "احمد علي" differ only in hamza and alef-maqsura.

FU-3  A follow-up plan does not serve the week the client just finished.
"""

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import followup as fu  # noqa: E402

CLIENT = {
    "name": "أحمد على", "phone": "01012345678", "age": "32",
    "gender": "ذكر", "height": "176", "goal_type": "weight_loss",
    "activity": "1.55",
}


def _visit(weight, tdee, goal_cal, days_ago=30, **kw):
    v = dict(CLIENT, weight=weight, tdee=tdee, goal_cal=goal_cal)
    v["created_at"] = (dt.datetime.now() - dt.timedelta(days=days_ago)
                       ).strftime("%Y-%m-%d %H:%M:%S")
    v.update(kw)
    return v


def test_the_same_name_spelled_differently_is_one_file():
    spellings = ["أحمد على", "احمد علي", "أحـمد  عـلى", "احمد على "]
    keys = {fu.client_key(s, "01012345678") for s in spellings}
    assert len(keys) == 1, f"the same person produced {len(keys)} different files: {keys}"

    # a different phone is a different person, even with the same name
    assert fu.client_key("أحمد على", "01012345678") != fu.client_key("أحمد على", "01099999999")
    # no phone at all still yields a usable key
    assert fu.client_key("أحمد على") == fu.client_key("احمد علي")
    # and nothing usable yields nothing
    assert fu.client_key("") == ""
    assert fu.client_key(None) == ""


def test_tdee_falls_when_weight_falls():
    """FU-1. This is the whole point of a follow-up visit."""
    prev = _visit("95", "2350", "1750")
    got = fu.assess(prev, dict(CLIENT, weight="91"))

    assert got["new_tdee"] < got["old_tdee"], (
        f"client lost 4 kg but TDEE went from {got['old_tdee']} to {got['new_tdee']}")
    assert got["tdee_drop"] > 0
    # and it is derived from what the doctor actually used, not the dropdown
    assert 1.1 <= got["activity"] <= 2.1
    assert abs(got["activity"] - 2350 / fu.bmr_mifflin(95, 176, 32, "ذكر")) < 0.01


def test_a_hand_typed_tdee_beats_the_dropdown():
    """The doctor can type over the auto-calculated TDEE. When they do, the
    follow-up has to follow the number they used, not the factor on the form."""
    prev = _visit("95", "2350", "1750")           # implies ~1.24, not the 1.55 on the form
    got = fu.assess(prev, dict(CLIENT, weight="91", activity="1.55"))
    assert got["activity"] < 1.4, (
        f"the form's 1.55 overrode the doctor's own numbers (got {got['activity']})")
    assert got["new_tdee"] < 2350


def test_a_nonsense_previous_tdee_falls_back_to_the_factor():
    prev = _visit("95", "50", "1750")             # 50 kcal cannot be anyone's TDEE
    got = fu.assess(prev, dict(CLIENT, weight="91", activity="1.55"))
    assert got["activity"] == 1.55, "an impossible TDEE should not be trusted"


def test_each_verdict_comes_out_where_it_should():
    prev = _visit("95", "2350", "1750")
    cases = {
        "91":   "on_track",     # -0.93 kg/wk
        "93.5": "too_slow",     # -0.35
        "94.8": "plateau",      # -0.05
        "88":   "too_fast",     # -1.63
        "97":   "regained",
    }
    for weight, expected in cases.items():
        got = fu.assess(prev, dict(CLIENT, weight=weight))
        assert got["verdict"] == expected, (
            f"{weight} kg gave {got['verdict']}, expected {expected} (rate {got['rate']})")


def test_a_gaining_plan_reads_the_same_numbers_the_other_way():
    prev = _visit("70", "2600", "2900", goal_type="muscle_gain")
    gaining = dict(CLIENT, goal_type="muscle_gain")
    assert fu.assess(prev, dict(gaining, weight="71.2"))["verdict"] == "gain_on_track"
    assert fu.assess(prev, dict(gaining, weight="73"))["verdict"] == "gain_too_fast"
    assert fu.assess(prev, dict(gaining, weight="70.1"))["verdict"] == "gain_stalled"
    assert fu.assess(prev, dict(gaining, weight="68"))["verdict"] == "lost_on_gain"


def test_the_calorie_move_goes_the_right_way():
    prev = _visit("95", "2350", "1750")
    # losing too fast -> more food
    fast = fu.assess(prev, dict(CLIENT, weight="88"))
    assert fast["suggested_goal_cal"] > fast["old_goal_cal"]
    # stalled -> less food
    stuck = fu.assess(prev, dict(CLIENT, weight="94.8"))
    assert stuck["suggested_goal_cal"] < stuck["old_goal_cal"]
    # on track -> essentially unchanged apart from the TDEE drop
    ok = fu.assess(prev, dict(CLIENT, weight="91"))
    assert abs(ok["suggested_goal_cal"] - ok["old_goal_cal"]) <= 120


def test_one_visit_never_swings_the_plan_wildly():
    prev = _visit("95", "2350", "1750")
    for weight in ("80", "88", "91", "95", "99", "110"):
        got = fu.assess(prev, dict(CLIENT, weight=weight))
        assert abs(got["suggested_goal_cal"] - got["old_goal_cal"]) <= fu.MAX_STEP_KCAL, (
            f"{weight} kg moved the target by more than {fu.MAX_STEP_KCAL} kcal in one visit")


def test_the_suggestion_never_goes_below_the_safe_floor():
    # a small woman on an already-low target who has stalled
    prev = _visit("58", "1500", "1250", gender="انثى", height="158", age="41")
    woman = dict(CLIENT, gender="انثى", height="158", age="41")
    got = fu.assess(prev, dict(woman, weight="57.9"))
    assert got["suggested_goal_cal"] >= 1200, (
        f"suggested {got['suggested_goal_cal']} kcal, below the safe floor")


def test_a_visit_within_a_week_is_not_judged():
    prev = _visit("95", "2350", "1750", days_ago=3)
    got = fu.assess(prev, dict(CLIENT, weight="93"))
    assert got["verdict"] == "too_soon"
    assert got["step"] == 0, "a few days of water weight must not move the calories"
    # and it must not quietly suggest a new target either -- saying "this is
    # water, leave it alone" while proposing a different number contradicts itself
    assert got["suggested_goal_cal"] == got["old_goal_cal"]


def test_history_rows_measure_between_visits_not_from_today():
    """A stored visit compared to the one before it must use its own date."""
    first = _visit("95", "2350", "1750", days_ago=60)
    second = _visit("90", "2300", "1700", days_ago=30)
    got = fu.assess(first, second)
    assert got["days"] == 30, f"measured {got['days']} days between two visits 30 days apart"


def test_missing_or_broken_input_returns_nothing():
    assert fu.assess(None, dict(CLIENT, weight="90")) is None
    assert fu.assess(_visit("95", "2350", "1750"), {}) is None
    assert fu.assess(_visit("", "2350", "1750"), dict(CLIENT, weight="90")) is None
    assert fu.assess(_visit("95", "2350", "1750"), dict(CLIENT, weight="nonsense")) is None


def test_every_verdict_is_bilingual():
    for key, (ar, en, step) in fu.VERDICTS.items():
        assert ar.strip() and en.strip(), f"{key} is missing a language"
        assert isinstance(step, int), f"{key} has a non-integer calorie step"


def test_the_meals_of_a_plan_come_back_out():
    plan = [
        {"day": "الاحد", "breakfast": "بيض مسلوق 2", "lunch": "دجاج مشوي",
         "dinner": "زبادي", "snack": "تفاحة", "total_cal": 1200},
        {"day": "الاثنين", "meal1": "شوفان", "meal2": "سمك", "total_cal": 1100},
    ]
    got = fu.meals_in_plan(plan)
    assert "بيض مسلوق 2" in got and "شوفان" in got and "سمك" in got
    assert "الاحد" not in got and 1200 not in got
    assert fu.meals_in_plan([]) == []
    assert fu.meals_in_plan(None) == []
    assert fu.meals_in_plan(["not a dict"]) == []


def test_a_follow_up_plan_avoids_last_visits_meals():
    """FU-3. Coming back after a month and being handed the same week is the
    complaint this whole feature exists to answer."""
    os.environ.setdefault("SECRET_KEY", "test-key")
    from core import app  # noqa: E402
    from plan_engine import generate_weekly_plan  # noqa: E402

    data = {
        "name": "أحمد على", "age": "32", "gender": "ذكر", "height": "176",
        "weight": "95", "tdee": "2350", "goal_cal": "1750", "goal_type": "weight_loss",
        "culture": "مصري", "diet_plan_type": "standard", "symptoms": [],
        "allergies": [], "notes": "", "disliked_foods": "", "user_id": 1,
        "protein_per_kg": "1.8", "fat_pct_cal": "30", "zigzag_mode": "off",
    }
    with app.test_request_context("/"):
        first = generate_weekly_plan(data)
    eaten = fu.meals_in_plan(first)
    assert eaten, "the first plan produced no meals to avoid"

    with app.test_request_context("/"):
        second = generate_weekly_plan(dict(data, weight="91", avoid_meals=eaten))
    got = set(fu.meals_in_plan(second))
    fresh = len(got - set(eaten))
    ratio = fresh / max(len(got), 1)

    # Measured over 25 runs: without avoid_meals the second week comes back
    # 0% new at the median -- literally the same plan, which is the complaint
    # this feature exists to answer. With it, 46-71% new (median 57%).
    #
    # The floor is 40%, not "more new than repeated": the pool is finite and
    # medical filtering shrinks it further, so demanding a strict majority
    # puts the assertion right on the noise and the test flakes on a tie.
    assert ratio >= 0.40, (
        f"only {fresh} of {len(got)} meals ({ratio:.0%}) were new in the follow-up week")


def test_history_summary_spans_the_whole_journey():
    visits = [                       # newest first, the order the query returns
        {"weight": 88, "created_at": (dt.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")},
        {"weight": 91, "created_at": (dt.datetime.now() - dt.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")},
        {"weight": 95, "created_at": (dt.datetime.now() - dt.timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")},
    ]
    s = fu.summarise_history(visits)
    assert s["visits"] == 3
    assert s["first_weight"] == 95 and s["current_weight"] == 88
    assert s["total_change"] == -7
    assert s["days"] == 60
    assert fu.summarise_history([]) is None
    assert fu.summarise_history([{"weight": None}]) is None


def test_visits_are_recorded_and_numbered():
    os.environ.setdefault("SECRET_KEY", "test-key")
    os.environ.setdefault("ADMIN_PASSWORD", "Test12345!")
    import app as A  # noqa: E402
    from core import last_visit, record_visit, recent_clients, visits_for  # noqa: E402

    data = dict(CLIENT, weight="95", tdee="2350", goal_cal="1750",
                symptoms=["سكري النوع الثاني"], diet_plan_type="standard")
    plan = [{"day": "الاحد", "breakfast": "بيض مسلوق 2", "total_cal": 1200}]

    with A.app.test_request_context("/"):
        assert record_visit(7, data, plan) == 1
        assert record_visit(7, dict(data, weight="91"), plan) == 2
        assert record_visit(7, dict(data, weight="88"), plan) == 3

    key = fu.client_key(CLIENT["name"], CLIENT["phone"])
    rows = visits_for(7, key)
    assert len(rows) == 3
    assert [r["visit_no"] for r in rows] == [3, 2, 1], "visits came back in the wrong order"
    assert float(last_visit(7, key)["weight"]) == 88.0

    # another doctor's clients are not visible
    assert visits_for(8, key) == []
    # a nameless client is not filed at all
    with A.app.test_request_context("/"):
        assert record_visit(7, dict(data, name="", phone=""), plan) is None

    names = [c["client_name"] for c in recent_clients(7)]
    assert CLIENT["name"] in names


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

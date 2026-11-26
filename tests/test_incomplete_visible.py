# -*- coding: utf-8 -*-
"""A meal with an unresolved item must not look item-computed.

day_progress used to take the partial sums of such meals as proportions and
the page looked normal. Now the basis is reported ("items" or "even_split"),
the meals at fault are listed, and the page says so. Saved plans and targets
are untouched.

Run with:  python3 tests/test_incomplete_visible.py
"""
import json
import os
import re
import sys
from datetime import datetime

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_incomplete_visible.db"
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A  # noqa: E402
import day_progress as DP  # noqa: E402
import meal_macros as MM  # noqa: E402
import plan_tools as PT  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
KEYS = ["breakfast", "lunch", "dinner"]
LABELS = {"breakfast": "B", "lunch": "L", "dinner": "D"}
GOOD = {"day": "x", "breakfast": "بيض مسلوق 2 + جبن قريش 100جم",
        "lunch": "صدر دجاج مشوي 200جم + أرز أبيض مطبوخ 150جم",
        "dinner": "زبادي 150جم + جبن قريش 100جم",
        "total_cal": 1500, "total_p": 110, "total_c": 120, "total_f": 40}
BAD = dict(GOOD, breakfast="🥞 بغرير 5 + جبن قريش 100جم")


def _b(day):
    return DP.build(day, KEYS, set(KEYS), set(), LABELS, is_ar=True, hour=13)


def test_the_fixture_is_what_it_claims_to_be():
    assert all(MM.macros(GOOD[k])["complete"] for k in KEYS)
    assert not MM.macros(BAD["breakfast"])["complete"]


def test_complete_day_is_item_based():
    r = _b(GOOD)
    assert r["basis"] == "items" and r["incomplete_meals"] == []


def test_incomplete_meal_switches_to_a_declared_even_split():
    r = _b(BAD)
    assert r["basis"] == "even_split" and r["incomplete_meals"] == ["breakfast"], r
    cals = [r["meals"][k]["cal"] for k in KEYS]
    assert max(cals) - min(cals) <= 1, cals          # not driven by partial sums
    assert sum(cals) == 1500                          # target unchanged
    assert r["target"]["cal"] == 1500


def test_no_most_protein_meal_hint_from_an_even_split():
    day = dict(BAD)
    r = DP.build(day, KEYS, set(), set(), LABELS, is_ar=False, hour=13)
    assert r["basis"] == "even_split"
    assert not any("the most protein left" in h for h in r["hints"]), r["hints"]


def test_week_marks_approximate_days():
    plan = [BAD] * 7
    import datetime as dt
    today = dt.date(2026, 11, 26)
    w = DP.week(plan, KEYS, LABELS, {today.isoformat(): set(KEYS)}, {}, today)
    assert w["days"][-1]["approx"] is True


def test_swap_estimate_is_flagged_when_the_new_meal_is_incomplete():
    day = {"total_cal": 1500, "total_p": 110}
    st = PT.apply_change({}, day, GOOD["lunch"], BAD["breakfast"])
    assert st["estimated"] is True, st
    day = {"total_cal": 1500, "total_p": 110}
    st = PT.apply_change({}, day, GOOD["lunch"], GOOD["dinner"])
    assert st["estimated"] is False, st


def _client(email, day):
    A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) VALUES (?,?,?,'client',1,?)",
             ("R", email, generate_password_hash("pw123456"), datetime.now()))
    uid = A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]
    plan = {"plan": [day] * 7, "data": {"diet_plan_type": "standard"}}
    A.db_run("INSERT INTO plan_requests (client_id,client_name,status,plan_data,updated_at) VALUES (?,?,'approved',?,?)",
             (uid, "R", json.dumps(plan), datetime.now()))
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = uid
        s["lang"] = "ar"
    return c


def _note(html):
    m = re.search(r'<p class="dp-note" id="dpNote"([^>]*)>', html)
    assert m, "note element missing"
    return "hidden" not in m.group(1)


def test_page_shows_the_note_only_when_a_meal_is_incomplete():
    good = _client("g@x.test", GOOD)
    bad = _client("b@x.test", BAD)
    pg = good.get("/my-plan").get_data(as_text=True)
    pb = bad.get("/my-plan").get_data(as_text=True)
    assert 'id="dpBox"' in pg and 'id="dpBox"' in pb
    assert _note(pb) is True and _note(pg) is False
    assert bad.get("/my-plan/progress").get_json()["basis"] == "even_split"


def test_even_split_never_says_kcal_or_protein_left():
    r = DP.build(BAD, KEYS, set(), set(), LABELS, is_ar=False, hour=13)
    text = " ".join(r["hints"])
    assert "Meals left" in text and "not calculated from the foods" in text, text
    assert not re.search(r"\d+ kcal|\d+ g protein", text), text
    ar = " ".join(DP.build(BAD, KEYS, set(), set(), LABELS, is_ar=True, hour=13)["hints"])
    assert "فاضلك" not in ar and "مش محسوبة من الأصناف" in ar, ar
    assert r["meals_done"] == 0 and r["meals_total"] == 3


def test_page_replaces_rings_with_a_plan_meal_counter():
    bad = _client("c@x.test", BAD)
    bad.post("/track/meal", data={"meal_key": "lunch", "checked": "1"})
    html = bad.get("/my-plan").get_data(as_text=True)
    assert 'id="dpPlan"' in html and 'data-done="1"' in html and 'data-total="3"' in html
    assert 'class="dp-rings"' not in html and 'class="dp-ring"' not in html
    good = _client("d@x.test", GOOD).get("/my-plan").get_data(as_text=True)
    assert 'id="dpPlan"' not in good and 'class="dp-rings"' in good


def test_week_incomplete_day_reports_meals_not_nutrition():
    import datetime as dt
    today = dt.date(2026, 11, 26)
    plan = [BAD] * 7
    iso = today.isoformat()
    w = DP.week(plan, KEYS, LABELS, {iso: {"lunch"}}, {}, today)
    d = w["days"][-1]
    assert d["approx"] and d["cal"] == 0 and d["cal_target"] == 0, d
    assert (d["meals_done"], d["meals_total"]) == (1, 3)
    assert w["this"]["cal_pct"] is None and w["this"]["p_pct"] is None   # no aggregate of unlike quantities
    assert w["delta"] is None


def test_mixed_week_aggregates_only_calculated_days():
    import datetime as dt
    today = dt.date(2026, 11, 26)
    yday = today - dt.timedelta(days=1)
    plan = [GOOD] * 7
    plan[(today.weekday() + 1) % 7] = BAD       # today incomplete, yesterday complete
    w = DP.week(plan, KEYS, LABELS, {today.isoformat(): {"lunch"}, yday.isoformat(): set(KEYS)}, {}, today)
    assert w["days"][-1]["approx"] and not w["days"][-2]["approx"]
    # 6 calculated days in the window (today excluded): 1500 eaten of 6*1500
    # targets = 17%. Counting today too would give 14% (7 targets).
    assert w["this"]["cal_pct"] == 17, w["this"]
    assert w["this"]["approx_days"] == 1


def test_week_page_labels_meal_days_as_meals_and_not_percent():
    bad = _client("e@x.test", BAD)
    bad.post("/track/meal", data={"meal_key": "lunch", "checked": "1"})
    html = bad.get("/my-plan").get_data(as_text=True)
    assert 'id="wkApprox"' in html and 'data-approx="1"' in html
    assert re.search(r'wk-meals[^>]*data-approx="1"[^>]*>\s*<span class="wk-v"><bdi dir="ltr">1/3</bdi>', html), "meals label"
    assert "~" not in re.search(r'id="wkCompare".*?</div>\s*</div>', html, re.S).group(0)
    assert "No fully" in html or "مفيش يوم حسابه كامل" in html
    good = _client("f@x.test", GOOD)
    good.post("/track/meal", data={"meal_key": "lunch", "checked": "1"})
    gh = good.get("/my-plan").get_data(as_text=True)
    assert 'id="wkApprox"' not in gh and 'data-approx="1"' not in gh


def test_shopping_list_never_lists_an_unresolved_guess():
    import shopping_list as SL
    plan = [dict(day="x", breakfast="لبن لوز 200 مل + تفاحة 1")]
    out = SL.build(plan, "ar") if hasattr(SL, "build") else None
    names = [i["name"] for g in out["groups"] for i in g["items"]]
    assert not any("لوز" in n for n in names), names
    assert any("لبن لوز" in u["name"] for u in out["unknown"]), out["unknown"]
    assert any("تفاح" in n for n in names), names


def test_portion_scale_gives_no_calories_for_an_unresolved_item():
    import portion_scale as PS
    assert PS._item_cal("لبن لوز 200 مل") is None
    assert PS._item_cal("تفاحة 180جم") is not None


def test_snack_option_with_partial_sum_has_no_numbers():
    import routes_plans as RP
    import plan_engine
    orig = plan_engine.snack_queue
    plan_engine.snack_queue = lambda data: ["لبن لوز 200 مل", "تفاحة 1"]
    try:
        out = RP._snack_options({})
    finally:
        plan_engine.snack_queue = orig
    by = {o["meal"]: o for o in out}
    assert by["لبن لوز 200 مل"]["cal"] is None and by["لبن لوز 200 مل"]["incomplete"] is True
    assert by["تفاحة 1"]["cal"] and by["تفاحة 1"]["incomplete"] is False


def test_fatta_dish_is_not_resolved_from_one_ingredient():
    r = MM.macros("فتة حمص كبيرة 250جم")
    assert r["complete"] is False and r["items"][0]["unresolved"] == "dish", r
    assert MM.macros("حمص مسلوق 250جم")["complete"] is True


def test_named_dishes_and_vegetable_dishes_are_not_one_ingredient():
    for text in ("شاورما دجاج 150جم", "مندي دجاج 150جم", "بيض بالخضار 2", "بيض مع الطماطم 2",
                 "كفتة بالصينية 150جم", "طاجين دجاج بالخضار 150جم"):
        r = MM.macros(text)
        assert r["complete"] is False, (text, r["items"])
    # dishes the table holds under their own name still resolve
    assert MM.macros("كبسة دجاج 150جم")["complete"] is True


if __name__ == "__main__":
    tests = [(n, f) for n, f in list(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, "--", repr(e)[:300])
    print("\n%d passed, %d failed" % (len(tests) - failed, failed))
    sys.exit(1 if failed else 0)

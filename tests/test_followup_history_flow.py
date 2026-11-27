# -*- coding: utf-8 -*-
"""The next program for a returning client is built from ALL earlier visits.

The doctor's request: when a program is made for someone already registered,
the earlier schedules are analysed and the new one continues from them.

What this locks in, end to end through /generate and /preview with a
fictional client (no real patient data):

  * every earlier interval is read, and a stall that repeats says so;
  * the new plan avoids the meals of the last three plans, not only one;
  * the result is a draft: nothing is saved or recorded until the doctor asks.

Run with:  python3 tests/test_followup_history_flow.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_history_flow_test.db"
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

import app as A  # noqa: E402
import core  # noqa: E402
import followup  # noqa: E402
from plan_engine import generate_weekly_plan  # noqa: E402

DEMO = {"name": "عميل تجريبي", "phone": "0100%07d" % (os.getpid() % 10000000), "age": "34",
        "gender": "ذكر", "height": "178", "fat_pct": "", "tdee": "2500",
        "goal_cal": "1800", "activity_mult": "1.55", "goal_type": "weight_loss",
        "diet_plan_type": "standard", "culture": "مصري",
        "protein_per_kg": "1.6", "fat_pct_cal": "30", "zigzag_mode": "off"}


def _staff():
    A.app.config["WTF_CSRF_ENABLED"] = False
    # A shared DB (batch runs) may carry lockouts / a changed admin from other test
    # files; this file only needs the seeded staff login to work.
    # (the first test file to create the admin on a shared DB fixes its password)
    core.db_run("UPDATE users SET password=?, active=1 WHERE email=?",
                (core.hp("pw123456"), "admin@nutrax.com"))
    A._clear_login_attempts("admin@nutrax.com")
    try:
        core.db_run("DELETE FROM blocked_users WHERE email=?", ("admin@nutrax.com",))
    except Exception:
        pass
    c = A.app.test_client()
    page = c.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', page).group(1)
    c.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                           "password": "pw123456", "csrf_token": token})
    return c


def _seed():
    """Three earlier visits, 84/56/28 days ago: 96 -> 93.2 -> 93 kg."""
    uid = core.db_row("SELECT id FROM users WHERE email=?", ("admin@nutrax.com",))["id"]
    # clean fixture: drop any earlier rows of this client (re-runs on a reused DB)
    core.db_run("DELETE FROM plan_visits WHERE user_id=? AND client_key=?",
                (uid, followup.client_key(DEMO["name"], DEMO["phone"])))
    plans = []
    with A.app.test_request_context("/"):
        for w, days in (("96", 84), ("93.2", 56), ("93", 28)):
            data = dict(DEMO, weight=w, symptoms=[], allergies=[], notes="",
                        disliked_foods="", user_id=uid)
            plan = generate_weekly_plan(dict(data))
            plans.append(plan)
            core.record_visit(uid, data, plan)
            # computed in Python so the same statement runs on SQLite and Postgres
            import datetime as _dt
            _ts = (_dt.datetime.now() - _dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            core.db_run("UPDATE plan_visits SET created_at=? "
                        "WHERE id=(SELECT MAX(id) FROM plan_visits)", (_ts,))
    return uid, plans


def _counts(uid):
    # this test's own client only: other test files share the admin user and the DB
    key = followup.client_key(DEMO["name"], DEMO["phone"])
    return (core.db_row("SELECT COUNT(*) c FROM plan_visits WHERE user_id=? AND client_key=?",
                        (uid, key))["c"],
            core.db_row("SELECT COUNT(*) c FROM saved_plans WHERE user_id=?", (uid,))["c"])


def test_the_next_program_reads_the_whole_history_and_stays_a_draft():
    uid, plans = _seed()
    before = _counts(uid)
    assert before[0] == 3
    c = _staff()
    r = c.post("/generate", data=dict(DEMO, weight="93"))
    assert r.status_code in (302, 303), r.status_code
    html = c.get("/preview").get_data(as_text=True)

    assert 'id="fuHistory"' in html, "the history panel is missing from the preview"
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    assert "متابعة رقم 4" in text
    # two stalled intervals in a row are named, with the count
    assert "2 فترات ورا بعض" in html and "مش دليل على السبب" in html
    assert "قرأنا 3 من 3" in text.replace("  ", " ")
    # meals of three earlier plans, not one
    assert "من آخر 3 خطط" in text and "تأخير مش منع" in text
    # all three earlier plans are inside the avoid list that was used
    rows = core.visits_for(uid, followup.client_key(DEMO["name"], DEMO["phone"]), limit=6)
    avoid = set(followup.meals_across_plans(rows, 3))
    import json
    for v in rows:
        assert set(followup.meals_in_plan(json.loads(v["plan_json"]))) <= avoid

    # a draft: no visit and no saved plan was created by generating
    assert _counts(uid) == before



if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); passed += 1; print("  PASS ", name)
            except Exception as e:
                import traceback; traceback.print_exc()
                failed += 1; print("  FAIL ", name, e)
    print("\n%d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)

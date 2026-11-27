# -*- coding: utf-8 -*-
"""‏"أسبوعك" في خطتي: رسم آخر ٧ أيام، ومقارنة بالأسبوع اللي فات.

‏كل يوم: المتاكل قصاد المستهدف من خطة الدكتور، بنفس حساب دواير النهارده
(day_progress.build)، فالرقم اللي العميل شافه يوم الاتنين هو نفس عمود
الاتنين في الرسم.

Run with:  python3 tests/test_week_progress.py
"""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_week_progress.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A              # noqa: E402
import day_progress as DP    # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
ARABIC = re.compile(r"[؀-ۿ]")

DAY = {"breakfast": "بيض مسلوق 2 + عيش بلدي 1 رغيف", "lunch": "دجاج مشوى 200جم + أرز أبيض مطبوخ 150جم",
       "dinner": "جبن قريش 100جم", "total_cal": 1500, "total_p": 120, "total_c": 140, "total_f": 45}
KEYS = ["breakfast", "lunch", "dinner"]
LABELS = {k: k for k in KEYS}
TODAY = date(2026, 3, 15)


def _week(checks, skips=None):
    return DP.week([DAY] * 7, KEYS, LABELS, checks, skips or {}, TODAY)


def _iso(n):
    return (TODAY - timedelta(days=n)).isoformat()


def test_fourteen_days_newest_last():
    w = _week({})
    assert len(w["days"]) == 14
    assert w["days"][-1]["date"] == TODAY.isoformat()
    assert w["days"][0]["date"] == _iso(13)


def test_a_full_day_eats_the_whole_target():
    w = _week({_iso(0): set(KEYS)})
    d = w["days"][-1]
    assert d["cal"] == d["cal_target"] == 1500 and d["p"] == d["p_target"] == 120


def test_a_day_matches_todays_rings():
    checked = {"breakfast", "lunch"}
    w = _week({_iso(0): checked})
    ring = DP.build(DAY, KEYS, checked, set(), LABELS, hour=12)
    assert w["days"][-1]["cal"] == ring["eaten"]["cal"]
    assert w["days"][-1]["p"] == ring["eaten"]["p"]


def test_this_week_versus_last_week():
    checks = {_iso(n): set(KEYS) for n in range(7)}            # ‏الأسبوع ده كامل
    checks.update({_iso(n): {"breakfast"} for n in range(7, 14)})  # ‏اللي فات: فطار بس
    w = _week(checks)
    assert w["this"]["cal_pct"] == 100
    assert 0 < w["last"]["cal_pct"] < 50
    assert w["delta"]["cal_pct"] == w["this"]["cal_pct"] - w["last"]["cal_pct"]
    assert w["this"]["days_logged"] == 7


def test_skipped_meals_do_not_count():
    w = _week({_iso(0): {"breakfast"}}, {_iso(0): {"breakfast"}})
    assert w["days"][-1]["cal"] == 0


def test_an_empty_last_week_has_no_comparison():
    w = _week({_iso(0): set(KEYS)})
    assert w["last"]["days_logged"] == 0 and w["delta"] is None


# ═══ الصفحة ═══

def _client():
    A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) VALUES (?,?,?,'client',1,?)",
             ("Hala", "hala@x.test", generate_password_hash("pw123456"), datetime.now()))
    uid = A.db_row("SELECT id FROM users WHERE email='hala@x.test'")["id"]
    A.db_run("INSERT INTO plan_requests (client_id,client_name,status,plan_data,updated_at) VALUES (?,?,'approved',?,?)",
             (uid, "Hala", json.dumps({"plan": [DAY] * 7, "data": {"diet_plan_type": "standard"}}), datetime.now()))
    today = A.client_now().date()
    for n in range(10):
        for k in KEYS[: (n % 3) + 1]:
            A.db_run("INSERT INTO meal_checks (user_id,check_date,meal_key) VALUES (?,?,?)",
                     (uid, today - timedelta(days=n), k))
    return uid


UID = _client()


def _page(lang="ar"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = UID
        s["lang"] = lang
    return c.get("/my-plan").get_data(as_text=True)


def test_my_plan_no_longer_shows_the_week_card():
    """‏الدكتور (٢٦ نوفمبر): صفحة العميل أربع وجهات بس — كارت «أسبوعك»
    ‏اتشال من الرئيسية. حساب الأسبوع نفسه محفوظ في week_progress."""
    html = _page()
    assert 'id="wkCard"' not in html
    assert 'data-wk-metric' not in html


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

# -*- coding: utf-8 -*-
"""‏سرعة الموقع: عدد الاستعلامات مش لازم يكبر مع عدد العملاء.

‏صاحب المشروع قال إن الموقع تقيل. القياس على ١٢٠ عميل بخطة وشهر علامات:

  ‏- لوحة الأدمن: **٨٦٦ استعلام** في الزيارة الواحدة. "محتاجين متابعة"
    و"أبطال الالتزام" كانوا بيحسبوا كل عميل لوحده (٣-٦ استعلامات للعميل).
    على Neon كل استعلام رحلة شبكة (~٢٠-٥٠ ms)، يعني ١٥-٤٠ ثانية.
  ‏- السيرفر كان شغّال بـgunicorn من غير إعدادات = عامل واحد بخيط واحد،
    فطلب واحد بطيء بيوقّف كل الزوار وراه، حتى ملفات الـCSS.
  ‏- كل صفحة كانت بتجيب نفس المستخدم ٣-٤ مرات.

Run with:  python3 tests/test_speed.py
"""

import json
import os
import runpy
import sys
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_speed.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app as A      # noqa: E402
import core          # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
ADMIN = A.db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")["id"]
PW = generate_password_hash("pw123456")
TODAY = A.client_now().date()

PLAN4 = {"plan": [{"breakfast": "بيض", "lunch": "فراخ", "dinner": "زبادي", "snack": "تفاح"}] * 7,
         "data": {"diet_plan_type": "standard"}}
PLAN2 = {"plan": [{"breakfast": "بيض", "lunch": "فراخ"}] * 7,
         "data": {"diet_plan_type": "standard"}}

_n = [0]


def _client(pattern, plan=PLAN4, tz="Africa/Cairo", days=40):
    """عميل بخطة وعلامات: pattern(d) بترجع الوجبات اللي اتعلّم عليها من 'd' يوم."""
    _n[0] += 1
    email = "s%d@x.test" % _n[0]
    A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at,timezone)"
             " VALUES (?,?,?,'client',1,?,?)", ("S%d" % _n[0], email, PW, datetime.now(), tz))
    uid = A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]
    if plan is not None:
        A.db_run("INSERT INTO plan_requests (client_id,client_name,status,plan_data,updated_at)"
                 " VALUES (?,?,'approved',?,?)", (uid, "S", json.dumps(plan), datetime.now()))
    for d in range(days):
        for k in pattern(d):
            A.db_run("INSERT INTO meal_checks (user_id,check_date,meal_key) VALUES (?,?,?)",
                     (uid, TODAY - timedelta(days=d), k))
    return uid


ALL4 = ["breakfast", "lunch", "dinner", "snack"]
CLIENTS = [
    _client(lambda d: ALL4),                                  # ‏ملتزم كل يوم
    _client(lambda d: ALL4 if d else []),                     # ‏النهارده لسه
    _client(lambda d: ALL4 if d % 5 else ALL4[:2]),           # ‏بيقطع كل ٥ أيام
    _client(lambda d: ALL4[: d % 4]),                         # ‏متلخبط
    _client(lambda d: []),                                    # ‏مابيعلّمش
    _client(lambda d: ALL4, plan=None),                       # ‏من غير خطة
    _client(lambda d: ["breakfast", "lunch"], plan=PLAN2),    # ‏خطة وجبتين
    _client(lambda d: ALL4, tz="Asia/Dubai"),                 # ‏منطقة تانية
    _client(lambda d: ALL4 if 2 < d < 20 else []),            # ‏التزام قديم
]


class _Count:
    def __enter__(self):
        self.n, self.orig = 0, core.get_db

        def counting():
            self.n += 1
            return self.orig()
        core.get_db = counting
        return self

    def __exit__(self, *a):
        core.get_db = self.orig


def _as(uid):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = uid
    return c


# ═══ ١) السيرفر بيخدم كذا طلب في نفس الوقت ═══

def test_gunicorn_serves_several_requests_at_once():
    path = os.path.join(ROOT, "gunicorn.conf.py")
    assert os.path.exists(path), "gunicorn.conf.py مش موجود"
    conf = runpy.run_path(path)
    assert conf.get("threads", 1) >= 4, conf.get("threads")
    assert conf.get("worker_class") == "gthread", conf.get("worker_class")
    # ‏عامل واحد بالقصد: حد محاولات الدخول في الذاكرة، ولفّات التذكير
    # بتتشغّل مع كل عامل -- عاملين = كل تذكير بيوصل مرتين.
    assert conf.get("workers") == 1, conf.get("workers")


# ═══ ٢) لوحة الأدمن بعدد استعلامات ثابت ═══

def test_bulk_stats_match_the_per_client_numbers_exactly():
    stats = A.bulk_client_stats()
    for uid in CLIENTS:
        one = A.get_meal_tracking(uid)
        streak = A.get_meal_streak(uid)
        got = stats.get(uid, {})
        assert got.get("has_plan", False) == one["has_plan"], (uid, got, one)
        assert got.get("week_pct") == one["week_pct"], (uid, got.get("week_pct"), one["week_pct"])
        assert got.get("current_streak", 0) == streak["current_streak"], (uid, got, streak)
        assert got.get("best_streak", 0) == streak["best_streak"], (uid, got, streak)


def test_at_risk_list_is_unchanged():
    old = []
    for uid in CLIENTS:
        t = A.get_meal_tracking(uid)
        if t["has_plan"] and t["week_pct"] is not None and t["week_pct"] < 40:
            old.append((uid, t["week_pct"]))
    old.sort(key=lambda x: x[1])
    assert [(c["id"], c["week_pct"]) for c in A.get_at_risk_clients()] == old[:10]


def test_dashboard_queries_do_not_grow_with_clients():
    c = _as(ADMIN)
    c.get("/dashboard")
    with _Count() as before:
        c.get("/dashboard")
    for _ in range(15):
        _client(lambda d: ALL4[: d % 3])
    with _Count() as after:
        c.get("/dashboard")
    assert after.n == before.n, (before.n, after.n)
    assert after.n <= 30, after.n


# ═══ ٣) المستخدم بيتجاب مرة واحدة في الطلب ═══

def test_the_same_user_is_read_once_per_request():
    with A.app.test_request_context("/"):
        with _Count() as q:
            a = core.get_user_by_id(ADMIN)
            b = core.get_user_by_id(ADMIN)
        assert q.n == 1, q.n
        assert a == b and a is not b       # ‏نسخة، علشان محدش يعدّل في الكاش


def test_a_change_to_users_is_seen_in_the_same_request():
    with A.app.test_request_context("/"):
        core.get_user_by_id(ADMIN)
        A.db_run("UPDATE users SET name=? WHERE id=?", ("Renamed", ADMIN))
        assert core.get_user_by_id(ADMIN)["name"] == "Renamed"
        A.db_run("UPDATE users SET name=? WHERE id=?", ("Admin", ADMIN))


def test_background_jobs_are_never_cached():
    # ‏لفّات التذكير شغّالة برّه أي طلب -- لازم تقرا من القاعدة كل مرة.
    with _Count() as q:
        core.get_user_by_id(ADMIN)
        core.get_user_by_id(ADMIN)
    assert q.n == 2, q.n


def test_an_ordinary_page_reads_the_user_once():
    c = _as(ADMIN)
    with _Count() as q:
        c.get("/patients")
    assert q.n <= 8, q.n


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

# -*- coding: utf-8 -*-
"""‏لوحة الأدمن الجديدة: تحية، وتابين "نظرة عامة" و"الإدارة".

‏كل الأرقام من الجداول الحقيقية -- مفيش أرقام وهمية. ومفيش حاجة من
اللوحة القديمة اتشالت: نفس الأرقام والروابط، بس متقسّمة على تابين.

Run with:  python3 tests/test_admin_dashboard.py
"""

import os
import re
import sys
from datetime import date, datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_admin_dashboard.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A                 # noqa: E402
import booking as B             # noqa: E402
import dashboard_data as D      # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
ARABIC = re.compile(r"[؀-ۿ]")

ADMIN = A.db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")["id"]


def _mk(email, name):
    A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at)"
             " VALUES (?,?,?,'client',1,?)",
             (name, email, generate_password_hash("pw123456"), datetime.now()))
    return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]


SARA = _mk("sara@d.test", "Sara")
OMAR = _mk("omar@d.test", "Omar")


def _tick(uid, day, key):
    A.db_run("INSERT INTO meal_checks (user_id, check_date, meal_key) VALUES (?,?,?)",
             (uid, day, key))


def _as(uid, lang="ar"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = uid
        s["lang"] = lang
    return c


# ═══ الحسابات ═══

def test_greeting_follows_the_clock():
    assert D.greeting(datetime(2026, 1, 1, 8), True) == "صباح الخير"
    assert D.greeting(datetime(2026, 1, 1, 14), True) == "مساء الخير"
    assert D.greeting(datetime(2026, 1, 1, 22), False) == "Good evening"
    assert D.greeting(datetime(2026, 1, 1, 9), False) == "Good morning"
    assert D.greeting(datetime(2026, 1, 1, 15), False) == "Good afternoon"


def test_week_counts_clients_not_ticks():
    A.db_run("DELETE FROM meal_checks")
    today = date(2026, 3, 10)
    _tick(SARA, today, "breakfast")
    _tick(SARA, today, "lunch")          # ‏نفس العميل مرتين = واحد
    _tick(OMAR, today, "dinner")
    _tick(OMAR, today - timedelta(days=2), "lunch")
    _tick(OMAR, today - timedelta(days=9), "lunch")   # ‏برّه الأسبوع
    week = D.clients_logging_week(A.db_rows, today)
    assert [d["count"] for d in week] == [0, 0, 0, 0, 1, 0, 2]
    assert week[-1]["date"] == "2026-03-10"
    assert len(week) == 7


def test_recent_ticks_name_the_client_and_meal():
    A.db_run("DELETE FROM meal_checks")
    _tick(SARA, date(2026, 3, 9), "breakfast")
    _tick(OMAR, date(2026, 3, 10), "dinner")
    rows = D.recent_ticks(A.db_rows, limit=5)
    assert [(r["name"], r["meal_key"]) for r in rows] == [("Omar", "dinner"), ("Sara", "breakfast")]


# ═══ الصفحة ═══

def test_dashboard_has_greeting_and_two_tabs():
    html = _as(ADMIN).get("/dashboard").get_data(as_text=True)
    assert re.search(r'role="tablist"', html)
    tabs = re.findall(r'role="tab"[^>]*aria-controls="(\w+)"', html)
    assert tabs[:2] == ["tabOverview", "tabManage"], tabs
    assert 'id="tabOverview"' in html and 'id="tabManage"' in html
    assert re.search(r"(صباح|مساء) الخير", html)


def test_nothing_from_the_old_dashboard_is_lost():
    html = _as(ADMIN).get("/dashboard").get_data(as_text=True)
    for link in ('href="/generate"', 'href="/patients"', 'href="/admin/requests"',
                 'href="/saved"', 'href="/analyzer"', 'href="/clinical"'):
        assert link in html, link
    for label in ("طلبات جديدة", "إجمالي العملاء", "خطط مكتملة", "رسايل غير مقروءة"):
        assert label in html, label


def test_overview_shows_real_client_activity_today():
    A.db_run("DELETE FROM meal_checks")
    today = A.client_now().date()
    _tick(SARA, today, "breakfast")
    html = _as(ADMIN).get("/dashboard").get_data(as_text=True)
    assert 'data-active-today="1"' in html
    assert "Sara" in html            # ‏آخر النشاط


def test_english_dashboard_has_no_arabic():
    html = _as(ADMIN, "en").get("/dashboard").get_data(as_text=True)
    main = html[html.index('<div class="dash"'):html.index("<!-- /dash -->")]
    assert not ARABIC.search(main), ARABIC.findall(main)[:20]


def test_a_hidden_tab_is_really_hidden():
    # ‏.dash-panel{display:flex} كان بيغلب على [hidden]، فالتاب يتعلّم
    # إنه اتختار والمحتوى مايتغيّرش.
    html = _as(ADMIN).get("/dashboard").get_data(as_text=True)
    assert ".dash-panel[hidden]{display:none}" in html


def test_clients_still_go_to_their_plan():
    r = _as(SARA).get("/dashboard")
    assert r.status_code == 302 and r.headers["Location"].endswith("/my-plan")


# ═══ التوقيت على البلد اللي الأدمن فيها ═══

class _Clock:
    def __init__(self, at):
        self.at, self.old = at, B.utcnow
    def __enter__(self):
        B.utcnow = lambda: self.at
    def __exit__(self, *a):
        B.utcnow = self.old


def test_browser_timezone_is_saved_on_the_account():
    c = _as(ADMIN)
    r = c.post("/me/timezone", json={"tz": "Asia/Dubai"})
    assert r.status_code == 200, r.status_code
    assert A.db_row("SELECT timezone FROM users WHERE id=?", (ADMIN,))["timezone"] == "Asia/Dubai"


def test_a_made_up_timezone_is_refused():
    c = _as(ADMIN)
    c.post("/me/timezone", json={"tz": "Asia/Dubai"})
    r = c.post("/me/timezone", json={"tz": "Mars/Olympus"})
    assert r.status_code == 400
    assert A.db_row("SELECT timezone FROM users WHERE id=?", (ADMIN,))["timezone"] == "Asia/Dubai"


def test_saving_a_timezone_needs_a_session():
    r = A.app.test_client().post("/me/timezone", json={"tz": "Asia/Dubai"})
    assert r.status_code in (302, 401)


def test_greeting_and_date_follow_the_admins_country():
    # ‏٩:٣٠ UTC = ١١:٣٠ القاهرة (صباح) = ١:٣٠ دبي (بعد الضهر)
    with _Clock(datetime(2026, 3, 10, 9, 30)):
        A.db_run("UPDATE users SET timezone='Africa/Cairo' WHERE id=?", (ADMIN,))
        assert "صباح الخير" in _as(ADMIN).get("/dashboard").get_data(as_text=True)
        A.db_run("UPDATE users SET timezone='Asia/Dubai' WHERE id=?", (ADMIN,))
        html = _as(ADMIN).get("/dashboard").get_data(as_text=True)
        assert "مساء الخير" in html
        assert 'data-tz="Asia/Dubai"' in html
    # ‏١١ بالليل UTC = ٣ الفجر في دبي يوم ١١
    with _Clock(datetime(2026, 3, 10, 23, 0)):
        assert "2026-03-11" in _as(ADMIN).get("/dashboard").get_data(as_text=True)
    A.db_run("UPDATE users SET timezone='Africa/Cairo' WHERE id=?", (ADMIN,))


# ═══ أجزاء البرونت اللي اتضافت ببيانات حقيقية ═══

def test_goal_breakdown_groups_the_goal_names():
    A.db_run("UPDATE users SET goal='weight_loss' WHERE id=?", (SARA,))
    A.db_run("UPDATE users SET goal='bulking' WHERE id=?", (OMAR,))
    g = D.goal_breakdown(A.db_rows)
    assert g["lose"] == 1 and g["gain"] == 1 and g["total"] == 2, g


def test_plan_cards_count_people_with_access_now():
    A.db_run("DELETE FROM payments"); A.db_run("DELETE FROM subscriptions")
    now = datetime(2026, 3, 10, 12)
    A.db_run("INSERT INTO payments (user_id, plan_key, status, expires_at) VALUES (?,?,?,?)",
             (SARA, "single_plan", "completed", now + timedelta(days=5)))
    A.db_run("INSERT INTO payments (user_id, plan_key, status, expires_at) VALUES (?,?,?,?)",
             (OMAR, "single_plan", "completed", now - timedelta(days=1)))   # ‏خلص
    A.db_run("INSERT INTO subscriptions (user_id, plan_key, status, current_period_end) VALUES (?,?,?,?)",
             (OMAR, "monthly_subscription", "active", now + timedelta(days=20)))
    cards = {c["key"]: c["count"] for c in D.plan_cards(A.db_rows, now)}
    assert cards["single_plan"] == 1 and cards["monthly_subscription"] == 1, cards
    assert "consultation" in cards


def test_streak_leaders_skip_zero_and_sort():
    streaks = {SARA: 4, OMAR: 0}
    rows = D.streak_leaders(A.db_rows, lambda uid: {"current_streak": streaks.get(uid, 0),
                                                    "best_streak": streaks.get(uid, 0)})
    assert [(r["name"], r["current"]) for r in rows] == [("Sara", 4)], rows


def test_dashboard_has_three_tabs_and_the_new_sections():
    html = _as(ADMIN).get("/dashboard").get_data(as_text=True)
    tabs = re.findall(r'role="tab"[^>]*aria-controls="(\w+)"', html)
    assert tabs == ["tabOverview", "tabManage", "tabStreaks"], tabs
    for hook in ('id="goalMix"', 'id="planCards"', 'id="streakBoard"'):
        assert hook in html, hook


def test_the_orange_plan_card_is_the_busiest_plan():
    # ‏البرتقالي معناه "ده المهم"، فبيروح للباقة اللي عليها أكتر ناس --
    # مش لأول باقة في القايمة وهي عليها صفر.
    A.db_run("DELETE FROM payments"); A.db_run("DELETE FROM subscriptions")
    A.db_run("INSERT INTO payments (user_id, plan_key, status, expires_at) VALUES (?,?,?,?)",
             (SARA, "single_plan", "completed", datetime.now() + timedelta(days=5)))
    html = _as(ADMIN).get("/dashboard").get_data(as_text=True)
    cards = re.findall(r'<div class="dash-plan( is-lead)?">\s*<span class="dash-plan-n">([^<]+)<', html)
    lead = [name for flag, name in cards if flag]
    assert lead == ["خطة واحدة"], cards


def test_the_dashboard_sits_on_the_page_not_on_black():
    # ‏صاحب المشروع اختار الشفاف (A) بدل المعرض الأسود: الكروت البيضا
    # قاعدة على رمادي الموقع، واللوحة شبه باقي الصفحات.
    html = _as(ADMIN).get("/dashboard").get_data(as_text=True)
    rule = re.search(r"\.dash\{--dx-ink[^}]*\}", html).group(0)
    assert "background:transparent" in rule, rule
    assert "background:var(--dx-ink)" not in rule


def test_dashboard_uses_the_prompt_colours():
    html = _as(ADMIN).get("/dashboard").get_data(as_text=True)
    assert "--dx-ink:#0B0B0C" in html and "--dx-accent:#FF6A1A" in html


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

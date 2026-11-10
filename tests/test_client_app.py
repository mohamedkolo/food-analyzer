# -*- coding: utf-8 -*-
"""‏يوميات العميل: المياه، ملاحظات الوجبات، التوصيات، التقييم، والشريط السفلي.

‏اللي بيتسجّل هنا بيانات صحية لعميل بعينه، فأغلب الاختبارات على سؤال
واحد: **هل اللي كتبه عميل بيفضل بتاعه؟** كل مسار بياخد صاحب البيانات
من الجلسة، مش من الفورم -- والاختبارات بتبعت رقم عميل تاني في الفورم
وتتأكد إنه مااتسمعش.

Run with:  python3 tests/test_client_app.py
"""

import os
import re
import sys
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_client_app.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A          # noqa: E402
import booking as B      # noqa: E402
import client_app as C   # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False


def _mk(email, role="client", **cols):
    keys = ["name", "email", "password", "role", "active",
            "onboarded_at"] + list(cols)
    vals = [email.split("@")[0], email, generate_password_hash("pw123456"),
            role, 1, datetime.now()] + list(cols.values())
    A.db_run("INSERT INTO users (%s) VALUES (%s)"
             % (",".join(keys), ",".join("?" * len(keys))), tuple(vals))
    return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]


ADMIN = _mk("boss@c.test", "admin", is_admin=1)
NUTRI = _mk("nutri@c.test", "nutritionist")
ALICE = _mk("alice@c.test")
BASEM = _mk("basem@c.test")


def _as(uid=None, lang="en"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["lang"] = lang
        if uid:
            s["uid"] = uid
    return c


def _reset():
    for table in ("water_log", "meal_notes", "meal_checks", "recommendations",
                  "appointment_ratings", "appointments", "services"):
        A.db_run("DELETE FROM %s" % table)
    A.db_run("UPDATE users SET water_goal_ml=2000")


def _water(uid):
    return C.water_state(A.get_user_by_id(uid))


def _json(c, path, **data):
    return c.post(path, data=data, headers={"X-Requested-With": "fetch"})


# ── المياه ──────────────────────────────────────────────────────────

def test_water_adds_up_for_today_and_stops_at_a_hundred_percent():
    _reset()
    c = _as(ALICE)
    assert _json(c, "/water", amount_ml=200).get_json() == {
        "ok": True, "total": 200, "goal": 2000, "pct": 10}
    _json(c, "/water", amount_ml=500)
    assert _water(ALICE)["total"] == 700
    for _ in range(4):
        _json(c, "/water", amount_ml=500)
    state = _water(ALICE)
    assert state["total"] == 2700 and state["pct"] == 100, state


def test_water_is_the_clients_own():
    """‏الفورم مافيهوش خانة لرقم العميل، ولو حد زوّدها بإيده مابتتسمعش."""
    _reset()
    A.app.test_client().post("/water", data={"amount_ml": 200})
    assert not A.db_rows("SELECT id FROM water_log"), "logged without a login"
    _as(ALICE).post("/water", data={"amount_ml": 300, "user_id": BASEM})
    assert _water(ALICE)["total"] == 300 and _water(BASEM)["total"] == 0
    _json(_as(BASEM), "/water/undo")
    assert _water(ALICE)["total"] == 300, "someone else undid my glass"


def test_water_refuses_amounts_nobody_drinks():
    _reset()
    c = _as(ALICE)
    for bad in ("0", "-200", "49", "2001", "99999", "abc", ""):
        assert _json(c, "/water", amount_ml=bad).status_code == 400, bad
    assert _water(ALICE)["total"] == 0


def test_undo_takes_back_only_the_last_glass():
    _reset()
    c = _as(ALICE)
    _json(c, "/water", amount_ml=200)
    _json(c, "/water", amount_ml=500)
    assert _json(c, "/water/undo").get_json()["total"] == 200
    _json(c, "/water/undo")
    assert _json(c, "/water/undo").get_json() == {
        "ok": False, "total": 0, "goal": 2000, "pct": 0}


def test_the_water_day_is_the_clients_day_not_the_servers():
    """‏كوب الساعة ١٢:٣٠ بعد نص الليل في القاهرة بتاع اليوم الجديد هناك.
    بساعة السيرفر (UTC) لسه إمبارح -- فاليوم بيتحسب بساعة العميل."""
    _reset()
    user = A.get_user_by_id(ALICE)
    start, end = C._today_bounds(user)
    for when in (start - timedelta(minutes=1), end):
        A.db_run("INSERT INTO water_log (user_id, amount_ml, logged_at) "
                 "VALUES (?,?,?)", (ALICE, 999, B.to_db(when)))
    A.db_run("INSERT INTO water_log (user_id, amount_ml, logged_at) "
             "VALUES (?,?,?)", (ALICE, 250, B.to_db(start)))
    assert _water(ALICE)["total"] == 250
    assert (end - start) == timedelta(days=1)
    cairo_midnight = B.to_local(start, B.tz("Africa/Cairo"))
    assert (cairo_midnight.hour, cairo_midnight.minute) == (0, 0)


def test_the_water_card_is_on_the_home_page_and_a_plain_form_works_too():
    _reset()
    c = _as(ALICE)
    r = c.post("/water", data={"amount_ml": 350})
    assert r.status_code == 302 and r.headers["Location"].endswith("/my-plan#water")
    page = c.get("/my-plan").get_data(as_text=True)
    assert "Water today" in page and "350 / 2000 ml" in page


# ── ملاحظات الوجبات ─────────────────────────────────────────────────

def _notes(uid):
    return {r["meal_key"]: r for r in A.db_rows(
        "SELECT * FROM meal_notes WHERE user_id=?", (uid,))}


def test_a_skipped_meal_is_not_also_an_eaten_meal():
    """‏حساب الالتزام والتتابع بيعدّ صفوف meal_checks. وجبة متعلّم عليها
    "اتاكلت" و"ماكلتهاش" مع بعض كانت هتتحسب التزام."""
    _reset()
    c = _as(ALICE)
    c.post("/track/meal", data={"meal_key": "lunch", "checked": "1"})
    assert A.db_rows("SELECT id FROM meal_checks WHERE user_id=?", (ALICE,))
    r = c.post("/track/meal-note", data={"meal_key": "lunch", "skipped": "1",
                                         "comment": "  was   travelling "})
    assert r.get_json() == {"ok": True, "skipped": 1, "comment": "was travelling"}
    assert not A.db_rows("SELECT id FROM meal_checks WHERE user_id=?", (ALICE,))
    note = _notes(ALICE)["lunch"]
    assert note["skipped"] == 1 and note["comment"] == "was travelling"


def test_a_comment_alone_keeps_the_tick_and_clearing_it_removes_the_note():
    _reset()
    c = _as(ALICE)
    c.post("/track/meal", data={"meal_key": "dinner", "checked": "1"})
    c.post("/track/meal-note", data={"meal_key": "dinner", "comment": "smaller portion"})
    assert A.db_rows("SELECT id FROM meal_checks WHERE user_id=?", (ALICE,))
    assert _notes(ALICE)["dinner"]["skipped"] == 0
    c.post("/track/meal-note", data={"meal_key": "dinner", "comment": ""})
    assert _notes(ALICE) == {}
    assert c.post("/track/meal-note", data={"comment": "x"}).status_code == 400


def test_meal_notes_are_the_clients_own_and_reach_the_nutritionist():
    _reset()
    _as(ALICE).post("/track/meal-note", data={"meal_key": "lunch", "skipped": "1",
                                              "comment": "felt sick"})
    assert _notes(BASEM) == {}
    assert C.meal_notes_today(A.get_user_by_id(BASEM)) == {}
    profile = _as(ADMIN).get("/admin/users/%d" % ALICE).get_data(as_text=True)
    assert "felt sick" in profile and "Skipped" in profile
    assert "felt sick" not in _as(ADMIN).get(
        "/admin/users/%d" % BASEM).get_data(as_text=True)


# ── التوصيات ────────────────────────────────────────────────────────

def _rec(uid, **data):
    return _as(ADMIN).post("/admin/users/%d/recommendations" % uid, data=data)


def test_recommendations_reach_only_the_client_they_were_written_for():
    _reset()
    _rec(ALICE, action="add", kind="goal", body="Walk 30 minutes a day")
    _rec(ALICE, action="add", kind="avoid", body="Fizzy drinks")
    _rec(ALICE, action="add", kind="note", body="Eat before 9pm")
    page = _as(ALICE).get("/recommendations").get_data(as_text=True)
    for text in ("Walk 30 minutes a day", "Fizzy drinks", "Eat before 9pm"):
        assert text in page, text
    other = _as(BASEM).get("/recommendations").get_data(as_text=True)
    assert "Fizzy drinks" not in other and "has not added anything" in other
    assert _as().get("/recommendations").status_code == 302


def test_only_staff_write_recommendations():
    _reset()
    for who in (ALICE, BASEM, None):
        _as(who).post("/admin/users/%d/recommendations" % ALICE,
                      data={"action": "add", "kind": "note", "body": "hello"})
        _as(who).post("/admin/users/%d/recommendations" % ALICE,
                      data={"action": "water_goal", "water_goal_ml": 5000})
    assert not A.db_rows("SELECT id FROM recommendations")
    assert A.get_user_by_id(ALICE)["water_goal_ml"] == 2000
    _as(NUTRI).post("/admin/users/%d/recommendations" % ALICE,
                    data={"action": "add", "kind": "note", "body": "hello"})
    assert len(A.db_rows("SELECT id FROM recommendations")) == 1


def test_a_recommendation_is_deleted_only_through_its_own_client():
    """‏رقم توصية بتاعة عميل، مبعوت على صفحة عميل تاني، مايتمسحش."""
    _reset()
    _rec(ALICE, action="add", kind="note", body="keep")
    rid = A.db_row("SELECT id FROM recommendations")["id"]
    _rec(BASEM, action="delete", id=rid)
    assert A.db_row("SELECT id FROM recommendations WHERE id=?", (rid,))
    _rec(ALICE, action="delete", id=rid)
    assert not A.db_rows("SELECT id FROM recommendations")


def test_bad_recommendations_and_water_goals_are_dropped():
    _reset()
    _rec(ALICE, action="add", kind="order", body="x")
    _rec(ALICE, action="add", kind="note", body="   ")
    _rec(ADMIN, action="add", kind="note", body="staff are not clients")
    assert not A.db_rows("SELECT id FROM recommendations")
    for bad in (100, 99999, "lots"):
        _rec(ALICE, action="water_goal", water_goal_ml=bad)
        assert A.get_user_by_id(ALICE)["water_goal_ml"] == 2000, bad
    _rec(ALICE, action="water_goal", water_goal_ml=3000)
    assert _water(ALICE)["goal"] == 3000 and _water(BASEM)["goal"] == 2000
    assert "3000 ml a day" in _as(ALICE).get(
        "/recommendations").get_data(as_text=True)


# ── التقييم ─────────────────────────────────────────────────────────

def _session(uid, status="completed", days_ago=1):
    if not A.db_row("SELECT id FROM services"):
        A.db_run("INSERT INTO services (name, duration_min, price) "
                 "VALUES ('Follow-up', 30, 0)")
    svc = A.db_row("SELECT id FROM services")["id"]
    start = (B.utcnow() - timedelta(days=days_ago)).replace(minute=0, second=0)
    A.db_run("INSERT INTO appointments (client_id, service_id, start_at, "
             "end_at, status, slot_key) VALUES (?,?,?,?,?,?)",
             (uid, svc, B.to_db(start), B.to_db(start + timedelta(minutes=30)),
              status, "k%s-%s-%s" % (uid, status, days_ago)))
    return A.db_row("SELECT id FROM appointments ORDER BY id DESC LIMIT 1")["id"]


def _ratings():
    return A.db_rows("SELECT * FROM appointment_ratings ORDER BY id")


def test_a_client_rates_a_finished_session_once():
    _reset()
    appt = _session(ALICE)
    c = _as(ALICE)
    assert 'action="/book/%d/rate"' % appt in c.get(
        "/book/%d" % appt).get_data(as_text=True)
    assert "How was your consultation?" in c.get("/my-plan").get_data(as_text=True)
    r = c.post("/book/%d/rate" % appt, data={"score": 9, "comment": "Clear plan"})
    assert "msg=rated" in r.headers["Location"]
    c.post("/book/%d/rate" % appt, data={"score": 1})
    got = _ratings()
    assert len(got) == 1 and got[0]["score"] == 9 and got[0]["anonymous"] == 0
    assert 'action="/book/%d/rate"' % appt not in c.get(
        "/book/%d" % appt).get_data(as_text=True)
    assert "How was your consultation?" not in c.get(
        "/my-plan").get_data(as_text=True)


def test_only_a_session_that_happened_can_be_rated_and_only_by_its_client():
    _reset()
    done = _session(ALICE)
    for status in ("accepted", "no_show", "cancelled", "pending"):
        appt = _session(ALICE, status, days_ago=2 + len(status))
        _as(ALICE).post("/book/%d/rate" % appt, data={"score": 8})
    old = _session(ALICE, days_ago=C.RATE_WINDOW_DAYS + 3)
    _as(ALICE).post("/book/%d/rate" % old, data={"score": 8})
    assert _as(BASEM).post("/book/%d/rate" % done,
                           data={"score": 1}).status_code == 404
    _as(NUTRI).post("/book/%d/rate" % done, data={"score": 10})
    for bad in (0, 11, "ten", ""):
        _as(ALICE).post("/book/%d/rate" % done, data={"score": bad})
    assert _ratings() == []


def test_an_anonymous_rating_does_not_show_who_sent_it():
    _reset()
    A.db_run("UPDATE users SET name='Alice Unique' WHERE id=?", (ALICE,))
    A.db_run("UPDATE users SET name='Basem Unique' WHERE id=?", (BASEM,))
    _as(ALICE).post("/book/%d/rate" % _session(ALICE),
                    data={"score": 3, "comment": "Too rushed", "anonymous": "1"})
    _as(BASEM).post("/book/%d/rate" % _session(BASEM),
                    data={"score": 10, "comment": "Great"})
    seen = C.ratings_overview()
    assert seen["average"] == 6.5
    by_comment = {r["comment"]: r["client_name"] for r in seen["rows"]}
    assert by_comment == {"Too rushed": None, "Great": "Basem Unique"}, by_comment
    page = _as(NUTRI).get("/admin/calendar").get_data(as_text=True)
    card = page[page.index("Client ratings"):]
    card = card[:card.index("<details")]
    assert "Too rushed" in card and "Anonymous" in card
    assert "Basem Unique" in card
    assert "Alice Unique" not in card, "an anonymous rating shows its sender"


# ── الشريط السفلي ───────────────────────────────────────────────────

def test_the_bottom_bar_is_the_clients_and_only_the_clients():
    """‏صفحة ملف العميل عند الأدمن بتبعت العميل نفسه في user. لو الشرط على
    user لوحده، الأدمن يشوف شريط العميل ويسجّل مياه باسمه هو."""
    _reset()
    client_page = _as(ALICE).get("/my-plan").get_data(as_text=True)
    assert 'class="cbar"' in client_page and 'id="csheet"' in client_page
    for href in ('href="/my-plan"', 'href="/plan"', 'href="/recommendations"'):
        assert href in client_page[client_page.index('class="cbar"'):], href
    assert 'class="cbar"' not in _as(NUTRI).get("/dashboard").get_data(as_text=True)
    assert 'class="cbar"' not in _as(ADMIN).get(
        "/admin/users/%d" % ALICE).get_data(as_text=True)
    assert 'class="cbar"' not in _as().get("/book").get_data(as_text=True)


def test_the_plan_tab_goes_to_the_plan_in_force():
    _reset()
    A.db_run("DELETE FROM plan_requests WHERE client_id=?", (ALICE,))
    r = _as(ALICE).get("/plan")
    assert r.headers["Location"].endswith("/my-plan")
    A.db_run("INSERT INTO plan_requests (client_id, client_name, status, "
             "request_data, plan_data) VALUES (?,?,?,?,?)",
             (ALICE, "alice", "approved", "{}", '{"data": {}, "plan": []}'))
    pid = A.db_row("SELECT id FROM plan_requests WHERE client_id=?", (ALICE,))["id"]
    assert _as(ALICE).get("/plan").headers["Location"].endswith(
        "/my-plans-history/%d" % pid)
    assert _as().get("/plan").status_code == 302


def test_a_page_title_holds_a_title_and_nothing_else():
    """‏فورم الحجز اليدوي اتحط مرة جوّه بلوك العنوان (استبدال على كل
    endblock)، فعنوان التبويب بقى فيه فورم كامل."""
    A.db_run("INSERT INTO services (name, duration_min, price) "
             "VALUES ('Consult', 30, 0)")
    for path in ("/admin/calendar", "/admin/booking-settings"):
        page = _as(NUTRI).get(path).get_data(as_text=True)
        title = re.search(r"<title>(.*?)</title>", page, re.S).group(1)
        assert "<" not in title and len(title) < 80, (path, title[:120])
        assert page.count('action="/admin/appointments/new"') <= 1


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
        except Exception as e:
            print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

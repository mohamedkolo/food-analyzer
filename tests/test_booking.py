# -*- coding: utf-8 -*-
"""‏حجز الاستشارة: المواعيد اللي بتتعرض، ومين بياخد الموعد، ومين بيشوفه.

‏أربع حاجات لو باظت في صمت بتكلّف على طول، وكل واحدة ليها اختباراتها:

  ‏١) **توليد المواعيد** -- موعد برّه ساعات العمل، أو متداخل مع موعد
     محجوز، معناه عميلين في نفس الساعة.
  ‏٢) **الحجز المزدوج** -- اتنين داسوا على نفس الموعد في نفس اللحظة.
     اللي بيحسمها قيد UNIQUE في القاعدة، مش الصفحة.
  ‏٣) **التوقيت** -- الأخصائي في دبي والعملاء في القاهرة، والفرق بينهم
     ساعتين في الشتا وساعة في الصيف. موعد بيتعرض بساعة غلط = عميل
     بيدخل الجلسة بدري ساعة أو متأخر ساعة.
  ‏٤) **الصلاحيات** -- عميل مايشوفش موعد عميل تاني، ومايقبلش طلب نفسه.

Run with:  python3 tests/test_booking.py
"""

import os
import sys
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_booking.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A        # noqa: E402
import booking as B    # noqa: E402
import booking_notify as N  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False

DUBAI = ZoneInfo("Asia/Dubai")
CAIRO = ZoneInfo("Africa/Cairo")


def _mk(email, role="client", **cols):
    keys = ["name", "email", "password", "role", "active",
            "onboarded_at"] + list(cols)
    vals = [email.split("@")[0], email, generate_password_hash("pw123456"),
            role, 1, datetime.now()] + list(cols.values())
    A.db_run("INSERT INTO users (%s) VALUES (%s)"
             % (",".join(keys), ",".join("?" * len(keys))), tuple(vals))
    return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]


ADMIN = _mk("boss@b.test", "admin", is_admin=1)
NUTRI = _mk("nutri@b.test", "nutritionist")
ALICE = _mk("alice@b.test")
BASEM = _mk("basem@b.test")


def _as(uid=None, lang="en"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["lang"] = lang
        if uid:
            s["uid"] = uid
    return c


def _reset(hours=True):
    """‏قاعدة نضيفة لكل اختبار: خدمتين، وساعات عمل طول اليوم كل يوم --
    فالاختبار مابيعتمدش على اليوم ولا الساعة اللي اتشغّل فيهم."""
    for table in ("appointments", "services", "availability",
                  "booking_settings", "messages", "notifications"):
        A.db_run("DELETE FROM %s" % table)
    A.db_run("INSERT INTO services (name, duration_min, price) "
             "VALUES ('Follow-up', 30, 30000)")
    A.db_run("INSERT INTO services (name, duration_min, price) "
             "VALUES ('First visit', 60, 50000)")
    if hours:
        for wd in range(7):
            A.db_run("INSERT INTO availability (weekday, start_min, end_min) "
                     "VALUES (?,?,?)", (wd, 0, 24 * 60))
    return (A.db_row("SELECT * FROM services WHERE duration_min=30"),
            A.db_row("SELECT * FROM services WHERE duration_min=60"))


def _slot(days=3, hour=9, minute=0):
    """‏موعد على الشبكة بعد كام يوم، بتوقيت UTC."""
    d = B.utcnow() + timedelta(days=days)
    return d.replace(hour=hour, minute=minute, second=0)


def _book(client_id, service, start):
    return B.create_request(A.db_row, A.db_rows, A.db_run, client_id,
                            service, start)


def _status(appt_id):
    return A.db_row("SELECT * FROM appointments WHERE id=?", (appt_id,))


# ── ١) توليد المواعيد ───────────────────────────────────────────────

# ‏أسبوع ثابت في يناير: الاثنين ١١ يناير ٢٠٢٧ (شتا، القاهرة UTC+2).
_MON = datetime(2027, 1, 11)
_WEEK = (B.to_utc(_MON, DUBAI), B.to_utc(_MON + timedelta(days=7), DUBAI))


def _local(slots, zone=DUBAI):
    return [B.to_local(s, zone).strftime("%a %H:%M") for s in slots]


def test_slots_stay_inside_working_hours_and_on_the_grid():
    got = B.generate_slots([(0, 600, 720)], 30, [], *_WEEK, zone=DUBAI)
    assert _local(got) == ["Mon 10:00", "Mon 10:30", "Mon 11:00",
                           "Mon 11:30"], _local(got)


def test_a_long_service_is_not_offered_where_it_would_run_past_closing():
    """‏ساعة كاملة مابتبدأش ١١:٣٠ لو الشغل بيخلص ١٢:٠٠."""
    got = B.generate_slots([(0, 600, 720)], 60, [], *_WEEK, zone=DUBAI)
    assert _local(got) == ["Mon 10:00", "Mon 10:30", "Mon 11:00"], _local(got)


def test_a_booked_hour_hides_every_slot_it_touches():
    """‏موعد ساعة من ١٠:٣٠ لـ١١:٣٠ بيقفل ١٠:٣٠ و١١:٠٠ على خدمة النص
    ساعة -- وعلى خدمة الساعة بيقفل ١٠:٠٠ كمان، لأنها هتخبط فيه."""
    busy = [(B.to_utc(_MON.replace(hour=10, minute=30), DUBAI),
             B.to_utc(_MON.replace(hour=11, minute=30), DUBAI))]
    half = B.generate_slots([(0, 600, 780)], 30, busy, *_WEEK, zone=DUBAI)
    assert _local(half) == ["Mon 10:00", "Mon 11:30", "Mon 12:00",
                            "Mon 12:30"], _local(half)
    full = B.generate_slots([(0, 600, 780)], 60, busy, *_WEEK, zone=DUBAI)
    assert _local(full) == ["Mon 11:30", "Mon 12:00"], _local(full)


def test_no_working_hours_means_no_slots():
    assert B.generate_slots([], 30, [], *_WEEK, zone=DUBAI) == []


def test_overlapping_windows_do_not_offer_a_slot_twice():
    got = B.generate_slots([(0, 600, 660), (0, 630, 690)], 30, [], *_WEEK,
                           zone=DUBAI)
    assert len(got) == len(set(got)) == 3, _local(got)


def test_a_slot_too_soon_or_too_far_is_not_offered():
    half, _ = _reset()
    now = B.utcnow()
    got = B.open_slots(A.db_rows, half, now - timedelta(days=1),
                       now + timedelta(days=90), now=now)
    assert got, "no slots at all"
    assert min(got) >= now + timedelta(minutes=B.MIN_LEAD_MIN), min(got)
    assert max(got) < now + timedelta(days=B.DAYS_AHEAD), max(got)


# ── ٣) التوقيت ──────────────────────────────────────────────────────

def test_ten_in_dubai_is_eight_in_cairo_in_winter_and_nine_in_summer():
    """‏دبي مافيهاش توقيت صيفي والقاهرة فيها. نفس "١٠ الصبح" عند الأخصائي
    بتبقى ٨ عند العميل في يناير و٩ في يوليو. لو الكود خزّن فرق ثابت
    (ساعتين)، مواعيد الصيف كلها هتتعرض بدري ساعة."""
    for monday, cairo_hour in ((datetime(2027, 1, 11), "08:00"),
                               (datetime(2027, 7, 12), "09:00")):
        week = (B.to_utc(monday, DUBAI),
                B.to_utc(monday + timedelta(days=1), DUBAI))
        got = B.generate_slots([(0, 600, 630)], 30, [], *week, zone=DUBAI)
        assert len(got) == 1, got
        assert B.to_local(got[0], CAIRO).strftime("%H:%M") == cairo_hour, (
            monday, B.to_local(got[0], CAIRO))
        assert got[0].tzinfo is None and got[0].hour == 6, got[0]


def test_working_days_follow_the_nutritionists_calendar_not_the_clients():
    """‏الاثنين ١٢:٣٠ بعد نص الليل في دبي لسه **الأحد** ١٠:٣٠ بالليل في
    القاهرة. الموعد بيتولّد من يوم الأخصائي، وبيتعرض في يوم العميل."""
    got = B.generate_slots([(0, 30, 60)], 30, [], *_WEEK, zone=DUBAI)
    assert _local(got) == ["Mon 00:30"], _local(got)
    assert _local(got, CAIRO) == ["Sun 22:30"], _local(got, CAIRO)
    sunday = (_MON - timedelta(days=1)).date()
    start, end = B.local_day_bounds(sunday, CAIRO)
    assert start <= got[0] < end, "the slot is missing from the client's Sunday"


def test_the_client_reads_cairo_time_and_the_calendar_reads_dubai_time():
    half, _ = _reset()
    start = datetime(2027, 7, 12, 6, 0)          # 06:00 UTC, summer
    A.db_run("INSERT INTO appointments (client_id, service_id, start_at, "
             "end_at, status, slot_key) VALUES (?,?,?,?,'accepted',?)",
             (ALICE, half["id"], B.to_db(start),
              B.to_db(start + timedelta(minutes=30)), B.slot_key(start)))
    appt = A.db_row("SELECT id FROM appointments")["id"]

    page = _as(ALICE).get("/book/%d" % appt).get_data(as_text=True)
    assert "9:00 AM" in page and "Cairo" in page, "client is not on Cairo time"
    assert "10:00 AM" not in page, "client was shown the nutritionist's clock"

    cal = _as(NUTRI).get("/admin/calendar?from=2027-07-12").get_data(as_text=True)
    assert "10:00 AM" in cal and "Dubai" in cal, "calendar is not on Dubai time"


def test_an_unknown_time_zone_on_a_user_falls_back_instead_of_crashing():
    assert B.tz("Mars/Olympus").key == "Africa/Cairo"
    assert B.viewer_tz({"role": "client", "timezone": ""}).key == "Africa/Cairo"
    assert B.viewer_tz({"role": "nutritionist"}).key == B.pro_tz().key


# ── ٢) الحجز المزدوج ────────────────────────────────────────────────

def test_the_same_slot_cannot_be_booked_twice():
    half, _ = _reset()
    start = _slot()
    _book(ALICE, half, start)
    try:
        _book(BASEM, half, start)
        assert False, "the second client booked a slot that was taken"
    except B.SlotTaken:
        pass
    assert len(A.db_rows("SELECT id FROM appointments")) == 1


def test_the_database_refuses_a_second_active_row_on_one_slot():
    """‏ده القيد نفسه، من غير أي فحص قبله: لو حد شال الفحص اللي في الكود
    أو كتب مسار جديد بيدخّل مواعيد، القاعدة لسه بترفض."""
    half, _ = _reset()
    start = _slot()
    sql = ("INSERT INTO appointments (client_id, service_id, start_at, end_at,"
           " slot_key) VALUES (?,?,?,?,?)")
    args = (half["id"], B.to_db(start), B.to_db(start + timedelta(minutes=30)),
            B.slot_key(start))
    A.db_run(sql, (ALICE,) + args)
    try:
        A.db_run(sql, (BASEM,) + args)
        assert False, "UNIQUE (slot_key) is not enforced"
    except AssertionError:
        raise
    except Exception as exc:
        assert "unique" in str(exc).lower(), exc


def test_two_clients_racing_for_one_slot_leave_exactly_one_booking():
    half, _ = _reset()
    start = _slot()
    results, gate = [], threading.Barrier(2)

    def go(client_id):
        gate.wait()
        try:
            _book(client_id, half, start)
            results.append("won")
        except B.SlotTaken:
            results.append("taken")
        except Exception as exc:                 # noqa: BLE001
            results.append(repr(exc))

    threads = [threading.Thread(target=go, args=(c,)) for c in (ALICE, BASEM)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert sorted(results) == ["taken", "won"], results
    assert len(A.db_rows("SELECT id FROM appointments")) == 1


def test_a_booking_that_slipped_past_the_check_still_cannot_overlap():
    """‏القيد بيمسك نفس البداية بس. واحد حجز ساعة من ٩:٠٠ والتاني في نفس
    اللحظة نص ساعة من ٩:٣٠: بدايتين مختلفتين. هنا بنخلي الفحص الأول
    "مايشوفش" (زي ما بيحصل في السباق)، واللي بعد الإدراج لازم يمسكها."""
    half, full = _reset()
    _book(ALICE, full, _slot(hour=9))
    late = _slot(hour=9, minute=30)
    real = B.open_slots
    B.open_slots = lambda *a, **k: [late]
    try:
        _book(BASEM, half, late)
        assert False, "an overlapping appointment was booked"
    except B.SlotTaken:
        pass
    finally:
        B.open_slots = real
    assert len(A.db_rows("SELECT id FROM appointments")) == 1


def test_a_rejected_request_frees_its_slot():
    half, _ = _reset()
    start = _slot()
    first = _book(ALICE, half, start)
    assert B.decide(A.db_row, A.db_run, first, False, reason="busy")
    row = _status(first)
    assert row["status"] == "rejected" and row["slot_key"] is None, row
    second = _book(BASEM, half, start)
    assert _status(second)["status"] == "pending"


def test_a_time_off_the_grid_or_outside_working_hours_is_refused():
    half, _ = _reset(hours=False)
    A.db_run("INSERT INTO availability (weekday, start_min, end_min) "
             "VALUES (?,?,?)", (_slot().weekday(), 600, 720))   # 10-12 Dubai
    for bad in (_slot(hour=20), _slot(hour=7, minute=15)):
        try:
            _book(ALICE, half, bad)
            assert False, "booked %s" % bad
        except B.NotBookable:
            pass
    assert B.parse_slot("2027-01-11T10:15") is None
    assert B.parse_slot("<script>") is None


def test_one_client_cannot_hold_the_whole_week_with_pending_requests():
    half, _ = _reset()
    for i in range(B.MAX_OPEN_PER_CLIENT):
        _book(ALICE, half, _slot(hour=9 + i))
    try:
        _book(ALICE, half, _slot(hour=15))
        assert False, "no limit on pending requests"
    except B.NotBookable as why:
        assert str(why) == "too_many"


# ── الصفحات ─────────────────────────────────────────────────────────

def test_the_booking_page_opens_without_a_login():
    _reset()
    page = _as().get("/book")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "Follow-up" in body and "First visit" in body
    assert 'name="slot"' in body, "no times on the page"
    assert "Cairo" in body, "the page does not say which clock it uses"


def test_the_booking_page_says_so_when_nothing_is_set_up():
    for table in ("appointments", "services", "availability"):
        A.db_run("DELETE FROM %s" % table)
    page = _as().get("/book")
    assert page.status_code == 200
    assert "not open right now" in page.get_data(as_text=True)


def test_slots_json_matches_what_can_be_booked():
    half, _ = _reset()
    day = (B.utcnow() + timedelta(days=3)).date().isoformat()
    c = _as(ALICE)
    data = c.get("/book/slots?service=%d&date=%s" % (half["id"], day)).get_json()
    assert data["timezone"] == "Africa/Cairo" and len(data["slots"]) == 48, data
    first = data["slots"][0]
    assert first["time"] == "00:00", first
    r = c.post("/book", data={"service": half["id"], "date": day,
                              "slot": first["start"]})
    assert r.status_code == 302 and "/book/" in r.headers["Location"], r.headers
    again = c.get("/book/slots?service=%d&date=%s" % (half["id"], day)).get_json()
    assert first["start"] not in [s["start"] for s in again["slots"]]
    assert _as().get("/book/slots?service=x&date=nope").status_code == 400


def test_a_visitor_is_sent_to_log_in_and_comes_back_to_the_slot_they_chose():
    half, _ = _reset()
    start = B.slot_key(_slot())
    c = _as()
    r = c.post("/book", data={"service": half["id"], "date": "", "slot": start})
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert not A.db_rows("SELECT id FROM appointments"), "booked without login"
    r = c.post("/login", data={"action": "login", "email": "alice@b.test",
                               "password": "pw123456"})
    dest = r.headers.get("Location", "")
    assert dest.startswith("/book?") and "slot=" in dest, dest
    assert 'value="%s" required checked' % start in c.get(dest).get_data(as_text=True)


def test_a_taken_slot_sends_the_client_back_with_a_message():
    half, _ = _reset()
    start = _slot()
    _book(ALICE, half, start)
    r = _as(BASEM).post("/book", data={"service": half["id"], "date": "",
                                       "slot": B.slot_key(start)},
                        follow_redirects=True)
    assert "just taken" in r.get_data(as_text=True)


def test_a_paused_service_is_not_offered_and_cannot_be_booked():
    half, full = _reset()
    A.db_run("UPDATE services SET active=0 WHERE id=?", (full["id"],))
    assert "First visit" not in _as().get("/book").get_data(as_text=True)
    _as(ALICE).post("/book", data={"service": full["id"], "date": "",
                                   "slot": B.slot_key(_slot())})
    assert not A.db_rows("SELECT id FROM appointments")


# ── ٤) الصلاحيات ────────────────────────────────────────────────────

def test_a_client_cannot_see_another_clients_appointment():
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    assert _as(ALICE).get("/book/%d" % appt).status_code == 200
    other = _as(BASEM).get("/book/%d" % appt)
    assert other.status_code == 404, other.status_code
    # ‏نفس الرد بالظبط لرقم مش موجود -- الصفحة ماتقولش إن الموعد موجود.
    assert _as(BASEM).get("/book/999999").status_code == 404
    anon = _as().get("/book/%d" % appt)
    assert anon.status_code == 302 and "/login" in anon.headers["Location"]
    assert "alice" not in _as(BASEM).get("/book").get_data(as_text=True)


def test_staff_can_open_any_appointment():
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    for uid in (ADMIN, NUTRI):
        assert _as(uid).get("/book/%d" % appt).status_code == 200


def test_a_client_cannot_reach_the_calendar_or_answer_a_request():
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    for who in (ALICE, None):
        c = _as(who)
        for path in ("/admin/calendar", "/admin/booking-settings"):
            assert c.get(path).status_code == 302, (who, path)
        c.post("/admin/appointments/%d/accept" % appt,
               data={"video_url": "https://meet.google.com/abc"})
        c.post("/admin/appointments/%d/reject" % appt, data={"reason": "x"})
        c.post("/admin/booking-settings",
               data={"action": "add_service", "name": "Free", "duration_min": 30,
                     "price": 0})
    row = _status(appt)
    assert row["status"] == "pending" and not row["video_url"], row
    assert not A.db_row("SELECT id FROM services WHERE name='Free'")


def test_staff_do_not_book_from_the_client_page():
    half, _ = _reset()
    r = _as(NUTRI).post("/book", data={"service": half["id"], "date": "",
                                       "slot": B.slot_key(_slot())})
    assert r.status_code == 302 and "/admin/calendar" in r.headers["Location"]
    assert not A.db_rows("SELECT id FROM appointments")


# ── القبول والرفض ───────────────────────────────────────────────────

def test_accepting_puts_the_meeting_link_on_the_clients_page():
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    before = _as(ALICE).get("/book/%d" % appt).get_data(as_text=True)
    assert "Waiting for the nutritionist" in before
    cal = _as(NUTRI).get("/admin/calendar").get_data(as_text=True)
    assert "/admin/appointments/%d/accept" % appt in cal, "request not listed"
    _as(NUTRI).post("/admin/appointments/%d/accept" % appt,
                    data={"video_url": "https://meet.google.com/abc-defg-hij"})
    row = _status(appt)
    assert row["status"] == "accepted" and row["slot_key"], row
    after = _as(ALICE).get("/book/%d" % appt).get_data(as_text=True)
    assert 'href="https://meet.google.com/abc-defg-hij"' in after
    assert "confirmed" in after


def test_a_meeting_link_that_is_not_https_is_refused():
    """‏اللينك ده بيتحط في href والعميل بيدوس عليه."""
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    for bad in ("javascript:alert(1)", "http://meet.google.com/abc",
                'https://x.test/"onmouseover="x'):
        _as(ADMIN).post("/admin/appointments/%d/accept" % appt,
                        data={"video_url": bad})
        assert _status(appt)["status"] == "pending", bad


def test_rejecting_shows_the_reason_to_the_client():
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    _as(ADMIN).post("/admin/appointments/%d/reject" % appt,
                    data={"reason": "Out of office"})
    page = _as(ALICE).get("/book/%d" % appt).get_data(as_text=True)
    assert "declined" in page and "Out of office" in page


def test_a_request_is_answered_once():
    """‏ضغطتين على "رفض" بعد "قبول"، أو اتنين من الطاقم بيردّوا على نفس
    الطلب: القرار الأول هو اللي بيفضل، والموعد مايتفتحش من تحت عميل
    اتأكد له."""
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    _as(NUTRI).post("/admin/appointments/%d/accept" % appt, data={})
    r = _as(ADMIN).post("/admin/appointments/%d/reject" % appt,
                        data={"reason": "late click"})
    assert "msg=stale" in r.headers["Location"]
    row = _status(appt)
    assert row["status"] == "accepted" and row["slot_key"], row


# ── الإعدادات ───────────────────────────────────────────────────────

def test_settings_refuse_what_would_break_the_grid():
    """‏خدمة ٤٥ دقيقة أو شغل بيبدأ ١٠:١٥ بيطلّعوا مواعيد برّه الشبكة،
    والتداخل الجزئي بيرجع ممكن."""
    _reset(hours=False)
    c = _as(NUTRI)
    before = len(A.db_rows("SELECT id FROM services"))
    for bad in ({"name": "Odd", "duration_min": 45, "price": 100},
                {"name": "", "duration_min": 30, "price": 100},
                {"name": "Neg", "duration_min": 30, "price": -5},
                {"name": "Long", "duration_min": 600, "price": 5}):
        r = c.post("/admin/booking-settings", data=dict(bad, action="add_service"))
        assert "msg=bad_service" in r.headers["Location"], bad
    assert len(A.db_rows("SELECT id FROM services")) == before
    for bad in ({"weekday": 0, "start": "10:15", "end": "12:00"},
                {"weekday": 0, "start": "12:00", "end": "10:00"},
                {"weekday": 9, "start": "10:00", "end": "12:00"}):
        r = c.post("/admin/booking-settings", data=dict(bad, action="add_hours"))
        assert "msg=bad_hours" in r.headers["Location"], bad
    assert not A.db_rows("SELECT id FROM availability")


def test_settings_save_a_service_in_piastres_and_hours_in_minutes():
    _reset(hours=False)
    c = _as(NUTRI)
    c.post("/admin/booking-settings",
           data={"action": "add_service", "name": "Online consult",
                 "duration_min": 60, "price": "450.50"})
    row = A.db_row("SELECT * FROM services WHERE name='Online consult'")
    assert row["price"] == 45050 and row["currency"] == "EGP", row
    c.post("/admin/booking-settings",
           data={"action": "add_hours", "weekday": 5, "start": "10:00",
                 "end": "14:30"})
    hrs = A.db_row("SELECT * FROM availability")
    assert (hrs["weekday"], hrs["start_min"], hrs["end_min"]) == (5, 600, 870)
    page = c.get("/admin/booking-settings").get_data(as_text=True)
    assert "Saturday" in page and "10:00 – 14:30" in page
    c.post("/admin/booking-settings", data={"action": "delete_hours",
                                            "id": hrs["id"]})
    assert not A.db_rows("SELECT id FROM availability")
    c.post("/admin/booking-settings", data={"action": "toggle_service",
                                            "id": row["id"]})
    assert A.db_row("SELECT active FROM services WHERE id=?",
                    (row["id"],))["active"] == 0


def test_the_price_is_frozen_on_the_appointment():
    """‏لو الأخصائي غيّر سعر الخدمة بعد الحجز، العميل لسه عليه السعر اللي
    حجز بيه."""
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    A.db_run("UPDATE services SET price=99900 WHERE id=?", (half["id"],))
    assert _status(appt)["price"] == 30000
    assert "300 EGP" in _as(ALICE).get("/book/%d" % appt).get_data(as_text=True)


# ══ M2: الدفع ═══════════════════════════════════════════════════════

def _pay_setup():
    half, full = _reset()
    B.set_setting(A.db_run, "instapay", "doctor@instapay")
    B.set_setting(A.db_run, "wallet", "01000000000")
    return half, full


def _pay(appt_id):
    return _status(appt_id)["pay_status"]


def test_the_client_sees_where_to_pay_only_on_their_own_booking():
    """‏عنوان InstaPay مابيتعرضش على الصفحة العامة -- لصاحب الحجز بس."""
    half, _ = _pay_setup()
    appt = _book(ALICE, half, _slot())
    page = _as(ALICE).get("/book/%d" % appt).get_data(as_text=True)
    assert "doctor@instapay" in page and "01000000000" in page
    assert "300 EGP" in page and 'name="pay_ref"' in page
    for public in (_as().get("/book"), _as(BASEM).get("/book")):
        assert "doctor@instapay" not in public.get_data(as_text=True)


def test_saying_you_paid_is_not_the_same_as_having_paid():
    """‏القاعدة اللي المرحلة كلها عليها: العميل بيوصّل الحالة لـclaimed
    بس. لو أي مسار للعميل وصّلها لـpaid، أي حد يكتب رقم من دماغه ويبقى
    دافع."""
    half, _ = _pay_setup()
    appt = _book(ALICE, half, _slot())
    c = _as(ALICE)
    r = c.post("/book/%d/paid" % appt,
               data={"pay_method": "instapay", "pay_ref": " 9876 5432 "})
    assert "msg=claimed" in r.headers["Location"]
    row = _status(appt)
    assert (row["pay_status"], row["pay_method"], row["pay_ref"]) == (
        "claimed", "instapay", "9876 5432"), row
    assert "Waiting for it to be confirmed" in c.get(
        "/book/%d" % appt).get_data(as_text=True)
    # ‏العميل بيحاول يأكّد لنفسه
    c.post("/admin/appointments/%d/confirm-payment" % appt)
    assert _pay(appt) == "claimed"


def test_a_client_can_correct_a_mistyped_reference_until_it_is_confirmed():
    half, _ = _pay_setup()
    appt = _book(ALICE, half, _slot())
    c = _as(ALICE)
    c.post("/book/%d/paid" % appt, data={"pay_method": "wallet", "pay_ref": "111"})
    c.post("/book/%d/paid" % appt, data={"pay_method": "wallet", "pay_ref": "222"})
    assert _status(appt)["pay_ref"] == "222"
    _as(ADMIN).post("/admin/appointments/%d/confirm-payment" % appt)
    c.post("/book/%d/paid" % appt, data={"pay_method": "wallet", "pay_ref": "333"})
    row = _status(appt)
    assert row["pay_status"] == "paid" and row["pay_ref"] == "222", row


def test_a_payment_report_needs_a_real_reference_and_a_known_method():
    half, _ = _pay_setup()
    appt = _book(ALICE, half, _slot())
    c = _as(ALICE)
    for bad in ({"pay_method": "instapay", "pay_ref": ""},
                {"pay_method": "instapay", "pay_ref": "x"},
                {"pay_method": "instapay", "pay_ref": "9" * 80},
                {"pay_method": "paid", "pay_ref": "12345"}):
        c.post("/book/%d/paid" % appt, data=bad)
        assert _pay(appt) == "unpaid", bad


def test_nobody_else_can_report_or_confirm_a_payment():
    half, _ = _pay_setup()
    appt = _book(ALICE, half, _slot())
    r = _as(BASEM).post("/book/%d/paid" % appt,
                        data={"pay_method": "instapay", "pay_ref": "12345"})
    assert r.status_code == 404
    r = _as().post("/book/%d/paid" % appt,
                   data={"pay_method": "instapay", "pay_ref": "12345"})
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert _pay(appt) == "unpaid"


def test_only_the_admin_handles_the_money():
    """‏الأخصائي بيشغّل التقويم؛ مابيأكّدش استلام ولا بيغيّر الفلوس بتتبعت
    فين. تغيير عنوان InstaPay = تحويل فلوس كل العملاء لحساب تاني."""
    half, _ = _pay_setup()
    appt = _book(ALICE, half, _slot())
    n = _as(NUTRI)
    n.post("/admin/appointments/%d/confirm-payment" % appt)
    assert _pay(appt) == "unpaid"
    r = n.post("/admin/booking-settings",
               data={"action": "save_pay", "instapay": "thief@instapay"})
    assert "msg=admin_only" in r.headers["Location"]
    assert B.get_settings(A.db_rows)["instapay"] == "doctor@instapay"
    assert 'name="instapay"' not in n.get(
        "/admin/booking-settings").get_data(as_text=True)

    a = _as(ADMIN)
    a.post("/admin/booking-settings",
           data={"action": "save_pay", "instapay": "new@instapay", "wallet": ""})
    saved = B.get_settings(A.db_rows)
    assert saved.get("instapay") == "new@instapay" and "wallet" not in saved
    a.post("/admin/appointments/%d/confirm-payment" % appt)
    assert _pay(appt) == "paid"


def test_a_confirmed_payment_shows_on_the_payments_page_and_to_the_client():
    half, _ = _pay_setup()
    appt = _book(ALICE, half, _slot())
    _as(ALICE).post("/book/%d/paid" % appt,
                    data={"pay_method": "instapay", "pay_ref": "REF-778"})
    a = _as(ADMIN)
    page = a.get("/admin/payments").get_data(as_text=True)
    assert "REF-778" in page and "Client says paid" in page
    assert "/admin/appointments/%d/confirm-payment" % appt in page
    r = a.post("/admin/appointments/%d/confirm-payment" % appt)
    assert "msg=pay_confirmed" in r.headers["Location"]
    page = a.get("/admin/payments").get_data(as_text=True)
    assert "300 EGP" in page and "Received" in page
    assert "/admin/appointments/%d/confirm-payment" % appt not in page
    assert "Payment received" in _as(ALICE).get(
        "/book/%d" % appt).get_data(as_text=True)
    # ‏مرة تانية: مافيش حاجة تتغيّر
    r = a.post("/admin/appointments/%d/confirm-payment" % appt)
    assert "msg=pay_stale" in r.headers["Location"]


def test_rejecting_a_paid_booking_leaves_a_refund_to_do_and_records_it():
    """‏الرفض بعد الدفع لازم يسيب أثر: الفلوس عند الأخصائي والعميل مالوش
    موعد. بيظهر "محتاج استرداد" لحد ما الأدمن يسجّل إنه رجّعه."""
    half, _ = _pay_setup()
    appt = _book(ALICE, half, _slot())
    a = _as(ADMIN)
    a.post("/admin/appointments/%d/confirm-payment" % appt)
    a.post("/admin/appointments/%d/reject" % appt, data={"reason": "Travelling"})
    assert B.owes_refund(_status(appt))
    assert "Refund due" in a.get("/admin/payments").get_data(as_text=True)
    assert "will be refunded" in _as(ALICE).get(
        "/book/%d" % appt).get_data(as_text=True)
    r = a.post("/admin/appointments/%d/refund" % appt)
    assert "msg=pay_refunded" in r.headers["Location"]
    assert _pay(appt) == "refunded"
    assert "was refunded" in _as(ALICE).get(
        "/book/%d" % appt).get_data(as_text=True)
    assert "Refund due" not in a.get("/admin/payments").get_data(as_text=True)


def test_a_free_consultation_asks_for_no_payment():
    half, _ = _pay_setup()
    A.db_run("UPDATE services SET price=0 WHERE id=?", (half["id"],))
    free = A.db_row("SELECT * FROM services WHERE id=?", (half["id"],))
    appt = _book(ALICE, free, _slot())
    c = _as(ALICE)
    assert 'name="pay_ref"' not in c.get("/book/%d" % appt).get_data(as_text=True)
    c.post("/book/%d/paid" % appt, data={"pay_method": "instapay", "pay_ref": "123"})
    assert _pay(appt) == "unpaid"
    _as(ADMIN).post("/admin/appointments/%d/confirm-payment" % appt)
    assert _pay(appt) == "unpaid"


# ══ M3: الربط والإشعارات ════════════════════════════════════════════

def _inbox(uid):
    return [r["message"] for r in A.db_rows(
        "SELECT message FROM messages WHERE receiver_id=? ORDER BY id", (uid,))]


def _bell():
    return A.db_rows("SELECT * FROM notifications ORDER BY id")


def test_staff_are_told_about_a_new_request_and_a_reported_payment():
    half, _ = _pay_setup()
    c = _as(ALICE)
    c.post("/book", data={"service": half["id"], "date": "",
                          "slot": B.slot_key(_slot())})
    appt = A.db_row("SELECT id FROM appointments")["id"]
    c.post("/book/%d/paid" % appt, data={"pay_method": "instapay",
                                         "pay_ref": "REF-1"})
    bell = _bell()
    assert [n["type"] for n in bell] == ["booking_request", "booking_payment"], bell
    assert bell[0]["link"] == "/admin/calendar" and "alice" in bell[0]["message"]
    assert "REF-1" in bell[1]["message"] and bell[1]["link"] == "/admin/payments"


def test_the_client_gets_a_message_when_the_request_is_answered():
    half, _ = _reset()
    first = _book(ALICE, half, _slot(hour=9))
    second = _book(ALICE, half, _slot(hour=11))
    _as(NUTRI).post("/admin/appointments/%d/accept" % first, data={})
    _as(NUTRI).post("/admin/appointments/%d/reject" % second,
                    data={"reason": "Clinic closed"})
    got = _inbox(ALICE)
    assert len(got) == 2, got
    assert "اتأكد" in got[0] and "Follow-up" in got[0], got[0]
    assert "اترفض" in got[1] and "Clinic closed" in got[1], got[1]
    assert not _inbox(BASEM), "someone else was told"
    # ‏ضغطة تانية على طلب اترد عليه مابتبعتش رسالة تانية
    _as(NUTRI).post("/admin/appointments/%d/accept" % first, data={})
    assert len(_inbox(ALICE)) == 2


def test_messages_speak_the_clients_language_and_the_clients_clock():
    """‏الأخصائي بيقبل وهو على توقيت دبي وواجهته عربي. الرسالة بتتكتب
    بلغة العميل وساعته هو -- من صفّه في users، مش من جلسة اللي داس."""
    half, _ = _reset()
    start = datetime(2027, 7, 12, 6, 0)          # 10:00 Dubai, 09:00 Cairo
    row = {"start_at": B.to_db(start), "service_name": "Follow-up",
           "admin_note": None, "status": "accepted", "pay_status": "unpaid",
           "client_lang": "en", "client_tz": "Africa/Cairo"}
    subject, body = N.client_text(row, "accepted")
    assert subject == "Appointment confirmed"
    assert "9:00 AM Cairo time" in body and "Monday 12/7" in body, body
    row.update(client_lang="ar")
    assert "9:00 ص بتوقيت القاهرة" in N.client_text(row, "accepted")[1]


def test_a_notice_that_fails_does_not_undo_the_action():
    """‏السيرفر بتاع الإيميل واقع أو جدول الرسايل فيه مشكلة: الموعد اللي
    اتقبل لازم يفضل مقبول."""
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    real = N.db_run

    def broken(*a, **k):
        raise RuntimeError("messages table is down")
    N.db_run = broken
    try:
        r = _as(NUTRI).post("/admin/appointments/%d/accept" % appt, data={})
    finally:
        N.db_run = real
    assert r.status_code == 302 and "msg=accepted" in r.headers["Location"]
    assert _status(appt)["status"] == "accepted"


def test_an_unanswered_request_expires_and_frees_its_slot():
    half, _ = _reset()
    start = _slot(days=5)
    appt = _book(ALICE, half, start)
    now = B.utcnow()
    assert N.tick(now + timedelta(hours=47))["expired"] == [], "expired early"
    done = N.tick(now + timedelta(hours=49))
    assert done["expired"] == [appt], done
    row = _status(appt)
    assert row["status"] == "expired" and row["slot_key"] is None, row
    assert any("انتهت مهلته" in m for m in _inbox(ALICE)), _inbox(ALICE)
    assert _status(_book(BASEM, half, start))["status"] == "pending"
    assert appt not in N.tick(now + timedelta(hours=50))["expired"], \
        "expired twice"


def test_a_pending_request_whose_time_has_passed_expires_too():
    half, _ = _reset()
    start = _slot(days=1)
    appt = _book(ALICE, half, start)
    assert N.tick(start + timedelta(minutes=1))["expired"] == [appt]


def test_an_accepted_appointment_never_expires():
    half, _ = _reset()
    appt = _book(ALICE, half, _slot(days=5))
    B.decide(A.db_row, A.db_run, appt, True)
    assert N.tick(B.utcnow() + timedelta(days=4))["expired"] == []
    assert _status(appt)["status"] == "accepted"


def test_reminders_go_out_once_each_a_day_before_and_an_hour_before():
    half, _ = _reset()
    start = _slot(days=5)
    appt = _book(ALICE, half, start)
    B.decide(A.db_row, A.db_run, appt, True)

    def at(**before):
        return N.tick(start - timedelta(**before))["reminded"]

    assert at(hours=30) == [], "reminded more than a day ahead"
    assert at(hours=23) == [(appt, "day")]
    assert at(hours=22) == [], "the day reminder was sent twice"
    assert at(minutes=90) == [], "the hour reminder went out too early"
    assert at(minutes=60) == [(appt, "hour")]
    assert at(minutes=30) == [], "the hour reminder was sent twice"
    assert N.tick(start + timedelta(minutes=5))["reminded"] == []


def test_a_late_wake_up_sends_one_reminder_not_two():
    """‏الاستضافة المجانية بتنام. لو صحيت والموعد فاضل عليه ٤٠ دقيقة،
    العميل ياخد تذكير واحد ("كمان شوية")، مش تذكير "بكرة" وراه تذكير
    "كمان شوية" في نفس اللحظة."""
    half, _ = _reset()
    start = _slot(days=5)
    appt = _book(ALICE, half, start)
    B.decide(A.db_row, A.db_run, appt, True)
    assert N.tick(start - timedelta(minutes=40))["reminded"] == [(appt, "hour")]
    assert N.tick(start - timedelta(minutes=10))["reminded"] == []


def test_only_accepted_appointments_are_reminded():
    half, _ = _reset()
    start = _slot(days=5)
    pending = _book(ALICE, half, start)
    assert N.tick(start - timedelta(hours=2))["reminded"] == []
    B.decide(A.db_row, A.db_run, pending, False)
    assert N.tick(start - timedelta(minutes=30))["reminded"] == []


def test_reminders_do_not_fill_the_chat():
    half, _ = _reset()
    start = _slot(days=5)
    appt = _book(ALICE, half, start)
    B.decide(A.db_row, A.db_run, appt, True)
    N.tick(start - timedelta(hours=23))
    N.tick(start - timedelta(minutes=50))
    assert _inbox(ALICE) == []


def test_the_next_appointment_card_shows_on_the_clients_plan_page():
    half, _ = _reset()
    c = _as(ALICE)
    assert "Your next appointment" not in c.get(
        "/my-plan", follow_redirects=True).get_data(as_text=True)
    appt = _book(ALICE, half, _slot())
    page = c.get("/my-plan", follow_redirects=True).get_data(as_text=True)
    assert "Your next appointment" in page and "/book/%d" % appt in page
    assert "Awaiting reply" in page and "Unpaid" in page
    assert "Your next appointment" not in _as(BASEM).get(
        "/my-plan", follow_redirects=True).get_data(as_text=True)
    B.decide(A.db_row, A.db_run, appt, False)
    assert "Your next appointment" not in c.get(
        "/my-plan", follow_redirects=True).get_data(as_text=True)


def test_the_dashboard_shows_staff_the_next_confirmed_appointment():
    half, _ = _reset()
    appt = _book(ALICE, half, _slot())
    n = _as(NUTRI)
    assert "Next appointment" not in n.get("/dashboard").get_data(as_text=True)
    B.decide(A.db_row, A.db_run, appt, True)
    page = n.get("/dashboard").get_data(as_text=True)
    assert "Next appointment" in page and "alice" in page


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

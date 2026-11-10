# -*- coding: utf-8 -*-
"""Appointment booking: which slots are open, and who gets one.

Nothing here knows about Flask. The routes (routes_booking.py) hand in the
database functions, the way payments.py is used, so the arithmetic can be
tested on its own.

Three rules everything else rests on:

1. **Times are stored in UTC**, as naive timestamps. The nutritionist works
   on Dubai time (UTC+4, no summer time) and the clients are in Cairo (UTC+2,
   UTC+3 in summer). The gap between them is two hours in winter and one in
   summer, so a time kept in either one's local clock is wrong for the other
   half the year. Working hours are the one thing kept in the nutritionist's
   own clock -- "10:00 to 14:00" means their 10:00 all year.

2. **One grid.** Every slot starts on a multiple of SLOT_MIN from midnight
   and every service lasts a multiple of SLOT_MIN. Two appointments can then
   only collide whole-slot against whole-slot, never by a sliver.

3. **The database decides who wins a slot, not the page.** An active
   appointment holds `slot_key` (its UTC start as text) under a UNIQUE
   constraint. Two people pressing "book" on the same slot in the same second
   both pass every check the page can make; only one INSERT survives. When an
   appointment is rejected or cancelled its slot_key goes NULL -- NULLs never
   collide under UNIQUE, in Postgres and SQLite alike -- and the slot is free
   again.
"""

import os
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SLOT_MIN = 30
MAX_DURATION_MIN = 240
# ‏العميل مايحجزش موعد بعد ربع ساعة -- الأخصائي لازم يلحق يشوف الطلب.
MIN_LEAD_MIN = 120
DAYS_AHEAD = 21
# ‏طلب معلّق بيمسك الموعد لحد ما يتقبل أو يترفض، فعميل واحد مايقدرش
# يقفل الأسبوع كله بطلبات.
MAX_OPEN_PER_CLIENT = 2

ACTIVE = ("pending", "accepted")
DEFAULT_CLIENT_TZ = "Africa/Cairo"
PRO_TZ_NAME = os.environ.get("BOOKING_TZ", "").strip() or "Asia/Dubai"

_FMT = "%Y-%m-%d %H:%M:%S"


class SlotTaken(Exception):
    """Somebody else holds this slot."""


class NotBookable(Exception):
    """The request does not name an open slot."""


def tz(name, fallback=DEFAULT_CLIENT_TZ):
    """A ZoneInfo for `name`, or for the fallback when the name is unknown.

    The name comes out of a users row; a typo there must not take the booking
    page down with it.
    """
    try:
        return ZoneInfo(name or fallback)
    except Exception:
        return ZoneInfo(fallback)


def pro_tz():
    return tz(PRO_TZ_NAME, "Asia/Dubai")


def viewer_tz(user):
    """The clock a page should be written in for this reader."""
    if user and (user.get("is_admin")
                 or user.get("role") in ("admin", "nutritionist")):
        return pro_tz()
    return tz((user or {}).get("timezone"))


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def to_db(dt):
    """Naive UTC datetime -> the text both databases compare correctly."""
    return dt.strftime(_FMT)


def from_db(v):
    """Postgres hands back a datetime, SQLite hands back the text."""
    if v is None or isinstance(v, datetime):
        return v
    return datetime.strptime(str(v)[:19].replace("T", " "), _FMT)


def to_local(utc_naive, zone):
    return utc_naive.replace(tzinfo=timezone.utc).astimezone(zone)


def to_utc(local_naive, zone):
    return (local_naive.replace(tzinfo=zone)
            .astimezone(timezone.utc).replace(tzinfo=None))


def slot_key(start_utc):
    return start_utc.strftime("%Y-%m-%dT%H:%M")


def parse_slot(text):
    """The slot a form sent back, or None. Only whole grid times pass."""
    try:
        dt = datetime.strptime((text or "").strip(), "%Y-%m-%dT%H:%M")
    except ValueError:
        return None
    return dt if dt.minute % SLOT_MIN == 0 else None


def parse_hhmm(text):
    """'09:30' -> 570. None unless it sits on the grid."""
    try:
        h, m = (text or "").strip().split(":")[:2]
        h, m = int(h), int(m)
    except ValueError:
        return None
    if not (0 <= h <= 24 and 0 <= m < 60) or m % SLOT_MIN:
        return None
    total = h * 60 + m
    return total if total <= 24 * 60 else None


def hhmm(minutes):
    return "%02d:%02d" % divmod(int(minutes), 60)


def valid_duration(minutes):
    return (isinstance(minutes, int) and SLOT_MIN <= minutes <= MAX_DURATION_MIN
            and minutes % SLOT_MIN == 0)


def generate_slots(windows, duration_min, busy, start_utc, end_utc,
                   zone=None):
    """Every open start time in [start_utc, end_utc), as naive UTC.

    windows  -- [(weekday, start_min, end_min)] in the nutritionist's clock,
                weekday 0 = Monday
    busy     -- [(start_utc, end_utc)] of appointments already holding time

    A slot is offered only when the whole appointment fits inside one window
    and touches nothing in `busy`. That overlap test is what keeps a
    60-minute booking at 10:00 from leaving 10:30 on offer.
    """
    zone = zone or pro_tz()
    by_day = {}
    for wd, s, e in windows:
        by_day.setdefault(int(wd), []).append((int(s), int(e)))

    day = to_local(start_utc, zone).date() - timedelta(days=1)
    last = to_local(end_utc, zone).date() + timedelta(days=1)
    length = timedelta(minutes=duration_min)
    out = set()
    while day <= last:
        for s, e in by_day.get(day.weekday(), ()):
            t = s
            while t + duration_min <= e:
                local = (datetime(day.year, day.month, day.day)
                         + timedelta(minutes=t))
                begin = to_utc(local, zone)
                finish = begin + length
                if (start_utc <= begin < end_utc
                        and not any(b0 < finish and begin < b1
                                    for b0, b1 in busy)):
                    out.add(begin)
                t += SLOT_MIN
        day += timedelta(days=1)
    return sorted(out)


def _busy(db_rows, start_utc, end_utc):
    q = ",".join("?" * len(ACTIVE))
    rows = db_rows(
        "SELECT start_at, end_at FROM appointments WHERE status IN (%s) "
        "AND start_at < ? AND end_at > ?" % q,
        ACTIVE + (to_db(end_utc), to_db(start_utc)))
    return [(from_db(r["start_at"]), from_db(r["end_at"])) for r in rows]


def open_slots(db_rows, service, start_utc, end_utc, now=None):
    """Bookable starts for one service, from the tables as they are now."""
    now = now or utcnow()
    earliest = max(start_utc, now + timedelta(minutes=MIN_LEAD_MIN))
    latest = min(end_utc, now + timedelta(days=DAYS_AHEAD))
    if earliest >= latest:
        return []
    windows = [(r["weekday"], r["start_min"], r["end_min"])
               for r in db_rows("SELECT weekday, start_min, end_min "
                                "FROM availability")]
    return generate_slots(windows, int(service["duration_min"]),
                          _busy(db_rows, earliest - timedelta(hours=5), latest
                                + timedelta(hours=5)),
                          earliest, latest)


def local_day_bounds(day, zone):
    """[start, end) in UTC of one calendar day on the reader's clock."""
    start = to_utc(datetime(day.year, day.month, day.day), zone)
    nxt = day + timedelta(days=1)
    return start, to_utc(datetime(nxt.year, nxt.month, nxt.day), zone)


def parse_day(text):
    try:
        return date.fromisoformat((text or "").strip())
    except ValueError:
        return None


def _is_unique_violation(exc):
    name = type(exc).__name__
    return ("Integrity" in name or "UniqueViolation" in name
            or "unique" in str(exc).lower())


def create_request(db_row, db_rows, db_run, client_id, service, start_utc,
                   note="", now=None):
    """Book `start_utc` for the client, as a pending request. Returns the id.

    Raises NotBookable when the slot is not on offer, SlotTaken when someone
    else got it first.
    """
    now = now or utcnow()
    held = db_row(
        "SELECT COUNT(*) AS c FROM appointments WHERE client_id=? "
        "AND status='pending'", (client_id,))
    if held and held["c"] >= MAX_OPEN_PER_CLIENT:
        raise NotBookable("too_many")

    end_utc = start_utc + timedelta(minutes=int(service["duration_min"]))
    if start_utc not in open_slots(db_rows, service, start_utc,
                                   start_utc + timedelta(minutes=1), now=now):
        # ‏مش على الشبكة، برّه ساعات العمل، فات وقته -- أو لسه واخده حد.
        taken = db_row("SELECT id FROM appointments WHERE slot_key=?",
                       (slot_key(start_utc),))
        if taken or _busy(db_rows, start_utc, end_utc):
            raise SlotTaken()
        raise NotBookable("closed")

    key = slot_key(start_utc)
    try:
        db_run(
            "INSERT INTO appointments (client_id, service_id, start_at, "
            "end_at, status, slot_key, client_note, price, currency) "
            "VALUES (?,?,?,?,'pending',?,?,?,?)",
            (client_id, service["id"], to_db(start_utc), to_db(end_utc), key,
             (note or "")[:500], int(service.get("price") or 0),
             service.get("currency") or "EGP"))
    except Exception as exc:
        if _is_unique_violation(exc):
            raise SlotTaken()
        raise
    mine = db_row("SELECT id FROM appointments WHERE slot_key=?", (key,))["id"]

    # ‏القيد بيحسم اتنين على **نفس** بداية الموعد. اللي مابيشوفوش: واحد
    # حجز ساعة من ١٠:٠٠ والتاني في نفس اللحظة حجز نص ساعة من ١٠:٣٠ --
    # بدايتين مختلفتين، فالاتنين بيعدّوا. فبعد الإدراج بنبص تاني: لو فيه
    # موعد نشط متداخل اتسجّل قبلنا (رقمه أصغر)، إحنا اللي بننسحب.
    q = ",".join("?" * len(ACTIVE))
    clash = db_row(
        "SELECT id FROM appointments WHERE id < ? AND status IN (%s) "
        "AND start_at < ? AND end_at > ?" % q,
        (mine,) + ACTIVE + (to_db(end_utc), to_db(start_utc)))
    if clash:
        db_run("DELETE FROM appointments WHERE id=?", (mine,))
        raise SlotTaken()
    return mine


def decide(db_row, db_run, appt_id, accept, video_url="", reason="",
           now=None):
    """Accept or reject a pending request. False when it was not pending.

    The WHERE carries status='pending', so a double click -- or two staff
    members answering the same request -- changes the row once.
    """
    row = db_row("SELECT status FROM appointments WHERE id=?", (appt_id,))
    if not row or row["status"] != "pending":
        return False
    stamp = to_db(now or utcnow())
    if accept:
        db_run("UPDATE appointments SET status='accepted', video_url=?, "
               "updated_at=? WHERE id=? AND status='pending'",
               (video_url or None, stamp, appt_id))
    else:
        db_run("UPDATE appointments SET status='rejected', slot_key=NULL, "
               "admin_note=?, updated_at=? WHERE id=? AND status='pending'",
               ((reason or "")[:500] or None, stamp, appt_id))
    return True


def clean_video_url(text):
    """A meeting link the client will be told to click: https or nothing."""
    url = (text or "").strip()
    if not url:
        return ""
    if not url.lower().startswith("https://") or len(url) > 300 \
            or any(c in url for c in " \"'<>\n\r\t"):
        return None
    return url

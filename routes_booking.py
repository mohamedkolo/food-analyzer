# -*- coding: utf-8 -*-
"""Booking a consultation: the client's side and the clinic's calendar.

M1 of replica/architecture.md -- services, working hours, the public booking
page, the request a client sends, and the nutritionist accepting or rejecting
it with a meeting link. Payment, reminders, cancelling and rescheduling are
later milestones and deliberately not here.

Who reaches what:
  /book, /book/slots          anyone, signed in or not
  POST /book                  a signed-in client
  /book/<id>                  the client who owns it, or staff
  /admin/calendar, accept,
  reject, booking-settings    staff (admin and nutritionist)

Another client asking for /book/<id> gets the same 404 as an id that does
not exist: the answer must not say whether the appointment is there.
"""

from datetime import timedelta
from urllib.parse import urlencode

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session)

import booking as B
from core import (
    cur_lang, db_row, db_rows, db_run, get_user_by_id, login_required,
    site_origin, staff_required,
)

bp = Blueprint("booking", __name__)

_DAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت",
            "الأحد"]
_DAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]
_ZONE_NAMES = {"Africa/Cairo": ("القاهرة", "Cairo"),
               "Asia/Dubai": ("دبي", "Dubai")}


# ── عرض الوقت ───────────────────────────────────────────────────────

def _ar():
    return cur_lang() == "ar"


def _day_name(weekday):
    return (_DAYS_AR if _ar() else _DAYS_EN)[weekday]


def _clock(local_dt):
    hour = local_dt.hour % 12 or 12
    if _ar():
        half = "ص" if local_dt.hour < 12 else "م"
    else:
        half = "AM" if local_dt.hour < 12 else "PM"
    return "%d:%02d %s" % (hour, local_dt.minute, half)


def _zone_label(zone):
    ar, en = _ZONE_NAMES.get(zone.key, (None, None))
    if ar:
        return ar if _ar() else en
    return zone.key.split("/")[-1].replace("_", " ")


def _money(piastres, currency):
    if not piastres:
        return "مجانًا" if _ar() else "Free"
    amount = piastres / 100.0
    text = ("%d" % amount) if amount == int(amount) else ("%.2f" % amount)
    if currency == "EGP":
        return "%s %s" % (text, "جنيه" if _ar() else "EGP")
    return "%s %s" % (text, currency)


def _show(row, zone):
    """An appointments row plus the strings a page prints for it."""
    out = dict(row)
    start = B.to_local(B.from_db(row["start_at"]), zone)
    end = B.to_local(B.from_db(row["end_at"]), zone)
    out["day_label"] = "%s %d/%d" % (_day_name(start.weekday()), start.day,
                                     start.month)
    out["time_label"] = "%s – %s" % (_clock(start), _clock(end))
    out["local_date"] = start.date().isoformat()
    out["price_label"] = _money(row.get("price"), row.get("currency"))
    return out


def _current_user():
    return get_user_by_id(session["uid"]) if "uid" in session else None


def _is_staff(user):
    return bool(user and (user.get("is_admin")
                          or user.get("role") in ("admin", "nutritionist")))


def _services(only_active=True):
    sql = "SELECT * FROM services"
    if only_active:
        sql += " WHERE active=1"
    rows = db_rows(sql + " ORDER BY sort_order, id")
    for r in rows:
        r["price_label"] = _money(r.get("price"), r.get("currency"))
    return rows


def _service(service_id):
    try:
        return db_row("SELECT * FROM services WHERE id=? AND active=1",
                      (int(service_id),))
    except (TypeError, ValueError):
        return None


_APPT_SQL = ("SELECT a.*, s.name AS service_name, s.duration_min, "
             "u.name AS client_name, u.phone AS client_phone, "
             "u.email AS client_email "
             "FROM appointments a "
             "LEFT JOIN services s ON s.id = a.service_id "
             "LEFT JOIN users u ON u.id = a.client_id ")


# ── العميل ──────────────────────────────────────────────────────────

@bp.route("/book")
def book():
    user = _current_user()
    zone = B.viewer_tz(user)
    now = B.utcnow()
    services = _services()
    service = _service(request.args.get("service")) or (services[0]
                                                        if services else None)

    days, slots, picked_day = [], [], None
    if service:
        horizon = now + timedelta(days=B.DAYS_AHEAD)
        by_day = {}
        for start in B.open_slots(db_rows, service, now, horizon, now=now):
            local = B.to_local(start, zone)
            by_day.setdefault(local.date(), []).append(
                {"value": B.slot_key(start), "label": _clock(local)})

        wanted = B.parse_day(request.args.get("date"))
        chosen = B.parse_slot(request.args.get("slot"))
        if chosen and wanted not in by_day:
            # ‏راجع من صفحة الدخول بموعد اختاره: نفتح له يوم الموعد ده.
            wanted = B.to_local(chosen, zone).date()
        picked_day = (wanted if wanted in by_day
                      else (min(by_day) if by_day else None))
        today = B.to_local(now, zone).date()
        last = B.to_local(horizon, zone).date()
        d = today
        while d <= last:
            days.append({"iso": d.isoformat(), "name": _day_name(d.weekday()),
                         "num": "%d/%d" % (d.day, d.month),
                         "open": d in by_day, "picked": d == picked_day})
            d += timedelta(days=1)
        slots = by_day.get(picked_day, [])

    mine = []
    if user and not _is_staff(user):
        mine = [_show(r, zone) for r in db_rows(
            _APPT_SQL + "WHERE a.client_id=? ORDER BY a.start_at DESC "
            "LIMIT 10", (user["id"],))]

    return render_template(
        "book.html", user=user, lang=cur_lang(), services=services,
        service=service, days=days, slots=slots,
        picked_day=picked_day.isoformat() if picked_day else "",
        picked_slot=request.args.get("slot", ""), zone_label=_zone_label(zone),
        mine=mine, msg=request.args.get("msg", ""), is_staff=_is_staff(user))


@bp.route("/book/slots")
def book_slots():
    """The open slots of one day on the reader's clock, as JSON."""
    user = _current_user()
    zone = B.viewer_tz(user)
    service = _service(request.args.get("service"))
    day = B.parse_day(request.args.get("date"))
    if not service or not day:
        return jsonify({"error": "bad_request"}), 400
    start, end = B.local_day_bounds(day, zone)
    found = B.open_slots(db_rows, service, start, end)
    return jsonify({
        "date": day.isoformat(), "timezone": zone.key,
        "slots": [{"start": B.slot_key(s),
                   "time": B.to_local(s, zone).strftime("%H:%M")}
                  for s in found]})


@bp.route("/book", methods=["POST"])
def book_create():
    service_id = request.form.get("service", "")
    slot_text = request.form.get("slot", "")
    day = request.form.get("date", "")
    back = {"service": service_id, "date": day}

    user = _current_user()
    if not user:
        # ‏الزائر اختار موعد ولسه مادخلش. بنفتكر اختياره ونرجّعه له بعد
        # الدخول -- مايختارش من الأول. العنوان بيتبني هنا من قيم معروفة،
        # مش بيتاخد من الطلب، فمافيش تحويل لموقع بره.
        session["after_login"] = "/book?" + urlencode(dict(back,
                                                           slot=slot_text))
        return redirect("/login")
    if _is_staff(user):
        return redirect("/admin/calendar")

    service = _service(service_id)
    start = B.parse_slot(slot_text)
    if not service or not start:
        return redirect("/book?" + urlencode(dict(back, msg="pick")))
    try:
        appt_id = B.create_request(db_row, db_rows, db_run, user["id"],
                                   service, start,
                                   note=request.form.get("note", "").strip())
    except B.SlotTaken:
        return redirect("/book?" + urlencode(dict(back, msg="taken")))
    except B.NotBookable as why:
        return redirect("/book?" + urlencode(dict(back, msg=str(why))))
    return redirect("/book/%d?new=1" % appt_id)


@bp.route("/book/<int:appt_id>")
@login_required
def book_status(appt_id):
    user = _current_user()
    row = db_row(_APPT_SQL + "WHERE a.id=?", (appt_id,))
    staff = _is_staff(user)
    if not row or not user or not (staff or row["client_id"] == user["id"]):
        return render_template("404.html", user=user, lang=cur_lang()), 404
    return render_template(
        "book_status.html", user=user, lang=cur_lang(),
        appt=_show(row, B.viewer_tz(user)),
        zone_label=_zone_label(B.viewer_tz(user)), is_staff=staff,
        just_sent=request.args.get("new") == "1")


# ── الأخصائي ────────────────────────────────────────────────────────

@bp.route("/admin/calendar")
@staff_required
def admin_calendar():
    user = _current_user()
    zone = B.pro_tz()
    today = B.to_local(B.utcnow(), zone).date()
    first = B.parse_day(request.args.get("from")) or today
    start, _ = B.local_day_bounds(first, zone)
    _, end = B.local_day_bounds(first + timedelta(days=6), zone)

    pending = [_show(r, zone) for r in db_rows(
        _APPT_SQL + "WHERE a.status='pending' ORDER BY a.start_at")]
    booked = [_show(r, zone) for r in db_rows(
        _APPT_SQL + "WHERE a.status IN ('accepted','completed','no_show') "
        "AND a.start_at >= ? AND a.start_at < ? ORDER BY a.start_at",
        (B.to_db(start), B.to_db(end)))]

    week = []
    for i in range(7):
        d = first + timedelta(days=i)
        week.append({"name": _day_name(d.weekday()),
                     "num": "%d/%d" % (d.day, d.month),
                     "today": d == today,
                     "items": [a for a in booked
                               if a["local_date"] == d.isoformat()]})

    ready = bool(db_row("SELECT id FROM services WHERE active=1 LIMIT 1")
                 and db_row("SELECT id FROM availability LIMIT 1"))
    return render_template(
        "admin_calendar.html", user=user, lang=cur_lang(), pending=pending,
        week=week, zone_label=_zone_label(zone), ready=ready,
        prev_from=(first - timedelta(days=7)).isoformat(),
        next_from=(first + timedelta(days=7)).isoformat(),
        booking_link=site_origin() + "/book", msg=request.args.get("msg", ""))


@bp.route("/admin/appointments/<int:appt_id>/accept", methods=["POST"])
@staff_required
def admin_appointment_accept(appt_id):
    url = B.clean_video_url(request.form.get("video_url"))
    if url is None:
        return redirect("/admin/calendar?msg=bad_link")
    done = B.decide(db_row, db_run, appt_id, True, video_url=url)
    return redirect("/admin/calendar?msg=" + ("accepted" if done else "stale"))


@bp.route("/admin/appointments/<int:appt_id>/reject", methods=["POST"])
@staff_required
def admin_appointment_reject(appt_id):
    done = B.decide(db_row, db_run, appt_id, False,
                    reason=request.form.get("reason", "").strip())
    return redirect("/admin/calendar?msg=" + ("rejected" if done else "stale"))


def _settings_action(form):
    """Apply one form from the settings page. Returns the message code."""
    action = form.get("action", "")

    if action in ("add_service", "update_service"):
        name = form.get("name", "").strip()[:80]
        try:
            duration = int(form.get("duration_min", ""))
            price = int(round(float(form.get("price", "0") or 0) * 100))
        except ValueError:
            return "bad_service"
        if not name or not B.valid_duration(duration) \
                or not 0 <= price <= 100000000:
            return "bad_service"
        if action == "add_service":
            db_run("INSERT INTO services (name, duration_min, price) "
                   "VALUES (?,?,?)", (name, duration, price))
        else:
            db_run("UPDATE services SET name=?, duration_min=?, price=? "
                   "WHERE id=?", (name, duration, price,
                                  form.get("id", type=int)))
        return "saved"

    if action == "toggle_service":
        db_run("UPDATE services SET active = 1 - active WHERE id=?",
               (form.get("id", type=int),))
        return "saved"

    if action == "add_hours":
        weekday = form.get("weekday", type=int)
        start = B.parse_hhmm(form.get("start"))
        end = B.parse_hhmm(form.get("end"))
        if weekday not in range(7) or start is None or end is None \
                or end <= start:
            return "bad_hours"
        db_run("INSERT INTO availability (weekday, start_min, end_min) "
               "VALUES (?,?,?)", (weekday, start, end))
        return "saved"

    if action == "delete_hours":
        db_run("DELETE FROM availability WHERE id=?",
               (form.get("id", type=int),))
        return "saved"

    return "unknown"


@bp.route("/admin/booking-settings", methods=["GET", "POST"])
@staff_required
def admin_booking_settings():
    if request.method == "POST":
        return redirect("/admin/booking-settings?msg="
                        + _settings_action(request.form))
    hours = db_rows("SELECT * FROM availability ORDER BY weekday, start_min")
    for h in hours:
        h["day"] = _day_name(h["weekday"])
        h["from"] = B.hhmm(h["start_min"])
        h["to"] = B.hhmm(h["end_min"])
    return render_template(
        "admin_booking_settings.html", user=_current_user(), lang=cur_lang(),
        services=_services(only_active=False), hours=hours,
        day_names=[_day_name(i) for i in range(7)],
        zone_label=_zone_label(B.pro_tz()), slot_min=B.SLOT_MIN,
        max_duration=B.MAX_DURATION_MIN, msg=request.args.get("msg", ""),
        booking_link=site_origin() + "/book")

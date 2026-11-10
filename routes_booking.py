# -*- coding: utf-8 -*-
"""Booking a consultation: the client's side and the clinic's calendar.

replica/architecture.md, milestones M1-M3: services, working hours, the
public booking page, the request, accepting or rejecting it with a meeting
link (M1); paying by transfer with the admin confirming it (M2); the "next
appointment" card and the notices each side gets (M3). Cancelling and
rescheduling are M4 and deliberately not here.

Who reaches what:
  /book, /book/slots            anyone, signed in or not
  POST /book                    a signed-in client
  /book/<id>, /book/<id>/paid   the client who owns it (staff may view)
  /admin/calendar, accept,
  reject, booking-settings      staff (admin and nutritionist)
  confirm-payment, refund,
  where the money is sent       admin only

The last line follows the rule the rest of the site already keeps: a
nutritionist builds plans and runs the calendar; they do not handle the
money. Changing the InstaPay address is changing where every client's
payment goes.

Another client asking for /book/<id> gets the same 404 as an id that does
not exist: the answer must not say whether the appointment is there.
"""

from datetime import timedelta
from urllib.parse import urlencode

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session)

import booking as B
import booking_notify as N
from core import (
    admin_required, cur_lang, db_row, db_rows, db_run, get_user_by_id,
    login_required, site_origin, staff_required,
)

bp = Blueprint("booking", __name__)


# ── عرض الوقت ───────────────────────────────────────────────────────

def _ar():
    return cur_lang() == "ar"


def _day_name(weekday):
    return B.day_name(weekday, _ar())


def _clock(local_dt):
    return B.clock(local_dt, _ar())


def _zone_label(zone):
    return B.zone_label(zone, _ar())


def _money(piastres, currency):
    return B.money(piastres, currency, _ar())


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
    out["owes_refund"] = B.owes_refund(row)
    return out


def _current_user():
    return get_user_by_id(session["uid"]) if "uid" in session else None


def _is_staff(user):
    return bool(user and (user.get("is_admin")
                          or user.get("role") in ("admin", "nutritionist")))


def _is_admin(user):
    return bool(user and (user.get("is_admin") or user.get("role") == "admin"))


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

    # ‏التأجيل بيستخدم نفس الصفحة: نفس الخدمة، والموعد القديم مابيقفلش
    # على نفسه (skip_id)، والفورم بيتبعت لمسار التأجيل.
    moving = _own_changeable(user, request.args.get("move"))
    if moving:
        service = db_row("SELECT * FROM services WHERE id=?",
                         (moving["service_id"],)) or service
        services = [s for s in services if service and s["id"] == service["id"]]

    days, slots, picked_day = [], [], None
    if service:
        horizon = now + timedelta(days=B.DAYS_AHEAD)
        by_day = {}
        for start in B.open_slots(db_rows, service, now, horizon, now=now,
                                  skip_id=moving["id"] if moving else None):
            if moving and start == B.from_db(moving["start_at"]):
                continue
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
        mine=mine, msg=request.args.get("msg", ""), is_staff=_is_staff(user),
        moving=_show(moving, zone) if moving else None)


def _own_changeable(user, appt_id):
    """The appointment, when it is this client's and can still be changed."""
    try:
        row = db_row(_APPT_SQL + "WHERE a.id=?", (int(appt_id),))
    except (TypeError, ValueError):
        return None
    if (not row or not user or row["client_id"] != user["id"]
            or not B.can_change(row)):
        return None
    return row


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
    N.tell_staff(appt_id, "request")
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
        just_sent=request.args.get("new") == "1",
        can_change=(not staff) and B.can_change(row),
        change_hours=B.CHANGE_LEAD_HOURS,
        can_rate=False,
        # ‏بيانات التحويل بتتعرض لصاحب الموعد بس، مش على الصفحة العامة.
        pay=B.pay_details(db_rows), msg=request.args.get("msg", ""))


@bp.route("/book/<int:appt_id>/paid", methods=["POST"])
@login_required
def book_paid(appt_id):
    """The client reports a transfer. This never marks anything as paid."""
    user = _current_user()
    row = db_row("SELECT client_id FROM appointments WHERE id=?", (appt_id,))
    if not row or not user or row["client_id"] != user["id"]:
        return render_template("404.html", user=user, lang=cur_lang()), 404
    ref = B.clean_pay_ref(request.form.get("pay_ref"))
    if not ref:
        return redirect("/book/%d?msg=bad_ref" % appt_id)
    if not B.claim_payment(db_row, db_run, appt_id,
                           request.form.get("pay_method", ""), ref):
        return redirect("/book/%d?msg=no_claim" % appt_id)
    N.tell_staff(appt_id, "claimed")
    return redirect("/book/%d?msg=claimed" % appt_id)


@bp.route("/book/<int:appt_id>/cancel", methods=["POST"])
@login_required
def book_cancel(appt_id):
    user = _current_user()
    row = db_row("SELECT client_id FROM appointments WHERE id=?", (appt_id,))
    if not row or not user or row["client_id"] != user["id"]:
        return render_template("404.html", user=user, lang=cur_lang()), 404
    if not B.cancel(db_row, db_run, appt_id):
        return redirect("/book/%d?msg=too_late" % appt_id)
    N.tell_staff(appt_id, "cancelled")
    return redirect("/book/%d?msg=cancelled" % appt_id)


@bp.route("/book/<int:appt_id>/reschedule", methods=["POST"])
@login_required
def book_reschedule(appt_id):
    user = _current_user()
    row = db_row("SELECT client_id, service_id FROM appointments WHERE id=?",
                 (appt_id,))
    if not row or not user or row["client_id"] != user["id"]:
        return render_template("404.html", user=user, lang=cur_lang()), 404
    service = db_row("SELECT * FROM services WHERE id=?", (row["service_id"],))
    start = B.parse_slot(request.form.get("slot"))
    back = "/book?" + urlencode({"move": appt_id,
                                 "date": request.form.get("date", "")})
    if not service or not start:
        return redirect(back + "&msg=pick")
    try:
        B.reschedule(db_row, db_rows, db_run, appt_id, service, start)
    except B.SlotTaken:
        return redirect(back + "&msg=taken")
    except B.NotBookable as why:
        if str(why) == "too_late":
            return redirect("/book/%d?msg=too_late" % appt_id)
        return redirect(back + "&msg=closed")
    N.tell_staff(appt_id, "moved")
    return redirect("/book/%d?msg=moved" % appt_id)


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

    now = B.utcnow()
    for a in booked:
        a["past"] = (a["status"] == "accepted"
                     and B.from_db(a["start_at"]) <= now)
    clients = db_rows("SELECT id, name, email FROM users WHERE role='client' "
                      "AND active=1 ORDER BY name LIMIT 500")

    ready = bool(db_row("SELECT id FROM services WHERE active=1 LIMIT 1")
                 and db_row("SELECT id FROM availability LIMIT 1"))
    return render_template(
        "admin_calendar.html", user=user, lang=cur_lang(), pending=pending,
        week=week, zone_label=_zone_label(zone), ready=ready,
        prev_from=(first - timedelta(days=7)).isoformat(),
        next_from=(first + timedelta(days=7)).isoformat(),
        booking_link=site_origin() + "/book", msg=request.args.get("msg", ""),
        is_admin=_is_admin(user), clients=clients, services=_services(),
        today_iso=today.isoformat(), slot_min=B.SLOT_MIN)


@bp.route("/admin/appointments/new", methods=["POST"])
@staff_required
def admin_appointment_new():
    """The nutritionist books a client in by hand (a phone call, WhatsApp)."""
    service = _service(request.form.get("service"))
    client = db_row("SELECT id FROM users WHERE id=? AND role='client'",
                    (request.form.get("client", type=int),))
    day = B.parse_day(request.form.get("date"))
    minutes = B.parse_hhmm(request.form.get("time"))
    url = B.clean_video_url(request.form.get("video_url"))
    if not service or not client or not day or minutes is None or url is None:
        return redirect("/admin/calendar?msg=bad_manual")
    from datetime import datetime as _dt
    start = B.to_utc(_dt(day.year, day.month, day.day)
                     + timedelta(minutes=minutes), B.pro_tz())
    try:
        appt_id = B.create_manual(db_row, db_rows, db_run, client["id"],
                                  service, start, video_url=url)
    except B.SlotTaken:
        return redirect("/admin/calendar?msg=manual_taken")
    except B.NotBookable:
        return redirect("/admin/calendar?msg=bad_manual")
    N.tell_client(appt_id, "accepted", actor_id=session["uid"])
    return redirect("/admin/calendar?msg=accepted&from=%s" % day.isoformat())


@bp.route("/admin/appointments/<int:appt_id>/status/<outcome>",
          methods=["POST"])
@staff_required
def admin_appointment_outcome(appt_id, outcome):
    done = B.set_outcome(db_row, db_run, appt_id, outcome)
    return redirect("/admin/calendar?msg=" + ("saved" if done else "stale"))


@bp.route("/admin/appointments/<int:appt_id>/accept", methods=["POST"])
@staff_required
def admin_appointment_accept(appt_id):
    url = B.clean_video_url(request.form.get("video_url"))
    if url is None:
        return redirect("/admin/calendar?msg=bad_link")
    done = B.decide(db_row, db_run, appt_id, True, video_url=url)
    if done:
        N.tell_client(appt_id, "accepted", actor_id=session["uid"])
    return redirect("/admin/calendar?msg=" + ("accepted" if done else "stale"))


@bp.route("/admin/appointments/<int:appt_id>/reject", methods=["POST"])
@staff_required
def admin_appointment_reject(appt_id):
    done = B.decide(db_row, db_run, appt_id, False,
                    reason=request.form.get("reason", "").strip())
    if done:
        N.tell_client(appt_id, "rejected", actor_id=session["uid"])
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

    if action == "add_block":
        first = B.parse_day(form.get("first"))
        last = B.parse_day(form.get("last")) or first
        if not first or not B.add_block(db_run, first, last,
                                        form.get("reason", "").strip()):
            return "bad_block"
        return "saved"

    if action == "delete_block":
        db_run("DELETE FROM availability_blocks WHERE id=?",
               (form.get("id", type=int),))
        return "saved"

    if action == "save_pay":
        # ‏فين الفلوس بتتبعت: للأدمن بس، حتى لو الطلب جه من أخصائي.
        if not _is_admin(_current_user()):
            return "admin_only"
        for key in B.PAY_SETTING_KEYS:
            limit = 300 if key == "pay_note" else 80
            B.set_setting(db_run, key, form.get(key, "").strip()[:limit])
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
    zone = B.pro_tz()
    blocks = db_rows("SELECT * FROM availability_blocks WHERE end_at > ? "
                     "ORDER BY start_at", (B.to_db(B.utcnow()),))
    for b in blocks:
        first = B.to_local(B.from_db(b["start_at"]), zone).date()
        last = (B.to_local(B.from_db(b["end_at"]), zone)
                - timedelta(minutes=1)).date()
        b["label"] = "%d/%d/%d" % (first.day, first.month, first.year)
        if last != first:
            b["label"] += " – %d/%d/%d" % (last.day, last.month, last.year)
    return render_template(
        "admin_booking_settings.html", user=_current_user(), lang=cur_lang(),
        blocks=blocks, today_iso=B.to_local(B.utcnow(), zone).date().isoformat(),
        services=_services(only_active=False), hours=hours,
        day_names=[_day_name(i) for i in range(7)],
        zone_label=_zone_label(B.pro_tz()), slot_min=B.SLOT_MIN,
        max_duration=B.MAX_DURATION_MIN, msg=request.args.get("msg", ""),
        booking_link=site_origin() + "/book",
        pay=B.get_settings(db_rows), is_admin=_is_admin(_current_user()))


# ── الفلوس: للأدمن بس ───────────────────────────────────────────────

@bp.route("/admin/appointments/<int:appt_id>/confirm-payment",
          methods=["POST"])
@admin_required
def admin_appointment_confirm_payment(appt_id):
    done = B.confirm_payment(db_row, db_run, appt_id)
    if done:
        N.tell_client(appt_id, "paid", actor_id=session["uid"])
    return redirect("/admin/payments?msg=%s#consults"
                    % ("pay_confirmed" if done else "pay_stale"))


@bp.route("/admin/appointments/<int:appt_id>/refund", methods=["POST"])
@admin_required
def admin_appointment_refund(appt_id):
    done = B.mark_refunded(db_row, db_run, appt_id)
    if done:
        N.tell_client(appt_id, "refunded", actor_id=session["uid"])
    return redirect("/admin/payments?msg=%s#consults"
                    % ("pay_refunded" if done else "pay_stale"))


def consult_payments():
    """What /admin/payments shows about consultations: rows and totals."""
    zone = B.pro_tz()
    rows = [_show(r, zone) for r in db_rows(
        _APPT_SQL + "WHERE a.price > 0 ORDER BY a.start_at DESC LIMIT 200")]
    paid = [r for r in rows if r["pay_status"] == "paid"
            and not r["owes_refund"]]
    return {
        "rows": rows,
        "received_label": _money(sum(r["price"] for r in paid) or 0, "EGP")
        if paid else "0",
        "to_confirm": sum(1 for r in rows if r["pay_status"] == "claimed"
                          and not r["owes_refund"]),
        "to_refund": sum(1 for r in rows if r["owes_refund"]),
    }


# ── اللي بيظهر في صفحات تانية ───────────────────────────────────────

@bp.app_template_global("next_appointment")
def next_appointment(user):
    """The card on /my-plan and /dashboard. None when there is nothing ahead.

    A template global, not a value each route passes in: the card sits on
    pages owned by other modules, and a page that does not draw it pays
    nothing.
    """
    try:
        if not user:
            return None
        zone = B.viewer_tz(user)
        now = B.to_db(B.utcnow())
        if _is_staff(user):
            row = db_row(_APPT_SQL + "WHERE a.status='accepted' "
                         "AND a.end_at > ? ORDER BY a.start_at LIMIT 1",
                         (now,))
        else:
            row = db_row(_APPT_SQL + "WHERE a.client_id=? AND a.status IN "
                         "('pending','accepted') AND a.end_at > ? "
                         "ORDER BY a.start_at LIMIT 1", (user["id"], now))
        if not row:
            return None
        out = _show(row, zone)
        out["zone_label"] = _zone_label(zone)
        return out
    except Exception as exc:                      # noqa: BLE001
        print("[booking] next_appointment failed: %s" % exc)
        return None


@bp.app_context_processor
def _booking_badge():
    """Pending booking requests, for the red count beside the calendar link."""
    try:
        if session.get("role") in ("admin", "nutritionist"):
            row = db_row("SELECT COUNT(*) AS c FROM appointments "
                         "WHERE status='pending'")
            return {"booking_pending": row["c"] if row else 0}
    except Exception:                             # noqa: BLE001
        pass
    return {"booking_pending": 0}

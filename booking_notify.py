# -*- coding: utf-8 -*-
"""Telling people what happened to an appointment (M3).

Three audiences, and each hears through the channels it already uses:

  the client   a message in /messages, a push, an email
  the staff    a row in the notifications bell (which pushes and emails too)
  nobody       -- tick() -- the half-hourly pass that expires unanswered
               requests and sends the reminders

Every function here swallows its own failures. A booking that was accepted
must stay accepted when the mail server is down; the notice is the part that
is allowed to fail, never the action it reports.

The client is written to in *their* language and *their* clock -- the columns
on their users row, not the session of whoever pressed the button. The
nutritionist accepts on Dubai time; the message the client reads says Cairo.
"""

import threading

import booking as B
from core import add_notification, db_row, db_rows, db_run, push_to_user
from notifications import send_client_email

# event -> (Arabic, English). {when} {service} {reason} {ref} are filled in.
_TEXTS = {
    "accepted": (
        "✅ موعدك اتأكد: {service} يوم {when}.",
        "✅ Your appointment is confirmed: {service} on {when}."),
    "rejected": (
        "⚠️ طلب الحجز بتاعك ({service} يوم {when}) اترفض.{reason}",
        "⚠️ Your booking request ({service} on {when}) was declined.{reason}"),
    "expired": (
        "⌛ طلب الحجز بتاعك ({service} يوم {when}) انتهت مهلته من غير رد، "
        "والموعد اتفتح تاني. تقدر تحجز موعد غيره.",
        "⌛ Your booking request ({service} on {when}) expired without a "
        "reply and the slot is open again. You can book another time."),
    "paid": (
        "💵 استلمنا تحويل استشارتك ({service} يوم {when}). شكرًا.",
        "💵 We received your payment for {service} on {when}. Thank you."),
    "refunded": (
        "↩️ اترد لك مبلغ استشارة {service} يوم {when}.",
        "↩️ Your payment for {service} on {when} has been refunded."),
    "day": (
        "🔔 تذكير: استشارتك ({service}) بكرة — {when}.",
        "🔔 Reminder: your consultation ({service}) is tomorrow — {when}."),
    "hour": (
        "🔔 استشارتك ({service}) كمان شوية — {when}.",
        "🔔 Your consultation ({service}) starts soon — {when}."),
}
_SUBJECTS = {
    "accepted": ("موعدك اتأكد", "Appointment confirmed"),
    "rejected": ("طلب الحجز اترفض", "Booking request declined"),
    "expired": ("طلب الحجز انتهت مهلته", "Booking request expired"),
    "paid": ("استلمنا الدفع", "Payment received"),
    "refunded": ("تم رد المبلغ", "Payment refunded"),
    "day": ("تذكير بموعدك", "Appointment reminder"),
    "hour": ("موعدك كمان شوية", "Your appointment starts soon"),
}
_REFUND_NOTE = (" المبلغ اللي حوّلته هيترد لك.",
                " The amount you transferred will be refunded.")
# ‏التذكير مابيتحطش في الرسايل: الشات للكلام بين العميل والأخصائي، وتذكيرين
# لكل موعد بيغرّقوه.
_NO_CHAT = ("day", "hour")


def _load(appt_id):
    return db_row(
        "SELECT a.*, s.name AS service_name, u.name AS client_name, "
        "u.email AS client_email, u.lang AS client_lang, "
        "u.timezone AS client_tz FROM appointments a "
        "LEFT JOIN services s ON s.id = a.service_id "
        "LEFT JOIN users u ON u.id = a.client_id WHERE a.id=?", (appt_id,))


def _sender(actor_id=None):
    """Whose name the automatic message carries in the client's chat."""
    if actor_id:
        return actor_id
    row = db_row("SELECT id FROM users WHERE role='admin' OR is_admin=1 "
                 "ORDER BY id LIMIT 1")
    return row["id"] if row else None


def client_text(row, event):
    """(subject, body) for the client, in their language and clock."""
    ar = (row.get("client_lang") or "ar") != "en"
    pick = 0 if ar else 1
    reason = ""
    if event == "rejected":
        if row.get("admin_note"):
            reason = (" السبب: %s." if ar else " Reason: %s.") % row["admin_note"]
        if B.owes_refund(row):
            reason += _REFUND_NOTE[pick]
    if event == "expired" and B.owes_refund(row):
        reason = _REFUND_NOTE[pick]
    body = _TEXTS[event][pick].format(
        service=row.get("service_name") or ("استشارة" if ar else "consultation"),
        when=B.when(row["start_at"], B.tz(row.get("client_tz")), ar),
        reason=reason)
    if event == "expired":
        body += reason
    return _SUBJECTS[event][pick], body


def tell_client(appt_id, event, actor_id=None):
    """Message + push + email to the client. Never raises."""
    try:
        row = _load(appt_id)
        if not row:
            return False
        subject, body = client_text(row, event)
        link = "/book/%d" % appt_id
        if event not in _NO_CHAT:
            sender = _sender(actor_id)
            if sender and sender != row["client_id"]:
                db_run("INSERT INTO messages (sender_id, receiver_id, message)"
                       " VALUES (?,?,?)", (sender, row["client_id"], body))
        push_to_user(row["client_id"], subject, body, url=link)
        if row.get("client_email"):
            threading.Thread(
                target=send_client_email,
                args=(row["client_email"], subject, body, link),
                daemon=True).start()
        return True
    except Exception as exc:                      # noqa: BLE001
        print("[booking] tell_client(%s, %s) failed: %s"
              % (appt_id, event, exc))
        return False


def tell_staff(appt_id, event):
    """The bell (and through it push + admin email). Never raises.

    Written in Arabic like every other row in the bell.
    """
    try:
        row = _load(appt_id)
        if not row:
            return False
        who = row.get("client_name") or "عميل"
        at = B.when(row["start_at"], B.pro_tz(), True)
        if event == "request":
            add_notification(
                db_run, "booking_request", "طلب حجز جديد",
                "%s طلب %s يوم %s." % (who, row.get("service_name") or "استشارة", at),
                link="/admin/calendar", related_user_id=row["client_id"])
        elif event == "claimed":
            add_notification(
                db_run, "booking_payment", "عميل بلّغ بتحويل",
                "%s بيقول إنه حوّل %s (رقم العملية: %s). راجع حسابك وأكّد الاستلام."
                % (who, B.money(row["price"], row["currency"], True),
                   row.get("pay_ref") or "-"),
                link="/admin/payments", related_user_id=row["client_id"])
        elif event == "cancelled":
            note = " كان محوّل، فمحتاج استرداد." if B.owes_refund(row) else ""
            add_notification(
                db_run, "booking_request", "عميل لغى موعده",
                "%s لغى %s يوم %s، والموعد اتفتح تاني.%s"
                % (who, row.get("service_name") or "استشارة", at, note),
                link="/admin/payments" if note else "/admin/calendar",
                related_user_id=row["client_id"])
        elif event == "moved":
            add_notification(
                db_run, "booking_request", "عميل أجّل موعده",
                "%s نقل %s ليوم %s. الطلب مستني ردك."
                % (who, row.get("service_name") or "استشارة", at),
                link="/admin/calendar", related_user_id=row["client_id"])
        return True
    except Exception as exc:                      # noqa: BLE001
        print("[booking] tell_staff(%s, %s) failed: %s"
              % (appt_id, event, exc))
        return False


def tick(now=None):
    """One pass of the scheduled work. Returns what it did, for the tests.

    Called from the meal-reminder loop that already runs every half hour,
    on purpose: a second loop on its own timer would wake the database at
    its own times too, and waking it is what the monthly quota is spent on
    (README, rule 1). It is never tied to /health or the keep-awake ping.

    On a free host the service sleeps when nobody visits, and nothing runs
    while it sleeps. So the reminders are "due and not yet sent", not "it is
    exactly 24 hours before": the first pass after waking sends whatever is
    still ahead, once.
    """
    done = {"expired": [], "reminded": []}
    try:
        done["expired"] = B.expire_stale(db_rows, db_run, now=now)
        for appt_id in done["expired"]:
            tell_client(appt_id, "expired")
    except Exception as exc:                      # noqa: BLE001
        print("[booking] expiry pass failed: %s" % exc)
    try:
        done["reminded"] = B.due_reminders(db_rows, db_run, now=now)
        for appt_id, kind in done["reminded"]:
            tell_client(appt_id, kind)
    except Exception as exc:                      # noqa: BLE001
        print("[booking] reminder pass failed: %s" % exc)
    return done

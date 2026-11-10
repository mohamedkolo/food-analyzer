# -*- coding: utf-8 -*-
"""The client's day-to-day: water, meal notes, recommendations, ratings.

These are the pieces of the client app that sit around the meal plan --
what the client records between sessions, and what the nutritionist leaves
for them to read. The bottom bar and the (+) sheet in base.html are the way
in; this file is what they post to.

Each thing a client writes here is theirs alone: every query carries
`user_id = session uid`, taken from the session and never from the form.
The nutritionist reads it from the client's profile, and writes the
recommendations and the water goal there.
"""

from datetime import datetime, timedelta

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session)

import booking as B
from core import (
    cur_lang, db_row, db_rows, db_run, get_user_by_id, login_required,
    staff_required,
)

bp = Blueprint("clientapp", __name__)

WATER_MIN_ML, WATER_MAX_ML = 50, 2000
WATER_GOAL_MIN, WATER_GOAL_MAX, WATER_GOAL_DEFAULT = 500, 6000, 2000
REC_KINDS = ("goal", "avoid", "note")
_MEAL_KEY_MAX = 30


def _today_bounds(user):
    """Today, on the client's own clock, as a UTC range.

    A glass of water at 00:30 in Cairo belongs to the new day in Cairo. On
    the server's clock (UTC) it would still be yesterday.
    """
    zone = B.tz((user or {}).get("timezone"))
    return B.local_day_bounds(B.to_local(B.utcnow(), zone).date(), zone)


def _meal_day():
    """The date meal_checks files today's meals under.

    Deliberately the same expression /track/meal uses (the server's date),
    not the client's clock: a note has to land on the same day as the tick
    it belongs to, or the two disagree for the hours either side of midnight.
    """
    return datetime.now().strftime("%Y-%m-%d")


def _goal(user):
    try:
        goal = int((user or {}).get("water_goal_ml") or WATER_GOAL_DEFAULT)
    except (TypeError, ValueError):
        goal = WATER_GOAL_DEFAULT
    return goal if WATER_GOAL_MIN <= goal <= WATER_GOAL_MAX else WATER_GOAL_DEFAULT


# ── المياه ──────────────────────────────────────────────────────────

def water_state(user):
    start, end = _today_bounds(user)
    row = db_row("SELECT COALESCE(SUM(amount_ml), 0) AS total FROM water_log "
                 "WHERE user_id=? AND logged_at >= ? AND logged_at < ?",
                 (user["id"], B.to_db(start), B.to_db(end)))
    total = int((row or {}).get("total") or 0)
    goal = _goal(user)
    return {"total": total, "goal": goal,
            "pct": min(100, round(total * 100 / goal))}


@bp.app_template_global("water_today")
def water_today(user):
    try:
        return water_state(user) if user else None
    except Exception as exc:                      # noqa: BLE001
        print("[client] water_today failed: %s" % exc)
        return None


def _wants_json():
    return request.headers.get("X-Requested-With") == "fetch"


@bp.route("/water", methods=["POST"])
@login_required
def water_add():
    user = get_user_by_id(session["uid"])
    try:
        amount = int(request.form.get("amount_ml", ""))
    except ValueError:
        amount = 0
    ok = WATER_MIN_ML <= amount <= WATER_MAX_ML
    if ok:
        db_run("INSERT INTO water_log (user_id, amount_ml, logged_at) "
               "VALUES (?,?,?)", (user["id"], amount, B.to_db(B.utcnow())))
    if _wants_json():
        return jsonify(dict(water_state(user), ok=ok)), (200 if ok else 400)
    return redirect("/my-plan#water")


@bp.route("/water/undo", methods=["POST"])
@login_required
def water_undo():
    """Take back the last glass logged today -- a mis-tap, not an edit tool."""
    user = get_user_by_id(session["uid"])
    start, end = _today_bounds(user)
    last = db_row("SELECT id FROM water_log WHERE user_id=? AND logged_at >= ? "
                  "AND logged_at < ? ORDER BY id DESC LIMIT 1",
                  (user["id"], B.to_db(start), B.to_db(end)))
    if last:
        db_run("DELETE FROM water_log WHERE id=? AND user_id=?",
               (last["id"], user["id"]))
    if _wants_json():
        return jsonify(dict(water_state(user), ok=bool(last)))
    return redirect("/my-plan#water")


# ── ملاحظات الوجبات: تخطّي وتعليق ───────────────────────────────────

@bp.app_template_global("meal_notes_today")
def meal_notes_today(user):
    """{meal_key: {skipped, comment}} for the client's today."""
    try:
        if not user:
            return {}
        rows = db_rows("SELECT meal_key, skipped, comment FROM meal_notes "
                       "WHERE user_id=? AND check_date=?",
                       (user["id"], _meal_day()))
        return {r["meal_key"]: r for r in rows}
    except Exception as exc:                      # noqa: BLE001
        print("[client] meal_notes_today failed: %s" % exc)
        return {}


@bp.route("/track/meal-note", methods=["POST"])
@login_required
def track_meal_note():
    """Mark today's meal as skipped, and/or leave a line about it."""
    user = get_user_by_id(session["uid"])
    key = (request.form.get("meal_key") or "").strip()[:_MEAL_KEY_MAX]
    if not key:
        return jsonify({"ok": False}), 400
    skipped = 1 if request.form.get("skipped") == "1" else 0
    comment = " ".join((request.form.get("comment") or "").split())[:300]
    day = _meal_day()
    db_run("DELETE FROM meal_notes WHERE user_id=? AND check_date=? "
           "AND meal_key=?", (user["id"], day, key))
    if skipped or comment:
        db_run("INSERT INTO meal_notes (user_id, check_date, meal_key, "
               "skipped, comment) VALUES (?,?,?,?,?)",
               (user["id"], day, key, skipped, comment or None))
    if skipped:
        # ‏وجبة متخطّية مش وجبة اتاكلت: العلامتين مايتجمعوش.
        db_run("DELETE FROM meal_checks WHERE user_id=? AND check_date=? "
               "AND meal_key=?", (user["id"], day, key))
    return jsonify({"ok": True, "skipped": skipped, "comment": comment})


# ── التوصيات ────────────────────────────────────────────────────────

def recs_for(client_id):
    out = {k: [] for k in REC_KINDS}
    for r in db_rows("SELECT * FROM recommendations WHERE client_id=? "
                     "ORDER BY id", (client_id,)):
        if r["kind"] in out:
            out[r["kind"]].append(r)
    return out


@bp.app_template_global("client_recs")
def client_recs(client_id):
    try:
        return recs_for(client_id)
    except Exception as exc:                      # noqa: BLE001
        print("[client] client_recs failed: %s" % exc)
        return {k: [] for k in REC_KINDS}


@bp.route("/recommendations")
@login_required
def recommendations():
    user = get_user_by_id(session["uid"])
    return render_template("recommendations.html", user=user, lang=cur_lang(),
                           recs=recs_for(user["id"]), water_goal=_goal(user))


@bp.route("/admin/users/<int:uid>/recommendations", methods=["POST"])
@staff_required
def admin_recommendations(uid):
    action = request.form.get("action", "")
    client = db_row("SELECT id FROM users WHERE id=? AND role='client'", (uid,))
    if client and action == "add":
        kind = request.form.get("kind", "")
        body = " ".join((request.form.get("body") or "").split())[:300]
        if kind in REC_KINDS and body:
            db_run("INSERT INTO recommendations (client_id, kind, body) "
                   "VALUES (?,?,?)", (uid, kind, body))
    elif client and action == "delete":
        # ‏client_id في الشرط: رقم توصية بتاعة عميل تاني مايتمسحش من هنا.
        db_run("DELETE FROM recommendations WHERE id=? AND client_id=?",
               (request.form.get("id", type=int), uid))
    elif client and action == "water_goal":
        goal = request.form.get("water_goal_ml", type=int)
        if goal and WATER_GOAL_MIN <= goal <= WATER_GOAL_MAX:
            db_run("UPDATE users SET water_goal_ml=? WHERE id=?", (goal, uid))
    return redirect("/admin/users/%d#recs" % uid)


@bp.app_template_global("client_day")
def client_day(client_id):
    """What the nutritionist sees of a client's today, on their profile."""
    try:
        client = get_user_by_id(client_id)
        if not client:
            return None
        return {"water": water_state(client),
                "notes": list(meal_notes_today(client).values())}
    except Exception as exc:                      # noqa: BLE001
        print("[client] client_day failed: %s" % exc)
        return None


# ── تقييم الاستشارة ─────────────────────────────────────────────────

RATE_WINDOW_DAYS = 14


def rateable(appt, user, now=None):
    """Only the client, only a session that took place, only once."""
    now = now or B.utcnow()
    if (not appt or not user or appt["client_id"] != user["id"]
            or appt["status"] != "completed"):
        return False
    if B.from_db(appt["end_at"]) < now - timedelta(days=RATE_WINDOW_DAYS):
        return False
    return not db_row("SELECT id FROM appointment_ratings "
                      "WHERE appointment_id=?", (appt["id"],))


@bp.app_template_global("pending_rating")
def pending_rating(user):
    """The most recent finished session the client has not rated yet."""
    try:
        if not user or user.get("is_admin") \
                or user.get("role") in ("admin", "nutritionist"):
            return None
        cutoff = B.utcnow() - timedelta(days=RATE_WINDOW_DAYS)
        return db_row(
            "SELECT a.id, s.name AS service_name FROM appointments a "
            "LEFT JOIN services s ON s.id = a.service_id "
            "WHERE a.client_id=? AND a.status='completed' AND a.end_at >= ? "
            "AND NOT EXISTS (SELECT 1 FROM appointment_ratings r "
            "WHERE r.appointment_id = a.id) ORDER BY a.end_at DESC LIMIT 1",
            (user["id"], B.to_db(cutoff)))
    except Exception as exc:                      # noqa: BLE001
        print("[client] pending_rating failed: %s" % exc)
        return None


@bp.route("/book/<int:appt_id>/rate", methods=["POST"])
@login_required
def book_rate(appt_id):
    user = get_user_by_id(session["uid"])
    appt = db_row("SELECT * FROM appointments WHERE id=?", (appt_id,))
    if not appt or appt["client_id"] != user["id"]:
        return render_template("404.html", user=user, lang=cur_lang()), 404
    score = request.form.get("score", type=int)
    if not rateable(appt, user) or not score or not 1 <= score <= 10:
        return redirect("/book/%d" % appt_id)
    try:
        db_run("INSERT INTO appointment_ratings (appointment_id, score, "
               "comment, anonymous) VALUES (?,?,?,?)",
               (appt_id, score,
                " ".join((request.form.get("comment") or "").split())[:500]
                or None, 1 if request.form.get("anonymous") else 0))
    except Exception:                             # noqa: BLE001
        pass                # ‏UNIQUE: ضغطتين على "إرسال" = تقييم واحد
    return redirect("/book/%d?msg=rated" % appt_id)


def ratings_overview(limit=30):
    """For the calendar page: the scores, with the name hidden when asked.

    An anonymous rating must not be traceable from the page that shows it,
    so it carries no name, no appointment link and no exact time.
    """
    rows = db_rows(
        "SELECT r.score, r.comment, r.anonymous, r.created_at, "
        "u.name AS client_name, s.name AS service_name "
        "FROM appointment_ratings r "
        "JOIN appointments a ON a.id = r.appointment_id "
        "LEFT JOIN users u ON u.id = a.client_id "
        "LEFT JOIN services s ON s.id = a.service_id "
        "ORDER BY r.id DESC LIMIT ?", (limit,))
    out = []
    for r in rows:
        out.append({"score": r["score"], "comment": r["comment"],
                    "service_name": r["service_name"],
                    "client_name": None if r["anonymous"] else r["client_name"]})
    avg = round(sum(r["score"] for r in out) / len(out), 1) if out else None
    return {"rows": out, "average": avg}


@bp.route("/plan")
@login_required
def current_plan():
    """The bottom bar's "Plan" tab: straight to the plan in force."""
    latest = db_row("SELECT id FROM plan_requests WHERE client_id=? AND "
                    "status='approved' ORDER BY updated_at DESC LIMIT 1",
                    (session["uid"],))
    return redirect("/my-plans-history/%d" % latest["id"] if latest
                    else "/my-plan")

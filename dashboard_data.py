# -*- coding: utf-8 -*-
"""‏أرقام لوحة الأدمن، من الجداول الحقيقية.

‏اللوحة الجديدة اتصممت على شكل داشبورد بنكي (رصيد، مصاريف الشهر، آخر
العمليات)، وده اتنقل لعيادة: "الرصيد" بقى العملاء اللي علّموا على وجبة
النهارده، و"آخر العمليات" بقت آخر وجبات اتعلّم عليها. مفيش رقم وهمي:
لو مفيش بيانات، الرقم صفر والقايمة فاضية برسالة.
"""

from datetime import date, datetime, timedelta

MEAL_NAMES = {
    "breakfast": ("الفطار", "Breakfast"), "lunch": ("الغدا", "Lunch"),
    "dinner": ("العشا", "Dinner"), "snack": ("سناك", "Snack"),
    "snack1": ("سناك ١", "Snack 1"), "snack2": ("سناك ٢", "Snack 2"),
    "meal1": ("وجبة ١", "Meal 1"), "meal2": ("وجبة ٢", "Meal 2"),
    "pre_workout": ("قبل التمرين", "Pre-workout"),
    "post_workout": ("بعد التمرين", "Post-workout"),
    "iftar": ("الفطار (رمضان)", "Iftar"), "suhoor": ("السحور", "Suhoor"),
}


def greeting(now, is_ar):
    h = now.hour
    if 5 <= h < 12:
        return "صباح الخير" if is_ar else "Good morning"
    if 12 <= h < 17:
        return "مساء الخير" if is_ar else "Good afternoon"
    return "مساء الخير" if is_ar else "Good evening"


def meal_name(key, is_ar):
    ar, en = MEAL_NAMES.get(key, (key, key))
    return ar if is_ar else en


def _day(v):
    # ‏SQLite بيرجّع التاريخ نص، وPostgres بيرجّعه date.
    if isinstance(v, (date, datetime)):
        return v if not isinstance(v, datetime) else v.date()
    return date.fromisoformat(str(v)[:10])


def clients_logging_week(db_rows, today):
    """لكل يوم من آخر ٧ أيام: كام عميل علّم على وجبة واحدة على الأقل.

    ‏بنعدّ عملاء مش علامات: عميل علّم على ٥ وجبات وعميل علّم على واحدة
    الاتنين "التزموا النهارده"، والسؤال اللي اللوحة بتجاوب عليه هو مين
    لسه ماشي مع الخطة، مش كام زرار اتداس."""
    start = today - timedelta(days=6)
    try:
        rows = db_rows("SELECT DISTINCT user_id, check_date FROM meal_checks"
                       " WHERE check_date >= ? AND check_date <= ?", (start, today))
    except Exception as e:  # noqa: BLE001
        print(f"[dashboard] week query error: {e}")
        rows = []
    per_day = {}
    for r in rows or []:
        d = _day(r["check_date"])
        per_day.setdefault(d, set()).add(r["user_id"])
    out = []
    for i in range(7):
        d = start + timedelta(days=i)
        out.append({"date": d.isoformat(), "dow": d.weekday(), "count": len(per_day.get(d, ()))})
    return out


def recent_ticks(db_rows, limit=6):
    """آخر وجبات العملاء علّموا عليها. الجدول مافيهوش ساعة، فالترتيب
    باليوم وبعدين بترتيب التسجيل."""
    try:
        rows = db_rows("SELECT m.user_id, m.check_date, m.meal_key, u.name"
                       " FROM meal_checks m JOIN users u ON u.id = m.user_id"
                       " ORDER BY m.check_date DESC, m.id DESC LIMIT ?", (limit,))
    except Exception as e:  # noqa: BLE001
        print(f"[dashboard] recent query error: {e}")
        rows = []
    return [{"user_id": r["user_id"], "name": r.get("name") or "-",
             "meal_key": r["meal_key"], "date": _day(r["check_date"])} for r in rows or []]


# ═══ أجزاء جاية من البرونت، ببيانات حقيقية ═══

# ‏الهدف متخزّن بأسامي كتير على مدار السنين (الفورم القديم والجديد
# وبرامج الرياضة)، فبنلمّهم في تلات مجموعات.
_LOSE = {"weight_loss", "cutting", "lose", "fat_loss"}
_GAIN = {"muscle_gain", "bulking", "gain", "weight_gain"}


def goal_breakdown(db_rows):
    """مكان "Macro breakdown" في البرونت: العملاء حسب الهدف."""
    try:
        rows = db_rows("SELECT goal FROM users WHERE role='client' AND active=1")
    except Exception as e:  # noqa: BLE001
        print(f"[dashboard] goals query error: {e}")
        rows = []
    out = {"lose": 0, "keep": 0, "gain": 0}
    for r in rows or []:
        g = (r.get("goal") or "").strip().lower()
        out["lose" if g in _LOSE else "gain" if g in _GAIN else "keep"] += 1
    out["total"] = sum(out.values())
    return out


def plan_cards(db_rows, now):
    """مكان "Your cards": كل باقة وعدد اللي معاهم وصول ليها دلوقتي."""
    from payments import PRICING
    counts = {k: set() for k in PRICING}
    try:
        for r in db_rows("SELECT user_id, plan_key FROM payments WHERE status='completed'"
                         " AND expires_at > ?", (now,)) or []:
            counts.setdefault(r["plan_key"], set()).add(r["user_id"])
        for r in db_rows("SELECT user_id, plan_key FROM subscriptions WHERE status IN"
                         " ('active','trialing') AND current_period_end > ?", (now,)) or []:
            counts.setdefault(r["plan_key"], set()).add(r["user_id"])
    except Exception as e:  # noqa: BLE001
        print(f"[dashboard] plan cards error: {e}")
    return [{"key": k, "name": p.get("name", k), "name_en": p.get("name_en", k),
             "icon": p.get("icon", ""), "count": len(counts.get(k, ()))}
            for k, p in PRICING.items()]


def streak_leaders(db_rows, streak_of, limit=5):
    """مكان "Rewards": العملاء اللي ماشيين أيام ورا بعض بالتزام كامل.
    من غير نقاط -- العدد هو الأيام نفسها."""
    try:
        clients = db_rows("SELECT id, name FROM users WHERE role='client' AND active=1")
    except Exception as e:  # noqa: BLE001
        print(f"[dashboard] leaders query error: {e}")
        clients = []
    out = []
    for c in clients or []:
        try:
            s = streak_of(c["id"])
        except Exception:  # noqa: BLE001
            continue
        if s.get("current_streak", 0) > 0:
            out.append({"id": c["id"], "name": c.get("name") or "-",
                        "current": s["current_streak"], "best": s.get("best_streak", 0)})
    out.sort(key=lambda r: (-r["current"], -r["best"]))
    return out[:limit]

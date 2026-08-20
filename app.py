# -*- coding: utf-8 -*-
"""NutraX routes.

The app object, configuration, database layer, auth decorators and shared
template helpers live in core.py. This file holds the routes.
"""

from core import *                      # noqa: F401,F403
# names starting with an underscore are not covered by `import *`
from core import (                      # noqa: F401
    _CULTURE_EN, _GENDER_EN, _clear_login_attempts, _is_login_rate_limited,
    _login_msg, _plan_name, _record_failed_login,
)

# the public, crawlable pages live on their own
import routes_public
app.register_blueprint(routes_public.bp)

# everything that touches money
import routes_billing
app.register_blueprint(routes_billing.bp)

# building and editing a plan
import routes_plans
app.register_blueprint(routes_plans.bp)

# how a plan is actually built -- pure logic, no routes
from plan_engine import (              # noqa: F401
    ALLERGY_KEYWORDS, parse_user_exclusions, filter_meals_by_exclusions,
    filter_carbs, _rank_by_condition, _apply_clinical_safety_caps,
    generate_weekly_plan, get_allowed_forbidden, build_pdf, _has,
)


@app.route("/login", methods=["GET", "POST"])
@app.route("/", methods=["POST"])
def login():
    if "uid" in session: return redirect("/dashboard")
    lang = session.get("lang", "ar")
    error = ""
    is_success = False
    tab = request.args.get("tab", "login")
    if request.method == "POST":
        check_email = request.form.get("email", "").lower().strip()
        if is_email_blocked(check_email):
            error = _login_msg("blocked", lang)
            return render_template("login.html", error=error, tab="login", lang=lang, is_success=False)
        action = request.form.get("action")
        if action == "login":
            if _is_login_rate_limited(check_email):
                error = _login_msg("rate_limited", lang)
                return render_template("login.html", error=error, tab="login", lang=lang, is_success=False)
            u = get_user(request.form.get("email","").lower(), request.form.get("password",""))
            if u:
                if not u.get("active", 1):
                    error = _login_msg("inactive", lang)
                else:
                    _clear_login_attempts(check_email)
                    session.permanent = True
                    session["uid"] = u["id"]
                    session["lang"] = u["lang"] or "ar"
                    session["role"] = get_user_role(u)
                    return redirect("/dashboard")
            else:
                _record_failed_login(check_email)
                error = _login_msg("bad_creds", lang)
        elif action == "register":
            tab = "register"
            name = request.form.get("name","").strip()
            email = request.form.get("reg_email","").lower().strip()
            pw = request.form.get("reg_password","")
            country = request.form.get("country","")
            age = request.form.get("age","")
            phone = request.form.get("phone","").strip()
            if not name or not email or not pw or not country or not phone:
                error = _login_msg("all_required", lang)
            elif len(pw) < 6:
                error = _login_msg("pw_short", lang)
            else:
                try: age_int = int(age) if age else None
                except: age_int = None
                r = register(name, email, pw, country, age_int, phone)
                if r == "ok":
                    error = _login_msg("registered", lang)
                    is_success = True
                    tab = "login"
                else:
                    error = _login_msg("email_taken", lang)
    return render_template("login.html", error=error, tab=tab, lang=lang, is_success=is_success)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/lang/<l>")
def set_lang(l):
    if l in ["ar","en"]: session["lang"] = l
    return redirect(request.referrer or "/dashboard")

@app.route("/dashboard")
@login_required
def dashboard():
    u = get_user_by_id(session["uid"])
    role = get_user_role(u)
    if role == "client":
        return redirect("/my-plan")

    pending_count = 0
    total_clients = 0
    total_plans = 0
    recent_requests = []
    unread_messages = 0
    try:
        pending_count = get_pending_requests_count()
        r = db_row("SELECT COUNT(*) as cnt FROM users WHERE role='client'")
        total_clients = r.get("cnt", 0) if r else 0
        r2 = db_row("SELECT COUNT(*) as cnt FROM plan_requests WHERE status='approved'")
        total_plans = r2.get("cnt", 0) if r2 else 0
        recent_requests = db_rows("SELECT * FROM plan_requests ORDER BY created_at DESC LIMIT 5")
        r3 = db_row("SELECT COUNT(*) as cnt FROM messages WHERE receiver_id=? AND is_read=0", (session["uid"],))
        unread_messages = r3.get("cnt", 0) if r3 else 0
    except:
        pass

    analytics = build_admin_analytics(db_rows)
    at_risk = get_at_risk_clients()

    return render_template("dashboard.html", user=u, lang=session.get("lang","ar"),
                           role=role, pending_count=pending_count, total_clients=total_clients,
                           total_plans=total_plans, recent_requests=recent_requests,
                           unread_messages=unread_messages, renewals_soon=analytics["renewals_soon"],
                           recently_lost=analytics["recently_lost"], at_risk_clients=at_risk)

COUNTRY_DIAL_CODES = {
    "مصر": "20", "السعودية": "966", "الإمارات": "971", "الكويت": "965",
    "قطر": "974", "البحرين": "973", "عمان": "968", "الأردن": "962",
    "لبنان": "961", "المغرب": "212", "الجزائر": "213", "تونس": "216",
}

def build_whatsapp_link(phone, country=None):
    """يحوّل رقم العميل المحلي لرابط واتساب صحيح بكود الدولة."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    code = COUNTRY_DIAL_CODES.get((country or "").strip())
    if code:
        if digits.startswith(code):
            pass  # الرقم أصلاً بكود الدولة
        elif digits.startswith("0"):
            digits = code + digits[1:]
        else:
            digits = code + digits
    return f"https://wa.me/{digits}"

def build_weight_progress(user_id, user=None):
    """بيحضّر بيانات رسم تطور الوزن للعميل (نقاط SVG + أرقام + إحصائيات تحفيزية)."""
    out = {"has_data": False, "count": 0, "start": None, "current": None,
           "change": 0.0, "points": "", "dots": [],
           "pace": None, "bmi": None, "bmi_label": "", "bmi_color": "#475569",
           "days_tracking": 0, "message": "", "message_icon": "💪"}
    try:
        logs = db_rows("SELECT weight, logged_at FROM weight_log WHERE user_id=? ORDER BY logged_at ASC LIMIT 60", (user_id,))
    except Exception:
        logs = []
    pts = []
    dates = []
    for r in (logs or []):
        try:
            w = float(r.get("weight"))
        except Exception:
            continue
        v = r.get("logged_at")
        if hasattr(v, "strftime"):
            d = v.strftime("%m/%d")
            dt_obj = v
        else:
            d = str(v)[5:10] if v else ""
            try:
                dt_obj = datetime.fromisoformat(str(v)[:19])
            except Exception:
                dt_obj = None
        pts.append((d, w))
        dates.append(dt_obj)
    if not pts:
        return out
    out["has_data"] = True
    out["count"] = len(pts)
    out["start"] = round(pts[0][1], 1)
    out["current"] = round(pts[-1][1], 1)
    out["change"] = round(pts[-1][1] - pts[0][1], 1)

    # ── مدة المتابعة والمعدل الأسبوعي ──
    try:
        if dates[0] and dates[-1]:
            days = max((dates[-1] - dates[0]).days, 0)
            out["days_tracking"] = days
            if days >= 7 and out["change"] != 0:
                out["pace"] = round(out["change"] / (days / 7.0), 2)
    except Exception:
        pass

    # ── BMI الحالي وتصنيفه ──
    try:
        h = float((user or {}).get("height") or 0)
        if h > 0:
            bmi = pts[-1][1] / ((h / 100) ** 2)
            out["bmi"] = round(bmi, 1)
            if bmi < 18.5:
                out["bmi_label"], out["bmi_color"] = "نحافة", "#1d6fa5"
            elif bmi < 25:
                out["bmi_label"], out["bmi_color"] = "وزن صحي", "#1e4a3d"
            elif bmi < 30:
                out["bmi_label"], out["bmi_color"] = "زيادة وزن", "#b7791f"
            else:
                out["bmi_label"], out["bmi_color"] = "سمنة", "#dc2626"
    except Exception:
        pass

    # ── رسالة تحفيزية حسب هدف العميل واتجاه التغيّر ──
    goal = (user or {}).get("goal") or "weight_loss"
    ch = out["change"]
    if goal in ("muscle_gain", "bulking"):
        if ch > 0:
            out["message"], out["message_icon"] = f"زيادة {abs(ch)} كجم من البداية — عضلاتك بتتبني، كمّل تمرين وبروتين!", "🏋️"
        elif ch < 0:
            out["message"], out["message_icon"] = "الوزن نزل شوية — راجع سعراتك وزوّد البروتين، وكلّم الدكتور لو محتاج تعديل.", "📋"
        else:
            out["message"], out["message_icon"] = "الوزن ثابت — التضخيم محتاج فائض سعرات بسيط، التزم بالخطة.", "⚖️"
    elif goal == "maintain":
        if abs(ch) <= 1:
            out["message"], out["message_icon"] = "وزنك ثابت زي ما هو مطلوب — ده بالظبط هدف المحافظة، ممتاز!", "🎯"
        else:
            out["message"], out["message_icon"] = f"في تغيّر {abs(ch)} كجم — لو مش مقصود راجع التزامك بالخطة.", "📋"
    elif goal == "cutting":
        if ch < 0:
            out["message"], out["message_icon"] = f"نزلت {abs(ch)} كجم مع الحفاظ على عضلاتك — التنشيف ماشي مظبوط، ثبّت البروتين والتمرين!", "🔥"
        elif ch > 0:
            out["message"], out["message_icon"] = "الوزن زاد شوية — في التنشيف راجع سعراتك، وممكن يكون احتباس مياه مؤقت.", "📋"
        else:
            out["message"], out["message_icon"] = "الوزن ثابت — في التنشيف بنستهدف نزول 0.5-1% أسبوعياً، ظبط العجز مع الدكتور.", "⚖️"
    else:  # weight_loss
        if ch < 0:
            out["message"], out["message_icon"] = f"نزلت {abs(ch)} كجم من أول ما بدأت — شغل جامد، استمر!", "🔥"
        elif ch > 0:
            out["message"], out["message_icon"] = "الرحلة فيها طلوع ونزول وده طبيعي — ارجع للخطة من بكرة وهتشوف الفرق.", "🌱"
        else:
            out["message"], out["message_icon"] = "الوزن ثابت حالياً — الثبات مرحلة معروفة، التزم والنزول جاي.", "⏳"

    weights = [p[1] for p in pts]
    wmin, wmax = min(weights), max(weights)
    pad = max(1.0, (wmax - wmin) * 0.15)
    lo, hi = wmin - pad, wmax + pad
    if hi - lo < 1:
        hi = lo + 1
    W, H, PX, PY = 600.0, 200.0, 40.0, 24.0
    n = len(pts)
    def xc(i):
        return W / 2 if n == 1 else PX + (W - 2 * PX) * i / (n - 1)
    def yc(w):
        return PY + (H - 2 * PY) * (1 - (w - lo) / (hi - lo))
    coords = [(round(xc(i), 1), round(yc(w), 1)) for i, (d, w) in enumerate(pts)]
    out["points"] = " ".join(f"{x},{y}" for x, y in coords)
    out["dots"] = [{"x": coords[i][0], "y": coords[i][1], "w": round(pts[i][1], 1), "d": pts[i][0]} for i in range(n)]
    return out

ARABIC_DAYS = ["الاحد","الاثنين","الثلاثاء","الاربعاء","الخميس","الجمعة","السبت"]

# ═══════════════════════════════════════════════
# MEAL TRACKING (تتبع وجبات اليوم + نسبة الالتزام)
# ═══════════════════════════════════════════════

def get_meal_tracking(user_id):
    """بيرجّع وجبات النهارده من خطة العميل المعتمدة + حالة التعليم + نسبة التزام الأسبوع"""
    out = {"has_plan": False, "today_meals": [], "today_date": datetime.now().strftime("%Y-%m-%d"),
           "day_name": "", "week_pct": None, "today_done": 0, "today_total": 0}
    try:
        latest = db_row("SELECT plan_data FROM plan_requests WHERE client_id=? AND status='approved' ORDER BY updated_at DESC LIMIT 1", (user_id,))
        if not latest or not latest.get("plan_data"):
            return out
        pd = json.loads(latest["plan_data"])
        plan = pd.get("plan") or []
        if not plan:
            return out
        # اليوم الحالي: الخطة بتبدأ بالأحد — Python: Monday=0..Sunday=6
        idx = (datetime.now().weekday() + 1) % 7
        idx = min(idx, len(plan) - 1)
        day = plan[idx]
        labels = day.get("meal_labels") or {}
        emojis = day.get("meal_emojis") or {}
        # the plan stores Arabic labels/meals; swap them out for display in EN
        if cur_lang() != "ar":
            _info = get_diet_plan_info(day.get("diet_type")
                                       or (pd.get("data") or {}).get("diet_plan_type", "standard"))
            labels = _info.get("meal_labels_en") or labels
        meal_keys = [k for k in ["breakfast","snack1","meal1","pre_workout","lunch","post_workout","iftar","snack","snack2","suhoor","meal2","dinner"] if day.get(k)]
        checks = {}
        try:
            rows = db_rows("SELECT meal_key FROM meal_checks WHERE user_id=? AND check_date=?", (user_id, out["today_date"]))
            checks = {r["meal_key"]: 1 for r in (rows or [])}
        except Exception:
            pass
        for k in meal_keys:
            out["today_meals"].append({"key": k, "label": labels.get(k, k), "emoji": emojis.get(k, "🍽️"),
                                       "text": day.get(k, ""), "checked": bool(checks.get(k))})
        out["has_plan"] = True
        out["day_name"] = day.get("day", "")
        if cur_lang() != "ar":
            out["day_name"] = ENGLISH_DAYS.get(out["day_name"], out["day_name"])
        out["today_total"] = len(meal_keys)
        out["today_done"] = sum(1 for m in out["today_meals"] if m["checked"])
        # التزام آخر 7 أيام
        try:
            week_ago = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
            r = db_row("SELECT COUNT(*) as c FROM meal_checks WHERE user_id=? AND check_date>=?", (user_id, week_ago))
            done = (r or {}).get("c", 0)
            expected = max(len(meal_keys) * 7, 1)
            out["week_pct"] = min(round(done / expected * 100), 100)
        except Exception:
            pass
    except Exception as _e:
        print(f"meal tracking error: {_e}")
    return out


def get_meal_streak(user_id, max_days=90):
    """بيحسب تتابع الالتزام الحالي (أيام متتالية بالتزام كامل بكل وجبات اليوم) وأطول تتابع، من بيانات meal_checks الموجودة."""
    out = {"current_streak": 0, "best_streak": 0, "badge": None}
    try:
        latest = db_row("""SELECT plan_data FROM plan_requests
                           WHERE client_id=? AND status='approved'
                           ORDER BY updated_at DESC LIMIT 1""", (user_id,))
        if not latest or not latest.get("plan_data"):
            return out
        pd = json.loads(latest["plan_data"])
        plan = pd.get("plan") or []
        if not plan:
            return out
        diet_type = (pd.get("data") or {}).get("diet_plan_type", "standard")
        meal_list = get_diet_plan_info(diet_type).get("meals", [])

        # الوجبات المتوقعة لكل يوم أسبوع (0=الأحد..6=السبت) حسب الخطة
        expected_by_weekday = {}
        for i in range(7):
            day = plan[min(i, len(plan) - 1)]
            expected_by_weekday[i] = [k for k in meal_list if day.get(k)]

        rows = db_rows("SELECT check_date, meal_key FROM meal_checks WHERE user_id=?", (user_id,))
        done_by_date = {}
        for r in (rows or []):
            d = str(r["check_date"])[:10]
            done_by_date.setdefault(d, set()).add(r["meal_key"])

        def is_complete(d):
            widx = (d.weekday() + 1) % 7
            expected = expected_by_weekday.get(widx, [])
            if not expected:
                return None  # يوم مفيهوش وجبات متوقعة أصلاً — نتجاهله
            done = done_by_date.get(d.strftime("%Y-%m-%d"), set())
            return all(k in done for k in expected)

        today = datetime.now().date()
        current, run, best, counting_current = 0, 0, 0, True
        for back in range(1, max_days + 1):
            complete = is_complete(today - timedelta(days=back))
            if complete is None:
                continue
            if complete:
                run += 1
                best = max(best, run)
                if counting_current:
                    current = run
            else:
                run = 0
                counting_current = False

        if is_complete(today):
            current += 1
            best = max(best, current)

        out["current_streak"] = current
        out["best_streak"] = max(best, current)
    except Exception as e:
        print(f"[streak] error: {e}")
        return out

    if out["current_streak"] >= 30:
        out["badge"] = {"emoji": "🏆", "label": "شهر كامل!"}
    elif out["current_streak"] >= 14:
        out["badge"] = {"emoji": "🥇", "label": "أسبوعين متتاليين"}
    elif out["current_streak"] >= 7:
        out["badge"] = {"emoji": "🔥", "label": "أسبوع كامل"}
    elif out["current_streak"] >= 3:
        out["badge"] = {"emoji": "⭐", "label": "بداية قوية"}
    return out


def get_at_risk_clients(threshold=40, limit=10):
    """عملاء عندهم خطة معتمدة والتزامهم بالوجبات آخر 7 أيام أقل من حد معيّن — إشارة مبكرة إنهم محتاجين متابعة."""
    out = []
    try:
        clients = db_rows("SELECT id, name, email FROM users WHERE role='client' AND active=1")
    except Exception as e:
        print(f"[at risk] users query error: {e}")
        return out
    for c in (clients or []):
        try:
            tracking = get_meal_tracking(c["id"])
            pct = tracking.get("week_pct")
            if tracking.get("has_plan") and pct is not None and pct < threshold:
                out.append({"id": c["id"], "name": c.get("name") or "-",
                           "email": c.get("email") or "-", "week_pct": pct})
        except Exception:
            continue
    out.sort(key=lambda x: x["week_pct"])
    return out[:limit]


def send_meal_time_reminders():
    """يفحص وجبات النهاردة لكل عميل عنده خطة معتمدة، ويبعت تذكير لأي وجبة فات وقتها ومتسجلتش (مرة واحدة بس لكل وجبة/يوم)."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    try:
        clients = db_rows("SELECT id FROM users WHERE role='client' AND active=1")
    except Exception as e:
        print(f"[meal reminders] users query error: {e}")
        return

    for c in (clients or []):
        uid = c["id"]
        try:
            latest = db_row("""SELECT plan_data FROM plan_requests
                               WHERE client_id=? AND status='approved'
                               ORDER BY updated_at DESC LIMIT 1""", (uid,))
            if not latest or not latest.get("plan_data"):
                continue
            pd = json.loads(latest["plan_data"])
            plan = pd.get("plan") or []
            if not plan:
                continue
            diet_type = (pd.get("data") or {}).get("diet_plan_type", "standard")
            plan_info = get_diet_plan_info(diet_type)
            meal_hours = plan_info.get("meal_hours", {})
            labels = plan_info.get("meal_labels", {})
            emojis = plan_info.get("meal_emojis", {})

            idx = (now.weekday() + 1) % 7
            idx = min(idx, len(plan) - 1)
            day = plan[idx]

            checked = {r["meal_key"] for r in (db_rows(
                "SELECT meal_key FROM meal_checks WHERE user_id=? AND check_date=?", (uid, today)) or [])}
            reminded = {r["meal_key"] for r in (db_rows(
                "SELECT meal_key FROM meal_reminders_sent WHERE user_id=? AND check_date=?", (uid, today)) or [])}

            for meal_key in plan_info.get("meals", []):
                if not day.get(meal_key) or meal_key in checked or meal_key in reminded:
                    continue
                hour = meal_hours.get(meal_key)
                if hour is None or now.hour < hour:
                    continue
                push_to_user(uid, f"{emojis.get(meal_key, '🍽️')} فاتك تسجّل {labels.get(meal_key, meal_key)}؟",
                            "متنساش تاخد وجبتك حسب خطتك — سجّلها من التطبيق.",
                            url="/my-plan")
                db_run("INSERT INTO meal_reminders_sent (user_id, check_date, meal_key) VALUES (?,?,?)",
                       (uid, today, meal_key))
        except Exception as e:
            print(f"[meal reminders] user {uid} error: {e}")


# ── تذكير مواعيد الوجبات: فحص دوري في الخلفية كل 30 دقيقة ──
def _meal_reminders_loop():
    import time
    while True:
        try:
            send_meal_time_reminders()
        except Exception as e:
            print(f"[meal reminders] loop error: {e}")
        time.sleep(30 * 60)

threading.Thread(target=_meal_reminders_loop, daemon=True).start()


def _weekly_weight_delta(user_id):
    """فرق الوزن بين أول وآخر تسجيل في آخر 7 أيام (None لو أقل من تسجيلين)."""
    try:
        week_ago = datetime.now() - timedelta(days=7)
        logs = db_rows("""SELECT weight, logged_at FROM weight_log
                          WHERE user_id=? AND logged_at >= ? ORDER BY logged_at ASC""",
                       (user_id, week_ago))
        if not logs or len(logs) < 2:
            return None
        return round(float(logs[-1]["weight"]) - float(logs[0]["weight"]), 1)
    except Exception:
        return None


def send_weekly_summaries():
    """يبعت ملخص أسبوعي (وزن + التزام + تتابع) لكل عميل نشط عنده خطة، مرة واحدة بس في الأسبوع لكل عميل."""
    now = datetime.now()
    year, week_num, _ = now.isocalendar()
    week_key = f"{year}-W{week_num:02d}"
    try:
        clients = db_rows("SELECT id FROM users WHERE role='client' AND active=1")
    except Exception as e:
        print(f"[weekly summary] users query error: {e}")
        return

    for c in (clients or []):
        uid = c["id"]
        try:
            if db_row("SELECT id FROM weekly_summary_sent WHERE user_id=? AND week_key=?", (uid, week_key)):
                continue

            tracking = get_meal_tracking(uid)
            if not tracking.get("has_plan"):
                continue

            streak = get_meal_streak(uid)
            delta = _weekly_weight_delta(uid)

            parts = []
            if delta is not None:
                if delta < 0:
                    parts.append(f"نزل وزنك {abs(delta)} كجم")
                elif delta > 0:
                    parts.append(f"زاد وزنك {delta} كجم")
                else:
                    parts.append("وزنك ثابت")
            if tracking.get("week_pct") is not None:
                parts.append(f"التزامك بالوجبات {tracking['week_pct']}%")
            if streak.get("current_streak", 0) > 0:
                parts.append(f"تتابع {streak['current_streak']} يوم 🔥")

            if not parts:
                continue

            push_to_user(uid, "📊 ملخص أسبوعك", "، ".join(parts) + ". كمّل كده!", url="/my-plan")
            db_run("INSERT INTO weekly_summary_sent (user_id, week_key) VALUES (?,?)", (uid, week_key))
        except Exception as e:
            print(f"[weekly summary] user {uid} error: {e}")


# ── ملخص أسبوعي تلقائي: فحص دوري في الخلفية كل 3 ساعات (بيتبعت مرة واحدة بس لكل عميل كل أسبوع) ──
def _weekly_summary_loop():
    import time
    while True:
        try:
            send_weekly_summaries()
        except Exception as e:
            print(f"[weekly summary] loop error: {e}")
        time.sleep(3 * 3600)

threading.Thread(target=_weekly_summary_loop, daemon=True).start()


@app.route("/track/meal", methods=["POST"])
@login_required
def track_meal():
    """العميل بيعلّم ✅ أو يشيل العلامة من وجبة النهارده"""
    meal_key = (request.form.get("meal_key") or "").strip()[:30]
    checked = 1 if request.form.get("checked") == "1" else 0
    day_date = datetime.now().strftime("%Y-%m-%d")
    if not meal_key:
        return jsonify({"ok": False}), 400
    try:
        exists = db_row("SELECT id FROM meal_checks WHERE user_id=? AND check_date=? AND meal_key=?",
                        (session["uid"], day_date, meal_key))
        if checked and not exists:
            db_run("INSERT INTO meal_checks (user_id, check_date, meal_key) VALUES (?,?,?)",
                   (session["uid"], day_date, meal_key))
        elif not checked and exists:
            db_run("DELETE FROM meal_checks WHERE id=?", (exists["id"],))
        return jsonify({"ok": True, "checked": checked})
    except Exception as e:
        print(f"track meal error: {e}")
        return jsonify({"ok": False}), 500


@app.route("/my-plan")
@login_required
def my_plan():
    u = get_user_by_id(session["uid"])
    role = get_user_role(u)
    if role in ["admin", "nutritionist"]:
        return redirect("/dashboard")
    latest_plan = None
    pending_request = None
    try:
        latest_plan = db_row("SELECT * FROM plan_requests WHERE client_id=? AND status='approved' ORDER BY updated_at DESC LIMIT 1", (session["uid"],))
        pending_request = db_row("SELECT * FROM plan_requests WHERE client_id=? AND status='pending' ORDER BY created_at DESC LIMIT 1", (session["uid"],))
    except:
        pass
    can_request, days_left, hours_left, last_date = can_request_new_plan(session["uid"])

    tips = get_tips_for_user(u)
    today_tip = tips[datetime.now().day % len(tips)] if tips else None

    weight = build_weight_progress(session["uid"], u)
    tracking = get_meal_tracking(session["uid"])
    streak = get_meal_streak(session["uid"])
    return render_template("my_plan.html", user=u, lang=session.get("lang","ar"),
                           latest_plan=latest_plan, pending_request=pending_request,
                           can_request=can_request, days_left=days_left,
                           hours_left=hours_left, last_request_date=last_date,
                           today_tip=today_tip, weight=weight, tracking=tracking,
                           streak=streak)

def _plan_input_error(age, height, weight, lang="ar"):
    """None when age/height/weight are usable, otherwise a message to show.

    Ranges match the form's min/max so client and server agree.
    """
    checks = (
        (age, 10, 100, "العمر", "Age"),
        (height, 100, 230, "الطول", "Height"),
        (weight, 30, 300, "الوزن", "Weight"),
    )
    missing_ar, missing_en = [], []
    for raw, lo, hi, ar, en in checks:
        try:
            val = float(str(raw).strip())
        except (TypeError, ValueError):
            missing_ar.append(ar)
            missing_en.append(en)
            continue
        if not (lo <= val <= hi):
            missing_ar.append(f"{ar} ({lo}-{hi})")
            missing_en.append(f"{en} ({lo}-{hi})")
    if not missing_ar:
        return None
    if lang == "ar":
        return "محتاجين البيانات دي صح عشان نبني الخطة: " + "، ".join(missing_ar)
    return "We need these to build the plan: " + ", ".join(missing_en)


@app.route("/request-plan", methods=["GET","POST"])
@login_required
def request_plan():
    u = get_user_by_id(session["uid"])
    role = get_user_role(u)
    if role in ["admin", "nutritionist"]:
        return redirect("/dashboard")
    can_request, days_left, hours_left, last_date = can_request_new_plan(session["uid"])
    if not can_request:
        return render_template("request_plan_blocked.html", user=u, lang=session.get("lang","ar"),
                               days_left=days_left, hours_left=hours_left, last_request_date=last_date)
    if request.method == "POST":
        can_request_now, _, _, _ = can_request_new_plan(session["uid"])
        if not can_request_now:
            return redirect("/my-plan")
        symptoms = request.form.getlist("symptoms")
        allergies = request.form.getlist("allergies")

        # `request.form.get(k, default)` returns "" when the field is present but
        # blank, so the profile fallback never fired and empty requests were
        # stored with no age/height/weight. Use `or` so blanks fall through.
        _lang = session.get("lang", "ar")
        _height = request.form.get("height") or u.get("height") or ""
        _weight = request.form.get("weight") or u.get("weight") or ""
        _age = request.form.get("age") or u.get("age") or ""

        # the plan cannot be built without these, and the client-side `required`
        # is trivially bypassed, so check here too
        _bad = _plan_input_error(_age, _height, _weight, _lang)
        if _bad:
            return render_template("request_plan.html", user=u, lang=_lang,
                                   diet_plans=DIET_PLAN_TYPES, error=_bad)

        request_data = {
            "height": _height,
            "weight": _weight,
            "age": _age,
            "gender": request.form.get("gender") or u.get("gender") or "ذكر",
            "fat_pct": request.form.get("fat_pct", ""),
            "bmi": request.form.get("bmi", ""),
            "tdee": request.form.get("tdee", ""),
            "goal_cal": request.form.get("goal_cal", ""),
            "goal_type": request.form.get("goal_type", "weight_loss"),
            "culture": request.form.get("culture", "مصري"),
            "diet_plan_type": request.form.get("diet_plan_type", "standard"),
            "symptoms": symptoms,
            "allergies": allergies,
            "liked_foods": request.form.get("liked_foods", ""),
            "disliked_foods": request.form.get("disliked_foods", ""),
            "notes": request.form.get("notes", ""),
        }
        try:
            db_run("""INSERT INTO plan_requests (client_id, client_name, request_data, status) VALUES (?, ?, ?, 'pending')""",
                   (session["uid"], u.get("name","Client"), json.dumps(request_data)))
            if symptoms:
                db_run("UPDATE users SET conditions=? WHERE id=?", (json.dumps(symptoms), session["uid"]))
        except Exception as e:
            print(f"request_plan insert error: {e}")
            return render_template(
                "request_plan.html", user=u, lang=_lang,
                diet_plans=DIET_PLAN_TYPES,
                error=("حصلت مشكلة وإحنا بنسجل الطلب — حاول تاني." if _lang == "ar"
                       else "Something went wrong saving your request -- please try again.")), 500

        # ── إشعار للأدمن: طلب خطة جديد ──
        try:
            add_notification(
                db_run, "plan_request",
                f"طلب خطة جديد من: {u.get('name','عميل')}",
                f"العميل {u.get('name','')} طلب خطة غذائية جديدة. افتح صفحة الطلبات لمراجعتها.",
                link="/admin/requests",
                related_user_id=session["uid"]
            )
        except Exception as _e:
            print(f"notif plan_request error: {_e}")

        return redirect("/my-plan")
    return render_template("request_plan.html", user=u, lang=session.get("lang","ar"), diet_plans=DIET_PLAN_TYPES)

@app.route("/admin/users")
@admin_required
def admin_users():
    u = get_user_by_id(session["uid"])
    try: all_users = db_rows("SELECT * FROM users ORDER BY id DESC")
    except: all_users = []
    return render_template("admin_users.html", user=u, lang=session.get("lang","ar"), users=all_users)

@app.route("/admin/users/export")
@admin_required
def admin_users_export():
    """تصدير كل العملاء لملف CSV يفتح في Excel بالعربي سليم"""
    import csv
    try:
        rows = db_rows("SELECT * FROM users ORDER BY id")
    except Exception:
        rows = []
    goal_labels = {"weight_loss": "تخسيس", "muscle_gain": "زيادة عضل",
                   "bulking": "تضخيم", "cutting": "تنشيف", "maintain": "محافظة", "maintenance": "محافظة"}
    role_labels = {"client": "عميل", "nutritionist": "أخصائي", "admin": "أدمن"}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["#", "الاسم", "الإيميل", "التليفون", "البلد", "العمر", "الجنس",
                "الطول", "الوزن", "الهدف", "الدور", "الحالة", "تاريخ التسجيل"])
    for u in rows:
        created = u.get("created_at")
        created_str = created.strftime("%Y-%m-%d") if hasattr(created, "strftime") else (str(created)[:10] if created else "")
        w.writerow([
            u.get("id"), u.get("name") or "", u.get("email") or "", u.get("phone") or "",
            u.get("country") or "", u.get("age") or "", u.get("gender") or "",
            u.get("height") or "", u.get("weight") or "",
            goal_labels.get(u.get("goal"), u.get("goal") or ""),
            role_labels.get(u.get("role"), u.get("role") or ""),
            "نشط" if u.get("active", 1) else "موقوف",
            created_str,
        ])
    # BOM عشان Excel يقرأ العربي صح
    data = "\ufeff" + buf.getvalue()
    out = io.BytesIO(data.encode("utf-8"))
    out.seek(0)
    fname = f"NutraX_clients_{datetime.now().strftime('%Y-%m-%d')}.csv"
    return send_file(out, as_attachment=True, download_name=fname, mimetype="text/csv; charset=utf-8")


@app.route("/admin/users/new", methods=["GET","POST"])
@admin_required
def admin_new_user():
    u = get_user_by_id(session["uid"])
    if request.method == "POST":
        name = request.form.get("name","")
        email = request.form.get("email","").lower()
        pw = request.form.get("password","")
        role = request.form.get("role","client")
        phone = request.form.get("phone","")
        if not email or not pw:
            return render_template("admin_new_user.html", user=u, lang=session.get("lang","ar"), error="الإيميل وكلمة السر مطلوبة")
        try:
            db_run("INSERT INTO users (name,email,password,role,phone,active) VALUES (?,?,?,?,?,1)",
                   (name, email, hp(pw), role, phone))
            return redirect("/admin/users")
        except:
            return render_template("admin_new_user.html", user=u, lang=session.get("lang","ar"), error="الإيميل موجود بالفعل")
    return render_template("admin_new_user.html", user=u, lang=session.get("lang","ar"))

@app.route("/admin/users/<int:uid>/toggle")
@admin_required
def admin_toggle_user(uid):
    target = db_row("SELECT * FROM users WHERE id=?", (uid,))
    if target and not target.get("is_admin"):
        new_active = 0 if target.get("active", 1) else 1
        db_run("UPDATE users SET active=? WHERE id=?", (new_active, uid))
    return redirect("/admin/users")

@app.route("/admin/users/<int:uid>/role/<role>")
@admin_required
def admin_change_role(uid, role):
    if role in ["client", "nutritionist", "admin"]:
        target = db_row("SELECT * FROM users WHERE id=?", (uid,))
        if target and not target.get("is_admin"):
            db_run("UPDATE users SET role=? WHERE id=?", (role, uid))
    return redirect("/admin/users")

@app.route("/admin/users/<int:uid>/delete", methods=["POST"])
@admin_required
def admin_delete_user(uid):
    target = db_row("SELECT * FROM users WHERE id=?", (uid,))
    if target and not target.get("is_admin"):
        db_run("DELETE FROM users WHERE id=?", (uid,))
    return redirect("/admin/users")

@app.route("/admin/requests")
@staff_required
def admin_requests():
    u = get_user_by_id(session["uid"])
    try: requests_list = db_rows("SELECT * FROM plan_requests ORDER BY created_at DESC LIMIT 50")
    except: requests_list = []
    return render_template("admin_requests.html", user=u, lang=session.get("lang","ar"), requests=requests_list)

@app.route("/admin/requests/<int:rid>/generate")
@staff_required
def admin_request_generate(rid):
    req = db_row("SELECT * FROM plan_requests WHERE id=?", (rid,))
    if not req: return redirect("/admin/requests")
    try: rdata = json.loads(req["request_data"])
    except: return redirect("/admin/requests")
    client = get_user_by_id(req["client_id"])
    data = {
        "name": client.get("name","") if client else req.get("client_name",""),
        **rdata,
    }
    session["pdf_data"] = data
    session["current_plan"] = generate_weekly_plan(data)
    session["current_request_id"] = rid
    return redirect("/preview")


@app.route("/admin/requests/<int:rid>/manual")
@staff_required
def admin_request_manual(rid):
    """Generate empty plan for manual filling"""
    req = db_row("SELECT * FROM plan_requests WHERE id=?", (rid,))
    if not req: return redirect("/admin/requests")
    try: rdata = json.loads(req["request_data"])
    except: return redirect("/admin/requests")
    client = get_user_by_id(req["client_id"])
    data = {
        "name": client.get("name","") if client else req.get("client_name",""),
        **rdata,
    }
    diet_type = data.get("diet_plan_type", "standard")
    plan_info = get_diet_plan_info(diet_type)
    days = ["الاحد","الاثنين","الثلاثاء","الاربعاء","الخميس","الجمعة","السبت"]

    goal = (data.get("goal") or "").lower()
    conditions_raw = data.get("symptoms") or data.get("conditions") or ""
    conditions = conditions_raw.lower() if isinstance(conditions_raw, str) else ""
    is_diabetes = any(k in conditions for k in ["سكري", "سكر", "diabet"])
    is_kidney = any(k in conditions for k in ["كلى", "كلي", "kidney"])

    def get_starter(meal_key, day_idx):
        breakfasts_general = [
            "🥣 شوفان بالحليب 40جم + 🍌 موز + 🌰 لوز 10جم",
            "🥚 بيضتين مسلوق + 🧀 جبن قريش 50جم + 🍞 خبز اسمر",
            "🥘 فول مدمس 150جم + 🥚 بيضة + 🍞 خبز اسمر",
            "🥞 توست بالأفوكادو + 🥚 بيضة + 🍅 طماطم",
            "🥛 زبادي يوناني 200جم + 🍓 فراولة + 🥜 جوز",
            "🥚 اومليت بالسبانخ + 🍞 خبز اسمر + 🧀 جبن قريش",
            "🥣 موسلي بالحليب + 🍎 تفاح + 🌰 لوز",
        ]
        breakfasts_diabetes = [
            "🥣 شوفان مطبوخ 40جم + 🥜 لوز 10جم + 🥚 بيضة مسلوقة",
            "🥚 بيضتين + 🥒 خيار + 🍞 خبز اسمر شريحة + 🥑 أفوكادو",
            "🥘 فول 100جم + 🥚 بيضة + 🥬 سلطة خضراء",
            "🥛 زبادي يوناني سادة + 🌰 جوز 10جم + 🍓 فراولة قليلة",
            "🥚 اومليت 2 بيضة + 🥬 سبانخ + 🍞 خبز اسمر شريحة",
            "🥚 بيض مسلوق + 🧀 جبن قريش + 🥒 خيار",
            "🥣 شوفان + 🥜 لوز + 🥛 حليب قليل دسم",
        ]
        breakfasts_kidney = [
            "🥚 بياض بيض 3 + 🍞 خبز ابيض + 🥒 خيار",
            "🥣 شوفان بماء + 🍎 تفاح + 🌰 لوز قليل",
            "🥚 بيضتين + 🍞 خبز ابيض + 🥒 خيار",
            "🥚 اومليت ببياض البيض + 🥬 خس",
            "🥖 توست + 🧈 زبدة قليلة + 🍯 عسل",
            "🥚 بياض بيض + 🍞 خبز ابيض + 🍎 تفاح",
            "🥣 شوفان + 🍓 فراولة قليلة",
        ]
        lunches_general = [
            "🍗 صدر دجاج مشوي 150جم + 🍚 أرز 100جم + 🥗 سلطة",
            "🐟 سمك مشوي 150جم + 🍠 بطاطا حلوة 100جم + 🥦 بروكلي",
            "🥩 لحم مشوي 120جم + 🍚 أرز بني 80جم + 🥗 سلطة",
            "🍗 دجاج بالخضار + 🍚 أرز 80جم + 🥒 خيار",
            "🐟 سلمون 150جم + 🍠 بطاطا حلوة + 🥬 سبانخ",
            "🍗 شيش طاووق 150جم + 🍚 أرز 100جم + 🥗 طبق سلطة",
            "🥚 طاجن فول + 🍞 خبز اسمر + 🥗 سلطة بلدي",
        ]
        lunches_diabetes = [
            "🍗 صدر دجاج 150جم + 🍚 أرز بني 70جم + 🥗 سلطة كبيرة",
            "🐟 سمك مشوي 150جم + 🥦 بروكلي + 🍠 بطاطا حلوة 80جم",
            "🥩 لحم 100جم + 🍚 أرز بني 60جم + 🥬 سبانخ",
            "🍗 دجاج مشوي + 🥗 سلطة كبيرة + 🍞 خبز اسمر شريحة",
            "🐟 تونة + 🥗 سلطة بأفوكادو + 🥖 خبز اسمر",
            "🥚 طاجن خضار بالبيض + 🍞 خبز اسمر شريحة",
            "🍗 صدر دجاج + 🥦 بروكلي + 🥕 جزر",
        ]
        lunches_kidney = [
            "🍗 صدر دجاج 100جم + 🍚 أرز ابيض + 🥒 خيار",
            "🐟 سمك ابيض 120جم + 🍚 أرز + 🥗 خس",
            "🍗 دجاج 100جم + 🍚 أرز + 🥒 خيار",
            "🥚 بيضتين + 🍚 أرز + 🥬 خس",
            "🍗 صدر دجاج + 🍚 أرز + 🍆 كوسى",
            "🐟 سمك مسلوق + 🍚 أرز + 🍎 تفاح",
            "🍗 دجاج + 🍚 أرز + 🥒 خيار + 🥬 خس",
        ]
        dinners_general = [
            "🥗 سلطة دجاج + 🍞 خبز اسمر + 🧀 جبن قريش",
            "🥚 بيضتين + 🧀 جبن + 🥒 خضار + 🍞 خبز اسمر",
            "🐟 تونة + 🥗 سلطة كبيرة + 🍞 توست",
            "🥛 زبادي يوناني + 🍓 فاكهة + 🥜 مكسرات",
            "🍗 صدر دجاج صغير + 🥗 سلطة + 🥖 خبز",
            "🥚 اومليت بالخضار + 🍞 خبز",
            "🥗 سلطة قيصر بالدجاج",
        ]
        snacks_general = [
            "🍎 تفاحة + 🌰 لوز 10 حبات",
            "🥛 زبادي + 🍓 فراولة",
            "🥜 مكسرات 30جم",
            "🍌 موزة + 🥜 زبدة فول سوداني ملعقة",
            "🥕 جزر + حمص",
            "🍐 كمثرى + 🧀 جبن قريش",
            "🥚 بيضة مسلوقة + 🥒 خيار",
        ]

        if "breakfast" in meal_key or "فطار" in meal_key.lower() or "فطور" in meal_key.lower():
            pool = breakfasts_kidney if is_kidney else (breakfasts_diabetes if is_diabetes else breakfasts_general)
        elif "lunch" in meal_key or "غدا" in meal_key.lower():
            pool = lunches_kidney if is_kidney else (lunches_diabetes if is_diabetes else lunches_general)
        elif "dinner" in meal_key or "عشا" in meal_key.lower():
            pool = dinners_general
        elif "snack" in meal_key or "سناك" in meal_key.lower() or "وجبة خفيفة" in meal_key.lower():
            pool = snacks_general
        else:
            pool = breakfasts_general

        return pool[day_idx % len(pool)]

    empty_plan = []
    for i in range(7):
        day_plan = {"day": days[i], "diet_type": diet_type,
                    "meal_labels": plan_info["meal_labels"],
                    "meal_emojis": plan_info["meal_emojis"], "total_cal": 0}
        for meal_key in plan_info["meals"]:
            day_plan[meal_key] = get_starter(meal_key, i)
        empty_plan.append(day_plan)
    session["pdf_data"] = data
    session["current_plan"] = empty_plan
    session["current_request_id"] = rid
    session["manual_mode"] = True
    return redirect("/preview")


@app.route("/admin/requests/<int:rid>/approve", methods=["POST"])
@staff_required
def admin_request_approve(rid):
    plan = session.get("current_plan")
    data = session.get("pdf_data")
    if not plan or not data: return redirect("/admin/requests")
    db_run("UPDATE plan_requests SET status='approved', plan_data=?, updated_at=? WHERE id=?",
           (json.dumps({"plan": plan, "data": data}), datetime.now().isoformat(), rid))
    # ── إشعار موبايل للعميل إن خطته جاهزة ──
    client = None
    try:
        req = db_row("SELECT client_id FROM plan_requests WHERE id=?", (rid,))
        if req and req.get("client_id"):
            client = get_user_by_id(req["client_id"])
            push_to_user(req["client_id"], "خطتك الغذائية جاهزة! 🎉",
                         "د. محمد جهّزلك خطة جديدة. افتح التطبيق لمشاهدتها.",
                         url="/my-plan")
    except Exception as _e:
        print(f"push to client (plan) error: {_e}")

    # ── إرسال الخطة PDF بالإيميل للعميل ──
    try:
        if client and client.get("email"):
            pdf_bytes = build_pdf(data, plan)
            threading.Thread(
                target=send_plan_pdf_email,
                args=(client["email"], client.get("name"), pdf_bytes),
                daemon=True
            ).start()
    except Exception as _e:
        print(f"email plan pdf error: {_e}")

    session.pop("current_request_id", None)
    return redirect("/admin/requests")

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """تغيير كلمة السر — لكل المستخدمين بما فيهم الأدمن"""
    u = get_user_by_id(session["uid"])
    error = ""
    success = False
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if not verify_password(u.get("password"), current):
            error = "كلمة السر الحالية غير صحيحة"
        elif len(new_pw) < 6:
            error = "كلمة السر الجديدة لازم تكون 6 أحرف على الأقل"
        elif new_pw != confirm:
            error = "تأكيد كلمة السر غير مطابق"
        elif new_pw == current:
            error = "كلمة السر الجديدة لازم تختلف عن الحالية"
        else:
            try:
                db_run("UPDATE users SET password=? WHERE id=?", (hp(new_pw), session["uid"]))
                success = True
            except Exception as e:
                print(f"change password error: {e}")
                error = "حصلت مشكلة أثناء الحفظ — حاول تاني"
    return render_template("change_password.html", user=u,
                           lang=session.get("lang", "ar"),
                           error=error, success=success)


@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    u = get_user_by_id(session["uid"])
    saved = False
    if request.method == "POST":
        db_run("UPDATE users SET height=?, weight=?, age=?, gender=?, goal=?, activity=? WHERE id=?",
            (request.form.get("height"), request.form.get("weight"), request.form.get("age"),
             request.form.get("gender"), request.form.get("goal"), request.form.get("activity"), session["uid"]))
        u = get_user_by_id(session["uid"])
        saved = True
    return render_template("settings.html", user=u, lang=session.get("lang","ar"), saved=saved)

@app.route("/privacy")
def privacy():
    return render_template("privacy.html", lang=session.get("lang", "ar"))


@app.route("/terms")
def terms():
    # pass PRICING so the plan list in the terms cannot drift from what we charge
    return render_template("terms.html", lang=session.get("lang", "ar"), pricing=PRICING)


@app.route("/analyzer")
@subscription_required
def analyzer():
    return render_template("analyzer.html", user=get_user_by_id(session["uid"]),
                           lang=session.get("lang", "ar"),
                           foods_json=json.dumps(food_data.FOODS, ensure_ascii=False))

def _lookup_barcode(code):
    """يجيب بيانات منتج معلّب بالباركود من Open Food Facts. بيرجّع (payload_dict, status_code)."""
    import urllib.request as _ur

    clean_code = re.sub(r"\D", "", code or "")[:20]
    if not clean_code:
        return {"ok": False, "error": "باركود غير صالح"}, 400

    try:
        req = _ur.Request(
            f"https://world.openfoodfacts.org/api/v2/product/{clean_code}.json",
            headers={"User-Agent": "NutraX-FoodAnalyzer/1.0 (contact: admin@nutrax.com)"}
        )
        with _ur.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"[barcode] fetch error: {e}")
        return {"ok": False, "error": "تعذر الاتصال بقاعدة بيانات الباركود"}, 502

    if data.get("status") != 1 or not data.get("product"):
        return {"ok": False, "error": "المنتج ده مش موجود في القاعدة"}, 404

    p = data["product"]
    nutr = p.get("nutriments") or {}
    cal, protein, carbs, fat = (nutr.get("energy-kcal_100g"), nutr.get("proteins_100g"),
                                 nutr.get("carbohydrates_100g"), nutr.get("fat_100g"))
    if cal is None or protein is None or carbs is None or fat is None:
        return {"ok": False, "error": "البيانات الغذائية لهذا المنتج ناقصة"}, 404

    name_ar = p.get("product_name_ar") or ""
    name_en = p.get("product_name") or p.get("generic_name") or ""
    food = {
        "n": name_ar or name_en or "منتج بدون اسم",
        "en": name_en if name_ar and name_en != name_ar else "",
        "cat": "packaged", "cal": round(float(cal)), "p": round(float(protein), 1),
        "c": round(float(carbs), 1), "f": round(float(fat), 1),
        "safe": [], "units": [],
        "note": "من قاعدة بيانات Open Food Facts (منتج معلّب) — تأكد من مطابقة الباركود للمنتج.",
        "tip": "", "barcode": clean_code,
    }
    return {"ok": True, "food": food}, 200


@app.route("/api/food/barcode/<code>")
@subscription_required
def food_barcode_lookup(code):
    payload, status = _lookup_barcode(code)
    return jsonify(payload), status


# ═══════════════════════════════════════════════════════════════════
# DEVELOPER API PLATFORM — صفحات + endpoints للمطورين الخارجيين
# ═══════════════════════════════════════════════════════════════════

@app.route("/developers")
def developers_docs():
    """صفحة عامة: شرح الـ API + الأسعار — متاحة للجميع من غير تسجيل دخول."""
    u = get_user_by_id(session["uid"]) if "uid" in session else None
    user_currency = detect_currency(u.get("country")) if u else "USD"
    return render_template("api_docs.html", user=u, lang=session.get("lang", "ar"),
                           tiers=API_TIERS, user_currency=user_currency)


@app.route("/dashboard/api")
@login_required
def api_dashboard():
    u = get_user_by_id(session["uid"])
    usage = get_usage_info(session["uid"], db_row, db_run)
    user_currency = detect_currency(u.get("country")) if u else "USD"
    return render_template("api_dashboard.html", user=u, lang=session.get("lang", "ar"),
                           usage=usage, tiers=API_TIERS, user_currency=user_currency,
                           api_base=request.url_root.rstrip("/"))


@app.route("/dashboard/api/regenerate", methods=["POST"])
@login_required
def api_regenerate_key():
    regenerate_api_key(session["uid"], db_row, db_run)
    return redirect("/dashboard/api")


@app.route("/dashboard/api/checkout/<tier_key>")
@login_required
def api_checkout(tier_key):
    u = get_user_by_id(session["uid"])
    if tier_key not in API_TIERS or not API_TIERS[tier_key]["prices"]:
        return redirect("/dashboard/api")
    currency = request.args.get("currency", "").upper()
    if currency not in get_supported_currencies():
        currency = detect_currency(u.get("country"))
    try:
        checkout_session = create_api_checkout_session(u, tier_key, currency)
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        import traceback; traceback.print_exc()
        return render_template("payment_cancel.html", user=u, lang=session.get("lang", "ar"),
                               error=f"خطأ في إنشاء جلسة الدفع: {str(e)}"), 500


@app.route("/api/v1/health")
def api_v1_health():
    return jsonify({"ok": True, "service": "nutrax-api", "time": datetime.now().isoformat()})


@app.route("/api/v1/meal-plan", methods=["POST"])
@csrf.exempt
@require_api_key
def api_v1_meal_plan():
    """بيولّد خطة وجبات أسبوعية كاملة — نفس محرك توليد الخطط بتاع الموقع، متاح كـ API لمطورين تانيين."""
    body = request.get_json(silent=True) or {}
    data = {
        "goal_type": body.get("goal_type", "weight_loss"),
        "culture": body.get("culture", "مصري"),
        "diet_plan_type": body.get("diet_plan_type", "standard"),
        "activity_level": body.get("activity_level", "regular"),
        "symptoms": body.get("conditions") or body.get("symptoms") or [],
        "allergies": body.get("allergies") or [],
        "disliked_foods": body.get("disliked_foods", ""),
        "notes": body.get("notes", ""),
        "user_id": 0,
    }
    if data["culture"] not in ["مصري", "خليجي", "شامي", "مغربي", "عالمي"]:
        return jsonify({"ok": False, "error": "invalid_culture",
                         "message": "culture لازم يكون واحد من: مصري, خليجي, شامي, مغربي, عالمي"}), 400
    try:
        plan = generate_weekly_plan(data)
    except Exception as e:
        print(f"[api/v1/meal-plan] error: {e}")
        return jsonify({"ok": False, "error": "generation_failed"}), 500
    return jsonify({"ok": True, "plan": plan, "meta": {
        "goal_type": data["goal_type"], "culture": data["culture"],
        "diet_plan_type": data["diet_plan_type"], "days": len(plan),
    }})


@app.route("/api/v1/food/barcode/<code>")
@require_api_key
def api_v1_barcode(code):
    payload, status = _lookup_barcode(code)
    return jsonify(payload), status


@app.route("/planner")
@staff_required
def planner():
    return redirect("/generate")

@app.route("/clinical")
@staff_required
def clinical():
    return render_template("clinical.html", user=get_user_by_id(session["uid"]), lang=session.get("lang","ar"))

@app.route("/history")
@login_required
def history():
    u = get_user_by_id(session["uid"])
    logs = db_rows("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at DESC LIMIT 30", (session["uid"],))
    can_log, days_left, hours_left = can_log_weight(session["uid"])
    return render_template("history.html", user=u, lang=session.get("lang","ar"),
                           logs=logs, can_log_weight=can_log, days_left=days_left, hours_left=hours_left)

@app.route("/log_weight", methods=["POST"])
@login_required
def log_weight():
    can_log, _, _ = can_log_weight(session["uid"])
    if not can_log: return redirect("/history")
    w = request.form.get("weight")
    if w:
        try:
            w_float = float(w)
            if 20 < w_float < 300:
                db_run("INSERT INTO weight_log (user_id,weight) VALUES (?,?)", (session["uid"], w_float))
        except: pass
    return redirect("/history")

@app.route("/knowledge")
@login_required
def knowledge():
    u = get_user_by_id(session["uid"])
    return render_template("knowledge_hub.html", user=u, lang=session.get("lang","ar"))

@app.route("/daily-tips")
@login_required
def daily_tips():
    u = get_user_by_id(session["uid"])
    tips = get_tips_for_user(u)
    return render_template("daily_tips.html", user=u, lang=session.get("lang","ar"),
                           tips=tips, today_index=datetime.now().day % len(tips) if tips else 0)


# ═══════════════════════════════════════════════════
# CHAT/MESSAGING SYSTEM
# ═══════════════════════════════════════════════════

@app.route("/messages")
@login_required
def messages():
    """View all conversations - safe if table missing"""
    # Check subscription for clients
    user = get_user_by_id(session["uid"])
    role = get_user_role(user)
    if role == "client" and not has_active_access(session["uid"], db_row):
        return redirect("/subscription-required?reason=chat")

    try:
        if DATABASE_URL:
            db_run("""CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender_id INTEGER, receiver_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        else:
            db_run("""CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    except: pass

    user = get_user_by_id(session["uid"])
    role = get_user_role(user)

    if role in ['admin', 'nutritionist']:
        clients = db_rows("SELECT * FROM users WHERE role='client' OR role IS NULL ORDER BY name")
        conversations = []
        for c in clients:
            try:
                last_msg = db_row("""SELECT message, created_at FROM messages 
                                    WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                                    ORDER BY created_at DESC LIMIT 1""",
                                  (user["id"], c["id"], c["id"], user["id"]))
                unread = db_row("""SELECT COUNT(*) as c FROM messages 
                                  WHERE sender_id=? AND receiver_id=? AND is_read=0""",
                                (c["id"], user["id"]))
                conversations.append({
                    "user": c,
                    "last_message": last_msg["message"][:60] if last_msg else None,
                    "last_at": last_msg["created_at"] if last_msg else None,
                    "unread": unread["c"] if unread else 0
                })
            except:
                conversations.append({"user": c, "last_message": None, "last_at": None, "unread": 0})
        return render_template("messages_list.html", conversations=conversations, user=user, lang=session.get("lang","ar"))
    else:
        admin = db_row("SELECT * FROM users WHERE role='admin' OR is_admin=1 ORDER BY id LIMIT 1")
        if not admin: return redirect("/dashboard")
        return redirect(f"/messages/{admin['id']}")


@app.route("/messages/<int:other_id>", methods=["GET","POST"])
@login_required
def chat(other_id):
    user = get_user_by_id(session["uid"])
    # Subscription gate for clients
    role = get_user_role(user)
    if role == "client" and not has_active_access(session["uid"], db_row):
        return redirect("/subscription-required?reason=chat")

    other = get_user_by_id(other_id)
    if not other: return redirect("/messages")

    # عميل يقدر يكلم الستاف (الأدمن/الأخصائي) بس، مش أي مستخدم تاني
    if role == "client":
        other_role = get_user_role(other)
        if other_role not in ("admin", "nutritionist"):
            return redirect("/messages")

    if request.method == "POST":
        msg = request.form.get("message", "").strip()
        if msg:
            db_run("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?,?,?)",
                   (user["id"], other_id, msg))
            # ── إشعار للأدمن لو الراسل عميل ──
            try:
                if role == "client":
                    preview_txt = (msg[:120] + "…") if len(msg) > 120 else msg
                    add_notification(
                        db_run, "new_message",
                        f"رسالة جديدة من: {user.get('name','عميل')}",
                        preview_txt,
                        link=f"/messages/{user['id']}",
                        related_user_id=user["id"]
                    )
            except Exception as _e:
                print(f"notif new_message error: {_e}")
            # ── إشعار موبايل للعميل لو الراسل ستاف (أدمن/أخصائي) ──
            try:
                if role in ("admin", "nutritionist"):
                    preview_txt = (msg[:120] + "…") if len(msg) > 120 else msg
                    push_to_user(other_id, "رسالة جديدة من د. محمد",
                                 preview_txt, url="/messages")
            except Exception as _e:
                print(f"push to client (msg) error: {_e}")
        return redirect(f"/messages/{other_id}")

    db_run("UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=?", (other_id, user["id"]))

    msgs = db_rows("""SELECT * FROM messages 
                    WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                    ORDER BY created_at ASC""",
                  (user["id"], other_id, other_id, user["id"]))

    return render_template("chat.html", messages=msgs, user=user, other=other, lang=session.get("lang","ar"))


# ═══════════════════════════════════════════════════
# NOTIFICATIONS (إشعارات الأدمن)
# ═══════════════════════════════════════════════════

@app.route("/admin/notifications")
@staff_required
def admin_notifications():
    """صفحة كل الإشعارات (وبتعلّمها مقروءة بعد العرض)"""
    user = get_user_by_id(session["uid"])
    items = get_all_notifications(db_rows, limit=100)
    notifs = []
    for n in items:
        nd = dict(n)
        v = nd.get("created_at")
        if v:
            nd["created_str"] = v.strftime("%Y-%m-%d %H:%M") if hasattr(v, "strftime") else str(v)[:16]
        else:
            nd["created_str"] = ""
        meta = get_type_meta(nd.get("type"))
        nd["icon"] = meta["icon"]
        nd["type_label"] = meta["label"]
        notifs.append(nd)
    unread_before = sum(1 for n in notifs if not n.get("is_read"))
    # نعلّمها كلها مقروءة بعد ما اتعرضت
    try:
        mark_all_read(db_run)
    except: pass
    return render_template("admin_notifications.html", user=user,
                           lang=session.get("lang", "ar"),
                           notifications=notifs, unread_before=unread_before)


@app.route("/admin/notifications/read", methods=["POST"])
@staff_required
def admin_notifications_read():
    """تعليم كل الإشعارات كمقروءة"""
    mark_all_read(db_run)
    return redirect("/admin/notifications")


@app.route("/admin/notifications/count")
@staff_required
def admin_notifications_count():
    """API للجرس: بيرجّع عدد الإشعارات غير المقروءة (للـ polling والصوت)"""
    return jsonify({"count": get_unread_count(db_row)})


@app.route("/track/whatsapp-click", methods=["POST"])
def track_whatsapp_click():
    """بيتنادى من زرار واتساب (JS) عشان نسجّل إشعار إن العميل ضغط للدفع"""
    try:
        data = request.get_json(silent=True) or {}
        plan = (data.get("plan") or "خطة").strip()
        price = (data.get("price") or "").strip()
        source = (data.get("source") or "").strip()
        uid = session.get("uid")
        who = "زائر"
        if uid:
            u = get_user_by_id(uid)
            if u:
                who = u.get("name") or u.get("email") or "عميل"
        title = f"ضغط دفع واتساب: {who}"
        msg = f"العميل ضغط زرار واتساب للاشتراك في «{plan}»"
        if price:
            msg += f" بسعر {price}"
        if source:
            msg += f" (من {source})"
        add_notification(db_run, "payment_click", title, msg,
                         link="/admin/payments", related_user_id=uid)
    except Exception as _e:
        print(f"notif whatsapp click error: {_e}")
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════
# REJECT PLAN REQUEST
# ═══════════════════════════════════════════════════

@app.route("/admin/requests/<int:rid>/reject", methods=["POST"])
@staff_required
def admin_request_reject(rid):
    reason = request.form.get("reason", "").strip()
    db_run("UPDATE plan_requests SET status='rejected', notes=?, updated_at=? WHERE id=?",
           (reason, datetime.now().isoformat(), rid))

    req = db_row("SELECT client_id FROM plan_requests WHERE id=?", (rid,))
    if req:
        admin = db_row("SELECT id FROM users WHERE role='admin' OR is_admin=1 LIMIT 1")
        if admin:
            msg = f"⚠️ طلبك للخطة تم رفضه. السبب: {reason}" if reason else "⚠️ طلبك للخطة تم رفضه. تواصل معنا للمزيد."
            db_run("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?,?,?)",
                   (admin["id"], req["client_id"], msg))
    return redirect("/admin/requests")


# ═══════════════════════════════════════════════════
# BLOCK / UNBLOCK USERS  
# ═══════════════════════════════════════════════════

@app.route("/admin/users/<int:uid>/block", methods=["POST"])
@admin_required
def admin_block_user(uid):
    user = get_user_by_id(uid)
    if not user: return redirect("/admin/users")
    reason = request.form.get("reason", "").strip()

    try:
        db_run("INSERT INTO blocked_users (email, reason) VALUES (?,?)", (user["email"].lower(), reason))
    except Exception as e:
        # Blocking the same email twice lands here and is harmless. Anything
        # else means the account gets deactivated below without making it onto
        # the block list, so the person could sign up again with that email --
        # worth seeing in the logs rather than losing.
        log_error(f"blocked_users insert for {user['email'].lower()!r}", e)

    db_run("UPDATE users SET active=0 WHERE id=?", (uid,))
    return redirect("/admin/users")


@app.route("/admin/users/<int:uid>/unblock", methods=["POST"])
@admin_required
def admin_unblock_user(uid):
    user = get_user_by_id(uid)
    if not user: return redirect("/admin/users")

    db_run("DELETE FROM blocked_users WHERE email=?", (user["email"].lower(),))
    db_run("UPDATE users SET active=1 WHERE id=?", (uid,))
    return redirect("/admin/users")


@app.route("/admin/blocked")
@admin_required
def admin_blocked_list():
    try:
        blocked = db_rows("SELECT * FROM blocked_users ORDER BY blocked_at DESC")
    except Exception:
        try:
            if DATABASE_URL:
                db_run("""CREATE TABLE IF NOT EXISTS blocked_users (id SERIAL PRIMARY KEY, email TEXT UNIQUE, blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason TEXT)""")
            else:
                db_run("""CREATE TABLE IF NOT EXISTS blocked_users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason TEXT)""")
        except: pass
        blocked = []
    user = get_user_by_id(session["uid"])
    return render_template("admin_blocked.html", blocked=blocked, user=user, lang=session.get("lang","ar"))


@app.route("/admin/blocked/<int:bid>/remove", methods=["POST"])
@admin_required
def admin_blocked_remove(bid):
    row = db_row("SELECT email FROM blocked_users WHERE id=?", (bid,))
    if row:
        db_run("UPDATE users SET active=1 WHERE email=?", (row["email"],))
    db_run("DELETE FROM blocked_users WHERE id=?", (bid,))
    return redirect("/admin/blocked")


@app.route("/regenerate_plan", methods=["POST"])
@staff_required
def regenerate_plan():
    data = session.get("pdf_data")
    if not data: return redirect("/generate")
    session["current_plan"] = generate_weekly_plan(data)
    return redirect("/preview")

@app.route("/download_pdf")
@login_required
def download_pdf():
    data = session.get("pdf_data")
    plan = session.get("current_plan")
    u = get_user_by_id(session["uid"])
    role = get_user_role(u)
    if role == "client":
        try:
            latest = db_row("SELECT * FROM plan_requests WHERE client_id=? AND status='approved' ORDER BY updated_at DESC LIMIT 1", (session["uid"],))
            if latest and latest.get("plan_data"):
                pd = json.loads(latest["plan_data"])
                data = pd.get("data")
                plan = pd.get("plan")
        except: pass
    if not data: return redirect("/dashboard")
    try:
        pdf_bytes = build_pdf(data, plan)
        buf = io.BytesIO(pdf_bytes); buf.seek(0)
        name = data.get("name","plan").replace(" ","_")
        return send_file(buf, as_attachment=True, download_name=f"NutraX_{name}.pdf", mimetype="application/pdf")
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"خطأ: {str(e)}", 500


@app.route("/patients")
@staff_required
def patients():
    u = get_user_by_id(session["uid"])
    search = request.args.get("q","")
    status_filter = request.args.get("status","")
    sql = "SELECT * FROM patients WHERE user_id=?"
    params = [session["uid"]]
    if search: sql += " AND name LIKE ?"; params.append(f"%{search}%")
    if status_filter: sql += " AND status=?"; params.append(status_filter)
    sql += " ORDER BY created_at DESC"
    try: pts = db_rows(sql, tuple(params))
    except: pts = []
    return render_template("patients.html", user=u, lang=session.get("lang","ar"),
                           patients=pts, search=search, status=status_filter)

@app.route("/patients/new", methods=["GET","POST"])
@staff_required
def new_patient():
    u = get_user_by_id(session["uid"])
    if request.method == "POST":
        db_run("""INSERT INTO patients (user_id,name,age,gender,height,weight,fat_pct,bmi,tdee,goal_cal,conditions,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (session["uid"], request.form.get("name",""), request.form.get("age",0),
             request.form.get("gender","ذكر"), request.form.get("height",0),
             request.form.get("weight",0), request.form.get("fat_pct",0),
             request.form.get("bmi",0), request.form.get("tdee",0),
             request.form.get("goal_cal",1400),
             json.dumps(request.form.getlist("conditions")),
             request.form.get("notes","")))
        return redirect("/patients")
    return render_template("new_patient.html", user=u, lang=session.get("lang","ar"))

@app.route("/patients/<int:pid>")
@staff_required
def view_patient(pid):
    u = get_user_by_id(session["uid"])
    pt = db_row("SELECT * FROM patients WHERE id=? AND user_id=?", (pid, session["uid"]))
    if not pt: return redirect("/patients")
    plans = db_rows("SELECT * FROM saved_plans WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (session["uid"],))
    return render_template("view_patient.html", user=u, lang=session.get("lang","ar"), patient=pt, plans=plans)

@app.route("/patients/<int:pid>/generate")
@staff_required
def patient_generate(pid):
    pt = db_row("SELECT * FROM patients WHERE id=? AND user_id=?", (pid, session["uid"]))
    if not pt: return redirect("/patients")
    data = {
        "name": pt["name"], "age": pt["age"], "gender": pt["gender"],
        "height": pt["height"], "weight": pt["weight"], "fat_pct": pt["fat_pct"],
        "bmi": pt["bmi"], "tdee": pt["tdee"], "goal_cal": pt["goal_cal"],
        "goal_type": "weight_loss", "culture": "مصري", "diet_plan_type": "standard",
        "symptoms": json.loads(pt["conditions"] or "[]"), "notes": pt["notes"] or "",
    }
    session["pdf_data"] = data
    session["current_plan"] = generate_weekly_plan(data)
    return redirect("/preview")

@app.route("/patients/<int:pid>/status/<s>")
@staff_required
def update_patient_status(pid, s):
    if s in ["draft","published"]:
        db_run("UPDATE patients SET status=? WHERE id=? AND user_id=?", (s, pid, session["uid"]))
    return redirect(f"/patients/{pid}")

@app.route("/patients/<int:pid>/delete", methods=["POST"])
@staff_required
def delete_patient(pid):
    db_run("DELETE FROM patients WHERE id=? AND user_id=?", (pid, session["uid"]))
    return redirect("/patients")


# ═══════════════════════════════════════════════════════════════════
# ADMIN USER PROFILE - صفحة العميل الشاملة
# ═══════════════════════════════════════════════════════════════════

@app.route("/admin/users/<int:uid>")
@admin_required
def admin_user_profile(uid):
    """عرض صفحة الملف الشامل للعميل"""
    target_user = get_user_by_id(uid)
    if not target_user:
        return redirect("/admin/users")

    conditions = []
    allergies = []
    liked_foods = []
    disliked_foods = []
    try:
        if target_user.get("conditions"):
            conditions = json.loads(target_user["conditions"])
    except: pass
    try:
        if target_user.get("allergies"):
            allergies = json.loads(target_user["allergies"])
    except: pass
    try:
        if target_user.get("liked_foods"):
            liked_foods = json.loads(target_user["liked_foods"])
    except: pass
    try:
        if target_user.get("disliked_foods"):
            disliked_foods = json.loads(target_user["disliked_foods"])
    except: pass

    bmi = None
    try:
        h = float(target_user.get("height") or 0)
        w = float(target_user.get("weight") or 0)
        if h > 0 and w > 0:
            bmi = w / ((h / 100) ** 2)
    except: pass

    tdee = None
    try:
        h = float(target_user.get("height") or 0)
        w = float(target_user.get("weight") or 0)
        a = float(target_user.get("age") or 0)
        gender = (target_user.get("gender") or "ذكر").lower()
        activity = float(target_user.get("activity") or 1.55)
        if h > 0 and w > 0 and a > 0:
            if gender in ("ذكر", "male", "m"):
                bmr = 10 * w + 6.25 * h - 5 * a + 5
            else:
                bmr = 10 * w + 6.25 * h - 5 * a - 161
            tdee = int(bmr * activity)
    except: pass

    active_sub = None
    try:
        sub = db_row("""SELECT * FROM subscriptions 
                        WHERE user_id=? AND status IN ('active', 'trialing') 
                        ORDER BY current_period_end DESC LIMIT 1""", (uid,))
        if sub:
            active_sub = dict(sub)
            plan_info = PRICING.get(sub.get("plan_key"), {})
            active_sub["plan_name"] = _plan_name(plan_info, sub.get("plan_key"))
            for k in ("current_period_start", "current_period_end", "trial_end"):
                v = active_sub.get(k)
                if v:
                    if hasattr(v, "strftime"):
                        active_sub[k.replace("current_period_", "") + "_date" if k.startswith("current_period_") else k] = v.strftime("%Y-%m-%d")
                    else:
                        active_sub[k.replace("current_period_", "") + "_date" if k.startswith("current_period_") else k] = str(v)[:10]
            active_sub["start_date"] = active_sub.get("start_date") or "-"
            active_sub["end_date"] = active_sub.get("end_date") or "-"
    except: pass

    active_payment = None
    try:
        pay = db_row("""SELECT * FROM payments 
                        WHERE user_id=? AND status='completed' 
                        AND expires_at > ? 
                        ORDER BY expires_at DESC LIMIT 1""", (uid, datetime.now()))
        if pay:
            active_payment = dict(pay)
            plan_info = PRICING.get(pay.get("plan_key"), {})
            active_payment["plan_name"] = _plan_name(plan_info, pay.get("plan_key"))
            v = active_payment.get("expires_at")
            if v:
                active_payment["expires"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
    except: pass

    plan_requests = []
    try:
        plans = db_rows("SELECT * FROM plan_requests WHERE client_id=? ORDER BY created_at DESC LIMIT 50", (uid,))
        for p in plans:
            pd = dict(p)
            v = pd.get("created_at")
            if v:
                pd["created_date"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
            plan_requests.append(pd)
    except: pass

    payments = []
    try:
        pays = db_rows("SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (uid,))
        for p in pays:
            pd = dict(p)
            plan_info = PRICING.get(pd.get("plan_key"), {})
            pd["plan_label"] = plan_info.get("name", pd.get("plan_key"))
            v = pd.get("created_at")
            if v:
                pd["created_date"] = v.strftime("%Y-%m-%d %H:%M") if hasattr(v, "strftime") else str(v)[:16]
            v2 = pd.get("expires_at")
            if v2:
                pd["expires_date"] = v2.strftime("%Y-%m-%d") if hasattr(v2, "strftime") else str(v2)[:10]
            payments.append(pd)
    except: pass

    weight_logs = []
    try:
        logs = db_rows("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at DESC LIMIT 30", (uid,))
        prev = None
        logs_list = list(logs)
        for i, w in enumerate(logs_list):
            wd = dict(w)
            v = wd.get("logged_at")
            if v:
                wd["logged_date"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
            if i + 1 < len(logs_list):
                try:
                    diff = float(wd["weight"]) - float(logs_list[i + 1]["weight"])
                    wd["diff"] = diff
                except: wd["diff"] = None
            else:
                wd["diff"] = None
            weight_logs.append(wd)
    except: pass

    return render_template("admin_user_profile.html",
                           user=target_user, lang=session.get("lang", "ar"),
                           client_whatsapp=build_whatsapp_link(target_user.get("phone"), target_user.get("country")),
                           tracking=get_meal_tracking(uid),
                           conditions=conditions, allergies=allergies,
                           liked_foods=liked_foods, disliked_foods=disliked_foods,
                           bmi=bmi, tdee=tdee,
                           active_sub=active_sub, active_payment=active_payment,
                           plan_requests=plan_requests, payments=payments,
                           weight_logs=weight_logs,
                           doctor_notes=target_user.get("doctor_notes") or "",
                           today_date=datetime.now().strftime("%Y-%m-%d"))


@app.route("/admin/users/<int:uid>/update", methods=["POST"])
@admin_required
def admin_user_update(uid):
    """تعديل بيانات العميل الشاملة"""
    target = get_user_by_id(uid)
    if not target:
        return redirect("/admin/users")
    try:
        name = request.form.get("name", "").strip() or target.get("name")
        email = request.form.get("email", "").strip().lower() or target.get("email")
        phone = request.form.get("phone", "").strip() or target.get("phone")
        country = request.form.get("country", "").strip() or target.get("country")
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip() or target.get("gender")

        weight = request.form.get("weight", "").strip()
        height = request.form.get("height", "").strip()
        goal = request.form.get("goal", "").strip() or target.get("goal")
        activity = request.form.get("activity", "").strip()

        conditions = request.form.get("conditions", "[]")
        allergies = request.form.get("allergies", "[]")

        liked_text = request.form.get("liked_foods_text", "").strip()
        disliked_text = request.form.get("disliked_foods_text", "").strip()

        def text_to_json(txt):
            if not txt:
                return "[]"
            items = [s.strip() for s in txt.replace("،", ",").replace(";", ",").split(",") if s.strip()]
            return json.dumps(items, ensure_ascii=False)

        liked_foods = text_to_json(liked_text)
        disliked_foods = text_to_json(disliked_text)

        try: age_v = int(age) if age else target.get("age")
        except: age_v = target.get("age")
        try: weight_v = float(weight) if weight else target.get("weight")
        except: weight_v = target.get("weight")
        try: height_v = float(height) if height else target.get("height")
        except: height_v = target.get("height")
        try: activity_v = float(activity) if activity else target.get("activity")
        except: activity_v = target.get("activity")

        db_run("""UPDATE users SET 
                  name=?, email=?, phone=?, country=?, age=?, gender=?,
                  weight=?, height=?, goal=?, activity=?,
                  conditions=?, allergies=?,
                  liked_foods=?, disliked_foods=?
                  WHERE id=?""",
               (name, email, phone, country, age_v, gender,
                weight_v, height_v, goal, activity_v,
                conditions, allergies,
                liked_foods, disliked_foods,
                uid))

        if weight and weight_v and float(weight_v) != (target.get("weight") or 0):
            try:
                db_run("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)", (uid, weight_v))
            except: pass
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"Update error: {e}")
    return redirect(f"/admin/users/{uid}?updated=1")


@app.route("/admin/users/<int:uid>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(uid):
    """الأدمن يعيّن كلمة سر جديدة لعميل نسي كلمة سره"""
    target = db_row("SELECT * FROM users WHERE id=?", (uid,))
    if not target or target.get("is_admin"):
        return redirect("/admin/users")
    new_pw = request.form.get("new_password", "").strip()
    if len(new_pw) < 6:
        return redirect(f"/admin/users/{uid}?pwreset=short")
    try:
        db_run("UPDATE users SET password=? WHERE id=?", (hp(new_pw), uid))
        return redirect(f"/admin/users/{uid}?pwreset=ok")
    except Exception as e:
        print(f"admin reset password error: {e}")
        return redirect(f"/admin/users/{uid}?pwreset=err")


@app.route("/admin/users/<int:uid>/notes", methods=["POST"])
@admin_required
def admin_user_notes(uid):
    """حفظ ملاحظات الدكتور الخاصة عن العميل"""
    notes = request.form.get("notes", "").strip()
    try:
        db_run("UPDATE users SET doctor_notes=? WHERE id=?", (notes, uid))
    except Exception as e:
        print(f"Notes save error: {e}")
    return redirect(f"/admin/users/{uid}")


@app.route("/admin/users/<int:uid>/add-weight", methods=["POST"])
@admin_required
def admin_user_add_weight(uid):
    """إضافة قياس وزن يدوياً للعميل"""
    try:
        w = float(request.form.get("weight", 0))
        if 20 < w < 300:
            logged_date = request.form.get("logged_date", "")
            if logged_date:
                db_run("INSERT INTO weight_log (user_id, weight, logged_at) VALUES (?, ?, ?)",
                       (uid, w, logged_date))
            else:
                db_run("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)", (uid, w))
            db_run("UPDATE users SET weight=? WHERE id=?", (w, uid))
    except Exception as e:
        print(f"Add weight error: {e}")
    return redirect(f"/admin/users/{uid}")


@app.route("/admin/users/<int:uid>/manual-activate", methods=["POST"])
@admin_required
def admin_manual_activate(uid):
    """تفعيل اشتراك مدفوع للعميل يدوياً (بعد ما يدفع عبر واتساب)"""
    target = get_user_by_id(uid)
    if not target:
        return redirect("/admin/users")

    try:
        plan_key = request.form.get("plan_key", "").strip()
        amount_raw = request.form.get("amount", "0").strip()
        currency = request.form.get("currency", "EGP").strip()
        payment_method = request.form.get("payment_method", "other").strip()
        notes = request.form.get("notes", "").strip()

        if plan_key not in ("consultation", "single_plan", "monthly_subscription"):
            return redirect(f"/admin/users/{uid}?error=invalid_plan")

        try:
            amount_value = float(amount_raw or 0)
            amount_cents = int(amount_value * 100)
        except:
            amount_cents = 0

        duration_days_map = {
            "consultation": 1,
            "single_plan": 7,
            "monthly_subscription": 30,
        }
        plan_names_map = {
            "consultation": "استشارة فردية",
            "single_plan": "خطة واحدة",
            "monthly_subscription": "اشتراك شهري",
        }
        method_names = {
            "vodafone_cash": "فودافون كاش",
            "instapay": "InstaPay",
            "bank_transfer_eg": "تحويل بنكي مصري",
            "bank_transfer_ae": "تحويل بنكي إماراتي",
            "cash": "كاش",
            "other": "طريقة أخرى",
        }

        duration_days = duration_days_map.get(plan_key, 30)
        plan_name = plan_names_map.get(plan_key, plan_key)
        method_name = method_names.get(payment_method, payment_method)

        now = datetime.now()
        end_date = now + timedelta(days=duration_days)

        metadata = {
            "manual_activation": True,
            "payment_method": payment_method,
            "method_name": method_name,
            "notes": notes,
            "activated_by_admin": session.get("uid"),
        }

        try:
            db_run("""INSERT INTO payments 
                      (user_id, stripe_session_id, plan_key, status, currency, amount, expires_at, metadata)
                      VALUES (?, ?, ?, 'completed', ?, ?, ?, ?)""",
                   (uid, f"manual_{uid}_{int(now.timestamp())}", plan_key,
                    currency, amount_cents, end_date, json.dumps(metadata, ensure_ascii=False)))
        except Exception as e:
            print(f"Insert payment error: {e}")

        if plan_key == "monthly_subscription":
            try:
                db_run("""INSERT INTO subscriptions
                          (user_id, plan_key, status, currency, amount,
                           current_period_start, current_period_end,
                           stripe_subscription_id)
                          VALUES (?, ?, 'active', ?, ?, ?, ?, ?)""",
                       (uid, plan_key, currency, amount_cents,
                        now, end_date, f"manual_sub_{uid}_{int(now.timestamp())}"))
            except Exception as e:
                print(f"Insert subscription error: {e}")

        try:
            admin = db_row("SELECT id FROM users WHERE role='admin' OR is_admin=1 LIMIT 1")
            if admin:
                msg = f"""✅ تم تفعيل اشتراكك بنجاح!

📋 الخطة: {plan_name}
💰 المبلغ: {amount_value:.0f} {currency}
💳 طريقة الدفع: {method_name}
📅 ساري حتى: {end_date.strftime('%Y-%m-%d')}

شكراً لثقتك فينا. تقدر تستخدم كل خدمات الموقع دلوقتي."""
                db_run("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                       (admin["id"], uid, msg))
        except Exception as e:
            print(f"Send message error: {e}")

    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"Manual activate error: {e}")
        return redirect(f"/admin/users/{uid}?error=activation_failed")

    return redirect(f"/admin/users/{uid}?activated=1")


@app.route("/admin/users/<int:uid>/grant-trial", methods=["POST"])
@admin_required
def admin_grant_trial(uid):
    """إعطاء العميل 7 أيام تجربة مجاناً (يدوي - بدون Stripe)"""
    target = get_user_by_id(uid)
    if not target:
        return redirect("/admin/users")
    try:
        if has_active_access(uid, db_row):
            return redirect(f"/admin/users/{uid}")
        now = datetime.now()
        trial_end = now + timedelta(days=7)
        db_run("""INSERT INTO subscriptions 
                  (user_id, plan_key, status, currency, amount,
                   current_period_start, current_period_end, trial_end,
                   stripe_subscription_id)
                  VALUES (?, 'monthly_subscription', 'trialing', 'EGP', 0, ?, ?, ?, ?)""",
               (uid, now, trial_end, trial_end, f"manual_trial_{uid}_{int(now.timestamp())}"))
        admin = db_row("SELECT id FROM users WHERE role='admin' OR is_admin=1 LIMIT 1")
        if admin:
            msg = "🎁 تم منحك فترة تجريبية مجانية 7 أيام! تقدر تستخدم كل خدمات الموقع مجاناً."
            db_run("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                   (admin["id"], uid, msg))
    except Exception as e:
        print(f"Grant trial error: {e}")
    return redirect(f"/admin/users/{uid}")


@app.route("/admin/users/<int:uid>/cancel-subscription", methods=["POST"])
@admin_required
def admin_cancel_subscription(uid):
    """إلغاء اشتراك العميل من جهة admin"""
    try:
        sub = db_row("""SELECT * FROM subscriptions 
                        WHERE user_id=? AND status IN ('active', 'trialing') 
                        ORDER BY current_period_end DESC LIMIT 1""", (uid,))
        if sub:
            sub_id = sub.get("stripe_subscription_id", "")
            if sub_id and not sub_id.startswith("manual_"):
                try:
                    import stripe as _stripe
                    _stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
                    _stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
                except Exception as e:
                    print(f"Stripe cancel error: {e}")
            db_run("""UPDATE subscriptions SET status='canceled', cancel_at=?, updated_at=? 
                      WHERE id=?""", (datetime.now(), datetime.now(), sub["id"]))
    except Exception as e:
        print(f"Cancel subscription error: {e}")
    return redirect(f"/admin/users/{uid}")


@app.route("/admin/users/<int:uid>/payments")
@admin_required
def admin_user_payments(uid):
    """صفحة كل دفعات العميل (redirect لصفحة الـ admin payments مع filter)"""
    return redirect(f"/admin/payments?user={uid}")


# ═══════════════════════════════════════════════════════════════════
# ONBOARDING WIZARD - استبيان العملاء الجداد
# ═══════════════════════════════════════════════════════════════════

ONBOARDING_EXEMPT = {
    "login", "logout", "set_lang", "onboarding", "static", "health", "assetlinks",
    "stripe_webhook", "check_access_endpoint", "register",
    "track_whatsapp_click", "pricing", "payment_cancel",
    "developers_docs", "api_v1_health", "api_v1_meal_plan", "api_v1_barcode",
}

@app.before_request
def check_onboarding_status():
    """Middleware: العملاء الجداد بيتحولوا للاستبيان تلقائياً"""
    if not request.endpoint or request.endpoint in ONBOARDING_EXEMPT:
        return None
    if request.path.startswith("/static") or request.path.startswith("/webhook") or request.path.startswith("/track") or request.path.startswith("/push"):
        return None
    if "uid" not in session:
        return None
    try:
        user = get_user_by_id(session["uid"])
        if not user:
            return None
        if user.get("is_admin") or user.get("role") in ("admin", "nutritionist"):
            return None
        if user.get("onboarded_at"):
            return None
        if request.path != "/onboarding":
            return redirect("/onboarding")
    except Exception as e:
        print(f"Onboarding middleware error: {e}")
    return None


# ═══════════════════════════════════════════════════════════════════
# UNIFIED REGISTER (Sign-up + Onboarding في صفحة واحدة)
# ═══════════════════════════════════════════════════════════════════

@app.route("/register", methods=["GET", "POST"])
def register_wizard():
    """صفحة التسجيل الموحدة - sign-up + onboarding مدمجين"""
    if "uid" in session:
        return redirect("/dashboard")

    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").lower().strip()
            password = request.form.get("password", "")
            phone = request.form.get("phone", "").strip()

            country = request.form.get("country", "").strip()
            age = request.form.get("age", "").strip()
            gender = request.form.get("gender", "").strip()
            height = request.form.get("height", "").strip()
            weight = request.form.get("weight", "").strip()

            goal = request.form.get("goal", "weight_loss").strip()
            activity = request.form.get("activity", "1.55").strip()

            liked_foods = request.form.get("liked_foods", "[]")
            disliked_foods = request.form.get("disliked_foods", "[]")
            allergies = request.form.get("allergies", "[]")
            conditions = request.form.get("conditions", "[]")

            sleep_hours = request.form.get("sleep_hours", "").strip()
            water_cups = request.form.get("water_cups", "").strip()
            stress_level = request.form.get("stress_level", "").strip()
            caffeine = request.form.get("caffeine", "").strip()
            smoking = request.form.get("smoking", "").strip()

            medications = request.form.get("medications", "").strip()
            past_surgeries = request.form.get("past_surgeries", "").strip()
            family_diseases = request.form.get("family_diseases", "[]")
            supplements = request.form.get("supplements", "[]")

            try:
                lifestyle_data = json.dumps({
                    "sleep_hours": int(sleep_hours) if sleep_hours else None,
                    "water_cups": int(water_cups) if water_cups else None,
                    "stress_level": int(stress_level) if stress_level else None,
                    "caffeine": caffeine,
                    "smoking": smoking,
                    "medications": medications,
                    "past_surgeries": past_surgeries,
                    "family_diseases": json.loads(family_diseases) if family_diseases else [],
                    "supplements": json.loads(supplements) if supplements else [],
                }, ensure_ascii=False)
            except:
                lifestyle_data = "{}"

            if not all([name, email, password, phone, country, age, gender, height, weight]):
                return render_template("register.html",
                                       lang=session.get("lang", "ar"),
                                       error="من فضلك املأ كل الحقول المطلوبة")

            if len(password) < 6:
                return render_template("register.html",
                                       lang=session.get("lang", "ar"),
                                       error="كلمة السر لازم 6 حروف على الأقل")

            if is_email_blocked(email):
                return render_template("register.html",
                                       lang=session.get("lang", "ar"),
                                       error="هذا الإيميل محظور")

            existing = db_row("SELECT id FROM users WHERE email=?", (email,))
            if existing:
                return render_template("register.html",
                                       lang=session.get("lang", "ar"),
                                       error="الإيميل ده مستخدم قبل كده - سجل دخول")

            try: age_v = int(age)
            except: age_v = None
            try: height_v = float(height)
            except: height_v = None
            try: weight_v = float(weight)
            except: weight_v = None
            try: activity_v = float(activity)
            except: activity_v = 1.55

            db_run("""INSERT INTO users 
                      (name, email, password, country, age, gender, height, weight, 
                       goal, activity, phone, role, active,
                       liked_foods, disliked_foods, allergies, conditions, onboarded_at, lifestyle_data)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,'client',1,?,?,?,?,?,?)""",
                   (name, email, hp(password), country, age_v, gender,
                    height_v, weight_v, goal, activity_v, phone,
                    liked_foods, disliked_foods, allergies, conditions, datetime.now(),
                    lifestyle_data))

            new_user = get_user(email, password)
            if new_user:
                session.permanent = True
                session["uid"] = new_user["id"]
                session["lang"] = "ar"
                session["role"] = "client"

                try:
                    if weight_v:
                        db_run("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)",
                               (new_user["id"], weight_v))
                except: pass

                # ── إشعار للأدمن: عميل جديد سجّل ──
                try:
                    add_notification(
                        db_run, "new_client",
                        f"عميل جديد سجّل: {name}",
                        f"الاسم: {name}\nالبلد: {country}\nالتليفون: {phone}\nالإيميل: {email}",
                        link="/admin/users",
                        related_user_id=new_user["id"]
                    )
                except Exception as _e:
                    print(f"notif new_client error: {_e}")

                return redirect("/my-plan?welcome=1")
            else:
                return render_template("register.html",
                                       lang=session.get("lang", "ar"),
                                       error="حصلت مشكلة - حاول تاني")

        except Exception as e:
            import traceback; traceback.print_exc()
            return render_template("register.html",
                                   lang=session.get("lang", "ar"),
                                   error=f"خطأ: {str(e)}")

    return render_template("register.html", lang=session.get("lang", "ar"))


@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    """صفحة الاستبيان المبدئي للعميل الجديد"""
    user = get_user_by_id(session["uid"])
    if not user:
        return redirect("/")

    if user.get("is_admin") or user.get("role") in ("admin", "nutritionist"):
        return redirect("/dashboard")

    if request.method == "POST":
        try:
            age = request.form.get("age", "").strip()
            gender = request.form.get("gender", "").strip()
            height = request.form.get("height", "").strip()
            weight = request.form.get("weight", "").strip()
            goal = request.form.get("goal", "weight_loss").strip()
            activity = request.form.get("activity", "1.55").strip()

            liked_foods = request.form.get("liked_foods", "[]")
            disliked_foods = request.form.get("disliked_foods", "[]")
            conditions = request.form.get("conditions", "[]")
            allergies = request.form.get("allergies", "[]")

            _lang = session.get("lang", "ar")
            if not (age and gender and height and weight):
                return render_template("onboarding.html",
                                       user=user, lang=_lang,
                                       error="من فضلك املأ كل الحقول المطلوبة" if _lang == "ar"
                                       else "Please fill in all required fields")

            db_run("""UPDATE users SET 
                      age=?, gender=?, height=?, weight=?, goal=?, activity=?,
                      liked_foods=?, disliked_foods=?, conditions=?, allergies=?,
                      onboarded_at=?
                      WHERE id=?""",
                   (int(age) if age else None, gender,
                    float(height) if height else None,
                    float(weight) if weight else None,
                    goal, float(activity) if activity else 1.55,
                    liked_foods, disliked_foods, conditions, allergies,
                    datetime.now(), session["uid"]))

            try:
                db_run("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)",
                       (session["uid"], float(weight)))
            except: pass

            return redirect("/dashboard?welcome=1")
        except Exception as e:
            import traceback; traceback.print_exc()
            _lang = session.get("lang", "ar")
            return render_template("onboarding.html",
                                   user=user, lang=_lang,
                                   error=(f"خطأ في الحفظ: {e}" if _lang == "ar"
                                          else f"Could not save: {e}"))

    return render_template("onboarding.html",
                           user=user, lang=session.get("lang", "ar"))


# ═══════════════════════════════════════════════════════════════════
# MY PLANS HISTORY - العميل يشوف خططه السابقة
# ═══════════════════════════════════════════════════════════════════

@app.route("/my-plans-history")
@login_required
def my_plans_history():
    """قائمة كل خطط العميل السابقة"""
    user = get_user_by_id(session["uid"])
    if not user:
        return redirect("/")
    if user.get("is_admin") or user.get("role") in ("admin", "nutritionist"):
        return redirect("/admin/requests")

    plans_processed = []
    active_count = 0
    archived_count = 0
    days_following = 0

    try:
        rows = db_rows("""SELECT * FROM plan_requests 
                          WHERE client_id=? AND status='approved' 
                          ORDER BY created_at DESC""", (session["uid"],))

        latest_active_id = rows[0]["id"] if rows else None

        for r in rows:
            p = dict(r)
            try:
                rd = json.loads(p.get("request_data") or "{}")
            except: rd = {}

            p["goal_type"] = rd.get("goal_type") or "weight_loss"
            p["culture"] = rd.get("culture") or "مصري"
            p["weight"] = rd.get("weight") or "-"
            p["goal_cal"] = rd.get("goal_cal") or "-"
            p["conditions_count"] = len(rd.get("symptoms", []) or [])
            p["is_currently_active"] = (p["id"] == latest_active_id)

            v = p.get("created_at")
            if v:
                p["created_date"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
            else:
                p["created_date"] = "-"

            plans_processed.append(p)

        active_count = sum(1 for p in plans_processed if p["is_currently_active"])
        archived_count = len(plans_processed) - active_count

        if rows:
            first_date = rows[-1].get("created_at")
            if first_date and hasattr(first_date, "date"):
                days_following = max(0, (datetime.now().date() - first_date.date()).days)
            elif first_date:
                try:
                    fd = datetime.fromisoformat(str(first_date)[:19])
                    days_following = max(0, (datetime.now() - fd).days)
                except: pass
    except Exception as e:
        print(f"my_plans_history error: {e}")

    return render_template("my_plans_history.html",
                           user=user, lang=session.get("lang", "ar"),
                           plans=plans_processed,
                           active_count=active_count,
                           archived_count=archived_count,
                           days_following=days_following)


@app.route("/my-plans-history/<int:plan_id>")
@login_required
def my_plans_history_view(plan_id):
    """عرض خطة قديمة كاملة"""
    user = get_user_by_id(session["uid"])
    if not user:
        return redirect("/")

    plan_req = db_row("SELECT * FROM plan_requests WHERE id=? AND client_id=?",
                      (plan_id, session["uid"]))
    if not plan_req:
        return redirect("/my-plans-history")

    try:
        request_data = json.loads(plan_req.get("request_data") or "{}")
    except: request_data = {}

    plan_data = {}
    plan_days = []
    if plan_req.get("plan_data"):
        try:
            pd = json.loads(plan_req["plan_data"])
            plan_data = pd.get("data", request_data)
            plan_days = pd.get("plan", [])
        except: pass

    if not plan_data:
        plan_data = request_data

    diet_type = plan_data.get("diet_plan_type", "standard")
    plan_info = get_diet_plan_info(diet_type)

    created_str = "-"
    v = plan_req.get("created_at")
    if v:
        created_str = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]

    return render_template("view_old_plan.html",
                           user=user, lang=session.get("lang", "ar"),
                           plan_req=plan_req, plan_data=plan_data,
                           plan_days=plan_days, plan_info=plan_info,
                           created_date=created_str,
                           request_data=request_data)


@app.route("/my-plans-history/<int:plan_id>/pdf")
@login_required
def my_plans_history_pdf(plan_id):
    """تحميل PDF لخطة قديمة"""
    plan_req = db_row("SELECT * FROM plan_requests WHERE id=? AND client_id=?",
                      (plan_id, session["uid"]))
    if not plan_req:
        return redirect("/my-plans-history")

    try:
        request_data = json.loads(plan_req.get("request_data") or "{}")
    except: request_data = {}

    plan_data = request_data
    plan_days = []
    if plan_req.get("plan_data"):
        try:
            pd = json.loads(plan_req["plan_data"])
            plan_data = pd.get("data", request_data)
            plan_days = pd.get("plan", [])
        except: pass

    user = get_user_by_id(session["uid"])
    plan_data["name"] = user.get("name", "")

    try:
        pdf_bytes = build_pdf(plan_data, plan_days if plan_days else None)
        buf = io.BytesIO(pdf_bytes); buf.seek(0)
        name = (plan_data.get("name", "plan") or "plan").replace(" ", "_")
        return send_file(buf, as_attachment=True,
                         download_name=f"NutraX_{name}_{plan_id}.pdf",
                         mimetype="application/pdf")
    except Exception as e:
        return f"خطأ في توليد PDF: {e}", 500


@app.route("/my-plans-history/<int:plan_id>/reactivate", methods=["POST"])
@subscription_required
def my_plans_history_reactivate(plan_id):
    """إعادة تفعيل خطة قديمة كخطة حالية (بإنشاء request_id جديد بنفس البيانات)"""
    plan_req = db_row("SELECT * FROM plan_requests WHERE id=? AND client_id=?",
                      (plan_id, session["uid"]))
    if not plan_req:
        return redirect("/my-plans-history")

    try:
        db_run("""INSERT INTO plan_requests 
                  (client_id, client_name, request_data, plan_data, status, notes)
                  VALUES (?, ?, ?, ?, 'approved', ?)""",
               (session["uid"],
                plan_req.get("client_name", ""),
                plan_req.get("request_data", "{}"),
                plan_req.get("plan_data", "{}"),
                "إعادة تفعيل خطة سابقة #" + str(plan_id)))
    except Exception as e:
        print(f"Reactivate error: {e}")

    return redirect("/my-plans-history")


@app.route("/my-plans-history/<int:plan_id>/edit")
@subscription_required
def my_plans_history_edit(plan_id):
    """تعديل خطة قديمة (يفتح request-plan بالبيانات القديمة)"""
    plan_req = db_row("SELECT * FROM plan_requests WHERE id=? AND client_id=?",
                      (plan_id, session["uid"]))
    if not plan_req:
        return redirect("/my-plans-history")

    try:
        session["prefill_data"] = json.loads(plan_req.get("request_data") or "{}")
    except: pass

    return redirect("/request-plan?edit=" + str(plan_id))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")






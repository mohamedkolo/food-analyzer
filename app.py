from flask import Flask, render_template, request, redirect, session, send_file, jsonify
import hashlib, os, json, io, random
from datetime import timedelta, datetime

app = Flask(__name__)
from pdf_generator import pdf_bp
app.register_blueprint(pdf_bp)
app.secret_key = os.environ.get("SECRET_KEY", "nutrax2025")
app.permanent_session_lifetime = timedelta(days=30)

from meal_database import (
    get_meal_pool, get_snacks_for_goal, filter_by_conditions,
    get_diet_plan_info, DIET_PLAN_TYPES,
    WEIGHT_LOSS, MUSCLE_GAIN, BULKING, MAINTENANCE
)

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import psycopg2, psycopg2.extras
    def get_db(): return psycopg2.connect(DATABASE_URL)
    def db_row(sql, params=()):
        sql = sql.replace("?","%s")
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params); r = cur.fetchone(); conn.close(); return r
    def db_rows(sql, params=()):
        sql = sql.replace("?","%s")
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params); r = cur.fetchall(); conn.close(); return r
    def db_run(sql, params=(), commit=True):
        sql = sql.replace("?","%s")
        conn = get_db(); cur = conn.cursor()
        try: cur.execute(sql, params)
        except: conn.rollback(); conn.close(); raise
        if commit: conn.commit()
        conn.close()
else:
    import sqlite3
    DB = "/tmp/nutrax.db"
    def get_db():
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row; return conn
    def db_row(sql, params=()):
        conn = get_db(); r = conn.execute(sql, params).fetchone(); conn.close(); return r
    def db_rows(sql, params=()):
        conn = get_db(); r = conn.execute(sql, params).fetchall(); conn.close(); return r
    def db_run(sql, params=(), commit=True):
        conn = get_db(); conn.execute(sql, params)
        if commit: conn.commit()
        conn.close()

def hp(p): return hashlib.sha256(p.encode()).hexdigest()

@app.template_filter('from_json')
def from_json_filter(s):
    if not s: return {}
    try: return json.loads(s)
    except: return {}

def init_db():
    if DATABASE_URL:
        db_run("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, country TEXT, lang TEXT DEFAULT 'ar', height REAL, weight REAL, age INTEGER, gender TEXT DEFAULT 'male', goal TEXT DEFAULT 'maintain', activity REAL DEFAULT 1.55, is_admin INTEGER DEFAULT 0, role TEXT DEFAULT 'client', active INTEGER DEFAULT 1, phone TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS weight_log (id SERIAL PRIMARY KEY, user_id INTEGER, weight REAL, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS saved_plans (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, plan_data TEXT, plan_type TEXT DEFAULT 'personal', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS patients (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, age INTEGER, gender TEXT, height REAL, weight REAL, fat_pct REAL, bmi REAL, tdee INTEGER, goal_cal INTEGER, conditions TEXT, notes TEXT, status TEXT DEFAULT 'draft', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS plan_requests (id SERIAL PRIMARY KEY, client_id INTEGER, client_name TEXT, status TEXT DEFAULT 'pending', request_data TEXT, plan_data TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    else:
        db_run("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, country TEXT, lang TEXT DEFAULT 'ar', height REAL, weight REAL, age INTEGER, gender TEXT DEFAULT 'male', goal TEXT DEFAULT 'maintain', activity REAL DEFAULT 1.55, is_admin INTEGER DEFAULT 0, role TEXT DEFAULT 'client', active INTEGER DEFAULT 1, phone TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS weight_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS saved_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, plan_data TEXT, plan_type TEXT DEFAULT 'personal', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, age INTEGER, gender TEXT, height REAL, weight REAL, fat_pct REAL, bmi REAL, tdee INTEGER, goal_cal INTEGER, conditions TEXT, notes TEXT, status TEXT DEFAULT 'draft', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS plan_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, client_name TEXT, status TEXT DEFAULT 'pending', request_data TEXT, plan_data TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    for col_sql in [
        "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'client'",
        "ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN phone TEXT",
        "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    ]:
        try: db_run(col_sql)
        except: pass

    admin = db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")
    if not admin:
        db_run("INSERT INTO users (name,email,password,is_admin,role,active) VALUES (?,?,?,1,'admin',1)", ("Admin","admin@nutrax.com",hp("nutrax2025")))
    else:
        db_run("UPDATE users SET password=?, is_admin=1, role='admin', active=1 WHERE email='admin@nutrax.com'", (hp("nutrax2025"),))

init_db()

def get_user(email, pw): return db_row("SELECT * FROM users WHERE email=? AND password=?", (email, hp(pw)))
def get_user_by_id(uid): return db_row("SELECT * FROM users WHERE id=?", (uid,))

def register(name, email, pw, country, age=None, phone=None):
    try:
        db_run("""INSERT INTO users (name,email,password,country,age,phone,role,active)
                  VALUES (?,?,?,?,?,?,'client',1)""",
               (name, email, hp(pw), country, age, phone))
        return "ok"
    except:
        return "exists"

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session: return redirect("/")
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session: return redirect("/")
        u = get_user_by_id(session["uid"])
        if not u or (u.get("role") != "admin" and not u.get("is_admin")):
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return decorated

def staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session: return redirect("/")
        u = get_user_by_id(session["uid"])
        if not u or u.get("role") not in ["admin", "nutritionist"]:
            if not u.get("is_admin"):
                return redirect("/my-plan")
        return f(*args, **kwargs)
    return decorated

def get_user_role(u):
    if not u: return "client"
    if u.get("is_admin"): return "admin"
    return u.get("role") or "client"

def get_pending_requests_count():
    try:
        r = db_row("SELECT COUNT(*) as cnt FROM plan_requests WHERE status='pending'")
        return r.get("cnt", 0) if r else 0
    except:
        return 0

def can_log_weight(user_id):
    try:
        latest = db_row("""SELECT * FROM weight_log WHERE user_id=?
                           ORDER BY logged_at DESC LIMIT 1""", (user_id,))
        if not latest:
            return (True, 0, 0)
        date_str = latest.get("logged_at")
        if isinstance(date_str, str):
            try:
                last_date = datetime.fromisoformat(date_str.replace('Z', ''))
            except:
                try:
                    last_date = datetime.strptime(date_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                except:
                    return (True, 0, 0)
        else:
            last_date = date_str
        now = datetime.now()
        diff = now - last_date
        seconds_passed = diff.total_seconds()
        seconds_in_week = 7 * 24 * 60 * 60
        if seconds_passed >= seconds_in_week:
            return (True, 0, 0)
        seconds_left = seconds_in_week - seconds_passed
        days_left = int(seconds_left // (24 * 60 * 60))
        hours_left = int((seconds_left % (24 * 60 * 60)) // 3600)
        return (False, days_left, hours_left)
    except Exception as e:
        print(f"Error: {e}")
        return (True, 0, 0)

def can_request_new_plan(client_id):
    try:
        latest = db_row("""SELECT * FROM plan_requests WHERE client_id=?
                           ORDER BY created_at DESC LIMIT 1""", (client_id,))
        if not latest:
            return (True, 0, 0, None)
        date_str = latest.get("created_at")
        if isinstance(date_str, str):
            try:
                last_date = datetime.fromisoformat(date_str.replace('Z', ''))
            except:
                try:
                    last_date = datetime.strptime(date_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                except:
                    return (True, 0, 0, None)
        else:
            last_date = date_str
        now = datetime.now()
        diff = now - last_date
        seconds_passed = diff.total_seconds()
        seconds_in_week = 7 * 24 * 60 * 60
        if seconds_passed >= seconds_in_week:
            return (True, 0, 0, last_date.strftime("%Y-%m-%d"))
        seconds_left = seconds_in_week - seconds_passed
        days_left = int(seconds_left // (24 * 60 * 60))
        hours_left = int((seconds_left % (24 * 60 * 60)) // 3600)
        return (False, days_left, hours_left, last_date.strftime("%Y-%m-%d"))
    except Exception as e:
        print(f"Error: {e}")
        return (True, 0, 0, None)

@app.route("/", methods=["GET","POST"])
def login():
    if "uid" in session: return redirect("/dashboard")
    lang = session.get("lang", "ar")
    error = ""
    tab = request.args.get("tab", "login")
    if request.method == "POST":
        action = request.form.get("action")
        if action == "login":
            u = get_user(request.form.get("email","").lower(), request.form.get("password",""))
            if u:
                if not u.get("active", 1):
                    error = "هذا الحساب غير مفعل. تواصل مع الإدارة."
                else:
                    session.permanent = True
                    session["uid"] = u["id"]
                    session["lang"] = u["lang"] or "ar"
                    session["role"] = get_user_role(u)
                    return redirect("/dashboard")
            else:
                error = "البريد او كلمة المرور غير صحيحة"
        elif action == "register":
            tab = "register"
            name = request.form.get("name","").strip()
            email = request.form.get("reg_email","").lower().strip()
            pw = request.form.get("reg_password","")
            country = request.form.get("country","")
            age = request.form.get("age","")
            phone = request.form.get("phone","").strip()
            if not name or not email or not pw or not country or not phone:
                error = "كل البيانات مطلوبة"
            elif len(pw) < 6:
                error = "كلمة السر لازم 6 أحرف على الأقل"
            else:
                try:
                    age_int = int(age) if age else None
                except:
                    age_int = None
                r = register(name, email, pw, country, age_int, phone)
                if r == "ok":
                    error = "✓ تم التسجيل بنجاح! سجل دخولك دلوقتي."
                    tab = "login"
                else:
                    error = "البريد الإلكتروني مستخدم بالفعل"
    return render_template("login.html", error=error, tab=tab, lang=lang)

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
    try:
        pending_count = get_pending_requests_count()
        r = db_row("SELECT COUNT(*) as cnt FROM users WHERE role='client'")
        total_clients = r.get("cnt", 0) if r else 0
    except:
        pass
    return render_template("dashboard.html", user=u, lang=session.get("lang","ar"),
                           role=role, pending_count=pending_count, total_clients=total_clients)

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
        latest_plan = db_row("""SELECT * FROM plan_requests WHERE client_id=? AND status='approved'
                                ORDER BY updated_at DESC LIMIT 1""", (session["uid"],))
        pending_request = db_row("""SELECT * FROM plan_requests WHERE client_id=? AND status='pending'
                                    ORDER BY created_at DESC LIMIT 1""", (session["uid"],))
    except:
        pass
    can_request, days_left, hours_left, last_date = can_request_new_plan(session["uid"])
    return render_template("my_plan.html", user=u, lang=session.get("lang","ar"),
                           latest_plan=latest_plan, pending_request=pending_request,
                           can_request=can_request, days_left=days_left,
                           hours_left=hours_left, last_request_date=last_date)

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
        request_data = {
            "height": request.form.get("height", u.get("height", "")),
            "weight": request.form.get("weight", u.get("weight", "")),
            "age": request.form.get("age", u.get("age", "")),
            "gender": request.form.get("gender", u.get("gender", "ذكر")),
            "fat_pct": request.form.get("fat_pct", ""),
            "bmi": request.form.get("bmi", ""),
            "tdee": request.form.get("tdee", ""),
            "goal_cal": request.form.get("goal_cal", ""),
            "goal_type": request.form.get("goal_type", "weight_loss"),
            "culture": request.form.get("culture", "مصري"),
            "diet_plan_type": request.form.get("diet_plan_type", "standard"),
            "symptoms": request.form.getlist("symptoms"),
            "notes": request.form.get("notes", ""),
        }
        try:
            db_run("""INSERT INTO plan_requests (client_id, client_name, request_data, status)
                      VALUES (?, ?, ?, 'pending')""",
                   (session["uid"], u.get("name","Client"), json.dumps(request_data)))
        except Exception as e:
            return f"خطأ: {e}", 500
        return redirect("/my-plan")
    return render_template("request_plan.html", user=u, lang=session.get("lang","ar"),
                           diet_plans=DIET_PLAN_TYPES)

@app.route("/admin/users")
@admin_required
def admin_users():
    u = get_user_by_id(session["uid"])
    try:
        all_users = db_rows("SELECT * FROM users ORDER BY id DESC")
    except:
        all_users = []
    return render_template("admin_users.html", user=u, lang=session.get("lang","ar"), users=all_users)

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
            return render_template("admin_new_user.html", user=u, lang=session.get("lang","ar"),
                                   error="الإيميل وكلمة السر مطلوبة")
        try:
            db_run("INSERT INTO users (name,email,password,role,phone,active) VALUES (?,?,?,?,?,1)",
                   (name, email, hp(pw), role, phone))
            return redirect("/admin/users")
        except:
            return render_template("admin_new_user.html", user=u, lang=session.get("lang","ar"),
                                   error="الإيميل موجود بالفعل")
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
    try:
        requests_list = db_rows("SELECT * FROM plan_requests ORDER BY created_at DESC LIMIT 50")
    except:
        requests_list = []
    return render_template("admin_requests.html", user=u, lang=session.get("lang","ar"), requests=requests_list)

@app.route("/admin/requests/<int:rid>/generate")
@staff_required
def admin_request_generate(rid):
    req = db_row("SELECT * FROM plan_requests WHERE id=?", (rid,))
    if not req:
        return redirect("/admin/requests")
    try:
        rdata = json.loads(req["request_data"])
    except:
        return redirect("/admin/requests")
    client = get_user_by_id(req["client_id"])
    data = {
        "name": client.get("name","") if client else req.get("client_name",""),
        **rdata,
    }
    session["pdf_data"] = data
    session["current_plan"] = generate_weekly_plan(data)
    session["current_request_id"] = rid
    return redirect("/preview")

@app.route("/admin/requests/<int:rid>/approve", methods=["POST"])
@staff_required
def admin_request_approve(rid):
    plan = session.get("current_plan")
    data = session.get("pdf_data")
    if not plan or not data:
        return redirect("/admin/requests")
    db_run("""UPDATE plan_requests SET status='approved', plan_data=?, updated_at=?
              WHERE id=?""",
           (json.dumps({"plan": plan, "data": data}), datetime.now().isoformat(), rid))
    session.pop("current_request_id", None)
    return redirect("/admin/requests")

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

@app.route("/analyzer")
@staff_required
def analyzer():
    return render_template("analyzer.html", user=get_user_by_id(session["uid"]), lang=session.get("lang","ar"))

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
@app.route("/knowledge-hub")
@login_required
def history():
    u = get_user_by_id(session["uid"])
    logs = db_rows("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at DESC LIMIT 30", (session["uid"],))
    can_log, days_left, hours_left = can_log_weight(session["uid"])
    return render_template("history.html", user=u, lang=session.get("lang","ar"),
                           logs=logs, can_log_weight=can_log,
                           days_left=days_left, hours_left=hours_left)

@app.route("/log_weight", methods=["POST"])
@login_required
def log_weight():
    can_log, _, _ = can_log_weight(session["uid"])
    if not can_log:
        return redirect("/history")
    w = request.form.get("weight")
    if w:
        try:
            w_float = float(w)
            if 20 < w_float < 300:
                db_run("INSERT INTO weight_log (user_id,weight) VALUES (?,?)", (session["uid"], w_float))
        except:
            pass
    return redirect("/history")

@app.route("/saved")
@staff_required
def saved():
    u = get_user_by_id(session["uid"])
    plans = db_rows("SELECT * FROM saved_plans WHERE user_id=? ORDER BY created_at DESC", (session["uid"],))
    return render_template("saved.html", user=u, lang=session.get("lang","ar"), plans=plans)

@app.route("/save_plan", methods=["POST"])
@staff_required
def save_plan():
    n = request.form.get("plan_name", "خطتي")
    pt = request.form.get("plan_type", "personal")
    db_run("INSERT INTO saved_plans (user_id,name,plan_data,plan_type) VALUES (?,?,?,?)",
           (session["uid"], n, json.dumps(dict(request.form)), pt))
    return redirect("/saved")

@app.route("/delete_plan/<int:pid>", methods=["POST"])
@staff_required
def delete_plan(pid):
    db_run("DELETE FROM saved_plans WHERE id=? AND user_id=?", (pid, session["uid"]))
    return redirect("/saved")

@app.route("/generate", methods=["GET","POST"])
@staff_required
def generate():
    u = get_user_by_id(session["uid"])
    if request.method == "POST":
        data = {
            "name": request.form.get("name",""), "age": request.form.get("age",""),
            "gender": request.form.get("gender",""), "height": request.form.get("height",""),
            "weight": request.form.get("weight",""), "fat_pct": request.form.get("fat_pct",""),
            "bmi": request.form.get("bmi",""), "tdee": request.form.get("tdee",""),
            "goal_cal": request.form.get("goal_cal","1400"),
            "goal_type": request.form.get("goal_type","weight_loss"),
            "culture": request.form.get("culture","مصري"),
            "diet_plan_type": request.form.get("diet_plan_type","standard"),
            "symptoms": request.form.getlist("symptoms"),
            "notes": request.form.get("notes",""),
        }
        session["pdf_data"] = data
        session["current_plan"] = generate_weekly_plan(data)
        return redirect("/preview")
    return render_template("generate.html", user=u, lang=session.get("lang","ar"), diet_plans=DIET_PLAN_TYPES)

@app.route("/preview")
@staff_required
def preview():
    u = get_user_by_id(session["uid"])
    data = session.get("pdf_data")
    plan = session.get("current_plan")
    if not data or not plan: return redirect("/generate")
    current_request_id = session.get("current_request_id")
    return render_template("preview.html", user=u, lang=session.get("lang","ar"),
                           data=data, plan=plan, current_request_id=current_request_id)

@app.route("/swap_meal", methods=["POST"])
@staff_required
def swap_meal():
    data = session.get("pdf_data")
    plan = session.get("current_plan")
    if not data or not plan: return jsonify({"ok": False}), 400
    day_idx = int(request.form.get("day_idx", 0))
    meal_type = request.form.get("meal_type", "breakfast")
    goal = data.get("goal_type", "weight_loss")
    culture = data.get("culture", "مصري")
    pool = get_meal_pool(goal, culture)
    pool_key = meal_type
    if meal_type in ["meal1", "meal2", "iftar", "suhoor", "snack1", "snack2", "pre_workout", "post_workout"]:
        if meal_type in ["meal1", "iftar"]: pool_key = "lunch"
        elif meal_type in ["meal2", "suhoor"]: pool_key = "dinner"
        elif meal_type in ["snack1", "snack2"]: pool_key = "breakfast"
        elif meal_type == "pre_workout": pool_key = "breakfast"
        elif meal_type == "post_workout": pool_key = "lunch"
    if pool_key in pool and pool[pool_key]:
        current = plan[day_idx].get(meal_type, "")
        options = [m for m in pool[pool_key] if m["meal"] != current]
        if options:
            new_meal = random.choice(options)
            plan[day_idx][meal_type] = new_meal["meal"]
            session["current_plan"] = plan
            return jsonify({"ok": True, "new_meal": new_meal["meal"]})
    return jsonify({"ok": False}), 400

# ═══════════════════════════════════════════════
# ✨ NEW: GET MEAL OPTIONS (for manual picking)
# ═══════════════════════════════════════════════
@app.route("/get_meal_options", methods=["POST"])
@staff_required
def get_meal_options():
    """Return all available meal options for manual selection"""
    data = session.get("pdf_data")
    if not data:
        return jsonify({"ok": False, "options": []}), 400

    meal_type = request.form.get("meal_type", "breakfast")
    goal = data.get("goal_type", "weight_loss")
    culture = data.get("culture", "مصري")
    pool = get_meal_pool(goal, culture)

    # Map diet types to pool keys
    pool_key = meal_type
    if meal_type in ["meal1", "meal2", "iftar", "suhoor", "snack1", "snack2", "pre_workout", "post_workout"]:
        if meal_type in ["meal1", "iftar"]: pool_key = "lunch"
        elif meal_type in ["meal2", "suhoor"]: pool_key = "dinner"
        elif meal_type in ["snack1", "snack2"]: pool_key = "breakfast"
        elif meal_type == "pre_workout": pool_key = "breakfast"
        elif meal_type == "post_workout": pool_key = "lunch"

    # Get all meals from the pool + also from other cuisines
    all_options = []

    # 1. Current cuisine
    if pool_key in pool and pool[pool_key]:
        for m in pool[pool_key]:
            all_options.append({
                "meal": m["meal"],
                "cal": m.get("cal", 0),
                "p": m.get("p", 0),
                "source": culture
            })

    # 2. Other cuisines (for variety)
    pools_map = {
        "weight_loss": WEIGHT_LOSS,
        "muscle_gain": MUSCLE_GAIN,
        "bulking": BULKING,
    }
    main_pool = pools_map.get(goal, WEIGHT_LOSS)

    for other_culture, other_pool in main_pool.items():
        if other_culture != culture and pool_key in other_pool:
            for m in other_pool[pool_key][:5]:  # only top 5 from each
                all_options.append({
                    "meal": m["meal"],
                    "cal": m.get("cal", 0),
                    "p": m.get("p", 0),
                    "source": other_culture
                })

    return jsonify({"ok": True, "options": all_options})

# ═══════════════════════════════════════════════
# ✨ NEW: REPLACE MEAL (manual selection)
# ═══════════════════════════════════════════════
@app.route("/replace_meal", methods=["POST"])
@staff_required
def replace_meal():
    """Replace a meal with a specific selected meal"""
    plan = session.get("current_plan")
    if not plan:
        return jsonify({"ok": False, "error": "no plan"}), 400

    try:
        day_idx = int(request.form.get("day_idx", 0))
        meal_type = request.form.get("meal_type", "")
        new_meal = request.form.get("new_meal", "").strip()

        if not new_meal or not meal_type:
            return jsonify({"ok": False, "error": "missing data"}), 400

        if day_idx < 0 or day_idx >= len(plan):
            return jsonify({"ok": False, "error": "invalid day"}), 400

        plan[day_idx][meal_type] = new_meal
        session["current_plan"] = plan

        return jsonify({"ok": True, "new_meal": new_meal})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/edit_meal", methods=["POST"])
@staff_required
def edit_meal():
    plan = session.get("current_plan")
    if not plan:
        return jsonify({"ok": False, "error": "no plan"}), 400
    try:
        day_idx = int(request.form.get("day_idx", 0))
        meal_type = request.form.get("meal_type", "")
        new_text = request.form.get("new_text", "").strip()
        if not new_text or not meal_type:
            return jsonify({"ok": False, "error": "missing data"}), 400
        if day_idx < 0 or day_idx >= len(plan):
            return jsonify({"ok": False, "error": "invalid day"}), 400
        plan[day_idx][meal_type] = new_text
        session["current_plan"] = plan
        return jsonify({"ok": True, "saved_text": new_text})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

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
            latest = db_row("""SELECT * FROM plan_requests WHERE client_id=? AND status='approved'
                               ORDER BY updated_at DESC LIMIT 1""", (session["uid"],))
            if latest and latest.get("plan_data"):
                pd = json.loads(latest["plan_data"])
                data = pd.get("data")
                plan = pd.get("plan")
        except:
            pass
    if not data: return redirect("/dashboard")
    try:
        pdf_bytes = build_pdf(data, plan)
        buf = io.BytesIO(pdf_bytes); buf.seek(0)
        name = data.get("name","plan").replace(" ","_")
        return send_file(buf, as_attachment=True, download_name=f"NutraX_{name}.pdf", mimetype="application/pdf")
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"خطأ: {str(e)}", 500

def _has(symptoms, keywords):
    for s in symptoms:
        s_low = str(s).lower().strip()
        for k in keywords:
            if k.lower() in s_low: return True
    return False

def generate_weekly_plan(data):
    symptoms = data.get("symptoms", [])
    goal = data.get("goal_type", "weight_loss")
    culture = data.get("culture", "مصري")
    diet_type = data.get("diet_plan_type", "standard")
    pool = get_meal_pool(goal, culture)
    breakfasts = list(pool.get("breakfast", []))
    lunches = list(pool.get("lunch", []))
    dinners = list(pool.get("dinner", []))
    if len(breakfasts) < 7: breakfasts = list(WEIGHT_LOSS["مصري"]["breakfast"])
    if len(lunches) < 7: lunches = list(WEIGHT_LOSS["مصري"]["lunch"])
    if len(dinners) < 7: dinners = list(WEIGHT_LOSS["مصري"]["dinner"])
    breakfasts = filter_by_conditions(breakfasts, symptoms)
    lunches = filter_by_conditions(lunches, symptoms)
    dinners = filter_by_conditions(dinners, symptoms)
    snacks = get_snacks_for_goal(goal)
    pool_snacks = pool.get("snack", [])
    if pool_snacks: snacks = pool_snacks[:10]
    while len(snacks) < 7: snacks.append("فاكهة + مكسرات (120 kcal)")
    days = ["الاحد","الاثنين","الثلاثاء","الاربعاء","الخميس","الجمعة","السبت"]
    plan_info = get_diet_plan_info(diet_type)
    random.shuffle(breakfasts)
    random.shuffle(lunches)
    random.shuffle(dinners)
    plan = []
    for i in range(7):
        day_plan = {"day": days[i], "diet_type": diet_type,
                    "meal_labels": plan_info["meal_labels"], "meal_emojis": plan_info["meal_emojis"]}
        total_cal = 0
        if diet_type == "standard":
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["breakfast"] = b["meal"]
            day_plan["lunch"] = l["meal"]
            day_plan["dinner"] = d["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            total_cal = b.get("cal",300) + l.get("cal",400) + d.get("cal",300) + 150
        elif diet_type == "five_meals":
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["breakfast"] = b["meal"]
            day_plan["snack1"] = snacks[i % len(snacks)]
            day_plan["lunch"] = l["meal"]
            day_plan["snack2"] = snacks[(i+3) % len(snacks)]
            day_plan["dinner"] = d["meal"]
            total_cal = b.get("cal",300) + l.get("cal",400) + d.get("cal",300) + 300
        elif diet_type == "intermittent_16_8":
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["meal1"] = l["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            day_plan["meal2"] = d["meal"]
            total_cal = l.get("cal",400) + d.get("cal",400) + 150
        elif diet_type == "intermittent_18_6":
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["meal1"] = l["meal"]
            day_plan["meal2"] = d["meal"]
            total_cal = l.get("cal",400) + d.get("cal",400)
        elif diet_type == "ramadan":
            l = lunches[i % len(lunches)]
            b = breakfasts[i % len(breakfasts)]
            day_plan["iftar"] = l["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            day_plan["suhoor"] = b["meal"]
            total_cal = l.get("cal",400) + b.get("cal",300) + 150
        elif diet_type == "workout":
            b = breakfasts[i % len(breakfasts)]
            l = lunches[i % len(lunches)]
            d = dinners[i % len(dinners)]
            day_plan["pre_workout"] = "موزة + زبدة فول سوداني + قهوة"
            day_plan["breakfast"] = b["meal"]
            day_plan["post_workout"] = "بروتين شيك + موز + لوز"
            day_plan["lunch"] = l["meal"]
            day_plan["dinner"] = d["meal"]
            total_cal = 200 + b.get("cal",300) + 250 + l.get("cal",400) + d.get("cal",300)
        day_plan["total_cal"] = total_cal
        plan.append(day_plan)
    return plan

def get_allowed_forbidden(symptoms, goal="weight_loss"):
    has_g6pd = _has(symptoms, ["g6pd","g6bd","فافيزم"])
    has_thal = _has(symptoms, ["ثلاسيميا","thalassemia"])
    has_colon = _has(symptoms, ["قولون عصبي","ibs"])
    needs_d3 = _has(symptoms, ["نقص فيتامين d","نقص d3"])
    needs_fe = _has(symptoms, ["نقص الحديد","فقر دم"])
    if goal in ["muscle_gain","bulking"]:
        allowed = ["مصادر بروتين عالية: دجاج + لحم + سمك + بيض","كاربوهيدرات معقدة: ارز بني + شوفان + بطاطا",
                   "مكسرات + افوكادو + زيت زيتون","حليب كامل + زبادي يوناني","بروتين شيك بعد التمرين"]
        forbidden = ["الأكل المقلي الزائد","السكريات المضافة","المشروبات الغازية","الوجبات السريعة"]
    else:
        allowed = ["دجاج مشوي أو فرن + بيض","شوفان + خبز أسمر + أرز بني",
                   "زبادي يوناني سادة + جبن قريش","ملوخية + كوسة + خضار مطبوخة",
                   "زيت زيتون (ملعقة) + فاكهة طازجة","شاي أخضر + ماء بالليمون"]
        forbidden = ["الخبز الأبيض","الأكل المقلي + السمن","المشروبات الغازية","الحلويات والسكريات"]
    if has_g6pd:
        forbidden = ["❗ الفول بكل أنواعه","❗ الحمص والبقوليات الحمراء"] + forbidden
        allowed = ["عدس أصفر بكميات محدودة"] + allowed
    else:
        if goal in ["weight_loss","maintenance"]:
            allowed = ["فول مدمس + عدس + شوربات + سمك مشوي"] + allowed
    if has_thal:
        forbidden = ["❗ الكبدة والأعضاء الداخلية","❗ اللحوم الحمراء بإفراط"] + forbidden
        allowed = ["شاي مع الوجبات"] + allowed
    if has_colon:
        forbidden.append("التوابل الحارة")
        forbidden.append("الكافيين الزائد")
    if needs_d3:
        allowed = ["⭐ أسماك دهنية: سلمون","⭐ صفار البيض + الفطر","⭐ تعرض للشمس 15 دقيقة"] + allowed
    if needs_fe and not has_thal:
        allowed = ["⭐ لحوم حمراء + كبدة","⭐ سبانخ + عدس"] + allowed
    return allowed[:8], forbidden[:8]

def build_pdf(data, plan=None):
    from weasyprint import HTML
    import datetime as dt
    if plan is None: plan = generate_weekly_plan(data)
    symptoms = data.get("symptoms", [])
    goal = data.get("goal_type", "weight_loss")
    diet_type = data.get("diet_plan_type", "standard")
    plan_info = get_diet_plan_info(diet_type)
    allowed, forbidden = get_allowed_forbidden(symptoms, goal)
    try:
        tdee = float(data.get("tdee", 0) or 0)
        target = float(data.get("goal_cal", 0) or 0)
        deficit = int(tdee - target) if tdee and target else 0
    except: deficit = 0
    notes_parts = []
    if symptoms: notes_parts.append(" • ".join(symptoms))
    if data.get("notes"): notes_parts.append(data.get("notes"))
    clinical_notes = " | ".join(notes_parts) if notes_parts else "لا توجد ملاحظات"
    uid = session.get("uid", 0)
    file_num = f"NX-{dt.datetime.now().year}-{uid:03d}"
    goal_labels = {"weight_loss":"خطة تخسيس","muscle_gain":"خطة زيادة عضل","bulking":"خطة تضخيم","maintenance":"خطة مكتنز"}
    plan_title = goal_labels.get(goal, "خطة غذائية")
    pdf_days = []
    for d in plan:
        meals_html = []
        for meal_key in plan_info["meals"]:
            label = plan_info["meal_labels"].get(meal_key, meal_key)
            emoji = plan_info["meal_emojis"].get(meal_key, "•")
            meal_text = d.get(meal_key, "")
            if meal_text:
                meals_html.append({"label": label, "emoji": emoji, "text": meal_text})
        pdf_days.append({"name": d["day"], "total_kcal": d["total_cal"], "meals": meals_html,
                         "breakfast": d.get("breakfast",""), "lunch": d.get("lunch",""),
                         "dinner": d.get("dinner",""), "snack": d.get("snack","")})
    template_data = {
        'file_number': file_num, 'date': dt.date.today().strftime('%d/%m/%Y'),
        'plan_title': plan_title, 'diet_plan_name': plan_info["name"],
        'culture': data.get("culture","مصري"),
        'client': {'name': data.get('name','—'), 'age': data.get('age','—'),
            'gender': data.get('gender','—'), 'height': data.get('height','—'),
            'weight': data.get('weight','—'), 'bmi': data.get('bmi','—'),
            'body_fat': data.get('fat_pct','—'), 'tdee': data.get('tdee','—'),
            'target_kcal': data.get('goal_cal','—'), 'deficit': deficit},
        'conditions': symptoms if symptoms else ["لا توجد حالات مسجلة"],
        'clinical_notes': clinical_notes,
        'allowed': allowed, 'forbidden': forbidden, 'days': pdf_days,
        'tips': {
            'water': ['كوب ماء دافئ + نصف ليمونة فور الاستيقاظ','8 أكواب ماء يومياً',
                      'كوب ماء قبل كل وجبة بـ 30 دقيقة','تجنب الماء البارد جداً'],
            'habits': ['مضغ بطيء — الشبع بعد 20 دقيقة','لا تأكل أمام الشاشة',
                       'نوم 7-8 ساعات','تعرض للشمس يومياً'],
            'metabolism': (['بروتين في كل وجبة','توابل آمنة: كركم + قرفة + زنجبيل',
                            'مشي 30 دقيقة بعد الغداء','قم وتحرك 5 دقائق كل ساعة']
                           if goal in ["weight_loss","maintenance"] else
                           ['بروتين في كل وجبة (1.6-2.2 جم/كجم)','كارب حول التمرين',
                            'تدريب مقاومة 4-5 مرات أسبوعياً','نوم 7-9 ساعات']),
            'warnings': ['لا تخفض السعرات أكثر من المحدد','لو جعت: ماء أولاً ثم فاكهة',
                         'راجع مع أخصائي التغذية كل 4 أسابيع','أي أعراض غير عادية — راجع طبيبك'],
        },
        'clinic_name': 'NutraX Clinical Nutrition',
        'author': 'إعداد د. محمد — أخصائي التغذية الإكلينيكية',
        'review_weeks': 4,
    }
    html_string = render_template('meal_plan.html', **template_data)
    pdf_bytes = HTML(string=html_string).write_pdf()
    return pdf_bytes

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
        db_run("""INSERT INTO patients (user_id,name,age,gender,height,weight,fat_pct,bmi,tdee,goal_cal,conditions,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
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

if __name__ == "__main__":
    app.run(debug=True)

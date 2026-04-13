from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3, hashlib, os, json
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nutrax2025")
app.permanent_session_lifetime = timedelta(days=30)

DB = "/tmp/nutrax.db"

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hp(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, country TEXT, lang TEXT DEFAULT 'ar', height REAL, weight REAL, age INTEGER, gender TEXT DEFAULT 'male', goal TEXT DEFAULT 'maintain', activity REAL DEFAULT 1.55, is_admin INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS weight_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS saved_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, plan_data TEXT, plan_type TEXT DEFAULT 'personal', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("SELECT id FROM users WHERE is_admin=1")
    if not c.fetchone():
        c.execute("INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,1)", ("Admin","admin@nutrax.com",hp("nutrax2025")))
    conn.commit()
    conn.close()

init_db()

def get_user(email, password):
    conn = get_conn()
    u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hp(password))).fetchone()
    conn.close()
    return u

def get_user_by_id(uid):
    conn = get_conn()
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return u

def register_user(name, email, password, country):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO users (name,email,password,country) VALUES (?,?,?,?)", (name,email,hp(password),country))
        conn.commit()
        return "ok"
    except:
        return "exists"
    finally:
        conn.close()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/", methods=["GET","POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    tab = "login"
    if request.method == "POST":
        action = request.form.get("action")
        if action == "login":
            u = get_user(request.form.get("email","").lower(), request.form.get("password",""))
            if u:
                session.permanent = True
                session["user_id"] = u["id"]
                session["lang"] = u["lang"] or "ar"
                return redirect(url_for("dashboard"))
            else:
                error = "البريد أو كلمة المرور غير صحيحة"
        elif action == "register":
            tab = "register"
            r = register_user(request.form.get("name",""), request.form.get("reg_email","").lower(), request.form.get("reg_password",""), request.form.get("country",""))
            if r == "ok":
                error = "✅ تم التسجيل! سجل دخولك."
                tab = "login"
            else:
                error = "البريد مستخدم بالفعل"
    return render_template("login.html", error=error, tab=tab)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=get_user_by_id(session["user_id"]), lang=session.get("lang","ar"))

@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    user = get_user_by_id(session["user_id"])
    saved = False
    if request.method == "POST":
        conn = get_conn()
        conn.execute("UPDATE users SET height=?,weight=?,age=?,gender=?,goal=?,activity=? WHERE id=?",
            (request.form.get("height"), request.form.get("weight"), request.form.get("age"),
             request.form.get("gender"), request.form.get("goal"), request.form.get("activity"), session["user_id"]))
        conn.commit()
        conn.close()
        user = get_user_by_id(session["user_id"])
        saved = True
    return render_template("settings.html", user=user, lang=session.get("lang","ar"), saved=saved)

@app.route("/analyzer")
@login_required
def analyzer():
    return render_template("analyzer.html", user=get_user_by_id(session["user_id"]), lang=session.get("lang","ar"))

@app.route("/planner")
@login_required
def planner():
    return render_template("planner.html", user=get_user_by_id(session["user_id"]), lang=session.get("lang","ar"))

@app.route("/clinical")
@login_required
def clinical():
    return render_template("clinical.html", user=get_user_by_id(session["user_id"]), lang=session.get("lang","ar"))

@app.route("/history")
@login_required
def history():
    user = get_user_by_id(session["user_id"])
    conn = get_conn()
    logs = conn.execute("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at ASC", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("history.html", user=user, lang=session.get("lang","ar"), logs=logs)

@app.route("/saved")
@login_required
def saved():
    user = get_user_by_id(session["user_id"])
    conn = get_conn()
    plans = conn.execute("SELECT * FROM saved_plans WHERE user_id=? ORDER BY created_at DESC", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("saved.html", user=user, lang=session.get("lang","ar"), plans=plans)

@app.route("/log_weight", methods=["POST"])
@login_required
def log_weight():
    weight = request.form.get("weight")
    if weight:
        conn = get_conn()
        conn.execute("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)", (session["user_id"], weight))
        conn.commit()
        conn.close()
    return redirect(url_for("history"))

@app.route("/save_plan", methods=["POST"])
@login_required
def save_plan():
    plan_name = request.form.get("plan_name", "خطتي")
    plan_type = request.form.get("plan_type", "personal")
    plan_data = json.dumps(dict(request.form))
    conn = get_conn()
    conn.execute("INSERT INTO saved_plans (user_id, name, plan_data, plan_type) VALUES (?, ?, ?, ?)",
                 (session["user_id"], plan_name, plan_data, plan_type))
    conn.commit()
    conn.close()
    return redirect(url_for("saved"))

@app.route("/delete_plan/<int:plan_id>", methods=["POST"])
@login_required
def delete_plan(plan_id):
    conn = get_conn()
    conn.execute("DELETE FROM saved_plans WHERE id=? AND user_id=?", (plan_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("saved"))

@app.route("/api/lang/<lang>")
@login_required
def set_lang(lang):
    if lang in ["ar","en"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)

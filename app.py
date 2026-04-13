from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import os
from utils.database import init_db, get_user, register_user, update_user_profile, get_user_by_id
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nutrax-secret-2025-change-this")
app.permanent_session_lifetime = timedelta(days=30)

# ══════════════════════════════════════════════════════════════
# Init DB on startup
# ══════════════════════════════════════════════════════════════
with app.app_context():
    init_db()

# ══════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    error = None
    tab = "login"

    if request.method == "POST":
        action = request.form.get("action")

        if action == "login":
            email    = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "").strip()
            remember = request.form.get("remember") == "on"
            user = get_user(email, password)
            if user:
                session.permanent = remember
                session["user_id"] = user["id"]
                session["lang"]    = user["lang"] or "ar"
                return redirect(url_for("dashboard"))
            else:
                error = "البريد أو كلمة المرور غير صحيحة" if True else "Wrong email or password"
                tab = "login"

        elif action == "register":
            tab = "register"
            name     = request.form.get("name", "").strip()
            email    = request.form.get("reg_email", "").strip().lower()
            password = request.form.get("reg_password", "").strip()
            country  = request.form.get("country", "")
            result   = register_user(name, email, password, country)
            if result == "ok":
                error = "✅ تم التسجيل! سجل دخولك الآن."
                tab = "login"
            elif result == "exists":
                error = "البريد الإلكتروني مستخدم بالفعل"

    return render_template("login.html", error=error, tab=tab)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════════
# MAIN ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/dashboard")
@login_required
def dashboard():
    user = get_user_by_id(session["user_id"])
    return render_template("dashboard.html", user=user, lang=session.get("lang","ar"))

@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    user = get_user_by_id(session["user_id"])
    saved = False
    if request.method == "POST":
        data = {
            "height":   request.form.get("height"),
            "weight":   request.form.get("weight"),
            "age":      request.form.get("age"),
            "gender":   request.form.get("gender"),
            "goal":     request.form.get("goal"),
            "activity": request.form.get("activity"),
        }
        update_user_profile(session["user_id"], data)
        user = get_user_by_id(session["user_id"])
        saved = True
    return render_template("settings.html", user=user, lang=session.get("lang","ar"), saved=saved)

@app.route("/analyzer")
@login_required
def analyzer():
    user = get_user_by_id(session["user_id"])
    return render_template("analyzer.html", user=user, lang=session.get("lang","ar"))

@app.route("/planner")
@login_required
def planner():
    user = get_user_by_id(session["user_id"])
    return render_template("planner.html", user=user, lang=session.get("lang","ar"))

@app.route("/clinical")
@login_required
def clinical():
    user = get_user_by_id(session["user_id"])
    return render_template("clinical.html", user=user, lang=session.get("lang","ar"))

@app.route("/history")
@login_required
def history():
    user = get_user_by_id(session["user_id"])
    return render_template("history.html", user=user, lang=session.get("lang","ar"))

@app.route("/saved")
@login_required
def saved():
    user = get_user_by_id(session["user_id"])
    return render_template("saved.html", user=user, lang=session.get("lang","ar"))

# ══════════════════════════════════════════════════════════════
# API — Language toggle
# ══════════════════════════════════════════════════════════════
@app.route("/api/lang/<lang>")
@login_required
def set_lang(lang):
    if lang in ["ar","en"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("dashboard"))

# ══════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=True, port=5000)

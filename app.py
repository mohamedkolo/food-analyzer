from flask import Flask, render_template, request, redirect, session, send_file
import hashlib, os, json, io
from datetime import timedelta

app = Flask(__name__)
from pdf_generator import pdf_bp
app.register_blueprint(pdf_bp)
app.secret_key = os.environ.get("SECRET_KEY", "nutrax2025")
app.permanent_session_lifetime = timedelta(days=30)

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import psycopg2, psycopg2.extras
    def get_db():
        return psycopg2.connect(DATABASE_URL)
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
        try: cur.execute(sql, params);
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

def init_db():
    if DATABASE_URL:
        db_run("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, country TEXT, lang TEXT DEFAULT 'ar', height REAL, weight REAL, age INTEGER, gender TEXT DEFAULT 'male', goal TEXT DEFAULT 'maintain', activity REAL DEFAULT 1.55, is_admin INTEGER DEFAULT 0)""")
        db_run("""CREATE TABLE IF NOT EXISTS weight_log (id SERIAL PRIMARY KEY, user_id INTEGER, weight REAL, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS saved_plans (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, plan_data TEXT, plan_type TEXT DEFAULT 'personal', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS patients (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, age INTEGER, gender TEXT, height REAL, weight REAL, fat_pct REAL, bmi REAL, tdee INTEGER, goal_cal INTEGER, conditions TEXT, notes TEXT, status TEXT DEFAULT 'draft', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    else:
        db_run("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, country TEXT, lang TEXT DEFAULT 'ar', height REAL, weight REAL, age INTEGER, gender TEXT DEFAULT 'male', goal TEXT DEFAULT 'maintain', activity REAL DEFAULT 1.55, is_admin INTEGER DEFAULT 0)""")
        db_run("""CREATE TABLE IF NOT EXISTS weight_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS saved_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, plan_data TEXT, plan_type TEXT DEFAULT 'personal', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        db_run("""CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, age INTEGER, gender TEXT, height REAL, weight REAL, fat_pct REAL, bmi REAL, tdee INTEGER, goal_cal INTEGER, conditions TEXT, notes TEXT, status TEXT DEFAULT 'draft', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    if not db_row("SELECT id FROM users WHERE is_admin=1"):
        db_run("INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,1)", ("Admin","admin@nutrax.com",hp("nutrax2025")))

init_db()

def get_user(email, pw): return db_row("SELECT * FROM users WHERE email=? AND password=?", (email, hp(pw)))
def get_user_by_id(uid): return db_row("SELECT * FROM users WHERE id=?", (uid,))
def register(name, email, pw, country):
    try: db_run("INSERT INTO users (name,email,password,country) VALUES (?,?,?,?)", (name,email,hp(pw),country)); return "ok"
    except: return "exists"

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════
@app.route("/", methods=["GET","POST"])
def login():
    if "uid" in session:
        return redirect("/dashboard")
    lang = session.get("lang", "ar")
    error = ""
    tab = request.args.get("tab", "login")
    if request.method == "POST":
        action = request.form.get("action")
        if action == "login":
            u = get_user(request.form.get("email","").lower(),
                         request.form.get("password",""))
            if u:
                session.permanent = True
                session["uid"] = u["id"]
                session["lang"] = u["lang"] or "ar"
                return redirect("/dashboard")
            error = "البريد او كلمة المرور غير صحيحة"
        elif action == "register":
            tab = "register"
            r = register(request.form.get("name",""),
                        request.form.get("reg_email","").lower(),
                        request.form.get("reg_password",""),
                        request.form.get("country",""))
            if r == "ok":
                error = "تم التسجيل! سجل دخولك."
                tab = "login"
            else:
                error = "البريد مستخدم بالفعل"
    return render_template("login.html", error=error, tab=tab, lang=lang)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/lang/<l>")
def set_lang(l):
    if l in ["ar","en"]:
        session["lang"] = l
    return redirect(request.referrer or "/dashboard")

# ══════════════════════════════════════════════
# MAIN PAGES
# ══════════════════════════════════════════════
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html",
                           user=get_user_by_id(session["uid"]),
                           lang=session.get("lang","ar"))

@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    u = get_user_by_id(session["uid"])
    saved = False
    if request.method == "POST":
        db_run("UPDATE users SET height=?, weight=?, age=?, gender=?, goal=?, activity=? WHERE id=?",
            (request.form.get("height"), request.form.get("weight"),
             request.form.get("age"), request.form.get("gender"),
             request.form.get("goal"), request.form.get("activity"),
             session["uid"]))
        u = get_user_by_id(session["uid"])
        saved = True
    return render_template("settings.html", user=u,
                           lang=session.get("lang","ar"), saved=saved)

@app.route("/analyzer")
@login_required
def analyzer():
    return render_template("analyzer.html",
                           user=get_user_by_id(session["uid"]),
                           lang=session.get("lang","ar"))

@app.route("/planner")
@login_required
def planner():
    return render_template("planner.html",
                           user=get_user_by_id(session["uid"]),
                           lang=session.get("lang","ar"))

@app.route("/clinical")
@login_required
def clinical():
    return render_template("clinical.html",
                           user=get_user_by_id(session["uid"]),
                           lang=session.get("lang","ar"))

@app.route("/history")
@login_required
def history():
    u = get_user_by_id(session["uid"])
    logs = db_rows("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at DESC LIMIT 30", (session["uid"],))
    return render_template("history.html", user=u,
                           lang=session.get("lang","ar"), logs=logs)

@app.route("/saved")
@login_required
def saved():
    u = get_user_by_id(session["uid"])
    plans = db_rows("SELECT * FROM saved_plans WHERE user_id=? ORDER BY created_at DESC", (session["uid"],))
    return render_template("saved.html", user=u,
                           lang=session.get("lang","ar"), plans=plans)

@app.route("/log_weight", methods=["POST"])
@login_required
def log_weight():
    w = request.form.get("weight")
    if w:
        db_run("INSERT INTO weight_log (user_id,weight) VALUES (?,?)", (session["uid"], w))
    return redirect("/history")

@app.route("/save_plan", methods=["POST"])
@login_required
def save_plan():
    n = request.form.get("plan_name", "خطتي")
    pt = request.form.get("plan_type", "personal")
    db_run("INSERT INTO saved_plans (user_id,name,plan_data,plan_type) VALUES (?,?,?,?)",
           (session["uid"], n, json.dumps(dict(request.form)), pt))
    return redirect("/saved")

@app.route("/delete_plan/<int:pid>", methods=["POST"])
@login_required
def delete_plan(pid):
    db_run("DELETE FROM saved_plans WHERE id=? AND user_id=?", (pid, session["uid"]))
    return redirect("/saved")

# ══════════════════════════════════════════════
# PDF GENERATOR — مولد الجدول الغذائي
# ══════════════════════════════════════════════
@app.route("/generate", methods=["GET","POST"])
@login_required
def generate():
    u = get_user_by_id(session["uid"])
    if request.method == "POST":
        data = {
            "name":       request.form.get("name",""),
            "age":        request.form.get("age",""),
            "gender":     request.form.get("gender",""),
            "height":     request.form.get("height",""),
            "weight":     request.form.get("weight",""),
            "fat_pct":    request.form.get("fat_pct",""),
            "bmi":        request.form.get("bmi",""),
            "tdee":       request.form.get("tdee",""),
            "goal_cal":   request.form.get("goal_cal","1400"),
            "symptoms":   request.form.getlist("symptoms"),
            "notes":      request.form.get("notes",""),
        }
        session["pdf_data"] = data
        return redirect("/preview")
    return render_template("generate.html", user=u,
                           lang=session.get("lang","ar"))

@app.route("/preview")
@login_required
def preview():
    u = get_user_by_id(session["uid"])
    data = session.get("pdf_data")
    if not data:
        return redirect("/generate")
    plan = generate_weekly_plan(data)
    return render_template("preview.html", user=u,
                           lang=session.get("lang","ar"),
                           data=data, plan=plan)

@app.route("/download_pdf")
@login_required
def download_pdf():
    data = session.get("pdf_data")
    if not data:
        return redirect("/generate")
    try:
        pdf_bytes = build_pdf(data)
        buf = io.BytesIO(pdf_bytes)
        buf.seek(0)
        name = data.get("name","patient").replace(" ","_")
        return send_file(buf, as_attachment=True,
                        download_name=f"NutraX_{name}.pdf",
                        mimetype="application/pdf")
    except Exception as e:
        return f"خطأ في توليد الـ PDF: {str(e)}", 500

# ══════════════════════════════════════════════
# CLINICAL CONDITION HELPERS
# ══════════════════════════════════════════════
def _has(symptoms, keywords):
    """Check if any keyword matches any symptom (case-insensitive partial match)"""
    for s in symptoms:
        s_low = str(s).lower().strip()
        for k in keywords:
            if k.lower() in s_low:
                return True
    return False

def _filter_unsafe(meals, unsafe_keywords, alternatives):
    """Replace unsafe meals with safe alternatives"""
    result = []
    alt_idx = 0
    for meal in meals:
        txt = meal["meal"]
        unsafe = any(kw in txt for kw in unsafe_keywords)
        if unsafe and alternatives:
            result.append(alternatives[alt_idx % len(alternatives)])
            alt_idx += 1
        else:
            result.append(meal)
    return result

# ══════════════════════════════════════════════
# MEAL PLAN GENERATOR
# ══════════════════════════════════════════════
def generate_weekly_plan(data):
    symptoms = data.get("symptoms", [])

    has_colon    = _has(symptoms, ["قولون عصبي","ibs"])
    has_diabetes = _has(symptoms, ["سكري"])
    has_cardiac  = _has(symptoms, ["امراض القلب","ضغط الدم"])
    has_kidney   = _has(symptoms, ["الفشل الكلوي"])
    has_pregnant = _has(symptoms, ["الحمل"])
    has_g6pd     = _has(symptoms, ["g6pd","g6bd","فافيزم","انزيم G6"])
    has_thal     = _has(symptoms, ["ثلاسيميا","thalassemia"])
    needs_iron   = _has(symptoms, ["نقص الحديد","فقر دم","انيميا"])
    needs_d3     = _has(symptoms, ["نقص فيتامين d","نقص d3","فيتامين D"])

    # ─── FATHAR (Breakfast) pools ───
    breakfasts = [
        {"meal":"فول مدمس بزيت الزيتون + بيضتان مسلوقتان + خبز اسمر", "cal":446, "p":20},
        {"meal":"شوفان بالحليب + موزة + لوز", "cal":400, "p":12},
        {"meal":"بيض اومليت بالخضار + خبز اسمر", "cal":320, "p":18},
        {"meal":"فول مع طحينة وليمون + خبز اسمر", "cal":360, "p":14},
        {"meal":"شوفان بالموز والقرفة + لوز نيئ", "cal":430, "p":11},
        {"meal":"فول مدمس + بيضتان + طماطم وخيار", "cal":406, "p":21},
        {"meal":"شوفان بالكيوي والعسل", "cal":370, "p":10},
    ]

    # ⚠️ G6PD SAFETY: Replace all fava bean (فول) meals
    if has_g6pd:
        g6pd_safe = [
            {"meal":"بيض مسلوق + جبن قريش + خبز اسمر + طماطم", "cal":340, "p":22},
            {"meal":"زبادي يوناني + عسل + مكسرات + تفاح", "cal":350, "p":16},
            {"meal":"توست اسمر + افوكادو + بيضة مسلوقة", "cal":380, "p":18},
            {"meal":"شوفان بالحليب + موز + لوز + بذور شيا", "cal":410, "p":13},
        ]
        breakfasts = _filter_unsafe(breakfasts, ["فول","حمص"], g6pd_safe)

    # ─── GHADA (Lunch) pools ───
    lunches = [
        {"meal":"صدر دجاج مشوي + ارز بني + سلطة خضار", "cal":478, "p":49},
        {"meal":"سمك بلطي مشوي + بطاطا حلوة + كوسة مشوية", "cal":417, "p":42},
        {"meal":"فخذ دجاج فرن + برغل + سلطة فتوش", "cal":450, "p":38},
        {"meal":"كبدة دجاج مشوية + ارز بني + ملوخية", "cal":389, "p":33},
        {"meal":"سمكة بلطي كاملة + بطاطا مسلوقة + سلطة", "cal":436, "p":52},
        {"meal":"صدر دجاج فرن بالخضار + ارز بني", "cal":460, "p":52},
        {"meal":"سمك بلطي مشوي + برغل + سلطة فتوش", "cal":392, "p":44},
    ]

    # ⚠️ THALASSEMIA SAFETY: Replace liver (iron overload risk)
    if has_thal:
        thal_safe = [
            {"meal":"دجاج مشوي بالزعتر + ارز بني + ملوخية", "cal":440, "p":44},
            {"meal":"سمك سلمون مشوي + ارز + سلطة", "cal":450, "p":45},
            {"meal":"صدر ديك رومي + خضار مشوية + برغل", "cal":420, "p":46},
        ]
        lunches = _filter_unsafe(lunches, ["كبدة","كبد"], thal_safe)

    # 🌟 VITAMIN D3: Boost with fatty fish and eggs
    if needs_d3:
        d3_boost = [
            {"meal":"سلمون مشوي + ارز بني + بروكلي", "cal":460, "p":48},
            {"meal":"سردين بزيت الزيتون + خبز اسمر + سلطة", "cal":400, "p":35},
            {"meal":"سمك مكاريل مشوي + بطاطا مسلوقة", "cal":430, "p":40},
        ]
        lunches[1] = d3_boost[0]
        lunches[4] = d3_boost[1]

    # ─── ESHA (Dinner) pools — based on colon/diabetes ───
    if has_colon:
        dinners = [
            {"meal":"شوربة عدس احمر + خبز اسمر", "cal":250, "p":12},
            {"meal":"عدس مطهو بجزر وكرفس + خبز", "cal":270, "p":13},
            {"meal":"شوربة خضار + جبن قريش", "cal":199, "p":10},
            {"meal":"حمص بطحينة + خبز اسمر", "cal":320, "p":13},
            {"meal":"شوربة عدس + خبز اسمر", "cal":250, "p":12},
            {"meal":"عدس مطهو + جبن قريش", "cal":249, "p":16},
            {"meal":"شوربة خضار خفيفة + خبز", "cal":220, "p":8},
        ]
    elif has_diabetes:
        dinners = [
            {"meal":"صدر دجاج مشوي + خضار مشوية", "cal":280, "p":46},
            {"meal":"سمك مشوي + سلطة خضار", "cal":240, "p":40},
            {"meal":"عدس مطهو + خبز اسمر", "cal":270, "p":13},
            {"meal":"دجاج فرن + بروكلي مطهو", "cal":290, "p":48},
            {"meal":"تونة بالخضار + خبز اسمر", "cal":260, "p":28},
            {"meal":"شوربة عدس + سلطة", "cal":250, "p":12},
            {"meal":"بيض مسلوق + خضار نيئة", "cal":200, "p":15},
        ]
    else:
        dinners = [
            {"meal":"شوربة عدس احمر + خبز اسمر", "cal":250, "p":12},
            {"meal":"عدس مطهو بجزر وكرفس + خبز", "cal":270, "p":13},
            {"meal":"شوربة خضار + جبن قريش", "cal":199, "p":10},
            {"meal":"حمص بطحينة + خبز اسمر + طماطم", "cal":320, "p":13},
            {"meal":"شوربة عدس اصفر + خبز", "cal":250, "p":12},
            {"meal":"عدس مطهو + جبن قريش", "cal":249, "p":16},
            {"meal":"كشري مصري (كمية معتدلة)", "cal":280, "p":12},
        ]

    # G6PD safety on dinners too (remove لوبيا, فول, حمص)
    if has_g6pd:
        g6pd_dinner_safe = [
            {"meal":"شوربة خضار + جبن قريش + خبز اسمر", "cal":240, "p":12},
            {"meal":"صدر دجاج مشوي + سلطة خضراء", "cal":280, "p":38},
            {"meal":"بيض مسلوق + خضار مطبوخة", "cal":220, "p":16},
        ]
        dinners = _filter_unsafe(dinners, ["فول","حمص","لوبيا"], g6pd_dinner_safe)

    snacks = [
        "تفاحة بالقشر (80 kcal)",
        "لوز نيئ 20 جم (120 kcal)",
        "برتقالة (62 kcal)",
        "تمرتان (66 kcal)",
        "كيوي (61 kcal)",
        "رمانة نصف (53 kcal)",
        "موزة صغيرة (89 kcal)",
    ]
    before_sleep = [
        "زبادي يوناني سادة",
        "كمثرى",
        "حليب دافئ خالي الدسم",
        "زبادي يوناني",
        "تفاحة بالقشر",
        "زبادي يوناني",
        "موزة صغيرة",
    ]

    days = ["الاحد","الاثنين","الثلاثاء","الاربعاء","الخميس","الجمعة","السبت"]
    plan = []
    for i in range(7):
        b = breakfasts[i]
        l = lunches[i]
        d = dinners[i]
        total_cal = b["cal"] + l["cal"] + d["cal"] + 100
        total_p   = b["p"]   + l["p"]   + d["p"]
        plan.append({
            "day":         days[i],
            "breakfast":   b["meal"],
            "lunch":       l["meal"],
            "dinner":      d["meal"],
            "snack":       snacks[i],
            "before_sleep":before_sleep[i],
            "total_cal":   total_cal,
            "total_p":     total_p,
        })
    return plan

# ══════════════════════════════════════════════
# ALLOWED / FORBIDDEN FOODS BY CONDITION
# ══════════════════════════════════════════════
def get_allowed_forbidden(symptoms):
    has_g6pd  = _has(symptoms, ["g6pd","g6bd","فافيزم"])
    has_thal  = _has(symptoms, ["ثلاسيميا","thalassemia"])
    has_colon = _has(symptoms, ["قولون عصبي","ibs"])
    needs_d3  = _has(symptoms, ["نقص فيتامين d","نقص d3"])
    needs_fe  = _has(symptoms, ["نقص الحديد","فقر دم"])

    allowed = [
        "دجاج مشوي أو فرن (بدون جلد) + بيض",
        "شوفان + خبز أسمر + أرز بني + برغل",
        "زبادي يوناني سادة + جبن قريش",
        "ملوخية + كوسة + خضار مطبوخة",
        "زيت زيتون (ملعقة) + فاكهة طازجة",
        "شاي أخضر + ماء دافئ بالليمون صباحاً",
    ]

    forbidden = [
        "الخبز الأبيض والعيش الفينو",
        "الأكل المقلي + الدهانة + السمن",
        "المشروبات الغازية + العصائر المعلبة",
        "الحلويات والسكريات المضافة",
    ]

    # Adjust by condition
    if has_g6pd:
        forbidden = ["❗ الفول بكل أنواعه (مدمس/أخضر/ناشف)",
                     "❗ الحمص والبقوليات الحمراء",
                     "❗ الأطعمة المحتوية على نيتروفورانتوين"] + forbidden
        allowed = ["عدس أصفر بكميات محدودة (آمن نسبياً)"] + allowed
    else:
        allowed = ["فول مدمس + عدس + شوربات + سمك مشوي"] + allowed

    if has_thal:
        forbidden = ["❗ الكبدة والأعضاء الداخلية (حديد مرتفع)",
                     "❗ اللحوم الحمراء بإفراط",
                     "❗ مكملات الحديد بدون استشارة"] + forbidden
        allowed = ["شاي مع الوجبات (يقلل امتصاص الحديد)"] + allowed

    if has_colon:
        forbidden.append("التوابل الحارة (تستفز القولون)")
        forbidden.append("البقوليات بكميات كبيرة دفعة واحدة")
        forbidden.append("الكافيين الزائد (أكثر من كوب)")

    if needs_d3:
        allowed = ["⭐ أسماك دهنية: سلمون • سردين • تونة",
                   "⭐ صفار البيض + الفطر",
                   "⭐ تعرض للشمس 15 دقيقة يومياً"] + allowed

    if needs_fe and not has_thal:
        allowed = ["⭐ لحوم حمراء + كبدة (مع فيتامين C)",
                   "⭐ سبانخ + عدس + فاصوليا"] + allowed

    return allowed[:8], forbidden[:8]

# ══════════════════════════════════════════════
# PDF BUILDER — WeasyPrint + Beautiful Template
# ══════════════════════════════════════════════
def build_pdf(data):
    """
    Generate PDF using WeasyPrint + meal_plan.html template.
    Arabic renders perfectly in RTL — no reshaping needed.
    """
    from weasyprint import HTML
    import datetime

    plan = generate_weekly_plan(data)
    symptoms = data.get("symptoms", [])
    allowed, forbidden = get_allowed_forbidden(symptoms)

    # Calculate deficit safely
    try:
        tdee = float(data.get("tdee", 0) or 0)
        target = float(data.get("goal_cal", 0) or 0)
        deficit = int(tdee - target) if tdee and target else 0
    except:
        deficit = 0

    # Build clinical notes string from symptoms + notes
    notes_parts = []
    if symptoms:
        notes_parts.append(" • ".join(symptoms))
    if data.get("notes"):
        notes_parts.append(data.get("notes"))
    clinical_notes = " | ".join(notes_parts) if notes_parts else "لا توجد ملاحظات إضافية"

    # Prepare template data
    uid = session.get("uid", 0)
    file_num = f"NX-{datetime.datetime.now().year}-{uid:03d}"

    template_data = {
        'file_number': file_num,
        'date': datetime.date.today().strftime('%d/%m/%Y'),
        'client': {
            'name':        data.get('name', '—'),
            'age':         data.get('age', '—'),
            'gender':      data.get('gender', '—'),
            'height':      data.get('height', '—'),
            'weight':      data.get('weight', '—'),
            'bmi':         data.get('bmi', '—'),
            'body_fat':    data.get('fat_pct', '—'),
            'tdee':        data.get('tdee', '—'),
            'target_kcal': data.get('goal_cal', '—'),
            'deficit':     deficit,
        },
        'conditions':     symptoms if symptoms else ["لا توجد حالات مسجلة"],
        'clinical_notes': clinical_notes,
        'allowed':        allowed,
        'forbidden':      forbidden,
        'days': [
            {
                'name':       d['day'],
                'total_kcal': d['total_cal'],
                'breakfast':  d['breakfast'],
                'lunch':      d['lunch'],
                'dinner':     d['dinner'],
                'snack':      f"{d['snack']} | {d['before_sleep']}",
            } for d in plan
        ],
        'tips': {
            'water': [
                'كوب ماء دافئ + نصف ليمونة فور الاستيقاظ',
                '8 أكواب ماء يومياً (2 لتر على الأقل)',
                'كوب ماء قبل كل وجبة بـ 30 دقيقة',
                'تجنب الماء البارد جداً مع الأكل',
            ],
            'habits': [
                '3 وجبات رئيسية + سناك واحد',
                'مضغ بطيء — الشبع بعد 20 دقيقة',
                'لا تأكل أمام الشاشة — يزيد الكمية',
                'الفطار إجباري خلال ساعة من الاستيقاظ',
            ],
            'metabolism': [
                'بروتين في كل وجبة (بيض / دجاج / سمك / عدس)',
                'توابل آمنة: كركم + قرفة + زنجبيل',
                'مشي 30 دقيقة بعد الغداء',
                'قم وتحرك 5 دقائق كل ساعة',
            ],
            'warnings': [
                'لا تخفض السعرات أكثر من المحدد — يوقف الحرق',
                'لو جعت بين الوجبات: ماء أولاً ثم فاكهة',
                'راجع مع أخصائي التغذية كل 4 أسابيع',
                'أي أعراض غير عادية — راجع طبيبك فوراً',
            ],
        },
        'clinic_name':   'NutraX Clinical Nutrition',
        'author':        'إعداد د. محمد — أخصائي التغذية الإكلينيكية',
        'review_weeks':  4,
    }

    html_string = render_template('meal_plan.html', **template_data)
    pdf_bytes = HTML(string=html_string).write_pdf()
    return pdf_bytes

# ══════════════════════════════════════════════
# PATIENTS MANAGEMENT
# ══════════════════════════════════════════════
@app.route("/patients")
@login_required
def patients():
    u = get_user_by_id(session["uid"])
    search = request.args.get("q","")
    status_filter = request.args.get("status","")
    sql = "SELECT * FROM patients WHERE user_id=?"
    params = [session["uid"]]
    if search:
        sql += " AND name LIKE ?"
        params.append(f"%{search}%")
    if status_filter:
        sql += " AND status=?"
        params.append(status_filter)
    sql += " ORDER BY created_at DESC"
    try:
        pts = db_rows(sql, tuple(params))
    except:
        pts = []
    return render_template("patients.html", user=u,
                           lang=session.get("lang","ar"),
                           patients=pts, search=search, status=status_filter)

@app.route("/patients/new", methods=["GET","POST"])
@login_required
def new_patient():
    u = get_user_by_id(session["uid"])
    if request.method == "POST":
        name = request.form.get("name","")
        age = request.form.get("age",0)
        gender = request.form.get("gender","ذكر")
        height = request.form.get("height",0)
        weight = request.form.get("weight",0)
        fat_pct = request.form.get("fat_pct",0)
        bmi = request.form.get("bmi",0)
        tdee = request.form.get("tdee",0)
        goal_cal = request.form.get("goal_cal",1400)
        conditions = json.dumps(request.form.getlist("conditions"))
        notes = request.form.get("notes","")
        db_run("""INSERT INTO patients
            (user_id,name,age,gender,height,weight,fat_pct,bmi,tdee,goal_cal,conditions,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (session["uid"],name,age,gender,height,weight,fat_pct,bmi,tdee,goal_cal,conditions,notes))
        return redirect("/patients")
    return render_template("new_patient.html", user=u, lang=session.get("lang","ar"))

@app.route("/patients/<int:pid>")
@login_required
def view_patient(pid):
    u = get_user_by_id(session["uid"])
    pt = db_row("SELECT * FROM patients WHERE id=? AND user_id=?", (pid, session["uid"]))
    if not pt:
        return redirect("/patients")
    plans = db_rows("SELECT * FROM saved_plans WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (session["uid"],))
    return render_template("view_patient.html", user=u,
                           lang=session.get("lang","ar"),
                           patient=pt, plans=plans)

@app.route("/patients/<int:pid>/generate")
@login_required
def patient_generate(pid):
    pt = db_row("SELECT * FROM patients WHERE id=? AND user_id=?", (pid, session["uid"]))
    if not pt:
        return redirect("/patients")
    data = {
        "name": pt["name"], "age": pt["age"], "gender": pt["gender"],
        "height": pt["height"], "weight": pt["weight"],
        "fat_pct": pt["fat_pct"], "bmi": pt["bmi"],
        "tdee": pt["tdee"], "goal_cal": pt["goal_cal"],
        "symptoms": json.loads(pt["conditions"] or "[]"),
        "notes": pt["notes"] or "",
    }
    session["pdf_data"] = data
    return redirect("/preview")

@app.route("/patients/<int:pid>/status/<s>")
@login_required
def update_patient_status(pid, s):
    if s in ["draft","published"]:
        db_run("UPDATE patients SET status=? WHERE id=? AND user_id=?",
               (s, pid, session["uid"]))
    return redirect(f"/patients/{pid}")

@app.route("/patients/<int:pid>/delete", methods=["POST"])
@login_required
def delete_patient(pid):
    db_run("DELETE FROM patients WHERE id=? AND user_id=?", (pid, session["uid"]))
    return redirect("/patients")

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, session, send_file, jsonify
import hashlib, os, json, io, random
from datetime import timedelta

app = Flask(__name__)
from pdf_generator import pdf_bp
app.register_blueprint(pdf_bp)
app.secret_key = os.environ.get("SECRET_KEY", "nutrax2025")
app.permanent_session_lifetime = timedelta(days=30)

from meal_database import (
    get_meal_pool, get_snacks_for_goal,
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
        if "uid" not in session: return redirect("/")
        return f(*args, **kwargs)
    return decorated

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
                session.permanent = True
                session["uid"] = u["id"]
                session["lang"] = u["lang"] or "ar"
                return redirect("/dashboard")
            error = "البريد او كلمة المرور غير صحيحة"
        elif action == "register":
            tab = "register"
            r = register(request.form.get("name",""), request.form.get("reg_email","").lower(),
                        request.form.get("reg_password",""), request.form.get("country",""))
            if r == "ok":
                error = "تم التسجيل! سجل دخولك."
                tab = "login"
            else: error = "البريد مستخدم بالفعل"
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
    return render_template("dashboard.html", user=get_user_by_id(session["uid"]), lang=session.get("lang","ar"))

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
@login_required
def analyzer():
    return render_template("analyzer.html", user=get_user_by_id(session["uid"]), lang=session.get("lang","ar"))

@app.route("/planner")
@login_required
def planner():
    return render_template("planner.html", user=get_user_by_id(session["uid"]), lang=session.get("lang","ar"))

@app.route("/clinical")
@login_required
def clinical():
    return render_template("clinical.html", user=get_user_by_id(session["uid"]), lang=session.get("lang","ar"))

@app.route("/history")
@login_required
def history():
    u = get_user_by_id(session["uid"])
    logs = db_rows("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at DESC LIMIT 30", (session["uid"],))
    return render_template("history.html", user=u, lang=session.get("lang","ar"), logs=logs)

@app.route("/saved")
@login_required
def saved():
    u = get_user_by_id(session["uid"])
    plans = db_rows("SELECT * FROM saved_plans WHERE user_id=? ORDER BY created_at DESC", (session["uid"],))
    return render_template("saved.html", user=u, lang=session.get("lang","ar"), plans=plans)

@app.route("/log_weight", methods=["POST"])
@login_required
def log_weight():
    w = request.form.get("weight")
    if w: db_run("INSERT INTO weight_log (user_id,weight) VALUES (?,?)", (session["uid"], w))
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

@app.route("/generate", methods=["GET","POST"])
@login_required
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
            "symptoms": request.form.getlist("symptoms"),
            "notes": request.form.get("notes",""),
        }
        session["pdf_data"] = data
        session["current_plan"] = generate_weekly_plan(data)
        return redirect("/preview")
    return render_template("generate.html", user=u, lang=session.get("lang","ar"))

@app.route("/preview")
@login_required
def preview():
    u = get_user_by_id(session["uid"])
    data = session.get("pdf_data")
    plan = session.get("current_plan")
    if not data or not plan: return redirect("/generate")
    return render_template("preview.html", user=u, lang=session.get("lang","ar"), data=data, plan=plan)

@app.route("/swap_meal", methods=["POST"])
@login_required
def swap_meal():
    data = session.get("pdf_data")
    plan = session.get("current_plan")
    if not data or not plan: return jsonify({"ok": False, "error": "no plan"}), 400
    day_idx = int(request.form.get("day_idx", 0))
    meal_type = request.form.get("meal_type", "breakfast")
    goal = data.get("goal_type", "weight_loss")
    culture = data.get("culture", "مصري")
    pool = get_meal_pool(goal, culture)
    if meal_type in pool and pool[meal_type]:
        current = plan[day_idx].get(meal_type, "")
        options = [m for m in pool[meal_type] if m["meal"] != current]
        if options:
            new_meal = random.choice(options)
            plan[day_idx][meal_type] = new_meal["meal"]
            total_cal = 0
            for mt in ["breakfast","lunch","dinner"]:
                meal_text = plan[day_idx].get(mt, "")
                for m in pool.get(mt, []):
                    if m["meal"] == meal_text:
                        total_cal += m.get("cal",0); break
            total_cal += 150
            plan[day_idx]["total_cal"] = total_cal
            session["current_plan"] = plan
            return jsonify({"ok": True, "new_meal": new_meal["meal"], "total_cal": total_cal})
    return jsonify({"ok": False, "error": "no alternatives"}), 400

@app.route("/regenerate_plan", methods=["POST"])
@login_required
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
    if not data: return redirect("/generate")
    try:
        pdf_bytes = build_pdf(data, plan)
        buf = io.BytesIO(pdf_bytes); buf.seek(0)
        name = data.get("name","patient").replace(" ","_")
        return send_file(buf, as_attachment=True, download_name=f"NutraX_{name}.pdf", mimetype="application/pdf")
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"خطأ في توليد الـ PDF: {str(e)}", 500

def _has(symptoms, keywords):
    for s in symptoms:
        s_low = str(s).lower().strip()
        for k in keywords:
            if k.lower() in s_low: return True
    return False

def _filter_unsafe(meals, unsafe_keywords, alternatives):
    result = []; alt_idx = 0
    for meal in meals:
        txt = meal["meal"]
        unsafe = any(kw in txt for kw in unsafe_keywords)
        if unsafe and alternatives:
            result.append(alternatives[alt_idx % len(alternatives)])
            alt_idx += 1
        else: result.append(meal)
    return result

def generate_weekly_plan(data):
    symptoms = data.get("symptoms", [])
    goal = data.get("goal_type", "weight_loss")
    culture = data.get("culture", "مصري")
    has_g6pd = _has(symptoms, ["g6pd","g6bd","فافيزم"])
    has_thal = _has(symptoms, ["ثلاسيميا","thalassemia"])
    needs_d3 = _has(symptoms, ["نقص فيتامين d","نقص d3"])
    pool = get_meal_pool(goal, culture)
    breakfasts = list(pool.get("breakfast", []))
    lunches = list(pool.get("lunch", []))
    dinners = list(pool.get("dinner", []))
    if len(breakfasts) < 7: breakfasts = list(WEIGHT_LOSS["مصري"]["breakfast"])
    if len(lunches) < 7: lunches = list(WEIGHT_LOSS["مصري"]["lunch"])
    if len(dinners) < 7: dinners = list(WEIGHT_LOSS["مصري"]["dinner"])
    if has_g6pd:
        g6pd_safe = [
            {"meal":"بيض مسلوق + جبن قريش + خبز اسمر + طماطم","cal":340,"p":22},
            {"meal":"زبادي يوناني + عسل + مكسرات + تفاح","cal":350,"p":16},
            {"meal":"توست اسمر + افوكادو + بيضة مسلوقة","cal":380,"p":18},
            {"meal":"شوفان بالحليب + موز + لوز + بذور شيا","cal":410,"p":13},
        ]
        breakfasts = _filter_unsafe(breakfasts, ["فول","حمص"], g6pd_safe)
        dinners = _filter_unsafe(dinners, ["فول","حمص","لوبيا"], g6pd_safe)
    if has_thal:
        thal_safe = [
            {"meal":"دجاج مشوي بالزعتر + ارز بني + ملوخية","cal":440,"p":44},
            {"meal":"سمك سلمون مشوي + ارز + سلطة","cal":450,"p":45},
            {"meal":"صدر ديك رومي + خضار مشوية + برغل","cal":420,"p":46},
        ]
        lunches = _filter_unsafe(lunches, ["كبدة","كبد"], thal_safe)
    if needs_d3:
        d3_boost = [
            {"meal":"سلمون مشوي + ارز بني + بروكلي","cal":460,"p":48},
            {"meal":"سردين بزيت الزيتون + خبز اسمر + سلطة","cal":400,"p":35},
        ]
        if len(lunches) >= 2: lunches[1] = d3_boost[0]
        if len(lunches) >= 5: lunches[4] = d3_boost[1]
    snacks = get_snacks_for_goal(goal)
    pool_snacks = pool.get("snack", [])
    if pool_snacks: snacks = pool_snacks[:7]
    while len(snacks) < 7: snacks.append("فاكهة + مكسرات (120 kcal)")
    before_sleep = ["زبادي يوناني سادة","كمثرى","حليب دافئ","زبادي يوناني","تفاحة","زبادي","موزة"]
    days = ["الاحد","الاثنين","الثلاثاء","الاربعاء","الخميس","الجمعة","السبت"]
    plan = []
    for i in range(7):
        b = breakfasts[i % len(breakfasts)]
        l = lunches[i % len(lunches)]
        d = dinners[i % len(dinners)]
        total_cal = b.get("cal",300) + l.get("cal",400) + d.get("cal",300) + 150
        total_p = b.get("p",15) + l.get("p",30) + d.get("p",15)
        plan.append({
            "day": days[i], "breakfast": b["meal"], "lunch": l["meal"], "dinner": d["meal"],
            "snack": snacks[i] if i < len(snacks) else snacks[0],
            "before_sleep": before_sleep[i], "total_cal": total_cal, "total_p": total_p,
        })
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
        forbidden = ["الأكل المقلي الزائد","السكريات المضافة والحلويات","المشروبات الغازية","الوجبات السريعة المصنعة"]
    else:
        allowed = ["دجاج مشوي أو فرن (بدون جلد) + بيض","شوفان + خبز أسمر + أرز بني + برغل",
                   "زبادي يوناني سادة + جبن قريش","ملوخية + كوسة + خضار مطبوخة",
                   "زيت زيتون (ملعقة) + فاكهة طازجة","شاي أخضر + ماء دافئ بالليمون"]
        forbidden = ["الخبز الأبيض والعيش الفينو","الأكل المقلي + الدهانة + السمن",
                     "المشروبات الغازية + العصائر المعلبة","الحلويات والسكريات المضافة"]
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
        allowed = ["⭐ أسماك دهنية: سلمون • سردين • تونة","⭐ صفار البيض + الفطر","⭐ تعرض للشمس 15 دقيقة"] + allowed
    if needs_fe and not has_thal:
        allowed = ["⭐ لحوم حمراء + كبدة","⭐ سبانخ + عدس + فاصوليا"] + allowed
    return allowed[:8], forbidden[:8]

def build_pdf(data, plan=None):
    from weasyprint import HTML
    import datetime
    if plan is None: plan = generate_weekly_plan(data)
    symptoms = data.get("symptoms", [])
    goal = data.get("goal_type", "weight_loss")
    allowed, forbidden = get_allowed_forbidden(symptoms, goal)
    try:
        tdee = float(data.get("tdee", 0) or 0)
        target = float(data.get("goal_cal", 0) or 0)
        deficit = int(tdee - target) if tdee and target else 0
    except: deficit = 0
    notes_parts = []
    if symptoms: notes_parts.append(" • ".join(symptoms))
    if data.get("notes"): notes_parts.append(data.get("notes"))
    clinical_notes = " | ".join(notes_parts) if notes_parts else "لا توجد ملاحظات إضافية"
    uid = session.get("uid", 0)
    file_num = f"NX-{datetime.datetime.now().year}-{uid:03d}"
    goal_labels = {"weight_loss":"خطة تخسيس","muscle_gain":"خطة زيادة عضل","bulking":"خطة تضخيم","maintenance":"خطة مكتنز"}
    plan_title = goal_labels.get(goal, "خطة غذائية")
    template_data = {
        'file_number': file_num,
        'date': datetime.date.today().strftime('%d/%m/%Y'),
        'plan_title': plan_title,
        'culture': data.get("culture","مصري"),
        'client': {
            'name': data.get('name','—'), 'age': data.get('age','—'),
            'gender': data.get('gender','—'), 'height': data.get('height','—'),
            'weight': data.get('weight','—'), 'bmi': data.get('bmi','—'),
            'body_fat': data.get('fat_pct','—'), 'tdee': data.get('tdee','—'),
            'target_kcal': data.get('goal_cal','—'), 'deficit': deficit,
        },
        'conditions': symptoms if symptoms else ["لا توجد حالات مسجلة"],
        'clinical_notes': clinical_notes,
        'allowed': allowed, 'forbidden': forbidden,
        'days': [{'name':d['day'],'total_kcal':d['total_cal'],'breakfast':d['breakfast'],
                  'lunch':d['lunch'],'dinner':d['dinner'],
                  'snack':f"{d['snack']} | {d['before_sleep']}"} for d in plan],
        'tips': {
            'water': ['كوب ماء دافئ + نصف ليمونة فور الاستيقاظ','8 أكواب ماء يومياً',
                      'كوب ماء قبل كل وجبة بـ 30 دقيقة','تجنب الماء البارد جداً'],
            'habits': ['3 وجبات رئيسية + سناك','مضغ بطيء — الشبع بعد 20 دقيقة',
                       'لا تأكل أمام الشاشة','الفطار إجباري خلال ساعة من الاستيقاظ'],
            'metabolism': (['بروتين في كل وجبة','توابل آمنة: كركم + قرفة + زنجبيل',
                            'مشي 30 دقيقة بعد الغداء','قم وتحرك 5 دقائق كل ساعة']
                           if goal in ["weight_loss","maintenance"] else
                           ['بروتين في كل وجبة (1.6-2.2 جم/كجم)','كارب حول التمرين',
                            'تدريب مقاومة 4-5 مرات أسبوعياً','نوم 7-9 ساعات لبناء العضل']),
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
@login_required
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
        db_run("""INSERT INTO patients (user_id,name,age,gender,height,weight,fat_pct,bmi,tdee,goal_cal,conditions,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (session["uid"],name,age,gender,height,weight,fat_pct,bmi,tdee,goal_cal,conditions,notes))
        return redirect("/patients")
    return render_template("new_patient.html", user=u, lang=session.get("lang","ar"))

@app.route("/patients/<int:pid>")
@login_required
def view_patient(pid):
    u = get_user_by_id(session["uid"])
    pt = db_row("SELECT * FROM patients WHERE id=? AND user_id=?", (pid, session["uid"]))
    if not pt: return redirect("/patients")
    plans = db_rows("SELECT * FROM saved_plans WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (session["uid"],))
    return render_template("view_patient.html", user=u, lang=session.get("lang","ar"), patient=pt, plans=plans)

@app.route("/patients/<int:pid>/generate")
@login_required
def patient_generate(pid):
    pt = db_row("SELECT * FROM patients WHERE id=? AND user_id=?", (pid, session["uid"]))
    if not pt: return redirect("/patients")
    data = {
        "name": pt["name"], "age": pt["age"], "gender": pt["gender"],
        "height": pt["height"], "weight": pt["weight"], "fat_pct": pt["fat_pct"],
        "bmi": pt["bmi"], "tdee": pt["tdee"], "goal_cal": pt["goal_cal"],
        "goal_type": "weight_loss", "culture": "مصري",
        "symptoms": json.loads(pt["conditions"] or "[]"), "notes": pt["notes"] or "",
    }
    session["pdf_data"] = data
    session["current_plan"] = generate_weekly_plan(data)
    return redirect("/preview")

@app.route("/patients/<int:pid>/status/<s>")
@login_required
def update_patient_status(pid, s):
    if s in ["draft","published"]:
        db_run("UPDATE patients SET status=? WHERE id=? AND user_id=?", (s, pid, session["uid"]))
    return redirect(f"/patients/{pid}")

@app.route("/patients/<int:pid>/delete", methods=["POST"])
@login_required
def delete_patient(pid):
    db_run("DELETE FROM patients WHERE id=? AND user_id=?", (pid, session["uid"]))
    return redirect("/patients")

if __name__ == "__main__":
    app.run(debug=True)

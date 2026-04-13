from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, hashlib, os, json, io
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nutrax2025")
app.permanent_session_lifetime = timedelta(days=30)
DB = "/tmp/nutrax.db"

# ══════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hp(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT,
        country TEXT, lang TEXT DEFAULT 'ar',
        height REAL, weight REAL, age INTEGER,
        gender TEXT DEFAULT 'male',
        goal TEXT DEFAULT 'maintain',
        activity REAL DEFAULT 1.55,
        is_admin INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS weight_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, weight REAL,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS saved_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, name TEXT, plan_data TEXT,
        plan_type TEXT DEFAULT 'personal',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("SELECT id FROM users WHERE is_admin=1")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,1)",
                    ("Admin","admin@nutrax.com",hp("nutrax2025")))
    conn.commit()
    conn.close()

init_db()

def get_user(email, pw):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE email=? AND password=?",
                     (email, hp(pw))).fetchone()
    conn.close()
    return u

def get_user_by_id(uid):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return u

def register(name, email, pw, country):
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (name,email,password,country) VALUES (?,?,?,?)",
                     (name, email, hp(pw), country))
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
        conn = get_db()
        conn.execute("""UPDATE users SET
            height=?, weight=?, age=?, gender=?, goal=?, activity=?
            WHERE id=?""",
            (request.form.get("height"), request.form.get("weight"),
             request.form.get("age"), request.form.get("gender"),
             request.form.get("goal"), request.form.get("activity"),
             session["uid"]))
        conn.commit()
        conn.close()
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
    conn = get_db()
    logs = conn.execute("""SELECT * FROM weight_log WHERE user_id=?
                           ORDER BY logged_at DESC LIMIT 30""",
                        (session["uid"],)).fetchall()
    conn.close()
    return render_template("history.html", user=u,
                           lang=session.get("lang","ar"), logs=logs)

@app.route("/saved")
@login_required
def saved():
    u = get_user_by_id(session["uid"])
    conn = get_db()
    plans = conn.execute("""SELECT * FROM saved_plans WHERE user_id=?
                            ORDER BY created_at DESC""",
                         (session["uid"],)).fetchall()
    conn.close()
    return render_template("saved.html", user=u,
                           lang=session.get("lang","ar"), plans=plans)

@app.route("/log_weight", methods=["POST"])
@login_required
def log_weight():
    w = request.form.get("weight")
    if w:
        conn = get_db()
        conn.execute("INSERT INTO weight_log (user_id,weight) VALUES (?,?)",
                     (session["uid"], w))
        conn.commit()
        conn.close()
    return redirect("/history")

@app.route("/save_plan", methods=["POST"])
@login_required
def save_plan():
    n = request.form.get("plan_name", "خطتي")
    pt = request.form.get("plan_type", "personal")
    conn = get_db()
    conn.execute("""INSERT INTO saved_plans (user_id,name,plan_data,plan_type)
                    VALUES (?,?,?,?)""",
                 (session["uid"], n, json.dumps(dict(request.form)), pt))
    conn.commit()
    conn.close()
    return redirect("/saved")

@app.route("/delete_plan/<int:pid>", methods=["POST"])
@login_required
def delete_plan(pid):
    conn = get_db()
    conn.execute("DELETE FROM saved_plans WHERE id=? AND user_id=?",
                 (pid, session["uid"]))
    conn.commit()
    conn.close()
    return redirect("/saved")

# ══════════════════════════════════════════════
# PDF GENERATOR — مولد الجدول الغذائي
# ══════════════════════════════════════════════
@app.route("/generate", methods=["GET","POST"])
@login_required
def generate():
    u = get_user_by_id(session["uid"])
    if request.method == "POST":
        # حفظ البيانات في الـ session للمراجعة
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
    # توليد الجدول الأسبوعي
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
# MEAL PLAN GENERATOR
# ══════════════════════════════════════════════
def generate_weekly_plan(data):
    symptoms = data.get("symptoms", [])
    has_colon    = any(s in symptoms for s in ["قولون عصبي","ibs"])
    has_diabetes = any(s in symptoms for s in ["سكري النوع الثاني","سكري النوع الاول"])
    has_cardiac  = any(s in symptoms for s in ["امراض القلب","ضغط الدم المرتفع"])
    has_kidney   = any(s in symptoms for s in ["الفشل الكلوي المزمن"])
    has_pregnant = any(s in symptoms for s in ["الحمل"])

    breakfasts = [
        {"meal":"فول مدمس بزيت الزيتون + بيضتان مسلوقتان + خبز اسمر", "cal":446, "p":20},
        {"meal":"شوفان بالحليب + موزة + لوز", "cal":400, "p":12},
        {"meal":"بيض اومليت بالخضار + خبز اسمر", "cal":320, "p":18},
        {"meal":"فول مع طحينة وليمون + خبز اسمر", "cal":360, "p":14},
        {"meal":"شوفان بالموز والقرفة + لوز نيئ", "cal":430, "p":11},
        {"meal":"فول مدمس + بيضتان + طماطم وخيار", "cal":406, "p":21},
        {"meal":"شوفان بالكيوي والعسل", "cal":370, "p":10},
    ]
    lunches = [
        {"meal":"صدر دجاج مشوي + ارز بني + سلطة خضار", "cal":478, "p":49},
        {"meal":"سمك بلطي مشوي + بطاطا حلوة + كوسة مشوية", "cal":417, "p":42},
        {"meal":"فخذ دجاج فرن + برغل + سلطة فتوش", "cal":450, "p":38},
        {"meal":"كبدة دجاج مشوية + ارز بني + ملوخية", "cal":389, "p":33},
        {"meal":"سمكة بلطي كاملة + بطاطا مسلوقة + سلطة", "cal":436, "p":52},
        {"meal":"صدر دجاج فرن بالخضار + ارز بني", "cal":460, "p":52},
        {"meal":"سمك بلطي مشوي + برغل + سلطة فتوش", "cal":392, "p":44},
    ]

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
# PDF BUILDER
# ══════════════════════════════════════════════
def build_pdf(data):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable, PageBreak)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    import arabic_reshaper
try:
    from bidi.algorithm import get_display
except:
    def get_display(t): return t
    import tempfile, urllib.request

    # Font setup
    _tmp = tempfile.gettempdir()
    _reg = os.path.join(_tmp, "Amiri-Regular.ttf")
    _bold = os.path.join(_tmp, "Amiri-Bold.ttf")
    _base = "https://github.com/alif-type/amiri/raw/master/"

    def _get_font(tmp_path, url):
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(tmp_path)),
            tmp_path,
            f"/usr/share/fonts/opentype/fonts-hosny-amiri/{os.path.basename(tmp_path)}",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        urllib.request.urlretrieve(url, tmp_path)
        return tmp_path

    font_reg  = _get_font(_reg,  _base + "Amiri-Regular.ttf")
    font_bold = _get_font(_bold, _base + "Amiri-Bold.ttf")
    pdfmetrics.registerFont(TTFont("Amiri",     font_reg))
    pdfmetrics.registerFont(TTFont("AmiriBold", font_bold))

    def ar(t):
        try:
            return get_display(arabic_reshaper.reshape(str(t)))
        except:
            return str(t)

    def S(size=11, bold=False, color=colors.HexColor("#111111"), align=TA_RIGHT):
        return ParagraphStyle("s", fontName="AmiriBold" if bold else "Amiri",
                             fontSize=size, textColor=color, alignment=align,
                             spaceAfter=4, leading=size*1.5, rightIndent=4, leftIndent=4)

    C_BLUE   = colors.HexColor("#1a3a6b")
    C_GREEN  = colors.HexColor("#1a5c3a")
    C_RED    = colors.HexColor("#8b0000")
    C_ORANGE = colors.HexColor("#b34700")
    C_LBLUE  = colors.HexColor("#dce8f5")
    C_LGREEN = colors.HexColor("#e8f5ec")
    C_LRED   = colors.HexColor("#ffeef0")
    C_GRAY   = colors.HexColor("#f5f5f5")
    C_WHITE  = colors.white

    def tbl(rows, col_ws, hdr_bg=C_BLUE, row_bgs=(C_WHITE, C_GRAY)):
        t = Table([[Paragraph(ar(c), S(9, ri==0,
                    colors.white if ri==0 else colors.HexColor("#111")))
                   for c in row] for ri, row in enumerate(rows)],
                  colWidths=col_ws)
        t.setStyle(TableStyle([
            ("FONTNAME",  (0,0),(-1,-1),"Amiri"),
            ("FONTNAME",  (0,0),(-1,0), "AmiriBold"),
            ("FONTSIZE",  (0,0),(-1,-1),9),
            ("ALIGN",     (0,0),(-1,-1),"RIGHT"),
            ("VALIGN",    (0,0),(-1,-1),"MIDDLE"),
            ("BACKGROUND",(0,0),(-1,0), hdr_bg),
            ("TEXTCOLOR", (0,0),(-1,0), colors.white),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),list(row_bgs)),
            ("GRID",      (0,0),(-1,-1),0.4,colors.HexColor("#cccccc")),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("RIGHTPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(-1,-1),6),
        ]))
        return t

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                           rightMargin=1.5*cm, leftMargin=1.5*cm,
                           topMargin=1.2*cm, bottomMargin=1.2*cm)
    story = []
    import datetime

    symptoms = data.get("symptoms", [])

    # ── صفحة 1: بيانات المريض + مسموح/ممنوع ──
    story.append(Paragraph(ar("NutraX  —  النظام الغذائي الاسبوعي المتخصص"),
                           S(16, True, C_BLUE, TA_CENTER)))
    story.append(Paragraph(ar(f"تاريخ: {datetime.date.today().strftime('%d/%m/%Y')}"),
                           S(10, False, colors.HexColor("#666"), TA_CENTER)))
    story.append(HRFlowable(width="100%", thickness=2, color=C_BLUE,
                            spaceAfter=8, spaceBefore=6))

    # بيانات المريض
    pat = [
        ["الاسم", data.get("name","—"), "العمر", f"{data.get('age','—')} سنة",
         "الجنس", data.get("gender","—")],
        ["الطول", f"{data.get('height','—')} سم", "الوزن",
         f"{data.get('weight','—')} كجم", "BMI", str(data.get("bmi","—"))],
        ["دهون الجسم", f"{data.get('fat_pct','—')}%", "TDEE",
         f"{data.get('tdee','—')} kcal", "الهدف اليومي",
         f"{data.get('goal_cal','—')} kcal"],
    ]
    pt = Table([[Paragraph(ar(c), S(9, i%2==0, C_BLUE if i%2==0 else colors.HexColor("#111")))
                for i,c in enumerate(row)] for row in pat],
               colWidths=[2.4*cm,3*cm,2.4*cm,3*cm,2.4*cm,3*cm])
    pt.setStyle(TableStyle([
        ("FONTNAME",(0,0),(-1,-1),"Amiri"),("FONTSIZE",(0,0),(-1,-1),9),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BACKGROUND",(0,0),(0,-1),C_LBLUE),("BACKGROUND",(2,0),(2,-1),C_LBLUE),
        ("BACKGROUND",(4,0),(4,-1),C_LBLUE),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#aaa")),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[C_WHITE,C_GRAY]),
    ]))
    story.append(pt)

    if symptoms:
        story.append(Spacer(1,6))
        story.append(Paragraph(ar("الاعراض والحالات: " + " | ".join(symptoms)),
                               S(9, False, C_RED)))
    if data.get("notes"):
        story.append(Paragraph(ar(f"ملاحظات: {data['notes']}"),
                               S(9, False, colors.HexColor("#555"))))

    story.append(HRFlowable(width="100%", thickness=1, color=C_GREEN,
                            spaceAfter=6, spaceBefore=6))

    # مسموح / ممنوع
    story.append(Paragraph(ar("المسموح والممنوع"), S(13, True, C_BLUE, TA_CENTER)))
    story.append(Spacer(1,4))

    allowed = [
        "فول مدمس + عدس + شوربات + سمك مشوي",
        "دجاج مشوي او فرن (بدون جلد) + بيض",
        "شوفان + خبز اسمر + ارز بني + برغل",
        "زبادي يوناني سادة + جبن قريش",
        "ملوخية + كوسة + خضار مطبوخة",
        "زيت زيتون (ملعقة) + فاكهة طازجة",
        "شاي اخضر + ماء دافئ بالليمون صباحا",
    ]
    forbidden = [
        "الخبز الابيض والعيش الفينو",
        "الاكل المقلي + الدهانة + السمن",
        "المشروبات الغازية + العصائر المعلبة",
        "البهارات الحارة (تستفز القولون)",
        "الحلويات والسكريات المضافة",
        "الكافيين الزائد (اكثر من كوب)",
        "البقوليات بكميات كبيرة دفعة واحدة",
    ]
    ar_rows = [["المسموح — بحرية", "الممنوع او المقلل"]]
    for a, f in zip(allowed, forbidden):
        ar_rows.append([f"  {a}", f"  {f}"])
    ar_t = Table([[Paragraph(ar(c), S(9, ri==0,
                    C_GREEN if (ri==0 and ci==0) else C_RED if (ri==0 and ci==1)
                    else colors.HexColor("#14532d") if ci==0
                    else colors.HexColor("#991b1b")))
                  for ci,c in enumerate(row)]
                 for ri,row in enumerate(ar_rows)],
                colWidths=[9.15*cm, 9.15*cm])
    ar_t.setStyle(TableStyle([
        ("FONTNAME",(0,0),(-1,-1),"Amiri"),("FONTSIZE",(0,0),(-1,-1),9),
        ("ALIGN",(0,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BACKGROUND",(0,0),(0,0),C_GREEN),("BACKGROUND",(1,0),(1,0),C_RED),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_LGREEN,C_WHITE]),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#ccc")),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("RIGHTPADDING",(0,0),(-1,-1),6),("LEFTPADDING",(0,0),(-1,-1),6),
    ]))
    story.append(ar_t)
    story.append(PageBreak())

    # ── صفحة 2: الجدول الاسبوعي ──
    story.append(Paragraph(ar("الجدول الغذائي الاسبوعي التفصيلي"),
                           S(14, True, C_BLUE, TA_CENTER)))
    story.append(Paragraph(ar(f"الهدف اليومي: {data.get('goal_cal','—')} kcal"),
                           S(10, False, C_GREEN, TA_CENTER)))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE,
                            spaceAfter=6, spaceBefore=4))

    plan = generate_weekly_plan(data)
    week_rows = [["اليوم","الفطار","الغداء","العشاء","سناك / قبل النوم","kcal"]]
    for d in plan:
        week_rows.append([
            d["day"],
            d["breakfast"][:35],
            d["lunch"][:35],
            d["dinner"][:35],
            f"{d['snack'][:20]} | {d['before_sleep']}",
            str(d["total_cal"]),
        ])

    wt = Table([[Paragraph(ar(c), S(8, ri==0,
                colors.white if ri==0 else colors.HexColor("#111")))
               for c in row] for ri,row in enumerate(week_rows)],
               colWidths=[1.8*cm, 4*cm, 4*cm, 3.5*cm, 3.5*cm, 1.5*cm])
    wt.setStyle(TableStyle([
        ("FONTNAME",(0,0),(-1,-1),"Amiri"),("FONTSIZE",(0,0),(-1,-1),8),
        ("FONTNAME",(0,0),(-1,0),"AmiriBold"),("FONTSIZE",(0,0),(-1,0),9),
        ("ALIGN",(0,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BACKGROUND",(0,0),(-1,0),C_BLUE),("TEXTCOLOR",(0,0),(-1,0),C_WHITE),
        ("BACKGROUND",(0,1),(0,-1),C_LBLUE),("TEXTCOLOR",(0,1),(0,-1),C_BLUE),
        ("FONTNAME",(0,1),(0,-1),"AmiriBold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_WHITE,C_GRAY]),
        ("TEXTCOLOR",(5,1),(5,-1),C_RED),("FONTNAME",(5,1),(5,-1),"AmiriBold"),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#bbb")),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("RIGHTPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(wt)
    story.append(PageBreak())

    # ── صفحة 3: النصايح والبروتوكولات ──
    story.append(Paragraph(ar("النصايح العامة والبروتوكولات"),
                           S(14, True, C_BLUE, TA_CENTER)))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE,
                            spaceAfter=6, spaceBefore=4))

    sections = [
        (C_BLUE, "الماء اساس كل شيء", [
            "كوب ماء دافئ + نصف ليمون فور الاستيقاظ",
            "8 اكواب ماء على مدار اليوم (2 لتر على الاقل)",
            "كوب ماء قبل كل وجبة بـ 30 دقيقة يقلل الشهية",
            "تجنب الماء البارد جدا مع الاكل",
        ]),
        (C_GREEN, "عادات الاكل الصحيحة", [
            "3 وجبات رئيسية + سناك واحد — لا تقطع اكثر من 6 ساعات",
            "امضغ ببطء — الاحساس بالشبع يأتي بعد 20 دقيقة",
            "لا تأكل امام الشاشة — الاكل المشتت يزيد الكمية",
            "الفطار الزامي خلال ساعة من الاستيقاظ",
        ]),
        (C_ORANGE, "رفع معدل الحرق", [
            "بروتين في كل وجبة (بيض / دجاج / سمك / عدس)",
            "البهارات الامنة: كركم + قرفة + زنجبيل ترفع الحرق",
            "مشي 30 دقيقة بعد الغداء يرفع الحرق ويهدئ القولون",
            "الجلوس المستمر يقلل الحرق — قم وتحرك 5 دقائق كل ساعة",
        ]),
        (C_RED, "تحذيرات مهمة", [
            "لا تخفض السعرات اكثر من المحدد — يوقف الحرق",
            "لو جاعك بين الوجبات: اشرب ماء اولا ثم فاكهة",
            "راجع مع اخصائي التغذية كل 4 اسابيع",
            "اي اعراض غير عادية — راجع طبيبك فورا",
        ]),
    ]

    for color, title, items in sections:
        t_rows = [[title]] + [[f"  {item}"] for item in items]
        sec_t = Table([[Paragraph(ar(c), S(9.5, ri==0,
                       colors.white if ri==0 else colors.HexColor("#1a1a1a")))
                       for c in row] for ri,row in enumerate(t_rows)],
                     colWidths=[18.3*cm])
        sec_t.setStyle(TableStyle([
            ("FONTNAME",(0,0),(-1,-1),"Amiri"),("FONTSIZE",(0,0),(-1,-1),9.5),
            ("ALIGN",(0,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("BACKGROUND",(0,0),(0,0),color),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#f8f8f8"),C_WHITE]),
            ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#ddd")),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("RIGHTPADDING",(0,0),(-1,-1),8),
        ]))
        story.append(sec_t)
        story.append(Spacer(1,6))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=C_BLUE,
                            spaceAfter=4, spaceBefore=8))
    story.append(Paragraph(
        ar(f"NutraX  |  {data.get('name','المريض')}  |  {datetime.date.today().strftime('%d/%m/%Y')}  |  يراجع بعد 4 اسابيع"),
        S(9, False, colors.HexColor("#888"), TA_CENTER)))

    doc.build(story)
    return buf.getvalue()

if __name__ == "__main__":
    app.run(debug=True)

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

# ═══════════════════════════════════════════════
# INGREDIENTS DATABASE (Food Analyzer)
# ═══════════════════════════════════════════════
try:
    from ingredients_db import INGREDIENTS, CATEGORIES, TOTAL_INGREDIENTS, get_categories
    INGREDIENTS_AVAILABLE = True
except ImportError:
    INGREDIENTS_AVAILABLE = False
    INGREDIENTS = {}
    CATEGORIES = {}
    TOTAL_INGREDIENTS = 0
    def get_categories(): return []

# ═══════════════════════════════════════════════
# PAYMENTS MODULE (Stripe Integration)
# ═══════════════════════════════════════════════
from payments import (
    PRICING, create_checkout_session, verify_webhook,
    handle_checkout_completed, handle_invoice_paid,
    handle_subscription_updated, handle_subscription_canceled,
    has_active_access, get_user_access_info,
    cancel_user_subscription, detect_currency,
    get_supported_currencies, STRIPE_PUBLIC_KEY
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
    def _dict_factory(cursor, row):
        return {col[0]: row[i] for i, col in enumerate(cursor.description)}
    def get_db():
        conn = sqlite3.connect(DB); conn.row_factory = _dict_factory; return conn
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
    """Initialize database - safe with try/except for each table"""
    if DATABASE_URL:
        tables_pg = [
            """CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, country TEXT, lang TEXT DEFAULT 'ar', height REAL, weight REAL, age INTEGER, gender TEXT DEFAULT 'male', goal TEXT DEFAULT 'maintain', activity REAL DEFAULT 1.55, is_admin INTEGER DEFAULT 0, role TEXT DEFAULT 'client', active INTEGER DEFAULT 1, phone TEXT, conditions TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS weight_log (id SERIAL PRIMARY KEY, user_id INTEGER, weight REAL, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS saved_plans (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, plan_data TEXT, plan_type TEXT DEFAULT 'personal', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS patients (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, age INTEGER, gender TEXT, height REAL, weight REAL, fat_pct REAL, bmi REAL, tdee INTEGER, goal_cal INTEGER, conditions TEXT, notes TEXT, status TEXT DEFAULT 'draft', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS plan_requests (id SERIAL PRIMARY KEY, client_id INTEGER, client_name TEXT, status TEXT DEFAULT 'pending', request_data TEXT, plan_data TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender_id INTEGER, receiver_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS blocked_users (id SERIAL PRIMARY KEY, email TEXT UNIQUE, blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason TEXT)""",
            """CREATE TABLE IF NOT EXISTS subscriptions (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, stripe_customer_id TEXT, stripe_subscription_id TEXT, plan_key TEXT, status TEXT DEFAULT 'pending', currency TEXT DEFAULT 'USD', amount INTEGER DEFAULT 0, current_period_start TIMESTAMP, current_period_end TIMESTAMP, trial_end TIMESTAMP, cancel_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS payments (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, stripe_session_id TEXT UNIQUE, stripe_payment_intent_id TEXT, plan_key TEXT, status TEXT DEFAULT 'pending', currency TEXT DEFAULT 'USD', amount INTEGER DEFAULT 0, expires_at TIMESTAMP, metadata TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        ]
        for sql in tables_pg:
            try: db_run(sql)
            except Exception as e: print(f"Table create warning: {e}")
    else:
        tables_sq = [
            """CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, country TEXT, lang TEXT DEFAULT 'ar', height REAL, weight REAL, age INTEGER, gender TEXT DEFAULT 'male', goal TEXT DEFAULT 'maintain', activity REAL DEFAULT 1.55, is_admin INTEGER DEFAULT 0, role TEXT DEFAULT 'client', active INTEGER DEFAULT 1, phone TEXT, conditions TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS weight_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS saved_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, plan_data TEXT, plan_type TEXT DEFAULT 'personal', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, age INTEGER, gender TEXT, height REAL, weight REAL, fat_pct REAL, bmi REAL, tdee INTEGER, goal_cal INTEGER, conditions TEXT, notes TEXT, status TEXT DEFAULT 'draft', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS plan_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, client_name TEXT, status TEXT DEFAULT 'pending', request_data TEXT, plan_data TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS blocked_users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason TEXT)""",
            """CREATE TABLE IF NOT EXISTS subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, stripe_customer_id TEXT, stripe_subscription_id TEXT, plan_key TEXT, status TEXT DEFAULT 'pending', currency TEXT DEFAULT 'USD', amount INTEGER DEFAULT 0, current_period_start TIMESTAMP, current_period_end TIMESTAMP, trial_end TIMESTAMP, cancel_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, stripe_session_id TEXT UNIQUE, stripe_payment_intent_id TEXT, plan_key TEXT, status TEXT DEFAULT 'pending', currency TEXT DEFAULT 'USD', amount INTEGER DEFAULT 0, expires_at TIMESTAMP, metadata TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        ]
        for sql in tables_sq:
            try: db_run(sql)
            except Exception as e: print(f"Table create warning: {e}")

    for col_sql in [
        "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'client'",
        "ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN phone TEXT",
        "ALTER TABLE users ADD COLUMN conditions TEXT",
        "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE users ADD COLUMN doctor_notes TEXT",
        "ALTER TABLE users ADD COLUMN liked_foods TEXT",
        "ALTER TABLE users ADD COLUMN disliked_foods TEXT",
        "ALTER TABLE users ADD COLUMN allergies TEXT",
        "ALTER TABLE users ADD COLUMN onboarded_at TIMESTAMP",
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
        db_run("""INSERT INTO users (name,email,password,country,age,phone,role,active) VALUES (?,?,?,?,?,?,'client',1)""",
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


# ═══════════════════════════════════════════════
# SUBSCRIPTION/PAYMENT MIDDLEWARE
# ═══════════════════════════════════════════════

def subscription_required(f):
    """Decorator: العميل لازم يكون عنده اشتراك نشط أو دفعة سارية"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session:
            return redirect("/")
        u = get_user_by_id(session["uid"])
        # Admin/Nutritionist always allowed
        if u and (u.get("is_admin") or u.get("role") in ["admin", "nutritionist"]):
            return f(*args, **kwargs)
        # Client must have active access
        if not has_active_access(session["uid"], db_row):
            return redirect("/subscription-required?reason=" + (request.path or ""))
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
        latest = db_row("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at DESC LIMIT 1", (user_id,))
        if not latest: return (True, 0, 0)
        date_str = latest.get("logged_at")
        if isinstance(date_str, str):
            try: last_date = datetime.fromisoformat(date_str.replace('Z', ''))
            except:
                try: last_date = datetime.strptime(date_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                except: return (True, 0, 0)
        else:
            last_date = date_str
        diff = datetime.now() - last_date
        seconds = diff.total_seconds()
        week = 7 * 24 * 60 * 60
        if seconds >= week: return (True, 0, 0)
        left = week - seconds
        days = int(left // (24 * 60 * 60))
        hours = int((left % (24 * 60 * 60)) // 3600)
        return (False, days, hours)
    except:
        return (True, 0, 0)

def can_request_new_plan(client_id):
    try:
        latest = db_row("SELECT * FROM plan_requests WHERE client_id=? ORDER BY created_at DESC LIMIT 1", (client_id,))
        if not latest: return (True, 0, 0, None)
        date_str = latest.get("created_at")
        if isinstance(date_str, str):
            try: last_date = datetime.fromisoformat(date_str.replace('Z', ''))
            except:
                try: last_date = datetime.strptime(date_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                except: return (True, 0, 0, None)
        else:
            last_date = date_str
        diff = datetime.now() - last_date
        seconds = diff.total_seconds()
        week = 7 * 24 * 60 * 60
        if seconds >= week: return (True, 0, 0, last_date.strftime("%Y-%m-%d"))
        left = week - seconds
        days = int(left // (24 * 60 * 60))
        hours = int((left % (24 * 60 * 60)) // 3600)
        return (False, days, hours, last_date.strftime("%Y-%m-%d"))
    except:
        return (True, 0, 0, None)

# ═══════════════════════════════════════════════
# DAILY TIPS BASED ON CONDITIONS
# ═══════════════════════════════════════════════
DAILY_TIPS_GENERAL = [
    {"icon": "💧", "title": "اشرب المياه", "tip": "اشرب كوب ماء فاتر مع نصف ليمونة على الريق - يحفز الهضم"},
    {"icon": "🚶", "title": "تمشى شوية", "tip": "30 دقيقة مشي بعد الغداء ينظم السكر ويساعد على الهضم"},
    {"icon": "😴", "title": "نام كويس", "tip": "النوم 7-8 ساعات مهم زي الأكل والتمرين للوزن الصحي"},
    {"icon": "🍎", "title": "فاكهة بدل الحلويات", "tip": "لو حسيت برغبة في حاجة حلوة، خد فاكهة بدل البسكويت"},
    {"icon": "🥗", "title": "خضار في كل وجبة", "tip": "حط نصف الطبق خضار - شبع أكتر وسعرات أقل"},
    {"icon": "⏰", "title": "متاكلش بسرعة", "tip": "مضغ الأكل ببطء يخليك تشبع أسرع وتاكل أقل"},
    {"icon": "🧂", "title": "قلل الملح", "tip": "الأكل الجاهز فيه ملح كتير - حضر أكلك في البيت"},
]

CONDITION_TIPS = {
    "قولون": [
        {"icon": "⚠️", "title": "خلي بالك من القولون", "tip": "تجنب الفول والحمص والكرنب والبروكلي - بتعمل غازات"},
        {"icon": "🌶️", "title": "بعيداً عن الحار", "tip": "تجنب الفلفل الحار والبهارات الحارة - بتهيج القولون"},
        {"icon": "☕", "title": "قلل الكافيين", "tip": "القهوة والشاي بكميات كبيرة بتزود اضطراب القولون"},
    ],
    "سكري": [
        {"icon": "🍞", "title": "خد بالك من الكارب", "tip": "ابعد عن الأرز الأبيض والخبز الأبيض - الأسمر أفضل"},
        {"icon": "🍯", "title": "السكر عدو", "tip": "تجنب السكر المضاف، العسل، والعصائر المحلاة"},
        {"icon": "📊", "title": "اقيس السكر", "tip": "قيس السكر قبل الفطار وبعد الأكل بساعتين"},
    ],
    "ضغط": [
        {"icon": "🧂", "title": "ملح أقل", "tip": "تجنب المخللات والصوصات الجاهزة والشاورما"},
        {"icon": "🥬", "title": "خضار ورقية", "tip": "السبانخ والجرجير والبقدونس بيخفضوا الضغط"},
        {"icon": "🚫", "title": "ابعد عن المعلبات", "tip": "الأكل المعلب فيه ملح كتير جداً"},
    ],
    "كلوي": [
        {"icon": "💧", "title": "اشرب باعتدال", "tip": "اتبع تعليمات الدكتور بخصوص كمية المياه"},
        {"icon": "🍌", "title": "احذر البوتاسيوم", "tip": "قلل من الموز والطماطم والبطاطا والمكسرات"},
        {"icon": "🥩", "title": "بروتين معتدل", "tip": "كميات قليلة من البروتين الحيواني"},
    ],
    "قلب": [
        {"icon": "🐟", "title": "أوميجا 3", "tip": "السمك مرتين في الأسبوع - السلمون والسردين أفضل"},
        {"icon": "🥑", "title": "دهون صحية", "tip": "زيت الزيتون والأفوكادو بدل السمن والزبدة"},
        {"icon": "🚭", "title": "قلل الملح", "tip": "الملح يرفع الضغط ويهد القلب"},
    ],
    "حامل": [
        {"icon": "🤰", "title": "حمض الفوليك", "tip": "السبانخ والبروكلي والعدس مهمين جداً للحمل"},
        {"icon": "🥛", "title": "كالسيوم يومياً", "tip": "اللبن والزبادي والجبن لعظام الجنين"},
        {"icon": "🚫", "title": "تجنبي", "tip": "الكبدة، السمك النيء، والكافيين الكتير"},
    ],
    "g6pd": [
        {"icon": "🚫", "title": "ابعد عن الفول", "tip": "تجنب الفول، الحمص، اللوبيا والبقوليات الحمراء"},
        {"icon": "💊", "title": "احذر الأدوية", "tip": "بعض الأدوية ممنوعة - استشر الدكتور قبل أي علاج"},
        {"icon": "🌿", "title": "أعشاب آمنة", "tip": "تجنب الحناء والكافور وبعض الأعشاب"},
    ],
    "ثلاسيميا": [
        {"icon": "🚫", "title": "قلل الحديد", "tip": "ابعد عن الكبدة واللحوم الحمراء بكميات كبيرة"},
        {"icon": "☕", "title": "شاي مع الأكل", "tip": "الشاي يقلل امتصاص الحديد - اشربه مع الأكل"},
        {"icon": "🥬", "title": "خضار آمنة", "tip": "البروكلي والكرنب والجزر مفيدين"},
    ],
    "لاكتوز": [
        {"icon": "🥛", "title": "ابعد عن الألبان", "tip": "تجنب الحليب والزبادي والجبن الطازج"},
        {"icon": "🌱", "title": "بدائل نباتية", "tip": "حليب اللوز والصويا وجوز الهند بدائل ممتازة"},
        {"icon": "💊", "title": "أنزيم اللاكتيز", "tip": "ممكن تاخده قبل الأكل لو مضطر تاكل لبن"},
    ],
}

def get_tips_for_user(user):
    """Get personalized tips based on user's conditions"""
    tips = list(DAILY_TIPS_GENERAL)

    if user and user.get("conditions"):
        try:
            conditions = json.loads(user["conditions"])
            condition_map = {
                "قولون عصبي": "قولون", "IBS": "قولون",
                "سكري": "سكري", "diabetes": "سكري",
                "ضغط الدم": "ضغط", "hypertension": "ضغط",
                "فشل كلوي": "كلوي", "كلى": "كلوي",
                "أمراض القلب": "قلب", "قلب": "قلب",
                "حمل": "حامل", "رضاعة": "حامل",
                "G6PD": "g6pd", "نقص G6PD": "g6pd",
                "ثلاسيميا": "ثلاسيميا",
                "حساسية اللاكتوز": "لاكتوز", "lactose": "لاكتوز",
            }
            for cond in conditions:
                key = condition_map.get(cond)
                if key and key in CONDITION_TIPS:
                    tips = CONDITION_TIPS[key] + tips
        except:
            pass

    return tips


def is_email_blocked(email):
    """Check if email is in blocked list - safe if table missing"""
    if not email: return False
    try:
        row = db_row("SELECT id FROM blocked_users WHERE email=?", (email.lower().strip(),))
        return row is not None
    except Exception:
        return False

def get_unread_messages_count(user_id):
    """Get count of unread messages - safe if table missing"""
    try:
        row = db_row("SELECT COUNT(*) as c FROM messages WHERE receiver_id=? AND is_read=0", (user_id,))
        return row["c"] if row else 0
    except Exception:
        return 0



@app.context_processor
def inject_globals():
    """Make unread message count and pending count available in all templates"""
    ctx = {"unread_messages": 0, "pending_count": 0, "active_access": None}
    if "uid" in session:
        try:
            ctx["unread_messages"] = get_unread_messages_count(session["uid"])
            user = get_user_by_id(session["uid"])
            if user and (user.get("is_admin") or user.get("role") in ["admin", "nutritionist"]):
                ctx["pending_count"] = get_pending_requests_count()
            # Get active access info for all users
            try:
                ctx["active_access"] = get_user_access_info(session["uid"], db_row)
            except: pass
        except: pass
    return ctx


@app.route("/", methods=["GET","POST"])
def login():
    if "uid" in session: return redirect("/dashboard")
    lang = session.get("lang", "ar")
    error = ""
    tab = request.args.get("tab", "login")
    if request.method == "POST":
        check_email = request.form.get("email", "").lower().strip()
        if is_email_blocked(check_email):
            error = "هذا الحساب محظور. تواصل مع الإدارة."
            return render_template("login.html", error=error, tab="login", lang=lang)
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
                try: age_int = int(age) if age else None
                except: age_int = None
                r = register(name, email, pw, country, age_int, phone)
                if r == "ok":
                    error = "تم التسجيل بنجاح! سجل دخولك دلوقتي."
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
    total_plans = 0
    recent_requests = []
    try:
        pending_count = get_pending_requests_count()
        r = db_row("SELECT COUNT(*) as cnt FROM users WHERE role='client'")
        total_clients = r.get("cnt", 0) if r else 0
        r2 = db_row("SELECT COUNT(*) as cnt FROM plan_requests WHERE status='approved'")
        total_plans = r2.get("cnt", 0) if r2 else 0
        recent_requests = db_rows("SELECT * FROM plan_requests ORDER BY created_at DESC LIMIT 5")
    except:
        pass
    return render_template("dashboard.html", user=u, lang=session.get("lang","ar"),
                           role=role, pending_count=pending_count, total_clients=total_clients,
                           total_plans=total_plans, recent_requests=recent_requests)

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

    return render_template("my_plan.html", user=u, lang=session.get("lang","ar"),
                           latest_plan=latest_plan, pending_request=pending_request,
                           can_request=can_request, days_left=days_left,
                           hours_left=hours_left, last_request_date=last_date,
                           today_tip=today_tip)

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
            return f"خطأ: {e}", 500
        return redirect("/my-plan")
    return render_template("request_plan.html", user=u, lang=session.get("lang","ar"), diet_plans=DIET_PLAN_TYPES)

@app.route("/admin/users")
@admin_required
def admin_users():
    u = get_user_by_id(session["uid"])
    try: all_users = db_rows("SELECT * FROM users ORDER BY id DESC")
    except: all_users = []
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

@app.route("/privacy")
def privacy():
    return render_template("privacy.html", lang=session.get("lang", "ar"))


@app.route("/terms")
def terms():
    return render_template("terms.html", lang=session.get("lang", "ar"))


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
            "allergies": request.form.getlist("allergies"),
            "liked_foods": request.form.get("liked_foods",""),
            "disliked_foods": request.form.get("disliked_foods",""),
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

@app.route("/get_meal_options", methods=["POST"])
@staff_required
def get_meal_options():
    data = session.get("pdf_data")
    if not data: return jsonify({"ok": False, "options": []}), 400
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
    all_options = []
    if pool_key in pool and pool[pool_key]:
        for m in pool[pool_key]:
            all_options.append({"meal": m["meal"], "cal": m.get("cal", 0), "p": m.get("p", 0), "source": culture})
    pools_map = {"weight_loss": WEIGHT_LOSS, "muscle_gain": MUSCLE_GAIN, "bulking": BULKING}
    main_pool = pools_map.get(goal, WEIGHT_LOSS)
    for other_culture, other_pool in main_pool.items():
        if other_culture != culture and pool_key in other_pool:
            for m in other_pool[pool_key][:5]:
                all_options.append({"meal": m["meal"], "cal": m.get("cal", 0), "p": m.get("p", 0), "source": other_culture})
    return jsonify({"ok": True, "options": all_options})

@app.route("/replace_meal", methods=["POST"])
@staff_required
def replace_meal():
    plan = session.get("current_plan")
    if not plan: return jsonify({"ok": False, "error": "no plan"}), 400
    try:
        day_idx = int(request.form.get("day_idx", 0))
        meal_type = request.form.get("meal_type", "")
        new_meal = request.form.get("new_meal", "").strip()
        if not new_meal or not meal_type: return jsonify({"ok": False, "error": "missing data"}), 400
        if day_idx < 0 or day_idx >= len(plan): return jsonify({"ok": False, "error": "invalid day"}), 400
        plan[day_idx][meal_type] = new_meal
        session["current_plan"] = plan
        return jsonify({"ok": True, "new_meal": new_meal})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/edit_meal", methods=["POST"])
@staff_required
def edit_meal():
    plan = session.get("current_plan")
    if not plan: return jsonify({"ok": False, "error": "no plan"}), 400
    try:
        day_idx = int(request.form.get("day_idx", 0))
        meal_type = request.form.get("meal_type", "")
        new_text = request.form.get("new_text", "").strip()
        if not new_text or not meal_type: return jsonify({"ok": False, "error": "missing data"}), 400
        if day_idx < 0 or day_idx >= len(plan): return jsonify({"ok": False, "error": "invalid day"}), 400
        plan[day_idx][meal_type] = new_text
        session["current_plan"] = plan
        return jsonify({"ok": True, "saved_text": new_text})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



# ═══════════════════════════════════════════════════
# CHAT/MESSAGING SYSTEM (FIXED - was using db_all)
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

    if request.method == "POST":
        msg = request.form.get("message", "").strip()
        if msg:
            db_run("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?,?,?)",
                   (user["id"], other_id, msg))
        return redirect(f"/messages/{other_id}")

    db_run("UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=?", (other_id, user["id"]))

    msgs = db_rows("""SELECT * FROM messages 
                    WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                    ORDER BY created_at ASC""",
                  (user["id"], other_id, other_id, user["id"]))

    return render_template("chat.html", messages=msgs, user=user, other=other, lang=session.get("lang","ar"))


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
    except:
        pass

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

def _has(symptoms, keywords):
    for s in symptoms:
        s_low = str(s).lower().strip()
        for k in keywords:
            if k.lower() in s_low: return True
    return False


# ═══════════════════════════════════════════════
# USER EXCLUSIONS PARSING
# (notes + dislikes + allergies → list of words to exclude)
# ═══════════════════════════════════════════════

ALLERGY_KEYWORDS = {
    "اللاكتوز": ["حليب", "لبن", "زبادي", "جبن", "قشدة", "كريمة", "لبنة", "حلوم", "فيتا", "موزاريلا", "بارميزان", "ايس كريم", "بوظة", "كاكاو بحليب"],
    "الجلوتين": ["قمح", "خبز", "مكرونة", "برغل", "كسكس", "سميد", "شعير", "فريكة", "بسكويت", "كرواسون", "توست", "فطير"],
    "المكسرات": ["لوز", "كاجو", "بندق", "فستق", "جوز", "مكسرات", "بقان"],
    "البيض": ["بيض", "اومليت", "عجة", "شكشوكة", "بيضة", "بيضتين"],
    "الأسماك": ["سمك", "سلمون", "تونة", "بلطي", "هامور", "ماكريل", "سردين"],
    "الفول السوداني": ["فول سوداني", "زبدة فول"],
    "الصويا": ["صويا", "توفو", "تمبيه", "ادامامي"],
    "المحار": ["جمبري", "محار", "كركند", "اسكالوب", "اخطبوط"],
    "السمسم": ["سمسم", "طحينة", "حلاوة طحينية"],
}

def parse_user_exclusions(notes_text, disliked_foods, allergies):
    """يحوّل الملحوظات والحساسية والأكلات اللي مش بيحبها إلى قايمة كلمات تتشال من الوجبات."""
    exclusions = set()

    # 1. الأكلات اللي مش بيحبها (نص حر مفصول بفواصل)
    if disliked_foods:
        for item in disliked_foods.replace("،", ",").replace(";", ",").split(","):
            item = item.strip()
            if len(item) > 1:
                exclusions.add(item)

    # 2. الحساسية (list من الـ checkboxes)
    if allergies:
        for allergy in allergies:
            for key, kws in ALLERGY_KEYWORDS.items():
                if key in allergy:
                    exclusions.update(kws)

    # 3. الملحوظات النصية - دور على triggers
    if notes_text:
        text = notes_text.strip()
        triggers = ["اشيل", "شيل", "بدون", "تجنب", "مش بحب", "مش باكل",
                    "ما بحب", "لا اكل", "حساسية من", "remove", "no ", "avoid",
                    "without", "allergic to"]
        for trigger in triggers:
            idx = 0
            while True:
                pos = text.find(trigger, idx)
                if pos == -1:
                    break
                rest = text[pos + len(trigger):pos + len(trigger) + 60]
                rest = rest.replace("،", ".").replace(",", ".").replace(" و ", ".").replace("\n", ".")
                first_chunk = rest.split(".")[0].strip()
                if first_chunk:
                    words = first_chunk.split()[:3]
                    for w in words:
                        w = w.strip(":،.,!؟")
                        if len(w) > 2:
                            exclusions.add(w)
                idx = pos + 1

    return list(exclusions)


def filter_meals_by_exclusions(meals, exclusions):
    """شيل أي وجبة فيها كلمة من الـ exclusions. لو شلنا كل الوجبات نرجّع الأصلية."""
    if not exclusions:
        return meals
    result = []
    for meal in meals:
        meal_text = meal.get("meal", "") if isinstance(meal, dict) else str(meal)
        if not any(ex in meal_text for ex in exclusions):
            result.append(meal)
    return result if result else meals


def generate_weekly_plan(data):
    symptoms = data.get("symptoms", [])
    goal = data.get("goal_type", "weight_loss")
    culture = data.get("culture", "مصري")
    diet_type = data.get("diet_plan_type", "standard")

    # NEW: seed فريد لكل عميل عشان كل واحد يطلع له خطة مختلفة عن التاني
    try:
        user_id = data.get("user_id") or session.get("uid", 0) or 0
    except: user_id = 0
    seed_val = ((user_id or 1) * 1000007 + int(datetime.now().timestamp() * 1000)) % (2**32)
    random.seed(seed_val)

    # NEW: قراية الحقول الجديدة من الاستمارة الموحدة
    notes = data.get("notes", "")
    disliked = data.get("disliked_foods", "")
    allergies = data.get("allergies", []) if isinstance(data.get("allergies"), list) else []
    user_exclusions = parse_user_exclusions(notes, disliked, allergies)

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

    # NEW: شيل الأكلات اللي العميل مش عاوزها (notes / dislikes / allergies)
    breakfasts = filter_meals_by_exclusions(breakfasts, user_exclusions)
    lunches = filter_meals_by_exclusions(lunches, user_exclusions)
    dinners = filter_meals_by_exclusions(dinners, user_exclusions)

    snacks = get_snacks_for_goal(goal)
    pool_snacks = pool.get("snack", [])
    if pool_snacks: snacks = pool_snacks[:10]
    while len(snacks) < 7: snacks.append("فاكهة + مكسرات (120 kcal)")

    # NEW: شيل من الـ snacks كمان
    snacks = [s for s in snacks if not any(ex in (s if isinstance(s, str) else s.get("meal","")) for ex in user_exclusions)] or snacks

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
            # الوجبة الأولى = فطار شبع (مش غدا) - زي شوفان أو بيض أو فول
            b = breakfasts[i % len(breakfasts)]
            d = dinners[i % len(dinners)]
            day_plan["meal1"] = b["meal"]
            day_plan["snack"] = snacks[i % len(snacks)]
            day_plan["meal2"] = d["meal"]
            total_cal = b.get("cal",350) + d.get("cal",450) + 150
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
    has_lactose = _has(symptoms, ["لاكتوز","lactose"])
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
        forbidden = ["الفول بكل أنواعه","الحمص والبقوليات الحمراء"] + forbidden
        allowed = ["عدس أصفر بكميات محدودة"] + allowed
    else:
        if goal in ["weight_loss","maintenance"]:
            allowed = ["فول مدمس + عدس + شوربات + سمك مشوي"] + allowed
    if has_thal:
        forbidden = ["الكبدة والأعضاء الداخلية","اللحوم الحمراء بإفراط"] + forbidden
        allowed = ["شاي مع الوجبات"] + allowed
    if has_colon:
        forbidden.append("التوابل الحارة")
        forbidden.append("الكافيين الزائد")
    if has_lactose:
        forbidden = ["الحليب والألبان كاملة الدسم","الجبن الطازج","الايس كريم"] + forbidden
        allowed = ["حليب اللوز / الصويا / جوز الهند","جبن معتق بكميات قليلة"] + allowed
    if needs_d3:
        allowed = ["أسماك دهنية: سلمون","صفار البيض + الفطر","تعرض للشمس 15 دقيقة"] + allowed
    if needs_fe and not has_thal:
        allowed = ["لحوم حمراء + كبدة","سبانخ + عدس"] + allowed
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
    if symptoms: notes_parts.append(" - ".join(symptoms))
    allergies_data = data.get("allergies", [])
    if allergies_data: notes_parts.append("حساسية: " + " - ".join(allergies_data))
    if data.get("disliked_foods"): notes_parts.append("لا يأكل: " + data.get("disliked_foods"))
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
            emoji = plan_info["meal_emojis"].get(meal_key, "-")
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
        'client': {'name': data.get('name','-'), 'age': data.get('age','-'),
            'gender': data.get('gender','-'), 'height': data.get('height','-'),
            'weight': data.get('weight','-'), 'bmi': data.get('bmi','-'),
            'body_fat': data.get('fat_pct','-'), 'tdee': data.get('tdee','-'),
            'target_kcal': data.get('goal_cal','-'), 'deficit': deficit},
        'conditions': symptoms if symptoms else ["لا توجد حالات مسجلة"],
        'clinical_notes': clinical_notes,
        'allowed': allowed, 'forbidden': forbidden, 'days': pdf_days,
        'tips': {
            'water': ['كوب ماء دافئ + نصف ليمونة فور الاستيقاظ','8 أكواب ماء يومياً',
                      'كوب ماء قبل كل وجبة بـ 30 دقيقة','تجنب الماء البارد جداً'],
            'habits': ['مضغ بطيء - الشبع بعد 20 دقيقة','لا تأكل أمام الشاشة',
                       'نوم 7-8 ساعات','تعرض للشمس يومياً'],
            'metabolism': (['بروتين في كل وجبة','توابل آمنة: كركم + قرفة + زنجبيل',
                            'مشي 30 دقيقة بعد الغداء','قم وتحرك 5 دقائق كل ساعة']
                           if goal in ["weight_loss","maintenance"] else
                           ['بروتين في كل وجبة (1.6-2.2 جم/كجم)','كارب حول التمرين',
                            'تدريب مقاومة 4-5 مرات أسبوعياً','نوم 7-9 ساعات']),
            'warnings': ['لا تخفض السعرات أكثر من المحدد','لو جعت: ماء أولاً ثم فاكهة',
                         'راجع مع أخصائي التغذية كل 4 أسابيع','أي أعراض غير عادية - راجع طبيبك'],
        },
        'clinic_name': 'NutraX Clinical Nutrition',
        'author': 'إعداد د. محمد - أخصائي التغذية الإكلينيكية',
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
# PAYMENT ROUTES (Stripe Integration)
# ═══════════════════════════════════════════════════════════════════

@app.route("/pricing")
def pricing():
    """صفحة عرض الأسعار - متاحة للجميع حتى بدون تسجيل دخول"""
    user = None
    user_currency = "EGP"
    active_access = None
    if "uid" in session:
        user = get_user_by_id(session["uid"])
        if user:
            user_currency = detect_currency(user.get("country"))
            try:
                active_access = get_user_access_info(session["uid"], db_row)
            except: pass
    return render_template("pricing.html",
                           user=user,
                           lang=session.get("lang", "ar"),
                           pricing=PRICING,
                           user_currency=user_currency,
                           active_access=active_access)


@app.route("/subscription-required")
@login_required
def subscription_required_page():
    """صفحة الـ paywall - بتظهر لما العميل يحاول يدخل حاجة محتاجة اشتراك"""
    user = get_user_by_id(session["uid"])
    reason_key = request.args.get("reason", "")
    reasons_map = {
        "chat": "محتاج اشتراك علشان تكلم د. محمد مباشرة في الشات.",
        "plan": "محتاج اشتراك أو خطة مدفوعة علشان تطلب خطة جديدة.",
    }
    reason = reasons_map.get(reason_key, "محتاج اشتراك علشان تستخدم الخدمة دي.")
    return render_template("subscription_required.html",
                           user=user, lang=session.get("lang", "ar"),
                           reason=reason, pricing=PRICING)


@app.route("/checkout/<plan_key>")
@login_required
def checkout(plan_key):
    """بدء جلسة دفع Stripe"""
    user = get_user_by_id(session["uid"])
    if not user:
        return redirect("/")

    # Validate plan
    if plan_key not in PRICING:
        return redirect("/pricing")

    # Get currency from query param or detect from country
    currency = request.args.get("currency", "").upper()
    if currency not in get_supported_currencies():
        currency = detect_currency(user.get("country"))

    try:
        checkout_session = create_checkout_session(user, plan_key, currency)
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        import traceback; traceback.print_exc()
        return render_template("payment_cancel.html",
                               user=user, lang=session.get("lang", "ar"),
                               error=f"خطأ في إنشاء جلسة الدفع: {str(e)}"), 500


@app.route("/payment/success")
@login_required
def payment_success():
    """صفحة نجاح الدفع - بتعرض تأكيد للعميل"""
    import stripe
    user = get_user_by_id(session["uid"])
    session_id = request.args.get("session_id", "")

    plan_name = None
    amount = None
    expires_at = None
    is_trial = False

    # Try to fetch session details from Stripe
    if session_id and os.environ.get("STRIPE_SECRET_KEY"):
        try:
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
            cs = stripe.checkout.Session.retrieve(session_id)
            metadata = cs.get("metadata", {}) or {}
            plan_key = metadata.get("plan_key", "")
            if plan_key in PRICING:
                plan_name = PRICING[plan_key]["name"]
            currency = metadata.get("currency", "USD")
            amt = cs.get("amount_total", 0)
            if amt:
                amount = f"{amt / 100:.0f} {currency}"
            if cs.get("subscription"):
                try:
                    sub = stripe.Subscription.retrieve(cs.subscription)
                    if sub.trial_end:
                        is_trial = True
                        from datetime import datetime as dt
                        expires_at = dt.fromtimestamp(sub.trial_end).strftime("%Y-%m-%d")
                except: pass
        except Exception as e:
            print(f"Stripe fetch error: {e}")

    # Fallback: check our DB
    if not plan_name:
        try:
            access = get_user_access_info(session["uid"], db_row)
            if access and access.get("has_access"):
                plan_name = access.get("plan_name")
                is_trial = access.get("is_trial", False)
                exp = access.get("expires_at")
                if exp:
                    expires_at = exp.strftime("%Y-%m-%d") if hasattr(exp, "strftime") else str(exp)[:10]
        except: pass

    return render_template("payment_success.html",
                           user=user, lang=session.get("lang", "ar"),
                           plan_name=plan_name, amount=amount,
                           expires_at=expires_at, is_trial=is_trial)


@app.route("/payment/cancel")
def payment_cancel():
    """صفحة إلغاء الدفع"""
    user = None
    if "uid" in session:
        user = get_user_by_id(session["uid"])
    return render_template("payment_cancel.html",
                           user=user, lang=session.get("lang", "ar"))


@app.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    """استقبال أحداث Stripe (الدفع نجح، اشتراك اتجدد، إلخ)"""
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")

    event = verify_webhook(payload, sig_header)
    if not event:
        return jsonify({"error": "Invalid signature"}), 400

    event_type = event.get("type") if isinstance(event, dict) else event["type"]
    data_obj = event["data"]["object"] if isinstance(event, dict) else event.data.object

    try:
        if event_type == "checkout.session.completed":
            handle_checkout_completed(data_obj, db_run, db_row)
        elif event_type == "invoice.payment_succeeded":
            handle_invoice_paid(data_obj, db_run, db_row)
        elif event_type in ("customer.subscription.updated", "customer.subscription.trial_will_end"):
            handle_subscription_updated(data_obj, db_run)
        elif event_type == "customer.subscription.deleted":
            handle_subscription_canceled(data_obj, db_run)
    except Exception as e:
        print(f"Webhook handler error: {e}")
        import traceback; traceback.print_exc()

    return jsonify({"status": "ok"}), 200


@app.route("/subscription/cancel", methods=["POST"])
@login_required
def cancel_subscription():
    """إلغاء الاشتراك (سيستمر حتى نهاية الفترة المدفوعة)"""
    success, msg = cancel_user_subscription(session["uid"], db_row, db_run)
    if success:
        return redirect("/my-plan?msg=" + msg)
    return redirect("/my-plan?error=" + msg)


# ═══════════════════════════════════════════════
# ADMIN PAYMENTS DASHBOARD
# ═══════════════════════════════════════════════

@app.route("/admin/payments")
@admin_required
def admin_payments_view():
    """لوحة admin لمتابعة كل المدفوعات والاشتراكات"""
    user = get_user_by_id(session["uid"])
    payments = []
    subscriptions = []
    try:
        payments = db_rows("""
            SELECT p.*, u.name as user_name, u.email as user_email 
            FROM payments p 
            LEFT JOIN users u ON p.user_id = u.id 
            ORDER BY p.created_at DESC LIMIT 200
        """)
    except: pass

    try:
        subscriptions = db_rows("""
            SELECT s.*, u.name as user_name, u.email as user_email 
            FROM subscriptions s 
            LEFT JOIN users u ON s.user_id = u.id 
            ORDER BY s.created_at DESC LIMIT 200
        """)
    except: pass

    # Compute stats
    stats = {
        "total_revenue": 0,
        "total_revenue_currency": None,
        "active_subscriptions": 0,
        "trialing_count": 0,
        "successful_payments": 0,
        "total_attempts": len(payments) if payments else 0,
        "paying_customers": 0,
        "total_users": 0,
    }

    try:
        # Sum all completed payments (note: simplification - mixed currencies)
        currencies_seen = set()
        for p in payments:
            if p.get("status") == "completed":
                stats["total_revenue"] += (p.get("amount") or 0)
                stats["successful_payments"] += 1
                if p.get("currency"):
                    currencies_seen.add(p["currency"])

        if len(currencies_seen) == 1:
            stats["total_revenue_currency"] = list(currencies_seen)[0]
        elif len(currencies_seen) > 1:
            stats["total_revenue_currency"] = "مختلط"

        # Active subscriptions
        from datetime import datetime as dt
        now = dt.now()
        unique_paying_users = set()

        for s in subscriptions:
            status = s.get("status", "")
            if status in ("active", "trialing"):
                stats["active_subscriptions"] += 1
                unique_paying_users.add(s.get("user_id"))
                if status == "trialing":
                    stats["trialing_count"] += 1

        for p in payments:
            if p.get("status") == "completed":
                unique_paying_users.add(p.get("user_id"))

        stats["paying_customers"] = len(unique_paying_users)

        # Total users
        r = db_row("SELECT COUNT(*) as cnt FROM users WHERE role='client' OR role IS NULL")
        stats["total_users"] = r.get("cnt", 0) if r else 0
    except Exception as e:
        print(f"Stats compute error: {e}")

    return render_template("admin_payments.html",
                           user=user, lang=session.get("lang", "ar"),
                           payments=payments, subscriptions=subscriptions,
                           stats=stats)


# ═══════════════════════════════════════════════
# UPDATE request_plan TO CHECK SUBSCRIPTION
# (Note: keeping old request_plan logic but adding gate)
# ═══════════════════════════════════════════════

@app.route("/check-access")
@login_required
def check_access_endpoint():
    """API endpoint للتحقق من حالة الاشتراك"""
    info = get_user_access_info(session["uid"], db_row)
    if info.get("expires_at") and hasattr(info["expires_at"], "isoformat"):
        info["expires_at"] = info["expires_at"].isoformat()
    return jsonify(info)


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

    # Parse JSON fields
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

    # BMI calculation
    bmi = None
    try:
        h = float(target_user.get("height") or 0)
        w = float(target_user.get("weight") or 0)
        if h > 0 and w > 0:
            bmi = w / ((h / 100) ** 2)
    except: pass

    # TDEE calculation (Mifflin-St Jeor)
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

    # Active subscription
    active_sub = None
    try:
        sub = db_row("""SELECT * FROM subscriptions 
                        WHERE user_id=? AND status IN ('active', 'trialing') 
                        ORDER BY current_period_end DESC LIMIT 1""", (uid,))
        if sub:
            active_sub = dict(sub)
            plan_info = PRICING.get(sub.get("plan_key"), {})
            active_sub["plan_name"] = plan_info.get("name", sub.get("plan_key"))
            # Format dates
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

    # Active one-time payment
    active_payment = None
    try:
        pay = db_row("""SELECT * FROM payments 
                        WHERE user_id=? AND status='completed' 
                        AND expires_at > ? 
                        ORDER BY expires_at DESC LIMIT 1""", (uid, datetime.now()))
        if pay:
            active_payment = dict(pay)
            plan_info = PRICING.get(pay.get("plan_key"), {})
            active_payment["plan_name"] = plan_info.get("name", pay.get("plan_key"))
            v = active_payment.get("expires_at")
            if v:
                active_payment["expires"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
    except: pass

    # Plan requests
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

    # Payments
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

    # Weight logs (with diff calculation)
    weight_logs = []
    try:
        logs = db_rows("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at DESC LIMIT 30", (uid,))
        prev = None
        # Process oldest first to calc diff
        logs_list = list(logs)
        for i, w in enumerate(logs_list):
            wd = dict(w)
            v = wd.get("logged_at")
            if v:
                wd["logged_date"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
            # Diff vs next (older)
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
        # شخصية
        name = request.form.get("name", "").strip() or target.get("name")
        email = request.form.get("email", "").strip().lower() or target.get("email")
        phone = request.form.get("phone", "").strip() or target.get("phone")
        country = request.form.get("country", "").strip() or target.get("country")
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip() or target.get("gender")

        # قياسات
        weight = request.form.get("weight", "").strip()
        height = request.form.get("height", "").strip()
        goal = request.form.get("goal", "").strip() or target.get("goal")
        activity = request.form.get("activity", "").strip()

        # طبية - JSON
        conditions = request.form.get("conditions", "[]")
        allergies = request.form.get("allergies", "[]")

        # تفضيلات - من textarea نحوّلهم لقايمة JSON
        liked_text = request.form.get("liked_foods_text", "").strip()
        disliked_text = request.form.get("disliked_foods_text", "").strip()

        def text_to_json(txt):
            if not txt:
                return "[]"
            items = [s.strip() for s in txt.replace("،", ",").replace(";", ",").split(",") if s.strip()]
            return json.dumps(items, ensure_ascii=False)

        liked_foods = text_to_json(liked_text)
        disliked_foods = text_to_json(disliked_text)

        # تحويل القيم الرقمية
        try: age_v = int(age) if age else target.get("age")
        except: age_v = target.get("age")
        try: weight_v = float(weight) if weight else target.get("weight")
        except: weight_v = target.get("weight")
        try: height_v = float(height) if height else target.get("height")
        except: height_v = target.get("height")
        try: activity_v = float(activity) if activity else target.get("activity")
        except: activity_v = target.get("activity")

        # حفظ
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

        # لو تغير الوزن، اعمل log جديد
        if weight and weight_v and float(weight_v) != (target.get("weight") or 0):
            try:
                db_run("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)", (uid, weight_v))
            except: pass
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"Update error: {e}")
    return redirect(f"/admin/users/{uid}?updated=1")


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
            # Update users table too
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

        # Validate plan
        if plan_key not in ("consultation", "single_plan", "monthly_subscription"):
            return redirect(f"/admin/users/{uid}?error=invalid_plan")

        # Validate amount
        try:
            amount_value = float(amount_raw or 0)
            amount_cents = int(amount_value * 100)
        except:
            amount_cents = 0

        # Plan duration
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

        # Build metadata
        metadata = {
            "manual_activation": True,
            "payment_method": payment_method,
            "method_name": method_name,
            "notes": notes,
            "activated_by_admin": session.get("uid"),
        }

        # Insert into payments table (one-time record - always)
        try:
            db_run("""INSERT INTO payments 
                      (user_id, stripe_session_id, plan_key, status, currency, amount, expires_at, metadata)
                      VALUES (?, ?, ?, 'completed', ?, ?, ?, ?)""",
                   (uid, f"manual_{uid}_{int(now.timestamp())}", plan_key,
                    currency, amount_cents, end_date, json.dumps(metadata, ensure_ascii=False)))
        except Exception as e:
            print(f"Insert payment error: {e}")

        # If subscription, also insert in subscriptions table
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

        # Send notification message to user
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
        # Check if user already has active access
        if has_active_access(uid, db_row):
            return redirect(f"/admin/users/{uid}")
        # Insert manual trial subscription
        now = datetime.now()
        trial_end = now + timedelta(days=7)
        db_run("""INSERT INTO subscriptions 
                  (user_id, plan_key, status, currency, amount,
                   current_period_start, current_period_end, trial_end,
                   stripe_subscription_id)
                  VALUES (?, 'monthly_subscription', 'trialing', 'EGP', 0, ?, ?, ?, ?)""",
               (uid, now, trial_end, trial_end, f"manual_trial_{uid}_{int(now.timestamp())}"))
        # Send notification message
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
        # Get active subscription
        sub = db_row("""SELECT * FROM subscriptions 
                        WHERE user_id=? AND status IN ('active', 'trialing') 
                        ORDER BY current_period_end DESC LIMIT 1""", (uid,))
        if sub:
            sub_id = sub.get("stripe_subscription_id", "")
            # If real Stripe subscription, cancel in Stripe
            if sub_id and not sub_id.startswith("manual_"):
                try:
                    import stripe as _stripe
                    _stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
                    _stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
                except Exception as e:
                    print(f"Stripe cancel error: {e}")
            # Update DB
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

# قائمة الـ endpoints اللي ما تتأثرش بالـ onboarding redirect
ONBOARDING_EXEMPT = {
    "login", "logout", "set_lang", "onboarding", "static",
    "stripe_webhook", "check_access_endpoint", "register"
}

@app.before_request
def check_onboarding_status():
    """Middleware: العملاء الجداد بيتحولوا للاستبيان تلقائياً"""
    # Skip for static files and exempt endpoints
    if not request.endpoint or request.endpoint in ONBOARDING_EXEMPT:
        return None
    if request.path.startswith("/static") or request.path.startswith("/webhook"):
        return None
    # Skip if not logged in
    if "uid" not in session:
        return None
    # Skip for admin/nutritionist
    try:
        user = get_user_by_id(session["uid"])
        if not user:
            return None
        if user.get("is_admin") or user.get("role") in ("admin", "nutritionist"):
            return None
        # Skip if already onboarded
        if user.get("onboarded_at"):
            return None
        # Client without onboarding -> redirect
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
            # Required - Account
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").lower().strip()
            password = request.form.get("password", "")
            phone = request.form.get("phone", "").strip()

            # Required - Personal
            country = request.form.get("country", "").strip()
            age = request.form.get("age", "").strip()
            gender = request.form.get("gender", "").strip()
            height = request.form.get("height", "").strip()
            weight = request.form.get("weight", "").strip()

            # Required - Goal
            goal = request.form.get("goal", "weight_loss").strip()
            activity = request.form.get("activity", "1.55").strip()

            # Optional
            liked_foods = request.form.get("liked_foods", "[]")
            disliked_foods = request.form.get("disliked_foods", "[]")
            allergies = request.form.get("allergies", "[]")
            conditions = request.form.get("conditions", "[]")

            # Validation
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

            # Check existing
            existing = db_row("SELECT id FROM users WHERE email=?", (email,))
            if existing:
                return render_template("register.html",
                                       lang=session.get("lang", "ar"),
                                       error="الإيميل ده مستخدم قبل كده - سجل دخول")

            # Convert numerics
            try: age_v = int(age)
            except: age_v = None
            try: height_v = float(height)
            except: height_v = None
            try: weight_v = float(weight)
            except: weight_v = None
            try: activity_v = float(activity)
            except: activity_v = 1.55

            # Insert user with everything
            db_run("""INSERT INTO users 
                      (name, email, password, country, age, gender, height, weight, 
                       goal, activity, phone, role, active,
                       liked_foods, disliked_foods, allergies, conditions, onboarded_at)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,'client',1,?,?,?,?,?)""",
                   (name, email, hp(password), country, age_v, gender,
                    height_v, weight_v, goal, activity_v, phone,
                    liked_foods, disliked_foods, allergies, conditions, datetime.now()))

            # Auto login - get the new user
            new_user = get_user(email, password)
            if new_user:
                session.permanent = True
                session["uid"] = new_user["id"]
                session["lang"] = "ar"
                session["role"] = "client"

                # Log initial weight
                try:
                    if weight_v:
                        db_run("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)",
                               (new_user["id"], weight_v))
                except: pass

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

    # Admin/Nutritionist shouldn't access onboarding
    if user.get("is_admin") or user.get("role") in ("admin", "nutritionist"):
        return redirect("/dashboard")

    if request.method == "POST":
        try:
            # Required fields
            age = request.form.get("age", "").strip()
            gender = request.form.get("gender", "").strip()
            height = request.form.get("height", "").strip()
            weight = request.form.get("weight", "").strip()
            goal = request.form.get("goal", "weight_loss").strip()
            activity = request.form.get("activity", "1.55").strip()

            # Optional fields
            liked_foods = request.form.get("liked_foods", "[]")
            disliked_foods = request.form.get("disliked_foods", "[]")
            conditions = request.form.get("conditions", "[]")
            allergies = request.form.get("allergies", "[]")

            # Validate required
            if not (age and gender and height and weight):
                return render_template("onboarding.html",
                                       user=user, lang=session.get("lang", "ar"),
                                       error="من فضلك املأ كل الحقول المطلوبة")

            # Save to users table
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

            # Log initial weight
            try:
                db_run("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)",
                       (session["uid"], float(weight)))
            except: pass

            return redirect("/dashboard?welcome=1")
        except Exception as e:
            import traceback; traceback.print_exc()
            return render_template("onboarding.html",
                                   user=user, lang=session.get("lang", "ar"),
                                   error=f"خطأ في الحفظ: {str(e)}")

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
    # Admin/staff goes to admin panel
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

        # Latest approved plan is "currently active"
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

            # Format date
            v = p.get("created_at")
            if v:
                p["created_date"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
            else:
                p["created_date"] = "-"

            plans_processed.append(p)

        active_count = sum(1 for p in plans_processed if p["is_currently_active"])
        archived_count = len(plans_processed) - active_count

        # Days following = days since first plan
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

    # Get plan info
    diet_type = plan_data.get("diet_plan_type", "standard")
    plan_info = get_diet_plan_info(diet_type)

    # Format created date
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
        # Just update the timestamp to make it the latest "active"
        # OR create a new request based on it
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

    # Store old data in session for prefilling
    try:
        session["prefill_data"] = json.loads(plan_req.get("request_data") or "{}")
    except: pass

    return redirect("/request-plan?edit=" + str(plan_id))


if __name__ == "__main__":
    app.run(debug=True)

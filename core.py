# -*- coding: utf-8 -*-
"""The pieces every part of NutraX needs: the app object, configuration,
security headers, the database layer, authentication, and the shared template
helpers.

Split out of app.py, which had grown to 4,700 lines holding routes,
permissions, the database, PDF generation, plan logic and notifications all at
once. Route modules import from here; nothing here imports a route module, so
there is no cycle.

`app` still lives here, so `gunicorn app:app` keeps working -- app.py imports
it back out.
"""

from flask import Flask, render_template, request, redirect, session, send_file, jsonify, Response
import hashlib, os, json, io, random, re, threading
from datetime import timedelta, datetime

app = Flask(__name__)

# ═══ حماية CSRF ═══
from flask_wtf import CSRFProtect
csrf = CSRFProtect(app)
from pdf_generator import pdf_bp
app.register_blueprint(pdf_bp)
# SECRET_KEY لازم يجي من متغير بيئة — لو مش موجود نولّد واحد عشوائي (الجلسات هتتقطع مع كل restart لحد ما تضيفه)
import secrets as _secrets
app.secret_key = os.environ.get("SECRET_KEY") or _secrets.token_hex(32)
if not os.environ.get("SECRET_KEY"):
    print("WARNING: SECRET_KEY env var not set — using a random key. Sessions will reset on every restart. Set SECRET_KEY in Render environment settings.")
app.permanent_session_lifetime = timedelta(days=30)

# ═══ هل ده سيرفر بيخدم ناس حقيقيين؟ ═══
# Render بيحط RENDER=true في كل السيرفسات، وممكن كمان تحط ENV=production بنفسك.
# محلياً الاتنين مش موجودين، فالإعدادات الصارمة مابتتفعّلش وبتقدر تشتغل على http.
IS_PRODUCTION = (os.environ.get("ENV", "").lower() == "production"
                 or os.environ.get("RENDER", "").lower() == "true")

# ═══ كوكي الجلسة ═══
# الجلسة عايشة 30 يوم على أجهزة فيها بيانات صحية، فلازم تتقفل:
#   Secure   — ماتتبعتش أبداً على http عادي (على البرودكشن بس، عشان التطوير المحلي)
#   SameSite — الكوكي ماتتبعتش مع طلبات جاية من مواقع تانية
#   HttpOnly — جافاسكريبت مش بتشوفها (متفعّلة أصلاً بشكل افتراضي في Flask)
app.config.update(
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
)

# ═══ تسريع الموقع ═══
import gzip as _gzip

@app.route("/.well-known/assetlinks.json")
def assetlinks():
    """ملف Digital Asset Links — بيربط تطبيق Google Play بالموقع (TWA).
    البصمة SHA256 بتتحط في متغير بيئة PLAY_SHA256 في Render لما تيجي من Play Console."""
    sha = os.environ.get("PLAY_SHA256", "").strip()
    package = os.environ.get("PLAY_PACKAGE", "com.nutrax.app").strip()
    if not sha:
        return jsonify([]), 200
    fingerprints = [f.strip().upper() for f in sha.split(",") if f.strip()]
    return jsonify([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {"namespace": "android_app", "package_name": package,
                   "sha256_cert_fingerprints": fingerprints}
    }]), 200


@app.route("/health")
def health():
    """نقطة خفيفة لخدمات الـ ping — بتمنع Render من تنييم الموقع"""
    return "ok", 200

@app.after_request
def speed_headers(resp):
    """① كاش طويل للملفات الثابتة  ② ضغط gzip للصفحات (بيوفر ~80% من الحجم)"""
    try:
        # كاش الملفات الثابتة أسبوع — ما عدا service worker لازم يفضل طازة
        if request.path.startswith("/static"):
            if request.path.endswith("sw.js"):
                resp.headers["Cache-Control"] = "no-cache"
            else:
                resp.headers["Cache-Control"] = "public, max-age=604800"
        # ضغط gzip للردود النصية
        if (resp.direct_passthrough
                or not (200 <= resp.status_code < 300)
                or "gzip" not in (request.headers.get("Accept-Encoding") or "").lower()
                or "Content-Encoding" in resp.headers):
            return resp
        ct = resp.content_type or ""
        if not any(t in ct for t in ("text/html", "text/css", "text/plain",
                                     "application/json", "application/javascript", "image/svg")):
            return resp
        data = resp.get_data()
        if len(data) < 500:
            return resp
        gz = _gzip.compress(data, 6)
        if len(gz) < len(data):
            resp.set_data(gz)
            resp.headers["Content-Encoding"] = "gzip"
            resp.headers["Content-Length"] = str(len(gz))
            resp.headers["Vary"] = "Accept-Encoding"
    except Exception as _e:
        print(f"speed headers error: {_e}")
    return resp


# ═══════════════════════════════════════════════
# SECURITY HEADERS
# ═══════════════════════════════════════════════
# The allowlist below is derived from what the templates actually load. If you
# add a CDN, a font host or an image source, add it here or the browser will
# block it.
#
# 'unsafe-inline' is present for script-src because the pages are built around
# inline <script> blocks and onclick handlers; removing it means refactoring
# every template first. It is still worth shipping: the other directives close
# off framing, plugin embedding, base-tag hijacking and form exfiltration, and
# they narrow which hosts can serve script at all.
CSP = "; ".join([
    "default-src 'self'",
    # cdnjs -> Font Awesome, jsdelivr -> Chart.js
    "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
    "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:",
    # unsplash -> knowledge-hub article images
    "img-src 'self' data: blob: https://images.unsplash.com",
    # openfoodfacts -> the analyzer's barcode lookup
    "connect-src 'self' https://world.openfoodfacts.org",
    "frame-src https://www.youtube.com https://www.youtube-nocookie.com",
    "frame-ancestors 'none'",       # nobody may frame us -- clickjacking
    "base-uri 'self'",              # no injected <base> to hijack relative URLs
    "form-action 'self'",           # forms cannot post to another origin
    "object-src 'none'",            # no plugins
])


@app.after_request
def security_headers(resp):
    try:
        resp.headers.setdefault("Content-Security-Policy", CSP)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()")
        # only meaningful over TLS, and Render terminates TLS for us
        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            resp.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains")
    except Exception as _e:
        print(f"security headers error: {_e}")
    return resp


from meal_database import (
    get_meal_pool, get_snacks_for_goal, filter_by_conditions,
    get_diet_plan_info, DIET_PLAN_TYPES,
    WEIGHT_LOSS, MUSCLE_GAIN, BULKING, MAINTENANCE,
    get_nutrient_boost_notes, translate_boost_note
)
from meal_i18n import translate_meal, translate_guidance
import food_data

# دمج الوجبات الإضافية (ملف meal_extra) لو موجود — بيزوّد التنوّع من غير ما يلمس meal_database
try:
    import meal_extra
    meal_extra.apply()
except Exception as _e:
    print(f"meal_extra apply error: {_e}")

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
    get_supported_currencies, STRIPE_PUBLIC_KEY,
    send_renewal_reminders, build_admin_analytics
)

# ═══════════════════════════════════════════════
# DEVELOPER API PLATFORM (منتج SaaS منفصل - اشتراك شهري لمطورين تانيين)
# ═══════════════════════════════════════════════
from api_platform import (
    ensure_api_table, API_TIERS, make_require_api_key,
    get_or_create_api_key, regenerate_api_key, get_usage_info,
    create_api_checkout_session, handle_api_checkout_completed,
    handle_api_invoice_paid, handle_api_subscription_updated,
    handle_api_subscription_canceled,
)

# ═══════════════════════════════════════════════
# NOTIFICATIONS MODULE (إشعارات الأدمن)
# ═══════════════════════════════════════════════
from notifications import (
    add_notification, get_unread_count, get_all_notifications,
    mark_all_read, mark_read, get_type_meta,
    ensure_table as ensure_notif_table,
    send_plan_pdf_email
)

# ═══════════════════════════════════════════════
# PUSH NOTIFICATIONS (إشعارات الموبايل - Web Push)
# ═══════════════════════════════════════════════
from push import push_bp, push_to_staff, push_to_user
app.register_blueprint(push_bp)

# نلفّ add_notification عشان كل إشعار يتبعت كمان كـ Push للموبايل
_base_add_notification = add_notification
def add_notification(db_run, type_, title, message, link=None, related_user_id=None):
    _base_add_notification(db_run, type_, title, message, link=link, related_user_id=related_user_id)
    try:
        push_to_staff(title, message, link or "/admin/notifications")
    except Exception as _e:
        print(f"push send error: {_e}")

DATABASE_URL = os.environ.get("DATABASE_URL")

# ═══ من غير DATABASE_URL بنقع على SQLite في /tmp ═══
# على Render، /tmp بيتمسح مع كل restart. يعني الموقع يفضل "شغال"، يقبل عملاء
# جدد وخطط جديدة، وكل ده يروح مع أول إعادة تشغيل من غير ولا رسالة خطأ.
# فشل واضح وصريح أحسن ألف مرة من ضياع صامت للبيانات.
if IS_PRODUCTION and not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set while running in production. Refusing to start: "
        "the app would fall back to SQLite in /tmp, which Render wipes on every "
        "restart, and every client and plan written would be lost without a trace. "
        "Set DATABASE_URL in the service's environment settings and redeploy."
    )

if DATABASE_URL:
    import psycopg2, psycopg2.extras, psycopg2.pool
    # ═══ مخزن اتصالات: بنفتح الاتصال مرة ونعيد استخدامه بدل اتصال جديد لكل استعلام ═══
    _pg_pool = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=20, dsn=DATABASE_URL)

    def _pool_exec(sql, params, fetch):
        """ينفّذ الاستعلام باتصال من المخزن، ولو الاتصال باظ (قطع شبكة مثلاً) يجرب باتصال جديد"""
        last_err = None
        for attempt in range(2):
            conn = _pg_pool.getconn()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    if fetch == "one":
                        result = cur.fetchone()
                    elif fetch == "all":
                        result = cur.fetchall()
                    else:
                        result = None
                conn.commit()
                _pg_pool.putconn(conn)
                return result
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # اتصال بايظ — نتخلص منه ونحاول تاني باتصال جديد
                last_err = e
                try: _pg_pool.putconn(conn, close=True)
                except Exception: pass
            except Exception:
                try:
                    conn.rollback()
                    _pg_pool.putconn(conn)
                except Exception:
                    try: _pg_pool.putconn(conn, close=True)
                    except Exception: pass
                raise
        raise last_err

    def db_row(sql, params=()):
        return _pool_exec(sql.replace("?", "%s"), params, "one")
    def db_rows(sql, params=()):
        return _pool_exec(sql.replace("?", "%s"), params, "all")
    def db_run(sql, params=(), commit=True):
        _pool_exec(sql.replace("?", "%s"), params, None)
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

from werkzeug.security import generate_password_hash, check_password_hash

def hp(p):
    """تشفير الباسورد بطريقة آمنة (scrypt/pbkdf2 مع salt)"""
    return generate_password_hash(p)

def _legacy_hp(p):
    """الطريقة القديمة (SHA-256 بدون salt) — للتوافق مع الحسابات القديمة فقط"""
    return hashlib.sha256(p.encode()).hexdigest()

def verify_password(stored_hash, pw):
    """يتحقق من الباسورد: يجرب الطريقة الآمنة أولاً، ثم القديمة للحسابات المسجلة قبل التحديث"""
    if not stored_hash:
        return False
    try:
        if check_password_hash(stored_hash, pw):
            return True
    except Exception:
        pass
    # هاش قديم؟ (64 حرف hex = SHA-256)
    if len(stored_hash) == 64 and stored_hash == _legacy_hp(pw):
        return True
    return False

@app.template_global('t')
def t(ar, en):
    """ترجمة سريعة داخل القوالب: {{ t('عربي', 'English') }} — بتقرأ اللغة من الجلسة مباشرة."""
    try:
        return ar if session.get("lang", "ar") == "ar" else en
    except Exception:
        return ar

def log_error(where, exc, critical=False):
    """Record a caught exception instead of losing it.

    app.py catches a lot, and most of those handlers are correct fallbacks.
    The dangerous ones are where a failure changes what a patient is served or
    whether their data is saved -- those go through here so the failure shows
    up in the Render logs instead of running wrong in silence. Grep for
    NUTRAX-ERROR (or NUTRAX-CRITICAL) to find them.
    """
    tag = "NUTRAX-CRITICAL" if critical else "NUTRAX-ERROR"
    print(f"[{tag}] {where}: {type(exc).__name__}: {exc}", flush=True)


def cur_lang():
    """The session language, or Arabic outside a request (background threads)."""
    try:
        return session.get("lang", "ar")
    except Exception:
        return "ar"


# The medical conditions the plan forms offer. The Arabic side is what gets
# stored (and what UNSAFE_FOODS / filter_by_conditions match against), so these
# are display-only translations.
ENGLISH_CONDITIONS = {
    "قولون عصبي": "IBS",
    "سكري النوع الثاني": "Type 2 Diabetes",
    "سكري النوع الاول": "Type 1 Diabetes",
    "سكري": "Diabetes",
    "ضغط الدم المرتفع": "High Blood Pressure",
    "ضغط": "High Blood Pressure",
    "امراض القلب": "Heart Disease",
    "الفشل الكلوي المزمن": "Chronic Kidney Failure",
    "الحمل": "Pregnancy",
    "الرضاعة الطبيعية": "Breastfeeding",
    "السمنة": "Obesity",
    "G6PD": "G6PD",
    "ثلاسيميا": "Thalassemia",
    "نقص الحديد": "Iron Deficiency",
    "نقص فيتامين D3": "Vitamin D3 Deficiency",
    "حرق بطيء": "Slow Metabolism",
    "امساك مزمن": "Chronic Constipation",
    "حساسية اللاكتوز": "Lactose Intolerance",
    "الداء الزلاقي": "Celiac Disease",
    "الكبد الدهني": "Fatty Liver",
    "حصوات المرارة": "Gallstones",
    "التهاب الأمعاء": "IBD (Crohn's/Colitis)",
    "اضطراب في الأكل": "Eating Disorder",
    "هشاشة العظام": "Osteoporosis",
    "الوقاية من السرطان": "Cancer Risk Reduction",
}


@app.template_filter('cond_en')
def cond_en_filter(name):
    """A stored condition name, in the reader's language."""
    if cur_lang() == "ar":
        return name
    return ENGLISH_CONDITIONS.get((name or "").strip(), name)


@app.template_filter('culture_en')
def culture_en_filter(name):
    """A stored cuisine name, in the reader's language."""
    if cur_lang() == "ar":
        return name
    return _CULTURE_EN.get((name or "").strip(), name)


ENGLISH_DAYS = {
    "الاحد": "Sunday", "الأحد": "Sunday", "الاثنين": "Monday",
    "الثلاثاء": "Tuesday", "الاربعاء": "Wednesday", "الأربعاء": "Wednesday",
    "الخميس": "Thursday", "الجمعة": "Friday", "السبت": "Saturday",
}
# stored values are Arabic; these render them in English where needed
_CULTURE_EN = {
    "مصري": "Egyptian", "خليجي": "Gulf", "شامي": "Levantine",
    "مغربي": "Moroccan", "عالمي": "International",
}
_GENDER_EN = {
    "ذكر": "Male", "أنثى": "Female", "انثى": "Female",
    "male": "Male", "female": "Female",
}


@app.template_filter('meal_en')
def meal_en(text):
    """Render a stored meal string in the session language.

    Meals are stored in Arabic on purpose -- filter_by_conditions matches
    Arabic substrings against UNSAFE_FOODS, so the stored text has to stay
    Arabic for the safety filtering to work. Translation happens here, on the
    way to the page.
    """
    try:
        if session.get("lang", "ar") == "ar":
            return text
        return translate_meal(text)
    except Exception:
        return text


@app.template_filter('day_en')
def day_en(name):
    """Weekday names come out of the generator in Arabic."""
    try:
        if session.get("lang", "ar") == "ar":
            return name
        return ENGLISH_DAYS.get((name or "").strip(), name)
    except Exception:
        return name


@app.template_filter('from_json')
def from_json_filter(s):
    if not s: return {}
    try: return json.loads(s)
    except: return {}
@app.template_filter('measures')
def measures_filter(s):
    try:
        from measures import annotate
        return annotate(s or "")
    except Exception:
        return s
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
            """CREATE TABLE IF NOT EXISTS meal_checks (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, check_date DATE NOT NULL, meal_key TEXT NOT NULL, UNIQUE(user_id, check_date, meal_key))""",
            """CREATE TABLE IF NOT EXISTS meal_reminders_sent (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, check_date DATE NOT NULL, meal_key TEXT NOT NULL, UNIQUE(user_id, check_date, meal_key))""",
            """CREATE TABLE IF NOT EXISTS weekly_summary_sent (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, week_key TEXT NOT NULL, UNIQUE(user_id, week_key))""",
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
            """CREATE TABLE IF NOT EXISTS meal_checks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, check_date DATE NOT NULL, meal_key TEXT NOT NULL, UNIQUE(user_id, check_date, meal_key))""",
            """CREATE TABLE IF NOT EXISTS meal_reminders_sent (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, check_date DATE NOT NULL, meal_key TEXT NOT NULL, UNIQUE(user_id, check_date, meal_key))""",
            """CREATE TABLE IF NOT EXISTS weekly_summary_sent (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, week_key TEXT NOT NULL, UNIQUE(user_id, week_key))""",
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
        "ALTER TABLE users ADD COLUMN lifestyle_data TEXT",
        "ALTER TABLE subscriptions ADD COLUMN reminder_sent INTEGER DEFAULT 0",
        "ALTER TABLE payments ADD COLUMN reminder_sent INTEGER DEFAULT 0",
    ]:
        try: db_run(col_sql)
        except: pass

    # حساب الأدمن: يتعمل مرة واحدة فقط من متغير بيئة — ولا يتم إعادة تعيين الباسورد أبداً
    admin = db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")
    _admin_pw = os.environ.get("ADMIN_PASSWORD")
    if not admin:
        if _admin_pw:
            db_run("INSERT INTO users (name,email,password,is_admin,role,active) VALUES (?,?,?,1,'admin',1)", ("Admin","admin@nutrax.com",hp(_admin_pw)))
        else:
            print("WARNING: no admin account exists. Set ADMIN_PASSWORD env var and restart to create one.")
    elif _admin_pw:
        # ترحيل لمرة واحدة: لو الأدمن لسه باسورده هو الباسورد القديم المكشوف على GitHub (بأي صيغة تشفير)، نستبدله.
        # أول ما يتغير، الشرط مبيتحققش تاني ومفيش أي لمس للباسورد بعدها.
        _cur = db_row("SELECT password FROM users WHERE email='admin@nutrax.com'")
        if _cur and verify_password(_cur.get("password"), "nutrax2025"):
            db_run("UPDATE users SET password=? WHERE email='admin@nutrax.com'", (hp(_admin_pw),))
            print("admin password migrated away from compromised default.")

init_db()

# ── جدول الإشعارات (يتعمل مرة واحدة عند التشغيل) ──
try:
    ensure_notif_table(db_run, is_postgres=bool(DATABASE_URL))
except Exception as _e:
    print(f"notif table init error: {_e}")

# ── جدول مفاتيح الـ API (منتج المطورين) ──
try:
    ensure_api_table(db_run, is_postgres=bool(DATABASE_URL))
except Exception as _e:
    print(f"api_keys table init error: {_e}")
require_api_key = make_require_api_key(db_row, db_run)

# ── تذكير تجديد الاشتراك: فحص دوري في الخلفية كل 12 ساعة ──
def _renewal_reminders_loop():
    import time
    while True:
        try:
            send_renewal_reminders(db_run, db_rows, push_to_user)
        except Exception as e:
            print(f"[reminders] loop error: {e}")
        time.sleep(12 * 3600)

threading.Thread(target=_renewal_reminders_loop, daemon=True).start()

def get_user(email, pw):
    u = db_row("SELECT * FROM users WHERE email=?", (email,))
    if not u or not verify_password(u.get("password"), pw):
        return None
    # ترقية تلقائية: لو الحساب لسه بالهاش القديم، نحدثه للطريقة الآمنة
    if len(u.get("password") or "") == 64:
        try:
            db_run("UPDATE users SET password=? WHERE id=?", (hp(pw), u["id"]))
        except Exception as _e:
            print(f"hash upgrade error: {_e}")
    return u
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
        if "uid" not in session: return redirect("/login")
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session: return redirect("/login")
        u = get_user_by_id(session["uid"])
        if not u or (u.get("role") != "admin" and not u.get("is_admin")):
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return decorated

def staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session: return redirect("/login")
        u = get_user_by_id(session["uid"])
        if not u or (u.get("role") not in ["admin", "nutritionist"] and not u.get("is_admin")):
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
            return redirect("/login")
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
    {"icon": "💧", "title": "اشرب المياه", "tip": "اشرب كوب ماء فاتر مع نصف ليمونة على الريق - يحفز الهضم",
     "title_en": "Drink water", "tip_en": "A cup of warm water with half a lemon on an empty stomach gets digestion going"},
    {"icon": "🚶", "title": "تمشى شوية", "tip": "30 دقيقة مشي بعد الغداء ينظم السكر ويساعد على الهضم",
     "title_en": "Take a walk", "tip_en": "A 30-minute walk after lunch steadies your blood sugar and helps digestion"},
    {"icon": "😴", "title": "نام كويس", "tip": "النوم 7-8 ساعات مهم زي الأكل والتمرين للوزن الصحي",
     "title_en": "Sleep well", "tip_en": "7-8 hours of sleep matters as much as food and training for a healthy weight"},
    {"icon": "🍎", "title": "فاكهة بدل الحلويات", "tip": "لو حسيت برغبة في حاجة حلوة، خد فاكهة بدل البسكويت",
     "title_en": "Fruit instead of sweets", "tip_en": "When you crave something sweet, reach for fruit instead of biscuits"},
    {"icon": "🥗", "title": "خضار في كل وجبة", "tip": "حط نصف الطبق خضار - شبع أكتر وسعرات أقل",
     "title_en": "Vegetables at every meal", "tip_en": "Fill half the plate with vegetables - fuller for fewer calories"},
    {"icon": "⏰", "title": "متاكلش بسرعة", "tip": "مضغ الأكل ببطء يخليك تشبع أسرع وتاكل أقل",
     "title_en": "Do not rush your food", "tip_en": "Chewing slowly makes you feel full sooner, so you eat less"},
    {"icon": "🧂", "title": "قلل الملح", "tip": "الأكل الجاهز فيه ملح كتير - حضر أكلك في البيت",
     "title_en": "Cut back on salt", "tip_en": "Ready-made food is heavy on salt - cook at home"},
]

CONDITION_TIPS = {
    "قولون": [
        {"icon": "⚠️", "title": "خلي بالك من القولون", "tip": "تجنب الفول والحمص والكرنب والبروكلي - بتعمل غازات",
     "title_en": "Mind your gut", "tip_en": "Skip fava beans, chickpeas, cabbage and broccoli - they cause gas"},
        {"icon": "🌶️", "title": "بعيداً عن الحار", "tip": "تجنب الفلفل الحار والبهارات الحارة - بتهيج القولون",
     "title_en": "Stay off the spice", "tip_en": "Avoid chilli and hot spices - they irritate the gut"},
        {"icon": "☕", "title": "قلل الكافيين", "tip": "القهوة والشاي بكميات كبيرة بتزود اضطراب القولون",
     "title_en": "Less caffeine", "tip_en": "Large amounts of coffee and tea make gut trouble worse"},
    ],
    "سكري": [
        {"icon": "🍞", "title": "خد بالك من الكارب", "tip": "ابعد عن الأرز الأبيض والخبز الأبيض - الأسمر أفضل",
     "title_en": "Watch the carbs", "tip_en": "Stay away from white rice and white bread - wholemeal is better"},
        {"icon": "🍯", "title": "السكر عدو", "tip": "تجنب السكر المضاف، العسل، والعصائر المحلاة",
     "title_en": "Sugar is the enemy", "tip_en": "Avoid added sugar, honey and sweetened juice"},
        {"icon": "📊", "title": "اقيس السكر", "tip": "قيس السكر قبل الفطار وبعد الأكل بساعتين",
     "title_en": "Check your blood sugar", "tip_en": "Measure before breakfast and 2 hours after eating"},
    ],
    "ضغط": [
        {"icon": "🧂", "title": "ملح أقل", "tip": "تجنب المخللات والصوصات الجاهزة والشاورما",
     "title_en": "Less salt", "tip_en": "Avoid pickles, ready-made sauces and shawarma"},
        {"icon": "🥬", "title": "خضار ورقية", "tip": "السبانخ والجرجير والبقدونس بيخفضوا الضغط",
     "title_en": "Leafy greens", "tip_en": "Spinach, rocket and parsley help bring blood pressure down"},
        {"icon": "🚫", "title": "ابعد عن المعلبات", "tip": "الأكل المعلب فيه ملح كتير جداً",
     "title_en": "Skip tinned food", "tip_en": "Tinned food carries a great deal of salt"},
    ],
    "كلوي": [
        {"icon": "💧", "title": "اشرب باعتدال", "tip": "اتبع تعليمات الدكتور بخصوص كمية المياه",
     "title_en": "Drink in moderation", "tip_en": "Follow your doctor's instructions on how much water to drink"},
        {"icon": "🍌", "title": "احذر البوتاسيوم", "tip": "قلل من الموز والطماطم والبطاطا والمكسرات",
     "title_en": "Careful with potassium", "tip_en": "Go easy on banana, tomato, potato and nuts"},
        {"icon": "🥩", "title": "بروتين معتدل", "tip": "كميات قليلة من البروتين الحيواني",
     "title_en": "Moderate protein", "tip_en": "Small amounts of animal protein"},
    ],
    "قلب": [
        {"icon": "🐟", "title": "أوميجا 3", "tip": "السمك مرتين في الأسبوع - السلمون والسردين أفضل",
     "title_en": "Omega 3", "tip_en": "Fish twice a week - salmon and sardines are best"},
        {"icon": "🥑", "title": "دهون صحية", "tip": "زيت الزيتون والأفوكادو بدل السمن والزبدة",
     "title_en": "Healthy fats", "tip_en": "Olive oil and avocado instead of ghee and butter"},
        {"icon": "🚭", "title": "قلل الملح", "tip": "الملح يرفع الضغط ويهد القلب",
     "title_en": "Cut back on salt", "tip_en": "Salt raises blood pressure and strains the heart"},
    ],
    "حامل": [
        {"icon": "🤰", "title": "حمض الفوليك", "tip": "السبانخ والبروكلي والعدس مهمين جداً للحمل",
     "title_en": "Folic acid", "tip_en": "Spinach, broccoli and lentils matter a great deal in pregnancy"},
        {"icon": "🥛", "title": "كالسيوم يومياً", "tip": "اللبن والزبادي والجبن لعظام الجنين",
     "title_en": "Calcium every day", "tip_en": "Milk, yogurt and cheese for the baby's bones"},
        {"icon": "🚫", "title": "تجنبي", "tip": "الكبدة، السمك النيء، والكافيين الكتير",
     "title_en": "Things to avoid", "tip_en": "Liver, raw fish and too much caffeine"},
    ],
    "g6pd": [
        {"icon": "🚫", "title": "ابعد عن الفول", "tip": "تجنب الفول، الحمص، اللوبيا والبقوليات الحمراء",
     "title_en": "Avoid fava beans", "tip_en": "Skip fava beans, chickpeas, black-eyed peas and red legumes"},
        {"icon": "💊", "title": "احذر الأدوية", "tip": "بعض الأدوية ممنوعة - استشر الدكتور قبل أي علاج",
     "title_en": "Careful with medicines", "tip_en": "Some medicines are off limits - ask your doctor before any treatment"},
        {"icon": "🌿", "title": "أعشاب آمنة", "tip": "تجنب الحناء والكافور وبعض الأعشاب",
     "title_en": "Safe herbs", "tip_en": "Avoid henna, camphor and certain herbs"},
    ],
    "ثلاسيميا": [
        {"icon": "🚫", "title": "قلل الحديد", "tip": "ابعد عن الكبدة واللحوم الحمراء بكميات كبيرة",
     "title_en": "Less iron", "tip_en": "Go easy on liver and large amounts of red meat"},
        {"icon": "☕", "title": "شاي مع الأكل", "tip": "الشاي يقلل امتصاص الحديد - اشربه مع الأكل",
     "title_en": "Tea with meals", "tip_en": "Tea lowers iron absorption - drink it with your food"},
        {"icon": "🥬", "title": "خضار آمنة", "tip": "البروكلي والكرنب والجزر مفيدين",
     "title_en": "Safe vegetables", "tip_en": "Broccoli, cabbage and carrots are good for you"},
    ],
    "لاكتوز": [
        {"icon": "🥛", "title": "ابعد عن الألبان", "tip": "تجنب الحليب والزبادي والجبن الطازج",
     "title_en": "Avoid dairy", "tip_en": "Skip milk, yogurt and fresh cheese"},
        {"icon": "🌱", "title": "بدائل نباتية", "tip": "حليب اللوز والصويا وجوز الهند بدائل ممتازة",
     "title_en": "Plant-based alternatives", "tip_en": "Almond, soy and coconut milk are excellent substitutes"},
        {"icon": "💊", "title": "أنزيم اللاكتيز", "tip": "ممكن تاخده قبل الأكل لو مضطر تاكل لبن",
     "title_en": "Lactase enzyme", "tip_en": "You can take it before eating if you have to have dairy"},
    ],
}

def _plan_name(plan_info, fallback=None):
    """The pricing plan's name in the reader's language."""
    if cur_lang() != "ar":
        en = (plan_info or {}).get("name_en")
        if en:
            return en
    return (plan_info or {}).get("name", fallback)


def _localize_tips(tips):
    """Swap in the English title/text when the session is in English.

    Returns copies: the module-level tip dicts are shared across requests and
    must not be mutated.
    """
    if cur_lang() == "ar":
        return tips
    return [dict(t, title=t.get("title_en") or t["title"],
                 tip=t.get("tip_en") or t["tip"]) for t in tips]


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

    return _localize_tips(tips)


def is_email_blocked(email):
    """Check if email is in blocked list - safe if table missing"""
    if not email: return False
    try:
        row = db_row("SELECT id FROM blocked_users WHERE email=?", (email.lower().strip(),))
        return row is not None
    except Exception:
        return False

# ═══ حماية تسجيل الدخول من محاولات التخمين المتكررة (Brute-force) ═══
# ملاحظة: تخزين في الذاكرة — يشتغل صح طول ما السيرفر عامل بـ worker واحد (وضع Render الحالي).
# لو زاد عدد الـ workers مستقبلاً، لازم ينتقل التخزين لقاعدة البيانات أو Redis.
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 15 * 60
import time as _time
_login_attempts = {}

def _is_login_rate_limited(email):
    if not email: return False
    now = _time.time()
    attempts = [t for t in _login_attempts.get(email, []) if now - t < _LOGIN_WINDOW_SECONDS]
    _login_attempts[email] = attempts
    return len(attempts) >= _LOGIN_MAX_ATTEMPTS

def _record_failed_login(email):
    if not email: return
    _login_attempts.setdefault(email, []).append(_time.time())

def _clear_login_attempts(email):
    _login_attempts.pop(email, None)

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
    ctx = {"unread_messages": 0, "pending_count": 0, "active_access": None, "notif_unread": 0}
    if "uid" in session:
        try:
            ctx["unread_messages"] = get_unread_messages_count(session["uid"])
            user = get_user_by_id(session["uid"])
            if user and (user.get("is_admin") or user.get("role") in ["admin", "nutritionist"]):
                ctx["pending_count"] = get_pending_requests_count()
                # عدد الإشعارات غير المقروءة (للجرس الأحمر في الـ navbar)
                try:
                    ctx["notif_unread"] = get_unread_count(db_row)
                except: pass
            # Get active access info for all users
            try:
                ctx["active_access"] = get_user_access_info(session["uid"], db_row, cur_lang())
            except: pass
        except: pass
    return ctx


# رسائل صفحة الدخول/التسجيل بالعربي والإنجليزي
_LOGIN_MSGS = {
    "blocked":      ("هذا الحساب محظور. تواصل مع الإدارة.",
                     "This account is blocked. Please contact support."),
    "rate_limited": ("محاولات دخول كتير غلط على الحساب ده. حاول تاني بعد 15 دقيقة.",
                     "Too many failed login attempts for this account. Try again in 15 minutes."),
    "inactive":     ("هذا الحساب غير مفعل. تواصل مع الإدارة.",
                     "This account is not active. Please contact support."),
    "bad_creds":    ("البريد او كلمة المرور غير صحيحة",
                     "Incorrect email or password"),
    "all_required": ("كل البيانات مطلوبة",
                     "All fields are required"),
    "pw_short":     ("كلمة السر لازم 6 أحرف على الأقل",
                     "Password must be at least 6 characters"),
    "registered":   ("تم التسجيل بنجاح! سجل دخولك دلوقتي.",
                     "Registered successfully! You can sign in now."),
    "email_taken":  ("البريد الإلكتروني مستخدم بالفعل",
                     "This email is already registered"),
}

def _login_msg(key, lang):
    ar, en = _LOGIN_MSGS[key]
    return ar if (lang or "ar") == "ar" else en

# ═══════════════════════════════════════════════
# The canonical origin, used by canonical tags and the sitemap.
# Set DOMAIN in the environment to move it to a custom domain.
# ═══════════════════════════════════════════════
@app.template_global('site_origin')
def site_origin():
    from api_platform import DOMAIN as _D
    return (_D or "").rstrip("/")

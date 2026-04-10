# ===============================
# NUTRAX V2 - PRO SYSTEM
# ===============================

import streamlit as st
import sqlite3
# ===============================
# DATABASE CONNECTION & AUTO-REPAIR
# ===============================
import os

DB_FILE = "nutrax_v2.db"

# محاولة إصلاح قاعدة البيانات تلقائياً لو كانت تالفة
def init_db():
    global conn, c
    try:
        # نحاول نعمل كويري بسيط عشان نختبر صحة الملف
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT count(*) FROM users")
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        # لو في أي خطأ (ملف تالف)، نمسحه ونعمل جديد
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            print("Database was corrupted, deleted and recreating...")
        
        # نعيد المحاولة بعد المسح
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()

    # ===========================================
    # إنشاء الجداول (Safe Mode)
    # ===========================================
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        name TEXT,
        birth_year INTEGER,
        height REAL,
        weight REAL,
        goal TEXT DEFAULT 'maintain',
        is_admin INTEGER DEFAULT 0,
        join_date TEXT DEFAULT datetime('now')
    )
    """)

    c.execute("CREATE TABLE IF NOT EXISTS meals (id INTEGER PRIMARY KEY, name TEXT, calories INTEGER, protein REAL, carbs REAL, fat REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS tracking (id INTEGER PRIMARY KEY, user_id INTEGER, weight REAL, date TEXT)")

    # ===========================================
    # تحديث الجدول بأمان (Migration)
    # ===========================================
    try:
        c.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN birth_year INTEGER")
    except: pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN height REAL")
    except: pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN weight REAL")
    except: pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN goal TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN join_date TEXT")
    except: pass
    
    conn.commit()

# تشغيل دالة الإعداد
init_db()

# ===========================================
# إنشاء الأدمن (مرة واحدة فقط)
# ===========================================
def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users (email, password, name, is_admin) VALUES (?, ?, ?, ?)",
              ("admin@nutrax.com", hash_pass("admin123"), "Super Admin", 1))
    conn.commit()
    is_admin INTEGER DEFAULT 0,
    join_date TEXT DEFAULT datetime('now')
)
""")

# جداول الأكل والتتبع
c.execute("CREATE TABLE IF NOT EXISTS meals (id INTEGER PRIMARY KEY, name TEXT, calories INTEGER, protein REAL, carbs REAL, fat REAL)")
c.execute("CREATE TABLE IF NOT EXISTS tracking (id INTEGER PRIMARY KEY, user_id INTEGER, weight REAL, date TEXT)")

# تحديث الجدول تلقائياً لو كان قديم (Migration)
try:
    c.execute("ALTER TABLE users ADD COLUMN name TEXT")
    c.execute("ALTER TABLE users ADD COLUMN birth_year INTEGER")
    c.execute("ALTER TABLE users ADD COLUMN height REAL")
    c.execute("ALTER TABLE users ADD COLUMN weight REAL")
    c.execute("ALTER TABLE users ADD COLUMN goal TEXT")
    c.execute("ALTER TABLE users ADD COLUMN join_date TEXT")
except:
    pass # الأعمدة موجودة بالفعل
conn.commit()

# إنشاء أدمن افتراضي
def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users (email, password, name, is_admin) VALUES (?, ?, ?, ?)",
              ("admin@nutrax.com", hash_pass("admin123"), "Super Admin", 1))
    conn.commit()

# ===============================
# EXPANDED DATABASE (LOCAL_DB)
# ===============================
LOCAL_DB = {
    # فواكه وخضار (من السابق)
    "apple": {"name_ar": "تفاح أحمر", "cal": 52, "p": 0.3, "c": 14, "f": 0.2},
    "banana": {"name_ar": "موز", "cal": 89, "p": 1.1, "c": 23, "f": 0.3},
    "orange": {"name_ar": "برتقال", "cal": 47, "p": 0.9, "c": 12, "f": 0.1},
    "broccoli": {"name_ar": "بروكلي", "cal": 34, "p": 2.8, "c": 7, "f": 0.4},
    "spinach": {"name_ar": "سبانخ", "cal": 23, "p": 2.9, "c": 3.6, "f": 0.4},
    
    # بروتينات حيوانية (لحوم ودجاج متنوعة)
    "chicken breast": {"name_ar": "صدر دجاج مشوي", "cal": 165, "p": 31, "c": 0, "f": 3.6},
    "chicken thigh": {"name_ar": "فخذ دجاج", "cal": 209, "p": 26, "c": 0, "f": 10},
    "turkey breast": {"name_ar": "صدر ديك رومي", "cal": 135, "p": 30, "c": 0, "f": 1},
    "beef steak": {"name_ar": "ستيك لحم بقري", "cal": 271, "p": 25, "c": 0, "f": 19},
    "ground beef": {"name_ar": "لحم مفروم (15%)", "cal": 250, "p": 26, "c": 0, "f": 15},
    "lamb": {"name_ar": "لحم ضأن", "cal": 294, "p": 25, "c": 0, "f": 21},
    "salmon": {"name_ar": "سلمون", "cal": 208, "p": 20, "c": 0, "f": 13},
    "tuna": {"name_ar": "تونة معلبة", "cal": 116, "p": 26, "c": 0, "f": 1},
    "shrimp": {"name_ar": "جمبري", "cal": 99, "p": 24, "c": 0.2, "f": 0.3},
    "eggs": {"name_ar": "بيضة (كبيرة)", "cal": 78, "p": 6, "c": 0.6, "f": 5},

    # منتجات ألبان وجبن (تنوع كبير)
    "milk whole": {"name_ar": "حليب كامل الدسم", "cal": 61, "p": 3.2, "c": 4.8, "f": 3.3},
    "milk skim": {"name_ar": "حليب خالي الدسم", "cal": 35, "p": 3.4, "c": 5, "f": 0.1},
    "greek yogurt": {"name_ar": "زبادي يوناني", "cal": 59, "p": 10, "c": 3.6, "f": 0.4},
    "cottage cheese": {"name_ar": "جبن قريش", "cal": 98, "p": 11, "c": 3.4, "f": 4.3},
    "white cheese": {"name_ar": "جبن أبيض", "cal": 264, "p": 18, "c": 1.3, "f": 21},
    "mozzarella": {"name_ar": "موزاريلا", "cal": 280, "p": 28, "c": 2.2, "f": 17},
    "cheddar": {"name_ar": "جبن شيدر", "cal": 402, "p": 25, "c": 1.3, "f": 33},
    "parmesan": {"name_ar": "بارميزان", "cal": 431, "p": 38, "c": 3.2, "f": 29},

    # كربوهيدرات وحبوب (شوفان وأكثر)
    "oats": {"name_ar": "شوفان", "cal": 389, "p": 16.9, "c": 66, "f": 6.9},
    "quinoa": {"name_ar": "كينوا مطبوخة", "cal": 120, "p": 4.4, "c": 21, "f": 1.9},
    "brown rice": {"name_ar": "أرز بني", "cal": 111, "p": 2.6, "c": 23, "f": 0.9},
    "white rice": {"name_ar": "أرز أبيض", "cal": 130, "p": 2.7, "c": 28, "f": 0.3},
    "pasta": {"name_ar": "مكرونة", "cal": 131, "p": 5, "c": 25, "f": 1.1},
    "bulgur": {"name_ar": "برغل", "cal": 83, "p": 3.1, "c": 18, "f": 0.2},
    "bread whole": {"name_ar": "خبز قمح كامل", "cal": 247, "p": 13, "c": 41, "f": 3.4},
    "sweet potato": {"name_ar": "بطاطا حلوة", "cal": 86, "p": 1.6, "c": 20, "f": 0.1},
    "potato": {"name_ar": "بطاطس مسلوقة", "cal": 87, "p": 1.9, "c": 20, "f": 0.1},

    # دهون صحية ومكسرات
    "almonds": {"name_ar": "لوز", "cal": 579, "p": 21, "c": 22, "f": 50},
    "walnuts": {"name_ar": "جوز", "cal": 654, "p": 15, "c": 14, "f": 65},
    "peanut butter": {"name_ar": "زبدة فول سوداني", "cal": 588, "p": 25, "c": 20, "f": 50},
    "olive oil": {"name_ar": "زيت زيتون", "cal": 884, "p": 0, "c": 0, "f": 100},
    "avocado": {"name_ar": "أفوكادو", "cal": 160, "p": 2, "c": 9, "f": 15},
    "pumpkin seeds": {"name_ar": "بذور قرع", "cal": 559, "p": 30, "c": 10, "f": 49},
}

# ===============================
# HELPER FUNCTIONS
# ===============================
def get_user(uid):
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    return c.fetchone()

def calc_bmi(w, h): return w / ((h/100)**2)

# ===============================
# SESSION STATE INIT
# ===============================
if 'page' not in st.session_state: st.session_state.page = 'auth'
if 'user' not in st.session_state: st.session_state.user = None

# ===============================
# PAGE: AUTHENTICATION (Login/Register)
# ===============================
if st.session_state.page == 'auth':
    col_l, col_c, col_r = st.columns([1,2,1])
    with col_c:
        st.markdown("<h1 style='text-align:center; color:#0056b3; margin-bottom:30px;'>💊 NutraX Pro</h1>", unsafe_allow_html=True)
        
        auth_type = st.tabs(["تسجيل الدخول", "إنشاء حساب جديد"])
        
        with auth_type[0]: # Login
            with st.form("login_form"):
                email = st.text_input("البريد الإلكتروني")
                password = st.text_input("كلمة المرور", type="password")
                if st.form_submit_button("دخول"):
                    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hash_pass(password)))
                    u = c.fetchone()
                    if u:
                        st.session_state.user = u
                        st.session_state.page = 'dashboard'
                        st.rerun()
                    else:
                        st.error("البيانات غير صحيحة")

        with auth_type[1]: # Register
            with st.form("reg_form"):
                name = st.text_input("الاسم الكامل")
                email = st.text_input("البريد الإلكتروني")
                password = st.text_input("كلمة المرور", type="password")
                birth_year = st.number_input("سنة الميلاد", min_value=1950, max_value=2010, value=2000)
                
                if st.form_submit_button("إنشاء حساب"):
                    try:
                        c.execute("INSERT INTO users (email, password, name, birth_year) VALUES (?,?,?,?)",
                                  (email, hash_pass(password), name, birth_year))
                        conn.commit()
                        st.success("تم إنشاء الحساب! سجل دخولك الآن.")
                    except sqlite3.IntegrityError:
                        st.error("البريد الإلكتروني مستخدم من قبل.")

# ===============================
# MAIN APP LOGIC (If Logged In)
# ===============================
else:
    user_id = st.session_state.user[0]
    user = get_user(user_id)
    u_name, u_email, u_goal = user[3], user[1], user[6]
    is_admin = user[8]

    # ===================
    # SIDEBAR NAVIGATION
    # ===================
    with st.sidebar:
        # Profile Card
        st.markdown(f"""
        <div class='profile-card'>
            <div class='profile-avatar'>👤</div>
            <div class='profile-name'>{u_name}</div>
            <div class='profile-role'>عضو NutraX</div>
            <div style='font-size:0.8em; margin-top:10px; opacity:0.8'>{u_email}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Menu
        if st.button("🏠 الرئيسية (Dashboard)", use_container_width=True):
            st.session_state.page = 'dashboard'
            st.rerun()
        if st.button("👤 الملف الشخصي والأهداف", use_container_width=True):
            st.session_state.page = 'profile'
            st.rerun()
        if st.button("🥗 محلل الطعام", use_container_width=True):
            st.session_state.page = 'analyzer'
            st.rerun()
        if st.button("📅 مصمم الجدول", use_container_width=True):
            st.session_state.page = 'planner'
            st.rerun()
        
        st.divider()
        if st.button("🚪 تسجيل خروج", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = 'auth'
            st.rerun()
            
        if is_admin:
            st.markdown("---")
            st.warning("لوحة تحكم الأدمن")
            if st.button("🔔 مشاهدة المسجلين الجدد"):
                st.session_state.page = 'admin_notifications'
                st.rerun()

    # ===================
    # PAGE ROUTER
    # ===================
    
    # 1. DASHBOARD
    if st.session_state.page == 'dashboard':
        st.title(f"أهلاً بك، {u_name} 👋")
        c1, c2, c3 = st.columns(3)
        
        # Quick BMI check if data exists
        w = user[5] or 70
        h = user[4] or 170
        bmi = calc_bmi(w, h)
        
        c1.metric("مؤشر الكتلة (BMI)", f"{bmi:.1f}")
        c2.metric("هدفك الحالي", u_goal)
        c3.metric("تاريخ الانضمام", user[9][:10])
        
        st.markdown("<div class='card'><div class='card-header'>نصائح اليوم</div></div>", unsafe_allow_html=True)
        st.info("تأكد من شرب 3 لتر ماء يومياً ومتابعة وزنك في قسم التتبع.")

    # 2. PROFILE & GOALS
    elif st.session_state.page == 'profile':
        st.title("⚙️ إعدادات الملف الشخصي")
        
        with st.form("update_profile"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("الاسم", value=u_name)
                new_height = st.number_input("الطول (سم)", value=float(user[4] or 170))
            with col2:
                new_weight = st.number_input("الوزن (كجم)", value=float(user[5] or 70))
                new_goal = st.selectbox("ما هو هدفك الأساسي؟", ["خسارة دهون", "بناء عضل", "الحفاظ على الوزن"], 
                                         index=["loss","gain","maintain"].index(user[6]) if user[6] else 0)
            
            if st.form_submit_button("حفظ التغييرات"):
                goal_map = {"خسارة دهون": "loss", "بناء عضل": "gain", "الحفاظ على الوزن": "maintain"}
                c.execute("UPDATE users SET name=?, height=?, weight=?, goal=? WHERE id=?",
                          (new_name, new_height, new_weight, goal_map[new_goal], user_id))
                conn.commit()
                st.success("تم تحديث بياناتك بنجاح!")
                st.rerun()

    # 3. ANALYZER
    elif st.session_state.page == 'analyzer':
        st.title("🔍 محلل الطعام المتقدم")
        search = st.text_input("ابحث عن طعام (مثال: موز، ستيلك، موزاريلا)")
        
        if search:
            results = []
            for k, v in LOCAL_DB.items():
                if search.lower() in k.lower() or search in v['name_ar']:
                    results.append((k, v))
            
            if results:
                st.markdown(f"تم العثور على {len(results)} نتيجة:")
                for k, v in results:
                    with st.expander(f"🍴 {v['name_ar']} ({k})"):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("سعرات", f"{v['cal']} kcal")
                        c2.metric("بروتين", f"{v['p']} g")
                        c3.metric("كارب", f"{v['c']} g")
                        c4.metric("دهون", f"{v['f']} g")
            else:
                st.warning("عذراً، هذا الطعام غير موجود في قاعدتنا.")

    # 4. MEAL PLANNER
    elif st.session_state.page == 'planner':
        st.title("📅 مصمم وجباتك")
        st.info("هذه الميزة تستخدم بياناتك الشخصية والهدف المختار في الملف الشخصي.")
        
        # Simple Planner Logic based on goal
        goal = user[6]
        if not goal: st.warning("يرجى تحديد هدفك في الملف الشخصي أولاً.")
        else:
            target_cals = 2000 if goal == 'maintain' else (1800 if goal == 'loss' else 2500)
            st.write(f"هدفك اليومي التقريبي بناءً على {goal}: **{target_cals} kcal**")
            
            # Example Meal Structure
            meals = {
                "الإفطار": ["oats", "eggs", "milk whole"],
                "الغداء": ["chicken breast", "brown rice", "broccoli"],
                "العشاء": ["salmon", "sweet potato", "spinach"]
            }
            
            for m_name, foods in meals.items():
                st.subheader(f"☀️ {m_name}")
                total_c = 0
                for f in foods:
                    if f in LOCAL_DB:
                        item = LOCAL_DB[f]
                        st.markdown(f"<div class='food-item'><span class='food-name'>{item['name_ar']}</span><span class='food-cal'>{item['cal']} kcal</span></div>", unsafe_allow_html=True)
                        total_c += item['cal']
                st.caption(f"مجموع الوجبة: {total_c} kcal")
                st.markdown("---")

    # 5. ADMIN NOTIFICATIONS
    elif st.session_state.page == 'admin_notifications':
        st.title("🔔 إشعارات النظام (المسجلين الجدد)")
        c.execute("SELECT name, email, join_date FROM users ORDER BY id DESC LIMIT 10")
        users = c.fetchall()
        
        if users:
            html = "<table class='data-table'><thead><tr><th>الاسم</th><th>الإيميل</th><th>تاريخ التسجيل</th></tr></thead><tbody>"
            for u in users:
                html += f"<tr><td>{u[0]}</td><td>{u[1]}</td><td>{u[2]}</td></tr>"
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("لا يوجد مستخدمين جدد حالياً.")

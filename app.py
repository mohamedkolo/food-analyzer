import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime

# ==========================================
# 1. الإعدادات والتنسيقات (CSS)
# ==========================================
st.set_page_config(page_title="NutraX Pro", page_icon="💊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    
    /* شكل البروفايل */
    .profile-card {
        background: linear-gradient(135deg, #0056b3, #007bff);
        color: white; padding: 20px; border-radius: 15px; text-align: center;
        margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,123,255,0.3);
    }
    .profile-name { font-weight: 700; font-size: 1.2em; }
    
    /* الكروت العامة */
    .card {
        background: white; padding: 20px; border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 20px;
    }
    
    /* كروت الأهداف (زي الصورة) */
    .goal-container { display: flex; gap: 15px; justify-content: center; margin-top: 20px; }
    .goal-btn {
        background: white; border: 2px solid #e0e0e0; border-radius: 12px;
        padding: 30px 20px; text-align: center; cursor: pointer; transition: 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); width: 100%;
    }
    .goal-btn:hover { border-color: #007bff; transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,123,255,0.2); }
    .goal-btn.selected { border-color: #007bff; background-color: #f0f7ff; }
    .goal-icon { font-size: 3em; display: block; margin-bottom: 10px; }
    .goal-title { font-weight: bold; font-size: 1.2em; color: #333; }
    
    /* الجداول */
    .data-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .data-table th { background: #f8f9fa; padding: 12px; text-align: right; }
    .data-table td { padding: 12px; border-bottom: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. قاعدة البيانات
# ==========================================
DB_FILE = "nutrax_pro.db"

def init_db():
    global conn, c
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT count(*) FROM users")
    except:
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, name TEXT, birth_year INTEGER, height REAL, weight REAL, goal TEXT, is_admin INTEGER, join_date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS meals (id INTEGER PRIMARY KEY, name TEXT, calories INTEGER, protein REAL, carbs REAL, fat REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS tracking (id INTEGER PRIMARY KEY, user_id INTEGER, weight REAL, date TEXT)")
    conn.commit()

init_db()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users (email, password, name, is_admin) VALUES (?, ?, ?, ?)", ("admin@nutrax.com", hash_pass("admin123"), "Admin", 1))
    conn.commit()

# ==========================================
# 3. قاعدة الأكل
# ==========================================
LOCAL_DB = {
    "chicken breast": {"name_ar": "صدر دجاج مشوي", "cal": 165, "p": 31, "c": 0, "f": 3.6},
    "chicken thigh": {"name_ar": "فخذ دجاج", "cal": 209, "p": 26, "c": 0, "f": 10},
    "beef steak": {"name_ar": "ستيك لحم بقري", "cal": 271, "p": 25, "c": 0, "f": 19},
    "ground beef": {"name_ar": "لحم مفروم", "cal": 250, "p": 26, "c": 0, "f": 15},
    "salmon": {"name_ar": "سلمون", "cal": 208, "p": 20, "c": 0, "f": 13},
    "tuna": {"name_ar": "تونة معلبة", "cal": 116, "p": 26, "c": 0, "f": 1},
    "eggs": {"name_ar": "بيضة", "cal": 78, "p": 6, "c": 0.6, "f": 5},
    "milk whole": {"name_ar": "حليب كامل", "cal": 61, "p": 3.2, "c": 4.8, "f": 3.3},
    "greek yogurt": {"name_ar": "زبادي يوناني", "cal": 59, "p": 10, "c": 3.6, "f": 0.4},
    "cottage cheese": {"name_ar": "جبن قريش", "cal": 98, "p": 11, "c": 3.4, "f": 4.3},
    "white cheese": {"name_ar": "جبن أبيض", "cal": 264, "p": 18, "c": 1.3, "f": 21},
    "mozzarella": {"name_ar": "موزاريلا", "cal": 280, "p": 28, "c": 2.2, "f": 17},
    "cheddar": {"name_ar": "جبن شيدر", "cal": 402, "p": 25, "c": 1.3, "f": 33},
    "oats": {"name_ar": "شوفان", "cal": 389, "p": 16.9, "c": 66, "f": 6.9},
    "quinoa": {"name_ar": "كينوا مطبوخة", "cal": 120, "p": 4.4, "c": 21, "f": 1.9},
    "brown rice": {"name_ar": "أرز بني", "cal": 111, "p": 2.6, "c": 23, "f": 0.9},
    "white rice": {"name_ar": "أرز أبيض", "cal": 130, "p": 2.7, "c": 28, "f": 0.3},
    "pasta": {"name_ar": "مكرونة", "cal": 131, "p": 5, "c": 25, "f": 1.1},
    "bread whole": {"name_ar": "خبز قمح كامل", "cal": 247, "p": 13, "c": 41, "f": 3.4},
    "sweet potato": {"name_ar": "بطاطا حلوة", "cal": 86, "p": 1.6, "c": 20, "f": 0.1},
    "potato": {"name_ar": "بطاطس مسلوقة", "cal": 87, "p": 1.9, "c": 20, "f": 0.1},
    "almonds": {"name_ar": "لوز", "cal": 579, "p": 21, "c": 22, "f": 50},
    "walnuts": {"name_ar": "جوز", "cal": 654, "p": 15, "c": 14, "f": 65},
    "peanut butter": {"name_ar": "زبدة فول سوداني", "cal": 588, "p": 25, "c": 20, "f": 50},
    "olive oil": {"name_ar": "زيت زيتون", "cal": 884, "p": 0, "c": 0, "f": 100},
    "avocado": {"name_ar": "أفوكادو", "cal": 160, "p": 2, "c": 9, "f": 15},
    "apple": {"name_ar": "تفاح", "cal": 52, "p": 0.3, "c": 14, "f": 0.2},
    "banana": {"name_ar": "موز", "cal": 89, "p": 1.1, "c": 23, "f": 0.3},
    "orange": {"name_ar": "برتقال", "cal": 47, "p": 0.9, "c": 12, "f": 0.1},
    "broccoli": {"name_ar": "بروكلي", "cal": 34, "p": 2.8, "c": 7, "f": 0.4},
    "spinach": {"name_ar": "سبانخ", "cal": 23, "p": 2.9, "c": 3.6, "f": 0.4},
}

# ==========================================
# 4. إدارة الحالة
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None

# ==========================================
# 5. الصفحات
# ==========================================

if st.session_state.page == 'login':
    col_l, col_c, col_r = st.columns([1,2,1])
    with col_c:
        st.markdown("<h1 style='text-align:center; color:#0056b3;'>💊 NutraX Pro</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["تسجيل الدخول", "إنشاء حساب"])
        
        with tab1:
            with st.form("l"):
                e = st.text_input("البريد الإلكتروني")
                p = st.text_input("كلمة المرور", type="password")
                if st.form_submit_button("دخول"):
                    c.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hash_pass(p)))
                    u = c.fetchone()
                    if u:
                        st.session_state.user = u
                        st.session_state.page = 'dashboard'
                        st.rerun()
                    else: st.error("البيانات غير صحيحة")
        
        with tab2:
            with st.form("r"):
                n = st.text_input("الاسم الكامل")
                e = st.text_input("البريد الإلكتروني")
                p = st.text_input("كلمة المرور", type="password")
                by = st.number_input("سنة الميلاد", value=2000)
                if st.form_submit_button("إنشاء حساب"):
                    try:
                        c.execute("INSERT INTO users (email, password, name, birth_year, is_admin, goal) VALUES (?, ?, ?, ?, 0, 'maintain')", (e, hash_pass(p), n, by))
                        conn.commit()
                        st.success("تم التسجيل! سجل دخولك الآن.")
                    except: st.error("البريد مستخدم من قبل")

# التطبيق الرئيسي
else:
    u = st.session_state.user
    u_name, u_email, u_goal, is_admin = u[3], u[1], u[7], u[8]
    
    with st.sidebar:
        st.markdown(f"""
        <div class='profile-card'>
            <div style='font-size:2em'>👤</div>
            <div class='profile-name'>{u_name}</div>
            <div style='font-size:0.8em'>{u_email}</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        if st.button("🏠 الرئيسية"): st.session_state.page = 'dashboard'; st.rerun()
        if st.button("👤 الملف الشخصي"): st.session_state.page = 'profile'; st.rerun()
        if st.button("🥗 محلل الطعام"): st.session_state.page = 'analyzer'; st.rerun()
        if st.button("📅 مصمم الجدول"): st.session_state.page = 'planner'; st.rerun()
        if st.button("🚪 خروج"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()
        if is_admin:
            st.markdown("---")
            if st.button("🔔 المسجلين الجدد"): st.session_state.page = 'admin'; st.rerun()

    # --- الرئيسية ---
    if st.session_state.page == 'dashboard':
        st.title(f"أهلاً بك، {u_name}")
        c1, c2, c3 = st.columns(3)
        w = u[6] or 70
        h = u[5] or 170
        bmi = w / ((h/100)**2)
        c1.metric("الوزن", f"{w} kg")
        c2.metric("الطول", f"{h} cm")
        c3.metric("BMI", f"{bmi:.1f}")
        st.markdown("<div class='card'><h3>نصائح يومية</h3><p>اختر هدفك من الملف الشخصي لترى الجدول المناسب.</p></div>", unsafe_allow_html=True)

    # --- الملف الشخصي (مع كروت الأهداف) ---
    elif st.session_state.page == 'profile':
        st.title("إعدادات الملف الشخصي")
        
        with st.form("up_basic"):
            col1, col2 = st.columns(2)
            with col1:
                nn = st.text_input("الاسم", value=u_name)
                nh = st.number_input("الطول (سم)", value=float(u[5] or 170))
            with col2:
                nw = st.number_input("الوزن (كجم)", value=float(u[6] or 70))
                by = st.number_input("سنة الميلاد", value=int(u[4] or 2000))
            if st.form_submit_button("حفظ البيانات الأساسية"):
                c.execute("UPDATE users SET name=?, height=?, weight=?, birth_year=? WHERE id=?", (nn, nh, nw, by, u[0]))
                conn.commit()
                st.success("تم التحديث")
                st.rerun()

        st.markdown("---")
        st.subheader("اختر هدفك الرياضي")
        st.markdown("<div style='display:flex; gap:10px;'>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # زر خسارة
            c1_style = "border-color:#007bff; background-color:#f0f7ff;" if u_goal == "fat_loss" else ""
            st.markdown(f"""
            <div class='goal-btn {c1_style}' onclick="document.getElementById('btn_fat').click()">
                <span class='goal-icon'>🔥</span>
                <div class='goal-title'>خسارة دهون</div>
                <small>حرارة عالية + سعرات منخفضة</small>
            </div>
            """, unsafe_allow_html=True)
            if st.button("تثبيت: خسارة", key="btn_fat"):
                c.execute("UPDATE users SET goal='fat_loss' WHERE id=?", (u[0],))
                conn.commit()
                st.rerun()

        with col2:
            # زر عضل
            c2_style = "border-color:#28a745; background-color:#f0fff4;" if u_goal == "muscle_gain" else ""
            st.markdown(f"""
            <div class='goal-btn {c2_style}' onclick="document.getElementById('btn_muscle').click()">
                <span class='goal-icon'>💪</span>
                <div class='goal-title'>بناء عضل</div>
                <small>بروتين عالي + سعرات متوسطة</small>
            </div>
            """, unsafe_allow_html=True)
            if st.button("تثبيت: عضل", key="btn_muscle"):
                c.execute("UPDATE users SET goal='muscle_gain' WHERE id=?", (u[0],))
                conn.commit()
                st.rerun()

        with col3:
            # زر ثبات
            c3_style = "border-color:#ffc107; background-color:#fffbe6;" if u_goal == "maintain" else ""
            st.markdown(f"""
            <div class='goal-btn {c3_style}' onclick="document.getElementById('btn_main').click()">
                <span class='goal-icon'>⚖️</span>
                <div class='goal-title'>الحفاظ على الوزن</div>
                <small>توازن غذائي كامل</small>
            </div>
            """, unsafe_allow_html=True)
            if st.button("تثبيت: ثبات", key="btn_main"):
                c.execute("UPDATE users SET goal='maintain' WHERE id=?", (u[0],))
                conn.commit()
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

    # --- مصمم الجدول (ديناميكي) ---
    elif st.session_state.page == 'planner':
        st.title("جدولك الغذائي")
        
        # تحديد الهدف الحالي
        current_goal = u_goal if u_goal else "maintain"
        
        goal_text = {"fat_loss": "خسارة دهون", "muscle_gain": "بناء عضل", "maintain": "الحفاظ على الوزن"}
        st.info(f"الهدف الحالي: **{goal_text.get(current_goal)}**")

        # جداول مختلفة لكل هدف
        if current_goal == "fat_loss":
            st.subheader("برنامج خسارة الدهون (Low Carb / High Protein)")
            meals = [
                ("الإفطار", ["oats", "eggs", "apple"], "🔥 400 kcal"),
                ("الغداء", ["chicken breast", "broccoli", "spinach"], "🔥 350 kcal"),
                ("العشاء", ["tuna", "cucumber"], "🔥 250 kcal"),
                ("سناك", ["greek yogurt", "almonds"], "🔥 150 kcal")
            ]
        elif current_goal == "muscle_gain":
            st.subheader("برنامج بناء العضل (Bulking)")
            meals = [
                ("الإفطار", ["oats", "eggs", "milk whole", "banana"], "💪 700 kcal"),
                ("الغداء", ["chicken thigh", "white rice", "olive oil"], "💪 800 kcal"),
                ("العشاء", ["beef steak", "potato", "bread whole"], "💪 750 kcal"),
                ("سناك", ["peanut butter", "bread whole"], "💪 400 kcal")
            ]
        else: # maintain
            st.subheader("برنامج التوازن الغذائي")
            meals = [
                ("الإفطار", ["oats", "eggs"], "⚖️ 450 kcal"),
                ("الغداء", ["chicken breast", "brown rice", "broccoli"], "⚖️ 550 kcal"),
                ("العشاء", ["salmon", "sweet potato", "spinach"], "⚖️ 500 kcal"),
                ("سناك", ["apple", "almonds"], "⚖️ 200 kcal")
            ]

        # عرض الجدول
        for m_name, items, est_cal in meals:
            st.markdown(f"### {m_name} {est_cal}")
            total_cal = 0
            total_p = 0
            for i in items:
                if i in LOCAL_DB:
                    item = LOCAL_DB[i]
                    st.write(f"- **{item['name_ar']}** ({item['cal']} kcal)")
                    total_cal += item['cal']
                    total_p += item['p']
            st.caption(f"الإجمالي الفعلي: {total_cal} kcal | بروتين: {total_p:.1f}g")
            st.markdown("---")

    elif st.session_state.page == 'analyzer':
        st.title("محلل الطعام")
        s = st.text_input("ابحث عن طعام")
        if s:
            res = [(k,v) for k,v in LOCAL_DB.items() if s in k or s in v['name_ar']]
            if res:
                for k, v in res:
                    with st.expander(f"🍴 {v['name_ar']}"):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("سعرات", f"{v['cal']}")
                        c2.metric("بروتين", f"{v['p']}")
                        c3.metric("كارب", f"{v['c']}")
                        c4.metric("دهون", f"{v['f']}")
            else: st.warning("غير موجود")

    elif st.session_state.page == 'admin':
        st.title("المسجلين الجدد")
        c.execute("SELECT name, email, join_date FROM users ORDER BY id DESC LIMIT 10")
        users = c.fetchall()
        html = "<table class='data-table'><thead><tr><th>الاسم</th><th>الإيميل</th><th>التاريخ</th></tr></thead><tbody>"
        for user in users:
            html += f"<tr><td>{user[0]}</td><td>{user[1]}</td><td>{user[2]}</td></tr>"
        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)

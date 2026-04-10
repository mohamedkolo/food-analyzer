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
    
    /* شكل البروفايل في القائمة */
    .profile-card {
        background: linear-gradient(135deg, #0056b3, #007bff);
        color: white; padding: 20px; border-radius: 15px; text-align: center;
        margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,123,255,0.3);
    }
    .profile-name { font-weight: 700; font-size: 1.2em; }
    
    /* الكروت */
    .card {
        background: white; padding: 20px; border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 20px;
    }
    
    /* الجداول */
    .data-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .data-table th { background: #f8f9fa; padding: 12px; text-align: right; }
    .data-table td { padding: 12px; border-bottom: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. قاعدة البيانات (الإصدار الثابت)
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
# 3. قاعدة الأكل المتقدمة (المطلوبة)
# ==========================================
LOCAL_DB = {
    # بروتينات متقدمة
    "chicken breast": {"name_ar": "صدر دجاج مشوي", "cal": 165, "p": 31, "c": 0, "f": 3.6},
    "chicken thigh": {"name_ar": "فخذ دجاج", "cal": 209, "p": 26, "c": 0, "f": 10},
    "turkey breast": {"name_ar": "صدر ديك رومي", "cal": 135, "p": 30, "c": 0, "f": 1},
    "beef steak": {"name_ar": "ستيك لحم بقري", "cal": 271, "p": 25, "c": 0, "f": 19},
    "ground beef": {"name_ar": "لحم مفروم", "cal": 250, "p": 26, "c": 0, "f": 15},
    "lamb": {"name_ar": "لحم ضأن", "cal": 294, "p": 25, "c": 0, "f": 21},
    "salmon": {"name_ar": "سلمون", "cal": 208, "p": 20, "c": 0, "f": 13},
    "tuna": {"name_ar": "تونة معلبة", "cal": 116, "p": 26, "c": 0, "f": 1},
    "shrimp": {"name_ar": "جمبري", "cal": 99, "p": 24, "c": 0.2, "f": 0.3},
    "eggs": {"name_ar": "بيضة", "cal": 78, "p": 6, "c": 0.6, "f": 5},

    # منتجات ألبان وجبن متنوعة
    "milk whole": {"name_ar": "حليب كامل", "cal": 61, "p": 3.2, "c": 4.8, "f": 3.3},
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

    # دهون ومكسرات
    "almonds": {"name_ar": "لوز", "cal": 579, "p": 21, "c": 22, "f": 50},
    "walnuts": {"name_ar": "جوز", "cal": 654, "p": 15, "c": 14, "f": 65},
    "peanut butter": {"name_ar": "زبدة فول سوداني", "cal": 588, "p": 25, "c": 20, "f": 50},
    "olive oil": {"name_ar": "زيت زيتون", "cal": 884, "p": 0, "c": 0, "f": 100},
    "avocado": {"name_ar": "أفوكادو", "cal": 160, "p": 2, "c": 9, "f": 15},
    "pumpkin seeds": {"name_ar": "بذور قرع", "cal": 559, "p": 30, "c": 10, "f": 49},
    
    # فواكه وخضار
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
                    else:
                        st.error("البيانات غير صحيحة")
        
        with tab2:
            with st.form("r"):
                n = st.text_input("الاسم الكامل")
                e = st.text_input("البريد الإلكتروني")
                p = st.text_input("كلمة المرور", type="password")
                by = st.number_input("سنة الميلاد", value=2000)
                if st.form_submit_button("إنشاء حساب"):
                    try:
                        c.execute("INSERT INTO users (email, password, name, birth_year, is_admin) VALUES (?, ?, ?, ?, 0)", (e, hash_pass(p), n, by))
                        conn.commit()
                        st.success("تم التسجيل! سجل دخولك الآن.")
                    except:
                        st.error("البريد مستخدم من قبل")

# التطبيق الرئيسي
else:
    u = st.session_state.user
    u_name, u_email, u_goal, is_admin = u[3], u[1], u[7], u[8]
    
    # القائمة الجانبية
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
            st.warning("لوحة الأدمن")
            if st.button("🔔 المسجلين الجدد"): st.session_state.page = 'admin'; st.rerun()

    # المحتوى الداخلي
    if st.session_state.page == 'dashboard':
        st.title(f"أهلاً بك، {u_name}")
        c1, c2, c3 = st.columns(3)
        w = u[6] or 70
        h = u[5] or 170
        bmi = w / ((h/100)**2)
        c1.metric("الوزن", f"{w} kg")
        c2.metric("الطول", f"{h} cm")
        c3.metric("BMI", f"{bmi:.1f}")
        
        st.markdown("<div class='card'><h3>نصائح يومية</h3><p>اشرب 3 لتر ماء، وتأكد من تناول البروتين في كل وجبة.</p></div>", unsafe_allow_html=True)

    elif st.session_state.page == 'profile':
        st.title("الملف الشخصي")
        with st.form("up"):
            col1, col2 = st.columns(2)
            with col1:
                nn = st.text_input("الاسم", value=u_name)
                nh = st.number_input("الطول", value=float(u[5] or 170))
            with col2:
                nw = st.number_input("الوزن", value=float(u[6] or 70))
                ng = st.selectbox("الهدف", ["خسارة", "عضل", "ثبات"], index=0)
            
            if st.form_submit_button("حفظ التغييرات"):
                c.execute("UPDATE users SET name=?, height=?, weight=?, goal=? WHERE id=?", (nn, nh, nw, ng, u[0]))
                conn.commit()
                st.success("تم التحديث"); st.rerun()

    elif st.session_state.page == 'analyzer':
        st.title("محلل الطعام")
        s = st.text_input("ابحث عن طعام (مثال: موز، ستيلك، شوفان)")
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
            else:
                st.warning("غير موجود")

    elif st.session_state.page == 'planner':
        st.title("مصمم الجدول")
        st.info(f"هدفك الحالي: {u_goal}")
        # مثال بسيط للجدول
        st.subheader("اقتراح لليوم")
        meals = [
            ("الإفطار", ["oats", "eggs", "milk whole"]),
            ("الغداء", ["chicken breast", "brown rice", "broccoli"]),
            ("العشاء", ["salmon", "sweet potato", "spinach"])
        ]
        for m_name, items in meals:
            st.write(f"**{m_name}**")
            total = 0
            for i in items:
                if i in LOCAL_DB:
                    item = LOCAL_DB[i]
                    st.write(f"- {item['name_ar']}: {item['cal']} kcal")
                    total += item['cal']
            st.write(f"*المجموع: {total} kcal*")
            st.markdown("---")

    elif st.session_state.page == 'admin':
        st.title("المسجلين الجدد")
        c.execute("SELECT name, email, join_date FROM users ORDER BY id DESC LIMIT 10")
        users = c.fetchall()
        html = "<table class='data-table'><thead><tr><th>الاسم</th><th>الإيميل</th><th>التاريخ</th></tr></thead><tbody>"
        for user in users:
            html += f"<tr><td>{user[0]}</td><td>{user[1]}</td><td>{user[2]}</td></tr>"
        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)

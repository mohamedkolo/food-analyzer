# ===============================
# NUTRAX ULTIMATE SYSTEM (Compact Stable Version)
# ===============================

import streamlit as st
import sqlite3
import hashlib
import copy
from datetime import datetime

# ===============================
# PAGE CONFIG & STYLES
# ===============================
st.set_page_config(page_title="NutraX", page_icon="💊", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    .main { background-color: #f0f4f8; }
    .section-title { font-size: 1.1em; font-weight: 700; color: #0056b3; border-right: 5px solid #007bff; padding-right: 12px; margin: 20px 0 10px; }
    
    /* Plans Cards */
    .plan-container { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }
    .plan-card { background: white; border-radius: 20px; padding: 30px; width: 300px; text-align: center; box-shadow: 0 10px 25px rgba(0,123,255,0.1); border-top: 6px solid #ccc; }
    .plan-free { border-color: #6c757d; }
    .plan-pro { border-color: #007bff; }
    .plan-coach { border-color: #ffc107; }
    .plan-price { font-size: 2.5em; font-weight: 800; margin: 15px 0; color: #222; }
    .plan-features { list-style: none; padding: 0; text-align: right; margin: 25px 0; font-size: 1.05em; }
    .plan-features li { padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
    .btn-plan { display: block; width: 100%; padding: 12px; border: none; border-radius: 10px; color: white; font-weight: bold; cursor: pointer; margin-top: 15px; font-size: 1.1em; }
    
    /* Meal Planner */
    .meal-card { background: white; border-radius: 14px; padding: 20px; margin: 12px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-right: 6px solid #007bff; }
    .total-bar { background: linear-gradient(135deg, #0056b3, #007bff); color: white; border-radius: 16px; padding: 20px 30px; margin: 20px 0; text-align: center; font-weight: bold; font-size: 1.2em; }
</style>
""", unsafe_allow_html=True)

# ===============================
# DB SETUP
# ===============================
conn = sqlite3.connect("nutrax.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT, is_admin INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS meals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, calories INTEGER, protein INTEGER, carbs INTEGER, fat INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS tracking (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, date TEXT)")
conn.commit()

# ===============================
# AUTO-CREATE ADMIN
# ===============================
def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users (email, password, is_admin) VALUES (?, ?, ?)", ("admin@nutrax.com", hash_pass("admin123"), 1))
    conn.commit()

# ===============================
# DATA (Top 20 Essentials)
# ===============================
LOCAL_DB = {
    "apple": {"name_ar": "تفاح", "nutrients": {"Energy":52, "Protein":0.3,"Total lipid (fat)":0.2,"Carbohydrate, by difference":14,"Fiber, total dietary":2.4,"Calcium, Ca":6,"Iron, Fe":0.1}},
    "banana": {"name_ar": "موز", "nutrients": {"Energy":89, "Protein":1.1,"Total lipid (fat)":0.3,"Carbohydrate, by difference":23,"Fiber, total dietary":2.6,"Potassium, K":358}},
    "egg": {"name_ar": "بيضة", "nutrients": {"Energy":143, "Protein":12.6,"Total lipid (fat)":9.5,"Carbohydrate, by difference":0.7,"Calcium, Ca":56,"Iron, Fe":1.8,"Vitamin D (D2 + D3)":2.0}},
    "chicken breast": {"name_ar": "صدر دجاج", "nutrients": {"Energy":165, "Protein":31,"Total lipid (fat)":3.6,"Carbohydrate, by difference":0,"Iron, Fe":1.0,"Vitamin B-12":0.3}},
    "rice": {"name_ar": "أرز", "nutrients": {"Energy":130, "Protein":2.7,"Total lipid (fat)":0.3,"Carbohydrate, by difference":28,"Fiber, total dietary":0.4,"Iron, Fe":1.5}},
    "bread": {"name_ar": "خبز", "nutrients": {"Energy":265, "Protein":9,"Total lipid (fat)":3.2,"Carbohydrate, by difference":49,"Fiber, total dietary":2.7,"Calcium, Ca":182}},
    "milk": {"name_ar": "حليب", "nutrients": {"Energy":61, "Protein":3.2,"Total lipid (fat)":3.3,"Carbohydrate, by difference":4.8,"Calcium, Ca":113,"Vitamin D (D2 + D3)":1.3}},
    "yogurt": {"name_ar": "زبادي", "nutrients": {"Energy":61, "Protein":3.5,"Total lipid (fat)":3.3,"Carbohydrate, by difference":4.7,"Calcium, Ca":121}},
    "cheese": {"name_ar": "جبن", "nutrients": {"Energy":264, "Protein":18,"Total lipid (fat)":21,"Carbohydrate, by difference":1.3,"Calcium, Ca":500,"Sodium, Na":621}},
    "beef": {"name_ar": "لحم بقري", "nutrients": {"Energy":250, "Protein":26,"Total lipid (fat)":15,"Carbohydrate, by difference":0,"Iron, Fe":2.6,"Zinc, Zn":5.3}},
    "tuna": {"name_ar": "تونة", "nutrients": {"Energy":128, "Protein":29,"Total lipid (fat)":1.0,"Carbohydrate, by difference":0,"Iron, Fe":1.3,"Vitamin D (D2 + D3)":5.7}},
    "salmon": {"name_ar": "سلمون", "nutrients": {"Energy":208, "Protein":20,"Total lipid (fat)":13,"Carbohydrate, by difference":0,"Vitamin D (D2 + D3)":11}},
    "pasta": {"name_ar": "مكرونة", "nutrients": {"Energy":158, "Protein":5.8,"Total lipid (fat)":0.9,"Carbohydrate, by difference":31,"Fiber, total dietary":1.8}},
    "oats": {"name_ar": "شوفان", "nutrients": {"Energy":389, "Protein":16.9,"Total lipid (fat)":6.9,"Carbohydrate, by difference":66,"Fiber, total dietary":10.6,"Iron, Fe":4.7}},
    "potato": {"name_ar": "بطاطس", "nutrients": {"Energy":87, "Protein":1.9,"Total lipid (fat)":0.1,"Carbohydrate, by difference":20,"Vitamin C, total ascorbic acid":13}},
    "lentils": {"name_ar": "عدس", "nutrients": {"Energy":116, "Protein":9,"Total lipid (fat)":0.4,"Carbohydrate, by difference":20,"Fiber, total dietary":7.9,"Iron, Fe":3.3}},
    "almonds": {"name_ar": "لوز", "nutrients": {"Energy":579, "Protein":21,"Total lipid (fat)":50,"Carbohydrate, by difference":22,"Fiber, total dietary":12.5,"Calcium, Ca":264}},
    "orange": {"name_ar": "برتقال", "nutrients": {"Energy":47, "Protein":0.9,"Total lipid (fat)":0.1,"Carbohydrate, by difference":12,"Vitamin C, total ascorbic acid":53}},
    "avocado": {"name_ar": "أفوكادو", "nutrients": {"Energy":160, "Protein":2,"Total lipid (fat)":15,"Carbohydrate, by difference":9,"Fiber, total dietary":6.7}},
    "broccoli": {"name_ar": "بروكلي", "nutrients": {"Energy":34, "Protein":2.8,"Total lipid (fat)":0.4,"Carbohydrate, by difference":7,"Fiber, total dietary":2.6,"Vitamin C, total ascorbic acid":89}},
}

MEAL_PLAN_TEMPLATES = {
    "خسارة دهون وبناء عضل": {
        "الإفطار": [{"name": "شوفان", "amount": 50, "key": "oats"}, {"name": "بيضة", "amount": 100, "key": "egg"}],
        "الغداء": [{"name": "صدر دجاج", "amount": 150, "key": "chicken breast"}, {"name": "أرز", "amount": 100, "key": "rice"}],
        "العشاء": [{"name": "تونة", "amount": 100, "key": "tuna"}, {"name": "سلطة", "amount": 100, "key": "broccoli"}], 
    },
    "زيادة الوزن والعضل": {
        "الإفطار": [{"name": "شوفان", "amount": 80, "key": "oats"}, {"name": "بيضة", "amount": 150, "key": "egg"}, {"name": "حليب", "amount": 200, "key": "milk"}],
        "الغداء": [{"name": "صدر دجاج", "amount": 200, "key": "chicken breast"}, {"name": "أرز", "amount": 250, "key": "rice"}],
        "العشاء": [{"name": "لحم بقري", "amount": 150, "key": "beef"}, {"name": "مكرونة", "amount": 200, "key": "pasta"}],
    }
}

def get_meal_macros(items):
    total = {"Energy":0, "Protein":0, "Carbohydrate, by difference":0, "Total lipid (fat)":0}
    for item in items:
        key = item.get("key")
        amt = item.get("amount", 100) / 100.0
        if key in LOCAL_DB:
            nuts = LOCAL_DB[key]["nutrients"]
            for k in total: total[k] += nuts.get(k, 0) * amt
    return total

# ===============================
# APP UI & LOGIC
# ===============================
st.title("NutraX PRO 💊")

if "user" not in st.session_state: st.session_state.user = None

# Sidebar Menu
menu = st.sidebar.selectbox("القائمة", ["تسجيل الدخول", "إنشاء حساب"])

if menu == "إنشاء حساب":
    with st.form("reg"):
        e = st.text_input("البريد الإلكتروني")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("إنشاء"):
            try:
                c.execute("INSERT INTO users (email, password) VALUES (?,?)", (e, hash_pass(p)))
                conn.commit()
                st.success("تم إنشاء الحساب")
            except: st.error("البريد مستخدم")

if menu == "تسجيل الدخول":
    with st.form("login"):
        e = st.text_input("البريد الإلكتروني")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول"):
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hash_pass(p)))
            u = c.fetchone()
            if u:
                st.session_state.user = u
                st.rerun()
            else: st.error("خطأ في البيانات")

if st.session_state.user:
    uid = st.session_state.user[0]
    is_admin = st.session_state.user[3]
    st.sidebar.markdown("---")
    
    # Navigation
    page = st.sidebar.radio("الصفحات", ["📊 لوحة التحكم", "🔍 محلل الأكل", "🍽️ مصمم الوجبات", "💎 الباقات"], label_visibility="collapsed")
    if is_admin:
        page = st.sidebar.selectbox("أدمن", ["📊 لوحة التحكم", "🔍 محلل الأكل", "🍽️ مصمم الوجبات", "💎 الباقات", "🛠️ إدارة الأكل"], index=0)

    # Dashboard
    if page == "📊 لوحة التحكم":
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("احتياجاتك")
            with st.expander("بياناتك", expanded=True):
                g = st.radio("الجنس", ["ذكر", "أنثى"], horizontal=True)
                a = st.number_input("العمر", 10, 100, 25)
                h = st.number_input("الطول سم", 100, 250, 170)
                w = st.number_input("الوزن كجم", 30, 300, 70)
                act = st.selectbox("النشاط", ["خفيف", "متوسط", "رياضي"])
                gl = st.selectbox("الهدف", ["خسارة دهون", "بناء عضل", "ثبات"])
                if st.button("احسب"):
                    bmr = (10*w + 6.25*h - 5*a + 5) if g=="ذكر" else (10*w + 6.25*h - 5*a - 161)
                    mul = {"خفيف":1.2, "متوسط":1.55, "رياضي":1.8}[act]
                    tdee = bmr * mul
                    adj = {"خسارة دهون":-400, "بناء عضل":400, "ثبات":0}[gl]
                    st.session_state['cal'] = int(tdee+adj)
                    st.session_state['w'] = w
        with c2:
            if 'cal' in st.session_state:
                st.metric("BMI", f"{w/((h/100)**2):.1f}")
                st.metric("الهدف", f"{st.session_state['cal']} kcal")
        
        st.divider()
        st.subheader("تتبع الوزن")
        c1, c2 = st.columns([1,3])
        with c1:
            nw = st.number_input("وزن اليوم", value=float(st.session_state.get('w',70)))
            if st.button("حفظ"):
                c.execute("INSERT INTO tracking (user_id, weight, date) VALUES (?,?,datetime('now'))", (uid, nw))
                conn.commit()
                st.success("تم")
        with c2:
            c.execute("SELECT date, weight FROM tracking WHERE user_id=? ORDER BY id DESC LIMIT 7", (uid,))
            d = c.fetchall()
            if d: st.line_chart(dict(zip([x[0] for x in d[::-1]], [x[1] for x in d[::-1]])))

    # Analyzer
    elif page == "🔍 محلل الأكل":
        st.subheader("تحليل الطعام")
        c1, c2 = st.columns([3,1])
        with c1: s = st.text_input("ابحث (مثال: تفاح، دجاج)")
        with c2: g = st.number_input("جم", 100)
        if s:
            k = next((k for k,v in LOCAL_DB.items() if s in v["name_ar"] or s in k), None)
            if k:
                i = LOCAL_DB[k]
                st.write(f"### {i['name_ar']} ({g}جم)")
                n = i['nutrients']
                f = g/100.0
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("سعرات", f"{n['Energy']*f:.0f}")
                c2.metric("بروتين", f"{n['Protein']*f:.1f}g")
                c3.metric("كارب", f"{n['Carbohydrate, by difference']*f:.1f}g")
                c4.metric("دهون", f"{n['Total lipid (fat)']*f:.1f}g")
            else: st.warning("غير موجود")

    # Planner
    elif page == "🍽️ مصمم الوجبات":
        st.subheader("جدولك")
        if 'plan' not in st.session_state: st.session_state['plan'] = copy.deepcopy(MEAL_PLAN_TEMPLATES["خسارة دهون وبناء عضل"])
        p = st.session_state['plan']
        tot = 0
        for m, items in p.items():
            with st.expander(m):
                for i, it in enumerate(items):
                    cols = st.columns([3,1])
                    with cols[0]:
                        opts = list(LOCAL_DB.keys())
                        idx = opts.index(it['key']) if it['key'] in opts else 0
                        nk = st.selectbox("طعام", opts, idx, key=f"{m}_{i}")
                        if nk!=it['key']: it['key']=nk; it['name']=LOCAL_DB[nk]['name_ar']
                    with cols[1]:
                        na = st.number_input("جم", 5,500,int(it['amount']), key=f"a{m}_{i}")
                        it['amount']=na
                m_n = get_meal_macros(items)
                st.caption(f"🔥 {m_n['Energy']:.0f} kcal")
                tot += m_n['Energy']
        st.markdown(f'<div class="total-bar">مجموع الجدول: {tot:.0f} kcal</div>', unsafe_allow_html=True)

    # Plans
    elif page == "💎 الباقات":
        st.markdown("<h2 style='text-align:center'>باقات NutraX</h2>", unsafe_allow_html=True)
        st.markdown("<div class='plan-container'>", unsafe_allow_html=True)
        st.markdown("""
        <div class='plan-card plan-free'><h3>مجاني</h3><div class='plan-price'>0$</div>
        <ul class='plan-features'><li>تتبع الوزن</li><li>BMI</li></ul>
        <button class='btn-plan' style='background:#9e9e9e'>الحالي</button></div>
        <div class='plan-card plan-pro'><h3>PRO</h3><div class='plan-price'>10$</div>
        <ul class='plan-features'><li>محلل الأكل</li><li>مصمم الوجبات</li></ul>
        <button class='btn-plan' style='background:#007bff'>اشترك</button></div>
        <div class='plan-card plan-coach'><h3>COACH</h3><div class='plan-price'>30$</div>
        <ul class='plan-features'><li>متابعة مع مدرب</li><li>خطط مخصصة</li></ul>
        <button class='btn-plan' style='background:#ffc107'>تواصل</button></div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Admin
    elif page == "🛠️ إدارة الأكل":
        st.subheader("إضافة أكل للقاعدة")
        with st.form("add"):
            n = st.text_input("اسم (إنجليزي)")
            c, p, cb, f = st.number_input("سعرات"), st.number_input("بروتين"), st.number_input("كارب"), st.number_input("دهون")
            if st.form_submit_button("إضافة"):
                c.execute("INSERT INTO meals VALUES (?,?,?,?,?,?)", (None, n, c, p, cb, f))
                conn.commit()
                st.success("تم")
        st.subheader("الوجبات المسجلة")
        for r in c.execute("SELECT * FROM meals"): st.write(r)

else:
    st.info("سجل دخولك للبدء")

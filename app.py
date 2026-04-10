# =============================================================================
# [GPT Generated Code] NutraX Ultimate V5
# Developer: GPT & User Collaboration
# Features: Multi-day Planner, BMI/Calorie Logic, History Charts, Shopping List
# =============================================================================

import streamlit as st
import sqlite3
import hashlib
import os
import json
from datetime import datetime
import plotly.graph_objs as go

# ==========================================
# 1. CONFIG & STYLE
# ==========================================
st.set_page_config(page_title="NutraX V5", page_icon="💊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    .metric-box { background:#fff; padding:15px; border-radius:10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; border: 1px solid #eee; }
    .shopping-list { background: #f0f7ff; padding: 15px; border-radius: 10px; border: 1px solid #b3d7ff; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE SETUP (Upgraded)
# ==========================================
DB_FILE = "nutrax_v5.db"

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

    # Users Table (Added Height/Weight/Goal/BirthYear)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT,
        name TEXT,
        height REAL,
        weight REAL,
        birth_year INTEGER,
        goal TEXT,
        is_admin INTEGER
    )""")
    
    # Plans Table
    c.execute("""CREATE TABLE IF NOT EXISTS saved_plans (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        plan_name TEXT,
        plan_data TEXT,
        created_at TEXT,
        type TEXT
    )""")
    
    # Tracking Table (History)
    c.execute("""CREATE TABLE IF NOT EXISTS tracking (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        weight REAL,
        date TEXT
    )""")
    
    conn.commit()

init_db()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

# Create Admin
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, NULL, NULL, NULL, NULL, 1)", 
              ("admin@nutrax.com", hash_pass("123456"), "Admin"))
    conn.commit()

# ==========================================
# 3. LOCAL FOOD DB (Simple & Effective)
# ==========================================
LOCAL_DB = {
    "chicken": {"name": "دجاج", "cal":165, "p":31},
    "beef": {"name": "لحم", "cal":250, "p":26},
    "fish": {"name": "سمك", "cal":180, "p":20},
    "eggs": {"name": "بيض", "cal":78, "p":6},
    "rice": {"name": "رز", "cal":130, "p":2.7},
    "oats": {"name": "شوفان", "cal":389, "p":16.9},
    "milk": {"name": "لبن", "cal":60, "p":3.2},
    "banana": {"name": "موز", "cal":89, "p":1.1},
    "apple": {"name": "تفاح", "cal":52, "p":0.3},
    "almonds": {"name": "لوز", "cal":579, "p":21},
    "potato": {"name": "بطاطس", "cal":87, "p":1.9},
    "broccoli": {"name": "بروكلي", "cal":34, "p":2.8},
    "peanut": {"name": "زبدة فول سوداني", "cal":588, "p":25},
    "lentils": {"name": "عدس", "cal":116, "p":9},
    "dates": {"name": "تمر", "cal":282, "p":2.5},
    "bread": {"name": "خبز", "cal":265, "p":9},
    "cheese": {"name": "جبن", "cal":264, "p":18}
}

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
def calculate_macros(weight, height, age, goal):
    bmr = 10 * weight + 6.25 * height - 5 * age + 5 # Male default
    tdee = bmr * 1.55
    
    if goal == "fat_loss": target = tdee - 400
    elif goal == "muscle_gain": target = tdee + 400
    else: target = tdee
    return int(target)

def generate_shopping_list(plan_data):
    shopping = {}
    for day, meals in plan_data.items():
        for meal, foods in meals.items():
            for f_key, grams in foods.items():
                if f_key in LOCAL_DB:
                    if f_key not in shopping: shopping[f_key] = 0
                    shopping[f_key] += grams
    return shopping

# ==========================================
# 5. STATE MANAGEMENT
# ==========================================
if "page" not in st.session_state: st.session_state.page = "login"
if "user" not in st.session_state: st.session_state.user = None
if "targets" not in st.session_state: st.session_state.targets = None

# ==========================================
# 6. PAGES LOGIC
# ==========================================

if st.session_state.page == "login":
    st.markdown("<h1 style='text-align:center; color:#0056b3;'>💊 NutraX V5</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["تسجيل الدخول", "إنشاء حساب"])

    with tab1:
        e = st.text_input("البريد الإلكتروني")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("دخول"):
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hash_pass(p)))
            u = c.fetchone()
            if u:
                st.session_state.user = u
                # Check if user has metrics setup
                if u[4] and u[5]: # Height and Weight exist
                    st.session_state.page = "dashboard"
                else:
                    st.session_state.page = "profile_setup"
                st.rerun()
            else:
                st.error("البيانات غير صحيحة")

    with tab2:
        n = st.text_input("الاسم الكامل")
        e = st.text_input("البريد الإلكتروني")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("إنشاء حساب"):
            try:
                c.execute("INSERT INTO users (email, password, name, is_admin) VALUES (?, ?, ?, 0)", (e, hash_pass(p), n))
                conn.commit()
                st.success("تم التسجيل! سجل دخولك.")
            except:
                st.error("البريد مستخدم من قبل")

# ===== APP MAIN =====
else:
    u = st.session_state.user
    u_id = u[0]

    with st.sidebar:
        st.markdown(f"<div style='text-align:center; margin-bottom:20px'><h3>{u[3]}</h3></div>", unsafe_allow_html=True)
        if st.button("🏠 الرئيسية"): st.session_state.page="dashboard"; st.rerun()
        if st.button("👤 الإعدادات والهدف"): st.session_state.page="profile_setup"; st.rerun()
        if st.button("📅 مصمم الجدول"): st.session_state.page="planner"; st.rerun()
        if st.button("💾 جداولي المحفوظة"): st.session_state.page="saved"; st.rerun()
        if st.button("📈 سجل الوزن"): st.session_state.page="history"; st.rerun()
        if st.button("🚪 خروج"):
            st.session_state.user=None
            st.session_state.page="login"
            st.rerun()

    # --- 1. PROFILE / SETUP (The Logic Core) ---
    if st.session_state.page == "profile_setup":
        st.title("إعداداتك الغذائية")
        st.info("الخطوة الأولى لإنشاء جدول مثالي هي تحديد هدفك.")
        
        with st.form("setup_form"):
            col1, col2 = st.columns(2)
            with col1:
                h = st.number_input("الطول (سم)", value=float(u[4] or 170))
                w = st.number_input("الوزن (كجم)", value=float(u[5] or 70))
            with col2:
                age = st.number_input("العمر", value=25)
                goal = st.selectbox("هدفك", ["maintain", "fat_loss", "muscle_gain"], format_func=lambda x: {"maintain":"ثبات", "fat_loss":"خسارة", "muscle_gain":"عضل"}[x])
            
            if st.form_submit_button("حفظ وحساب احتياجي"):
                c.execute("UPDATE users SET height=?, weight=?, goal=?, birth_year=? WHERE id=?", 
                          (h, w, goal, datetime.now().year - age, u_id))
                conn.commit()
                
                target_cal = calculate_macros(w, h, age, goal)
                st.session_state.targets = {'cal': target_cal, 'goal': goal}
                
                # Update session user object with new data
                c.execute("SELECT * FROM users WHERE id=?", (u_id,))
                st.session_state.user = c.fetchone()
                
                st.success(f"تم الحفظ! احتياجك اليومي التقريبي: {target_cal} kcal")
                st.session_state.page = "planner"
                st.rerun()

    # --- 2. DASHBOARD ---
    elif st.session_state.page == "dashboard":
        st.title("لوحة التحكم")
        c1, c2, c3 = st.columns(3)
        
        # Stats
        c.execute("SELECT COUNT(*) FROM saved_plans WHERE user_id=?", (u_id,))
        c1.metric("الجداول المحفوظة", c.fetchone()[0])
        
        if st.session_state.targets:
            c2.metric("هدفك اليومي", f"{st.session_state.targets['cal']} kcal")
        
        # Latest Weight
        c.execute("SELECT weight FROM tracking WHERE user_id=? ORDER BY id DESC LIMIT 1", (u_id,))
        last_w = c.fetchone()
        c3.metric("آخر وزن مسجل", f"{last_w[0] if last_w else '---'} kg")
        
        st.markdown("---")
        st.info("ابدأ بتصميم جدول جديد أو راجع سجل وزنك.")

    # --- 3. PLANNER (Multi-day Logic) ---
    elif st.session_state.page == "planner":
        st.title("مصمم الجدول الغذائي")
        
        if not st.session_state.targets:
            st.warning("يرجى الذهاب للإعدادات وحساب هدفك أولاً.")
            if st.button("الذهاب للإعدادات"): st.session_state.page="profile_setup"; st.rerun()
            st.stop()
            
        target = st.session_state.targets['cal']
        st.info(f"الهدف اليومي: **{target} kcal**")
        
        days = st.number_input("عدد الأيام", 1, 30, 1)
        
        plan = {}
        total_cal = 0
        
        for d in range(days):
            st.subheader(f"📅 يوم {d+1}")
            plan[d] = {}
            
            cols = st.columns(4)
            meals = ["فطار", "غداء", "عشاء", "سناك"]
            
            for i, meal in enumerate(meals):
                with cols[i]:
                    st.write(f"**{meal}**")
                    # Allow multiple foods per meal
                    foods = st.multiselect(f"أضف أكل", list(LOCAL_DB.keys()), key=f"sel_{meal}_{d}")
                    plan[d][meal] = {}
                    
                    for f in foods:
                        # Grams Input
                        g = st.number_input(f"{LOCAL_DB[f]['name']} (جم)", 0, 1000, 100, key=f"inp_{f}_{meal}_{d}")
                        if g > 0:
                            plan[d][meal][f] = g
                            cals = (g/100) * LOCAL_DB[f]["cal"]
                            total_cal += cals
                            st.caption(f"{int(cals)} kcal")

        st.markdown("---")
        # Live Metrics
        c1, c2 = st.columns(2)
        c1.metric("إجمالي الجدول", f"{int(total_cal)} kcal")
        diff = total_cal - (target * days)
        c2.metric("الفارق عن الهدف", f"{int(diff)} kcal")
        
        name = st.text_input("اسم الجدول", value=f"جدول {datetime.now().day}-{datetime.now().month}")
        save_type = st.selectbox("نوع الحفظ", ["خاص بي", "للعميل", "عام"])
        
        col_save, col_shop = st.columns(2)
        with col_save:
            if st.button("💾 حفظ الجدول"):
                c.execute("INSERT INTO saved_plans VALUES (NULL, ?, ?, ?, datetime('now'), ?)",
                          (u_id, name, json.dumps(plan), save_type))
                conn.commit()
                st.success("تم الحفظ!")
                st.rerun()
        
        with col_shop:
            if st.button("🛒 إنشاء قائمة مشتريات (معاينة)"):
                shop_list = generate_shopping_list(plan)
                st.json(shop_list)

    # --- 4. SAVED PLANS ---
    elif st.session_state.page == "saved":
        st.title("جداولي المحفوظة")
        filter_type = st.selectbox("فلتر", ["الكل", "خاص بي", "للعميل", "عام"])
        
        query = "SELECT id, plan_name, created_at, type FROM saved_plans WHERE user_id=?"
        params = [u_id]
        
        if filter_type != "الكل":
            query += " AND type=?"
            params.append(filter_type)
            
        c.execute(query, params)
        data = c.fetchall()
        
        for pid, name, date, ptype in data:
            with st.expander(f"📂 {name} ({ptype}) - {date}"):
                col1, col2 = st.columns(2)
                with col1:
                    c.execute("SELECT plan_data FROM saved_plans WHERE id=?", (pid,))
                    p = json.loads(c.fetchone()[0])
                    for d, meals in p.items():
                        st.write(f"يوم {int(d)+1}")
                        for m, foods in meals.items():
                            items_str = ", ".join([f"{LOCAL_DB[k]['name']}: {v}g" for k,v in foods.items() if v>0])
                            st.write(f"- {m}: {items_str}")
                
                with col2:
                    if st.button("🛒 قائمة المشتريات", key=f"shop_{pid}"):
                        c.execute("SELECT plan_data FROM saved_plans WHERE id=?", (pid,))
                        raw_plan = json.loads(c.fetchone()[0])
                        shop = generate_shopping_list(raw_plan)
                        
                        st.subheader("قائمة المشتريات للجدول")
                        for f_key, total_g in shop.items():
                            st.write(f"- {LOCAL_DB[f_key]['name']}: **{total_g} جم** ({int(total_g/1000) if total_g>1000 else total_g} كجم/جم)")

    # --- 5. HISTORY (Charts) ---
    elif st.session_state.page == "history":
        st.title("سجل تقدم الوزن")
        
        with st.form("log_weight"):
            w = st.number_input("سجل وزنك اليوم (كجم)", 30.0, 300.0)
            if st.form_submit_button("تسجيل"):
                c.execute("INSERT INTO tracking (user_id, weight, date) VALUES (?, ?, datetime('now'))", (u_id, w))
                conn.commit()
                st.success("تم التسجيل")
                st.rerun()
        
        # Chart
        c.execute("SELECT date, weight FROM tracking WHERE user_id=? ORDER BY id ASC", (u_id,))
        data = c.fetchall()
        
        if data:
            dates = [d[0] for d in data]
            weights = [d[1] for d in data]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=weights, mode='lines+markers', name='الوزن'))
            fig.update_layout(title="تغير الوزن عبر الزمن", xaxis_title="التاريخ", yaxis_title="الوزن (كجم)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد سجلات وزن بعد.")

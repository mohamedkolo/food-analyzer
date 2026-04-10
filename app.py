# =============================================================================
# NutraX Final - Stable Version
# Fixes: Resolved StreamlitDuplicateElementId errors.
# Update: Added Country to Registration.
# Features: Full Profile, Multi-day Planner, Shopping List, History.
# =============================================================================

import streamlit as st
import sqlite3
import hashlib
import os
import json
from datetime import datetime

# ==========================================
# 1. CONFIG & STYLE
# ==========================================
st.set_page_config(page_title="NutraX Final", page_icon="💊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    .metric-box { background:#fff; padding:15px; border-radius:10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; border: 1px solid #eee; }
    .shopping-list { background: #f0f7ff; padding: 15px; border-radius: 10px; border: 1px solid #b3d7ff; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE SETUP
# ==========================================
DB_FILE = "nutrax_final.db"

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

    # جدول المستخدمين (مع إضافة البلد)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT,
        name TEXT,
        height REAL,
        weight REAL,
        birth_year INTEGER,
        country TEXT,
        goal TEXT,
        is_admin INTEGER
    )""")
    
    # محاولة إضافة عمود البلد لو قاعدة البيانات قديمة
    try:
        c.execute("ALTER TABLE users ADD COLUMN country TEXT")
    except:
        pass # العمود موجود بالفعل
    
    c.execute("""CREATE TABLE IF NOT EXISTS saved_plans (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        plan_name TEXT,
        plan_data TEXT,
        created_at TEXT,
        type TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS tracking (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        weight REAL,
        date TEXT
    )""")
    
    conn.commit()

init_db()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

# Admin
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, 1)", 
              ("admin@nutrax.com", hash_pass("123456"), "Admin"))
    conn.commit()

# ==========================================
# 3. FOOD DB
# ==========================================
LOCAL_DB = {
    "chicken_breast": {"name": "صدر دجاج", "cal":165, "p":31}, "chicken_thigh": {"name": "فخذ دجاج", "cal":209, "p":26},
    "turkey_breast": {"name": "صدر ديك رومي", "cal":135, "p":30}, "beef_steak": {"name": "ستيك لحم", "cal":271, "p":25},
    "ground_beef": {"name": "لحم مفروم", "cal":250, "p":26}, "lamb": {"name": "لحم ضأن", "cal":294, "p":25},
    "salmon": {"name": "سلمون", "cal":208, "p":20}, "tuna_canned": {"name": "تونة معلبة", "cal":116, "p":26},
    "shrimp": {"name": "جمبري", "cal":99, "p":24}, "white_fish": {"name": "سمك أبيض", "cal":96, "p":20},
    "eggs_whole": {"name": "بيضة كاملة", "cal":78, "p":6}, "eggs_whites": {"name": "بياض بيض", "cal":17, "p":3.6},
    "milk_whole": {"name": "حليب كامل", "cal":61, "p":3.2}, "milk_skim": {"name": "حليب خالي الدسم", "cal":35, "p":3.4},
    "greek_yogurt": {"name": "زبادي يوناني", "cal":59, "p":10}, "cottage_cheese": {"name": "جبن قريش", "cal":98, "p":11},
    "cheese_feta": {"name": "جبن فيتا", "cal":264, "p":14}, "cheese_mozzarella": {"name": "موزاريلا", "cal":280, "p":28},
    "rice_white": {"name": "أرز أبيض", "cal":130, "p":2.7}, "rice_brown": {"name": "أرز بني", "cal":111, "p":2.6},
    "oats": {"name": "شوفان", "cal":389, "p":16.9}, "quinoa": {"name": "كينوا", "cal":120, "p":4.4},
    "bulgur": {"name": "برغل/شعير", "cal":83, "p":3.1}, "pasta": {"name": "مكرونة", "cal":131, "p":5},
    "bread_whole": {"name": "خبز أسمر", "cal":247, "p":13}, "bread_white": {"name": "خبز أبيض", "cal":265, "p":9},
    "sweet_potato": {"name": "بطاطا حلوة", "cal":86, "p":1.6}, "potato": {"name": "بطاطس", "cal":87, "p":1.9},
    "lentils": {"name": "عدس", "cal":116, "p":9}, "chickpeas": {"name": "حمص", "cal":164, "p":8.9},
    "kidney_beans": {"name": "فاصوليا حمراء", "cal":127, "p":8.7}, "black_beans": {"name": "فاصوليا سوداء", "cal":132, "p":8.8},
    "almonds": {"name": "لوز", "cal":579, "p":21}, "walnuts": {"name": "جوز", "cal":654, "p":15},
    "peanut_butter": {"name": "زبدة فول سوداني", "cal":588, "p":25}, "chia_seeds": {"name": "بذور الشيا", "cal":486, "p":16.5},
    "flax_seeds": {"name": "بذور الكتان", "cal":534, "p":18}, "olive_oil": {"name": "زيت زيتون", "cal":884, "p":0},
    "avocado": {"name": "أفوكادو", "cal":160, "p":2}, "banana": {"name": "موز", "cal":89, "p":1.1},
    "apple": {"name": "تفاح", "cal":52, "p":0.3}, "orange": {"name": "برتقال", "cal":47, "p":0.9},
    "berries": {"name": "توت (مجمد)", "cal":35, "p":0.4}, "broccoli": {"name": "بروكلي", "cal":34, "p":2.8},
    "spinach": {"name": "سبانخ", "cal":23, "p":2.9}, "carrots": {"name": "جزر", "cal":41, "p":0.9},
    "cucumber": {"name": "خيار", "cal":16, "p":0.6}, "tomato": {"name": "طماطم", "cal":18, "p":0.9},
}

def calculate_macros(weight, height, age, goal):
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
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

if "page" not in st.session_state: st.session_state.page = "login"
if "user" not in st.session_state: st.session_state.user = None
if "targets" not in st.session_state: st.session_state.targets = None

# ==========================================
# 4. PAGES
# ==========================================
if st.session_state.page == "login":
    st.markdown("<h1 style='text-align:center; color:#0056b3;'>💊 NutraX Final</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["تسجيل الدخول", "إنشاء حساب جديد"])
    with tab1:
        with st.form("login_form"):
            e = st.text_input("البريد الإلكتروني")
            p = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول"):
                c.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hash_pass(p)))
                u = c.fetchone()
                if u:
                    st.session_state.user = u
                    st.session_state.page = "dashboard"
                    st.rerun()
                else: st.error("البيانات غير صحيحة")
    with tab2:
        with st.form("reg_form"):
            st.subheader("بيانات التسجيل")
            n = st.text_input("الاسم الكامل")
            e = st.text_input("البريد الإلكتروني")
            p = st.text_input("كلمة المرور", type="password")
            by = st.number_input("سنة الميلاد", 1950, 2010, 2000)
            country = st.selectbox("بلد المنشأ", ["Egypt", "Saudi Arabia", "UAE", "Kuwait", "Qatar", "USA", "UK", "Other"])
            if st.form_submit_button("إنشاء حساب"):
                try:
                    c.execute("INSERT INTO users (email, password, name, birth_year, country, is_admin) VALUES (?, ?, ?, ?, ?, 0)", 
                              (e, hash_pass(p), n, by, country))
                    conn.commit()
                    st.success("تم إنشاء الحساب بنجاح! سجل دخولك الآن.")
                except: st.error("البريد الإلكتروني مستخدم من قبل.")

else:
    u = st.session_state.user
    u_id = u[0]
    with st.sidebar:
        st.markdown(f"<div style='text-align:center; margin-bottom:20px'><h3>{u[3]}</h3></div>", unsafe_allow_html=True)
        if st.button("🏠 الرئيسية", key="btn_home"): st.session_state.page="dashboard"; st.rerun()
        if st.button("👤 الإعدادات والهدف", key="btn_profile"): st.session_state.page="profile_setup"; st.rerun()
        if st.button("📅 مصمم الجدول", key="btn_planner"): st.session_state.page="planner"; st.rerun()
        if st.button("💾 جداولي المحفوظة", key="btn_saved"): st.session_state.page="saved"; st.rerun()
        if st.button("📈 سجل الوزن", key="btn_history"): st.session_state.page="history"; st.rerun()
        if st.button("🚪 خروج", key="btn_logout"):
            st.session_state.user=None; st.session_state.page="login"; st.rerun()

    if st.session_state.page == "dashboard":
        st.title(f"أهلاً بك، {u[3]}")
        c1, c2, c3 = st.columns(3)
        c.execute("SELECT COUNT(*) FROM saved_plans WHERE user_id=?", (u_id,))
        c1.metric("الجداول المحفوظة", c.fetchone()[0])
        if st.session_state.targets: c2.metric("هدفك اليومي", f"{st.session_state.targets['cal']} kcal")
        c.execute("SELECT weight FROM tracking WHERE user_id=? ORDER BY id DESC LIMIT 1", (u_id,))
        last_w = c.fetchone()
        c3.metric("آخر وزن", f"{last_w[0] if last_w else '---'} kg")

    elif st.session_state.page == "profile_setup":
        st.title("إعداداتك الغذائية")
        with st.form("setup_form"):
            col1, col2 = st.columns(2)
            with col1:
                h = st.number_input("الطول (سم)", value=float(u[4] or 170))
                w = st.number_input("الوزن (كجم)", value=float(u[5] or 70))
            with col2:
                age = st.number_input("العمر", value=25)
                goal = st.selectbox("هدفك", ["maintain", "fat_loss", "muscle_gain"], format_func=lambda x: {"maintain":"ثبات", "fat_loss":"خسارة", "muscle_gain":"عضل"}[x])
            if st.form_submit_button("حفظ وحساب"):
                c.execute("UPDATE users SET height=?, weight=?, goal=?, birth_year=? WHERE id=?", (h, w, goal, datetime.now().year - age, u_id))
                conn.commit()
                target = calculate_macros(w, h, age, goal)
                st.session_state.targets = {'cal': target, 'goal': goal}
                c.execute("SELECT * FROM users WHERE id=?", (u_id,))
                st.session_state.user = c.fetchone()
                st.success("تم الحفظ!"); st.session_state.page="planner"; st.rerun()

    elif st.session_state.page == "planner":
        st.title("مصمم الجدول الغذائي")
        if not st.session_state.targets:
            st.warning("اذهب للإعدادات أولاً.")
            if st.button("الذهاب للإعدادات", key="to_setup"): st.session_state.page="profile_setup"; st.rerun()
            st.stop()
        
        target = st.session_state.targets['cal']
        st.info(f"الهدف اليومي: {target} kcal")
        days = st.number_input("عدد الأيام", 1, 30, 1)
        plan = {}
        total_cal = 0
        
        for d in range(days):
            with st.expander(f"📅 يوم {d+1}", expanded=(d==0)):
                plan[d] = {}
                cols = st.columns(4)
                meals = ["فطار", "غداء", "عشاء", "سناك"]
                for i, meal in enumerate(meals):
                    with cols[i]:
                        st.write(f"**{meal}**")
                        foods = st.multiselect(f"أضف أكل", list(LOCAL_DB.keys()), key=f"sel_{meal}_{d}")
                        plan[d][meal] = {}
                        for f in foods:
                            g = st.number_input(f"{LOCAL_DB[f]['name']} (جم)", 0, 1000, 100, key=f"inp_{f}_{meal}_{d}")
                            if g > 0:
                                plan[d][meal][f] = g
                                total_cal += (g/100) * LOCAL_DB[f]["cal"]
                                st.caption(f"{int((g/100)*LOCAL_DB[f]['cal'])} kcal")
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        c1.metric("الإجمالي", f"{int(total_cal)} kcal")
        c2.metric("الفارق", f"{int(total_cal - (target*days))} kcal")
        
        name = st.text_input("اسم الجدول", value=f"جدول {datetime.now().day}-{datetime.now().month}")
        save_type = st.selectbox("نوع الحفظ", ["خاص بي", "للعميل", "عام"])
        if st.button("💾 حفظ الجدول", key="save_plan_btn"):
            c.execute("INSERT INTO saved_plans VALUES (NULL, ?, ?, ?, datetime('now'), ?)", (u_id, name, json.dumps(plan), save_type))
            conn.commit()
            st.success("تم الحفظ!"); st.rerun()

    elif st.session_state.page == "saved":
        st.title("جداولي المحفوظة")
        filter_type = st.selectbox("فلتر", ["الكل", "خاص بي", "للعميل", "عام"])
        query = "SELECT id, plan_name, created_at, type FROM saved_plans WHERE user_id=?"
        params = [u_id]
        if filter_type != "الكل":
            query += " AND type=?"; params.append(filter_type)
        c.execute(query, params)
        data = c.fetchall()
        for pid, name, date, ptype in data:
            with st.expander(f"📂 {name} ({ptype})"):
                c1, c2 = st.columns(2)
                with c1:
                    c.execute("SELECT plan_data FROM saved_plans WHERE id=?", (pid,))
                    p = json.loads(c.fetchone()[0])
                    for d, meals in p.items():
                        st.write(f"يوم {int(d)+1}")
                        for m, foods in meals.items():
                            st.write(f"- {m}: {', '.join([f'{LOCAL_DB[k][\"name\"]} {v}g' for k,v in foods.items() if v>0])}")
                with c2:
                    if st.button("🛒 قائمة المشتريات", key=f"shop_{pid}"):
                        c.execute("SELECT plan_data FROM saved_plans WHERE id=?", (pid,))
                        shop = generate_shopping_list(json.loads(c.fetchone()[0]))
                        st.subheader("المشتريات")
                        for k,v in shop.items(): st.write(f"- {LOCAL_DB[k]['name']}: {v}جم")

    elif st.session_state.page == "history":
        st.title("سجل الوزن")
        with st.form("log_w"):
            w = st.number_input("وزن اليوم", 30.0, 300.0)
            if st.form_submit_button("تسجيل"):
                c.execute("INSERT INTO tracking VALUES (NULL, ?, ?, datetime('now'))", (u_id, w))
                conn.commit(); st.success("تم"); st.rerun()
        c.execute("SELECT date, weight FROM tracking WHERE user_id=? ORDER BY id ASC", (u_id,))
        data = c.fetchall()
        if data: st.line_chart({"الوزن": [d[1] for d in data]})
        else: st.info("لا توجد سجلات.")

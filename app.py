import streamlit as st
import sqlite3
import hashlib
import os
import json
from datetime import datetime

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(page_title="NutraX V4", page_icon="💊", layout="wide")

# تنسيقات بسيطة ونظيفة
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    .profile-card { background: linear-gradient(135deg, #0056b3, #007bff); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,123,255,0.3); }
    .goal-btn { background: white; border: 2px solid #e0e0e0; border-radius: 12px; padding: 25px; text-align: center; cursor: pointer; transition: 0.2s; margin-bottom: 15px; }
    .goal-btn:hover { border-color: #007bff; transform: translateY(-3px); box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .goal-icon { font-size: 2.5em; display: block; margin-bottom: 10px; }
    .metric-box { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; border: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. قاعدة البيانات
# ==========================================
DB_FILE = "nutrax_v4.db"

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
    c.execute("CREATE TABLE IF NOT EXISTS saved_plans (id INTEGER PRIMARY KEY, user_id INTEGER, plan_name TEXT, plan_data TEXT, created_at TEXT)")
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
    "oats": {"name_ar": "شوفان", "cal": 389, "p": 16.9, "c": 66, "f": 6.9},
    "brown rice": {"name_ar": "أرز بني", "cal": 111, "p": 2.6, "c": 23, "f": 0.9},
    "white rice": {"name_ar": "أرز أبيض", "cal": 130, "p": 2.7, "c": 28, "f": 0.3},
    "pasta": {"name_ar": "مكرونة", "cal": 131, "p": 5, "c": 25, "f": 1.1},
    "bread whole": {"name_ar": "خبز قمح كامل", "cal": 247, "p": 13, "c": 41, "f": 3.4},
    "sweet potato": {"name_ar": "بطاطا حلوة", "cal": 86, "p": 1.6, "c": 20, "f": 0.1},
    "potato": {"name_ar": "بطاطس مسلوقة", "cal": 87, "p": 1.9, "c": 20, "f": 0.1},
    "almonds": {"name_ar": "لوز", "cal": 579, "p": 21, "c": 22, "f": 50},
    "olive oil": {"name_ar": "زيت زيتون", "cal": 884, "p": 0, "c": 0, "f": 100},
    "apple": {"name_ar": "تفاح", "cal": 52, "p": 0.3, "c": 14, "f": 0.2},
    "banana": {"name_ar": "موز", "cal": 89, "p": 1.1, "c": 23, "f": 0.3},
    "broccoli": {"name_ar": "بروكلي", "cal": 34, "p": 2.8, "c": 7, "f": 0.4},
    "spinach": {"name_ar": "سبانخ", "cal": 23, "p": 2.9, "c": 3.6, "f": 0.4},
}

# ==========================================
# 4. حالة النظام
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
# متغيرات للتحكم في التسلسل
if 'metrics_calculated' not in st.session_state: st.session_state.metrics_calculated = False

# ==========================================
# 5. الصفحات
# ==========================================

if st.session_state.page == 'login':
    col_l, col_c, col_r = st.columns([1,2,1])
    with col_c:
        st.markdown("<h1 style='text-align:center; color:#0056b3;'>💊 NutraX V4</h1>", unsafe_allow_html=True)
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
                        c.execute("INSERT INTO users (email, password, name, birth_year, is_admin) VALUES (?, ?, ?, ?, 0)", (e, hash_pass(p), n, by))
                        conn.commit()
                        st.success("تم التسجيل! سجل دخولك الآن.")
                    except: st.error("البريد مستخدم من قبل")

# --- التطبيق الرئيسي ---
else:
    u = st.session_state.user
    u_id, u_name, u_email = u[0], u[3], u[1]
    
    with st.sidebar:
        st.markdown(f"<div class='profile-card'><div style='font-size:2em'>👤</div><div class='profile-name'>{u_name}</div></div>", unsafe_allow_html=True)
        st.divider()
        if st.button("🏠 الرئيسية"): st.session_state.page = 'dashboard'; st.rerun()
        if st.button("👤 الملف الشخصي والأهداف"): st.session_state.page = 'profile'; st.rerun()
        if st.button("🥗 مصمم الجدول"): st.session_state.page = 'planner'; st.rerun()
        if st.button("🥗 جداولي المحفوظة"): st.session_state.page = 'saved'; st.rerun()
        if st.button("🚪 خروج"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

    # --- 1. الرئيسية ---
    if st.session_state.page == 'dashboard':
        st.title(f"أهلاً بك، {u_name}")
        st.info("للبدء في إنشاء جدولك الغذائي، اذهب إلى 'الملف الشخصي والأهداف'.")

    # --- 2. الملف الشخصي (التسلسل المطلوب) ---
    elif st.session_state.page == 'profile':
        st.title("إعداداتك الغذائية")
        
        # إذا لم يتم الحساب بعد، اظهر الفورم فقط
        if not st.session_state.metrics_calculated:
            st.subheader("الخطوة 1: أدخل بياناتك")
            with st.form("calculate_form"):
                col1, col2 = st.columns(2)
                with col1:
                    height = st.number_input("الطول (سم)", min_value=100, max_value=250, value=170)
                    weight = st.number_input("الوزن (كجم)", min_value=30, max_value=300, value=70)
                with col2:
                    age = st.number_input("العمر", min_value=10, max_value=100, value=25)
                    gender = st.selectbox("الجنس", ["ذكر", "أنثى"])
                
                if st.form_submit_button("احسب السعرات والـ BMI", type="primary"):
                    # الحسابات
                    bmi = weight / ((height/100)**2)
                    if gender == "ذكر":
                        bmr = 10 * weight + 6.25 * height - 5 * age + 5
                    else:
                        bmr = 10 * weight + 6.25 * height - 5 * age - 161
                    
                    tdee = bmr * 1.55 # نشاط متوسط افتراضي
                    
                    # تخزين النتائج
                    st.session_state['user_metrics'] = {
                        'bmi': round(bmi, 1),
                        'bmr': int(bmr),
                        'tdee': int(tdee),
                        'weight': weight,
                        'height': height
                    }
                    # تفعيل الحالة
                    st.session_state.metrics_calculated = True
                    st.rerun()
        
        # إذا تم الحساب، اظهر النتائج والأهداف
        else:
            metrics = st.session_state['user_metrics']
            
            # عرض النتائج
            st.success("تم احتساب بياناتك بنجاح!")
            c1, c2, c3 = st.columns(3)
            c1.metric("مؤشر الكتلة (BMI)", metrics['bmi'])
            c2.metric("معدل الحرق الأساسي (BMR)", f"{metrics['bmr']} kcal")
            c3.metric("معدل الحرق الكلي (TDEE)", f"{metrics['tdee']} kcal")
            
            st.markdown("---")
            st.subheader("الخطوة 2: اختر هدفك")
            st.info("اختر الهدف المناسب لك للانتقال لتصميم الجدول الغذائي.")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("<div class='goal-btn'><span class='goal-icon'>🔥</span><b>خسارة دهون</b></div>", unsafe_allow_html=True)
                if st.button("ابدأ خسارة الدهون", key="g1"):
                    target = metrics['tdee'] - 400
                    st.session_state['plan_target'] = {'cal': target, 'goal': 'fat_loss'}
                    st.session_state.page = 'planner'
                    st.rerun()

            with col2:
                st.markdown("<div class='goal-btn'><span class='goal-icon'>💪</span><b>بناء عضل</b></div>", unsafe_allow_html=True)
                if st.button("ابدأ بناء العضل", key="g2"):
                    target = metrics['tdee'] + 400
                    st.session_state['plan_target'] = {'cal': target, 'goal': 'muscle_gain'}
                    st.session_state.page = 'planner'
                    st.rerun()

            with col3:
                st.markdown("<div class='goal-btn'><span class='goal-icon'>⚖️</span><b>ثبات وزن</b></div>", unsafe_allow_html=True)
                if st.button("الحفاظ على الوزن", key="g3"):
                    target = metrics['tdee']
                    st.session_state['plan_target'] = {'cal': target, 'goal': 'maintain'}
                    st.session_state.page = 'planner'
                    st.rerun()

            st.markdown("---")
            if st.button("🔄 إعادة حساب البيانات"):
                st.session_state.metrics_calculated = False
                st.rerun()

    # --- 3. مصمم الجدول ---
    elif st.session_state.page == 'planner':
        st.title("مصمم جدولك الغذائي")
        
        if 'plan_target' not in st.session_state:
            st.warning("يرجى الذهاب للملف الشخصي وحساب بياناتك أولاً.")
            if st.button("الذهاب للملف الشخصي"): st.session_state.page = 'profile'; st.rerun()
            st.stop()

        target = st.session_state['plan_target']
        goal_name = {'fat_loss': 'خسارة دهون', 'muscle_gain': 'بناء عضل', 'maintain': 'ثبات وزن'}[target['goal']]
        
        st.info(f"هدفك: {goal_name} | السعرات المستهدفة: {target['cal']} kcal")
        
        # القالب
        template = {
            "الإفطار": {"oats": 50, "eggs": 100, "apple": 100},
            "الغداء": {"chicken breast": 150, "brown rice": 100, "broccoli": 100},
            "العشاء": {"salmon": 120, "sweet potato": 150, "spinach": 100},
            "سناك": {"greek yogurt": 150, "almonds": 20}
        }
        
        if target['goal'] == 'muscle_gain':
            template["الغداء"]["white rice"] = 150 # زيادة كارب
            template["سناك"]["peanut butter"] = 20
            del template["الغداء"]["brown rice"]
        
        edited_plan = {}
        total_cal = 0
        
        for meal, foods in template.items():
            st.write(f"### {meal}")
            cols = st.columns(len(foods))
            edited_plan[meal] = {}
            
            for idx, (f_key, def_g) in enumerate(foods.items()):
                with cols[idx]:
                    if f_key in LOCAL_DB:
                        f_name = LOCAL_DB[f_key]['name_ar']
                        new_g = st.number_input(f"{f_name} (جم)", value=int(def_g), key=f"{meal}_{f_key}")
                        edited_plan[meal][f_key] = new_g
                        cal = (new_g / 100) * LOCAL_DB[f_key]['cal']
                        total_cal += cal

        st.metric("المجموع الحالي", f"{int(total_cal)} kcal", delta=f"{int(total_cal - target['cal'])} kcal")

        # الحفظ
        plan_name = st.text_input("اسم الجدول", value=f"جدول {goal_name} {datetime.now().day}")
        if st.button("💾 حفظ الجدول"):
            c.execute("INSERT INTO saved_plans (user_id, plan_name, plan_data, created_at) VALUES (?, ?, ?, datetime('now'))",
                      (u_id, plan_name, json.dumps(edited_plan)))
            conn.commit()
            st.success("تم الحفظ!")

    # --- 4. الجداول المحفوظة ---
    elif st.session_state.page == 'saved':
        st.title("جداولي المحفوظة")
        c.execute("SELECT id, plan_name, created_at FROM saved_plans WHERE user_id=? ORDER BY id DESC", (u_id,))
        plans = c.fetchall()
        if not plans: st.info("لا توجد جداول محفوظة.")
        for pid, pname, pdate in plans:
            with st.expander(f"📅 {pname} - {pdate}"):
                c.execute("SELECT plan_data FROM saved_plans WHERE id=?", (pid,))
                data = json.loads(c.fetchone()[0])
                for m, foods in data.items():
                    st.write(f"**{m}**")
                    for k, v in foods.items():
                        if k in LOCAL_DB:
                            st.write(f"- {LOCAL_DB[k]['name_ar']}: {v} جم")
                if st.button("حذف", key=f"del_{pid}"):
                    c.execute("DELETE FROM saved_plans WHERE id=?", (pid,))
                    conn.commit()
                    st.rerun()

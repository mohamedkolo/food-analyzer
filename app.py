import streamlit as st
import sqlite3
import hashlib
import os
import json
from datetime import datetime

# ==========================================
# 1. الإعدادات
# ==========================================
st.set_page_config(page_title="NutraX Pro", page_icon="💊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    .profile-card { background: linear-gradient(135deg, #0056b3, #007bff); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,123,255,0.3); }
    .goal-btn { background: white; border: 2px solid #e0e0e0; border-radius: 12px; padding: 20px; text-align: center; cursor: pointer; transition: 0.3s; margin-bottom: 10px; }
    .goal-btn:hover { border-color: #007bff; transform: translateY(-3px); }
    .goal-btn.selected { border-color: #007bff; background-color: #f0f7ff; }
    .goal-icon { font-size: 2.5em; display: block; margin-bottom: 5px; }
    .card { background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #eee; }
    .data-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .data-table th { background: #f8f9fa; padding: 12px; text-align: right; }
    .data-table td { padding: 12px; border-bottom: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. قاعدة البيانات (مع جدول الحفظ)
# ==========================================
DB_FILE = "nutrax_pro_v3.db"

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
    c.execute("CREATE TABLE IF NOT EXISTS tracking (id INTEGER PRIMARY KEY, user_id INTEGER, weight REAL, date TEXT)")
    # جدول جديد لحفظ الجداول
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

# دالة حساب السعرات والماكرو
def calculate_macros(weight, height, age, goal_type):
    # معادلة Mifflin-St Jeor (تقريبية للذكر)
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
    tdee = bmr * 1.55 # نشاط متوسط
    
    target_cal = tdee
    if goal_type == "fat_loss": target_cal -= 400
    elif goal_type == "muscle_gain": target_cal += 400
    
    # توزيع الماكرو
    if goal_type == "fat_loss":
        p_pct, f_pct, c_pct = 0.40, 0.30, 0.30
    elif goal_type == "muscle_gain":
        p_pct, f_pct, c_pct = 0.30, 0.25, 0.45
    else:
        p_pct, f_pct, c_pct = 0.30, 0.30, 0.40
        
    pro_g = (target_cal * p_pct) / 4
    fat_g = (target_cal * f_pct) / 9
    carb_g = (target_cal * c_pct) / 4
    
    return int(target_cal), int(pro_g), int(fat_g), int(carb_g)

# ==========================================
# 4. حالة النظام
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'plan_data' not in st.session_state: st.session_state.plan_data = None # لتخزين الجدول مؤقتاً

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

# --- التطبيق الرئيسي ---
else:
    u = st.session_state.user
    u_id, u_name, u_email, u_goal, is_admin = u[0], u[3], u[1], u[7], u[8]
    
    with st.sidebar:
        st.markdown(f"<div class='profile-card'><div style='font-size:2em'>👤</div><div class='profile-name'>{u_name}</div></div>", unsafe_allow_html=True)
        st.divider()
        if st.button("🏠 الرئيسية"): st.session_state.page = 'dashboard'; st.rerun()
        if st.button("👤 الملف الشخصي والأهداف"): st.session_state.page = 'profile'; st.rerun()
        if st.button("🥗 مصمم الجدول"): st.session_state.page = 'planner'; st.rerun()
        if st.button("🥗 جداولي المحفوظة"): st.session_state.page = 'saved_plans'; st.rerun()
        if st.button("🔍 محلل الطعام"): st.session_state.page = 'analyzer'; st.rerun()
        if st.button("🚪 خروج"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

    # --- 1. الرئيسية ---
    if st.session_state.page == 'dashboard':
        st.title(f"أهلاً بك، {u_name}")
        w = u[6] or 70
        h = u[5] or 170
        bmi = w / ((h/100)**2)
        c1, c2, c3 = st.columns(3)
        c1.metric("الوزن", f"{w} kg")
        c2.metric("الطول", f"{h} cm")
        c3.metric("BMI", f"{bmi:.1f}")
        st.info("اذهب إلى 'الملف الشخصي' لاختيار هدفك وحساب جدولك الغذائي.")

    # --- 2. الملف الشخصي (المنطق الجديد) ---
    elif st.session_state.page == 'profile':
        st.title("إعدادات الملف الشخصي")
        
        # فورم البيانات الأساسية
        with st.form("up_basic"):
            col1, col2 = st.columns(2)
            with col1:
                nn = st.text_input("الاسم", value=u_name)
                nh = st.number_input("الطول (سم)", value=float(u[5] or 170))
            with col2:
                nw = st.number_input("الوزن (كجم)", value=float(u[6] or 70))
                age = st.number_input("العمر", value=int(datetime.now().year - (u[4] or 2000)))
            if st.form_submit_button("حفظ البيانات"):
                c.execute("UPDATE users SET name=?, height=?, weight=?, birth_year=? WHERE id=?", (nn, nh, nw, datetime.now().year - age, u_id))
                conn.commit()
                st.success("تم التحديث"); st.rerun()

        st.markdown("---")
        st.subheader("اختر هدفك وابدأ التصميم")
        st.warning("لما تضغط على هدف، سيتم حساب احتياجك ونقلك لصفحة التصميم فوراً.")
        
        col1, col2, col3 = st.columns(3)
        
        # زر خسارة
        with col1:
            style = "border-color:#007bff; background-color:#f0f7ff;" if u_goal == "fat_loss" else ""
            st.markdown(f"<div class='goal-btn {style}'><span class='goal-icon'>🔥</span><b>خسارة دهون</b></div>", unsafe_allow_html=True)
            if st.button("ابدأ تصميم جدول خسارة", key="btn_fat"):
                # الحساب والانتقال
                w = u[6] or 70
                h = u[5] or 170
                age = datetime.now().year - (u[4] or 2000)
                cal, p, f, c = calculate_macros(w, h, age, "fat_loss")
                st.session_state['calc'] = {'cal': cal, 'p': p, 'f': f, 'c': c, 'goal': 'fat_loss'}
                c.execute("UPDATE users SET goal='fat_loss' WHERE id=?", (u_id,)); conn.commit()
                st.session_state.page = 'planner'; st.rerun()

        # زر عضل
        with col2:
            style = "border-color:#28a745; background-color:#f0fff4;" if u_goal == "muscle_gain" else ""
            st.markdown(f"<div class='goal-btn {style}'><span class='goal-icon'>💪</span><b>بناء عضل</b></div>", unsafe_allow_html=True)
            if st.button("ابدأ تصميم جدول عضل", key="btn_muscle"):
                w = u[6] or 70
                h = u[5] or 170
                age = datetime.now().year - (u[4] or 2000)
                cal, p, f, c = calculate_macros(w, h, age, "muscle_gain")
                st.session_state['calc'] = {'cal': cal, 'p': p, 'f': f, 'c': c, 'goal': 'muscle_gain'}
                c.execute("UPDATE users SET goal='muscle_gain' WHERE id=?", (u_id,)); conn.commit()
                st.session_state.page = 'planner'; st.rerun()

        # زر ثبات
        with col3:
            style = "border-color:#ffc107; background-color:#fffbe6;" if u_goal == "maintain" else ""
            st.markdown(f"<div class='goal-btn {style}'><span class='goal-icon'>⚖️</span><b>ثبات وزن</b></div>", unsafe_allow_html=True)
            if st.button("ابدأ تصميم جدول ثبات", key="btn_main"):
                w = u[6] or 70
                h = u[5] or 170
                age = datetime.now().year - (u[4] or 2000)
                cal, p, f, c = calculate_macros(w, h, age, "maintain")
                st.session_state['calc'] = {'cal': cal, 'p': p, 'f': f, 'c': c, 'goal': 'maintain'}
                c.execute("UPDATE users SET goal='maintain' WHERE id=?", (u_id,)); conn.commit()
                st.session_state.page = 'planner'; st.rerun()

    # --- 3. مصمم الجدول (التصميم والحفظ) ---
    elif st.session_state.page == 'planner':
        st.title("تصميم وحفظ جدولك الغذائي")
        
        # عرض الأهداف المحسوبة
        if 'calc' in st.session_state:
            calc = st.session_state['calc']
            st.success(f"🎯 تم ضبط الجدول بناءً على هدفك: {calc['goal'].upper()}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("الهدف اليومي", f"{calc['cal']} kcal")
            c2.metric("بروتين", f"{calc['p']} g")
            c3.metric("كارب", f"{calc['c']} g")
            c4.metric("دهون", f"{calc['f']} g")
        else:
            st.info("الرجاء الذهاب للملف الشخصي وتحديد هدفك أولاً.")
            st.stop()

        st.markdown("---")
        st.subheader("عدل الكميات حسب رغبتك ثم احفظ الجدول")
        
        # القالب الافتراضي
        template = {
            "الإفطار": {"oats": 50, "eggs": 100},
            "الغداء": {"chicken breast": 150, "brown rice": 100, "broccoli": 100},
            "العشاء": {"salmon": 120, "sweet potato": 150, "spinach": 100},
            "سناك": {"apple": 1, "almonds": 20}
        }
        
        # واجهة التعديل
        edited_plan = {}
        total_cal = 0
        
        for meal_name, foods in template.items():
            st.write(f"### {meal_name}")
            cols = st.columns(len(foods))
            edited_plan[meal_name] = {}
            
            for idx, (food_key, default_g) in enumerate(foods):
                with cols[idx]:
                    food_name = LOCAL_DB[food_key]['name_ar']
                    new_g = st.number_input(f"{food_name} (جم)", value=default_g, key=f"{meal_name}_{food_key}")
                    edited_plan[meal_name][food_key] = new_g
                    
                    # الحساب الفوري
                    cal_per_100 = LOCAL_DB[food_key]['cal']
                    total_cal += (new_g / 100) * cal_per_100

        st.markdown("---")
        st.metric("إجمالي الجدول الحالي", f"{int(total_cal)} kcal", delta=f"{int(total_cal - calc['cal'])} kcal عن الهدف")

        # زر الحفظ
        plan_name = st.text_input("اسم الجدول (للحفظ)", value=f"جدول {calc['goal']} {datetime.now().strftime('%d-%m')}")
        if st.button("💾 حفظ هذا الجدول في قاعدة البيانات"):
            plan_json = json.dumps(edited_plan)
            c.execute("INSERT INTO saved_plans (user_id, plan_name, plan_data, created_at) VALUES (?, ?, ?, datetime('now'))",
                      (u_id, plan_name, plan_json))
            conn.commit()
            st.success("تم حفظ الجدول بنجاح! يمكنك مشاهدته في قسم 'جداولي المحفوظة'.")

    # --- 4. جداولي المحفوظة ---
    elif st.session_state.page == 'saved_plans':
        st.title("جداولي المحفوظة")
        c.execute("SELECT id, plan_name, created_at FROM saved_plans WHERE user_id=? ORDER BY id DESC", (u_id,))
        plans = c.fetchall()
        
        if not plans:
            st.info("لم تقم بحفظ أي جداول بعد.")
        else:
            for plan_id, p_name, p_date in plans:
                with st.expander(f"📅 {p_name} - {p_date}"):
                    c.execute("SELECT plan_data FROM saved_plans WHERE id=?", (plan_id,))
                    data = json.loads(c.fetchone()[0])
                    
                    # عرض تفاصيل الجدول المحفوظ
                    for meal, foods in data.items():
                        st.write(f"**{meal}**")
                        for f_key, f_g in foods.items():
                            if f_key in LOCAL_DB:
                                f_name = LOCAL_DB[f_key]['name_ar']
                                f_cal = LOCAL_DB[f_key]['cal']
                                st.write(f"- {f_name}: {f_g} جم ({int((f_g/100)*f_cal)} kcal)")
                    if st.button("🗑️ حذف هذا الجدول", key=f"del_{plan_id}"):
                        c.execute("DELETE FROM saved_plans WHERE id=?", (plan_id,))
                        conn.commit()
                        st.rerun()

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

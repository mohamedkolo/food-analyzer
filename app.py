# ===============================
# DNP PRO ULTIMATE MERGED SYSTEM
# ===============================

import streamlit as st
import sqlite3
import hashlib
import random
import requests
import copy
from datetime import datetime

# ===============================
# PAGE CONFIG & STYLES (From Code 2)
# ===============================
st.set_page_config(
    page_title="DNP PRO — النظام المتكامل",
    page_icon="🥗",
    layout="centered",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    .main { background-color: #f8f9fa; }
    
    /* Cards & UI Elements */
    .metric-card {
        background: white; border-radius: 12px; padding: 14px 18px;
        margin: 6px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        display: flex; justify-content: space-between; align-items: center;
    }
    .section-title {
        font-size: 1.05em; font-weight: 700; color: #1b5e20;
        border-right: 4px solid #4caf50; padding-right: 10px; margin: 18px 0 8px;
    }
    
    /* Plans Cards */
    .plan-container { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }
    .plan-card {
        background: white; border-radius: 16px; padding: 25px;
        width: 280px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-top: 5px solid #ddd; transition: transform 0.2s;
    }
    .plan-card:hover { transform: translateY(-5px); }
    .plan-free { border-color: #9e9e9e; }
    .plan-pro { border-color: #2196f3; }
    .plan-coach { border-color: #ff9800; }
    .plan-price { font-size: 2em; font-weight: bold; margin: 10px 0; color: #333; }
    .plan-features { list-style: none; padding: 0; text-align: right; margin: 20px 0; }
    .plan-features li { padding: 5px 0; border-bottom: 1px solid #eee; }
    .btn-plan {
        display: block; width: 100%; padding: 10px; border: none; border-radius: 8px;
        color: white; font-weight: bold; cursor: pointer; margin-top: 10px;
    }

    /* Meal Planner Styles */
    .meal-card {
        background: white; border-radius: 14px; padding: 16px 20px;
        margin: 10px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-right: 5px solid #4caf50;
    }
    .total-bar {
        background: linear-gradient(135deg, #1b5e20, #4caf50);
        color: white; border-radius: 14px; padding: 18px 24px; margin: 16px 0; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# DB SETUP (From Code 1)
# ===============================
conn = sqlite3.connect("dnp_pro.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,
    is_admin INTEGER DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    calories INTEGER,
    protein INTEGER,
    carbs INTEGER,
    fat INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    weight REAL,
    date TEXT
)
""")
conn.commit()

# ===============================
# DATA Dictionaries (From Code 2)
# ===============================
LOCAL_DB = {
    "apple":          {"name_ar": "تفاح",            "nutrients": {"Energy":52,  "Protein":0.26,"Total lipid (fat)":0.17,"Carbohydrate, by difference":13.81,"Fiber, total dietary":2.4,"Sugars, total including NLEA":10.39,"Calcium, Ca":6,"Iron, Fe":0.12,"Potassium, K":107,"Sodium, Na":1,"Vitamin C, total ascorbic acid":4.6,"Vitamin A, RAE":3,"Magnesium, Mg":5,"Phosphorus, P":11,"Zinc, Zn":0.04,"Fatty acids, total saturated":0.03,"Cholesterol":0}},
    "banana":         {"name_ar": "موز",             "nutrients": {"Energy":89,  "Protein":1.09,"Total lipid (fat)":0.33,"Carbohydrate, by difference":22.84,"Fiber, total dietary":2.6,"Sugars, total including NLEA":12.23,"Calcium, Ca":5,"Iron, Fe":0.26,"Potassium, K":358,"Sodium, Na":1,"Vitamin C, total ascorbic acid":8.7,"Vitamin A, RAE":3,"Magnesium, Mg":27,"Phosphorus, P":22,"Zinc, Zn":0.15,"Vitamin B-6":0.37,"Folate, total":20,"Fatty acids, total saturated":0.11,"Cholesterol":0}},
    "chicken breast": {"name_ar": "صدر دجاج مشوي",  "nutrients": {"Energy":165, "Protein":31.02,"Total lipid (fat)":3.57,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":15,"Iron, Fe":1.04,"Potassium, K":220,"Sodium, Na":74,"Phosphorus, P":220,"Zinc, Zn":1.0,"Vitamin B-12":0.3,"Niacin":13.7,"Fatty acids, total saturated":1.01,"Cholesterol":85}},
    "egg":            {"name_ar": "بيضة كاملة",      "nutrients": {"Energy":143, "Protein":12.56,"Total lipid (fat)":9.51,"Carbohydrate, by difference":0.72,"Fiber, total dietary":0,"Calcium, Ca":56,"Iron, Fe":1.75,"Potassium, K":138,"Sodium, Na":142,"Phosphorus, P":198,"Zinc, Zn":1.29,"Vitamin A, RAE":160,"Vitamin D (D2 + D3)":2.0,"Vitamin B-12":0.89,"Riboflavin":0.46,"Fatty acids, total saturated":3.13,"Cholesterol":372}},
    "rice":           {"name_ar": "أرز أبيض مطبوخ", "nutrients": {"Energy":130, "Protein":2.69,"Total lipid (fat)":0.28,"Carbohydrate, by difference":28.17,"Fiber, total dietary":0.4,"Calcium, Ca":10,"Iron, Fe":1.49,"Potassium, K":35,"Sodium, Na":1,"Phosphorus, P":43,"Zinc, Zn":0.49,"Fatty acids, total saturated":0.08,"Cholesterol":0}},
    "salmon":         {"name_ar": "سمك سلمون",       "nutrients": {"Energy":208, "Protein":20.42,"Total lipid (fat)":13.42,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":12,"Iron, Fe":0.8,"Potassium, K":363,"Sodium, Na":59,"Phosphorus, P":252,"Zinc, Zn":0.64,"Vitamin D (D2 + D3)":11.1,"Vitamin B-12":3.18,"Fatty acids, total saturated":3.05,"Fatty acids, total polyunsaturated":3.77,"Cholesterol":63}},
    "milk":           {"name_ar": "حليب كامل الدسم", "nutrients": {"Energy":61,  "Protein":3.15,"Total lipid (fat)":3.27,"Carbohydrate, by difference":4.78,"Fiber, total dietary":0,"Sugars, total including NLEA":5.05,"Calcium, Ca":113,"Iron, Fe":0.03,"Potassium, K":150,"Sodium, Na":43,"Phosphorus, P":84,"Zinc, Zn":0.37,"Vitamin A, RAE":46,"Vitamin D (D2 + D3)":1.3,"Vitamin B-12":0.45,"Riboflavin":0.17,"Fatty acids, total saturated":1.87,"Cholesterol":10}},
    "bread":          {"name_ar": "خبز أبيض",        "nutrients": {"Energy":265, "Protein":9.0,"Total lipid (fat)":3.2,"Carbohydrate, by difference":49.0,"Fiber, total dietary":2.7,"Calcium, Ca":182,"Iron, Fe":3.6,"Potassium, K":115,"Sodium, Na":491,"Phosphorus, P":108,"Zinc, Zn":0.7,"Fatty acids, total saturated":0.7,"Cholesterol":0}},
    "potato":         {"name_ar": "بطاطا مسلوقة",   "nutrients": {"Energy":87,  "Protein":1.87,"Total lipid (fat)":0.1,"Carbohydrate, by difference":20.13,"Fiber, total dietary":1.8,"Sugars, total including NLEA":0.9,"Calcium, Ca":5,"Iron, Fe":0.31,"Potassium, K":379,"Sodium, Na":4,"Vitamin C, total ascorbic acid":13.0,"Vitamin B-6":0.27,"Magnesium, Mg":20,"Phosphorus, P":44,"Fatty acids, total saturated":0.03,"Cholesterol":0}},
    "oats":           {"name_ar": "شوفان جاف",       "nutrients": {"Energy":389, "Protein":16.89,"Total lipid (fat)":6.9,"Carbohydrate, by difference":66.27,"Fiber, total dietary":10.6,"Calcium, Ca":54,"Iron, Fe":4.72,"Potassium, K":429,"Sodium, Na":2,"Magnesium, Mg":177,"Phosphorus, P":523,"Zinc, Zn":3.97,"Thiamin":0.76,"Riboflavin":0.14,"Fatty acids, total saturated":1.22,"Cholesterol":0}},
    "orange":         {"name_ar": "برتقال",          "nutrients": {"Energy":47,  "Protein":0.94,"Total lipid (fat)":0.12,"Carbohydrate, by difference":11.75,"Fiber, total dietary":2.4,"Sugars, total including NLEA":9.35,"Calcium, Ca":40,"Iron, Fe":0.1,"Potassium, K":181,"Sodium, Na":0,"Vitamin C, total ascorbic acid":53.2,"Folate, total":30,"Fatty acids, total saturated":0.02,"Cholesterol":0}},
    "yogurt":         {"name_ar": "زبادي",           "nutrients": {"Energy":61,  "Protein":3.5,"Total lipid (fat)":3.3,"Carbohydrate, by difference":4.7,"Fiber, total dietary":0,"Sugars, total including NLEA":4.7,"Calcium, Ca":121,"Iron, Fe":0.05,"Potassium, K":155,"Sodium, Na":46,"Phosphorus, P":95,"Vitamin B-12":0.37,"Fatty acids, total saturated":2.1,"Cholesterol":13}},
    "almonds":        {"name_ar": "لوز",             "nutrients": {"Energy":579, "Protein":21.15,"Total lipid (fat)":49.93,"Carbohydrate, by difference":21.55,"Fiber, total dietary":12.5,"Calcium, Ca":264,"Iron, Fe":3.71,"Potassium, K":733,"Sodium, Na":1,"Magnesium, Mg":270,"Phosphorus, P":481,"Zinc, Zn":3.12,"Vitamin E (alpha-tocopherol)":25.63,"Fatty acids, total saturated":3.8,"Cholesterol":0}},
    "lentils":        {"name_ar": "عدس مطبوخ",      "nutrients": {"Energy":116, "Protein":9.02,"Total lipid (fat)":0.38,"Carbohydrate, by difference":20.13,"Fiber, total dietary":7.9,"Calcium, Ca":19,"Iron, Fe":3.33,"Potassium, K":369,"Sodium, Na":2,"Magnesium, Mg":36,"Phosphorus, P":180,"Zinc, Zn":1.27,"Folate, total":181,"Fatty acids, total saturated":0.05,"Cholesterol":0}},
    "tuna":           {"name_ar": "تونة معلبة",     "nutrients": {"Energy":128, "Protein":29.13,"Total lipid (fat)":0.97,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":11,"Iron, Fe":1.3,"Potassium, K":279,"Sodium, Na":396,"Phosphorus, P":237,"Zinc, Zn":0.9,"Vitamin D (D2 + D3)":5.7,"Vitamin B-12":2.52,"Niacin":15.05,"Fatty acids, total saturated":0.25,"Cholesterol":49}},
    "beef":           {"name_ar": "لحم بقري مطبوخ", "nutrients": {"Energy":250, "Protein":26.0,"Total lipid (fat)":15.0,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":18,"Iron, Fe":2.6,"Potassium, K":318,"Sodium, Na":72,"Phosphorus, P":200,"Zinc, Zn":5.3,"Vitamin B-12":2.5,"Niacin":4.0,"Fatty acids, total saturated":5.8,"Cholesterol":87}},
    "cheese":         {"name_ar": "جبن أبيض",       "nutrients": {"Energy":264, "Protein":18.0,"Total lipid (fat)":21.0,"Carbohydrate, by difference":1.3,"Fiber, total dietary":0,"Calcium, Ca":500,"Iron, Fe":0.2,"Potassium, K":93,"Sodium, Na":621,"Phosphorus, P":347,"Zinc, Zn":2.9,"Vitamin A, RAE":175,"Vitamin B-12":0.8,"Riboflavin":0.28,"Fatty acids, total saturated":13.0,"Cholesterol":75}},
    "pasta":          {"name_ar": "مكرونة مطبوخة",  "nutrients": {"Energy":158, "Protein":5.8,"Total lipid (fat)":0.93,"Carbohydrate, by difference":30.86,"Fiber, total dietary":1.8,"Calcium, Ca":7,"Iron, Fe":1.3,"Potassium, K":44,"Sodium, Na":1,"Phosphorus, P":58,"Zinc, Zn":0.51,"Thiamin":0.02,"Folate, total":7,"Fatty acids, total saturated":0.18,"Cholesterol":0}},
}

MEAL_PLAN_TEMPLATES = {
    "خسارة دهون وبناء عضل": {
        "الإفطار": [{"name": "شوفان جاف", "amount": 50, "key": "oats"}, {"name": "بيضة كاملة", "amount": 100, "key": "egg"}],
        "الغداء": [{"name": "صدر دجاج مشوي", "amount": 150, "key": "chicken breast"}, {"name": "أرز أبيض مطبوخ", "amount": 100, "key": "rice"}],
        "العشاء": [{"name": "تونة معلبة", "amount": 100, "key": "tuna"}, {"name": "سلطة خضراء", "amount": 100, "key": "lettuce"}], 
    },
    "زيادة الوزن والعضل": {
        "الإفطار": [{"name": "شوفان جاف", "amount": 80, "key": "oats"}, {"name": "بيضة كاملة", "amount": 150, "key": "egg"}, {"name": "حليب كامل الدسم", "amount": 200, "key": "milk"}],
        "الغداء": [{"name": "صدر دجاج مشوي", "amount": 200, "key": "chicken breast"}, {"name": "أرز أبيض مطبوخ", "amount": 250, "key": "rice"}],
        "العشاء": [{"name": "لحم بقري مطبوخ", "amount": 150, "key": "beef"}, {"name": "مكرونة مطبوخة", "amount": 200, "key": "pasta"}],
    }
}

ARABIC_TO_ENGLISH = {"تفاح": "apple", "موز": "banana", "بيض": "egg", "دجاج": "chicken breast", "أرز": "rice", "لحم": "beef"}

# ===============================
# HELPER FUNCTIONS
# ===============================
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

def calc_bmi(w, h):
    return w / ((h/100)**2)

def calc_bmr(w, h, age, gender):
    if gender == "ذكر":
        return 10*w + 6.25*h - 5*age + 5
    else:
        return 10*w + 6.25*h - 5*age - 161

def get_meal_macros(items):
    # simplified version for dashboard
    total = {"Energy":0, "Protein":0, "Carbohydrate, by difference":0, "Total lipid (fat)":0}
    for item in items:
        key = item.get("key")
        amt = item.get("amount", 100) / 100.0
        if key in LOCAL_DB:
            nuts = LOCAL_DB[key]["nutrients"]
            total["Energy"] += nuts.get("Energy", 0) * amt
            total["Protein"] += nuts.get("Protein", 0) * amt
            total["Carbohydrate, by difference"] += nuts.get("Carbohydrate, by difference", 0) * amt
            total["Total lipid (fat)"] += nuts.get("Total lipid (fat)", 0) * amt
    return total

# ===============================
# AUTHENTICATION SYSTEM
# ===============================
st.title("DNP PRO SYSTEM")

if "user" not in st.session_state:
    st.session_state.user = None

menu = st.sidebar.selectbox("القائمة", ["تسجيل الدخول", "إنشاء حساب"])

if menu == "إنشاء حساب":
    with st.form("register_form"):
        email = st.text_input("البريد الإلكتروني")
        password = st.text_input("كلمة المرور", type="password")
        submit = st.form_submit_button("إنشاء")
        if submit:
            try:
                c.execute("INSERT INTO users (email, password) VALUES (?,?)", (email, hash_pass(password)))
                conn.commit()
                st.success("تم إنشاء الحساب بنجاح! سجل دخولك الآن.")
            except sqlite3.IntegrityError:
                st.error("البريد الإلكتروني مستخدم من قبل.")

if menu == "تسجيل الدخول":
    with st.form("login_form"):
        email = st.text_input("البريد الإلكتروني")
        password = st.text_input("كلمة المرور", type="password")
        submit = st.form_submit_button("دخول")
        if submit:
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hash_pass(password)))
            user = c.fetchone()
            if user:
                st.session_state.user = user
                st.success("تم تسجيل الدخول")
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة")

# ===============================
# MAIN APP LOGIC (If Logged In)
# ===============================
if st.session_state.user:
    user_id = st.session_state.user[0]
    is_admin = st.session_state.user[3]
    
    st.sidebar.markdown("---")
    st.sidebar.success(f"أهلاً، المستخدم رقم {user_id}")
    
    # Navigation
    page = st.sidebar.radio(
        "انتقل إلى:",
        ["📊 لوحة التحكم", "🔍 محلل الأكل", "🍽️ مصمم الوجبات", "💎 الباقات"],
        label_visibility="collapsed"
    )
    
    if is_admin:
        page = st.sidebar.selectbox(
            "أدمن (إدارة النظام)",
            ["📊 لوحة التحكم", "🔍 محلل الأكل", "🍽️ مصمم الوجبات", "💎 الباقات", "🛠️ إدارة الأكل (Admin)"],
            index=0
        )

    # ===========================
    # PAGE 1: DASHBOARD
    # ===========================
    if page == "📊 لوحة التحكم":
        col1, col2 = st.columns(2)
        
        # --- Section 1: BMI & Calorie Calculator (From Code 2) ---
        with col1:
            st.subheader("احتياجاتك اليومية")
            with st.expander("أدخل بياناتك لحساب السعرات", expanded=True):
                gender = st.radio("الجنس", ["ذكر", "أنثى"], horizontal=True)
                age = st.number_input("العمر", 10, 100, 25)
                h = st.number_input("الطول (سم)", 100, 250, 170)
                w = st.number_input("الوزن الحالي (كجم)", 30, 300, 70)
                activity = st.selectbox("النشاط", ["خفيف", "متوسط", "رياضي"])
                goal = st.selectbox("هدفك", ["خسارة دهون", "بناء عضل", "ثبات الوزن"])
                
                if st.button("احسب الآن", use_container_width=True):
                    bmi = calc_bmi(w, h)
                    bmr = calc_bmr(w, h, age, gender)
                    
                    activity_mult = {"خفيف": 1.2, "متوسط": 1.55, "رياضي": 1.8}
                    tdee = bmr * activity_mult[activity]
                    
                    if goal == "خسارة دهون": target = tdee - 400
                    elif goal == "بناء عضل": target = tdee + 400
                    else: target = tdee
                    
                    st.session_state['target_cal'] = int(target)
                    st.session_state['current_weight'] = w

        with col2:
            if 'target_cal' in st.session_state:
                st.metric("مؤشر الكتلة (BMI)", f"{calc_bmi(st.session_state['current_weight'], h):.1f}")
                st.metric("احتياجك من السعرات", f"{st.session_state['target_cal']} kcal")
        
        st.divider()

        # --- Section 2: Weight Tracking (From Code 1) ---
        st.subheader("تتبع وزنك")
        c1, c2 = st.columns([1, 3])
        with c1:
            new_weight = st.number_input("سجل وزن اليوم", value=st.session_state.get('current_weight', 70.0))
            if st.button("حفظ الوزن"):
                c.execute("INSERT INTO tracking (user_id, weight, date) VALUES (?,?,datetime('now'))", (user_id, new_weight))
                conn.commit()
                st.success("تم الحفظ")
        
        with c2:
            # Show Graph
            c.execute("SELECT date, weight FROM tracking WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,))
            data = c.fetchall()
            if data:
                data.reverse() # Ascending order for chart
                dates = [d[0] for d in data]
                weights = [d[1] for d in data]
                st.line_chart(dict(zip(dates, weights)))
            else:
                st.info("لا توجد سجلات سابقة للوزن.")

    # ===========================
    # PAGE 2: FOOD ANALYZER (From Code 2 - Simplified)
    # ===========================
    elif page == "🔍 محلل الأكل":
        st.subheader("تحليل العناصر الغذائية")
        col1, col2 = st.columns([3, 1])
        with col1:
            search = st.text_input("ابحث عن طعام (عربي أو إنجليزي)")
        with col2:
            grams = st.number_input("الكمية (جم)", 100)
        
        if search:
            # Simple Search Logic
            found_key = None
            if search in LOCAL_DB:
                found_key = search
            else:
                for k, v in LOCAL_DB.items():
                    if search in v["name_ar"]:
                        found_key = k
                        break
            
            if found_key:
                item = LOCAL_DB[found_key]
                st.write(f"### {item['name_ar']} ({grams}جم)")
                nuts = item["nutrients"]
                
                # Scale
                factor = grams / 100.0
                cal = nuts.get("Energy", 0) * factor
                pro = nuts.get("Protein", 0) * factor
                carb = nuts.get("Carbohydrate, by difference", 0) * factor
                fat = nuts.get("Total lipid (fat)", 0) * factor
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("سعرات", f"{cal:.0f}")
                c2.metric("بروتين", f"{pro:.1f}g")
                c3.metric("كارب", f"{carb:.1f}g")
                c4.metric("دهون", f"{fat:.1f}g")
            else:
                st.warning("هذا الطعام غير موجود في قاعدة البيانات المحلية.")

    # ===========================
    # PAGE 3: MEAL PLANNER (From Code 2)
    # ===========================
    elif page == "🍽️ مصمم الوجبات":
        st.subheader("صمم جدولك الغذائي")
        
        if 'meal_plan' not in st.session_state:
            st.session_state['meal_plan'] = copy.deepcopy(MEAL_PLAN_TEMPLATES["خسارة دهون وبناء عضل"])
        
        current_plan = st.session_state['meal_plan']
        total_cals = 0
        
        for meal_name, items in current_plan.items():
            with st.expander(f"{meal_name}"):
                for i, item in enumerate(items):
                    cols = st.columns([3, 1, 1])
                    with cols[0]:
                        # Dropdown for food
                        options = list(LOCAL_DB.keys())
                        current_idx = options.index(item['key']) if item['key'] in options else 0
                        new_key = st.selectbox("الطعام", options, index=current_idx, key=f"{meal_name}_{i}")
                        if new_key != item['key']:
                            item['key'] = new_key
                            item['name'] = LOCAL_DB[new_key]['name_ar']
                    
                    with cols[1]:
                        new_amt = st.number_input("جم", 5, 500, int(item['amount']), key=f"amt_{meal_name}_{i}")
                        item['amount'] = new_amt
                
                # Show Meal Total
                macros = get_meal_macros(items)
                st.caption(f"🔥 إجمالي الوجبة: {macros['Energy']:.0f} kcal")
                total_cals += macros['Energy']

        st.markdown(f'<div class="total-bar">🔥 مجموع جدولك: {total_cals:.0f} kcal</div>', unsafe_allow_html=True)

    # ===========================
    # PAGE 4: PACKAGES (Styled from Code 2)
    # ===========================
    elif page == "💎 الباقات":
        st.markdown("<h2 style='text-align:center'>اختر الباقة المناسبة لك</h2>", unsafe_allow_html=True)
        st.markdown("<div class='plan-container'>", unsafe_allow_html=True)
        
        # Free Plan
        st.markdown("""
        <div class='plan-card plan-free'>
            <h3>مجاني</h3>
            <div class='plan-price'>0$</div>
            <ul class='plan-features'>
                <li>✅ تتبع الوزن الأساسي</li>
                <li>✅ حساب BMI</li>
                <li>❌ تحليل الأكل المتقدم</li>
            </ul>
            <button class='btn-plan' style='background:#9e9e9e'>الباقة الحالية</button>
        </div>
        """, unsafe_allow_html=True)
        
        # Pro Plan
        st.markdown("""
        <div class='plan-card plan-pro'>
            <h3>PRO</h3>
            <div class='plan-price'>10$</div>
            <ul class='plan-features'>
                <li>✅ كل مميزات المجاني</li>
                <li>✅ محلل الأكل الشامل</li>
                <li>✅ مصمم الوجبات الذكي</li>
            </ul>
            <button class='btn-plan' style='background:#2196f3'>اشترك الآن</button>
        </div>
        """, unsafe_allow_html=True)
        
        # Coach Plan
        st.markdown("""
        <div class='plan-card plan-coach'>
            <h3>COACH</h3>
            <div class='plan-price'>30$</div>
            <ul class='plan-features'>
                <li>✅ كل مميزات PRO</li>
                <li>✅ متابعة أسبوعية مع مدرب</li>
                <li>✅ تعديل الخطط حسب التقدم</li>
            </ul>
            <button class='btn-plan' style='background:#ff9800'>تواصل معنا</button>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # ===========================
    # PAGE 5: ADMIN ONLY (From Code 1)
    # ===========================
    elif page == "🛠️ إدارة الأكل (Admin)":
        st.subheader("إضافة وجبات جديدة للقاعدة")
        with st.form("add_meal"):
            name = st.text_input("اسم الطعام (إنجليزي - مفتاح)")
            cals = st.number_input("سعرات")
            pro = st.number_input("بروتين")
            carb = st.number_input("كارب")
            fat = st.number_input("دهون")
            if st.form_submit_button("إضافة للقاعدة"):
                c.execute("INSERT INTO meals (name, calories, protein, carbs, fat) VALUES (?,?,?,?,?)",
                          (name, cals, pro, carb, fat))
                conn.commit()
                st.success(f"تمت إضافة {name}")
        
        st.subheader("الوجبات الحالية في قاعدة البيانات")
        c.execute("SELECT * FROM meals")
        for row in c.fetchall():
            st.write(row)

else:
    st.info("يرجى تسجيل الدخول لاستخدام النظام.")

# Close connection when app stops (good practice, though streamlit keeps it alive usually)
# conn.close() 

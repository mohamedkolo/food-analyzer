# =============================================================================
# NutraX V9 - Enhanced Edition
# تحسينات: UI أجمل، ماكروز كاملة، AI Meal Suggester، تقدم يومي، فارق ملون
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
st.set_page_config(page_title="NutraX V9", page_icon="🥗", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
    }

    /* ── Background ── */
    .stApp {
        background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 50%, #0f1923 100%);
        min-height: 100vh;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a5f 0%, #0f2035 100%);
        border-right: 1px solid rgba(0,180,216,0.2);
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: right;
        background: rgba(255,255,255,0.05);
        color: #e8f8ff;
        border: 1px solid rgba(0,180,216,0.15);
        border-radius: 10px;
        padding: 10px 15px;
        margin-bottom: 6px;
        font-family: 'Cairo', sans-serif;
        font-size: 15px;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(0,180,216,0.2);
        border-color: #00b4d8;
        color: white;
        transform: translateX(-3px);
    }

    /* ── Cards ── */
    .stat-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
        border: 1px solid rgba(0,180,216,0.25);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        backdrop-filter: blur(10px);
        transition: transform 0.2s;
    }
    .stat-card:hover { transform: translateY(-3px); }
    .stat-card .label { color: #b8d8ff; font-size: 13px; margin-bottom: 6px; font-weight:600; }
    .stat-card .value { color: #ffffff; font-size: 28px; font-weight: 700; }
    .stat-card .unit  { color: #a8ccee; font-size: 12px; }

    /* ── Macro pills ── */
    .macro-row { display:flex; gap:10px; margin-top:12px; justify-content:center; }
    .macro-pill {
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    .pill-p { background:rgba(76,175,80,0.2); color:#81c784; border:1px solid rgba(76,175,80,0.3); }
    .pill-c { background:rgba(255,152,0,0.2); color:#ffb74d; border:1px solid rgba(255,152,0,0.3); }
    .pill-f { background:rgba(244,67,54,0.2); color:#ef9a9a; border:1px solid rgba(244,67,54,0.3); }

    /* ── Food card ── */
    .food-card {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(0,180,216,0.2);
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 10px;
        border-left: 4px solid #00b4d8;
    }
    .food-card h4 { color: #ffffff; margin: 0 0 8px 0; font-size: 16px; }

    /* ── Progress bar custom ── */
    .progress-wrap { background: rgba(255,255,255,0.08); border-radius:20px; height:12px; overflow:hidden; margin:6px 0; }
    .progress-fill { height:12px; border-radius:20px; transition: width 0.5s ease; }
    .progress-cal { background: linear-gradient(90deg,#00b4d8,#0077b6); }
    .progress-p   { background: linear-gradient(90deg,#4caf50,#2e7d32); }
    .progress-c   { background: linear-gradient(90deg,#ff9800,#e65100); }
    .progress-f   { background: linear-gradient(90deg,#f44336,#b71c1c); }

    /* ── Alert ── */
    .alert-warn {
        background: rgba(255,152,0,0.15);
        border: 1px solid rgba(255,152,0,0.4);
        color: #ffcc80;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
    }

    /* ── Page title ── */
    .page-title {
        color: #00d4ff;
        font-size: 28px;
        font-weight: 700;
        padding-bottom: 6px;
        border-bottom: 2px solid rgba(0,212,255,0.3);
        margin-bottom: 24px;
    }

    /* ── Difference tag ── */
    .diff-pos { color:#ef9a9a; font-weight:700; }
    .diff-neg { color:#81c784; font-weight:700; }
    .diff-zero{ color:#90caf9; font-weight:700; }

    /* ── General text in app ── */
    h1,h2,h3,h4,h5 { color: #ffffff !important; }
    p, li { color: #e8f4ff; }
    .stMarkdown p  { color: #e8f4ff !important; }
    .stMarkdown li { color: #e8f4ff !important; }
    .stMarkdown strong { color: #ffffff !important; }
    label, .stSelectbox label, .stNumberInput label, .stTextInput label { color: #c8e6ff !important; font-weight:600; }
    [data-testid="stText"] { color: #e8f4ff !important; }
    .stCaption, [data-testid="stCaptionContainer"] { color: #a8ccee !important; }
    [data-baseweb="select"] span { color: #ffffff !important; }
    [data-baseweb="menu"] li   { color: #1a2a3a !important; }

    /* ── Inputs ── */
    input, .stTextInput input, .stNumberInput input {
        background: rgba(255,255,255,0.10) !important;
        color: #ffffff !important;
        border: 1px solid rgba(0,180,216,0.4) !important;
        border-radius: 8px !important;
    }
    .stSelectbox > div > div {
        background: rgba(255,255,255,0.10) !important;
        color: #ffffff !important;
        border: 1px solid rgba(0,180,216,0.4) !important;
    }

    /* ── Main buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #0077b6, #00b4d8);
        color: white;
        border: none;
        border-radius: 10px;
        font-family: 'Cairo', sans-serif;
        font-weight: 600;
        padding: 10px 24px;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #0096c7, #48cae4);
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0,180,216,0.4);
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 10px !important;
        color: #cce8ff !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,0.04); border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { color: #90caf9; }
    .stTabs [aria-selected="true"] { background: rgba(0,180,216,0.2) !important; color: #00d4ff !important; }

    /* ── Success/Error ── */
    .stSuccess { background: rgba(76,175,80,0.15) !important; color: #a5d6a7 !important; border-radius: 10px !important; }
    .stError   { background: rgba(244,67,54,0.15) !important; color: #ef9a9a !important; border-radius: 10px !important; }
    .stWarning { background: rgba(255,152,0,0.15) !important; color: #ffcc80 !important; border-radius: 10px !important; }
    .stInfo    { background: rgba(0,180,216,0.12) !important; color: #80d8ff !important; border-radius: 10px !important; }

    /* ── Metric ── */
    [data-testid="metric-container"] {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(0,180,216,0.2);
        border-radius: 12px;
        padding: 12px;
    }
    [data-testid="metric-container"] label { color: #c8e6ff !important; font-weight:600; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #ffffff !important; font-weight:700; }

    /* ── Divider ── */
    hr { border-color: rgba(0,180,216,0.2) !important; }

    /* ── Suggestion box ── */
    .suggestion-box {
        background: linear-gradient(135deg, rgba(0,119,182,0.2), rgba(0,180,216,0.1));
        border: 1px solid rgba(0,180,216,0.35);
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 12px;
    }
    .suggestion-box h4 { color: #00d4ff; margin: 0 0 10px 0; }
    .suggestion-box p  { color: #dceeff; margin: 4px 0; font-size: 14px; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. DATABASE SETUP
# ==========================================
DB_FILE = "nutrax_v9.db"

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
    try: c.execute("ALTER TABLE users ADD COLUMN country TEXT")
    except: pass

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

c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, 1)",
              ("admin@nutrax.com", hash_pass("123456"), "Admin"))
    conn.commit()


# ==========================================
# 3. FOOD DB
# ==========================================
LOCAL_DB = {
    "chicken_breast":   {"name": "صدر دجاج",         "cal":165, "p":31,  "c":0,    "f":3.6},
    "chicken_thigh":    {"name": "فخذ دجاج",           "cal":209, "p":26,  "c":0,    "f":10},
    "turkey_breast":    {"name": "صدر ديك رومي",       "cal":135, "p":30,  "c":0,    "f":1},
    "beef_steak":       {"name": "ستيك لحم",           "cal":271, "p":25,  "c":0,    "f":19},
    "ground_beef":      {"name": "لحم مفروم",           "cal":250, "p":26,  "c":0,    "f":15},
    "lamb":             {"name": "لحم ضأن",             "cal":294, "p":25,  "c":0,    "f":21},
    "salmon":           {"name": "سلمون",               "cal":208, "p":20,  "c":0,    "f":13},
    "tuna_canned":      {"name": "تونة معلبة",         "cal":116, "p":26,  "c":0,    "f":1},
    "shrimp":           {"name": "جمبري",               "cal":99,  "p":24,  "c":0.2,  "f":0.3},
    "white_fish":       {"name": "سمك أبيض",           "cal":96,  "p":20,  "c":0,    "f":1.7},
    "eggs_whole":       {"name": "بيضة كاملة",         "cal":78,  "p":6,   "c":0.6,  "f":5},
    "eggs_whites":      {"name": "بياض بيض",           "cal":17,  "p":3.6, "c":0.2,  "f":0.1},
    "milk_whole":       {"name": "حليب كامل",           "cal":61,  "p":3.2, "c":4.8,  "f":3.3},
    "milk_skim":        {"name": "حليب خالي الدسم",    "cal":35,  "p":3.4, "c":5,    "f":0.1},
    "greek_yogurt":     {"name": "زبادي يوناني",       "cal":59,  "p":10,  "c":3.6,  "f":0.4},
    "cottage_cheese":   {"name": "جبن قريش",           "cal":98,  "p":11,  "c":3.4,  "f":4.3},
    "cheese_feta":      {"name": "جبن فيتا",           "cal":264, "p":14,  "c":4,    "f":21},
    "cheese_mozzarella":{"name": "موزاريلا",           "cal":280, "p":28,  "c":2.2,  "f":17},
    "rice_white":       {"name": "أرز أبيض",           "cal":130, "p":2.7, "c":28,   "f":0.3},
    "rice_brown":       {"name": "أرز بني",             "cal":111, "p":2.6, "c":23,   "f":0.9},
    "oats":             {"name": "شوفان",               "cal":389, "p":16.9,"c":66,   "f":6.9},
    "quinoa":           {"name": "كينوا",               "cal":120, "p":4.4, "c":21,   "f":1.9},
    "bulgur":           {"name": "برغل",                "cal":83,  "p":3.1, "c":18,   "f":0.2},
    "pasta":            {"name": "مكرونة",              "cal":131, "p":5,   "c":25,   "f":1.1},
    "bread_whole":      {"name": "خبز أسمر",           "cal":247, "p":13,  "c":41,   "f":3.4},
    "bread_white":      {"name": "خبز أبيض",           "cal":265, "p":9,   "c":49,   "f":3.2},
    "sweet_potato":     {"name": "بطاطا حلوة",         "cal":86,  "p":1.6, "c":20,   "f":0.1},
    "potato":           {"name": "بطاطس",               "cal":87,  "p":1.9, "c":20,   "f":0.1},
    "lentils":          {"name": "عدس",                 "cal":116, "p":9,   "c":20,   "f":0.4},
    "chickpeas":        {"name": "حمص",                 "cal":164, "p":8.9, "c":27,   "f":2.6},
    "kidney_beans":     {"name": "فاصوليا حمراء",      "cal":127, "p":8.7, "c":23,   "f":0.5},
    "almonds":          {"name": "لوز",                 "cal":579, "p":21,  "c":22,   "f":50},
    "walnuts":          {"name": "جوز",                 "cal":654, "p":15,  "c":14,   "f":65},
    "peanut_butter":    {"name": "زبدة فول سوداني",    "cal":588, "p":25,  "c":20,   "f":50},
    "chia_seeds":       {"name": "بذور الشيا",          "cal":486, "p":16.5,"c":42,   "f":31},
    "flax_seeds":       {"name": "بذور الكتان",         "cal":534, "p":18,  "c":29,   "f":42},
    "olive_oil":        {"name": "زيت زيتون",           "cal":884, "p":0,   "c":0,    "f":100},
    "avocado":          {"name": "أفوكادو",             "cal":160, "p":2,   "c":9,    "f":15},
    "banana":           {"name": "موز",                 "cal":89,  "p":1.1, "c":23,   "f":0.3},
    "apple":            {"name": "تفاح",                "cal":52,  "p":0.3, "c":14,   "f":0.2},
    "orange":           {"name": "برتقال",              "cal":47,  "p":0.9, "c":12,   "f":0.1},
    "berries":          {"name": "توت مجمد",            "cal":35,  "p":0.4, "c":10,   "f":0.3},
    "broccoli":         {"name": "بروكلي",              "cal":34,  "p":2.8, "c":7,    "f":0.4},
    "spinach":          {"name": "سبانخ",               "cal":23,  "p":2.9, "c":3.6,  "f":0.4},
    "carrots":          {"name": "جزر",                 "cal":41,  "p":0.9, "c":10,   "f":0.2},
    "cucumber":         {"name": "خيار",                "cal":16,  "p":0.6, "c":4,    "f":0.1},
    "tomato":           {"name": "طماطم",               "cal":18,  "p":0.9, "c":3.9,  "f":0.2},
    "dates":            {"name": "تمر",                 "cal":277, "p":1.8, "c":75,   "f":0.2},
    "honey":            {"name": "عسل",                 "cal":304, "p":0.3, "c":82,   "f":0},
    "hummus":           {"name": "حمص بطحينة",          "cal":166, "p":7.9, "c":14,   "f":9.6},
    "falafel":          {"name": "فلافل",               "cal":333, "p":13,  "c":32,   "f":18},
    "ful_medames":      {"name": "فول مدمس",            "cal":110, "p":7.6, "c":20,   "f":0.5},
    "koshary_pasta":    {"name": "مكرونة كشري",         "cal":131, "p":5,   "c":25,   "f":1.1},
    "pita_bread":       {"name": "خبز عيش بلدي",       "cal":255, "p":9,   "c":52,   "f":1.2},
    "tahini":           {"name": "طحينة",               "cal":595, "p":17,  "c":21,   "f":53},
}


# ==========================================
# 4. HELPERS
# ==========================================
def calculate_targets(weight, height, age, goal, activity=1.55):
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
    tdee = bmr * activity
    if goal == "fat_loss":
        cal = tdee - 400
        p_ratio, c_ratio, f_ratio = 0.35, 0.35, 0.30
    elif goal == "muscle_gain":
        cal = tdee + 400
        p_ratio, c_ratio, f_ratio = 0.30, 0.45, 0.25
    else:
        cal = tdee
        p_ratio, c_ratio, f_ratio = 0.25, 0.45, 0.30

    return {
        "cal": int(cal),
        "p":   int(cal * p_ratio / 4),
        "c":   int(cal * c_ratio / 4),
        "f":   int(cal * f_ratio / 9),
        "goal": goal,
    }

def calc_food_macros(food_key, grams):
    f = LOCAL_DB[food_key]
    factor = grams / 100
    return {
        "cal": round(f["cal"] * factor, 1),
        "p":   round(f["p"]   * factor, 1),
        "c":   round(f["c"]   * factor, 1),
        "f":   round(f["f"]   * factor, 1),
    }

def progress_bar(pct, css_class):
    pct = min(pct, 100)
    return f"""
    <div class="progress-wrap">
        <div class="progress-fill {css_class}" style="width:{pct}%"></div>
    </div>"""

def diff_html(diff):
    if diff > 50:
        return f'<span class="diff-pos">+{int(diff)} kcal زيادة ⬆️</span>'
    elif diff < -50:
        return f'<span class="diff-neg">{int(diff)} kcal ناقص ⬇️</span>'
    else:
        return f'<span class="diff-zero">مثالي ✅</span>'

def generate_shopping_list(plan_data):
    shopping = {}
    for day, meals in plan_data.items():
        for meal, foods in meals.items():
            for f_key, grams in foods.items():
                if f_key in LOCAL_DB:
                    shopping[f_key] = shopping.get(f_key, 0) + grams
    return shopping

def suggest_meals(remaining_cal, remaining_p, remaining_c, remaining_f):
    """يقترح وجبة بناءً على السعرات المتبقية"""
    suggestions = []
    target_p_ratio = remaining_p / max(remaining_cal / 4, 1) if remaining_cal > 0 else 0

    for key, food in LOCAL_DB.items():
        grams = min(300, max(50, int(remaining_cal / (food["cal"] / 100))))
        macro = calc_food_macros(key, grams)

        # check reasonable portion
        if macro["cal"] > remaining_cal * 1.2: continue
        if macro["cal"] < 50: continue

        score = 100 - abs(macro["cal"] - remaining_cal * 0.4)
        if remaining_p > 30 and food["p"] > 15: score += 30

        suggestions.append({"key": key, "name": food["name"], "grams": grams, "macro": macro, "score": score})

    suggestions.sort(key=lambda x: -x["score"])
    return suggestions[:4]


# ==========================================
# 5. SESSION STATE
# ==========================================
if "page"    not in st.session_state: st.session_state.page    = "login"
if "user"    not in st.session_state: st.session_state.user    = None
if "targets" not in st.session_state: st.session_state.targets = None


# ==========================================
# 6. LOGIN PAGE
# ==========================================
if st.session_state.page == "login":
    st.markdown("""
    <div style='text-align:center; padding: 40px 0 20px;'>
        <div style='font-size:60px;'>🥗</div>
        <h1 style='color:#00d4ff; font-size:42px; font-weight:900; margin:0;'>NutraX</h1>
        <p style='color:#90caf9; font-size:16px; margin-top:8px;'>مساعدك الذكي للتغذية الصحية</p>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        tab1, tab2 = st.tabs(["🔑 تسجيل الدخول", "✨ إنشاء حساب"])

        with tab1:
            with st.form("lgn"):
                e = st.text_input("📧 البريد الإلكتروني")
                p = st.text_input("🔒 كلمة المرور", type="password")
                if st.form_submit_button("دخول ←", use_container_width=True):
                    c.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hash_pass(p)))
                    u = c.fetchone()
                    if u:
                        st.session_state.user = u
                        st.session_state.page = "dashboard"
                        st.rerun()
                    else: st.error("البيانات غير صحيحة")

        with tab2:
            with st.form("reg"):
                n  = st.text_input("👤 الاسم الكامل")
                e  = st.text_input("📧 البريد الإلكتروني")
                p  = st.text_input("🔒 كلمة المرور", type="password")
                by = st.number_input("📅 سنة الميلاد", 1950, 2010, 1995)
                country = st.selectbox("🌍 البلد", ["Egypt","Saudi Arabia","UAE","Kuwait","Qatar","Bahrain","Jordan","USA","UK","Other"])
                if st.form_submit_button("إنشاء الحساب ←", use_container_width=True):
                    try:
                        c.execute("INSERT INTO users (email,password,name,birth_year,country,is_admin) VALUES (?,?,?,?,?,0)",
                                  (e, hash_pass(p), n, by, country))
                        conn.commit()
                        st.success("تم التسجيل! سجل دخولك الآن.")
                    except: st.error("البريد الإلكتروني مستخدم بالفعل")


# ==========================================
# 7. MAIN APP
# ==========================================
else:
    # Safety check
    if st.session_state.user is None or len(st.session_state.user) < 5:
        st.session_state.user = None
        st.session_state.page = "login"
        st.warning("انتهت الجلسة. يرجى تسجيل الدخول.")
        st.rerun()

    u    = st.session_state.user
    u_id = u[0]

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown(f"""
        <div style='text-align:center; padding:20px 0 10px;'>
            <div style='font-size:48px;'>👤</div>
            <h3 style='color:#00d4ff; margin:8px 0 4px;'>{u[3]}</h3>
            <p style='color:#90caf9; font-size:13px; margin:0;'>{u[1]}</p>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        pages = [
            ("🏠", "الرئيسية",          "dashboard"),
            ("⚙️", "الإعدادات والهدف",  "profile_setup"),
            ("🔍", "محلل الطعام",       "analyzer"),
            ("📅", "مصمم الجدول",       "planner"),
            ("💡", "مقترح الوجبات",     "suggester"),
            ("💾", "جداولي المحفوظة",   "saved"),
            ("📈", "سجل الوزن",         "history"),
        ]
        for icon, label, pg in pages:
            if st.button(f"{icon}  {label}", key=f"nav_{pg}"):
                st.session_state.page = pg
                st.rerun()

        st.divider()
        if st.button("🚪  خروج", key="logout"):
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()

    # ── Validate targets has all required keys (fix KeyError from old sessions) ──
    required_keys = {"cal", "p", "c", "f", "goal"}
    if st.session_state.targets and not required_keys.issubset(st.session_state.targets.keys()):
        st.session_state.targets = None

    # ============================================
    # DASHBOARD
    # ============================================
    if st.session_state.page == "dashboard":
        st.markdown("<div class='page-title'>🏠 الرئيسية</div>", unsafe_allow_html=True)

        if not st.session_state.targets:
            st.markdown("""
            <div class='alert-warn'>
                <b>⚠️ بياناتك غير مكتملة</b><br>
                يرجى إكمال إعداداتك حتى نستطيع حساب أهدافك الغذائية.
            </div>""", unsafe_allow_html=True)
            if st.button("⚙️ اذهب للإعدادات"):
                st.session_state.page = "profile_setup"; st.rerun()
        else:
            t = st.session_state.targets
            c.execute("SELECT COUNT(*) FROM saved_plans WHERE user_id=?", (u_id,))
            plans_count = c.fetchone()[0]
            c.execute("SELECT weight FROM tracking WHERE user_id=? ORDER BY id DESC LIMIT 1", (u_id,))
            last_w = c.fetchone()

            # Stat cards
            col1, col2, col3, col4 = st.columns(4)
            cards = [
                ("🎯 هدفك اليومي", t['cal'], "kcal"),
                ("💪 بروتين",       t['p'],   "جم"),
                ("🍞 كاربوهيدرات",  t['c'],   "جم"),
                ("🥑 دهون",         t['f'],   "جم"),
            ]
            for col, (label, value, unit) in zip([col1,col2,col3,col4], cards):
                col.markdown(f"""
                <div class='stat-card'>
                    <div class='label'>{label}</div>
                    <div class='value'>{value}</div>
                    <div class='unit'>{unit}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            col5, col6 = st.columns(2)
            with col5:
                st.markdown(f"""
                <div class='stat-card'>
                    <div class='label'>💾 جداولك المحفوظة</div>
                    <div class='value'>{plans_count}</div>
                    <div class='unit'>جدول</div>
                </div>""", unsafe_allow_html=True)
            with col6:
                st.markdown(f"""
                <div class='stat-card'>
                    <div class='label'>⚖️ آخر وزن مسجل</div>
                    <div class='value'>{last_w[0] if last_w else '---'}</div>
                    <div class='unit'>كجم</div>
                </div>""", unsafe_allow_html=True)

            # Goal label
            goal_labels = {"fat_loss":"🔥 خسارة دهون", "muscle_gain":"💪 بناء عضل", "maintain":"⚖️ ثبات الوزن"}
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"هدفك الحالي: **{goal_labels.get(t['goal'], t['goal'])}** — {t['cal']} kcal / يوم")

    # ============================================
    # PROFILE SETUP
    # ============================================
    elif st.session_state.page == "profile_setup":
        st.markdown("<div class='page-title'>⚙️ الإعدادات والهدف</div>", unsafe_allow_html=True)

        with st.form("profile_form"):
            col1, col2 = st.columns(2)
            with col1:
                h    = st.number_input("📏 الطول (سم)", min_value=140.0, max_value=220.0, value=float(u[4] or 170))
                w    = st.number_input("⚖️ الوزن (كجم)", min_value=40.0, max_value=250.0, value=float(u[5] or 70))
                age  = st.number_input("📅 العمر (سنة)", min_value=15, max_value=90, value=25)
            with col2:
                goal = st.selectbox("🎯 هدفك", ["maintain","fat_loss","muscle_gain"],
                                    format_func=lambda x: {"maintain":"⚖️ ثبات الوزن","fat_loss":"🔥 خسارة دهون","muscle_gain":"💪 بناء عضل"}[x])
                activity = st.selectbox("🏃 مستوى النشاط",
                    [1.2, 1.375, 1.55, 1.725, 1.9],
                    format_func=lambda x: {1.2:"مستقر (لا رياضة)",1.375:"خفيف (1-3 أيام)",1.55:"معتدل (3-5 أيام)",1.725:"نشيط (6-7 أيام)",1.9:"رياضي محترف"}[x])

            if st.form_submit_button("💾 حفظ وحساب الأهداف", use_container_width=True):
                c.execute("UPDATE users SET height=?, weight=?, goal=?, birth_year=? WHERE id=?",
                          (h, w, goal, datetime.now().year - age, u_id))
                conn.commit()
                st.session_state.targets = calculate_targets(w, h, age, goal, activity)
                c.execute("SELECT * FROM users WHERE id=?", (u_id,))
                st.session_state.user = c.fetchone()
                st.success("✅ تم الحفظ بنجاح!")
                st.session_state.page = "dashboard"
                st.rerun()

    # ============================================
    # ANALYZER
    # ============================================
    elif st.session_state.page == "analyzer":
        st.markdown("<div class='page-title'>🔍 محلل الطعام</div>", unsafe_allow_html=True)

        search = st.text_input("ابحث عن طعام بالعربي أو الإنجليزي")
        if search:
            s = search.lower()
            results = [(k, v) for k, v in LOCAL_DB.items() if s in k.lower() or s in v['name']]

            if results:
                for k, v in results:
                    st.markdown(f"""
                    <div class='food-card'>
                        <h4>🍴 {v['name']}</h4>
                        <div class='macro-row'>
                            <span class='macro-pill' style='background:rgba(0,180,216,0.2);color:#80d8ff;border:1px solid rgba(0,180,216,0.3)'>
                                🔥 {v['cal']} kcal
                            </span>
                            <span class='macro-pill pill-p'>💪 بروتين {v['p']}ج</span>
                            <span class='macro-pill pill-c'>🍞 كارب {v['c']}ج</span>
                            <span class='macro-pill pill-f'>🥑 دهون {v['f']}ج</span>
                        </div>
                        <p style='color:#90caf9; font-size:12px; margin:8px 0 0;'>القيم لكل 100 جرام</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("لم يتم العثور على نتائج. جرب كلمة أخرى.")
        else:
            st.info("💡 اكتب اسم الطعام في الخانة أعلاه للبحث")
            st.markdown("**أمثلة:** دجاج، أرز، شوفان، سلمون، موز، تمر ...")

    # ============================================
    # PLANNER
    # ============================================
    elif st.session_state.page == "planner":
        st.markdown("<div class='page-title'>📅 مصمم الجدول الغذائي</div>", unsafe_allow_html=True)

        if not st.session_state.targets:
            st.warning("يرجى إكمال الإعدادات أولاً")
            if st.button("⚙️ الإعدادات"): st.session_state.page="profile_setup"; st.rerun()
            st.stop()

        t      = st.session_state.targets
        target = t['cal']
        st.info(f"🎯 هدفك اليومي: **{target} kcal** | بروتين {t['p']}ج | كارب {t['c']}ج | دهون {t['f']}ج")

        days = st.number_input("عدد الأيام", 1, 30, 1)
        plan = {}
        total_cal = total_p = total_c = total_f = 0

        for d in range(days):
            with st.expander(f"📆 يوم {d+1}", expanded=(d==0)):
                plan[d] = {}
                cols = st.columns(4)
                meals = ["فطار", "غداء", "عشاء", "سناك"]
                for i, meal in enumerate(meals):
                    with cols[i]:
                        st.markdown(f"**{meal}**")
                        foods = st.multiselect("اختر الأكل",
                                               list(LOCAL_DB.keys()),
                                               format_func=lambda k: LOCAL_DB[k]['name'],
                                               key=f"sel_{d}_{i}")
                        plan[d][meal] = {}
                        for f_key in foods:
                            g = st.number_input(f"{LOCAL_DB[f_key]['name']} (جم)", 0, 1000, 100, key=f"inp_{d}_{i}_{f_key}")
                            if g > 0:
                                plan[d][meal][f_key] = g
                                m = calc_food_macros(f_key, g)
                                total_cal += m["cal"]
                                total_p   += m["p"]
                                total_c   += m["c"]
                                total_f   += m["f"]
                                st.caption(f"🔥 {m['cal']} kcal | 💪 {m['p']}ج | 🍞 {m['c']}ج | 🥑 {m['f']}ج")

        # Summary
        st.markdown("---")
        st.markdown("### 📊 ملخص الجدول")

        col1, col2 = st.columns(2)
        with col1:
            pct_cal = int(total_cal / (target * days) * 100) if days > 0 else 0
            pct_p   = int(total_p   / (t['p']  * days) * 100) if days > 0 else 0
            pct_c   = int(total_c   / (t['c']  * days) * 100) if days > 0 else 0
            pct_f   = int(total_f   / (t['f']  * days) * 100) if days > 0 else 0

            st.markdown(f"🔥 **سعرات: {int(total_cal)} / {target*days} kcal** ({pct_cal}%)")
            st.markdown(progress_bar(pct_cal, "progress-cal"), unsafe_allow_html=True)
            st.markdown(f"💪 **بروتين: {int(total_p)} / {t['p']*days} ج** ({pct_p}%)")
            st.markdown(progress_bar(pct_p, "progress-p"), unsafe_allow_html=True)
            st.markdown(f"🍞 **كارب: {int(total_c)} / {t['c']*days} ج** ({pct_c}%)")
            st.markdown(progress_bar(pct_c, "progress-c"), unsafe_allow_html=True)
            st.markdown(f"🥑 **دهون: {int(total_f)} / {t['f']*days} ج** ({pct_f}%)")
            st.markdown(progress_bar(pct_f, "progress-f"), unsafe_allow_html=True)

        with col2:
            diff = total_cal - (target * days)
            st.markdown(f"**الفارق الكلي:** {diff_html(diff)}", unsafe_allow_html=True)
            if abs(diff) < 100:
                st.success("ممتاز! الجدول متوازن جداً 🎯")
            elif diff > 0:
                st.warning(f"الجدول زيادة بمقدار {int(diff)} kcal — قلل بعض الكميات")
            else:
                st.warning(f"الجدول ناقص {int(abs(diff))} kcal — أضف وجبة أو زود الكميات")

        st.markdown("---")
        col_n, col_t = st.columns(2)
        with col_n: plan_name = st.text_input("📝 اسم الجدول", value=f"جدول {datetime.now().strftime('%d/%m/%Y')}")
        with col_t: save_type = st.selectbox("📁 نوع الحفظ", ["خاص بي", "للعميل", "عام"])

        if st.button("💾 حفظ الجدول", use_container_width=True):
            c.execute("INSERT INTO saved_plans VALUES (NULL, ?, ?, ?, datetime('now'), ?)",
                      (u_id, plan_name, json.dumps({str(k): v for k, v in plan.items()}), save_type))
            conn.commit()
            st.success("✅ تم حفظ الجدول!")
            st.rerun()

    # ============================================
    # MEAL SUGGESTER (NEW)
    # ============================================
    elif st.session_state.page == "suggester":
        st.markdown("<div class='page-title'>💡 مقترح الوجبات الذكي</div>", unsafe_allow_html=True)

        if not st.session_state.targets:
            st.warning("يرجى إكمال الإعدادات أولاً")
            if st.button("⚙️ الإعدادات"): st.session_state.page="profile_setup"; st.rerun()
            st.stop()

        t = st.session_state.targets
        st.info("أدخل ما أكلته اليوم ونقترح عليك وجباتك المتبقية!")

        with st.form("eaten_form"):
            st.markdown("**ماذا أكلت حتى الآن؟**")
            col1, col2, col3 = st.columns(3)
            with col1: eaten_cal = st.number_input("🔥 سعرات أكلتها", 0, 5000, 0, step=50)
            with col2: eaten_p   = st.number_input("💪 بروتين (جم)", 0, 500, 0)
            with col3: eaten_f   = st.number_input("🥑 دهون (جم)", 0, 300, 0)
            eaten_c = st.number_input("🍞 كارب (جم)", 0, 600, 0)
            submitted = st.form_submit_button("💡 اقترح لي وجبات ←", use_container_width=True)

        if submitted:
            rem_cal = max(0, t['cal'] - eaten_cal)
            rem_p   = max(0, t['p']   - eaten_p)
            rem_c   = max(0, t['c']   - eaten_c)
            rem_f   = max(0, t['f']   - eaten_f)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**✅ ما أكلته:**")
                st.markdown(f"- 🔥 {eaten_cal} kcal")
                st.markdown(f"- 💪 بروتين {eaten_p} ج")
                st.markdown(f"- 🍞 كارب {eaten_c} ج")
                st.markdown(f"- 🥑 دهون {eaten_f} ج")
            with col2:
                st.markdown("**🎯 المتبقي:**")
                st.markdown(f"- 🔥 {rem_cal} kcal")
                st.markdown(f"- 💪 بروتين {rem_p} ج")
                st.markdown(f"- 🍞 كارب {rem_c} ج")
                st.markdown(f"- 🥑 دهون {rem_f} ج")

            st.markdown("---")
            if rem_cal < 50:
                st.success("🎉 أنت وصلت لهدفك اليومي! لا تحتاج وجبات إضافية.")
            else:
                st.markdown("### 🍽️ وجبات مقترحة لك:")
                suggestions = suggest_meals(rem_cal, rem_p, rem_c, rem_f)
                for s in suggestions:
                    m = s["macro"]
                    st.markdown(f"""
                    <div class='suggestion-box'>
                        <h4>🍴 {s['name']} — {s['grams']} جرام</h4>
                        <div class='macro-row'>
                            <span class='macro-pill' style='background:rgba(0,180,216,0.2);color:#80d8ff;border:1px solid rgba(0,180,216,0.3)'>
                                🔥 {m['cal']} kcal
                            </span>
                            <span class='macro-pill pill-p'>💪 {m['p']}ج</span>
                            <span class='macro-pill pill-c'>🍞 {m['c']}ج</span>
                            <span class='macro-pill pill-f'>🥑 {m['f']}ج</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # ============================================
    # SAVED PLANS
    # ============================================
    elif st.session_state.page == "saved":
        st.markdown("<div class='page-title'>💾 جداولي المحفوظة</div>", unsafe_allow_html=True)

        ft = st.selectbox("🔎 فلتر النوع", ["الكل", "خاص بي", "للعميل", "عام"])
        q  = "SELECT id, plan_name, created_at, type FROM saved_plans WHERE user_id=?"
        p  = [u_id]
        if ft != "الكل": q += " AND type=?"; p.append(ft)
        c.execute(q, p)
        rows = c.fetchall()

        if not rows:
            st.info("لا توجد جداول محفوظة بعد. اذهب لـ مصمم الجدول وابدأ!")
        else:
            for pid, pname, pdate, ptype in rows:
                with st.expander(f"📋 {pname}   |   {ptype}   |   {pdate[:10] if pdate else ''}"):
                    c.execute("SELECT plan_data FROM saved_plans WHERE id=?", (pid,))
                    pd_raw = json.loads(c.fetchone()[0])

                    col1, col2 = st.columns([2,1])
                    with col1:
                        for d, meals in pd_raw.items():
                            st.markdown(f"**📆 يوم {int(d)+1}**")
                            for m, foods in meals.items():
                                items = []
                                for k, v in foods.items():
                                    if v > 0 and k in LOCAL_DB:
                                        items.append(f"{LOCAL_DB[k]['name']} ({v}ج)")
                                if items:
                                    st.markdown(f"- {m}: " + "، ".join(items))
                    with col2:
                        if st.button("🛒 قائمة المشتريات", key=f"shop_{pid}"):
                            shop = generate_shopping_list(pd_raw)
                            st.markdown("**🛒 قائمة المشتريات:**")
                            for k, v in shop.items():
                                if k in LOCAL_DB:
                                    st.markdown(f"- {LOCAL_DB[k]['name']}: **{v} جرام**")

                        if st.button("🗑️ حذف", key=f"del_{pid}"):
                            c.execute("DELETE FROM saved_plans WHERE id=?", (pid,))
                            conn.commit()
                            st.rerun()

    # ============================================
    # HISTORY
    # ============================================
    elif st.session_state.page == "history":
        st.markdown("<div class='page-title'>📈 سجل الوزن</div>", unsafe_allow_html=True)

        with st.form("weight_form"):
            col1, col2 = st.columns([2,1])
            with col1: w_input = st.number_input("⚖️ وزن اليوم (كجم)", 30.0, 300.0, 70.0, step=0.1)
            with col2: st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("✅ تسجيل الوزن", use_container_width=True):
                c.execute("INSERT INTO tracking VALUES (NULL, ?, ?, datetime('now'))", (u_id, w_input))
                conn.commit()
                st.success("تم تسجيل وزنك!")
                st.rerun()

        c.execute("SELECT date, weight FROM tracking WHERE user_id=? ORDER BY id ASC", (u_id,))
        data = c.fetchall()

        if data:
            weights = [d[1] for d in data]
            dates   = [d[0][:10] if d[0] else "" for d in data]

            col1, col2, col3 = st.columns(3)
            col1.metric("📉 أقل وزن",  f"{min(weights)} كجم")
            col2.metric("📈 أعلى وزن", f"{max(weights)} كجم")
            col3.metric("📊 آخر وزن",  f"{weights[-1]} كجم",
                        delta=f"{round(weights[-1]-weights[0],1)} كجم" if len(weights)>1 else None)

            st.line_chart({"الوزن (كجم)": weights})
        else:
            st.info("لم تسجل أي وزن حتى الآن. سجل وزنك اليوم!")

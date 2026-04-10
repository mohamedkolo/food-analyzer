import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime

# =========================
# إعداد الصفحة
# =========================
st.set_page_config(page_title="NutraX", layout="wide")

# اختيار اللغة
if "lang" not in st.session_state:
    st.session_state.lang = st.selectbox("اختر اللغة", ["العربية", "English"])

# =========================
# قاعدة البيانات
# =========================
conn = sqlite3.connect("nutrax.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
email TEXT,
password TEXT,
name TEXT,
is_admin INTEGER)""")

c.execute("""CREATE TABLE IF NOT EXISTS plans(
id INTEGER PRIMARY KEY,
user_id INTEGER,
data TEXT,
days INTEGER,
created TEXT)""")

conn.commit()

# إنشاء أدمن
def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES (NULL,?,?,?,1)",
              ("admin@nutrax.com", hash_pass("admin123"), "Admin"))
    conn.commit()

# =========================
# أكل (موسع)
# =========================
FOODS = {
    "chicken": {"cal":165,"p":31},
    "beef": {"cal":250,"p":26},
    "rice": {"cal":130,"p":2},
    "oats": {"cal":389,"p":16},
    "egg": {"cal":78,"p":6},
    "banana": {"cal":89,"p":1},
    "apple": {"cal":52,"p":0},
    "milk": {"cal":60,"p":3},
    "tuna": {"cal":116,"p":26},
    "salmon": {"cal":208,"p":20},
}

# =========================
# تسجيل الدخول
# =========================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:

    st.title("NutraX Login")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            c.execute("SELECT * FROM users WHERE email=? AND password=?",
                      (e, hash_pass(p)))
            u = c.fetchone()
            if u:
                st.session_state.user = u
                st.rerun()

    with tab2:
        n = st.text_input("Name")
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Create"):
            c.execute("INSERT INTO users VALUES (NULL,?,?,?,0)",
                      (e, hash_pass(p), n))
            conn.commit()
            st.success("Created")

# =========================
# بعد الدخول
# =========================
else:
    user = st.session_state.user

    with st.sidebar:
        st.write(user[3])
        if st.button("Dashboard"): st.session_state.page="dash"
        if st.button("Analyze Food"): st.session_state.page="analyze"
        if st.button("My Plans"): st.session_state.page="plans"
        if user[4]==1:
            if st.button("Admin Panel"): st.session_state.page="admin"
        if st.button("Logout"):
            st.session_state.user=None
            st.rerun()

    if "page" not in st.session_state:
        st.session_state.page="dash"

# =========================
# Dashboard
# =========================
    if st.session_state.page=="dash":
        st.title("Dashboard")

        c.execute("SELECT * FROM plans WHERE user_id=? ORDER BY id DESC LIMIT 1",(user[0],))
        plan=c.fetchone()

        if plan:
            st.success("آخر خطة محفوظة")
            st.json(json.loads(plan[2]))
        else:
            st.info("مفيش خطط لسه")

# =========================
# تحليل الأكل
# =========================
    elif st.session_state.page=="analyze":
        st.title("Food Analyzer")

        food = st.selectbox("اختار الأكل", list(FOODS.keys()))
        grams = st.number_input("جرام", value=100)

        if st.button("Analyze"):
            data = FOODS[food]
            cal = data["cal"] * grams/100
            protein = data["p"] * grams/100

            st.write(f"Calories: {cal}")
            st.write(f"Protein: {protein}")

            # نصيحة
            if cal > 500:
                st.warning("سعرات عالية قلل الكمية")
            else:
                st.success("تمام كمل")

# =========================
# إنشاء خطة
# =========================
    elif st.session_state.page=="plans":
        st.title("Create Plan")

        days = st.number_input("عدد الأيام",1,30,7)

        plan = {}

        for d in range(days):
            st.subheader(f"Day {d+1}")
            meal = st.text_input(f"Meal day {d}", key=d)
            plan[f"day_{d}"]=meal

        if st.button("Save"):
            c.execute("INSERT INTO plans VALUES(NULL,?,?,?,?)",
                      (user[0], json.dumps(plan), days, str(datetime.now())))
            conn.commit()
            st.success("Saved")

# =========================
# الأدمن
# =========================
    elif st.session_state.page=="admin":
        st.title("Admin Panel")

        st.subheader("Users")
        c.execute("SELECT email FROM users")
        st.write(c.fetchall())

        st.subheader("Add Food")
        name = st.text_input("Food name")
        cal = st.number_input("Calories")
        p = st.number_input("Protein")

        if st.button("Add"):
            FOODS[name]={"cal":cal,"p":p}
            st.success("Added")

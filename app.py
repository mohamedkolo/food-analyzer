import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime

# ======================
# إعداد الصفحة
# ======================
st.set_page_config(page_title="NutraX", layout="wide")

# ======================
# DB
# ======================
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
name TEXT,
data TEXT,
created_at TEXT)""")

conn.commit()

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# إنشاء أدمن
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users (email,password,name,is_admin) VALUES (?,?,?,1)",
              ("admin@nutrax.com", hash_pass("admin123"), "Admin"))
    conn.commit()

# ======================
# أكل
# ======================
FOOD = {
    "chicken": {"name":"صدر دجاج", "cal":165},
    "beef": {"name":"لحم بقري", "cal":250},
    "rice": {"name":"رز", "cal":130},
    "oats": {"name":"شوفان", "cal":389},
    "egg": {"name":"بيض", "cal":78},
    "milk": {"name":"لبن", "cal":60},
    "apple": {"name":"تفاح", "cal":52},
    "banana": {"name":"موز", "cal":89},
    "potato": {"name":"بطاطس", "cal":87},
    "fish": {"name":"سمك", "cal":200},
    "tuna": {"name":"تونة", "cal":116},
    "cheese": {"name":"جبنة", "cal":260},
    "bread": {"name":"عيش", "cal":250},
}

def food_advice(cal):
    if cal < 100:
        return "خفيف. ينفع دايت."
    elif cal < 250:
        return "متوسط. كويس للثبات."
    else:
        return "سعراته عالية. خلي بالك."

# ======================
# session
# ======================
if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "login"

# ======================
# login
# ======================
if st.session_state.page == "login":

    st.title("NutraX")

    tab1, tab2 = st.tabs(["دخول", "تسجيل"])

    with tab1:
        e = st.text_input("email")
        p = st.text_input("password", type="password")
        if st.button("login"):
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hash_pass(p)))
            u = c.fetchone()
            if u:
                st.session_state.user = u
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("غلط")

    with tab2:
        n = st.text_input("name")
        e = st.text_input("email ")
        p = st.text_input("password ", type="password")
        if st.button("create"):
            c.execute("INSERT INTO users (email,password,name,is_admin) VALUES (?,?,?,0)",
                      (e, hash_pass(p), n))
            conn.commit()
            st.success("تم")

# ======================
# app
# ======================
else:

    user = st.session_state.user

    if not user:
        st.session_state.page = "login"
        st.rerun()

    uid = user[0]
    name = user[3]
    is_admin = user[4]

    # sidebar
    with st.sidebar:
        st.write(name)

        if st.button("Dashboard"):
            st.session_state.page = "dashboard"
        if st.button("Analyze Food"):
            st.session_state.page = "analyze"
        if st.button("Create Plan"):
            st.session_state.page = "plan"
        if st.button("My Plans"):
            st.session_state.page = "myplans"

        if is_admin == 1:
            if st.button("Admin"):
                st.session_state.page = "admin"

        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()

    # ======================
    # dashboard
    # ======================
    if st.session_state.page == "dashboard":
        st.title(f"اهلا {name}")

        total = c.execute("SELECT COUNT(*) FROM plans WHERE user_id=?", (uid,)).fetchone()[0]
        st.metric("خططك", total)

    # ======================
    # تحليل
    # ======================
    elif st.session_state.page == "analyze":
        st.title("تحليل الأكل")

        f = st.selectbox("اختار", list(FOOD.keys()))
        g = st.number_input("جرام", 100)

        if st.button("حلل"):
            cal = FOOD[f]["cal"] * g / 100
            st.write(f"سعرات: {int(cal)}")
            st.info(food_advice(cal))

    # ======================
    # إنشاء جدول
    # ======================
    elif st.session_state.page == "plan":

        st.title("اعمل جدولك")

        days = st.number_input("عدد الأيام", 1, 30, 7)

        meals = ["فطار", "غداء", "عشاء", "سناك"]

        plan = {}

        for d in range(days):
            st.subheader(f"يوم {d+1}")
            plan[d] = {}

            for m in meals:
                f = st.selectbox(f"{m} - يوم {d+1}", list(FOOD.keys()), key=f"{d}_{m}")
                g = st.number_input("جرام", 50, 500, 100, key=f"{d}_{m}_g")
                plan[d][m] = {"food": f, "g": g}

        name_plan = st.text_input("اسم الجدول")

        if st.button("save"):
            c.execute("INSERT INTO plans (user_id,name,data,created_at) VALUES (?,?,?,?)",
                      (uid, name_plan, json.dumps(plan), datetime.now()))
            conn.commit()
            st.success("اتحفظ")

    # ======================
    # خططى
    # ======================
    elif st.session_state.page == "myplans":

        st.title("خططى")

        rows = c.execute("SELECT id,name,created_at FROM plans WHERE user_id=?", (uid,)).fetchall()

        for r in rows:
            with st.expander(r[1]):
                data = json.loads(c.execute("SELECT data FROM plans WHERE id=?", (r[0],)).fetchone()[0])

                for d in data:
                    st.write(f"يوم {int(d)+1}")
                    for m in data[d]:
                        f = data[d][m]["food"]
                        g = data[d][m]["g"]
                        st.write(f"{m}: {FOOD[f]['name']} {g}g")

    # ======================
    # admin
    # ======================
    elif st.session_state.page == "admin":

        st.title("Admin")

        users = c.execute("SELECT id,name,email FROM users").fetchall()
        for u in users:
            st.write(u)

import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime

st.set_page_config(page_title="NutraX", layout="wide")

# ======================
# DB
# ======================
conn = sqlite3.connect("nutrax.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
email TEXT UNIQUE,
password TEXT,
name TEXT,
is_admin INTEGER)""")

c.execute("""CREATE TABLE IF NOT EXISTS plans(
id INTEGER PRIMARY KEY,
user_id INTEGER,
plan TEXT,
days INTEGER,
created TEXT)""")

conn.commit()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

# admin
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES(NULL,?,?,?,1)",
              ("admin@nutrax.com", hash_pass("admin123"), "Admin"))
    conn.commit()

# ======================
# FOOD DB
# ======================
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
    "bread": {"cal":265,"p":9},
    "cheese": {"cal":402,"p":25}
}

# ======================
# SESSION
# ======================
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# ======================
# LOGIN
# ======================
if not st.session_state.user:

    st.title("NutraX")

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
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Wrong data")

    with tab2:
        n = st.text_input("Name")
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Create"):
            try:
                c.execute("INSERT INTO users VALUES(NULL,?,?,?,0)",
                          (e, hash_pass(p), n))
                conn.commit()
                st.success("Done")
            except:
                st.error("Email exists")

# ======================
# APP
# ======================
else:
    user = st.session_state.user

    with st.sidebar:
        st.write(f"👤 {user[3]}")

        if st.button("Dashboard"):
            st.session_state.page="dashboard"

        if st.button("Analyze Food"):
            st.session_state.page="analyze"

        if st.button("Create Plan"):
            st.session_state.page="create"

        if st.button("My Plans"):
            st.session_state.page="plans"

        if user[4]==1:
            if st.button("Admin"):
                st.session_state.page="admin"

        if st.button("Logout"):
            st.session_state.user=None
            st.rerun()

# ======================
# DASHBOARD
# ======================
    if st.session_state.page=="dashboard":
        st.title("Dashboard")

        c.execute("SELECT * FROM plans WHERE user_id=? ORDER BY id DESC LIMIT 1",(user[0],))
        last = c.fetchone()

        if last:
            st.success("Last Plan")
            st.json(json.loads(last[2]))
        else:
            st.info("No plans yet")

# ======================
# ANALYZE
# ======================
    elif st.session_state.page=="analyze":
        st.title("Food Analysis")

        food = st.selectbox("Food", list(FOODS.keys()))
        grams = st.number_input("Grams", value=100)

        if st.button("Analyze"):
            cal = FOODS[food]["cal"] * grams / 100
            protein = FOODS[food]["p"] * grams / 100

            st.metric("Calories", int(cal))
            st.metric("Protein", int(protein))

            if cal > 500:
                st.warning("High calories reduce it")
            else:
                st.success("Good choice")

# ======================
# CREATE PLAN
# ======================
    elif st.session_state.page=="create":
        st.title("Create Plan")

        days = st.number_input("Days",1,30,7)

        plan = {}

        for d in range(days):
            st.subheader(f"Day {d+1}")

            breakfast = st.text_input(f"Breakfast {d}", key=f"b{d}")
            lunch = st.text_input(f"Lunch {d}", key=f"l{d}")
            dinner = st.text_input(f"Dinner {d}", key=f"d{d}")
            snack = st.text_input(f"Snack {d}", key=f"s{d}")

            plan[f"day_{d}"] = {
                "breakfast": breakfast,
                "lunch": lunch,
                "dinner": dinner,
                "snack": snack
            }

        if st.button("Save Plan"):
            c.execute("INSERT INTO plans VALUES(NULL,?,?,?,?)",
                      (user[0], json.dumps(plan), days, str(datetime.now())))
            conn.commit()
            st.success("Saved")

# ======================
# MY PLANS
# ======================
    elif st.session_state.page=="plans":
        st.title("My Plans")

        c.execute("SELECT * FROM plans WHERE user_id=?",(user[0],))
        plans = c.fetchall()

        for p in plans:
            with st.expander(p[4]):
                st.json(json.loads(p[2]))

# ======================
# ADMIN
# ======================
    elif st.session_state.page=="admin":
        st.title("Admin")

        st.subheader("Users")
        c.execute("SELECT email FROM users")
        st.write(c.fetchall())

        st.subheader("Add Food")
        name = st.text_input("Name")
        cal = st.number_input("Calories")
        p = st.number_input("Protein")

        if st.button("Add Food"):
            FOODS[name]={"cal":cal,"p":p}
            st.success("Added")

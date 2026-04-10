import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime

st.set_page_config(page_title="NutraX", layout="wide")

# ================= DB =================
conn = sqlite3.connect("nutrax.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, password TEXT, is_admin INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS plans (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, data TEXT, days INTEGER, type TEXT)")
conn.commit()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

# create admin
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES (NULL, ?, ?, 1)", ("admin@nutrax.app", hash_pass("123456")))
    conn.commit()

# ================= FOOD =================
FOODS = {
    "Chicken": 165, "Beef": 250, "Fish": 180,
    "Eggs": 78, "Rice":130, "Oats":150,
    "Milk":60, "Cheese":200,
    "Apple":52, "Banana":89,
    "Almonds":579, "Olive Oil":884,
    "Potato":87, "Sweet Potato":90,
    "Broccoli":34, "Spinach":23
}

# ================= STATE =================
if "user" not in st.session_state: st.session_state.user = None
if "page" not in st.session_state: st.session_state.page = "login"

# ================= LOGIN =================
if st.session_state.page == "login":
    st.title("NutraX Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hash_pass(password)))
        user = c.fetchone()
        if user:
            st.session_state.user = user
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error("Wrong data")

# ================= DASHBOARD =================
else:
    user = st.session_state.user
    is_admin = user[3]

    st.sidebar.write("Logged in")

    if st.sidebar.button("Dashboard"):
        st.session_state.page = "dashboard"
    if st.sidebar.button("Create Plan"):
        st.session_state.page = "create"
    if st.sidebar.button("My Plans"):
        st.session_state.page = "myplans"

    if is_admin:
        if st.sidebar.button("Admin Plans"):
            st.session_state.page = "adminplans"

    # ===== Dashboard
    if st.session_state.page == "dashboard":
        st.title("Dashboard")

    # ===== Create Plan
    elif st.session_state.page == "create":
        st.title("Create Diet Plan")

        days = st.number_input("عدد الأيام", 1, 30, 7)

        meals = ["Breakfast", "Lunch", "Dinner", "Snack"]

        plan = {}

        for d in range(days):
            st.subheader(f"Day {d+1}")
            plan[d] = {}

            for meal in meals:
                foods = st.multiselect(f"{meal} - Day {d+1}", list(FOODS.keys()), key=f"{meal}{d}")
                plan[d][meal] = foods

        name = st.text_input("اسم الجدول")

        save_type = st.selectbox("نوع الحفظ", ["user", "admin"])

        if st.button("Save Plan"):
            c.execute("INSERT INTO plans VALUES (NULL, ?, ?, ?, ?, ?)",
                      (user[0], name, json.dumps(plan), days, save_type))
            conn.commit()
            st.success("Saved")

    # ===== My Plans
    elif st.session_state.page == "myplans":
        st.title("My Plans")

        c.execute("SELECT id, name FROM plans WHERE user_id=?", (user[0],))
        data = c.fetchall()

        for pid, name in data:
            with st.expander(name):
                c.execute("SELECT data FROM plans WHERE id=?", (pid,))
                plan = json.loads(c.fetchone()[0])

                for d, meals in plan.items():
                    st.write(f"Day {int(d)+1}")
                    for m, foods in meals.items():
                        st.write(m, ":", ", ".join(foods))

    # ===== Admin Plans
    elif st.session_state.page == "adminplans":
        st.title("Admin Saved Plans")

        c.execute("SELECT name FROM plans WHERE type='admin'")
        data = c.fetchall()

        for p in data:
            st.write(p[0])

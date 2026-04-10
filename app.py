# ===============================
# DNP PRO FULL SYSTEM (ADMIN FIXED)
# ===============================

import streamlit as st
import sqlite3
import hashlib
import random

# ===============================
# IMPORTANT: PUT YOUR EMAIL HERE
# ===============================
ADMIN_EMAIL = "your@email.com"  # غيره بإيميلك

# ===============================
# DB SETUP
# ===============================
conn = sqlite3.connect("dnp.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
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
# HELPERS
# ===============================
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()


def calc_bmi(w, h):
    return w / ((h/100)**2)


def calc_calories(w, h, age, goal):
    bmr = 10*w + 6.25*h - 5*age + 5

    if goal == "fat_loss":
        return bmr - 400
    elif goal == "muscle":
        return bmr + 400
    return bmr


def random_meals():
    c.execute("SELECT * FROM meals")
    data = c.fetchall()
    return random.sample(data, min(len(data), 5)) if data else []

# ===============================
# UI
# ===============================
st.set_page_config(layout="centered")

if "user" not in st.session_state:
    st.session_state.user = None

# ===============================
# AUTH
# ===============================
st.title("DNP PRO")

menu = st.sidebar.selectbox("menu", ["login", "register"])

if menu == "register":
    email = st.text_input("email")
    password = st.text_input("password", type="password")

    if st.button("create"):
        is_admin = 1 if email == ADMIN_EMAIL else 0

        c.execute("INSERT INTO users (email, password, is_admin) VALUES (?,?,?)",
                  (email, hash_pass(password), is_admin))
        conn.commit()

        st.success("account created")

if menu == "login":
    email = st.text_input("email")
    password = st.text_input("password", type="password")

    if st.button("login"):
        c.execute("SELECT * FROM users WHERE email=? AND password=?",
                  (email, hash_pass(password)))
        user = c.fetchone()

        if user:
            # ضمان إن الإيميل ده دايماً admin حتى لو اتسجل قبل كده
            if user[1] == ADMIN_EMAIL and user[3] == 0:
                c.execute("UPDATE users SET is_admin=1 WHERE email=?", (ADMIN_EMAIL,))
                conn.commit()
                c.execute("SELECT * FROM users WHERE email=?", (ADMIN_EMAIL,))
                user = c.fetchone()

            st.session_state.user = user
            st.success("logged in")

# ===============================
# MAIN APP
# ===============================
if st.session_state.user:

    user_id = st.session_state.user[0]
    is_admin = st.session_state.user[3]

    tab = st.sidebar.selectbox("app", ["dashboard", "tracking", "meals", "plans"])

    # ===========================
    # DASHBOARD
    # ===========================
    if tab == "dashboard":
        w = st.number_input("weight")
        h = st.number_input("height")
        age = st.number_input("age")

        goal = st.selectbox("goal", ["fat_loss", "muscle", "maintain"])

        if st.button("calculate"):
            bmi = calc_bmi(w, h)
            cal = calc_calories(w, h, age, goal)

            st.write("BMI", round(bmi,1))
            st.write("Calories", int(cal))

    # ===========================
    # TRACKING
    # ===========================
    if tab == "tracking":
        weight = st.number_input("today weight")

        if st.button("save"):
            c.execute("INSERT INTO tracking (user_id, weight, date) VALUES (?,?,datetime('now'))",
                      (user_id, weight))
            conn.commit()

        c.execute("SELECT weight, date FROM tracking WHERE user_id=? ORDER BY id DESC", (user_id,))
        data = c.fetchall()

        for d in data:
            st.write(d)

    # ===========================
    # MEALS
    # ===========================
    if tab == "meals":

        if is_admin:
            st.subheader("ADD / CONTROL MEALS")
            name = st.text_input("name")
            cal = st.number_input("calories")
            p = st.number_input("protein")
            cbs = st.number_input("carbs")
            f = st.number_input("fat")

            if st.button("add meal"):
                c.execute("INSERT INTO meals (name, calories, protein, carbs, fat) VALUES (?,?,?,?,?)",
                          (name, cal, p, cbs, f))
                conn.commit()

            # delete meals
            st.subheader("DELETE MEAL")
            c.execute("SELECT id, name FROM meals")
            all_meals = c.fetchall()
            meal_names = [m[1] for m in all_meals]

            if meal_names:
                selected = st.selectbox("choose meal to delete", meal_names)
                meal_id = next(m[0] for m in all_meals if m[1] == selected)

                if st.button("delete"):
                    c.execute("DELETE FROM meals WHERE id=?", (meal_id,))
                    conn.commit()

        st.subheader("MEAL OPTIONS")
        meals = random_meals()

        for m in meals:
            st.write(m)

    # ===========================
    # PLANS (PACKAGES)
    # ===========================
    if tab == "plans":
        st.subheader("packages")

        st.write("FREE")
        st.write("basic tracking")

        st.write("PRO - 10$")
        st.write("meal plans + tracking")

        st.write("COACH - 30$")
        st.write("custom plans + follow up")

# ===============================
# DEFAULT DATA
# ===============================
c.execute("SELECT COUNT(*) FROM meals")
if c.fetchone()[0] == 0:
    sample = [
        ("chicken breast", 165, 31, 0, 3),
        ("rice", 200, 4, 45, 1),
        ("eggs", 150, 12, 1, 10),
        ("tuna", 120, 25, 0, 1),
        ("beef", 250, 26, 0, 15),
    ]

    for s in sample:
        c.execute("INSERT INTO meals (name, calories, protein, carbs, fat) VALUES (?,?,?,?,?)", s)
    conn.commit()

# ===============================
# END
# ===============================

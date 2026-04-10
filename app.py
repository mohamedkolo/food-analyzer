import streamlit as st
import sqlite3
import hashlib
import os
import json
from datetime import datetime

st.set_page_config(page_title="NutraX", layout="wide")

# ===== Language =====
if "lang" not in st.session_state:
    st.session_state.lang = "ar"

lang = st.sidebar.selectbox("Language", ["ar", "en"])
st.session_state.lang = lang

# ===== Style =====
st.markdown("""
<style>
html, body { direction: rtl; }
.metric-box { background:#fff;padding:10px;border-radius:10px }
</style>
""", unsafe_allow_html=True)

# ===== DB =====
conn = sqlite3.connect("nutrax.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, password TEXT, name TEXT, is_admin INTEGER)")
c.execute("""CREATE TABLE IF NOT EXISTS saved_plans (
id INTEGER PRIMARY KEY,
user_id INTEGER,
plan_name TEXT,
plan_data TEXT,
created_at TEXT,
type TEXT)""")
conn.commit()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

# create admin
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, 1)", ("admin@nutrax.com", hash_pass("123456"), "Admin"))
    conn.commit()

# ===== FOOD DB =====
LOCAL_DB = {
    "chicken": {"name": "دجاج", "cal":165},
    "beef": {"name": "لحم", "cal":250},
    "fish": {"name": "سمك", "cal":180},
    "eggs": {"name": "بيض", "cal":78},
    "rice": {"name": "رز", "cal":130},
    "oats": {"name": "شوفان", "cal":389},
    "milk": {"name": "لبن", "cal":60},
    "banana": {"name": "موز", "cal":89},
    "apple": {"name": "تفاح", "cal":52},
    "almonds": {"name": "لوز", "cal":579},
    "potato": {"name": "بطاطس", "cal":87},
    "broccoli": {"name": "بروكلي", "cal":34},
    "peanut": {"name": "زبدة فول سوداني", "cal":588},
    "lentils": {"name": "عدس", "cal":116},
    "dates": {"name": "تمر", "cal":282}
}

# ===== STATE =====
if "page" not in st.session_state: st.session_state.page = "login"
if "user" not in st.session_state: st.session_state.user = None

# ===== LOGIN =====
if st.session_state.page == "login":
    st.title("NutraX")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hash_pass(p)))
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
        if st.button("Register"):
            c.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, 0)", (e, hash_pass(p), n))
            conn.commit()
            st.success("Done")

# ===== APP =====
else:
    u = st.session_state.user
    u_id = u[0]

    with st.sidebar:
        st.write(u[3])
        if st.button("Dashboard"): st.session_state.page="dashboard"
        if st.button("Create Plan"): st.session_state.page="planner"
        if st.button("Saved"): st.session_state.page="saved"
        if st.button("Logout"):
            st.session_state.user=None
            st.session_state.page="login"
            st.rerun()

    # ===== Dashboard =====
    if st.session_state.page == "dashboard":
        st.title("Dashboard")

        c.execute("SELECT COUNT(*) FROM saved_plans WHERE user_id=?", (u_id,))
        total = c.fetchone()[0]

        st.metric("عدد جداولك", total)

    # ===== Planner =====
    elif st.session_state.page == "planner":
        st.title("Diet Planner")

        days = st.number_input("عدد الأيام", 1, 14, 1)

        plan = {}
        total_cal = 0

        for d in range(days):
            st.subheader(f"يوم {d+1}")
            plan[d] = {}

            for meal in ["فطار", "غداء", "عشاء", "سناك"]:
                foods = st.multiselect(f"{meal} يوم {d+1}", list(LOCAL_DB.keys()), key=f"{meal}{d}")
                plan[d][meal] = {}

                for f in foods:
                    g = st.number_input(f"{LOCAL_DB[f]['name']} جرام", 0, 500, 100, key=f"{f}{meal}{d}")
                    plan[d][meal][f] = g
                    total_cal += (g/100)*LOCAL_DB[f]["cal"]

        st.metric("السعرات", int(total_cal))

        name = st.text_input("اسم الجدول")

        save_type = st.selectbox("نوع الحفظ", ["خاص بي", "للعميل", "عام"])

        if st.button("Save"):
            c.execute("INSERT INTO saved_plans VALUES (NULL, ?, ?, ?, datetime('now'), ?)",
                      (u_id, name, json.dumps(plan), save_type))
            conn.commit()
            st.success("Saved")

    # ===== Saved =====
    elif st.session_state.page == "saved":
        st.title("Saved Plans")

        filter_type = st.selectbox("فلتر", ["الكل", "خاص بي", "للعميل", "عام"])

        query = "SELECT id, plan_name FROM saved_plans WHERE user_id=?"
        params = [u_id]

        if filter_type != "الكل":
            query += " AND type=?"
            params.append(filter_type)

        c.execute(query, params)
        data = c.fetchall()

        for pid, name in data:
            with st.expander(name):
                c.execute("SELECT plan_data FROM saved_plans WHERE id=?", (pid,))
                p = json.loads(c.fetchone()[0])

                for d, meals in p.items():
                    st.write(f"يوم {int(d)+1}")
                    for m, foods in meals.items():
                        st.write(m, ":", foods)

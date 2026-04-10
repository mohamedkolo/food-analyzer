import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime

st.set_page_config(page_title="NutraX", page_icon="💊", layout="wide")

# قاعدة البيانات
DB_FILE = "nutrax_simple.db"
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

    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, name TEXT, goal TEXT, is_admin INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS tracking (id INTEGER PRIMARY KEY, user_id INTEGER, weight REAL, date TEXT)")
    conn.commit()

init_db()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users (email, password, name, is_admin) VALUES (?, ?, ?, ?)", ("admin@nutrax.com", hash_pass("admin123"), "Admin", 1))
    conn.commit()

# قاعدة الأكل
LOCAL_DB = {
    "apple": {"name_ar": "تفاح", "cal": 52, "p": 0.3, "c": 14, "f": 0.2},
    "banana": {"name_ar": "موز", "cal": 89, "p": 1.1, "c": 23, "f": 0.3},
    "chicken": {"name_ar": "دجاج", "cal": 165, "p": 31, "c": 0, "f": 3.6},
    "beef": {"name_ar": "لحم", "cal": 250, "p": 26, "c": 0, "f": 15},
    "rice": {"name_ar": "أرز", "cal": 130, "p": 2.7, "c": 28, "f": 0.3},
    "eggs": {"name_ar": "بيض", "cal": 78, "p": 6, "c": 0.6, "f": 5},
    "cheese": {"name_ar": "جبن", "cal": 264, "p": 18, "c": 1.3, "f": 21},
    "oats": {"name_ar": "شوفان", "cal": 389, "p": 16.9, "c": 66, "f": 6.9},
}

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None

# صفحة الدخول
if st.session_state.page == 'login':
    st.title("💊 NutraX Login")
    tab1, tab2 = st.tabs(["دخول", "تسجيل جديد"])
    with tab1:
        with st.form("l"):
            e = st.text_input("البريد")
            p = st.text_input("الباسورد", type="password")
            if st.form_submit_button("دخول"):
                c.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hash_pass(p)))
                u = c.fetchone()
                if u:
                    st.session_state.user = u
                    st.session_state.page = 'home'
                    st.rerun()
                else: st.error("خطأ")
    with tab2:
        with st.form("r"):
            n = st.text_input("الاسم")
            e = st.text_input("البريد")
            p = st.text_input("الباسورد", type="password")
            if st.form_submit_button("تسجيل"):
                try:
                    c.execute("INSERT INTO users (email, password, name, is_admin) VALUES (?, ?, ?, 0)", (e, hash_pass(p), n))
                    conn.commit()
                    st.success("تم")
                except: st.error("البريد مستخدم")

# التطبيق
else:
    u = st.session_state.user
    is_admin = u[5]
    with st.sidebar:
        st.write(f"أهلا، {u[3]}")
        if st.button("الرئيسية"): st.session_state.page = 'home'; st.rerun()
        if st.button("محلل الأكل"): st.session_state.page = 'food'; st.rerun()
        if st.button("خروج"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()
        if is_admin and st.button("Admin Panel"): st.session_state.page = 'admin'; st.rerun()

    if st.session_state.page == 'home':
        st.header("الرئيسية")
        st.metric("الهدف", u[4] or "لا يوجد")

    elif st.session_state.page == 'food':
        st.header("بحث عن طعام")
        s = st.text_input("اكتب اسم الطعام")
        if s:
            for k, v in LOCAL_DB.items():
                if s in k or s in v['name_ar']:
                    st.write(f"**{v['name_ar']}**: {v['cal']} سعرة")

    elif st.session_state.page == 'admin':
        st.header("المستخدمين")
        c.execute("SELECT * FROM users")
        st.write(c.fetchall())

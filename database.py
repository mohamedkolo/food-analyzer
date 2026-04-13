import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nutrax.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hp(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        country TEXT,
        lang TEXT DEFAULT 'ar',
        height REAL,
        weight REAL,
        age INTEGER,
        gender TEXT DEFAULT 'ذكر',
        goal TEXT DEFAULT 'maintain',
        activity REAL DEFAULT 1.55,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS weight_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        weight REAL NOT NULL,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS saved_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        plan_data TEXT NOT NULL,
        plan_type TEXT DEFAULT 'personal',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("SELECT id FROM users WHERE is_admin=1")
    if not c.fetchone():
        c.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, 1)",
                  ("Admin", "admin@nutrax.com", hp("nutrax2025")))
    conn.commit()
    conn.close()

def get_user(email, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hp(password)))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def register_user(name, email, password, country):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name, email, password, country) VALUES (?, ?, ?, ?)",
                  (name, email, hp(password), country))
        conn.commit()
        return "ok"
    except sqlite3.IntegrityError:
        return "exists"
    finally:
        conn.close()

def update_user_profile(user_id, data):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""UPDATE users SET height=?, weight=?, age=?, gender=?, goal=?, activity=?
        WHERE id=?""",
        (data["height"], data["weight"], data["age"],
         data["gender"], data["goal"], data["activity"], user_id))
    conn.commit()
    conn.close()

def log_weight(user_id, weight):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)", (user_id, weight))
    conn.commit()
    conn.close()

def get_weight_log(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at ASC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

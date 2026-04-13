import sqlite3
import hashlib
import os

DB_PATH = "/tmp/nutrax.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hp(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, country TEXT, lang TEXT DEFAULT 'ar', height REAL, weight REAL, age INTEGER, gender TEXT DEFAULT 'male', goal TEXT DEFAULT 'maintain', activity REAL DEFAULT 1.55, is_admin INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS weight_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS saved_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, plan_data TEXT, plan_type TEXT DEFAULT 'personal', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("SELECT id FROM users WHERE is_admin=1")
    if not c.fetchone():
        c.execute("INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,1)", ("Admin","admin@nutrax.com",hp("nutrax2025")))
    conn.commit()
    conn.close()

def get_user(email, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hp(password)))
    u = c.fetchone()
    conn.close()
    return u

def get_user_by_id(uid):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    u = c.fetchone()
    conn.close()
    return u

def register_user(name, email, password, country):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name,email,password,country) VALUES (?,?,?,?)", (name,email,hp(password),country))
        conn.commit()
        return "ok"
    except:
        return "exists"
    finally:
        conn.close()

def update_user_profile(uid, data):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET height=?,weight=?,age=?,gender=?,goal=?,activity=? WHERE id=?", (data["height"],data["weight"],data["age"],data["gender"],data["goal"],data["activity"],uid))
    conn.commit()
    conn.close()

def log_weight(uid, weight):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO weight_log (user_id,weight) VALUES (?,?)", (uid,weight))
    conn.commit()
    conn.close()

def get_weight_log(uid):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at ASC", (uid,))
    r = c.fetchall()
    conn.close()
    return r

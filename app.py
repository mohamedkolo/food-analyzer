# ===============================
# NUTRAX ULTIMATE SYSTEM
# ===============================

import streamlit as st
import sqlite3
import hashlib
import random
import requests
import copy
from datetime import datetime

# ===============================
# PAGE CONFIG & STYLES (NutraX Branding)
# ===============================
st.set_page_config(
    page_title="NutraX — النظام الغذائي المتكامل",
    page_icon="💊",
    layout="centered",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    .main { background-color: #f0f4f8; }
    
    /* Cards & UI Elements */
    .metric-card {
        background: white; border-radius: 12px; padding: 14px 18px;
        margin: 6px 0; box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        display: flex; justify-content: space-between; align-items: center;
    }
    .section-title {
        font-size: 1.1em; font-weight: 700; color: #0056b3;
        border-right: 5px solid #007bff; padding-right: 12px; margin: 20px 0 10px;
    }
    
    /* Plans Cards - NutraX Theme */
    .plan-container { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }
    .plan-card {
        background: white; border-radius: 20px; padding: 30px;
        width: 300px; text-align: center; box-shadow: 0 10px 25px rgba(0,123,255,0.1);
        border-top: 6px solid #ccc; transition: transform 0.3s, box-shadow 0.3s;
    }
    .plan-card:hover { transform: translateY(-8px); box-shadow: 0 15px 35px rgba(0,123,255,0.15); }
    .plan-free { border-color: #6c757d; }
    .plan-pro { border-color: #007bff; }
    .plan-coach { border-color: #ffc107; }
    .plan-price { font-size: 2.5em; font-weight: 800; margin: 15px 0; color: #222; }
    .plan-features { list-style: none; padding: 0; text-align: right; margin: 25px 0; font-size: 1.05em; }
    .plan-features li { padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
    .btn-plan {
        display: block; width: 100%; padding: 12px; border: none; border-radius: 10px;
        color: white; font-weight: bold; cursor: pointer; margin-top: 15px; font-size: 1.1em;
    }

    /* Meal Planner Styles */
    .meal-card {
        background: white; border-radius: 14px; padding: 20px;
        margin: 12px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-right: 6px solid #007bff;
    }
    .total-bar {
        background: linear-gradient(135deg, #0056b3, #007bff);
        color: white; border-radius: 16px; padding: 20px 30px; margin: 20px 0; text-align: center;
        font-weight: bold; font-size: 1.2em;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# DB SETUP
# ===============================
conn = sqlite3.connect("nutrax.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
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

# ===============================
# AUTO-CREATE DEFAULT ADMIN
# ===============================
# الكود ده هيفحص لو مفيش أدمن، وهيعمل واحد واحد
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    admin_email = "admin@nutrax.com"
    admin_pass = "admin123"
    c.execute("INSERT INTO users (email, password, is_admin) VALUES (?, ?, ?)",
              (admin_email, hash_pass(admin_pass), 1))
    conn.commit()

# ===============================
# DATA Dictionaries
# ===============================
LOCAL_DB = {
    "apple":          {"name_ar": "تفاح",            "nutrients": {"Energy":52,  "Protein":0.26,"Total lipid (fat)":0.17,"Carbohydrate, by difference":13.81,"Fiber, total dietary":2.4,"Sugars, total including NLEA":10.39,"Calcium, Ca":6,"Iron, Fe":0.12,"Potassium, K":107,"Sodium, Na":1,"Vitamin C, total ascorbic acid":4.6,"Vitamin A, RAE":3,"Magnesium, Mg":5,"Phosphorus, P":11,"Zinc, Zn":0.04,"Fatty acids, total saturated":0.03,"Cholesterol":0}},
    "banana":         {"name_ar": "موز",             "nutrients": {"Energy":89,  "Protein":1.09,"Total lipid (fat)":0.33,"Carbohydrate, by difference":22.84,"Fiber, total dietary":2.6,"Sugars, total including NLEA":12.23,"Calcium, Ca":5,"Iron, Fe":0.26,"Potassium, K":358,"Sodium, Na":1,"Vitamin C, total ascorbic acid":8.7,"Vitamin A, RAE":3,"Magnesium, Mg":27,"Phosphorus, P":22,"Zinc, Zn":0.15,"Vitamin B-6":0.37,"Folate, total":20,"Fatty acids, total saturated":0.11,"Cholesterol":0}},
    "chicken breast": {"name_ar": "صدر دجاج مشوي",  "nutrients": {"Energy":165, "Protein":31.02,"Total lipid (fat)":3.57,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":15,"Iron, Fe":1.04,"Potassium, K":220,"Sodium, Na":74,"Phosphorus, P":220,"Zinc, Zn":1.0,"Vitamin B-12":0.3,"Niacin":13.7,"Fatty acids, total saturated":1.01,"Cholesterol":85}},
    "egg":            {"name_ar": "بيضة كاملة",      "nutrients": {"Energy":143, "Protein":12.56,"Total lipid (fat)":9.51,"Carbohydrate, by difference":0.72,"Fiber, total dietary":0,"Calcium, Ca":56,"Iron, Fe":1.75,"Potassium, K":138,"Sodium, Na":142,"Phosphorus, P":198,"Zinc, Zn":1.29,"Vitamin A, RAE":160,"Vitamin D (D2 + D3)":2.0,"Vitamin B-12":0.89,"Riboflavin":0.46,"Fatty acids, total saturated":3.13,"Cholesterol":372}},
    "rice":           {"name_ar": "أرز أبيض مطبوخ", "nutrients": {"Energy":130, "Protein":2.69,"Total lipid (fat)":0.28,"Carbohydrate, by difference":28.17,"Fiber, total dietary":0.4,"Calcium, Ca":10,"Iron, Fe":1.49,"Potassium, K":35,"Sodium, Na":1,"Phosphorus, P":43,"Zinc, Zn":0.49,"Fatty acids, total saturated":0.08,"Cholesterol":0}},
    "salmon":         {"name_ar": "سمك سلمون",       "nutrients": {"Energy":208, "Protein":20.42,"Total lipid (fat)":13.42,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":12,"Iron, Fe":0.8,"Potassium, K":363,"Sodium, Na":59,"Phosphorus, P":252,"Zinc, Zn":0.64,"Vitamin D (D2 + D3)":11.1,"Vitamin B-12":3.18,"Fatty acids, total saturated":3.05,"Fatty acids, total polyunsaturated":3.77,"Cholesterol":63}},
    "milk":           {"name_ar": "حليب كامل الدسم", "nutrients": {"Energy":61,  "Protein":3.15,"Total lipid (fat)":3.27,"Carbohydrate, by difference":4.78,"Fiber, total dietary":0,"Sugars, total including NLEA":5.05,"Calcium, Ca":113,"Iron, Fe":0.03,"Potassium, K":150,"Sodium, Na":43,"Phosphorus, P":84,"Zinc, Zn":0.37,"Vitamin A, RAE":46,"Vitamin D (D2 + D3)":1.3,"Vitamin B-12":0.45,"Riboflavin":0.17,"Fatty acids, total saturated":1.87,"Cholesterol":10}},
    "bread":          {"name_ar": "خبز أبيض",        "nutrients": {"Energy":265, "Protein":9.0,"Total lipid (fat)":3.2,"Carbohydrate, by difference":49.0,"Fiber, total dietary":2.7,"Calcium, Ca":182,"Iron, Fe":3.6,"Potassium, K":115,"Sodium, Na":491,"Phosphorus, P":108,"Zinc, Z

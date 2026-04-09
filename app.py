# ===============================
# DNP PRO VERSION (CLEAN + OPTIMIZED)
# ===============================

import streamlit as st
import requests
import os
from datetime import datetime

# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="DNP Pro", layout="centered")

USDA_API_KEY = os.getenv("USDA_API_KEY")
BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# ===============================
# CACHE (PERFORMANCE BOOST)
# ===============================
@st.cache_data(ttl=3600)
def search_usda(query):
    r = requests.get(f"{BASE_URL}/foods/search", params={
        "query": query,
        "pageSize": 10,
        "api_key": USDA_API_KEY
    })
    return r.json().get("foods", [])

@st.cache_data(ttl=3600)
def get_food(fdc_id):
    r = requests.get(f"{BASE_URL}/food/{fdc_id}", params={
        "api_key": USDA_API_KEY
    })
    return r.json()

# ===============================
# CALCULATIONS
# ===============================
def calc_bmi(w, h):
    return w / ((h/100)**2)


def calc_bmr(w, h, age, gender):
    if gender == "ذكر":
        return 10*w + 6.25*h - 5*age + 5
    return 10*w + 6.25*h - 5*age - 161


def macros_split(cal, goal):
    if goal == "cut":
        p, f, c = 0.35, 0.25, 0.40
    elif goal == "bulk":
        p, f, c = 0.30, 0.25, 0.45
    else:
        p, f, c = 0.25, 0.30, 0.45

    return {
        "protein": (cal*p)/4,
        "fat": (cal*f)/9,
        "carbs": (cal*c)/4
    }

# ===============================
# UI
# ===============================
st.title("DNP — Pro Version")

# -------------------------------
# BMI SECTION
# -------------------------------
st.header("BMI + Calories")

col1, col2 = st.columns(2)
with col1:
    weight = st.number_input("وزن", value=70)
    age = st.number_input("العمر", value=25)
with col2:
    height = st.number_input("طول", value=170)
    gender = st.selectbox("الجنس", ["ذكر", "أنثى"])

activity = st.selectbox("النشاط", [1.2, 1.375, 1.55, 1.725])
goal = st.selectbox("الهدف", ["cut", "bulk", "maintain"])

if st.button("احسب"):
    bmi = calc_bmi(weight, height)
    bmr = calc_bmr(weight, height, age, gender)
    tdee = bmr * activity

    if goal == "cut":
        tdee -= 300
    elif goal == "bulk":
        tdee += 400

    macros = macros_split(tdee, goal)

    st.success(f"BMI: {bmi:.1f}")
    st.info(f"Calories: {tdee:.0f}")

    st.write(macros)

# -------------------------------
# FOOD ANALYZER
# -------------------------------
st.header("Food Analyzer")

query = st.text_input("food")

if st.button("search"):
    foods = search_usda(query)

    if foods:
        names = [f["description"] for f in foods]
        selected = st.selectbox("اختار", names)

        food = next(f for f in foods if f["description"] == selected)
        data = get_food(food["fdcId"])

        st.json(data)

# ===============================
# SIMPLE MEAL PLAN
# ===============================
st.header("Meal Plan")

if "meals" not in st.session_state:
    st.session_state.meals = []

meal = st.text_input("meal")

if st.button("add meal"):
    st.session_state.meals.append(meal)

for m in st.session_state.meals:
    st.write("-", m)

# ===============================
# END
# ===============================

import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime

st.set_page_config(page_title="NutraX", layout="wide")

# ===== DB =====
conn = sqlite3.connect("nutrax.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY,
email TEXT UNIQUE,
password TEXT,
name TEXT,
is_admin INTEGER)""")

c.execute("""CREATE TABLE IF NOT EXISTS saved_plans (
id INTEGER PRIMARY KEY,
user_id INTEGER,
plan_name TEXT,
plan_data TEXT,
created_at TEXT,
type TEXT)""")

conn.commit()

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

# admin
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users VALUES (NULL,'admin@nutrax.com',?,'Admin',1)", (hash_pass("123456"),))
    conn.commit()

# ===== FOOD =====
LOCAL_DB = {
"chicken":{"name":"دجاج","cal":165,"p":31,"c":0,"f":3},
"beef":{"name":"لحم","cal":250,"p":26,"c":0,"f":15},
"rice":{"name":"رز","cal":130,"p":2,"c":28,"f":0},
"oats":{"name":"شوفان","cal":389,"p":16,"c":66,"f":6},
"eggs":{"name":"بيض","cal":78,"p":6,"c":1,"f":5},
"milk":{"name":"لبن","cal":60,"p":3,"c":5,"f":3},
"banana":{"name":"موز","cal":89,"p":1,"c":23,"f":0},
"apple":{"name":"تفاح","cal":52,"p":0,"c":14,"f":0},
"almonds":{"name":"لوز","cal":579,"p":21,"c":22,"f":50},
"potato":{"name":"بطاطس","cal":87,"p":2,"c":20,"f":0},
"broccoli":{"name":"بروكلي","cal":34,"p":2,"c":7,"f":0},
"lentils":{"name":"عدس","cal":116,"p":9,"c":20,"f":0},
"dates":{"name":"تمر","cal":282,"p":2,"c":75,"f":0}
}

# ===== STATE =====
if "page" not in st.session_state: st.session_state.page="login"
if "user" not in st.session_state: st.session_state.user=None

# ===== LOGIN =====
if st.session_state.page=="login":
    st.title("NutraX")

    tab1,tab2=st.tabs(["Login","Register"])

    with tab1:
        e=st.text_input("Email")
        p=st.text_input("Password",type="password")
        if st.button("Login"):
            c.execute("SELECT * FROM users WHERE email=? AND password=?",(e,hash_pass(p)))
            u=c.fetchone()
            if u:
                st.session_state.user=u
                st.session_state.page="dashboard"
                st.rerun()
            else: st.error("Wrong data")

    with tab2:
        n=st.text_input("Name")
        e=st.text_input("Email")
        p=st.text_input("Password",type="password")
        if st.button("Register"):
            c.execute("INSERT INTO users VALUES(NULL,?,?,?,0)",(e,hash_pass(p),n))
            conn.commit()
            st.success("Done")

# ===== APP =====
else:
    u=st.session_state.user
    u_id=u[0]

    with st.sidebar:
        st.write(u[3])
        if st.button("Dashboard"): st.session_state.page="dashboard"
        if st.button("Profile"): st.session_state.page="profile"
        if st.button("Analyzer"): st.session_state.page="analyzer"
        if st.button("Planner"): st.session_state.page="planner"
        if st.button("Saved"): st.session_state.page="saved"
        if st.button("Logout"):
            st.session_state.user=None
            st.session_state.page="login"
            st.rerun()

    # ===== Dashboard =====
    if st.session_state.page=="dashboard":
        st.title("Dashboard")

        if "metrics" in st.session_state:
            m=st.session_state.metrics
            c1,c2,c3=st.columns(3)
            c1.metric("BMI",m["bmi"])
            c2.metric("BMR",m["bmr"])
            c3.metric("TDEE",m["tdee"])
        else:
            st.warning("ادخل بياناتك")

        c.execute("SELECT COUNT(*) FROM saved_plans WHERE user_id=?",(u_id,))
        st.metric("Plans",c.fetchone()[0])

    # ===== Profile =====
    elif st.session_state.page=="profile":
        st.title("Profile")

        h=st.number_input("Height",100,250,170)
        w=st.number_input("Weight",30,200,70)
        age=st.number_input("Age",10,80,25)

        if st.button("Calculate"):
            bmi=w/((h/100)**2)
            bmr=10*w+6.25*h-5*age+5
            tdee=bmr*1.55

            st.session_state.metrics={
                "bmi":round(bmi,1),
                "bmr":int(bmr),
                "tdee":int(tdee)
            }
            st.success("Done")

    # ===== Analyzer =====
    elif st.session_state.page=="analyzer":
        st.title("Food Analyzer")

        f=st.selectbox("Food",list(LOCAL_DB.keys()))
        g=st.number_input("Grams",0,1000,100)

        data=LOCAL_DB[f]

        cal=(g/100)*data["cal"]
        p=(g/100)*data["p"]
        c_=(g/100)*data["c"]
        f_=(g/100)*data["f"]

        c1,c2,c3,c4=st.columns(4)
        c1.metric("Cal",int(cal))
        c2.metric("Protein",round(p,1))
        c3.metric("Carb",round(c_,1))
        c4.metric("Fat",round(f_,1))

    # ===== Planner =====
    elif st.session_state.page=="planner":
        st.title("Planner")

        mode=st.radio("Mode",["جاهز","مخصص"])

        plan={}
        total=0

        if mode=="جاهز":
            template={
                "فطار":{"oats":50,"eggs":100},
                "غداء":{"chicken":150,"rice":100},
                "عشاء":{"beef":150,"potato":100}
            }

            for m,foods in template.items():
                st.write(m)
                for k,v in foods.items():
                    g=st.number_input(k,0,500,v)
                    total+=(g/100)*LOCAL_DB[k]["cal"]

        else:
            days=st.number_input("Days",1,7,1)
            for d in range(days):
                st.write("Day",d+1)
                plan[d]={}
                for meal in ["فطار","غداء","عشاء","سناك"]:
                    foods=st.multiselect(meal,list(LOCAL_DB.keys()),key=f"{meal}{d}")
                    plan[d][meal]={}
                    for f in foods:
                        g=st.number_input(f,0,500,100,key=f"{f}{meal}{d}")
                        plan[d][meal][f]=g
                        total+=(g/100)*LOCAL_DB[f]["cal"]

        st.metric("Calories",int(total))

        name=st.text_input("Plan name")
        t=st.selectbox("Type",["خاص بي","للعميل","عام"])

        if st.button("Save"):
            c.execute("INSERT INTO saved_plans VALUES(NULL,?,?,?,datetime('now'),?)",
                      (u_id,name,json.dumps(plan),t))
            conn.commit()
            st.success("Saved")

    # ===== Saved =====
    elif st.session_state.page=="saved":
        st.title("Saved")

        f=st.selectbox("Filter",["الكل","خاص بي","للعميل","عام"])

        q="SELECT id,plan_name FROM saved_plans WHERE user_id=?"
        p=[u_id]

        if f!="الكل":
            q+=" AND type=?"
            p.append(f)

        c.execute(q,p)
        data=c.fetchall()

        for pid,name in data:
            with st.expander(name):
                c.execute("SELECT plan_data FROM saved_plans WHERE id=?",(pid,))
                d=json.loads(c.fetchone()[0])

                for day,meals in d.items():
                    st.write("Day",int(day)+1)
                    for m,foods in meals.items():
                        st.write(m,foods)

import streamlit as st
import sqlite3, hashlib, os, json, math
from datetime import datetime

st.set_page_config(page_title="NutraX", page_icon="🥗", layout="wide",
                   initial_sidebar_state="collapsed")

# ══════════════════════════════════════════
# LANGUAGE SYSTEM
# ══════════════════════════════════════════
LANG = {
    "ar": {
        "app_name": "NutraX",
        "tagline": "مساعدك الذكي للتغذية الصحية",
        "login": "تسجيل الدخول", "register": "حساب جديد",
        "email": "البريد الإلكتروني", "password": "كلمة المرور",
        "name": "الاسم الكامل", "birth_year": "سنة الميلاد",
        "country": "البلد", "enter": "دخول ←", "create": "إنشاء الحساب ←",
        "remember": "تذكرني على هذا الجهاز",
        "wrong_creds": "البريد أو كلمة المرور غير صحيحة",
        "email_used": "البريد الإلكتروني مستخدم بالفعل",
        "registered": "تم التسجيل! سجل دخولك.",
        "dashboard": "الرئيسية", "settings": "الإعدادات",
        "analyzer": "محلل الطعام", "planner": "مصمم الجدول",
        "suggester": "مقترح الوجبات", "saved": "جداولي",
        "history": "سجل الوزن", "clinical": "المرجع الكلينيكي",
        "logout": "خروج",
        "complete_settings": "أكمل إعداداتك أولاً لحساب أهدافك",
        "go_settings": "اذهب للإعدادات",
        "your_goal": "هدفك", "tdee": "TDEE", "daily_target": "هدف يومي",
        "calories": "السعرات", "protein": "بروتين",
        "carbs": "كارب", "fat": "دهون",
        "bmi": "BMI", "last_weight": "آخر وزن", "plans": "جداول",
        "quick_access": "وصول سريع",
        "height": "الطول (سم)", "weight_kg": "الوزن (كجم)",
        "age": "العمر (سنة)", "your_goal_lbl": "هدفك",
        "activity": "مستوى النشاط", "save_calc": "حفظ وحساب الأهداف",
        "saved_ok": "تم الحفظ!",
        "fat_loss": "🔥 خسارة دهون", "muscle_gain": "💪 بناء عضل", "maintain": "⚖️ ثبات الوزن",
        "sedentary": "مستقر", "light": "خفيف (1-3 أيام)",
        "moderate": "معتدل (3-5 أيام)", "active": "نشيط (6-7 أيام)", "athlete": "رياضي محترف",
        "filter_cat": "الفئة", "all": "الكل", "search": "ابحث بالعربي أو الإنجليزي",
        "per_100g": "لكل 100 جرام",
        "results": "نتيجة من", "items": "صنف",
        "no_results": "لا نتائج. جرب كلمة مختلفة.",
        "show_first30": "عرض أول 30 — ضيّق البحث لرؤية المزيد",
        "days": "عدد الأيام", "breakfast": "🌅 فطار", "lunch": "☀️ غداء",
        "dinner": "🌙 عشاء", "snack": "🍎 سناك", "choose": "اختر",
        "summary": "ملخص الجدول", "gap": "الفارق", "perfect": "ممتاز! الجدول متوازن 🎯",
        "over_cal": "زيادة — قلل الكميات",
        "under_cal": "ناقص — أضف وجبة",
        "plan_name": "اسم الجدول", "plan_type": "نوع",
        "save_plan": "حفظ الجدول", "saved_plan_ok": "تم حفظ الجدول!",
        "personal": "خاص بي", "for_client": "للعميل", "public": "عام",
        "no_plans": "لا توجد جداول محفوظة بعد.",
        "shopping": "مشتريات", "delete": "حذف",
        "confirm_delete": "هل تحذف؟", "yes": "✅ نعم", "cancel": "❌ إلغاء",
        "log_weight": "وزن اليوم (كجم)", "log_btn": "تسجيل",
        "min_weight": "📉 أقل", "max_weight": "📈 أعلى", "last_weight2": "📊 آخر",
        "no_weight": "سجل وزنك اليوم!",
        "what_ate": "أدخل ما أكلته اليوم — سنقترح الوجبات المتبقية.",
        "ate": "✅ أكلته", "remaining": "🎯 المتبقي",
        "suggest_btn": "💡 اقترح لي ←", "reached_goal": "🎉 وصلت لهدفك اليومي!",
        "suggested_meals": "🍽️ وجبات مقترحة",
        "ideal_weight": "الوزن المثالي", "filter": "فلتر",
        "select_condition": "اختر الحالة أو الأمراض",
        "multi_condition": "يمكن اختيار أكثر من حالة",
        "calc_btn": "🧮 احسب الاحتياجات ←",
        "calc_title": "احسب الاحتياجات الغذائية حسب الحالة المرضية",
        "gender": "الجنس", "male": "ذكر", "female": "أنثى",
        "pregnancy_trim": "ثلث الحمل (إن حاملاً)",
        "not_applicable": "لا ينطبق", "first": "الأول", "second": "الثاني", "third": "الثالث",
        "conditions_label": "🏥 الحالات المرضية",
        "results_title": "📊 نتائج الحسابات",
        "macros_detail": "📐 الحسابات التفصيلية",
        "bmr_lbl": "BMR (معدل الأيض الأساسي)",
        "tdee_lbl": "TDEE (السعرات مع النشاط)",
        "target_cal": "السعرات المستهدفة",
        "fiber_rec": "الألياف الموصى بها",
        "sodium_max": "الصوديوم الأقصى",
        "fluid_lbl": "السوائل",
        "condition_notes": "📌 تعديلات الحالات المرضية",
        "micro_important": "💊 مغذيات دقيقة مهمة",
        "meal_dist": "🍽️ توزيع الوجبات المقترح",
        "meals_per_day": "وجبات يومياً",
        "cal_each": "kcal لكل وجبة",
        "meal_num": "الوجبة",
        "ref_detail": "📋 المرجع التفصيلي",
        "search_ref": "🔎 بحث في المرجع",
        "search_placeholder": "مثال: حديد، بوتاسيوم",
        "select_case": "اختر حالة",
        "treat_goals": "🎯 أهداف العلاج الغذائي",
        "quant_rec": "⚖️ التوصيات الكمية",
        "critical_micro": "💊 مغذيات دقيقة حرجة",
        "clinical_points": "🔑 نقاط سريرية رئيسية",
        "recommended": "✅ أطعمة مُشجَّعة",
        "limited": "⛔ أطعمة تُقلَّل",
        "weight_gain": "⚖️ الزيادة الوزنية حسب BMI",
        "source": "📚 المصدر",
        "gram": "جم", "kcal": "kcal", "day": "يوم",
        "lang_btn": "English",
    },
    "en": {
        "app_name": "NutraX",
        "tagline": "Your Smart Clinical Nutrition Assistant",
        "login": "Sign In", "register": "New Account",
        "email": "Email Address", "password": "Password",
        "name": "Full Name", "birth_year": "Birth Year",
        "country": "Country", "enter": "Sign In →", "create": "Create Account →",
        "remember": "Remember me on this device",
        "wrong_creds": "Incorrect email or password",
        "email_used": "Email already in use",
        "registered": "Account created! Sign in now.",
        "dashboard": "Dashboard", "settings": "Settings",
        "analyzer": "Food Analyzer", "planner": "Meal Planner",
        "suggester": "Meal Suggester", "saved": "My Plans",
        "history": "Weight Log", "clinical": "Clinical Reference",
        "logout": "Sign Out",
        "complete_settings": "Complete your profile to calculate daily targets",
        "go_settings": "Go to Settings",
        "your_goal": "Your Goal", "tdee": "TDEE", "daily_target": "Daily Target",
        "calories": "Calories", "protein": "Protein",
        "carbs": "Carbs", "fat": "Fat",
        "bmi": "BMI", "last_weight": "Last Weight", "plans": "Plans",
        "quick_access": "Quick Access",
        "height": "Height (cm)", "weight_kg": "Weight (kg)",
        "age": "Age (years)", "your_goal_lbl": "Your Goal",
        "activity": "Activity Level", "save_calc": "Save & Calculate Targets",
        "saved_ok": "Saved!",
        "fat_loss": "🔥 Fat Loss", "muscle_gain": "💪 Muscle Gain", "maintain": "⚖️ Maintain Weight",
        "sedentary": "Sedentary", "light": "Light (1-3 days)",
        "moderate": "Moderate (3-5 days)", "active": "Active (6-7 days)", "athlete": "Pro Athlete",
        "filter_cat": "Category", "all": "All", "search": "Search food...",
        "per_100g": "Per 100 grams",
        "results": "results from", "items": "items",
        "no_results": "No results found. Try a different term.",
        "show_first30": "Showing first 30 — narrow your search for more",
        "days": "Number of Days", "breakfast": "🌅 Breakfast", "lunch": "☀️ Lunch",
        "dinner": "🌙 Dinner", "snack": "🍎 Snack", "choose": "Choose",
        "summary": "Plan Summary", "gap": "Gap", "perfect": "Perfect! Balanced plan 🎯",
        "over_cal": "Over — reduce portions",
        "under_cal": "Under — add a meal",
        "plan_name": "Plan Name", "plan_type": "Type",
        "save_plan": "Save Plan", "saved_plan_ok": "Plan saved!",
        "personal": "Personal", "for_client": "For Client", "public": "Public",
        "no_plans": "No saved plans yet.",
        "shopping": "Shopping List", "delete": "Delete",
        "confirm_delete": "Confirm delete?", "yes": "✅ Yes", "cancel": "❌ Cancel",
        "log_weight": "Today's Weight (kg)", "log_btn": "Log",
        "min_weight": "📉 Min", "max_weight": "📈 Max", "last_weight2": "📊 Last",
        "no_weight": "Log your weight today!",
        "what_ate": "Enter what you ate today — we'll suggest remaining meals.",
        "ate": "✅ Eaten", "remaining": "🎯 Remaining",
        "suggest_btn": "💡 Suggest →", "reached_goal": "🎉 You reached your daily goal!",
        "suggested_meals": "🍽️ Suggested Meals",
        "ideal_weight": "Ideal Weight", "filter": "Filter",
        "select_condition": "Select condition(s)",
        "multi_condition": "Multiple conditions supported",
        "calc_btn": "🧮 Calculate Needs →",
        "calc_title": "Calculate Nutrition Targets by Clinical Condition",
        "gender": "Gender", "male": "Male", "female": "Female",
        "pregnancy_trim": "Pregnancy Trimester",
        "not_applicable": "N/A", "first": "1st", "second": "2nd", "third": "3rd",
        "conditions_label": "🏥 Clinical Conditions",
        "results_title": "📊 Calculated Results",
        "macros_detail": "📐 Detailed Breakdown",
        "bmr_lbl": "BMR (Basal Metabolic Rate)",
        "tdee_lbl": "TDEE (with Activity)",
        "target_cal": "Target Calories",
        "fiber_rec": "Recommended Fiber",
        "sodium_max": "Maximum Sodium",
        "fluid_lbl": "Fluids",
        "condition_notes": "📌 Condition-Specific Adjustments",
        "micro_important": "💊 Key Micronutrients",
        "meal_dist": "🍽️ Suggested Meal Distribution",
        "meals_per_day": "meals per day",
        "cal_each": "kcal each",
        "meal_num": "Meal",
        "ref_detail": "📋 Detailed Reference",
        "search_ref": "🔎 Search Reference",
        "search_placeholder": "e.g. iron, potassium",
        "select_case": "Select condition",
        "treat_goals": "🎯 Treatment Goals",
        "quant_rec": "⚖️ Quantitative Recommendations",
        "critical_micro": "💊 Critical Micronutrients",
        "clinical_points": "🔑 Key Clinical Points",
        "recommended": "✅ Recommended Foods",
        "limited": "⛔ Foods to Limit",
        "weight_gain": "⚖️ Weight Gain Guide (BMI)",
        "source": "📚 Source",
        "gram": "g", "kcal": "kcal", "day": "day",
        "lang_btn": "عربي",
    }
}

def T(key):
    lang = st.session_state.get("lang", "ar")
    return LANG[lang].get(key, key)


# ══════════════════════════════════════════
# CSS — Clean Light Theme + High Contrast
# ══════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;900&display=swap');

*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"]{font-family:'Cairo',sans-serif!important}

/* ─── Background ─── */
.stApp{
  background:#f4f6fa;
  min-height:100vh;
}

/* ─── Sidebar ─── */
[data-testid="stSidebar"]{
  background:#ffffff!important;
  border-left:1px solid #e2e8f0!important;
  border-right:none!important;
}
[data-testid="stSidebar"] .stButton>button{
  width:100%!important;
  background:#f8fafc!important;
  color:#1e293b!important;
  border:1px solid #e2e8f0!important;
  border-radius:10px!important;
  padding:12px 16px!important;
  margin-bottom:6px!important;
  font-family:'Cairo',sans-serif!important;
  font-size:14px!important;
  font-weight:600!important;
  transition:all .2s!important;
  text-align:right!important;
  direction:rtl!important;
}
[data-testid="stSidebar"] .stButton>button:hover{
  background:#eff6ff!important;
  border-color:#93c5fd!important;
  color:#1d4ed8!important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div{
  color:#1e293b!important;
  direction:rtl!important;
}

/* ─── Main content ─── */
.block-container{
  background:#f4f6fa!important;
  padding-top:1.5rem!important;
}

/* ─── Cards ─── */
.card{
  background:#ffffff;
  border:1.5px solid #d0daf0;
  border-radius:18px;padding:20px 18px;
  box-shadow:0 2px 12px rgba(0,0,0,0.06);
  transition:transform .2s,box-shadow .2s;
  position:relative;overflow:hidden;
}
.card::before{
  content:'';position:absolute;
  top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,#2563eb,#06b6d4);
}
.card:hover{
  transform:translateY(-3px);
  box-shadow:0 6px 24px rgba(37,99,235,0.12);
}
.card .c-label{
  color:#5a7096;font-size:11px;
  font-weight:700;letter-spacing:1px;
  text-transform:uppercase;margin-bottom:8px;
}
.card .c-value{
  color:#0f172a;font-size:28px;
  font-weight:900;line-height:1;
}
.card .c-unit{color:#94a3b8;font-size:12px;margin-top:5px}
.card .c-icon{font-size:24px;margin-bottom:8px}

/* ─── Section Title ─── */
.sec-title{
  font-size:20px;font-weight:800;
  color:#0f172a;padding-bottom:12px;
  border-bottom:2px solid #e2e8f0;
  margin-bottom:22px;
}
.sec-title .accent{color:#2563eb}

/* ─── Food Card ─── */
.food-card{
  background:#ffffff;
  border:1.5px solid #e2e8f0;
  border-radius:14px;padding:15px 17px;
  margin-bottom:10px;
  border-right:4px solid #2563eb;
  box-shadow:0 1px 6px rgba(0,0,0,0.04);
  transition:all .2s;
}
.food-card:hover{
  border-right-color:#06b6d4;
  box-shadow:0 3px 14px rgba(37,99,235,0.1);
}
.food-card .fc-name{
  color:#0f172a;font-size:15px;
  font-weight:700;margin-bottom:8px;
}
.food-card .fc-note{
  background:#eff6ff;
  border-right:3px solid #3b82f6;
  border-radius:8px;padding:8px 12px;
  color:#1e40af;font-size:13px;
  margin-top:8px;line-height:1.6;
}
.food-card .fc-tip{
  background:#fffbeb;
  border-right:3px solid #f59e0b;
  border-radius:8px;padding:8px 12px;
  color:#92400e;font-size:13px;
  margin-top:6px;line-height:1.6;
}

/* ─── Pills ─── */
.pills{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.pill{padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700}
.pill-cal{background:#dbeafe;color:#1e40af;border:1px solid #93c5fd}
.pill-p{background:#dcfce7;color:#166534;border:1px solid #86efac}
.pill-c{background:#fef3c7;color:#92400e;border:1px solid #fcd34d}
.pill-f{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5}

/* ─── Progress ─── */
.prog-wrap{background:#e2e8f0;border-radius:20px;height:8px;overflow:hidden;margin:4px 0 12px}
.prog-fill{height:8px;border-radius:20px;transition:width .6s}
.prog-cal{background:linear-gradient(90deg,#2563eb,#06b6d4)}
.prog-p{background:linear-gradient(90deg,#16a34a,#22c55e)}
.prog-c{background:linear-gradient(90deg,#d97706,#fbbf24)}
.prog-f{background:linear-gradient(90deg,#dc2626,#f87171)}

/* ─── Alerts ─── */
.alert-warn{background:#fffbeb;border:1.5px solid #fcd34d;border-radius:12px;padding:14px 18px;color:#78350f;margin-bottom:14px;font-size:14px;line-height:1.6;font-weight:500}
.alert-info{background:#eff6ff;border:1.5px solid #93c5fd;border-radius:12px;padding:12px 16px;color:#1e3a8a;margin-bottom:12px;font-size:14px;line-height:1.6;font-weight:500}
.alert-success{background:#f0fdf4;border:1.5px solid #86efac;border-radius:12px;padding:12px 16px;color:#14532d;margin-bottom:12px;font-size:14px;line-height:1.6;font-weight:500}

/* ─── BMI badges ─── */
.bmi-badge{display:inline-block;padding:5px 14px;border-radius:30px;font-size:13px;font-weight:700;margin-top:5px}
.bmi-under{background:#dbeafe;color:#1e40af;border:1px solid #93c5fd}
.bmi-normal{background:#dcfce7;color:#166534;border:1px solid #86efac}
.bmi-over{background:#fef3c7;color:#92400e;border:1px solid #fcd34d}
.bmi-obese{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5}

/* ─── ALL TEXT — HIGH CONTRAST ─── */
h1,h2,h3,h4,h5,h6{color:#0f172a!important;font-family:'Cairo',sans-serif!important}
p,li,span{color:#1e293b!important}
strong{color:#0f172a!important}
.stMarkdown p{color:#1e293b!important;font-size:14px!important;line-height:1.7!important}
.stMarkdown li{color:#1e293b!important;font-size:14px!important}
.stMarkdown strong{color:#0f172a!important}
label,
.stSelectbox label,
.stNumberInput label,
.stTextInput label{
  color:#374151!important;
  font-weight:700!important;
  font-size:13.5px!important;
}
[data-testid="stCaptionContainer"]{color:#64748b!important;font-size:12px!important}
.stCheckbox label p{color:#374151!important;font-size:13px!important}

/* ─── Inputs ─── */
input,textarea{
  background:#ffffff!important;
  color:#0f172a!important;
  border:1.5px solid #cbd5e1!important;
  border-radius:10px!important;
  font-size:15px!important;
  font-family:'Cairo',sans-serif!important;
}
input::placeholder,textarea::placeholder{color:#94a3b8!important;opacity:1!important}
input:focus{border-color:#2563eb!important;box-shadow:0 0 0 3px rgba(37,99,235,0.1)!important}
input:-webkit-autofill{
  -webkit-text-fill-color:#0f172a!important;
  -webkit-box-shadow:0 0 0px 1000px #fff inset!important;
}
.stSelectbox>div>div,[data-baseweb="select"]>div{
  background:#ffffff!important;
  color:#0f172a!important;
  border:1.5px solid #cbd5e1!important;
  border-radius:10px!important;
}
[data-baseweb="select"] span{color:#0f172a!important;font-size:14px!important;font-weight:500!important}
[data-baseweb="menu"]{background:#ffffff!important;border:1px solid #e2e8f0!important;box-shadow:0 4px 20px rgba(0,0,0,0.1)!important}
[data-baseweb="option"]{color:#0f172a!important;background:#ffffff!important;font-size:14px!important}
[data-baseweb="option"]:hover{background:#eff6ff!important}

/* ─── Buttons ─── */
.stButton>button{
  background:linear-gradient(135deg,#2563eb,#1d4ed8);
  color:#ffffff!important;
  border:none!important;
  border-radius:10px;
  font-family:'Cairo',sans-serif;
  font-weight:700;font-size:14px;
  padding:10px 22px;
  transition:all .2s;
  letter-spacing:0.3px;
}
.stButton>button:hover{
  background:linear-gradient(135deg,#1d4ed8,#1e40af);
  transform:translateY(-2px);
  box-shadow:0 4px 16px rgba(37,99,235,0.3);
}

/* ─── Tabs ─── */
.stTabs [data-baseweb="tab-list"]{background:#e2e8f0;border-radius:12px;padding:4px;gap:4px}
.stTabs [data-baseweb="tab"]{color:#475569;border-radius:8px;font-family:'Cairo',sans-serif;font-weight:600;font-size:14px}
.stTabs [aria-selected="true"]{background:#ffffff!important;color:#2563eb!important;box-shadow:0 1px 6px rgba(0,0,0,0.1)!important}

/* ─── Expander ─── */
.streamlit-expanderHeader{background:#ffffff!important;border-radius:12px!important;color:#0f172a!important;font-weight:700!important;font-size:14px!important;border:1.5px solid #e2e8f0!important}
.streamlit-expanderContent{background:#fafafa!important;border:1.5px solid #e2e8f0!important;border-top:none!important;border-radius:0 0 12px 12px!important}

/* ─── Metric ─── */
[data-testid="metric-container"]{background:#ffffff;border:1.5px solid #e2e8f0;border-radius:14px;padding:14px;box-shadow:0 1px 6px rgba(0,0,0,0.04)}
[data-testid="metric-container"] label{color:#5a7096!important;font-weight:700!important;font-size:12px!important}
[data-testid="stMetricValue"]{color:#0f172a!important;font-weight:900!important}

/* ─── Streamlit alerts ─── */
.stSuccess{background:#f0fdf4!important;color:#14532d!important;border-radius:12px!important;border:1.5px solid #86efac!important;font-weight:500!important}
.stError{background:#fef2f2!important;color:#7f1d1d!important;border-radius:12px!important;border:1.5px solid #fca5a5!important;font-weight:500!important}
.stWarning{background:#fffbeb!important;color:#78350f!important;border-radius:12px!important;border:1.5px solid #fcd34d!important;font-weight:500!important}
.stInfo{background:#eff6ff!important;color:#1e3a8a!important;border-radius:12px!important;border:1.5px solid #93c5fd!important;font-weight:500!important}

/* ─── Sug box ─── */
.sug-box{background:#ffffff;border:1.5px solid #e2e8f0;border-radius:14px;padding:15px 17px;margin-bottom:10px;box-shadow:0 1px 6px rgba(0,0,0,0.04);transition:all .2s}
.sug-box:hover{border-color:#93c5fd;box-shadow:0 3px 14px rgba(37,99,235,0.1)}
.sug-box h4{color:#0f172a;margin:0 0 8px;font-size:15px;font-weight:700}

/* ─── Clinical rows ─── */
.clin-row{background:#eff6ff;border-right:3px solid #3b82f6;border-radius:8px;padding:8px 12px;margin-bottom:7px}
.clin-row .cr-label{color:#1e40af;font-size:12px;font-weight:700;letter-spacing:0.5px}
.clin-row .cr-val{color:#0f172a;font-size:13px;font-weight:500}
.clin-row-warn{border-right-color:#f59e0b;background:#fffbeb}
.clin-row-warn .cr-label{color:#92400e}
.clin-row-green{border-right-color:#16a34a;background:#f0fdf4}
.clin-row-green .cr-label{color:#14532d}
.clin-row-red{border-right-color:#dc2626;background:#fef2f2}
.clin-row-red .cr-label{color:#7f1d1d}

/* ─── Calc box ─── */
.calc-box{background:#f8faff;border:1.5px solid #dbeafe;border-radius:16px;padding:20px 22px;margin:16px 0}
.calc-box h4{color:#1e3a8a;font-size:15px;font-weight:800;margin:0 0 14px}

/* ─── Divider ─── */
hr{border-color:#e2e8f0!important;margin:20px 0!important}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:#f1f5f9}
::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:10px}
::-webkit-scrollbar-thumb:hover{background:#2563eb}

/* ─── Login ─── */
.login-wrap{max-width:440px;margin:0 auto;padding:30px 20px 20px}
.login-logo{text-align:center;margin-bottom:28px}
.login-logo .logo-icon{font-size:52px}
.login-logo h1{font-size:40px;font-weight:900;background:linear-gradient(90deg,#2563eb,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:8px 0 4px}
.login-logo p{color:#64748b;font-size:15px;margin:0;font-weight:500}

/* ─── Mobile ─── */
@media(max-width:768px){
  section[data-testid="stSidebar"]{display:none!important}
  .block-container{padding:0.6rem 0.5rem 5rem!important;max-width:100%!important;background:#f4f6fa!important}
  .card{padding:14px 12px!important;margin-bottom:8px!important}
  .card .c-value{font-size:20px!important}
  .card .c-label{font-size:10px!important}
  .sec-title{font-size:16px!important;margin-bottom:14px!important}
  .food-card{padding:12px 13px!important}
  .stButton>button{padding:10px 12px!important;font-size:13px!important;width:100%!important}
  h1{font-size:22px!important}h2{font-size:18px!important}h3{font-size:15px!important}
  p,.stMarkdown p{font-size:13px!important}
  input,textarea{font-size:16px!important}
  label,.stSelectbox label,.stNumberInput label,.stTextInput label{font-size:12.5px!important}
  .pills{gap:4px!important}
  .pill{font-size:11px!important;padding:2px 7px!important}
  .alert-warn,.alert-info,.alert-success{padding:10px 13px!important;font-size:13px!important}
  .login-logo h1{font-size:32px!important}
  .login-wrap{padding:20px 14px!important}
}
@media(max-width:480px){
  .card .c-value{font-size:17px!important}
  .block-container{padding:0.4rem 0.4rem 5rem!important}
}

/* ─── Mobile Bottom Nav ─── */
.bottom-nav{display:none}
@media(max-width:768px){
  .bottom-nav{
    display:flex;position:fixed;bottom:0;left:0;right:0;
    background:#ffffff;border-top:2px solid #e2e8f0;
    padding:6px 0 10px;justify-content:space-around;
    align-items:center;z-index:9999;
    box-shadow:0 -2px 16px rgba(0,0,0,0.08);
  }
  .bn-item{
    display:flex;flex-direction:column;align-items:center;
    color:#94a3b8;font-size:10px;font-family:'Cairo',sans-serif;
    font-weight:600;cursor:pointer;min-width:50px;
  }
  .bn-item .bn-icon{font-size:20px;margin-bottom:2px}
  .bn-item.active{color:#2563eb}
  .block-container{padding-bottom:70px!important}
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════
DB_FILE = "nutrax_v11.db"
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
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT,
        name TEXT, height REAL, weight REAL, birth_year INTEGER,
        country TEXT, goal TEXT, is_admin INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS saved_plans (
        id INTEGER PRIMARY KEY, user_id INTEGER, plan_name TEXT,
        plan_data TEXT, created_at TEXT, type TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS tracking (
        id INTEGER PRIMARY KEY, user_id INTEGER, weight REAL, date TEXT)""")
    conn.commit()

init_db()
def hp(p): return hashlib.sha256(p.encode()).hexdigest()
c.execute("SELECT * FROM users WHERE is_admin=1")
if not c.fetchone():
    c.execute("INSERT INTO users (email,password,name,is_admin) VALUES (?,?,?,1)",
              ("admin@nutrax.com", hp("123456"), "Admin"))
    conn.commit()

LOCAL_DB = {
    # ── Poultry ──
    "chicken_breast":    {"name":"صدر دجاج","cal":165,"p":31,"c":0,"f":3.6,"cat":"🍗 دواجن",
        "note":"مصدر ممتاز للبروتين الكامل، قليل الدهون والكالوري. مثالي لبناء العضل وخسارة الدهون.",
        "tip":"💡 أفضل طريقة طهي: شوي أو بخار. تجنب القلي للحفاظ على قيمته الغذائية."},
    "chicken_thigh":     {"name":"فخذ دجاج","cal":209,"p":26,"c":0,"f":10,"cat":"🍗 دواجن",
        "note":"أعلى في الدهون الصحية من الصدر، مما يمنحه نكهة أغنى ويجعله أكثر إشباعاً.",
        "tip":"💡 مناسب لوجبات التحمل والرياضيين الذين يحتاجون كالوري أعلى."},
    "chicken_liver":     {"name":"كبدة دجاج","cal":119,"p":17,"c":0.7,"f":4.8,"cat":"🍗 دواجن",
        "note":"غنية جداً بالحديد والفيتامينات B12 وA. من أكثر الأطعمة كثافةً بالمغذيات الدقيقة.",
        "tip":"💡 يُنصح بتناولها مرة أو مرتين أسبوعياً كحد أقصى لتجنب الزيادة في فيتامين A."},
    "turkey_breast":     {"name":"صدر ديك رومي","cal":135,"p":30,"c":0,"f":1,"cat":"🍗 دواجن",
        "note":"من أعلى مصادر البروتين وأقلها في الدهون. مثالي لأهداف خسارة الدهون.",
        "tip":"💡 غني بالتريبتوفان الذي يساعد على النوم الجيد وتحسين المزاج."},
    "duck_breast":       {"name":"صدر بط","cal":201,"p":23,"c":0,"f":12,"cat":"🍗 دواجن",
        "note":"يحتوي على دهون صحية أعلى نسبياً، وغني بالحديد وفيتامين B.",
        "tip":"💡 مناسب كمصدر بروتين متنوع. قلل الجلد لتقليل الدهون المشبعة."},
    # ── Red Meat ──
    "beef_steak":        {"name":"ستيك لحم بقري","cal":271,"p":25,"c":0,"f":19,"cat":"🥩 لحوم حمراء",
        "note":"مصدر ممتاز للزنك والحديد الهيمي وB12. يدعم بناء العضل بشكل قوي.",
        "tip":"💡 اختر قطع lean مثل sirloin. الشوي أفضل من القلي لتقليل الدهون."},
    "ground_beef_lean":  {"name":"لحم مفروم قليل الدهن","cal":218,"p":27,"c":0,"f":12,"cat":"🥩 لحوم حمراء",
        "note":"متوازن بين البروتين والدهون. مرن في الاستخدام لوجبات متنوعة.",
        "tip":"💡 اختر نسبة دهون 10-15% للحصول على توازن جيد بين الطعم والقيمة الغذائية."},
    "lamb_leg":          {"name":"لحم ضأن (ساق)","cal":258,"p":26,"c":0,"f":17,"cat":"🥩 لحوم حمراء",
        "note":"غني بالزنك والحديد والكارنيتين. له مكانة مهمة في الثقافة الغذائية المصرية.",
        "tip":"💡 مصدر ممتاز للكارنيتين الذي يساعد على استهلاك الدهون كطاقة."},
    "veal":              {"name":"لحم عجل","cal":175,"p":29,"c":0,"f":6,"cat":"🥩 لحوم حمراء",
        "note":"أقل دهوناً من اللحم البقري الكامل، مع بروتين عالٍ وطعم لطيف.",
        "tip":"💡 خيار ممتاز لمن يريد لحماً أحمر بسعرات أقل."},
    "beef_liver":        {"name":"كبدة بقري","cal":135,"p":20,"c":4,"f":3.6,"cat":"🥩 لحوم حمراء",
        "note":"أغنى مصدر طبيعي للحديد وB12 وA وحمض الفوليك. استثنائي غذائياً.",
        "tip":"💡 وجبة واحدة أسبوعياً كافية لتلبية احتياجات الحديد بالكامل تقريباً."},
    # ── Fish ──
    "salmon":            {"name":"سلمون","cal":208,"p":20,"c":0,"f":13,"cat":"🐟 أسماك",
        "note":"ملك الأسماك غذائياً — غني بأوميغا 3 EPA/DHA. يقلل الالتهابات ويدعم القلب والمخ.",
        "tip":"💡 تناوله مرتين أسبوعياً. الشوي يحافظ على أوميغا 3 أفضل من القلي."},
    "tuna_fresh":        {"name":"تونة طازجة","cal":144,"p":30,"c":0,"f":2.5,"cat":"🐟 أسماك",
        "note":"بروتين عالٍ جداً مع دهون منخفضة. من أفضل الأسماك لبناء العضل.",
        "tip":"💡 نسبة البروتين إلى الكالوري فيها من أعلى النسب بين الأطعمة الحيوانية."},
    "tuna_canned":       {"name":"تونة معلبة (ماء)","cal":116,"p":26,"c":0,"f":1,"cat":"🐟 أسماك",
        "note":"اقتصادية ومريحة. خيار عملي لوجبة سريعة غنية بالبروتين.",
        "tip":"💡 فضّل المعلبة في ماء. قلل الاستهلاك لأكثر من 3-4 مرات أسبوعياً بسبب الزئبق."},
    "sardine_canned":    {"name":"سردين معلب","cal":208,"p":25,"c":0,"f":11,"cat":"🐟 أسماك",
        "note":"غني جداً بالكالسيوم (مع العظام) وأوميغا 3. من أرخص الأسماك المغذية.",
        "tip":"💡 السردين المعلب مع العظام يعطيك كالسيوم يقارب كوب الحليب."},
    "mackerel":          {"name":"سمك مكريل (سكمبري)","cal":205,"p":19,"c":0,"f":14,"cat":"🐟 أسماك",
        "note":"من أعلى الأسماك في أوميغا 3. يقلل الكوليسترول الضار ويرفع الجيد.",
        "tip":"💡 شائع ومتوفر في مصر والخليج بسعر معقول مقارنة بالسلمون."},
    "sea_bass":          {"name":"قاروس بحري","cal":97,"p":18,"c":0,"f":2,"cat":"🐟 أسماك",
        "note":"سمك أبيض خفيف، قليل الدهون ومناسب لأنظمة إنقاص الوزن.",
        "tip":"💡 مصدر جيد للسيلينيوم الذي يدعم الغدة الدرقية ومناعة الجسم."},
    "shrimp":            {"name":"جمبري","cal":99,"p":24,"c":0.2,"f":0.3,"cat":"🐟 أسماك",
        "note":"بروتين عالٍ جداً مع كالوري منخفض جداً. مثالي لأهداف التنشيف.",
        "tip":"💡 غني بالأيودين الضروري لوظيفة الغدة الدرقية. اسلقه أو اشوه."},
    "calamari":          {"name":"كاليماري (حبار)","cal":92,"p":16,"c":3,"f":1.4,"cat":"🐟 أسماك",
        "note":"قليل الدهون وغني بالبروتين والمعادن مثل النحاس والسيلينيوم.",
        "tip":"💡 المشوي أو المسلوق صحي جداً. القلي يرفع سعراته بشكل كبير."},
    "white_fish":        {"name":"سمك أبيض (بلطي/دنيس)","cal":96,"p":20,"c":0,"f":1.7,"cat":"🐟 أسماك",
        "note":"سمك عملي وبسعر مناسب، منخفض الدهون وجيد للوجبات اليومية.",
        "tip":"💡 متاح في مصر. يمكن طهيه بطرق متعددة مع الخضار."},
    "crab":              {"name":"كابوريا","cal":97,"p":19,"c":0,"f":1.5,"cat":"🐟 أسماك",
        "note":"بروتين عالٍ مع كالوري منخفض. غني بالزنك والسيلينيوم والنحاس.",
        "tip":"💡 خيار ممتاز لمن يريد تنوع بروتيني مع دهون منخفضة."},
    # ── Eggs ──
    "eggs_whole":        {"name":"بيضة كاملة","cal":78,"p":6,"c":0.6,"f":5,"cat":"🥚 بيض",
        "note":"يُلقب بـ'معيار الذهب للبروتين'. يحتوي على جميع الأحماض الأمينية الأساسية.",
        "tip":"💡 الصفار يحتوي على كولين مهم لصحة الدماغ والكبد."},
    "egg_whites":        {"name":"بياض بيض","cal":17,"p":3.6,"c":0.2,"f":0.1,"cat":"🥚 بيض",
        "note":"بروتين نقي تقريباً. مثالي لرفع البروتين بأقل سعرات ممكنة.",
        "tip":"💡 4 بياضات = ~15جم بروتين بـ68 سعرة فقط. مثالي للتنشيف."},
    "quail_eggs":        {"name":"بيض سمان","cal":158,"p":13,"c":0.4,"f":11,"cat":"🥚 بيض",
        "note":"أعلى في الفيتامينات والمعادن من بيض الدجاج نسبةً للحجم.",
        "tip":"💡 5 بيضات سمان تعادل تقريباً بيضة دجاج واحدة في الحجم."},
    # ── Dairy ──
    "milk_whole":        {"name":"حليب كامل الدسم","cal":61,"p":3.2,"c":4.8,"f":3.3,"cat":"🥛 ألبان",
        "note":"مصدر متكامل للكالسيوم وفيتامين D والبروتين. ضروري لصحة العظام.",
        "tip":"💡 يحتوي على دهون مشبعة لكن الدراسات الحديثة تظهر أنه آمن للاستهلاك المعتدل."},
    "milk_skim":         {"name":"حليب خالي الدسم","cal":35,"p":3.4,"c":5,"f":0.1,"cat":"🥛 ألبان",
        "note":"نفس كالسيوم الحليب الكامل بكالوري أقل. مناسب لأهداف خسارة الوزن.",
        "tip":"💡 جيد للرياضيين بعد التمرين لمزج البروتين مع الكارب بشكل طبيعي."},
    "greek_yogurt":      {"name":"زبادي يوناني","cal":59,"p":10,"c":3.6,"f":0.4,"cat":"🥛 ألبان",
        "note":"ضعف بروتين الزبادي العادي تقريباً. يحتوي على بروبيوتيك لصحة الأمعاء.",
        "tip":"💡 اختر النوع غير المحلى وأضف الفاكهة الطازجة."},
    "labneh":            {"name":"لبنة","cal":165,"p":9,"c":4,"f":13,"cat":"🥛 ألبان",
        "note":"زبادي مصفى — أعلى في البروتين والدهون. شائع جداً في المطبخ العربي.",
        "tip":"💡 مزجها بالزيتون والزعتر وجبة فطور غنية ومغذية."},
    "cottage_cheese":    {"name":"جبن قريش","cal":98,"p":11,"c":3.4,"f":4.3,"cat":"🥛 ألبان",
        "note":"بروتين بطيء الهضم (كازيين). ممتاز قبل النوم للحفاظ على العضل.",
        "tip":"💡 يمكن تناوله حلو (مع العسل) أو مالح (مع الخيار والطماطم)."},
    "cheese_feta":       {"name":"جبن فيتا","cal":264,"p":14,"c":4,"f":21,"cat":"🥛 ألبان",
        "note":"غني بالكالسيوم والبروبيوتيك. مذاق مميز يضيف قيمة غذائية للسلطات.",
        "tip":"💡 مملح جداً — قلل كميته لمن يعاني من ضغط الدم المرتفع."},
    "cheese_mozzarella": {"name":"موزاريلا","cal":280,"p":28,"c":2.2,"f":17,"cat":"🥛 ألبان",
        "note":"بروتين عالٍ مع كالسيوم ممتاز. من أفضل أجبان البروتين.",
        "tip":"💡 الموزاريلا الطازجة أفضل من المجففة في القيمة الغذائية."},
    "whey_protein":      {"name":"واي بروتين (سادة)","cal":375,"p":80,"c":6,"f":4,"cat":"🥛 ألبان",
        "note":"أسرع بروتين امتصاصاً في الجسم. مثالي بعد التمرين مباشرة.",
        "tip":"💡 لا يعوض الغذاء الطبيعي لكنه مكمل عملي لإتمام هدف البروتين اليومي."},
    # ── Grains ──
    "rice_white":        {"name":"أرز أبيض","cal":130,"p":2.7,"c":28,"f":0.3,"cat":"🌾 حبوب",
        "note":"كارب سريع الهضم. مصدر طاقة سهل للجسم. منخفض الألياف.",
        "tip":"💡 أفضل وقت: بعد التمرين مباشرة لتجديد الجليكوجين العضلي."},
    "rice_brown":        {"name":"أرز بني","cal":111,"p":2.6,"c":23,"f":0.9,"cat":"🌾 حبوب",
        "note":"أعلى في الألياف والمغنيسيوم من الأرز الأبيض. هضم أبطأ وشبع أطول.",
        "tip":"💡 أفضل خيار للتحكم في سكر الدم ولأهداف إنقاص الوزن."},
    "oats":              {"name":"شوفان","cal":389,"p":16.9,"c":66,"f":6.9,"cat":"🌾 حبوب",
        "note":"الملك بين الحبوب — غني بالبيتا جلوكان الذي يخفض الكوليسترول ويُشعر بالشبع.",
        "tip":"💡 جاهزه ببياض البيض لوجبة بروتين + كارب مثالية."},
    "quinoa":            {"name":"كينوا","cal":120,"p":4.4,"c":21,"f":1.9,"cat":"🌾 حبوب",
        "note":"الوحيدة من الحبوب التي تحتوي على بروتين كامل (جميع الأحماض الأمينية).",
        "tip":"💡 خيار ممتاز للنباتيين كمصدر بروتين كامل."},
    "bulgur":            {"name":"برغل","cal":83,"p":3.1,"c":18,"f":0.2,"cat":"🌾 حبوب",
        "note":"قمح مسلوق ومجفف — محتفظ بقيمته الغذائية. من أعلى الحبوب في الألياف.",
        "tip":"💡 أسرع تحضيراً من الأرز ومغذٍ أكثر."},
    "pasta_whole":       {"name":"مكرونة أسمر","cal":124,"p":5.3,"c":26,"f":0.8,"cat":"🌾 حبوب",
        "note":"أعلى بالألياف وأبطأ هضماً من المكرونة البيضاء.",
        "tip":"💡 اسلقها al dente (نصف ناعمة) لمؤشر جلايسيمي أقل."},
    "pasta_white":       {"name":"مكرونة بيضاء","cal":131,"p":5,"c":25,"f":1.1,"cat":"🌾 حبوب",
        "note":"كارب سريع مفيد بعد التمرين لإعادة بناء الجليكوجين.",
        "tip":"💡 لا تنسَ إضافة بروتين وخضار للوجبة لتكتمل."},
    "bread_whole":       {"name":"خبز أسمر","cal":247,"p":13,"c":41,"f":3.4,"cat":"🌾 حبوب",
        "note":"أعلى بالألياف ومعادن من الخبز الأبيض. يُعطي شبعاً أطول.",
        "tip":"💡 اقرأ المكونات: 'whole wheat' يجب أن تكون أول مكوّن."},
    "pita_bread":        {"name":"عيش بلدي","cal":255,"p":9,"c":52,"f":1.2,"cat":"🌾 حبوب",
        "note":"أساس المطبخ المصري. الأسمر منه أفضل بكثير من الأبيض.",
        "tip":"💡 الشعير البلدي (الأسمر الكامل) يحتوي على ضعف الألياف من العيش الأبيض."},
    "sweet_potato":      {"name":"بطاطا حلوة","cal":86,"p":1.6,"c":20,"f":0.1,"cat":"🌾 حبوب",
        "note":"كارب صحي بامتياز — غني جداً بالبيتا كاروتين وألياف.",
        "tip":"💡 من أفضل الكارب للرياضيين. الشوي في الفرن أفضل من السلق."},
    "potato":            {"name":"بطاطس","cal":87,"p":1.9,"c":20,"f":0.1,"cat":"🌾 حبوب",
        "note":"مصدر جيد للبوتاسيوم أكثر من الموز! غني أيضاً بفيتامين C.",
        "tip":"💡 تجنب القلي. مسلوق أو مشوي يحافظ على قيمته ويقلل الكالوري."},
    # ── Legumes ──
    "lentils":           {"name":"عدس","cal":116,"p":9,"c":20,"f":0.4,"cat":"🫘 بقوليات",
        "note":"سوبر فود نباتي — بروتين + ألياف + حديد في مكان واحد. رخيص ومغذٍ جداً.",
        "tip":"💡 العدس + الأرز (كشري) = بروتين كامل نباتياً. تراث غذائي مصري عظيم!"},
    "chickpeas":         {"name":"حمص","cal":164,"p":8.9,"c":27,"f":2.6,"cat":"🫘 بقوليات",
        "note":"غني بالألياف والبروتين والمغنيسيوم. ينظم سكر الدم ويشبع لساعات.",
        "tip":"💡 نقعه طوال الليل يسهل الهضم ويقلل الغازات."},
    "fava_beans":        {"name":"فول مدمس","cal":110,"p":7.6,"c":20,"f":0.5,"cat":"🫘 بقوليات",
        "note":"الإفطار الوطني المصري بجدارة. بروتين + ألياف + حديد. اقتصادي وسهل.",
        "tip":"💡 أضف زيت زيتون وليمون وثوم لرفع قيمته الغذائية وامتصاص الحديد."},
    "kidney_beans":      {"name":"فاصوليا حمراء","cal":127,"p":8.7,"c":23,"f":0.5,"cat":"🫘 بقوليات",
        "note":"غنية بمضادات الأكسدة والألياف القابلة للذوبان. ممتازة لصحة القلب.",
        "tip":"💡 لا تأكل الفاصوليا الحمراء خاماً — تحتوي على مادة سامة تزول بالطهي الكامل."},
    "black_beans":       {"name":"فاصوليا سوداء","cal":132,"p":8.9,"c":24,"f":0.5,"cat":"🫘 بقوليات",
        "note":"من أعلى البقوليات في مضادات الأكسدة بسبب لونها الداكن.",
        "tip":"💡 قيمتها الغذائية عالية جداً وتُستخدم في الطبخ الآسيوي واللاتيني."},
    "edamame":           {"name":"إيداماميه","cal":122,"p":11,"c":10,"f":5,"cat":"🫘 بقوليات",
        "note":"فاصوليا الصويا الخضراء — من قلة الأطعمة النباتية ذات البروتين الكامل.",
        "tip":"💡 وجبة خفيفة شعبية يابانية. متوفرة مجمدة في معظم المتاجر."},
    "tofu":              {"name":"توفو","cal":76,"p":8,"c":1.9,"f":4.8,"cat":"🫘 بقوليات",
        "note":"جبن الصويا — بروتين كامل نباتي. يمتص نكهة التوابل بشكل رائع.",
        "tip":"💡 الصلب (firm tofu) أعلى بروتيناً. تجفيفه قبل الطهي يعطي قوام أفضل."},
    # ── Nuts & Fats ──
    "almonds":           {"name":"لوز","cal":579,"p":21,"c":22,"f":50,"cat":"🥜 مكسرات",
        "note":"ملك المكسرات — غني بالمغنيسيوم وفيتامين E والدهون الأحادية غير المشبعة.",
        "tip":"💡 حفنة صغيرة (28جم~23 حبة) كافية. لا تبالغ في الكمية بسبب الكالوري."},
    "walnuts":           {"name":"جوز","cal":654,"p":15,"c":14,"f":65,"cat":"🥜 مكسرات",
        "note":"المصدر النباتي الأغنى بأوميغا 3 (ALA). يحسن صحة الدماغ والقلب.",
        "tip":"💡 7 حبات جوز يومياً تُغطي احتياجات أوميغا 3 النباتية."},
    "cashews":           {"name":"كاجو","cal":553,"p":18,"c":30,"f":44,"cat":"🥜 مكسرات",
        "note":"أعلى في الكارب من باقي المكسرات. غني بالزنك والمغنيسيوم والنحاس.",
        "tip":"💡 النحاس في الكاجو يساعد على امتصاص الحديد وصحة المفاصل."},
    "pistachios":        {"name":"فستق حلبي","cal":562,"p":20,"c":28,"f":45,"cat":"🥜 مكسرات",
        "note":"من أعلى المكسرات في البروتين والبوتاسيوم ومضادات الأكسدة.",
        "tip":"💡 المقشر أفضل لأنك تأكل أبطأ وتستهلك كمية أقل."},
    "peanut_butter":     {"name":"زبدة فول سوداني","cal":588,"p":25,"c":20,"f":50,"cat":"🥜 مكسرات",
        "note":"كثيف غذائياً. بروتين + دهون صحية. يرفع الشبع بشكل ممتاز.",
        "tip":"💡 اختر النوع الطبيعي (مكون واحد: فول سوداني فقط)."},
    "chia_seeds":        {"name":"بذور الشيا","cal":486,"p":16.5,"c":42,"f":31,"cat":"🥜 مكسرات",
        "note":"تمتص 10 أضعاف وزنها من الماء! غنية بأوميغا 3 وألياف وكالسيوم.",
        "tip":"💡 نقعها في الحليب يعطيك بودينج مغذٍ جداً. أضفها لأي وجبة بسهولة."},
    "flax_seeds":        {"name":"بذور الكتان","cal":534,"p":18,"c":29,"f":42,"cat":"🥜 مكسرات",
        "note":"المصدر النباتي الأغنى بـ ALA (أوميغا 3). يدعم صحة الهرمونات والأمعاء.",
        "tip":"💡 اطحنها قبل الأكل لأن البذرة الكاملة تمر دون امتصاص."},
    "hemp_seeds":        {"name":"بذور القنب","cal":553,"p":31,"c":9,"f":48,"cat":"🥜 مكسرات",
        "note":"بروتين كامل نباتي نادر الوجود في البذور! نسبة أوميغا مثالية.",
        "tip":"💡 أعلى بذور في البروتين. أضفها للسلطة أو الزبادي بدون طهي."},
    "pumpkin_seeds":     {"name":"بذور اليقطين (ليبي)","cal":559,"p":30,"c":11,"f":49,"cat":"🥜 مكسرات",
        "note":"من أغنى المصادر النباتية بالزنك والمغنيسيوم.",
        "tip":"💡 المغنيسيوم فيها يساعد على الاسترخاء والنوم. وجبة خفيفة مسائية مثالية."},
    "sesame":            {"name":"سمسم","cal":573,"p":17,"c":23,"f":50,"cat":"🥜 مكسرات",
        "note":"غني بالكالسيوم والزنك والحديد. الطحينة المصنوعة منه من أغنى الأطعمة بالكالسيوم.",
        "tip":"💡 إضافته للخبز أو السلطة ترفع القيمة الغذائية بشكل ملحوظ."},
    "tahini":            {"name":"طحينة","cal":595,"p":17,"c":21,"f":53,"cat":"🥜 مكسرات",
        "note":"سمسم مطحون — يحتفظ بجميع قيمته الغذائية. غني بالكالسيوم والحديد.",
        "tip":"💡 مزجها مع الليمون والثوم وماء يعطي صوص لذيذ ومغذٍ جداً."},
    "olive_oil":         {"name":"زيت زيتون","cal":884,"p":0,"c":0,"f":100,"cat":"🥜 مكسرات",
        "note":"ملك الدهون الصحية. 73% من دهونه أحادية غير مشبعة. يقلل الالتهاب.",
        "tip":"💡 استخدم البكر الممتاز (Extra Virgin) للسلطات والطهي على حرارة منخفضة."},
    "avocado":           {"name":"أفوكادو","cal":160,"p":2,"c":9,"f":15,"cat":"🥜 مكسرات",
        "note":"الفاكهة الوحيدة الغنية بالدهون الصحية! مليء بالبوتاسيوم وحمض الفوليك.",
        "tip":"💡 نصفة يعطيك بوتاسيوم أكثر من الموزة الكاملة. ممتاز مع البيض صباحاً."},
    "coconut_oil":       {"name":"زيت جوز الهند","cal":862,"p":0,"c":0,"f":100,"cat":"🥜 مكسرات",
        "note":"غني بالدهون المتوسطة السلسلة (MCT) التي تُحوَّل مباشرة لطاقة.",
        "tip":"💡 مناسب للطهي على حرارة عالية. لا تبالغ — غني بالدهون المشبعة."},
    # ── Fruits ──
    "banana":            {"name":"موز","cal":89,"p":1.1,"c":23,"f":0.3,"cat":"🍎 فاكهة",
        "note":"أسرع طاقة طبيعية للرياضيين. غني بالبوتاسيوم الضروري لوظيفة العضلات.",
        "tip":"💡 قبل التمرين بـ30 دقيقة = طاقة مثالية. بعده = تجديد الجليكوجين."},
    "apple":             {"name":"تفاح","cal":52,"p":0.3,"c":14,"f":0.2,"cat":"🍎 فاكهة",
        "note":"مضادات الأكسدة والألياف (بيكتين) تدعم الهضم وصحة القلب.",
        "tip":"💡 كله مع قشره — فيه 2/3 مضادات الأكسدة والألياف."},
    "orange":            {"name":"برتقال","cal":47,"p":0.9,"c":12,"f":0.1,"cat":"🍎 فاكهة",
        "note":"واحدة تُغطي 100% من احتياج فيتامين C اليومي. يعزز المناعة.",
        "tip":"💡 كل البرتقالة كاملاً للحصول على الألياف بدل العصير."},
    "mango":             {"name":"مانجو","cal":60,"p":0.8,"c":15,"f":0.4,"cat":"🍎 فاكهة",
        "note":"غني جداً بالبيتا كاروتين وفيتامين C والإنزيمات الهاضمة.",
        "tip":"💡 الكمية المعقولة: كوب مقطع (165جم). سكره طبيعي لكنه مرتفع نسبياً."},
    "watermelon":        {"name":"بطيخ","cal":30,"p":0.6,"c":8,"f":0.2,"cat":"🍎 فاكهة",
        "note":"94% ماء! مرطب طبيعي ممتاز. يحتوي على اللايكوبين لصحة القلب.",
        "tip":"💡 مثالي في الصيف بعد التمرين لتعويض الماء والكهارل الطبيعية."},
    "strawberries":      {"name":"فراولة","cal":32,"p":0.7,"c":7.7,"f":0.3,"cat":"🍎 فاكهة",
        "note":"من أعلى الفاكهة بفيتامين C ومضادات الأكسدة مع كالوري منخفض.",
        "tip":"💡 كوب كامل (150جم) = 28 سعرة فقط مع 85mg فيتامين C. مثالي للتنشيف."},
    "blueberries":       {"name":"توت أزرق","cal":57,"p":0.7,"c":14,"f":0.3,"cat":"🍎 فاكهة",
        "note":"'سوبر فود' — أعلى نسبة مضادات أكسدة بين الفاكهة الشائعة.",
        "tip":"💡 مجمد أو طازج له نفس القيمة الغذائية. أضفه للزبادي أو الشوفان."},
    "dates":             {"name":"تمر","cal":277,"p":1.8,"c":75,"f":0.2,"cat":"🍎 فاكهة",
        "note":"طاقة فورية طبيعية. غني بالحديد والبوتاسيوم والمغنيسيوم.",
        "tip":"💡 3 تمرات قبل التمرين = طاقة ممتازة. أو اكسر صيامك بها."},
    "pomegranate":       {"name":"رمان","cal":83,"p":1.7,"c":19,"f":1.2,"cat":"🍎 فاكهة",
        "note":"من أقوى مضادات الأكسدة في الطبيعة. يخفض ضغط الدم ويحارب الالتهاب.",
        "tip":"💡 ثبت علمياً أنه يحسن أداء التمرين. عصيره الطازج رائع."},
    "kiwi":              {"name":"كيوي","cal":61,"p":1.1,"c":15,"f":0.5,"cat":"🍎 فاكهة",
        "note":"ضعف فيتامين C مقارنة بالبرتقال! يحسن النوم ويساعد على هضم البروتين.",
        "tip":"💡 كيويتان قبل النوم بساعة ثبت أنهما يحسنان جودة النوم."},
    # ── Vegetables ──
    "broccoli":          {"name":"بروكلي","cal":34,"p":2.8,"c":7,"f":0.4,"cat":"🥦 خضروات",
        "note":"سوبر فود خضروات — السلفورافان فيه مضاد سرطان قوي. غني بالكالسيوم.",
        "tip":"💡 الطهي بالبخار يحافظ على السلفورافان. تجنب السلق الزائد."},
    "spinach":           {"name":"سبانخ","cal":23,"p":2.9,"c":3.6,"f":0.4,"cat":"🥦 خضروات",
        "note":"مكثف غذائياً — حديد وكالسيوم وماغنيسيوم وفيتامين K في كمية صغيرة.",
        "tip":"💡 أضف عصير ليمون للمساعدة على امتصاص الحديد النباتي."},
    "carrots":           {"name":"جزر","cal":41,"p":0.9,"c":10,"f":0.2,"cat":"🥦 خضروات",
        "note":"مصدر استثنائي للبيتا كاروتين (فيتامين A). يصون بصرك ويقوي مناعتك.",
        "tip":"💡 الطهي مع دهون قليلة يزيد امتصاص البيتا كاروتين."},
    "cucumber":          {"name":"خيار","cal":16,"p":0.6,"c":4,"f":0.1,"cat":"🥦 خضروات",
        "note":"96% ماء — مرطب ممتاز. مفيد للجلد والترطيب. كالوري شبه معدوم.",
        "tip":"💡 وجبة خفيفة مثالية للتنشيف. مع لبنة أو حمص وجبة مشبعة."},
    "tomato":            {"name":"طماطم","cal":18,"p":0.9,"c":3.9,"f":0.2,"cat":"🥦 خضروات",
        "note":"غني باللايكوبين — مضاد أكسدة قوي يقلل خطر أمراض القلب.",
        "tip":"💡 الطهي يرفع محتوى اللايكوبين. صلصة الطماطم أكثر فائدة للايكوبين."},
    "sweet_pepper":      {"name":"فلفل ألوان","cal":31,"p":1,"c":6,"f":0.3,"cat":"🥦 خضروات",
        "note":"ثلاثة أضعاف فيتامين C مقارنة بالبرتقال! الأحمر منه الأعلى بمضادات الأكسدة.",
        "tip":"💡 أضفه نيئاً للسلطة. مثالي لرفع فيتامين C بدون سعرات إضافية."},
    "onion":             {"name":"بصل","cal":40,"p":1.1,"c":9,"f":0.1,"cat":"🥦 خضروات",
        "note":"غني بالكيرسيتين والكبريت. مضاد التهابات طبيعي ويدعم صحة القلب.",
        "tip":"💡 الأكثر إفادة عندما يُؤكل نيئاً. إضافته للسلطة يرفع مضادات الأكسدة."},
    "garlic":            {"name":"ثوم","cal":149,"p":6.4,"c":33,"f":0.5,"cat":"🥦 خضروات",
        "note":"مضاد طبيعي للبكتيريا. يخفض ضغط الدم والكوليسترول الضار.",
        "tip":"💡 اتركه 10 دقائق بعد تقطيعه قبل الطهي لتفعيل الأليسين المفيد."},
    "zucchini":          {"name":"كوسة","cal":17,"p":1.2,"c":3.1,"f":0.3,"cat":"🥦 خضروات",
        "note":"كالوري منخفض جداً مع مياه عالية وفيتامينات B. مرنة في الطهي.",
        "tip":"💡 يمكن استخدامها بديلاً للمكرونة (zoodles) لتقليل الكارب."},
    "mushroom":          {"name":"فطر","cal":22,"p":3.1,"c":3.3,"f":0.3,"cat":"🥦 خضروات",
        "note":"المصدر النباتي الوحيد لفيتامين D (عند تعريضه للشمس). بروتينه عالٍ نسبياً.",
        "tip":"💡 ضعه في الشمس لساعة قبل الطهي يرفع محتواه من فيتامين D!"},
    # ── Egyptian ──
    "falafel":           {"name":"فلافل","cal":333,"p":13,"c":32,"f":18,"cat":"🇪🇬 مصري",
        "note":"مصنوع من الفول أو الحمص. بروتين نباتي جيد لكن القلي يرفع الدهون.",
        "tip":"💡 الفلافل المخبوزة تقلل الكالوري بنسبة 40% مع نفس الطعم تقريباً."},
    "hummus":            {"name":"حمص بطحينة","cal":166,"p":7.9,"c":14,"f":9.6,"cat":"🇪🇬 مصري",
        "note":"دهون صحية + بروتين + ألياف. وجبة خفيفة مشبعة ومغذية.",
        "tip":"💡 مع الخبز الأسمر أو الخضار النيئة وجبة متكاملة ومشبعة."},
    "molokhia":          {"name":"ملوخية","cal":44,"p":4.8,"c":8,"f":0.6,"cat":"🇪🇬 مصري",
        "note":"سوبر فود مصري مجهول! أعلى من السبانخ بالحديد والكالسيوم وفيتامينات متعددة.",
        "tip":"💡 من أغنى الخضروات العربية. إضافة زيت زيتون وثوم وليمون يرفع امتصاص معادنها."},
    "bamia":             {"name":"بامية","cal":33,"p":1.9,"c":7.5,"f":0.2,"cat":"🇪🇬 مصري",
        "note":"غنية بالمخاط الطبيعي الذي يلطف الأمعاء. مصدر جيد لفيتامين K.",
        "tip":"💡 طهيها بسرعة يحافظ على الفيتامينات. تجنب الطهي الزائد."},
    "koshary_lentils":   {"name":"عدس كشري","cal":116,"p":9,"c":20,"f":0.4,"cat":"🇪🇬 مصري",
        "note":"قلب الكشري المصري. عدس + أرز + مكرونة = وجبة متوازنة نباتياً.",
        "tip":"💡 إضافة الخل والثوم تحسن هضمه ومذاقه."},
    # ── Beverages ──
    "green_tea":         {"name":"شاي أخضر","cal":1,"p":0,"c":0,"f":0,"cat":"☕ مشروبات",
        "note":"الكاتيكين من أقوى مضادات الأكسدة الطبيعية. يعزز حرق الدهون.",
        "tip":"💡 كوبان إلى 3 يومياً. لا تشربه فوراً بعد الأكل لتجنب التأثير على امتصاص الحديد."},
    "black_coffee":      {"name":"قهوة سادة","cal":2,"p":0.3,"c":0,"f":0,"cat":"☕ مشروبات",
        "note":"الكافيين يحسن الأداء الرياضي والتركيز. مضادات الأكسدة فيها أعلى بكثير من المتوقع.",
        "tip":"💡 قبل التمرين بـ45 دقيقة يرفع الأداء والقوة. لا تجاوز 3-4 أكواب يومياً."},
    "milk_protein":      {"name":"حليب بالكاكاو","cal":83,"p":3.4,"c":12,"f":2.4,"cat":"☕ مشروبات",
        "note":"بروتين + كارب بنسبة مثالية بعد التمرين. بديل طبيعي ورخيص.",
        "tip":"💡 الدراسات تظهر أنه بديل فعّال لمشروبات الريكفري التجارية."},
}

CATEGORY_TIPS = {
    "🍗 دواجن":       "الدواجن تحتوي على بروتين عالي الجودة وسهل الهضم. أفضل طريقة: شوي، بخار، أو فرن.",
    "🥩 لحوم حمراء":  "اللحوم الحمراء غنية بالحديد الهيمي الأسهل امتصاصاً. تناولها 2-3 مرات أسبوعياً كحد أقصى.",
    "🐟 أسماك":       "الأسماك من أفضل مصادر البروتين. الدهنية منها (سلمون، مكريل) غنية بأوميغا 3.",
    "🥚 بيض":         "البيض من أكمل الأطعمة غذائياً. يحتوي على جميع العناصر اللازمة لبناء الجسم.",
    "🥛 ألبان":       "الألبان مصدر أساسي للكالسيوم وفيتامين D لصحة العظام والعضلات.",
    "🌾 حبوب":        "الحبوب الكاملة أفضل بكثير من المكررة — ألياف أعلى ومؤشر جلايسيمي أفضل.",
    "🫘 بقوليات":     "البقوليات من أرخص وأفضل مصادر البروتين النباتي والألياف القابلة للذوبان.",
    "🥜 مكسرات":      "الدهون الصحية في المكسرات ضرورية للهرمونات وامتصاص الفيتامينات الذائبة بالدهون.",
    "🍎 فاكهة":       "الفاكهة مصدر طبيعي للفيتامينات ومضادات الأكسدة. أكلها كاملة أفضل من العصير.",
    "🥦 خضروات":      "الخضروات الملونة = تنوع في مضادات الأكسدة. كل الألوان معاً للأفضل.",
    "🇪🇬 مصري":      "المطبخ المصري التقليدي حكيم غذائياً — فول وعدس وملوخية وكشري أطعمة ممتازة!",
    "☕ مشروبات":     "الماء أولاً دائماً. المشروبات الطبيعية كالشاي الأخضر والقهوة السادة مفيدة باعتدال.",
}

# ══════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════
def calc_targets(weight, height, age, goal, act=1.55):
    bmr  = 10*weight + 6.25*height - 5*age + 5
    tdee = bmr * act
    if   goal=="fat_loss":    cal=tdee-400; pr,cr,fr=0.35,0.35,0.30
    elif goal=="muscle_gain": cal=tdee+400; pr,cr,fr=0.30,0.45,0.25
    else:                     cal=tdee;     pr,cr,fr=0.25,0.45,0.30
    return {"cal":int(cal),"p":int(cal*pr/4),"c":int(cal*cr/4),"f":int(cal*fr/9),"goal":goal,"tdee":int(tdee)}

def macros(key, grams):
    f=LOCAL_DB[key]; r=grams/100
    return {"cal":round(f["cal"]*r,1),"p":round(f["p"]*r,1),"c":round(f["c"]*r,1),"f":round(f["f"]*r,1)}

def bmi_info(w, h_cm):
    h=h_cm/100; bmi=w/(h*h)
    if bmi<18.5: return round(bmi,1),"bmi-under","نقص في الوزن"
    elif bmi<25: return round(bmi,1),"bmi-normal","وزن مثالي ✅"
    elif bmi<30: return round(bmi,1),"bmi-over","زيادة في الوزن"
    else:        return round(bmi,1),"bmi-obese","سمنة"

def prog(pct, css):
    p=min(max(pct,0),100)
    return f'<div class="prog-wrap"><div class="prog-fill {css}" style="width:{p}%"></div></div>'

def diff_badge(diff):
    if diff>80:    return f'<span style="color:#ef9a9a;font-weight:700">+{int(diff)} kcal زيادة ⬆️</span>'
    elif diff<-80: return f'<span style="color:#a5d6a7;font-weight:700">{int(diff)} kcal ناقص ⬇️</span>'
    else:          return f'<span style="color:#80d8ff;font-weight:700">مثالي ✅</span>'

def shopping(plan_data):
    out={}
    for day,meals in plan_data.items():
        for meal,foods in meals.items():
            for k,g in foods.items():
                if k in LOCAL_DB: out[k]=out.get(k,0)+g
    return out

def smart_suggest(rem_cal, rem_p, rem_c, rem_f):
    sug=[]
    for k,v in LOCAL_DB.items():
        if rem_cal<=0: break
        g=min(300,max(50,int(rem_cal/max(v["cal"]/100,.1))))
        m=macros(k,g)
        if m["cal"]>rem_cal*1.3 or m["cal"]<40: continue
        score=100-abs(m["cal"]-rem_cal*.4)
        if rem_p>20 and v["p"]>15: score+=40
        if rem_f<10 and v["f"]<5:  score+=20
        sug.append({"key":k,"name":v["name"],"cat":v["cat"],"grams":g,"macro":m,"score":score})
    sug.sort(key=lambda x:-x["score"])
    return sug[:5]


# ══════════════════════════════════════════
# CLINICAL REFERENCE DATA (from textbook)
CLINICAL_CONDITIONS = {
    "diabetes_t1": {
        "name":"السكري النوع الأول (Type 1)","icon":"🩸","chapter":"Chapter 26 — Diabetes Mellitus",
        "overview":"النوع الأول اضطراب مناعي ذاتي يؤدي لتوقف إنتاج الأنسولين كلياً. التحكم الدقيق في الكارب ضروري لتجنب التذبذبات في السكر.",
        "goals":["الحفاظ على سكر الدم في النطاق الطبيعي (70–130 صيام، <180 بعد الأكل)","تنسيق وجبات الكارب مع جرعة الأنسولين","الوقاية من نقص السكر (hypoglycemia)","الحفاظ على وزن صحي وضبط الدهون والضغط"],
        "macros":{"energy":"يحسب EER فردياً حسب الوزن والنشاط","carb":"45–60% | موزعة بثبات | لا تقل عن 130 جم/يوم","protein":"15–20% | 0.8–1.0 جم/كجم","fat":"< 30% | مشبعة < 7% | كوليسترول < 200 مجم/يوم","fiber":"21–38 جم/يوم (بقوليات، حبوب كاملة)","sodium":"< 2300 مجم/يوم"},
        "key_points":["🔑 عد الكارب (Carb Counting) هو الأساس — كل 15 جم = 1 وحدة","🔑 ثبات الكميات بين الوجبات أهم من نوع الكارب","🔑 السكر لا يُحظر كلياً لكن يُحسب ضمن حصة الكارب","🔑 تجنب الدهون المشبعة والمتحولة — خطر القلب مرتفع","🔑 الكحول يسبب نقص السكر — يؤخذ مع وجبة فقط","🔑 النشاط البدني يخفض السكر — قد تحتاج تعديل الأنسولين"],
        "foods_recommended":["حبوب كاملة (شوفان، أرز بني، برغل، كينوا)","بقوليات (عدس، حمص، فول) — ألياف عالية ومؤشر جلايسيمي منخفض","خضروات غير نشوية (بروكلي، سبانخ، خيار)","بروتين قليل الدهون (صدر دجاج، سمك، بياض بيض)","دهون صحية (أفوكادو، زيت زيتون، مكسرات)","فاكهة طازجة بكميات معتدلة (حصة = 15 جم كارب)"],
        "foods_limit":["عصائر ومشروبات محلاة","خبز أبيض ومعجنات مكررة","أرز أبيض بكميات كبيرة","دهون مشبعة (لحوم دهنية، زبدة، قشطة)","حلويات ومحليات مكررة"],
        "meal_timing":"3 وجبات رئيسية + 2-3 وجبات خفيفة | ثبات التوقيت مع الأنسولين أساسي",
        "monitoring":"HbA1c هدف < 7% | قياس سكر ذاتي 3+ مرات يومياً",
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.26, pp.810–836",
    },
    "diabetes_t2": {
        "name":"السكري النوع الثاني (Type 2)","icon":"🩸","chapter":"Chapter 26 — Diabetes Mellitus",
        "overview":"النوع الثاني مقاومة للأنسولين مع نقص تدريجي في إفرازه. يرتبط بالوزن الزائد. فقدان 5-10% من الوزن يُحسّن التحكم في السكر بشكل ملحوظ.",
        "goals":["خسارة 5–10% من الوزن إن كان هناك زيادة","ضبط سكر الدم والدهون والضغط","تأخير مضاعفات السكري","تقليل الحاجة للأدوية بتحسين نمط الحياة"],
        "macros":{"energy":"عجز 500-750 kcal/يوم للإنقاص | 1200-1500 نساء | 1500-1800 رجال","carb":"45–60% | تقليل الكارب المكرر | مؤشر جلايسيمي منخفض","protein":"15–20% | بروتين عالي الجودة قليل الدهون","fat":"دهون أحادية غير مشبعة (زيت زيتون، أفوكادو) هي الأفضل | مشبعة < 7%","fiber":"25–38 جم/يوم — يُبطئ امتصاص الجلوكوز","sodium":"< 2300 مجم/يوم (< 1500 مع ضغط الدم)"},
        "key_points":["🔑 خسارة الوزن أكثر فعالية من أي دواء في المراحل الأولى","🔑 الألياف القابلة للذوبان (شوفان، بقوليات) تُبطئ امتصاص السكر","🔑 توزيع الوجبات على 3 وجبات منتظمة — لا تجاهل الإفطار","🔑 تقليل الدهون المشبعة — خطر القلب مرتفع جداً","🔑 150 دقيقة نشاط هوائي/أسبوع يُحسّن حساسية الأنسولين","🔑 الإفطار مهم — تجاهله يرفع سكر الظهر والعشاء"],
        "foods_recommended":["شوفان وحبوب كاملة يومياً","بقوليات يومياً (عدس، حمص، فول)","خضروات غير نشوية بكميات كبيرة","بروتين نباتي وحيواني قليل الدهون","زيت زيتون وأفوكادو","أسماك دهنية مرتين/أسبوع"],
        "foods_limit":["أرز أبيض، خبز أبيض، معجنات مكررة","مشروبات محلاة وعصائر","لحوم دهنية وأطعمة مقلية","وجبات سريعة عالية الصوديوم","حلويات ومعجنات"],
        "meal_timing":"3 وجبات منتظمة | وجبة خفيفة مسائية إن لزم | لا تجاوز 6 ساعات بين الوجبات",
        "monitoring":"HbA1c هدف < 7% | قياس سكر ذاتي حسب توجيه الطبيب",
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.26, pp.818–836",
    },
    "pregnancy": {
        "name":"الحمل (Pregnancy)","icon":"🤰","chapter":"Chapter 14 — Life Cycle Nutrition: Pregnancy and Lactation",
        "overview":"التغذية خلال الحمل تؤثر على صحة الأم والطفل طويل الأمد. الاحتياجات ترتفع كثيراً خاصة للحديد وحمض الفوليك والكالسيوم وأوميغا 3.",
        "goals":["تلبية الاحتياجات الغذائية المتزايدة للأم والجنين","زيادة وزن مناسبة حسب BMI قبل الحمل","الوقاية من فقر الدم وعيوب الأنبوب العصبي وسكر الحمل","ضمان نمو سليم للجنين"],
        "macros":{"energy":"+340 kcal/يوم في الثلث الثاني | +452 kcal/يوم في الثالث | لا زيادة في الأول","carb":"175 جم/يوم كحد أدنى (لنمو دماغ الجنين)","protein":"+25 جم/يوم = ~71 جم/يوم إجمالاً","fat":"DHA 200–300 مجم/يوم على الأقل (سلمون، سردين، مكمل)","fiber":"28 جم/يوم — يقلل الإمساك الشائع في الحمل","sodium":"لا تقييد إلا مع ضغط الحمل"},
        "key_micronutrients":{"folic_acid":"600 ميكروجرام/يوم — يبدأ قبل الحمل بشهر (يقي عيوب الأنبوب العصبي)","iron":"27 مجم/يوم — ضعف الاحتياج الطبيعي (كبدة، لحوم، بقوليات + فيتامين C)","calcium":"1000 مجم/يوم (ألبان، سمسم، أسماك معلبة بالعظم)","vitamin_d":"600 IU/يوم","iodine":"220 ميكروجرام/يوم (أسماك، ألبان، ملح معزز)","choline":"450 مجم/يوم — بيض، لحوم، بقوليات (لتطوير دماغ الجنين)","dha":"200–300 مجم/يوم — سلمون، سردين، مكمل زيت سمك"},
        "key_points":["🔑 حمض الفوليك الأهم — يبدأ قبل الحمل بـ 4 أسابيع","🔑 تجنب الكافيين الزائد (< 200 مجم/يوم = كوب قهوة واحد)","🔑 تجنب الأسماك عالية الزئبق (سوورد فيش، marlin)","🔑 لا كحول إطلاقاً — متلازمة الكحول الجنينية خطيرة","🔑 الغثيان: وجبات صغيرة متكررة، بسكويت جاف، تجنب الروائح","🔑 الحديد يُمتص أفضل مع فيتامين C، ويقل مع الشاي والقهوة"],
        "foods_recommended":["كبدة الدجاج أو البقر مرة أسبوعياً (حديد + فولات + B12)","سلمون وسردين معلب (DHA + كالسيوم)","بيض كامل (كولين + DHA + بروتين)","بقوليات (فولات + حديد + ألياف)","ألبان ومشتقاتها (كالسيوم + D + بروتين)","حبوب كاملة مدعمة بحمض الفوليك"],
        "foods_limit":["جبن غير مبستر ولحوم نيئة (خطر ليستيريا)","أسماك عالية الزئبق","كافيين زائد (> 200 مجم/يوم)","مكملات فيتامين A الزائدة (تشوه خلقي)"],
        "weight_gain_guide":{"BMI < 18.5 (نحافة)":"12.5–18 كجم","BMI 18.5–24.9 (طبيعي)":"11.5–16 كجم","BMI 25–29.9 (زيادة وزن)":"7–11.5 كجم","BMI ≥ 30 (سمنة)":"5–9 كجم","حمل توأم (BMI طبيعي)":"17–25 كجم"},
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.14, pp.476–512",
    },
    "lactation": {
        "name":"الرضاعة الطبيعية (Lactation)","icon":"🤱","chapter":"Chapter 14 — Life Cycle Nutrition: Pregnancy and Lactation",
        "overview":"الرضاعة تزيد الاحتياجات الغذائية بشكل أكبر من الحمل نفسه. جودة الحليب تتأثر بتغذية الأم وبعض المواد تنتقل للطفل.",
        "goals":["إنتاج حليب كافٍ وعالي الجودة","الحفاظ على صحة الأم وذخائرها الغذائية","تدعيم التعافي بعد الولادة"],
        "macros":{"energy":"+500 kcal/يوم فوق الاحتياج الطبيعي (أعلى من الحمل)","carb":"210 جم/يوم كحد أدنى","protein":"+25 جم/يوم — إجمالي ~71 جم/يوم","fat":"DHA مهم جداً — يؤثر مباشرة على تركيزه في الحليب","fluid":"13 أكواب (3.1 لتر) يومياً","fiber":"29 جم/يوم"},
        "key_micronutrients":{"iodine":"290 ميكروجرام/يوم (الأعلى في دورة الحياة)","vitamin_d":"600 IU/يوم (لتعزيز فيتامين D في الحليب)","calcium":"1000 مجم/يوم","vitamin_a":"1300 ميكروجرام/يوم (أعلى من الحمل)","dha":"200–300 مجم/يوم — يؤثر على تطور دماغ الرضيع","choline":"550 مجم/يوم"},
        "key_points":["🔑 الكافيين ينتقل للحليب — كوب واحد مقبول، تابع تأثيره على الطفل","🔑 بعض الأطعمة تغير طعم الحليب (ثوم، توابل) ولا تضره","🔑 الكحول ينتقل للحليب — امتنعي أو انتظري ساعتين","🔑 خسارة الوزن التدريجية (0.5 كجم/أسبوع) آمنة","🔑 الترطيب الكافي ضروري لإدرار الحليب","🔑 أدوية كثيرة تنتقل للحليب — استشيري الطبيب قبل أي دواء"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.14, pp.497–505",
    },
    "ckd_predialysis": {
        "name":"الفشل الكلوي المزمن — قبل الديلزة","icon":"🫘","chapter":"Chapter 28 — Renal Diseases",
        "overview":"مرض الكلى المزمن يستلزم تقليل البروتين لتخفيف حمل اليوريا، وضبط الصوديوم والبوتاسيوم والفوسفور حسب المرحلة. التغذية تُبطئ تقدم المرض.",
        "goals":["إبطاء تقدم الفشل الكلوي بتقليل البروتين","منع سوء التغذية","ضبط الفوسفور والبوتاسيوم والصوديوم","الحفاظ على ضغط الدم وصحة العظام"],
        "macros":{"energy":"35 kcal/كجم/يوم (< 60 سنة) | 30-35 (> 60 سنة)","protein":"0.60–0.75 جم/كجم/يوم | > 50% بروتين عالي الجودة","sodium":"1000–3000 مجم/يوم حسب الحالة","potassium":"غير مقيد إذا كان طبيعياً — يُقيّد عند hyperkalemia","phosphorus":"800–1000 مجم/يوم إذا ارتفع الفوسفور أو PTH","calcium":"1000–1500 مجم/يوم","fluid":"غير مقيد إذا كان البول طبيعياً"},
        "key_points":["🔑 تقليل البروتين — اليوريا الزائدة تُجهد الكلى","🔑 الطاقة يجب أن تكفي حتى لا يُستهلك البروتين كطاقة","🔑 الفوسفور مرتفع في ألبان، مكسرات، مشروبات غازية","🔑 سلق الخضار يقلل البوتاسيوم فيها","🔑 فيتامين D نشط (calcitriol) ضروري لصحة العظام","🔑 مراقبة الألبومين للكشف المبكر عن سوء التغذية"],
        "high_phosphorus_foods":["ألبان ومشتقاتها","مكسرات","مشروبات غازية (كولا)","فاصوليا وعدس","حبوب كاملة"],
        "high_potassium_foods":["موز","طماطم وعصيرها","بطاطس","برتقال","أفوكادو","مشمش مجفف"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.28, pp.872–892",
    },
    "ckd_hemodialysis": {
        "name":"الفشل الكلوي — غسيل الكلى (Hemodialysis)","icon":"🫘","chapter":"Chapter 28 — Renal Diseases",
        "overview":"عند الغسيل الكلوي يرتفع احتياج البروتين لتعويض الخسائر خلال الجلسات، لكن تقييد السوائل والبوتاسيوم والفوسفور يصبح أكثر صرامة.",
        "goals":["ضمان بروتين كافٍ لتعويض خسائر الغسيل","تقييد السوائل بين الجلسات","ضبط البوتاسيوم والفوسفور لتجنب المضاعفات القلبية"],
        "macros":{"energy":"35 kcal/كجم/يوم (< 60 سنة) | 30-35 (> 60 سنة)","protein":"≥ 1.2 جم/كجم/يوم | > 50% بروتين عالي الجودة","sodium":"1000–3000 مجم/يوم","potassium":"2000–3000 مجم/يوم | يُعدّل حسب الدم","phosphorus":"800–1000 مجم/يوم | مع ضابطات الفوسفور","calcium":"< 2000 مجم/يوم","fluid":"1000 مل + كمية البول اليومية"},
        "key_points":["🔑 السوائل تشمل: ماء، عصائر، شوربة، جيلاتين، آيسكريم — كلها تُحسب","🔑 لا تزيد الزيادة في الوزن بين جلستين عن 1-1.5 كجم","🔑 البروتين يرتفع الآن (عكس ما قبل الديلزة) لتعويض الخسائر","🔑 ضابطات الفوسفور تُؤخذ مع أول لقمة في كل وجبة","🔑 الفاكهة المعلبة المصفاة أقل بوتاسيوماً من الطازجة"],
        "high_phosphorus_foods":["ألبان","مكسرات","مشروبات غازية","بقوليات"],
        "high_potassium_foods":["موز","طماطم","بطاطس","برتقال","فاكهة طازجة بشكل عام"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.28, pp.883–887",
    },
    "cardiovascular": {
        "name":"أمراض القلب والأوعية / ضغط الدم","icon":"❤️","chapter":"Chapter 27 — Cardiovascular Diseases",
        "overview":"نظام TLC (Therapeutic Lifestyle Changes) هو الأساس الغذائي لأمراض القلب. يستهدف خفض LDL والكوليسترول الكلي مع الحفاظ على HDL.",
        "goals":["خفض LDL والكوليسترول الكلي","رفع HDL","خفض الدهون الثلاثية (TG)","التحكم في ضغط الدم والوزن"],
        "macros":{"energy":"يكفي للحفاظ على وزن صحي أو إنقاصه","carb":"50–60% | حبوب كاملة وألياف قابلة للذوبان","protein":"15–20%","fat":"25–35% إجمالي | مشبعة < 7% | متحولة < 1% | كوليسترول < 200 مجم/يوم","fiber":"25–30 جم/يوم | ألياف قابلة للذوبان 10–25 جم/يوم","sodium":"< 2300 مجم/يوم | < 1500 مع ضغط الدم (DASH)","omega3":"سمك دهني مرتين/أسبوع | 1 جم EPA+DHA يومياً لمرضى القلب"},
        "dash_diet":{"description":"حمية DASH لخفض ضغط الدم","fruits":"4–5 حصص/يوم","vegetables":"4–5 حصص/يوم","grains":"6–8 حصص/يوم (كاملة)","dairy_lowfat":"2–3 حصص/يوم","lean_meat":"≤ 6 أوقية/يوم","nuts_seeds":"4–5 حصص/أسبوع","fats_oils":"2–3 حصص/يوم (زيت زيتون، كانولا)","sodium":"1500–2300 مجم/يوم"},
        "key_points":["🔑 الدهون المشبعة أخطر من الكوليسترول الغذائي — قلل اللحوم الدهنية والزبدة","🔑 الدهون المتحولة (هدرجة) ترفع LDL وتخفض HDL — أخطر الدهون","🔑 الألياف القابلة للذوبان (شوفان، بقوليات) تخفض LDL","🔑 أوميغا 3 من السمك يخفض الدهون الثلاثية","🔑 DASH يخفض الضغط الانقباضي 8-14 نقطة","🔑 الصوديوم المخفي في الأطعمة المعلبة هو الأخطر"],
        "foods_recommended":["سمك دهني مرتين/أسبوع (سلمون، مكريل، سردين)","شوفان وحبوب كاملة يومياً","بقوليات 4-5 مرات/أسبوع","مكسرات غير مملحة (جوز، لوز)","زيت زيتون بكر ممتاز","فاكهة وخضروات متنوعة"],
        "foods_limit":["لحوم حمراء دهنية — مرتان/أسبوع كحد أقصى","زبدة وسمن حيواني وقشطة","أطعمة محتوية على زيوت هدرجة","أطعمة مقلية وعالية الملح","صفار البيض — 2/أسبوع للمرتفعي LDL"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.27, pp.840–870",
    },
    "liver_cirrhosis": {
        "name":"تليف الكبد (Liver Cirrhosis)","icon":"🫀","chapter":"Chapter 25 — Liver Disease and Gallstones",
        "overview":"التليف الكبدي يُعطل التمثيل الغذائي للبروتين والكربوهيدرات والدهون. سوء التغذية شائع جداً. تحاشي الكحول تماماً ضروري.",
        "goals":["الوقاية من سوء التغذية وضمان طاقة كافية","منع اعتلال الدماغ الكبدي","ضبط الاستسقاء بتقييد الصوديوم","توقف تام عن الكحول"],
        "macros":{"energy":"35–40 kcal/كجم/يوم من الوزن الجاف","protein":"1.2–1.5 جم/كجم/يوم | لا تقلل إلا عند اعتلال الدماغ الحاد","carb":"55–60% | وجبات صغيرة متكررة لتجنب نقص السكر","fat":"دهون طبيعية | MCT عند سوء الامتصاص الشديد","sodium":"< 2000 مجم/يوم عند الاستسقاء","fluid":"< 1000–1500 مل/يوم عند hyponatremia","zinc":"مكمل الزنك مفيد — كثيراً ما يكون ناقصاً"},
        "key_micronutrients":{"vitamin_k":"غالباً ناقص — ضروري لعوامل التخثر","vitamin_d":"ناقص في 90% من الحالات","zinc":"نقصه يُعجّل اعتلال الدماغ","folate":"ناقص خاصة في تليف الكحول","thiamine_b1":"حرج جداً — نقصه يُسبب متلازمة Wernicke"},
        "key_points":["🔑 6 وجبات صغيرة/يوم تقلل عبء البروتين وتمنع نقص السكر","🔑 وجبة خفيفة متأخرة في الليل (Late Evening Snack) تُقلل الانهيار العضلي","🔑 لا تقلل البروتين عشوائياً — سوء التغذية يُفاقم اعتلال الدماغ","🔑 عند اعتلال الدماغ: يُفضل البروتين النباتي مؤقتاً","🔑 الاستسقاء يزيف الوزن — استخدم الوزن الجاف للحسابات"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.25, pp.786–800",
    },
    "obesity": {
        "name":"السمنة وزيادة الوزن","icon":"⚖️","chapter":"Chapter 9 — Weight Management",
        "overview":"السمنة (BMI ≥ 30) تزيد خطر السكري والقلب والسرطان. خسارة 5-10% من الوزن الأولي تُحسن المؤشرات الصحية. النهج المتكامل هو الأكثر فعالية.",
        "goals":["خسارة 0.5–1 كجم/أسبوع بعجز 500–1000 kcal/يوم","الحفاظ على الكتلة العضلية","تعديل نمط الحياة طويل الأمد","علاج الأمراض المصاحبة"],
        "macros":{"energy":"1200–1500 kcal للنساء | 1500–1800 للرجال (الحد الأدنى)","protein":"25–30% — يزيد الشبع ويحافظ على العضل","carb":"45–50% — حبوب كاملة وبقوليات وخضروات","fat":"25–35% — مع تقليل المشبعة","fiber":"25–38 جم/يوم — يزيد الشبع ويُبطئ الهضم"},
        "key_points":["🔑 عجز الطاقة هو الأساس — لا نظام سحري","🔑 البروتين العالي (30%) يحافظ على العضل ويقلل الجوع","🔑 الألياف تزيد الشبع بدون كثير من السعرات","🔑 150–300 دقيقة نشاط هوائي/أسبوع للإنقاص","🔑 النوم الكافي يُعادل هرمونات الجوع والشبع","🔑 تتبع الطعام (food diary) يزيد الفقدان الفعلي"],
        "strategies":["أكل وجبات في أوقات منتظمة","تقليل حجم الأطباق والتحكم في الحصص","تناول الخضروات في بداية الوجبة","شرب كوب ماء قبل الأكل بـ 30 دقيقة","إزالة الأطعمة المغرية من المنزل","الأكل على الطاولة وليس أمام الشاشة"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.9, pp.270–310",
    },
    "cancer": {
        "name":"السرطان (Cancer)","icon":"🎗️","chapter":"Chapter 29 — Cancer and HIV Infection",
        "overview":"السرطان وعلاجه يسببان فقدان الوزن والعضل. الكاكسيا السرطانية حالة أيضية تعيق التغذية. الهدف: الحفاظ على الوزن والكتلة العضلية قدر الإمكان.",
        "goals":["الحفاظ على الوزن ومنع الكاكسيا","دعم تحمل العلاج","تعزيز المناعة","تحسين جودة الحياة"],
        "macros":{"energy":"25–35 kcal/كجم/يوم | 35–45 عند النحول الشديد","protein":"1.2–2.0 جم/كجم/يوم — لتعويض الهدم العضلي","fat":"دهون صحية — أوميغا 3 قد يُخفف الالتهاب","fluid":"30–35 مل/كجم/يوم على الأقل"},
        "key_points":["🔑 الأولوية لإدخال السعرات بأي وسيلة — الطاقة أهم في مراحل العلاج","🔑 وجبات صغيرة كثيرة (6-8/يوم) أسهل من 3 كبيرة","🔑 الغثيان: تجنب الروائح، أكل بارد، وجبات جافة","🔑 تقرحات الفم: طعام طري وبارد، تجنب الحمضيات","🔑 الإسهال: BRAT diet، تعويض الكهارل","🔑 مكملات EPA (أوميغا 3) قد تُخفف فقدان العضل"],
        "foods_recommended":["بياض بيض مطهو (بروتين عالٍ وسهل)","زبادي يوناني (بروتين + بروبيوتيك)","سمك مسلوق أو بخار","شوربات غنية بالبروتين","سموثي بالحليب وبروتين"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.29, pp.900–920",
    },
    "hiv_aids": {
        "name":"فيروس نقص المناعة البشري (HIV/AIDS)","icon":"🔴","chapter":"Chapter 29 — Cancer and HIV Infection",
        "overview":"HIV وعلاجه يزيدان الاحتياجات الغذائية ويسببان مقاومة للأنسولين واضطرابات الدهون. سلامة الغذاء بالغة الأهمية.",
        "goals":["الحفاظ على الوزن والكتلة العضلية","دعم جهاز المناعة","ضبط اضطرابات الدهون المرتبطة بالعلاج","ضمان سلامة الغذاء"],
        "macros":{"energy":"رفع 10% في المرحلة المستقرة | 20-30% عند الأعراض","protein":"1.0–1.5 جم/كجم/يوم | 1.5–2.0 عند الأعراض الشديدة"},
        "key_points":["🔑 سلامة الغذاء: طهي جيد، تجنب ألبان غير مبسترة، غسيل الفواكه جيداً","🔑 الدهون: علاجات الريتروفيراس قد ترفع الكوليسترول — تعديل الدهون مهم","🔑 بعض الأدوية تُؤخذ مع طعام وأخرى على معدة فارغة — راجع الدواء","🔑 مكملات الفيتامينات والمعادن موصى بها لأغلب المرضى"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.29, pp.911–917",
    },
    "gerd": {
        "name":"حرقة المعدة / الارتجاع (GERD)","icon":"🔥","chapter":"Chapter 23 — Upper Gastrointestinal Disorders",
        "overview":"ارتجاع المريء يحدث عند ارتداد حمض المعدة للمريء. التعديلات الغذائية وتغيير نمط الحياة أساس العلاج.",
        "goals":["تخفيف أعراض الارتجاع","منع تلف المريء","تحسين جودة الحياة"],
        "macros":{"energy":"يكفي للحفاظ على وزن صحي أو إنقاصه","carb":"طبيعي مع تجنب المُفاقِمات","protein":"طبيعي","fat":"تقليل الدهون العالية التي تُبطئ إفراغ المعدة"},
        "key_points":["🔑 تجنب الأكل قبل النوم بـ 3 ساعات","🔑 وجبات صغيرة متكررة أفضل من كبيرة","🔑 رفع رأس السرير 15–20 سم","🔑 محفزات: قهوة، كحول، شوكولاتة، نعناع، ثوم، بصل، طماطم، حمضيات","🔑 الدهون والمقليات تُبطئ إفراغ المعدة وتُفاقم الأعراض","🔑 خسارة الوزن تُحسّن الأعراض بشكل ملحوظ"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.23, pp.730–750",
    },
    "ibs": {
        "name":"القولون العصبي (IBS)","icon":"🫃","chapter":"Chapter 24 — Lower Gastrointestinal Disorders",
        "overview":"القولون العصبي اضطراب وظيفي مع آلام البطن وإسهال/إمساك. حمية Low-FODMAP فعّالة لدى 75% من المرضى.",
        "goals":["تخفيف الأعراض","تحديد المحفزات الغذائية الفردية","تحسين جودة الحياة"],
        "macros":{"energy":"طبيعي","carb":"تقليل FODMAP في المرحلة الأولى ثم إعادة إدخال تدريجي","protein":"طبيعي","fat":"طبيعي — تجنب الكميات الكبيرة دفعة واحدة","fiber":"ألياف قابلة للذوبان (psyllium) للإمساك السائد"},
        "key_points":["🔑 حمية Low-FODMAP: تقليل السكريات القابلة للتخمر (فركتوز، لاكتوز)","🔑 ألياف قابلة للذوبان (psyllium) للإمساك السائد","🔑 ألياف غير قابلة للذوبان قد تُفاقم الإسهال — استخدمها بحذر","🔑 البروبيوتيك قد يُخفف الأعراض في بعض المرضى","🔑 إدارة التوتر جزء أساسي من العلاج"],
        "high_fodmap_foods":["تفاح، كمثرى، مانجو","حليب عادي ولبن","قمح وشعير","بصل وثوم","عدس وحمص بكميات كبيرة"],
        "low_fodmap_foods":["موز ناضج، عنب، فراولة، كيوي","حليب خالٍ من اللاكتوز","أرز، شوفان، كينوا","جزر، خيار، طماطم"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.24, pp.754–780",
    },
    "metabolic_syndrome": {
        "name":"المتلازمة الأيضية","icon":"🔬","chapter":"Chapter 26 — Highlight: The Metabolic Syndrome",
        "overview":"المتلازمة الأيضية: 3 أو أكثر من: دهون البطن + ارتفاع الجلوكوز + ارتفاع الضغط + ارتفاع TG + انخفاض HDL. تسبق السكري وأمراض القلب.",
        "goals":["خسارة 5-10% من الوزن","تحسين جميع مكونات المتلازمة","تقليل خطر السكري وأمراض القلب"],
        "macros":{"energy":"عجز معتدل 500-750 kcal/يوم","carb":"تقليل الكارب المكرر والسكريات البسيطة","protein":"25-30%","fat":"زيادة الدهون الصحية (أحادية وغير مشبعة)","fiber":"25-38 جم/يوم"},
        "key_points":["🔑 خسارة 5-10% من الوزن تُحسّن أو تُعالج معظم مكونات المتلازمة","🔑 150 دقيقة نشاط هوائي/أسبوع أساسي","🔑 تقليل الكارب المكرر والسكريات البسيطة","🔑 زيادة الألياف والدهون الصحية","🔑 توقف عن التدخين"],
        "reference":"Rolfes et al., Understanding Normal and Clinical Nutrition, 8th Ed, Ch.26 Highlight, pp.836–839",
    },
}

COMBINATION_NOTES = {
    ("diabetes_t2","cardiovascular"): "⚠️ السكري + القلب: البروتين 15-20% (لحماية الكلى). دهون مشبعة < 7%. ضبط HbA1c وLDL معاً. حمية DASH مناسبة للحالتين.",
    ("diabetes_t2","ckd_predialysis"): "⚠️ السكري + الكلى: بروتين 0.6-0.75 جم/كجم + ضبط الكارب + مراقبة البوتاسيوم والفوسفور. HbA1c هدف 7.5-8% لتجنب نقص السكر الخطر.",
    ("cardiovascular","ckd_predialysis"): "⚠️ القلب + الكلى: تقليل الصوديوم والسوائل لكليهما. أوميغا 3 مفيد للقلب لكن راعِ مستوى الفوسفور.",
    ("pregnancy","diabetes_t1"): "⚠️ الحمل + السكري النوع 1: هدف السكر < 95 صيام و< 140 بعد ساعة. متابعة مكثفة. DHA ضروري لنمو دماغ الجنين.",
    ("pregnancy","diabetes_t2"): "⚠️ الحمل + السكري النوع 2: حمض الفوليك 5 مجم يومياً (ضعف المعتاد). بعض أدوية السكري ممنوعة في الحمل — راجع الطبيب فوراً.",
    ("diabetes_t1","cardiovascular"): "⚠️ السكري النوع 1 + القلب: ضبط مكثف للسكر والدهون. أوميغا 3 مهم. تجنب نقص السكر الشديد الذي يضر القلب.",
    ("obesity","diabetes_t2"): "⚠️ السمنة + السكري 2: خسارة الوزن هي العلاج الأساسي. عجز 500-750 kcal/يوم مع إعطاء الأولوية للبروتين العالي والألياف.",
    ("liver_cirrhosis","diabetes_t2"): "⚠️ تليف الكبد + السكري: سكر الكبد مختلف عن سكر البنكرياس. تحاشي نقص السكر مهم جداً. استشارة متخصصة.",
}

# ══════════════════════════════════════════
# SESSION
# ══════════════════════════════════════════

# ══════════════════════════════════════════
# SESSION INIT
# ══════════════════════════════════════════
for k,v in [("page","login"),("user",None),("targets",None),
            ("confirm_del",None),("lang","ar")]:
    if k not in st.session_state: st.session_state[k]=v
REQUIRED={"cal","p","c","f","goal"}

# ── Direction based on language ──
DIR = "rtl" if st.session_state.lang=="ar" else "ltr"
st.markdown(f"<style>html,body,[class*='css']{{direction:{DIR}!important}}</style>",
            unsafe_allow_html=True)

# ══════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════
if st.session_state.page=="login":

    # Language toggle top right
    col_lang, _ = st.columns([1,4])
    with col_lang:
        if st.button(f"🌐 {T('lang_btn')}", key="lang_toggle_login"):
            st.session_state.lang = "en" if st.session_state.lang=="ar" else "ar"
            st.rerun()

    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="login-logo">
        <div class="logo-icon">🥗</div>
        <h1>NutraX</h1>
        <p>{T('tagline')}</p>
    </div>""", unsafe_allow_html=True)

    t1,t2=st.tabs([f"🔑 {T('login')}", f"✨ {T('register')}"])
    with t1:
        with st.form("lgn"):
            e=st.text_input(f"📧 {T('email')}")
            p=st.text_input(f"🔒 {T('password')}",type="password")
            remember=st.checkbox(T('remember'), value=True)
            if st.form_submit_button(T('enter'), use_container_width=True):
                c.execute("SELECT * FROM users WHERE email=? AND password=?",(e,hp(p)))
                u=c.fetchone()
                if u:
                    st.session_state.user=u
                    st.session_state.page="dashboard"
                    if remember:
                        st.query_params["t"]=hp(p)
                    st.rerun()
                else: st.error(T('wrong_creds'))
    with t2:
        with st.form("reg"):
            n=st.text_input(f"👤 {T('name')}")
            e2=st.text_input(f"📧 {T('email')}")
            p2=st.text_input(f"🔒 {T('password')}",type="password")
            by=st.number_input(f"📅 {T('birth_year')}",1950,2010,1995)
            cn=st.selectbox(f"🌍 {T('country')}",
                ["Egypt","Saudi Arabia","UAE","Kuwait","Qatar","Bahrain","Jordan","Other"])
            if st.form_submit_button(T('create'), use_container_width=True):
                try:
                    c.execute("INSERT INTO users (email,password,name,birth_year,country,is_admin) VALUES (?,?,?,?,?,0)",
                              (e2,hp(p2),n,by,cn)); conn.commit()
                    st.success(T('registered'))
                except: st.error(T('email_used'))
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════
else:
    if st.session_state.user is None or len(st.session_state.user)<5:
        st.session_state.user=None; st.session_state.page="login"; st.rerun()
    if st.session_state.targets and not REQUIRED.issubset(st.session_state.targets.keys()):
        st.session_state.targets=None
    u=st.session_state.user; u_id=u[0]

    # ── SIDEBAR ──
    with st.sidebar:
        # Language toggle
        if st.button(f"🌐 {T('lang_btn')}", key="lang_toggle_app"):
            st.session_state.lang="en" if st.session_state.lang=="ar" else "ar"
            st.rerun()

        st.markdown(f"""
        <div style="text-align:center;padding:20px 0 16px;border-bottom:1px solid #e2e8f0;margin-bottom:12px">
            <div style="width:56px;height:56px;border-radius:50%;background:#eff6ff;
                border:2px solid #93c5fd;display:flex;align-items:center;
                justify-content:center;font-size:26px;margin:0 auto 10px">👤</div>
            <div style="color:#0f172a;font-size:15px;font-weight:700">{u[3]}</div>
            <div style="color:#64748b;font-size:12px;margin-top:3px">{u[1]}</div>
        </div>""", unsafe_allow_html=True)

        NAV=[("🏠", T("dashboard"),    "dashboard"),
             ("⚙️", T("settings"),     "profile_setup"),
             ("🔍", T("analyzer"),     "analyzer"),
             ("📅", T("planner"),      "planner"),
             ("💡", T("suggester"),    "suggester"),
             ("💾", T("saved"),        "saved"),
             ("📈", T("history"),      "history"),
             ("📚", T("clinical"),     "clinical")]
        if u[9]==1:
            NAV.append(("👑", "لوحة الأدمن", "admin"))

        for i,(icon,label,pg) in enumerate(NAV):
            is_active = st.session_state.page == pg
            # Active button gets blue highlight via CSS override
            if is_active:
                st.markdown(f"""
                <div style="background:#eff6ff;border:1px solid #93c5fd;border-radius:10px;
                    padding:12px 16px;margin-bottom:6px;cursor:pointer;direction:rtl;
                    display:flex;align-items:center;gap:10px">
                    <span style="font-size:16px">{icon}</span>
                    <span style="color:#1d4ed8;font-weight:700;font-size:14px">{label}</span>
                    <span style="margin-right:auto;width:6px;height:6px;border-radius:50%;background:#2563eb;display:inline-block"></span>
                </div>""", unsafe_allow_html=True)
            if st.button(f"{icon}  {label}" if not is_active else f"← {label}",
                        key=f"sb_nav_{i}",
                        type="secondary" if not is_active else "primary"):
                st.session_state.page=pg; st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown("<div style='border-top:1px solid #e2e8f0;margin:4px 0 12px'></div>", unsafe_allow_html=True)

        if st.button(f"🚪  {T('logout')}", key="logout"):
            st.query_params.clear()
            st.session_state.user=None; st.session_state.page="login"; st.rerun()

        st.markdown(f"<div style='text-align:center;color:#cbd5e1;font-size:10px;margin-top:16px'>NutraX V12 © 2025</div>",
                   unsafe_allow_html=True)

    # ── Mobile bottom nav ──
    pg_now=st.session_state.page
    st.markdown(f"""
    <div class="bottom-nav">
        <div class="bn-item {'active' if pg_now=='dashboard' else ''}"
             onclick="window.location.href='?page=dashboard'">
            <div class="bn-icon">🏠</div><div>{T('dashboard')}</div></div>
        <div class="bn-item {'active' if pg_now=='analyzer' else ''}"
             onclick="window.location.href='?page=analyzer'">
            <div class="bn-icon">🔍</div><div>{T('analyzer')}</div></div>
        <div class="bn-item {'active' if pg_now=='planner' else ''}"
             onclick="window.location.href='?page=planner'">
            <div class="bn-icon">📅</div><div>{T('planner')}</div></div>
        <div class="bn-item {'active' if pg_now=='clinical' else ''}"
             onclick="window.location.href='?page=clinical'">
            <div class="bn-icon">📚</div><div>{T('clinical')}</div></div>
        <div class="bn-item {'active' if pg_now=='profile_setup' else ''}"
             onclick="window.location.href='?page=settings'">
            <div class="bn-icon">⚙️</div><div>{T('settings')}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ═══════════════ DASHBOARD ═══════════════
    if st.session_state.page=="dashboard":
        gl={
            "fat_loss":   T("fat_loss"),
            "muscle_gain":T("muscle_gain"),
            "maintain":   T("maintain")
        }
        greet = "أهلاً بك 👋" if st.session_state.get("lang","ar")=="ar" else "Welcome 👋"
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#2563eb,#7c3aed);
            border-radius:18px;padding:20px 22px;margin-bottom:18px;color:#fff">
            <div style="font-size:14px;opacity:.85;margin-bottom:4px">{greet}</div>
            <div style="font-size:22px;font-weight:900">{u[3]}</div>
            <div style="font-size:12px;opacity:.8;margin-top:6px">{u[1]}</div>
        </div>""", unsafe_allow_html=True)

        if not st.session_state.targets:
            st.markdown(f"""
            <div style="background:#fffbeb;border:1.5px solid #fcd34d;border-radius:14px;
                padding:18px 20px;text-align:center;margin-bottom:16px">
                <div style="font-size:36px;margin-bottom:8px">⚙️</div>
                <div style="color:#78350f;font-weight:700;font-size:15px">{T('complete_settings')}</div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"⚙️ {T('go_settings')}", use_container_width=True):
                st.session_state.page="profile_setup"; st.rerun()
        else:
            t=st.session_state.targets
            c.execute("SELECT COUNT(*) FROM saved_plans WHERE user_id=?",(u_id,)); pn=c.fetchone()[0]
            c.execute("SELECT weight FROM tracking WHERE user_id=? ORDER BY id DESC LIMIT 1",(u_id,)); lw=c.fetchone()
            goal_label = gl.get(t['goal'], t['goal'])
            st.markdown(f"""
            <div style="background:#f8faff;border:1.5px solid #dbeafe;border-radius:12px;
                padding:14px 18px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="color:#64748b;font-size:12px;font-weight:700">{T('your_goal')}</div>
                    <div style="color:#0f172a;font-size:16px;font-weight:800">{goal_label}</div>
                </div>
                <div style="text-align:center">
                    <div style="color:#64748b;font-size:12px;font-weight:700">{T('tdee')}</div>
                    <div style="color:#0f172a;font-size:16px;font-weight:800">{t.get('tdee','—')}</div>
                    <div style="color:#94a3b8;font-size:10px">kcal</div>
                </div>
                <div>
                    <div style="color:#64748b;font-size:12px;font-weight:700">{T('daily_target')}</div>
                    <div style="color:#2563eb;font-size:20px;font-weight:900">{t['cal']}</div>
                    <div style="color:#94a3b8;font-size:10px">kcal</div>
                </div>
            </div>""", unsafe_allow_html=True)
            r1c1,r1c2=st.columns(2); r2c1,r2c2=st.columns(2)
            for col,ic,lb,val,un,clr in [
                (r1c1,"🔥",T("calories"),  t['cal'],"kcal","#2563eb"),
                (r1c2,"💪",T("protein"),   t['p'],  T("gram"),"#16a34a"),
                (r2c1,"🍞",T("carbs"),     t['c'],  T("gram"),"#d97706"),
                (r2c2,"🥑",T("fat"),       t['f'],  T("gram"),"#dc2626"),
            ]:
                col.markdown(f"""
                <div class="card" style="text-align:center;margin-bottom:10px">
                    <div style="font-size:24px;margin-bottom:4px">{ic}</div>
                    <div style="color:#64748b;font-size:12px;font-weight:700">{lb}</div>
                    <div style="color:{clr};font-size:26px;font-weight:900">{val}</div>
                    <div style="color:#94a3b8;font-size:12px">{un}</div>
                </div>""", unsafe_allow_html=True)
            bv_str="—"; bcls="bmi-normal"; blbl="—"
            if u[4] and u[5]:
                bv,bcls,blbl=bmi_info(float(u[5]),float(u[4])); bv_str=str(bv)
            wv=f"{lw[0]} kg" if lw else "—"
            ec1,ec2,ec3=st.columns(3)
            ec1.markdown(f'''<div class="card" style="text-align:center;padding:14px 8px">
                <div style="font-size:12px;color:#64748b;font-weight:700">{T("bmi")}</div>
                <div style="font-size:22px;font-weight:900;color:#0f172a">{bv_str}</div>
                <div class="bmi-badge {bcls}">{blbl}</div></div>''', unsafe_allow_html=True)
            ec2.markdown(f'''<div class="card" style="text-align:center;padding:14px 8px">
                <div style="font-size:12px;color:#64748b;font-weight:700">{T("last_weight")}</div>
                <div style="font-size:18px;font-weight:900;color:#0f172a;margin-top:4px">{wv}</div></div>''', unsafe_allow_html=True)
            ec3.markdown(f'''<div class="card" style="text-align:center;padding:14px 8px">
                <div style="font-size:12px;color:#64748b;font-weight:700">{T("plans")}</div>
                <div style="font-size:26px;font-weight:900;color:#7c3aed;margin-top:2px">{pn}</div></div>''', unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:16px;margin-bottom:8px;font-size:14px;font-weight:700;color:#374151'>{T('quick_access')}</div>", unsafe_allow_html=True)
            qn1,qn2=st.columns(2)
            with qn1:
                if st.button(f"🔍 {T('analyzer')}", use_container_width=True, key="qnav_a"):
                    st.session_state.page="analyzer"; st.rerun()
                if st.button(f"📚 {T('clinical')}", use_container_width=True, key="qnav_c"):
                    st.session_state.page="clinical"; st.rerun()
            with qn2:
                if st.button(f"📅 {T('planner')}", use_container_width=True, key="qnav_p"):
                    st.session_state.page="planner"; st.rerun()
                if st.button(f"📈 {T('history')}", use_container_width=True, key="qnav_h"):
                    st.session_state.page="history"; st.rerun()

    # ═══════════════ PROFILE ═══════════════
    elif st.session_state.page=="profile_setup":
        st.markdown("<div class='sec-title'>⚙️ الإعدادات والهدف</div>",unsafe_allow_html=True)
        with st.form("pf"):
            c1,c2=st.columns(2)
            with c1:
                h=st.number_input("📏 الطول (سم)",140.0,220.0,float(u[4] or 170))
                w=st.number_input("⚖️ الوزن (كجم)",40.0,250.0,float(u[5] or 70))
                age=st.number_input("📅 العمر (سنة)",15,90,25)
            with c2:
                goal=st.selectbox("🎯 هدفك",["maintain","fat_loss","muscle_gain"],
                    format_func=lambda x:{"maintain":"⚖️ ثبات الوزن","fat_loss":"🔥 خسارة دهون","muscle_gain":"💪 بناء عضل"}[x])
                act=st.selectbox("🏃 مستوى النشاط",[1.2,1.375,1.55,1.725,1.9],
                    format_func=lambda x:{1.2:"مستقر",1.375:"خفيف (1-3 أيام)",
                        1.55:"معتدل (3-5 أيام)",1.725:"نشيط (6-7 أيام)",1.9:"رياضي محترف"}[x])
            if st.form_submit_button("💾 حفظ وحساب الأهداف",use_container_width=True):
                c.execute("UPDATE users SET height=?,weight=?,goal=?,birth_year=? WHERE id=?",(h,w,goal,datetime.now().year-age,u_id)); conn.commit()
                st.session_state.targets=calc_targets(w,h,age,goal,act)
                c.execute("SELECT * FROM users WHERE id=?",(u_id,)); st.session_state.user=c.fetchone()
                st.success("✅ تم الحفظ!"); st.session_state.page="dashboard"; st.rerun()

    # ═══════════════ ANALYZER ═══════════════
    elif st.session_state.page=="analyzer":
        lang = st.session_state.get("lang","ar")
        is_ar = lang=="ar"
        gr = "ج" if is_ar else "g"

        st.markdown(f"<div class='sec-title'>🔍 {T('analyzer')}</div>", unsafe_allow_html=True)

        # ── Search + Category ──
        cats = sorted(set(v["cat"] for v in LOCAL_DB.values()))
        c1, c2 = st.columns([1, 2])
        with c1:
            sel_cat = st.selectbox(
                f"📂 {T('filter_cat')}",
                [T('all')] + cats
            )
        with c2:
            search = st.text_input(
                f"🔎 {T('search')}",
                placeholder="دجاج، سلمون، شوفان..." if is_ar else "chicken, salmon, oats..."
            )

        # ── Filter ──
        filtered = dict(LOCAL_DB)
        if sel_cat != T('all'):
            filtered = {k:v for k,v in filtered.items() if v["cat"]==sel_cat}
        if search:
            s = search.lower()
            filtered = {k:v for k,v in filtered.items() if s in k.lower() or s in v["name"]}

        # Category tip
        if not search and sel_cat != T('all') and sel_cat in CATEGORY_TIPS:
            st.markdown(f"<div class='alert-info'>💡 {CATEGORY_TIPS[sel_cat]}</div>", unsafe_allow_html=True)

        # Count
        total_label = f"{len(filtered)} {'نتيجة' if is_ar else 'results'} · {'لكل 100 جرام' if is_ar else 'per 100g'}"
        st.markdown(f"<div style='color:#64748b;font-size:13px;margin-bottom:12px;font-weight:500'>{total_label}</div>", unsafe_allow_html=True)

        if not filtered:
            st.markdown(f"<div class='alert-warn'>{T('no_results')}</div>", unsafe_allow_html=True)
        elif len(filtered) > 30 and not search:
            st.info(T('show_first30'))

        # ── Food cards ──
        for k, v in list(filtered.items())[:30]:
            with st.container():
                # Card header
                st.markdown(f"""
                <div style="background:#ffffff;border:1.5px solid #e2e8f0;border-radius:16px;
                    padding:16px 18px;margin-bottom:4px;border-right:4px solid #2563eb">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start">
                        <div>
                            <div style="font-size:17px;font-weight:800;color:#0f172a">{v['name']}</div>
                            <div style="font-size:12px;color:#64748b;margin-top:2px">{v['cat']}</div>
                        </div>
                        <div style="text-align:left">
                            <div style="font-size:22px;font-weight:900;color:#2563eb">{v['cal']}</div>
                            <div style="font-size:11px;color:#64748b">kcal/100{gr}</div>
                        </div>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
                        <span style="background:#dbeafe;color:#1e40af;border:1px solid #93c5fd;
                            padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700">
                            💪 {v['p']}{gr} {'بروتين' if is_ar else 'protein'}
                        </span>
                        <span style="background:#fef3c7;color:#92400e;border:1px solid #fcd34d;
                            padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700">
                            🍞 {v['c']}{gr} {'كارب' if is_ar else 'carbs'}
                        </span>
                        <span style="background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;
                            padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700">
                            🥑 {v['f']}{gr} {'دهون' if is_ar else 'fat'}
                        </span>
                    </div>
                </div>""", unsafe_allow_html=True)

                # ── Grams input + live calc ──
                gc1, gc2 = st.columns([1, 2])
                with gc1:
                    grams = st.number_input(
                        f"{'الكمية' if is_ar else 'Amount'} ({gr})",
                        min_value=0, max_value=2000,
                        value=100, step=10,
                        key=f"az_g_{k}"
                    )
                with gc2:
                    if grams > 0:
                        r = grams / 100
                        cal_r = round(v['cal'] * r, 1)
                        p_r   = round(v['p']   * r, 1)
                        c_r   = round(v['c']   * r, 1)
                        f_r   = round(v['f']   * r, 1)
                        st.markdown(f"""
                        <div style="background:#f0f7ff;border:1.5px solid #93c5fd;border-radius:12px;
                            padding:12px 16px;margin-top:22px">
                            <div style="font-size:11px;font-weight:700;color:#1e40af;margin-bottom:8px">
                                {'نتيجة' if is_ar else 'Result'} {grams}{gr} {'من' if is_ar else 'of'} {v['name']}
                            </div>
                            <div style="display:flex;gap:12px;flex-wrap:wrap">
                                <div style="text-align:center">
                                    <div style="font-size:20px;font-weight:900;color:#1d4ed8">{cal_r}</div>
                                    <div style="font-size:11px;color:#64748b">kcal</div>
                                </div>
                                <div style="text-align:center">
                                    <div style="font-size:20px;font-weight:900;color:#166534">{p_r}{gr}</div>
                                    <div style="font-size:11px;color:#64748b">{'بروتين' if is_ar else 'protein'}</div>
                                </div>
                                <div style="text-align:center">
                                    <div style="font-size:20px;font-weight:900;color:#92400e">{c_r}{gr}</div>
                                    <div style="font-size:11px;color:#64748b">{'كارب' if is_ar else 'carbs'}</div>
                                </div>
                                <div style="text-align:center">
                                    <div style="font-size:20px;font-weight:900;color:#991b1b">{f_r}{gr}</div>
                                    <div style="font-size:11px;color:#64748b">{'دهون' if is_ar else 'fat'}</div>
                                </div>
                            </div>
                        </div>""", unsafe_allow_html=True)

                # Notes + Tip (collapsible)
                with st.expander(f"📋 {'معلومة + نصيحة' if is_ar else 'Info & Tip'}"):
                    st.markdown(f"""
                    <div style="background:#f0fdf4;border-right:3px solid #16a34a;border-radius:8px;
                        padding:10px 14px;margin-bottom:8px;font-size:14px;color:#14532d;line-height:1.7">
                        {v['note']}
                    </div>
                    <div style="background:#fffbeb;border-right:3px solid #f59e0b;border-radius:8px;
                        padding:10px 14px;font-size:14px;color:#78350f;line-height:1.7">
                        {v['tip']}
                    </div>""", unsafe_allow_html=True)

                st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)


    # ═══════════════ PLANNER ═══════════════
    elif st.session_state.page=="planner":
        is_ar = st.session_state.get("lang","ar") == "ar"
        gr = "ج" if is_ar else "g"

        st.markdown(f"<div class='sec-title'>📅 {T('planner')}</div>", unsafe_allow_html=True)

        if not st.session_state.targets:
            st.markdown(f"<div class='alert-warn'>⚠️ {T('complete_settings')}</div>", unsafe_allow_html=True)
            if st.button(f"⚙️ {T('go_settings')}"): st.session_state.page="profile_setup"; st.rerun()
            st.stop()

        t = st.session_state.targets
        gr_lbl = "ج" if is_ar else "g"

        # ── Target bar ──
        st.markdown(f"""
        <div style="background:#f0f7ff;border:1.5px solid #93c5fd;border-radius:14px;
            padding:14px 18px;margin-bottom:18px;font-size:15px;font-weight:600;color:#1e3a8a">
            🎯 {'هدفك اليومي' if is_ar else 'Daily Target'}:
            <b>{t['cal']} kcal</b> &nbsp;|&nbsp;
            💪 {t['p']}{gr_lbl} {'بروتين' if is_ar else 'protein'} &nbsp;|&nbsp;
            🍞 {t['c']}{gr_lbl} {'كارب' if is_ar else 'carbs'} &nbsp;|&nbsp;
            🥑 {t['f']}{gr_lbl} {'دهون' if is_ar else 'fat'}
        </div>""", unsafe_allow_html=True)

        # ── Clinical condition selector ──
        with st.expander(f"🏥 {'ربط بحالة مرضية (اختياري)' if is_ar else 'Link to Clinical Condition (optional)'}"):
            CONDITIONS_OPTS_P = {
                "🩸 السكري النوع الأول" if is_ar else "🩸 Type 1 Diabetes":       "diabetes_t1",
                "🩸 السكري النوع الثاني" if is_ar else "🩸 Type 2 Diabetes":      "diabetes_t2",
                "🤰 الحمل" if is_ar else "🤰 Pregnancy":                          "pregnancy",
                "🤱 الرضاعة" if is_ar else "🤱 Lactation":                        "lactation",
                "🫘 الفشل الكلوي — قبل الديلزة" if is_ar else "🫘 CKD Pre-dialysis": "ckd_predialysis",
                "🫘 الفشل الكلوي — غسيل" if is_ar else "🫘 CKD Hemodialysis":    "ckd_hemodialysis",
                "❤️ أمراض القلب" if is_ar else "❤️ Cardiovascular":             "cardiovascular",
                "🫀 تليف الكبد" if is_ar else "🫀 Liver Cirrhosis":             "liver_cirrhosis",
                "⚖️ السمنة" if is_ar else "⚖️ Obesity":                         "obesity",
                "🎗️ السرطان" if is_ar else "🎗️ Cancer":                         "cancer",
            }
            sel_cond = st.multiselect(
                f"{'اختر الحالة' if is_ar else 'Select condition'}",
                list(CONDITIONS_OPTS_P.keys())
            )
            if sel_cond:
                for lbl in sel_cond:
                    cond_key = CONDITIONS_OPTS_P[lbl]
                    if cond_key in CLINICAL_CONDITIONS:
                        cd = CLINICAL_CONDITIONS[cond_key]
                        st.markdown(f"""
                        <div style="background:#f8faff;border:1.5px solid #dbeafe;
                            border-right:4px solid #2563eb;border-radius:12px;
                            padding:14px 16px;margin-top:10px">
                            <div style="font-size:16px;font-weight:800;color:#1e3a8a;margin-bottom:8px">
                                {cd['icon']} {cd['name']}
                            </div>
                            <div style="font-size:14px;color:#374151;line-height:1.6;margin-bottom:10px">
                                {cd['overview']}
                            </div>
                            <div style="display:flex;gap:8px;flex-wrap:wrap">""", unsafe_allow_html=True)
                        macros_d = cd.get('macros', {})
                        lmap = {
                            'energy':'🔥 سعرات' if is_ar else '🔥 Energy',
                            'protein':'💪 بروتين' if is_ar else '💪 Protein',
                            'carb':'🍞 كارب' if is_ar else '🍞 Carbs',
                            'fat':'🥑 دهون' if is_ar else '🥑 Fat',
                            'fiber':'🌾 ألياف' if is_ar else '🌾 Fiber',
                            'sodium':'🧂 صوديوم' if is_ar else '🧂 Sodium',
                        }
                        for mk, mv in list(macros_d.items())[:4]:
                            lbl_m = lmap.get(mk, mk)
                            st.markdown(f"""
                            <span style="background:#dbeafe;color:#1e40af;border:1px solid #93c5fd;
                                padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600;
                                display:inline-block;margin:2px">
                                {lbl_m}: {mv[:35]}
                            </span>""", unsafe_allow_html=True)
                        st.markdown("</div></div>", unsafe_allow_html=True)
                        if cd.get('key_points'):
                            st.markdown(f"<div style='margin-top:8px;font-size:13px;color:#374151'>", unsafe_allow_html=True)
                            for kp in cd['key_points'][:3]:
                                st.markdown(f"<div style='padding:3px 0;color:#374151;font-size:13px'>{kp}</div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)

        # ── Days ──
        days_lbl = "عدد الأيام" if is_ar else "Number of Days"
        days = st.number_input(days_lbl, 1, 14, 1)

        # ── Meals ──
        plan = {}; total_cal = total_p = total_c = total_f = 0
        food_opts = list(LOCAL_DB.keys())
        food_lbls = {k: f"{LOCAL_DB[k]['name']} ({LOCAL_DB[k]['cat']})" for k in food_opts}

        meals_labels = {
            "breakfast": ("🌅", "فطار" if is_ar else "Breakfast"),
            "lunch":     ("☀️", "غداء" if is_ar else "Lunch"),
            "dinner":    ("🌙", "عشاء" if is_ar else "Dinner"),
            "snack":     ("🍎", "سناك" if is_ar else "Snack"),
        }
        choose_lbl = "اختر" if is_ar else "Choose"
        day_lbl = "يوم" if is_ar else "Day"

        for d in range(days):
            with st.expander(f"📆 {day_lbl} {d+1}", expanded=(d==0)):
                plan[d] = {}
                cols = st.columns(2)
                for i, (mk, (mic, mlbl)) in enumerate(meals_labels.items()):
                    with cols[i % 2]:
                        st.markdown(f"""
                        <div style="font-size:16px;font-weight:700;color:#0f172a;
                            margin-bottom:8px;padding:8px 0;
                            border-bottom:1.5px solid #e2e8f0">
                            {mic} {mlbl}
                        </div>""", unsafe_allow_html=True)
                        foods = st.multiselect(
                            choose_lbl,
                            food_opts,
                            format_func=lambda k: food_lbls[k],
                            key=f"ms_{d}_{i}"
                        )
                        plan[d][mlbl] = {}
                        for fk in foods:
                            g_lbl = f"{LOCAL_DB[fk]['name']} ({'جم' if is_ar else 'g'})"
                            g = st.number_input(g_lbl, 0, 1000, 100, key=f"gi_{d}_{i}_{fk}")
                            if g > 0:
                                plan[d][mlbl][fk] = g
                                m = macros(fk, g)
                                total_cal += m["cal"]; total_p += m["p"]
                                total_c += m["c"];   total_f += m["f"]
                                # Macro badge
                                st.markdown(f"""
                                <div style="background:#f0f7ff;border-radius:8px;
                                    padding:6px 10px;margin:4px 0;font-size:13px;
                                    color:#1e3a8a;font-weight:600">
                                    🔥 {m['cal']} kcal &nbsp;
                                    💪 {m['p']}{gr} &nbsp;
                                    🍞 {m['c']}{gr} &nbsp;
                                    🥑 {m['f']}{gr}
                                </div>""", unsafe_allow_html=True)

        # ── Summary ──
        st.markdown("<hr>", unsafe_allow_html=True)
        sum_lbl  = "📊 ملخص الجدول" if is_ar else "📊 Plan Summary"
        st.markdown(f"<div style='font-size:18px;font-weight:800;color:#0f172a;margin-bottom:16px'>{sum_lbl}</div>", unsafe_allow_html=True)

        mc1, mc2 = st.columns(2)
        with mc1:
            labels = [
                (f"🔥 {'سعرات' if is_ar else 'Calories'}", int(total_cal), t['cal']*days, "prog-cal"),
                (f"💪 {'بروتين' if is_ar else 'Protein'}",  int(total_p),   t['p']*days,   "prog-p"),
                (f"🍞 {'كارب' if is_ar else 'Carbs'}",      int(total_c),   t['c']*days,   "prog-c"),
                (f"🥑 {'دهون' if is_ar else 'Fat'}",         int(total_f),   t['f']*days,   "prog-f"),
            ]
            for lbl, val, tgt, css in labels:
                pct = int(val/tgt*100) if tgt > 0 else 0
                st.markdown(f"""
                <div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:4px">
                    {lbl}: <span style="color:#2563eb">{val}</span>
                    <span style="color:#64748b;font-size:13px"> / {tgt} ({pct}%)</span>
                </div>""", unsafe_allow_html=True)
                st.markdown(prog(pct, css), unsafe_allow_html=True)

        with mc2:
            diff = total_cal - t['cal'] * days
            gap_lbl = "الفارق" if is_ar else "Gap"
            st.markdown(f"<div style='font-size:15px;font-weight:700;color:#0f172a;margin-bottom:10px'>{gap_lbl}: {diff_badge(diff)}</div>", unsafe_allow_html=True)
            if abs(diff) < 100:
                st.markdown(f"<div class='alert-success'>{'ممتاز! الجدول متوازن 🎯' if is_ar else 'Perfect! Balanced plan 🎯'}</div>", unsafe_allow_html=True)
            elif diff > 0:
                st.markdown(f"<div class='alert-warn'>{'زيادة' if is_ar else 'Over'} {int(diff)} kcal — {'قلل الكميات' if is_ar else 'reduce portions'}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='alert-warn'>{'ناقص' if is_ar else 'Under'} {int(abs(diff))} kcal — {'أضف وجبة' if is_ar else 'add a meal'}</div>", unsafe_allow_html=True)

        # ── Save ──
        st.markdown("<hr>", unsafe_allow_html=True)
        cn1, cn2 = st.columns(2)
        with cn1:
            pname = st.text_input(
                f"📝 {T('plan_name')}",
                value=f"{'جدول' if is_ar else 'Plan'} {datetime.now().strftime('%d/%m/%Y')}"
            )
        with cn2:
            ptype = st.selectbox(
                f"📁 {T('plan_type')}",
                [T('personal'), T('for_client'), T('public')]
            )
        if st.button(f"💾 {T('save_plan')}", use_container_width=True):
            c.execute("INSERT INTO saved_plans VALUES (NULL,?,?,?,datetime('now'),?)",
                      (u_id, pname, json.dumps({str(k):v for k,v in plan.items()}), ptype))
            conn.commit()
            st.success(f"✅ {T('saved_plan_ok')}")
            st.rerun()


    # ═══════════════ SUGGESTER ═══════════════
    elif st.session_state.page=="suggester":
        st.markdown("<div class='sec-title'>💡 مقترح الوجبات الذكي</div>",unsafe_allow_html=True)
        if not st.session_state.targets:
            st.warning("أكمل الإعدادات أولاً")
            if st.button("⚙️ الإعدادات"): st.session_state.page="profile_setup"; st.rerun()
            st.stop()
        t=st.session_state.targets
        st.markdown("<div class='alert-info'>أدخل ما أكلته اليوم — سنقترح الوجبات المتبقية.</div>",unsafe_allow_html=True)
        with st.form("eaten"):
            r1,r2,r3,r4=st.columns(4)
            ec=r1.number_input("🔥 سعرات",0,5000,0,50)
            ep=r2.number_input("💪 بروتين (ج)",0,500,0)
            ecc=r3.number_input("🍞 كارب (ج)",0,600,0)
            ef=r4.number_input("🥑 دهون (ج)",0,300,0)
            go=st.form_submit_button("💡 اقترح لي ←",use_container_width=True)
        if go:
            rem={"cal":max(0,t['cal']-ec),"p":max(0,t['p']-ep),"c":max(0,t['c']-ecc),"f":max(0,t['f']-ef)}
            r1,r2=st.columns(2)
            with r1:
                st.markdown("**✅ أكلته:**")
                for lb,vl in [("🔥",f"{ec} kcal"),("💪",f"{ep}ج"),("🍞",f"{ecc}ج"),("🥑",f"{ef}ج")]:
                    st.markdown(f"- {lb} {vl}")
            with r2:
                st.markdown("**🎯 المتبقي:**")
                for lb,vl in [("🔥",f"{rem['cal']} kcal"),("💪",f"{rem['p']}ج"),("🍞",f"{rem['c']}ج"),("🥑",f"{rem['f']}ج")]:
                    st.markdown(f"- {lb} {vl}")
            st.divider()
            if rem["cal"]<50:
                st.markdown("<div class='alert-success'>🎉 وصلت لهدفك اليومي!</div>",unsafe_allow_html=True)
            else:
                st.markdown("### 🍽️ وجبات مقترحة:")
                for s in smart_suggest(rem["cal"],rem["p"],rem["c"],rem["f"]):
                    m=s["macro"]
                    st.markdown(f"""<div class="sug-box">
                        <h4>🍴 {s['name']} — {s['grams']} جرام <span style="color:#6b7fa3;font-size:11px">{s['cat']}</span></h4>
                        <div class="pills">
                            <span class="pill pill-cal">🔥 {m['cal']} kcal</span>
                            <span class="pill pill-p">💪 {m['p']}ج</span>
                            <span class="pill pill-c">🍞 {m['c']}ج</span>
                            <span class="pill pill-f">🥑 {m['f']}ج</span>
                        </div>
                        <div class="fc-note">📋 {LOCAL_DB[s['key']]['note']}</div>
                    </div>""",unsafe_allow_html=True)

    # ═══════════════ SAVED ═══════════════
    elif st.session_state.page=="saved":
        st.markdown("<div class='sec-title'>💾 جداولي المحفوظة</div>",unsafe_allow_html=True)
        ft=st.selectbox("🔎 فلتر",["الكل","خاص بي","للعميل","عام"])
        q="SELECT id,plan_name,created_at,type FROM saved_plans WHERE user_id=?"
        p=[u_id]
        if ft!="الكل": q+=" AND type=?"; p.append(ft)
        c.execute(q,p); rows=c.fetchall()
        if not rows:
            st.markdown("<div class='alert-info'>لا توجد جداول محفوظة بعد.</div>",unsafe_allow_html=True)
        else:
            for pid,pname,pdate,ptype in rows:
                with st.expander(f"📋 {pname}  |  {ptype}  |  {str(pdate)[:10]}"):
                    c.execute("SELECT plan_data FROM saved_plans WHERE id=?",(pid,))
                    pd_raw=json.loads(c.fetchone()[0])
                    col1,col2=st.columns([3,1])
                    with col1:
                        for d,meals in pd_raw.items():
                            st.markdown(f"**📆 يوم {int(d)+1}**")
                            for m,foods in meals.items():
                                items=[f"{LOCAL_DB[k]['name']} ({v}ج)" for k,v in foods.items() if v>0 and k in LOCAL_DB]
                                if items: st.markdown(f"- {m}: "+"، ".join(items))
                    with col2:
                        if st.button("🛒 مشتريات",key=f"sh_{pid}"):
                            shop=shopping(pd_raw)
                            st.markdown("**قائمة المشتريات:**")
                            for k,v in shop.items():
                                if k in LOCAL_DB: st.markdown(f"- {LOCAL_DB[k]['name']}: **{v}ج**")
                        if st.session_state.confirm_del==pid:
                            st.warning("هل تحذف؟")
                            cc1,cc2=st.columns(2)
                            if cc1.button("✅ نعم",key=f"yes_{pid}"):
                                c.execute("DELETE FROM saved_plans WHERE id=?",(pid,)); conn.commit()
                                st.session_state.confirm_del=None; st.rerun()
                            if cc2.button("❌ إلغاء",key=f"no_{pid}"):
                                st.session_state.confirm_del=None; st.rerun()
                        else:
                            if st.button("🗑️ حذف",key=f"del_{pid}"):
                                st.session_state.confirm_del=pid; st.rerun()

    # ═══════════════ HISTORY ═══════════════
    elif st.session_state.page=="history":
        st.markdown("<div class='sec-title'>📈 سجل الوزن</div>",unsafe_allow_html=True)
        with st.form("wf"):
            wc1,_=st.columns([3,1])
            with wc1: w_in=st.number_input("⚖️ وزن اليوم (كجم)",30.0,300.0,70.0,.1)
            if st.form_submit_button("✅ تسجيل",use_container_width=True):
                c.execute("INSERT INTO tracking VALUES (NULL,?,?,datetime('now'))",(u_id,w_in))
                conn.commit(); st.success("تم!"); st.rerun()
        c.execute("SELECT date,weight FROM tracking WHERE user_id=? ORDER BY id ASC",(u_id,))
        data=c.fetchall()
        if data:
            weights=[d[1] for d in data]
            m1,m2,m3=st.columns(3)
            m1.metric("📉 أقل",f"{min(weights)} كجم")
            m2.metric("📈 أعلى",f"{max(weights)} كجم")
            m3.metric("📊 آخر",f"{weights[-1]} كجم",
                      delta=f"{round(weights[-1]-weights[0],1)} كجم" if len(weights)>1 else None)
            if st.session_state.targets and u[4]:
                bv,bcls,blbl=bmi_info(weights[-1],float(u[4]))
                st.markdown(f"<div class='alert-info'>📏 BMI: <b>{bv}</b> — <span class='bmi-badge {bcls}'>{blbl}</span></div>",unsafe_allow_html=True)
            st.line_chart({"الوزن (كجم)":weights})
        else:
            st.markdown("<div class='alert-info'>سجل وزنك اليوم!</div>",unsafe_allow_html=True)

    # ═══════════════ CLINICAL REFERENCE ═══════════════
    elif st.session_state.page=="clinical":
        st.markdown("<div class='sec-title'>📚 <span>المرجع الكلينيكي</span> والحسابات التغذوية</div>",unsafe_allow_html=True)
        st.markdown(
            "<div class='alert-info'>📖 مستخلص من: <b>Understanding Normal and Clinical Nutrition, 8th Ed</b> — Rolfes, Pinna & Whitney</div>",
            unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🧮 حاسبة التغذية الكلينيكية", "📋 المرجع التفصيلي"])

        # ─── TAB 1: Clinical Calculator ───
        with tab1:
            st.markdown("### 🧮 احسب الاحتياجات الغذائية حسب الحالة المرضية")
            st.markdown("<div class='alert-info'>أدخل بيانات المريض واختر الحالات — ستظهر الحسابات فوراً</div>",unsafe_allow_html=True)

            # Initialize defaults BEFORE form to avoid NameError
            cc_w=70.0; cc_h=165.0; cc_age=35; cc_sex="ذكر"
            cc_act=1.55; cc_trim="لا ينطبق"; cc_conds_lbl=[]; calc_btn=False
            CONDITIONS_OPTS={
                "🩸 السكري النوع الأول":"diabetes_t1",
                "🩸 السكري النوع الثاني":"diabetes_t2",
                "🤰 الحمل":"pregnancy",
                "🤱 الرضاعة":"lactation",
                "🫘 الفشل الكلوي — قبل الديلزة":"ckd_predialysis",
                "🫘 الفشل الكلوي — غسيل الكلى":"ckd_hemodialysis",
                "❤️ أمراض القلب / ضغط الدم":"cardiovascular",
                "🫀 تليف الكبد":"liver_cirrhosis",
                "⚖️ السمنة":"obesity",
                "🎗️ السرطان":"cancer",
                "🔥 حرقة المعدة (GERD)":"gerd",
                "🫃 القولون العصبي (IBS)":"ibs",
                "🔬 المتلازمة الأيضية":"metabolic_syndrome",
            }

            with st.form("clin_calc"):
                cr1,cr2,cr3=st.columns(3)
                with cr1:
                    cc_w=st.number_input("⚖️ الوزن (كجم)",20.0,300.0,70.0,0.5)
                    cc_h=st.number_input("📏 الطول (سم)",100.0,220.0,165.0,0.5)
                with cr2:
                    cc_age=st.number_input("📅 العمر",5,100,35)
                    cc_sex=st.selectbox("👤 الجنس",["ذكر","أنثى"])
                with cr3:
                    cc_act=st.selectbox("🏃 النشاط",[1.2,1.375,1.55,1.725,1.9],index=2,
                        format_func=lambda x:{1.2:"مستقر",1.375:"خفيف",1.55:"معتدل",1.725:"نشيط",1.9:"رياضي"}[x])
                    cc_trim=st.selectbox("🤰 ثلث الحمل (إن حاملاً)",["لا ينطبق","الأول","الثاني","الثالث"])
                cc_conds_lbl=st.multiselect("🏥 الحالات المرضية (يمكن اختيار أكثر من حالة)",list(CONDITIONS_OPTS.keys()))
                calc_btn=st.form_submit_button("🧮 احسب الاحتياجات ←",use_container_width=True)

            if calc_btn:
                cc_conds=[CONDITIONS_OPTS[l] for l in cc_conds_lbl]
                res=clinical_calc(cc_w,cc_h,cc_age,cc_sex,cc_conds,cc_act)

                # pregnancy trimester adjustment
                if "pregnancy" in cc_conds:
                    bonus={"الأول":0,"الثاني":340,"الثالث":452}.get(cc_trim,340)
                    res["cal"]=int(res["cal"]-340+bonus)

                st.markdown("---")
                st.markdown(f"### 📊 نتائج الحسابات لـ {u[3] if cc_w==float(u[5] or 0) else 'المريض'}")

                # Main macros
                col_r1,col_r2,col_r3,col_r4=st.columns(4)
                for col,ic,lb,val,un in [
                    (col_r1,"🔥","السعرات اليومية",res["cal"],"kcal"),
                    (col_r2,"💪","البروتين",res["p"],"جم/يوم"),
                    (col_r3,"🍞","الكارب",res["c"],"جم/يوم"),
                    (col_r4,"🥑","الدهون",res["f"],"جم/يوم"),
                ]:
                    col.markdown(f'<div class="card" style="text-align:center"><div class="c-icon">{ic}</div><div class="c-label">{lb}</div><div class="c-value">{val}</div><div class="c-unit">{un}</div></div>',unsafe_allow_html=True)

                st.markdown("<br>",unsafe_allow_html=True)

                # Extra info
                col_x1,col_x2,col_x3=st.columns(3)
                with col_x1:
                    bv,bcls,blbl=bmi_info(cc_w,cc_h)
                    st.markdown(f'<div class="card"><div class="c-label">📏 BMI</div><div class="c-value">{bv}</div><div class="bmi-badge {bcls}">{blbl}</div></div>',unsafe_allow_html=True)
                with col_x2:
                    ibw = 22 * (cc_h/100)**2
                    st.markdown(f'<div class="card" style="text-align:center"><div class="c-label">📐 الوزن المثالي</div><div class="c-value">{round(ibw,1)}</div><div class="c-unit">كجم (BMI 22)</div></div>',unsafe_allow_html=True)
                with col_x3:
                    st.markdown(f'<div class="card" style="text-align:center"><div class="c-label">⚡ TDEE</div><div class="c-value">{res["tdee"]}</div><div class="c-unit">kcal/يوم</div></div>',unsafe_allow_html=True)

                # Detailed macro breakdown
                st.markdown("#### ⚖️ تفاصيل الماكروز")
                st.markdown(f"""
                <div class="calc-box">
                    <h4>📐 الحسابات التفصيلية</h4>
                    <div class="clin-row"><span class="cr-label">BMR (معدل الأيض الأساسي)</span><br><span class="cr-val">{res['bmr']} kcal/يوم (Mifflin-St Jeor)</span></div>
                    <div class="clin-row"><span class="cr-label">TDEE (السعرات مع النشاط)</span><br><span class="cr-val">{res['tdee']} kcal/يوم</span></div>
                    <div class="clin-row clin-row-green"><span class="cr-label">السعرات المستهدفة</span><br><span class="cr-val">{res['cal']} kcal/يوم</span></div>
                    <div class="clin-row"><span class="cr-label">البروتين</span><br><span class="cr-val">{res['p']} جم/يوم = {res['p_g_kg']} جم/كجم = {res['p']*4} kcal ({round(res['p']*4/res['cal']*100)}%)</span></div>
                    <div class="clin-row"><span class="cr-label">الكارب</span><br><span class="cr-val">{res['c']} جم/يوم = {res['c']*4} kcal ({round(res['c']*4/res['cal']*100)}%)</span></div>
                    <div class="clin-row"><span class="cr-label">الدهون</span><br><span class="cr-val">{res['f']} جم/يوم = {res['f']*9} kcal ({round(res['f']*9/res['cal']*100)}%)</span></div>
                    <div class="clin-row clin-row-warn"><span class="cr-label">الألياف الموصى بها</span><br><span class="cr-val">{res['fiber']} جم/يوم</span></div>
                    <div class="clin-row clin-row-warn"><span class="cr-label">الصوديوم الأقصى</span><br><span class="cr-val">{res['sodium']:,} مجم/يوم</span></div>
                    {'<div class="clin-row clin-row-warn"><span class="cr-label">السوائل</span><br><span class="cr-val">' + (f"{res['fluid']:,} مل/يوم" if res['fluid']>0 else "غير مقيدة إذا كان البول طبيعياً") + '</span></div>' if res['fluid']!=0 else ''}
                </div>""",unsafe_allow_html=True)

                # Condition notes
                if res["notes"]:
                    st.markdown("#### 📌 تعديلات الحالات المرضية")
                    for n in res["notes"]:
                        st.markdown(f"<div class='alert-warn'>{n}</div>",unsafe_allow_html=True)

                # Micronutrient restrictions
                if res["restrictions"]:
                    st.markdown("#### 💊 مغذيات دقيقة مهمة لهذه الحالات")
                    cols_r=st.columns(min(len(res["restrictions"]),3))
                    for i,(rk,rv) in enumerate(res["restrictions"].items()):
                        cols_r[i%3].markdown(f"""
                        <div class="clin-row clin-row-green">
                            <span class="cr-label">{rk}</span><br>
                            <span class="cr-val">{rv}</span>
                        </div>""",unsafe_allow_html=True)

                # Meal distribution
                st.markdown("#### 🍽️ توزيع الوجبات المقترح")
                n_meals=6 if any(c in cc_conds for c in ["liver_cirrhosis","cancer","gerd","diabetes_t1"]) else 3
                cal_per=res["cal"]//n_meals
                p_per=res["p"]//n_meals
                st.markdown(f"""
                <div class="calc-box">
                    <h4>📅 {n_meals} وجبات يومياً × {cal_per} kcal لكل وجبة</h4>
                    {''.join([f'<div class="clin-row"><span class="cr-label">الوجبة {i+1}</span><span class="cr-val"> {cal_per} kcal | بروتين {p_per} جم</span></div>' for i in range(n_meals)])}
                </div>""",unsafe_allow_html=True)

        # ─── TAB 2: Reference ───
        with tab2:
            CONDITIONS_LIST={
                "🩸 السكري النوع الأول":"diabetes_t1","🩸 السكري النوع الثاني":"diabetes_t2",
                "🤰 الحمل":"pregnancy","🤱 الرضاعة الطبيعية":"lactation",
                "🫘 الفشل الكلوي — قبل الديلزة":"ckd_predialysis","🫘 الفشل الكلوي — غسيل الكلى":"ckd_hemodialysis",
                "❤️ أمراض القلب / ضغط الدم":"cardiovascular","🫀 تليف الكبد":"liver_cirrhosis",
                "⚖️ السمنة":"obesity","🎗️ السرطان":"cancer",
                "🔴 HIV/AIDS":"hiv_aids","🔥 GERD":"gerd","🫃 القولون العصبي (IBS)":"ibs",
                "🔬 المتلازمة الأيضية":"metabolic_syndrome",
            }
            search_ref=st.text_input("🔎 بحث في المرجع",placeholder="مثال: حديد، بوتاسيوم، سكر")
            selected_labels=st.multiselect("اختر حالة",list(CONDITIONS_LIST.keys()))

            if not selected_labels and not search_ref:
                cols3=st.columns(3)
                for i,(lbl,key) in enumerate(CONDITIONS_LIST.items()):
                    cond=CLINICAL_CONDITIONS[key]
                    cols3[i%3].markdown(f"""
                    <div class="card" style="text-align:center;padding:14px 10px;margin-bottom:10px;cursor:pointer">
                        <div style="font-size:26px">{cond['icon']}</div>
                        <div style="color:#1a2a4a;font-size:12px;font-weight:700;margin:5px 0 2px">{cond['name']}</div>
                        <div style="color:#6b7fa3;font-size:10px">{cond['chapter'][:28]}...</div>
                    </div>""",unsafe_allow_html=True)

            if search_ref:
                sq=search_ref.lower()
                st.markdown(f"### نتائج: '{search_ref}'")
                found=False
                for key,cond in CLINICAL_CONDITIONS.items():
                    if any(sq in str(v).lower() for v in [cond.get('overview',''),cond.get('key_points',''),cond.get('macros','')]):
                        found=True
                        st.markdown(f"""<div class="sug-box"><h4>{cond['icon']} {cond['name']}</h4>
                        <div style="color:#6b7fa3;font-size:12px">{cond['chapter']}</div>
                        <div class="fc-note">{cond['overview'][:280]}...</div></div>""",unsafe_allow_html=True)
                if not found: st.markdown("<div class='alert-warn'>لا نتائج. جرب كلمة مختلفة.</div>",unsafe_allow_html=True)

            for lbl in selected_labels:
                key=CONDITIONS_LIST[lbl]
                cond=CLINICAL_CONDITIONS[key]
                st.markdown("---")
                st.markdown(f"## {cond['icon']} {cond['name']}")
                st.markdown(f"<div style='color:#6b7fa3;font-size:12px;margin-bottom:10px'>📖 {cond['chapter']}</div>",unsafe_allow_html=True)
                st.markdown(f"<div class='fc-note'>📋 {cond['overview']}</div>",unsafe_allow_html=True)
                st.markdown("<br>",unsafe_allow_html=True)

                if cond.get('goals'):
                    st.markdown("#### 🎯 أهداف العلاج الغذائي")
                    for g in cond['goals']: st.markdown(f"- {g}")

                if cond.get('macros'):
                    st.markdown("#### ⚖️ التوصيات الكمية")
                    items=list(cond['macros'].items()); half=(len(items)+1)//2
                    mc1,mc2=st.columns(2)
                    LMAP={"energy":"🔥 السعرات","carb":"🍞 الكارب","protein":"💪 البروتين",
                          "fat":"🥑 الدهون","fiber":"🌾 الألياف","sodium":"🧂 الصوديوم",
                          "potassium":"⚡ البوتاسيوم","phosphorus":"🔵 الفوسفور",
                          "calcium":"🦴 الكالسيوم","fluid":"💧 السوائل","omega3":"🐟 أوميغا 3","zinc":"🔩 الزنك"}
                    with mc1:
                        for k,v in items[:half]:
                            st.markdown(f'<div class="clin-row"><span class="cr-label">{LMAP.get(k,k)}</span><br><span class="cr-val">{v}</span></div>',unsafe_allow_html=True)
                    with mc2:
                        for k,v in items[half:]:
                            st.markdown(f'<div class="clin-row"><span class="cr-label">{LMAP.get(k,k)}</span><br><span class="cr-val">{v}</span></div>',unsafe_allow_html=True)

                if cond.get('key_micronutrients'):
                    st.markdown("#### 💊 مغذيات دقيقة حرجة")
                    for km,kv in cond['key_micronutrients'].items():
                        st.markdown(f'<div class="clin-row clin-row-warn"><span class="cr-label">{km.replace("_"," ").title()}</span><br><span class="cr-val">{kv}</span></div>',unsafe_allow_html=True)

                if cond.get('key_points'):
                    st.markdown("#### 🔑 نقاط سريرية رئيسية")
                    for kp in cond['key_points']:
                        st.markdown(f'<div class="food-card" style="padding:9px 13px;margin-bottom:5px"><span style="color:#374151;font-size:13px">{kp}</span></div>',unsafe_allow_html=True)

                fa,fb=st.columns(2)
                with fa:
                    if cond.get('foods_recommended'):
                        st.markdown("#### ✅ أطعمة مُشجَّعة")
                        for f in cond['foods_recommended']:
                            st.markdown(f"<div style='color:#15803d;font-size:13px;padding:2px 0'>✔ {f}</div>",unsafe_allow_html=True)
                with fb:
                    if cond.get('foods_limit'):
                        st.markdown("#### ⛔ أطعمة تُقلَّل")
                        for f in cond['foods_limit']:
                            st.markdown(f"<div style='color:#b91c1c;font-size:13px;padding:2px 0'>✖ {f}</div>",unsafe_allow_html=True)

                if cond.get('weight_gain_guide'):
                    st.markdown("#### ⚖️ الزيادة الوزنية حسب BMI (الحمل)")
                    for br,rec in cond['weight_gain_guide'].items():
                        st.markdown(f'<div class="clin-row clin-row-green"><span class="cr-label">{br}</span><br><span class="cr-val">{rec}</span></div>',unsafe_allow_html=True)

                if cond.get('dash_diet'):
                    dd=cond['dash_diet']
                    st.markdown(f"<div class='alert-info'>🥗 حمية DASH — صوديوم {dd['sodium']}</div>",unsafe_allow_html=True)

                if cond.get('high_fodmap_foods'):
                    fi1,fi2=st.columns(2)
                    with fi1:
                        st.markdown("**🔴 High-FODMAP (تجنب)**")
                        for f in cond['high_fodmap_foods']: st.markdown(f"<div style='color:#b91c1c;font-size:13px'>✖ {f}</div>",unsafe_allow_html=True)
                    with fi2:
                        st.markdown("**🟢 Low-FODMAP (مسموح)**")
                        for f in cond['low_fodmap_foods']: st.markdown(f"<div style='color:#15803d;font-size:13px'>✔ {f}</div>",unsafe_allow_html=True)

                if cond.get('high_phosphorus_foods'):
                    rp1,rp2=st.columns(2)
                    with rp1:
                        st.markdown("**🔵 عالية الفوسفور (تحكم)**")
                        for f in cond['high_phosphorus_foods']: st.markdown(f"<div style='color:#b56b00;font-size:13px'>⚠ {f}</div>",unsafe_allow_html=True)
                    with rp2:
                        if cond.get('high_potassium_foods'):
                            st.markdown("**⚡ عالية البوتاسيوم (تحكم)**")
                            for f in cond['high_potassium_foods']: st.markdown(f"<div style='color:#b56b00;font-size:13px'>⚠ {f}</div>",unsafe_allow_html=True)

                if cond.get('meal_timing'): st.markdown(f"<div class='alert-info'>⏰ {cond['meal_timing']}</div>",unsafe_allow_html=True)
                if cond.get('monitoring'): st.markdown(f"<div class='alert-warn'>📊 {cond['monitoring']}</div>",unsafe_allow_html=True)
                st.markdown(f"<div style='background:#f8faff;border:1px solid #e2ecff;border-radius:8px;padding:8px 12px;margin-top:12px'><span style='color:#6b7fa3;font-size:11px'>📚 {cond['reference']}</span></div>",unsafe_allow_html=True)

    # ═══════════════ ADMIN — مولّد الجداول الغذائية ═══════════════
    elif st.session_state.page=="admin" and u[9]==1:
        import os, tempfile

        st.markdown("""
        <div class='sec-title'>
            <span style='color:#1a3a6b'>👑 لوحة الأدمن</span>
            <span style='font-size:14px;color:#64748b;font-weight:400'> — مولّد الجدول الغذائي الأسبوعي</span>
        </div>""", unsafe_allow_html=True)

        with st.form("admin_form"):
            st.markdown("<div style='font-size:15px;font-weight:800;color:#1e3a8a;margin-bottom:12px'>📋 بيانات المريض</div>", unsafe_allow_html=True)
            col1,col2,col3=st.columns(3)
            with col1:
                pt_name   = st.text_input("👤 اسم المريض")
                pt_age    = st.number_input("📅 العمر",10,90,30)
            with col2:
                pt_gender = st.selectbox("👤 الجنس",["ذكر","أنثى"])
                pt_height = st.number_input("📏 الطول (سم)",130.0,220.0,165.0,0.5)
            with col3:
                pt_weight = st.number_input("⚖️ الوزن (كجم)",30.0,250.0,80.0,0.1)
                pt_fat    = st.number_input("📊 نسبة الدهون %",0.0,70.0,30.0,0.1)
            col4,col5,col6=st.columns(3)
            with col4:
                pt_visceral=st.number_input("🔴 دهون البطن",0.0,30.0,10.0,0.1)
                pt_muscle  =st.number_input("💪 نسبة العضلات %",0.0,60.0,35.0,0.1)
            with col5:
                pt_water=st.number_input("💧 نسبة الماء %",0.0,70.0,50.0,0.1)
                pt_bone =st.number_input("🦴 كتافة العظام (كجم)",0.0,10.0,3.0,0.05)
            with col6:
                pt_bmi =st.number_input("📐 BMI",10.0,60.0,25.0,0.1)
                pt_tdee=st.number_input("🔥 TDEE (kcal/يوم)",1000,5000,2000,50)

            st.markdown("<div style='font-size:15px;font-weight:700;color:#1e3a8a;margin:14px 0 8px'>🏥 الأعراض والحالات المرضية</div>", unsafe_allow_html=True)
            SYMPTOMS_LIST=["قولون عصبي","إمساك مزمن","حرق بطيء","سمنة",
                           "سكري النوع الثاني","سكري النوع الأول","ضغط الدم",
                           "أمراض القلب","الفشل الكلوي","تليف الكبد",
                           "حمل","رضاعة","نحافة وضعف شهية","GERD / حرقة معدة"]
            cols_s=st.columns(4); selected_symptoms=[]
            for i,symp in enumerate(SYMPTOMS_LIST):
                with cols_s[i%4]:
                    if st.checkbox(symp,key=f"symp_{i}"): selected_symptoms.append(symp)

            cg1,cg2=st.columns(2)
            with cg1: pt_goal_cal=st.number_input("🎯 السعرات المستهدفة (kcal)",800,3000,max(1000,int(pt_tdee*0.55)),50)
            with cg2: pt_notes=st.text_area("📝 ملاحظات إضافية",height=80,placeholder="ملاحظات سريرية...")
            gen_btn=st.form_submit_button("🚀 توليد الجدول الغذائي وتحميل PDF",use_container_width=True)

        if gen_btn:
            if not pt_name.strip():
                st.error("أدخل اسم المريض أولاً!")
            else:
                with st.spinner("⏳ جاري توليد الجدول الغذائي..."):
                    try:
                        # ── Inline PDF generation (no external files) ──
                        from reportlab.lib.pagesizes import A4
                        from reportlab.lib import colors as rlcolors
                        from reportlab.lib.units import cm
                        from reportlab.platypus import (SimpleDocTemplate, Paragraph,
                            Spacer, Table, TableStyle, HRFlowable, PageBreak)
                        from reportlab.lib.styles import ParagraphStyle
                        from reportlab.pdfbase import pdfmetrics
                        from reportlab.pdfbase.ttfonts import TTFont
                        from reportlab.lib.enums import TA_RIGHT, TA_CENTER
                        import arabic_reshaper
                        from bidi.algorithm import get_display

                        # ── Find font ──
                        def _find_font(fname):
                            # Look next to app.py first (GitHub repo)
                            app_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
                            candidates = [
                                os.path.join(app_dir, fname),
                                os.path.join(os.getcwd(), fname),
                                f"/usr/share/fonts/opentype/fonts-hosny-amiri/{fname}",
                                f"/usr/share/fonts/truetype/amiri/{fname}",
                                os.path.join(tempfile.gettempdir(), fname),
                            ]
                            for p in candidates:
                                if os.path.exists(p):
                                    return p
                            raise FileNotFoundError(
                                f"Font '{fname}' not found!\n"
                                "Please upload Amiri-Regular.ttf and Amiri-Bold.ttf "
                                "to your GitHub repo alongside app.py"
                            )

                        try:
                            pdfmetrics.registerFont(TTFont("Amiri",     _find_font("Amiri-Regular.ttf")))
                            pdfmetrics.registerFont(TTFont("AmiriBold", _find_font("Amiri-Bold.ttf")))
                        except Exception as fe:
                            st.error(f"❌ الـ Font مش موجود: {fe}")
                            st.info("📌 ارفع ملفات Amiri-Regular.ttf و Amiri-Bold.ttf على GitHub في نفس مجلد app.py")
                            st.stop()

                        def ar(t):
                            try: return get_display(arabic_reshaper.reshape(str(t)))
                            except: return str(t)

                        def S(size=11, bold=False, color=None, align=TA_RIGHT):
                            return ParagraphStyle("s",
                                fontName="AmiriBold" if bold else "Amiri",
                                fontSize=size, textColor=color or rlcolors.HexColor("#222222"),
                                alignment=align, spaceAfter=4, leading=size*1.5,
                                rightIndent=3, leftIndent=3)

                        CB = rlcolors.HexColor("#1a3a6b")
                        CG = rlcolors.HexColor("#1a5c3a")
                        CR = rlcolors.HexColor("#8b0000")
                        CO = rlcolors.HexColor("#b34700")
                        LB = rlcolors.HexColor("#dce8f5")
                        LG = rlcolors.HexColor("#e8f5ec")
                        LO = rlcolors.HexColor("#fef3e2")
                        GR = rlcolors.HexColor("#f5f5f5")
                        bd = {"style":0.4,"color":rlcolors.HexColor("#cccccc")}

                        def cell_row(items, hdr_bg=CB, row_bgs=(rlcolors.white, GR), col_ws=None):
                            rows=[]
                            for ri,row in enumerate(items):
                                rows.append([Paragraph(ar(c), S(10, ri==0,
                                    rlcolors.white if ri==0 else rlcolors.HexColor("#111111")))
                                    for c in row])
                            t=Table(rows, colWidths=col_ws or [17.4*cm/len(items[0])]*len(items[0]))
                            ts=[("FONTNAME",(0,0),(-1,-1),"Amiri"),
                                ("FONTNAME",(0,0),(-1,0),"AmiriBold"),
                                ("FONTSIZE",(0,0),(-1,-1),10),
                                ("ALIGN",(0,0),(-1,-1),"RIGHT"),
                                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                                ("BACKGROUND",(0,0),(-1,0),hdr_bg),
                                ("TEXTCOLOR",(0,0),(-1,0),rlcolors.white),
                                ("ROWBACKGROUNDS",(0,1),(-1,-1),list(row_bgs)),
                                ("GRID",(0,0),(-1,-1),0.4,rlcolors.HexColor("#cccccc")),
                                ("TOPPADDING",(0,0),(-1,-1),5),
                                ("BOTTOMPADDING",(0,0),(-1,-1),5),
                                ("RIGHTPADDING",(0,0),(-1,-1),6),
                                ("LEFTPADDING",(0,0),(-1,-1),6)]
                            t.setStyle(TableStyle(ts)); return t

                        # ── Meal plan data ──
                        symptoms = selected_symptoms
                        has_colon = any(s in symptoms for s in ["قولون عصبي"])
                        breakfasts=[
                            ["فطار","فول مدمس بزيت الزيتون","200 جم","220","8","ألياف + أوميغا 3"],
                            ["فطار","شوفان بالحليب + موز","6 ملاعق","280","10","بيتا جلوكان يهدئ القولون"],
                            ["فطار","بيض أومليت بالخضار","3 بيضات","250","18","بروتين يرفع الحرق"],
                            ["فطار","فول مع طحينة وليمون","200 جم","290","11","كالسيوم + دهون صحية"],
                            ["فطار","شوفان بالموز والقرفة","6 ملاعق","310","9","قرفة تنظم السكر"],
                            ["فطار","فول + بيضتان مسلوقتان","200 جم + 2 بيض","376","20","وجبة مصرية متكاملة"],
                            ["فطار","شوفان بالكيوي واللوز","6 ملاعق","310","10","مضادات أكسدة + ألياف"],
                        ]
                        lunches=[
                            ["غداء","صدر دجاج مشوي + أرز بني + سلطة","150 جم + 4 ملاعق","378","49","بروتين يرفع الحرق"],
                            ["غداء","سمك بلطي مشوي + بطاطا حلوة","200 جم + حبة","321","42","أوميغا 3 يقلل الالتهاب"],
                            ["غداء","فخذ دجاج فرن + برغل + سلطة فتوش","200 جم + 4 ملاعق","450","42","متنوع وغني"],
                            ["غداء","كبدة دجاج + أرز بني + ملوخية","150 جم + 4 ملاعق","389","33","أغنى مصدر للحديد"],
                            ["غداء","سمكة بلطي كاملة + بطاطا مسلوقة","250 جم + 150 جم","356","52","بروتين عالي جداً"],
                            ["غداء","صدر دجاج فرن + خضار مشوية","180 جم + 200 جم","350","52","وجبة مثالية للحرق"],
                            ["غداء","كبسة دجاج بالأرز البني (بدون جلد)","قطعة + أرز","380","38","وجبة اجتماعية صحية"],
                        ]
                        dinners=[
                            ["عشاء","شوربة عدس أحمر + خبز أسمر","طبق + شريحة","250","12","ألياف قابلة للذوبان"],
                            ["عشاء","عدس مطهو بجزر وكرفس + خبز","طبق + شريحة","270","13","بروتين نباتي + ألياف"],
                            ["عشاء","شوربة خضار + جبن قريش","طبق + 50 جم","199","10","خفيف يريح القولون"],
                            ["عشاء","حمص بطحينة + خبز أسمر","150 جم + شريحة","320","13","بروتين نباتي"],
                            ["عشاء","شوربة عدس أصفر + خبز","طبق + شريحة","250","12","ألياف + بروتين"],
                            ["عشاء","عدس مع جزر + جبن قريش","طبق + 50 جم","249","16","وجبة متكاملة"],
                            ["عشاء","كشري مصري (كمية معتدلة)","طبق صغير","280","12","عدس + أرز = بروتين كامل"],
                        ]
                        snacks=["تفاحة بالقشر (80 kcal)","لوز نيئ 20 جم (120 kcal)",
                                "برتقالة (62 kcal)","تمرتان (66 kcal)",
                                "كيوي (61 kcal)","رمانة نصف (53 kcal)","موزة صغيرة (89 kcal)"]
                        sleep=["زبادي يوناني سادة (89 kcal)","كمثرى (101 kcal)",
                               "حليب دافئ خالي الدسم (70 kcal)","زبادي يوناني (89 kcal)",
                               "تفاحة بالقشر (80 kcal)","زبادي يوناني (89 kcal)","موزة صغيرة (89 kcal)"]
                        days_ar=["الأحد","الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت"]

                        # ── Build PDF ──
                        tmp=tempfile.NamedTemporaryFile(suffix=".pdf",delete=False)
                        doc=SimpleDocTemplate(tmp.name, pagesize=A4,
                            rightMargin=1.8*cm, leftMargin=1.8*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
                        story=[]

                        # Cover
                        story.append(Spacer(1,16))
                        story.append(Paragraph(ar("NutraX — النظام الغذائي الأسبوعي"),S(22,True,CB,TA_CENTER)))
                        story.append(Spacer(1,6))
                        story.append(HRFlowable(width="100%",thickness=2,color=CB,spaceAfter=8,spaceBefore=8))

                        # Patient info
                        bmi_cat="سمنة" if pt_bmi>=30 else "زيادة وزن" if pt_bmi>=25 else "طبيعي" if pt_bmi>=18.5 else "نحافة"
                        pat=[["الاسم",pt_name,"العمر",f"{pt_age} سنة","الجنس",pt_gender],
                             ["الطول",f"{pt_height} سم","الوزن",f"{pt_weight} كجم","BMI",f"{pt_bmi} ({bmi_cat})"],
                             ["نسبة الدهون",f"{pt_fat}%","TDEE",f"{pt_tdee} kcal","الهدف اليومي",f"{pt_goal_cal} kcal"]]
                        pt_rows=[]
                        for row in pat:
                            pt_rows.append([Paragraph(ar(c),S(10,i%2==0,CB if i%2==0 else rlcolors.HexColor("#111111")))
                                           for i,c in enumerate(row)])
                        pt_t=Table(pt_rows,colWidths=[2.3*cm,2.9*cm,2.3*cm,2.9*cm,2.3*cm,2.9*cm])
                        pt_t.setStyle(TableStyle([
                            ("FONTNAME",(0,0),(-1,-1),"Amiri"),("FONTSIZE",(0,0),(-1,-1),10),
                            ("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                            ("BACKGROUND",(0,0),(0,-1),LB),("BACKGROUND",(2,0),(2,-1),LB),
                            ("BACKGROUND",(4,0),(4,-1),LB),
                            ("TEXTCOLOR",(0,0),(0,-1),CB),("TEXTCOLOR",(2,0),(2,-1),CB),("TEXTCOLOR",(4,0),(4,-1),CB),
                            ("GRID",(0,0),(-1,-1),0.5,rlcolors.HexColor("#aaaaaa")),
                            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
                            ("ROWBACKGROUNDS",(0,0),(-1,-1),[rlcolors.white,GR])]))
                        story.append(pt_t); story.append(Spacer(1,8))

                        if symptoms:
                            story.append(Paragraph(ar(f"الأعراض: {'  |  '.join(symptoms)}"),S(11,False,CR)))
                        if pt_notes.strip():
                            story.append(Paragraph(ar(f"ملاحظات: {pt_notes}"),S(10)))
                        story.append(HRFlowable(width="100%",thickness=1.5,color=CG,spaceAfter=6,spaceBefore=6))
                        story.append(PageBreak())

                        # Rules
                        story.append(Paragraph(ar("المسموح والممنوع"),S(15,True,CB)))
                        story.append(Spacer(1,6))
                        allowed=["فول مدمس • عدس • شوربات • سمك مشوي",
                                 "دجاج مشوي أو فرن (بدون جلد) • بيض",
                                 "شوفان • خبز أسمر • أرز بني • برغل",
                                 "زيت زيتون • طحينة بكميات صغيرة",
                                 "زبادي يوناني سادة • جبن قريش • لبن رايب",
                                 "ملوخية • كوسة • جزر • خضار مطبوخة",
                                 "شاي أخضر • ماء دافئ بالليمون صباحاً"]
                        forbidden=["الخبز الأبيض والعيش الفينو",
                                   "البهارات الحارة — تستفز القولون",
                                   "الدهانة والسمن والأكل المقلي",
                                   "المشروبات الغازية والعصائر المعلبة",
                                   "الكافيين الزائد (أكثر من كوب يومياً)",
                                   "البقوليات بكميات كبيرة دفعة واحدة",
                                   "الحلويات والسكريات المضافة"]
                        r_rows=[[ar("✅ مسموح — بحرية"),ar("🚫 ممنوع أو مقلل")]]
                        for a,f in zip(allowed,forbidden): r_rows.append([ar(a),ar(f)])
                        r_t=Table([[Paragraph(c,S(10,ri==0,
                            CG if ri==0 and ci==0 else CR if ri==0 and ci==1
                            else rlcolors.HexColor("#166534") if ci==0
                            else rlcolors.HexColor("#991b1b")))
                            for ci,c in enumerate(row)] for ri,row in enumerate(r_rows)],
                            colWidths=[8.7*cm,8.7*cm])
                        r_t.setStyle(TableStyle([
                            ("FONTNAME",(0,0),(-1,-1),"Amiri"),("FONTSIZE",(0,0),(-1,-1),10),
                            ("ALIGN",(0,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                            ("BACKGROUND",(0,0),(0,0),CG),("BACKGROUND",(1,0),(1,0),CR),
                            ("ROWBACKGROUNDS",(0,1),(-1,-1),[LG,rlcolors.white]),
                            ("GRID",(0,0),(-1,-1),0.4,rlcolors.HexColor("#cccccc")),
                            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                            ("RIGHTPADDING",(0,0),(-1,-1),7),("LEFTPADDING",(0,0),(-1,-1),7)]))
                        story.append(r_t); story.append(PageBreak())

                        # Weekly plan
                        story.append(Paragraph(ar("الجدول الغذائي الأسبوعي التفصيلي"),S(15,True,CB)))
                        story.append(Spacer(1,8))

                        for di in range(7):
                            story.append(Paragraph(ar(f"اليوم {di+1} — {days_ar[di]}"),S(13,True,CG)))
                            day_rows=[["الوجبة","الأكل","الكمية","kcal","بروتين","ملاحظة"]]
                            total_cal=0; total_p=0
                            # breakfast
                            br=breakfasts[di]
                            day_rows.append(["🌅 "+br[0],br[1],br[2],br[3],br[4],br[5]])
                            total_cal+=int(br[3]); total_p+=int(br[4])
                            # snack
                            day_rows.append(["🍎 سناك",snacks[di],"","","","فاكهة طبيعية"])
                            # lunch
                            lu=lunches[di]
                            day_rows.append(["☀️ "+lu[0],lu[1],lu[2],lu[3],lu[4],lu[5]])
                            total_cal+=int(lu[3]); total_p+=int(lu[4])
                            # dinner
                            dn=dinners[di]
                            day_rows.append(["🌙 "+dn[0],dn[1],dn[2],dn[3],dn[4],dn[5]])
                            total_cal+=int(dn[3]); total_p+=int(dn[4])
                            # before sleep
                            day_rows.append(["🌛 قبل النوم",sleep[di],"","","","بروبيوتيك ليلي"])
                            # total
                            day_rows.append(["الإجمالي","","",str(total_cal)+f" kcal",f"{total_p}ج",""])

                            cw=[1.9*cm,3.8*cm,2.5*cm,1.8*cm,1.5*cm,5.9*cm]
                            m_t=Table([[Paragraph(ar(c),S(9.5,ri==0 or ri==len(day_rows)-1,
                                CB if ri==0 else LB if ri==len(day_rows)-1 else None))
                                for ci,c in enumerate(row)]
                                for ri,row in enumerate(day_rows)], colWidths=cw)
                            m_t.setStyle(TableStyle([
                                ("FONTNAME",(0,0),(-1,-1),"Amiri"),("FONTSIZE",(0,0),(-1,-1),9.5),
                                ("ALIGN",(0,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                                ("BACKGROUND",(0,0),(-1,0),CB),("TEXTCOLOR",(0,0),(-1,0),rlcolors.white),
                                ("BACKGROUND",(0,-1),(-1,-1),LB),
                                ("ROWBACKGROUNDS",(0,1),(-1,-2),[rlcolors.white,GR]),
                                ("GRID",(0,0),(-1,-1),0.4,rlcolors.HexColor("#cccccc")),
                                ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
                                ("RIGHTPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(0,0),(-1,-1),5)]))
                            story.append(m_t); story.append(Spacer(1,8))
                            if di<6: story.append(HRFlowable(width="100%",thickness=0.5,
                                color=rlcolors.HexColor("#dddddd"),spaceAfter=4,spaceBefore=4))

                        story.append(PageBreak())

                        # Protocols
                        story.append(Paragraph(ar("بروتوكول القولون والإمساك"),S(14,True,CR)))
                        story.append(Spacer(1,4))
                        gut=["زبادي يوناني سادة كل ليلة — بروبيوتيك يصلح البكتيريا",
                             "تفاحة أو كمثرى بالقشر يومياً — بيكتين يلين الأمعاء",
                             "كمون + شبت في الطهي — يقلل الغازات ويهدئ القولون",
                             "شاي النعنع بعد الغداء — مضاد تشنج طبيعي",
                             "المضغ الجيد يقلل 50% من مشاكل القولون",
                             "لا تشرب ماء بارد جداً مع الأكل",
                             "ملعقة بذور الكتان المطحونة في الزبادي إذا استمر الإمساك"]
                        gut_rows=[[ar("بروتوكول القولون والإمساك")]]+[[ar(f"• {g}")] for g in gut]
                        g_t=Table([[Paragraph(c,S(10,ri==0,rlcolors.white if ri==0 else rlcolors.HexColor("#7f1d1d")))
                            for c in row] for ri,row in enumerate(gut_rows)],colWidths=[17.4*cm])
                        g_t.setStyle(TableStyle([
                            ("FONTNAME",(0,0),(-1,-1),"Amiri"),("FONTSIZE",(0,0),(-1,-1),10),
                            ("ALIGN",(0,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                            ("BACKGROUND",(0,0),(0,0),CR),
                            ("ROWBACKGROUNDS",(0,1),(-1,-1),[rlcolors.HexColor("#ffeef0"),rlcolors.white]),
                            ("GRID",(0,0),(-1,-1),0.4,rlcolors.HexColor("#cccccc")),
                            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                            ("RIGHTPADDING",(0,0),(-1,-1),8)]))
                        story.append(g_t); story.append(Spacer(1,10))

                        story.append(Paragraph(ar("رفع معدل الحرق"),S(14,True,CO)))
                        met=["وجبة الصباح إلزامية خلال ساعة — إغلاقها يخفض الحرق 20%",
                             "البروتين في كل وجبة — هضمه يحرق 25% من سعراته",
                             "كركم + قرفة + زنجبيل في الطهي — يرفعون الحرق 10%",
                             "الشاي الأخضر كوب يومياً — يرفع الحرق 4-6%",
                             "8 أكواب ماء يومياً — الجفاف يبطئ الحرق 30%",
                             "مشي 30 دقيقة بعد الغداء — الأفضل لحرق الدهون"]
                        met_rows=[[ar("رفع معدل الحرق")]]+[[ar(f"• {m}")] for m in met]
                        m_t2=Table([[Paragraph(c,S(10,ri==0,rlcolors.white if ri==0 else rlcolors.HexColor("#92400e")))
                            for c in row] for ri,row in enumerate(met_rows)],colWidths=[17.4*cm])
                        m_t2.setStyle(TableStyle([
                            ("FONTNAME",(0,0),(-1,-1),"Amiri"),("FONTSIZE",(0,0),(-1,-1),10),
                            ("ALIGN",(0,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                            ("BACKGROUND",(0,0),(0,0),CO),
                            ("ROWBACKGROUNDS",(0,1),(-1,-1),[LO,rlcolors.white]),
                            ("GRID",(0,0),(-1,-1),0.4,rlcolors.HexColor("#cccccc")),
                            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                            ("RIGHTPADDING",(0,0),(-1,-1),8)]))
                        story.append(m_t2); story.append(Spacer(1,10))

                        # Footer
                        story.append(HRFlowable(width="100%",thickness=1.5,color=CB,spaceAfter=6,spaceBefore=6))
                        story.append(Paragraph(
                            ar(f"NutraX | معد لـ {pt_name} | {datetime.now().strftime('%d/%m/%Y')} | يراجع بعد 4 أسابيع"),
                            S(10,False,rlcolors.HexColor("#888888"),TA_CENTER)))

                        doc.build(story)

                        with open(tmp.name,"rb") as f: pdf_bytes=f.read()
                        os.unlink(tmp.name)

                        # ── Results ──
                        st.markdown(f"<div class='alert-success'>✅ تم توليد الجدول الغذائي لـ <b>{pt_name}</b> بنجاح!</div>",
                            unsafe_allow_html=True)
                        weekly_loss=round((pt_tdee-pt_goal_cal)*7/7700,2)
                        s1,s2,s3=st.columns(3)
                        s1.metric("BMI",f"{pt_bmi}",bmi_cat)
                        s2.metric("العجز اليومي",f"{pt_tdee-pt_goal_cal} kcal")
                        s3.metric("خسارة متوقعة/أسبوع",f"{weekly_loss} كجم")
                        st.download_button(
                            "⬇️ تحميل PDF الجدول الغذائي",
                            data=pdf_bytes,
                            file_name=f"NutraX_{pt_name.replace(' ','_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True)

                    except Exception as e:
                        st.error(f"خطأ في توليد الـ PDF: {str(e)}")
                        st.code(str(e))

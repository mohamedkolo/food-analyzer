import streamlit as st
import requests
from datetime import datetime

# ===========================================================================
# إعدادات الصفحة
# ===========================================================================
st.set_page_config(
    page_title="DNP — التغذية الذكية",
    page_icon="🥗",
    layout="centered",
)

# ===========================================================================
# CSS
# ===========================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
    }
    .main { background-color: #f8f9fa; }
    .block-container { padding: 1rem 1rem 2rem; max-width: 800px; }
    h1 { color: #2e7d32; text-align: center; }
    .metric-card {
        background: white; border-radius: 12px; padding: 14px 18px;
        margin: 6px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        display: flex; justify-content: space-between; align-items: center;
    }
    .badge-rich  { background:#e8f5e9; color:#2e7d32; border-radius:8px; padding:2px 10px; font-size:0.8em; }
    .badge-mid   { background:#fff8e1; color:#f57f17; border-radius:8px; padding:2px 10px; font-size:0.8em; }
    .badge-low   { background:#fce4ec; color:#c62828; border-radius:8px; padding:2px 10px; font-size:0.8em; }
    .section-title {
        font-size: 1.05em; font-weight: 700; color: #1b5e20;
        border-right: 4px solid #4caf50; padding-right: 10px;
        margin: 18px 0 8px;
    }
    .note-card {
        background: #e3f2fd; border-radius: 10px;
        padding: 10px 14px; margin: 4px 0; font-size: 0.9em; color: #0d47a1;
    }
    .bmi-card {
        border-radius: 16px; padding: 20px; text-align: center;
        font-size: 2em; font-weight: 700; margin: 10px 0;
    }
    .result-box {
        background: white; border-radius: 14px; padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.10); margin: 10px 0;
        text-align: center;
    }
    .stProgress > div > div > div { background-color: #4caf50; }
    .stTabs [data-baseweb="tab"] { font-family: 'Cairo', sans-serif; font-size: 1em; }

    /* ===== جدول غذائي ===== */
    .meal-card {
        background: white; border-radius: 14px; padding: 16px 20px;
        margin: 10px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-right: 5px solid #4caf50;
    }
    .meal-card-breakfast { border-right-color: #ff9800; }
    .meal-card-lunch     { border-right-color: #2196f3; }
    .meal-card-dinner    { border-right-color: #9c27b0; }
    .meal-card-snack     { border-right-color: #4caf50; }
    .meal-header {
        font-size: 1.1em; font-weight: 700; margin-bottom: 10px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .meal-item {
        display: flex; justify-content: space-between;
        padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 0.92em;
    }
    .meal-item:last-child { border-bottom: none; }
    .cal-badge {
        background: #e8f5e9; color: #2e7d32;
        border-radius: 20px; padding: 2px 10px;
        font-size: 0.85em; font-weight: 600;
    }
    .total-bar {
        background: linear-gradient(135deg, #1b5e20, #4caf50);
        color: white; border-radius: 14px; padding: 18px 24px;
        margin: 16px 0; text-align: center;
    }
    .total-bar h3 { color: white; margin: 0; }
    .plan-day-header {
        background: #f1f8e9; border-radius: 10px;
        padding: 10px 16px; margin: 14px 0 6px;
        font-weight: 700; font-size: 1.05em; color: #33691e;
    }
    .warning-bar {
        background: #fff3e0; border-radius: 10px;
        padding: 10px 16px; margin: 8px 0; color: #e65100; font-size: 0.9em;
    }
    .info-bar {
        background: #e3f2fd; border-radius: 10px;
        padding: 10px 16px; margin: 8px 0; color: #0d47a1; font-size: 0.9em;
    }
    .summary-table {
        width: 100%; border-collapse: collapse; margin: 12px 0;
        font-size: 0.9em;
    }
    .summary-table th {
        background: #e8f5e9; color: #1b5e20; padding: 8px 12px;
        text-align: right; font-weight: 700;
    }
    .summary-table td {
        padding: 8px 12px; border-bottom: 1px solid #f0f0f0;
        text-align: right;
    }
    .summary-table tr:last-child td { border-bottom: none; }
</style>
""", unsafe_allow_html=True)

# ===========================================================================
# البيانات الغذائية DRI
# ===========================================================================
DRI = {
    "Energy":                              {"dri": 2000,  "unit": "kcal",  "ar": "سعرات حرارية",     "type": "macro"},
    "Protein":                             {"dri": 50,    "unit": "g",     "ar": "بروتين",            "type": "macro"},
    "Total lipid (fat)":                   {"dri": 65,    "unit": "g",     "ar": "دهون",              "type": "macro"},
    "Carbohydrate, by difference":         {"dri": 300,   "unit": "g",     "ar": "كربوهيدرات",        "type": "macro"},
    "Fiber, total dietary":                {"dri": 28,    "unit": "g",     "ar": "ألياف غذائية",      "type": "macro"},
    "Sugars, total including NLEA":        {"dri": 50,    "unit": "g",     "ar": "سكريات",            "type": "macro"},
    "Sodium, Na":                          {"dri": 2300,  "unit": "mg",    "ar": "صوديوم",            "type": "mineral"},
    "Potassium, K":                        {"dri": 3500,  "unit": "mg",    "ar": "بوتاسيوم",          "type": "mineral"},
    "Calcium, Ca":                         {"dri": 1000,  "unit": "mg",    "ar": "كالسيوم",           "type": "mineral"},
    "Iron, Fe":                            {"dri": 18,    "unit": "mg",    "ar": "حديد",              "type": "mineral"},
    "Magnesium, Mg":                       {"dri": 400,   "unit": "mg",    "ar": "مغنيسيوم",          "type": "mineral"},
    "Phosphorus, P":                       {"dri": 700,   "unit": "mg",    "ar": "فوسفور",            "type": "mineral"},
    "Zinc, Zn":                            {"dri": 11,    "unit": "mg",    "ar": "زنك",               "type": "mineral"},
    "Vitamin C, total ascorbic acid":      {"dri": 90,    "unit": "mg",    "ar": "فيتامين C",         "type": "vitamin"},
    "Vitamin A, RAE":                      {"dri": 900,   "unit": "mcg",   "ar": "فيتامين A",         "type": "vitamin"},
    "Vitamin D (D2 + D3)":                 {"dri": 20,    "unit": "mcg",   "ar": "فيتامين D",         "type": "vitamin"},
    "Vitamin B-12":                        {"dri": 2.4,   "unit": "mcg",   "ar": "فيتامين B12",       "type": "vitamin"},
    "Vitamin B-6":                         {"dri": 1.7,   "unit": "mg",    "ar": "فيتامين B6",        "type": "vitamin"},
    "Folate, total":                       {"dri": 400,   "unit": "mcg",   "ar": "فولات (B9)",        "type": "vitamin"},
    "Vitamin K (phylloquinone)":           {"dri": 120,   "unit": "mcg",   "ar": "فيتامين K",         "type": "vitamin"},
    "Vitamin E (alpha-tocopherol)":        {"dri": 15,    "unit": "mg",    "ar": "فيتامين E",         "type": "vitamin"},
    "Thiamin":                             {"dri": 1.2,   "unit": "mg",    "ar": "ثيامين (B1)",       "type": "vitamin"},
    "Riboflavin":                          {"dri": 1.3,   "unit": "mg",    "ar": "ريبوفلافين (B2)",   "type": "vitamin"},
    "Niacin":                              {"dri": 16,    "unit": "mg",    "ar": "نياسين (B3)",       "type": "vitamin"},
    "Fatty acids, total saturated":        {"dri": 20,    "unit": "g",     "ar": "دهون مشبعة",        "type": "fat"},
    "Fatty acids, total monounsaturated":  {"dri": 22,    "unit": "g",     "ar": "دهون أحادية",       "type": "fat"},
    "Fatty acids, total polyunsaturated":  {"dri": 17,    "unit": "g",     "ar": "دهون متعددة",       "type": "fat"},
    "Cholesterol":                         {"dri": 300,   "unit": "mg",    "ar": "كوليسترول",         "type": "fat"},
}

SMART_NOTES = {
    "Protein":                        {"high": "💪 مصدر ممتاز للبروتين — يدعم بناء العضلات والإصلاح الخلوي."},
    "Fiber, total dietary":           {"high": "🌿 غني بالألياف — يدعم صحة الهضم ويقلل الكوليسترول."},
    "Vitamin C, total ascorbic acid": {"high": "🍊 غني بفيتامين C — يعزز المناعة ومضاد للأكسدة."},
    "Iron, Fe":                       {"high": "🩸 مصدر جيد للحديد — يدعم تكوين الهيموغلوبين."},
    "Calcium, Ca":                    {"high": "🦴 غني بالكالسيوم — يقوّي العظام والأسنان."},
    "Potassium, K":                   {"high": "❤️ غني بالبوتاسيوم — مفيد للقلب وضغط الدم."},
    "Sodium, Na":                     {"high": "⚠️ مرتفع الصوديوم — يُنصح بالتقليل لمرضى الضغط.",
                                       "low":  "✅ منخفض الصوديوم — خيار ممتاز لمرضى الضغط."},
    "Vitamin D (D2 + D3)":            {"high": "☀️ غني بفيتامين D — يدعم امتصاص الكالسيوم وصحة العظام."},
    "Cholesterol":                    {"high": "⚠️ مرتفع الكوليسترول — يُنصح بالاعتدال لمرضى القلب."},
    "Magnesium, Mg":                  {"high": "⚡ غني بالمغنيسيوم — يدعم وظائف العضلات والأعصاب."},
    "Vitamin A, RAE":                 {"high": "👁️ غني بفيتامين A — مهم للبصر والجهاز المناعي."},
}

ARABIC_TO_ENGLISH = {
    "تفاح": "apple", "موز": "banana", "برتقال": "orange", "عنب": "grapes",
    "فراولة": "strawberry", "بطيخ": "watermelon", "مانجو": "mango",
    "بطاطا": "potato", "بطاطس": "potato", "جزر": "carrot", "طماطم": "tomato",
    "خيار": "cucumber", "بصل": "onion", "ثوم": "garlic", "سبانخ": "spinach",
    "بروكلي": "broccoli", "قرنبيط": "cauliflower", "خس": "lettuce",
    "فلفل": "bell pepper", "باذنجان": "eggplant", "كوسة": "zucchini",
    "دجاج": "chicken", "لحم بقر": "beef", "لحم غنم": "lamb", "سمك": "fish",
    "تونة": "tuna", "سلمون": "salmon", "جمبري": "shrimp", "بيضة": "egg",
    "حليب": "milk", "جبن": "cheese", "زبادي": "yogurt", "لبن": "yogurt",
    "زبدة": "butter", "أرز": "rice", "خبز": "bread", "معكرونة": "pasta",
    "شوفان": "oats", "عدس": "lentils", "حمص": "chickpeas", "فول": "fava beans",
    "لوز": "almonds", "جوز": "walnuts", "فستق": "pistachios", "كاجو": "cashews",
    "زيت زيتون": "olive oil", "سكر": "sugar", "عسل": "honey",
    "بطاطا حلوة": "sweet potato", "أفوكادو": "avocado", "رمان": "pomegranate",
    "تمر": "dates", "تين": "figs", "مشمش": "apricot", "خوخ": "peach",
    "كيوي": "kiwi", "أناناس": "pineapple", "ليمون": "lemon",
    "صدر دجاج": "chicken breast", "فخذ دجاج": "chicken thigh",
    "كشري": "koshary", "فول مدمس": "fava beans", "طعمية": "falafel",
    "ملوخية": "molokhia", "كفتة": "kofta", "شاورما": "shawarma",
    "فراخ": "chicken", "سمك بلطي": "tilapia", "جبنة": "cheese",
    "قريدس": "shrimp", "لحمة": "beef", "حنطة": "wheat",
    "بقلاوة": "baklava", "كنافة": "kunafa", "عيش": "bread",
    "رز": "rice", "مكرونة": "pasta", "جوافة": "guava",
    "بلح": "dates", "قمر الدين": "apricot", "تمر هندي": "tamarind",
}

LOCAL_DB = {
    "apple":          {"name_ar": "تفاح",            "nutrients": {"Energy":52,  "Protein":0.26,"Total lipid (fat)":0.17,"Carbohydrate, by difference":13.81,"Fiber, total dietary":2.4,"Sugars, total including NLEA":10.39,"Calcium, Ca":6,"Iron, Fe":0.12,"Potassium, K":107,"Sodium, Na":1,"Vitamin C, total ascorbic acid":4.6,"Vitamin A, RAE":3,"Magnesium, Mg":5,"Phosphorus, P":11,"Zinc, Zn":0.04,"Fatty acids, total saturated":0.03,"Cholesterol":0}},
    "banana":         {"name_ar": "موز",             "nutrients": {"Energy":89,  "Protein":1.09,"Total lipid (fat)":0.33,"Carbohydrate, by difference":22.84,"Fiber, total dietary":2.6,"Sugars, total including NLEA":12.23,"Calcium, Ca":5,"Iron, Fe":0.26,"Potassium, K":358,"Sodium, Na":1,"Vitamin C, total ascorbic acid":8.7,"Vitamin A, RAE":3,"Magnesium, Mg":27,"Phosphorus, P":22,"Zinc, Zn":0.15,"Vitamin B-6":0.37,"Folate, total":20,"Fatty acids, total saturated":0.11,"Cholesterol":0}},
    "chicken breast": {"name_ar": "صدر دجاج مشوي",  "nutrients": {"Energy":165, "Protein":31.02,"Total lipid (fat)":3.57,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":15,"Iron, Fe":1.04,"Potassium, K":220,"Sodium, Na":74,"Phosphorus, P":220,"Zinc, Zn":1.0,"Vitamin B-12":0.3,"Niacin":13.7,"Fatty acids, total saturated":1.01,"Cholesterol":85}},
    "egg":            {"name_ar": "بيضة كاملة",      "nutrients": {"Energy":143, "Protein":12.56,"Total lipid (fat)":9.51,"Carbohydrate, by difference":0.72,"Fiber, total dietary":0,"Calcium, Ca":56,"Iron, Fe":1.75,"Potassium, K":138,"Sodium, Na":142,"Phosphorus, P":198,"Zinc, Zn":1.29,"Vitamin A, RAE":160,"Vitamin D (D2 + D3)":2.0,"Vitamin B-12":0.89,"Riboflavin":0.46,"Fatty acids, total saturated":3.13,"Cholesterol":372}},
    "rice":           {"name_ar": "أرز أبيض مطبوخ", "nutrients": {"Energy":130, "Protein":2.69,"Total lipid (fat)":0.28,"Carbohydrate, by difference":28.17,"Fiber, total dietary":0.4,"Calcium, Ca":10,"Iron, Fe":1.49,"Potassium, K":35,"Sodium, Na":1,"Phosphorus, P":43,"Zinc, Zn":0.49,"Fatty acids, total saturated":0.08,"Cholesterol":0}},
    "salmon":         {"name_ar": "سمك سلمون",       "nutrients": {"Energy":208, "Protein":20.42,"Total lipid (fat)":13.42,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":12,"Iron, Fe":0.8,"Potassium, K":363,"Sodium, Na":59,"Phosphorus, P":252,"Zinc, Zn":0.64,"Vitamin D (D2 + D3)":11.1,"Vitamin B-12":3.18,"Fatty acids, total saturated":3.05,"Fatty acids, total polyunsaturated":3.77,"Cholesterol":63}},
    "milk":           {"name_ar": "حليب كامل الدسم", "nutrients": {"Energy":61,  "Protein":3.15,"Total lipid (fat)":3.27,"Carbohydrate, by difference":4.78,"Fiber, total dietary":0,"Sugars, total including NLEA":5.05,"Calcium, Ca":113,"Iron, Fe":0.03,"Potassium, K":150,"Sodium, Na":43,"Phosphorus, P":84,"Zinc, Zn":0.37,"Vitamin A, RAE":46,"Vitamin D (D2 + D3)":1.3,"Vitamin B-12":0.45,"Riboflavin":0.17,"Fatty acids, total saturated":1.87,"Cholesterol":10}},
    "bread":          {"name_ar": "خبز أبيض",        "nutrients": {"Energy":265, "Protein":9.0,"Total lipid (fat)":3.2,"Carbohydrate, by difference":49.0,"Fiber, total dietary":2.7,"Calcium, Ca":182,"Iron, Fe":3.6,"Potassium, K":115,"Sodium, Na":491,"Phosphorus, P":108,"Zinc, Zn":0.7,"Fatty acids, total saturated":0.7,"Cholesterol":0}},
    "potato":         {"name_ar": "بطاطا مسلوقة",   "nutrients": {"Energy":87,  "Protein":1.87,"Total lipid (fat)":0.1,"Carbohydrate, by difference":20.13,"Fiber, total dietary":1.8,"Sugars, total including NLEA":0.9,"Calcium, Ca":5,"Iron, Fe":0.31,"Potassium, K":379,"Sodium, Na":4,"Vitamin C, total ascorbic acid":13.0,"Vitamin B-6":0.27,"Magnesium, Mg":20,"Phosphorus, P":44,"Fatty acids, total saturated":0.03,"Cholesterol":0}},
    "oats":           {"name_ar": "شوفان جاف",       "nutrients": {"Energy":389, "Protein":16.89,"Total lipid (fat)":6.9,"Carbohydrate, by difference":66.27,"Fiber, total dietary":10.6,"Calcium, Ca":54,"Iron, Fe":4.72,"Potassium, K":429,"Sodium, Na":2,"Magnesium, Mg":177,"Phosphorus, P":523,"Zinc, Zn":3.97,"Thiamin":0.76,"Riboflavin":0.14,"Fatty acids, total saturated":1.22,"Cholesterol":0}},
    "orange":         {"name_ar": "برتقال",          "nutrients": {"Energy":47,  "Protein":0.94,"Total lipid (fat)":0.12,"Carbohydrate, by difference":11.75,"Fiber, total dietary":2.4,"Sugars, total including NLEA":9.35,"Calcium, Ca":40,"Iron, Fe":0.1,"Potassium, K":181,"Sodium, Na":0,"Vitamin C, total ascorbic acid":53.2,"Folate, total":30,"Fatty acids, total saturated":0.02,"Cholesterol":0}},
    "yogurt":         {"name_ar": "زبادي",           "nutrients": {"Energy":61,  "Protein":3.5,"Total lipid (fat)":3.3,"Carbohydrate, by difference":4.7,"Fiber, total dietary":0,"Sugars, total including NLEA":4.7,"Calcium, Ca":121,"Iron, Fe":0.05,"Potassium, K":155,"Sodium, Na":46,"Phosphorus, P":95,"Vitamin B-12":0.37,"Fatty acids, total saturated":2.1,"Cholesterol":13}},
    "almonds":        {"name_ar": "لوز",             "nutrients": {"Energy":579, "Protein":21.15,"Total lipid (fat)":49.93,"Carbohydrate, by difference":21.55,"Fiber, total dietary":12.5,"Calcium, Ca":264,"Iron, Fe":3.71,"Potassium, K":733,"Sodium, Na":1,"Magnesium, Mg":270,"Phosphorus, P":481,"Zinc, Zn":3.12,"Vitamin E (alpha-tocopherol)":25.63,"Fatty acids, total saturated":3.8,"Cholesterol":0}},
    "lentils":        {"name_ar": "عدس مطبوخ",      "nutrients": {"Energy":116, "Protein":9.02,"Total lipid (fat)":0.38,"Carbohydrate, by difference":20.13,"Fiber, total dietary":7.9,"Calcium, Ca":19,"Iron, Fe":3.33,"Potassium, K":369,"Sodium, Na":2,"Magnesium, Mg":36,"Phosphorus, P":180,"Zinc, Zn":1.27,"Folate, total":181,"Fatty acids, total saturated":0.05,"Cholesterol":0}},
    "tuna":           {"name_ar": "تونة معلبة",     "nutrients": {"Energy":128, "Protein":29.13,"Total lipid (fat)":0.97,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":11,"Iron, Fe":1.3,"Potassium, K":279,"Sodium, Na":396,"Phosphorus, P":237,"Zinc, Zn":0.9,"Vitamin D (D2 + D3)":5.7,"Vitamin B-12":2.52,"Niacin":15.05,"Fatty acids, total saturated":0.25,"Cholesterol":49}},
    "avocado":        {"name_ar": "أفوكادو",        "nutrients": {"Energy":160, "Protein":2.0,"Total lipid (fat)":14.66,"Carbohydrate, by difference":8.53,"Fiber, total dietary":6.7,"Sugars, total including NLEA":0.66,"Calcium, Ca":12,"Iron, Fe":0.55,"Potassium, K":485,"Sodium, Na":7,"Magnesium, Mg":29,"Phosphorus, P":52,"Zinc, Zn":0.64,"Vitamin C, total ascorbic acid":10.0,"Vitamin K (phylloquinone)":21.0,"Folate, total":81,"Vitamin B-6":0.257,"Fatty acids, total monounsaturated":9.8,"Fatty acids, total saturated":2.13,"Cholesterol":0}},
    "spinach":        {"name_ar": "سبانخ طازجة",    "nutrients": {"Energy":23,  "Protein":2.86,"Total lipid (fat)":0.39,"Carbohydrate, by difference":3.63,"Fiber, total dietary":2.2,"Calcium, Ca":99,"Iron, Fe":2.71,"Potassium, K":558,"Sodium, Na":79,"Magnesium, Mg":79,"Phosphorus, P":49,"Zinc, Zn":0.53,"Vitamin C, total ascorbic acid":28.1,"Vitamin A, RAE":469,"Vitamin K (phylloquinone)":482.9,"Folate, total":194,"Fatty acids, total saturated":0.06,"Cholesterol":0}},
    "dates":          {"name_ar": "تمر",             "nutrients": {"Energy":277, "Protein":1.81,"Total lipid (fat)":0.15,"Carbohydrate, by difference":74.97,"Fiber, total dietary":6.7,"Sugars, total including NLEA":66.47,"Calcium, Ca":64,"Iron, Fe":0.9,"Potassium, K":696,"Sodium, Na":1,"Magnesium, Mg":54,"Phosphorus, P":62,"Zinc, Zn":0.44,"Vitamin B-6":0.249,"Niacin":1.61,"Fatty acids, total saturated":0.03,"Cholesterol":0}},
    "olive oil":      {"name_ar": "زيت زيتون",      "nutrients": {"Energy":884, "Protein":0,"Total lipid (fat)":100.0,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":1,"Iron, Fe":0.56,"Potassium, K":1,"Sodium, Na":2,"Vitamin E (alpha-tocopherol)":14.35,"Vitamin K (phylloquinone)":60.2,"Fatty acids, total saturated":13.8,"Fatty acids, total monounsaturated":72.96,"Fatty acids, total polyunsaturated":10.52,"Cholesterol":0}},
    "broccoli":       {"name_ar": "بروكلي",          "nutrients": {"Energy":34,  "Protein":2.82,"Total lipid (fat)":0.37,"Carbohydrate, by difference":6.64,"Fiber, total dietary":2.6,"Calcium, Ca":47,"Iron, Fe":0.73,"Potassium, K":316,"Sodium, Na":33,"Magnesium, Mg":21,"Phosphorus, P":66,"Zinc, Zn":0.41,"Vitamin C, total ascorbic acid":89.2,"Vitamin A, RAE":31,"Vitamin K (phylloquinone)":101.6,"Folate, total":63,"Fatty acids, total saturated":0.04,"Cholesterol":0}},
    "sweet potato":   {"name_ar": "بطاطا حلوة",     "nutrients": {"Energy":86,  "Protein":1.57,"Total lipid (fat)":0.05,"Carbohydrate, by difference":20.12,"Fiber, total dietary":3.0,"Sugars, total including NLEA":4.18,"Calcium, Ca":30,"Iron, Fe":0.61,"Potassium, K":337,"Sodium, Na":55,"Vitamin C, total ascorbic acid":2.4,"Vitamin A, RAE":961,"Vitamin B-6":0.286,"Magnesium, Mg":25,"Phosphorus, P":47,"Fatty acids, total saturated":0.02,"Cholesterol":0}},
    "chickpeas":      {"name_ar": "حمص مطبوخ",      "nutrients": {"Energy":164, "Protein":8.86,"Total lipid (fat)":2.59,"Carbohydrate, by difference":27.42,"Fiber, total dietary":7.6,"Calcium, Ca":49,"Iron, Fe":2.89,"Potassium, K":291,"Sodium, Na":7,"Magnesium, Mg":48,"Phosphorus, P":168,"Zinc, Zn":1.53,"Folate, total":172,"Vitamin B-6":0.139,"Fatty acids, total saturated":0.27,"Cholesterol":0}},
    "fava beans":     {"name_ar": "فول مطبوخ",      "nutrients": {"Energy":110, "Protein":7.6,"Total lipid (fat)":0.4,"Carbohydrate, by difference":19.65,"Fiber, total dietary":5.4,"Calcium, Ca":36,"Iron, Fe":1.5,"Potassium, K":250,"Sodium, Na":5,"Magnesium, Mg":43,"Phosphorus, P":125,"Zinc, Zn":1.0,"Folate, total":104,"Fatty acids, total saturated":0.07,"Cholesterol":0}},
    "tilapia":        {"name_ar": "سمك بلطي",       "nutrients": {"Energy":96,  "Protein":20.08,"Total lipid (fat)":1.7,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":10,"Iron, Fe":0.56,"Potassium, K":302,"Sodium, Na":52,"Phosphorus, P":168,"Zinc, Zn":0.33,"Vitamin B-12":1.58,"Niacin":3.9,"Fatty acids, total saturated":0.58,"Cholesterol":50}},
    "beef":           {"name_ar": "لحم بقري مطبوخ", "nutrients": {"Energy":250, "Protein":26.0,"Total lipid (fat)":15.0,"Carbohydrate, by difference":0,"Fiber, total dietary":0,"Calcium, Ca":18,"Iron, Fe":2.6,"Potassium, K":318,"Sodium, Na":72,"Phosphorus, P":200,"Zinc, Zn":5.3,"Vitamin B-12":2.5,"Niacin":4.0,"Fatty acids, total saturated":5.8,"Cholesterol":87}},
    "cheese":         {"name_ar": "جبن أبيض",       "nutrients": {"Energy":264, "Protein":18.0,"Total lipid (fat)":21.0,"Carbohydrate, by difference":1.3,"Fiber, total dietary":0,"Calcium, Ca":500,"Iron, Fe":0.2,"Potassium, K":93,"Sodium, Na":621,"Phosphorus, P":347,"Zinc, Zn":2.9,"Vitamin A, RAE":175,"Vitamin B-12":0.8,"Riboflavin":0.28,"Fatty acids, total saturated":13.0,"Cholesterol":75}},
    "pasta":          {"name_ar": "مكرونة مطبوخة",  "nutrients": {"Energy":158, "Protein":5.8,"Total lipid (fat)":0.93,"Carbohydrate, by difference":30.86,"Fiber, total dietary":1.8,"Calcium, Ca":7,"Iron, Fe":1.3,"Potassium, K":44,"Sodium, Na":1,"Phosphorus, P":58,"Zinc, Zn":0.51,"Thiamin":0.02,"Folate, total":7,"Fatty acids, total saturated":0.18,"Cholesterol":0}},
    "guava":          {"name_ar": "جوافة",           "nutrients": {"Energy":68,  "Protein":2.55,"Total lipid (fat)":0.95,"Carbohydrate, by difference":14.32,"Fiber, total dietary":5.4,"Sugars, total including NLEA":8.92,"Calcium, Ca":18,"Iron, Fe":0.26,"Potassium, K":417,"Sodium, Na":2,"Vitamin C, total ascorbic acid":228.3,"Vitamin A, RAE":31,"Folate, total":49,"Fatty acids, total saturated":0.27,"Cholesterol":0}},
    "watermelon":     {"name_ar": "بطيخ",            "nutrients": {"Energy":30,  "Protein":0.61,"Total lipid (fat)":0.15,"Carbohydrate, by difference":7.55,"Fiber, total dietary":0.4,"Sugars, total including NLEA":6.2,"Calcium, Ca":7,"Iron, Fe":0.24,"Potassium, K":112,"Sodium, Na":1,"Vitamin C, total ascorbic acid":8.1,"Vitamin A, RAE":28,"Magnesium, Mg":10,"Fatty acids, total saturated":0.02,"Cholesterol":0}},
    "strawberry":     {"name_ar": "فراولة",          "nutrients": {"Energy":32,  "Protein":0.67,"Total lipid (fat)":0.3,"Carbohydrate, by difference":7.68,"Fiber, total dietary":2.0,"Sugars, total including NLEA":4.89,"Calcium, Ca":16,"Iron, Fe":0.41,"Potassium, K":153,"Sodium, Na":1,"Vitamin C, total ascorbic acid":58.8,"Folate, total":24,"Fatty acids, total saturated":0.02,"Cholesterol":0}},
    "mango":          {"name_ar": "مانجو",           "nutrients": {"Energy":60,  "Protein":0.82,"Total lipid (fat)":0.38,"Carbohydrate, by difference":14.98,"Fiber, total dietary":1.6,"Sugars, total including NLEA":13.66,"Calcium, Ca":11,"Iron, Fe":0.16,"Potassium, K":168,"Sodium, Na":1,"Vitamin C, total ascorbic acid":36.4,"Vitamin A, RAE":54,"Folate, total":43,"Fatty acids, total saturated":0.09,"Cholesterol":0}},
    "shrimp":         {"name_ar": "جمبري مطبوخ",    "nutrients": {"Energy":99,  "Protein":20.91,"Total lipid (fat)":1.08,"Carbohydrate, by difference":0.93,"Fiber, total dietary":0,"Calcium, Ca":70,"Iron, Fe":0.52,"Potassium, K":185,"Sodium, Na":224,"Phosphorus, P":137,"Zinc, Zn":1.34,"Vitamin B-12":1.16,"Niacin":2.2,"Fatty acids, total saturated":0.29,"Cholesterol":189}},
    "walnuts":        {"name_ar": "جوز",             "nutrients": {"Energy":654, "Protein":15.23,"Total lipid (fat)":65.21,"Carbohydrate, by difference":13.71,"Fiber, total dietary":6.7,"Calcium, Ca":98,"Iron, Fe":2.91,"Potassium, K":441,"Sodium, Na":2,"Magnesium, Mg":158,"Phosphorus, P":346,"Zinc, Zn":3.09,"Vitamin E (alpha-tocopherol)":0.7,"Fatty acids, total polyunsaturated":47.17,"Fatty acids, total saturated":6.13,"Cholesterol":0}},
    "falafel":        {"name_ar": "فلافل (طعمية)",  "nutrients": {"Energy":333, "Protein":13.31,"Total lipid (fat)":17.8,"Carbohydrate, by difference":31.84,"Fiber, total dietary":4.9,"Calcium, Ca":49,"Iron, Fe":2.76,"Potassium, K":585,"Sodium, Na":294,"Magnesium, Mg":66,"Phosphorus, P":196,"Zinc, Zn":1.82,"Folate, total":172,"Fatty acids, total saturated":2.03,"Cholesterol":0}},
    "kofta":          {"name_ar": "كفتة مشوية",     "nutrients": {"Energy":236, "Protein":19.5,"Total lipid (fat)":16.5,"Carbohydrate, by difference":2.2,"Fiber, total dietary":0.3,"Calcium, Ca":30,"Iron, Fe":2.2,"Potassium, K":280,"Sodium, Na":350,"Phosphorus, P":165,"Zinc, Zn":4.2,"Vitamin B-12":2.0,"Niacin":4.5,"Fatty acids, total saturated":6.3,"Cholesterol":80}},
}

# ===========================================================================
# قوالب الجداول الغذائية الجاهزة
# ===========================================================================
MEAL_PLAN_TEMPLATES = {
    "خسارة دهون وبناء عضل": {
        "الإفطار": [
            {"name": "شوفان جاف", "amount": 50, "unit": "جم", "key": "oats"},
            {"name": "بيضة كاملة", "amount": 100, "unit": "جم", "key": "egg"},
            {"name": "موز", "amount": 100, "unit": "جم", "key": "banana"},
        ],
        "وجبة خفيفة صباح": [
            {"name": "زبادي", "amount": 150, "unit": "جم", "key": "yogurt"},
            {"name": "لوز", "amount": 20, "unit": "جم", "key": "almonds"},
        ],
        "الغداء": [
            {"name": "صدر دجاج مشوي", "amount": 150, "unit": "جم", "key": "chicken breast"},
            {"name": "أرز أبيض مطبوخ", "amount": 150, "unit": "جم", "key": "rice"},
            {"name": "بروكلي", "amount": 100, "unit": "جم", "key": "broccoli"},
        ],
        "وجبة خفيفة مساء": [
            {"name": "تفاح", "amount": 150, "unit": "جم", "key": "apple"},
        ],
        "العشاء": [
            {"name": "سمك سلمون", "amount": 120, "unit": "جم", "key": "salmon"},
            {"name": "بطاطا حلوة", "amount": 150, "unit": "جم", "key": "sweet potato"},
            {"name": "سبانخ طازجة", "amount": 80, "unit": "جم", "key": "spinach"},
        ],
    },
    "زيادة الوزن والعضل": {
        "الإفطار": [
            {"name": "شوفان جاف", "amount": 80, "unit": "جم", "key": "oats"},
            {"name": "بيضة كاملة", "amount": 150, "unit": "جم", "key": "egg"},
            {"name": "موز", "amount": 150, "unit": "جم", "key": "banana"},
            {"name": "حليب كامل الدسم", "amount": 200, "unit": "مل", "key": "milk"},
        ],
        "وجبة خفيفة صباح": [
            {"name": "لوز", "amount": 30, "unit": "جم", "key": "almonds"},
            {"name": "تمر", "amount": 50, "unit": "جم", "key": "dates"},
        ],
        "الغداء": [
            {"name": "صدر دجاج مشوي", "amount": 200, "unit": "جم", "key": "chicken breast"},
            {"name": "أرز أبيض مطبوخ", "amount": 250, "unit": "جم", "key": "rice"},
            {"name": "أفوكادو", "amount": 80, "unit": "جم", "key": "avocado"},
        ],
        "وجبة خفيفة مساء": [
            {"name": "زبادي", "amount": 200, "unit": "جم", "key": "yogurt"},
            {"name": "موز", "amount": 100, "unit": "جم", "key": "banana"},
        ],
        "العشاء": [
            {"name": "لحم بقري مطبوخ", "amount": 150, "unit": "جم", "key": "beef"},
            {"name": "مكرونة مطبوخة", "amount": 200, "unit": "جم", "key": "pasta"},
            {"name": "بروكلي", "amount": 100, "unit": "جم", "key": "broccoli"},
        ],
    },
    "الحفاظ على الوزن الحالي": {
        "الإفطار": [
            {"name": "خبز أبيض", "amount": 60, "unit": "جم", "key": "bread"},
            {"name": "بيضة كاملة", "amount": 100, "unit": "جم", "key": "egg"},
            {"name": "جبن أبيض", "amount": 30, "unit": "جم", "key": "cheese"},
        ],
        "وجبة خفيفة صباح": [
            {"name": "برتقال", "amount": 150, "unit": "جم", "key": "orange"},
        ],
        "الغداء": [
            {"name": "تونة معلبة", "amount": 100, "unit": "جم", "key": "tuna"},
            {"name": "أرز أبيض مطبوخ", "amount": 200, "unit": "جم", "key": "rice"},
            {"name": "سبانخ طازجة", "amount": 80, "unit": "جم", "key": "spinach"},
        ],
        "وجبة خفيفة مساء": [
            {"name": "زبادي", "amount": 150, "unit": "جم", "key": "yogurt"},
        ],
        "العشاء": [
            {"name": "عدس مطبوخ", "amount": 150, "unit": "جم", "key": "lentils"},
            {"name": "خبز أبيض", "amount": 60, "unit": "جم", "key": "bread"},
            {"name": "بروكلي", "amount": 100, "unit": "جم", "key": "broccoli"},
        ],
    },
}

MEAL_ICONS = {
    "الإفطار":           ("🌅", "meal-card-breakfast"),
    "وجبة خفيفة صباح":  ("🍎", "meal-card-snack"),
    "الغداء":            ("☀️", "meal-card-lunch"),
    "وجبة خفيفة مساء":  ("🥜", "meal-card-snack"),
    "العشاء":            ("🌙", "meal-card-dinner"),
}

USDA_API_KEY = "DEMO_KEY"
USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# ===========================================================================
# دوال المساعدة
# ===========================================================================
def translate_query(q):
    q = q.strip()
    if q in ARABIC_TO_ENGLISH:
        return ARABIC_TO_ENGLISH[q]
    for ar, en in ARABIC_TO_ENGLISH.items():
        if ar in q:
            return en
    return q

def search_usda(query):
    try:
        r = requests.get(f"{USDA_BASE_URL}/foods/search",
                         params={"query": query, "pageSize": 20,
                                 "api_key": USDA_API_KEY,
                                 "dataType": "Foundation,SR Legacy"},
                         timeout=10)
        foods = r.json().get("foods", [])
        q_lower = query.lower().strip()
        exact = [f for f in foods if f.get("description", "").lower().startswith(q_lower)]
        close = [f for f in foods if q_lower in f.get("description", "").lower() and f not in exact]
        rest  = [f for f in foods if f not in exact and f not in close]
        return (exact + close + rest)[:8]
    except Exception:
        return []

def get_usda_detail(fdc_id):
    try:
        r = requests.get(f"{USDA_BASE_URL}/food/{fdc_id}",
                         params={"api_key": USDA_API_KEY}, timeout=10)
        return r.json()
    except Exception:
        return {}

def extract_nutrients(detail):
    out = {}
    for n in detail.get("foodNutrients", []):
        name = n.get("nutrient", {}).get("name", "")
        amt  = n.get("amount", 0) or 0
        if name in DRI:
            out[name] = amt
    return out

def search_local(query):
    q = query.lower()
    res = [(k, v) for k, v in LOCAL_DB.items() if q in k or q in v["name_ar"]]
    if not res:
        res = [(k, v) for k, v in LOCAL_DB.items() if any(w in k for w in q.split())]
    return res

def scale(nutrients, weight):
    f = weight / 100.0
    return {k: v * f for k, v in nutrients.items()}

def classify(pct):
    if pct >= 20: return "غني",   "badge-rich"
    if pct >= 10: return "متوسط", "badge-mid"
    if pct > 0:   return "قليل",  "badge-low"
    return "—", ""

def smart_notes(nutrients_scaled):
    notes = []
    for nutrient, texts in SMART_NOTES.items():
        val = nutrients_scaled.get(nutrient, 0)
        if val <= 0:
            continue
        dri = DRI[nutrient]["dri"]
        pct = val / dri * 100
        if pct >= 20 and "high" in texts:
            notes.append(texts["high"])
        elif pct < 5 and "low" in texts:
            notes.append(texts["low"])
    return notes

def render_section(ns, title, keys):
    items = [(k, ns.get(k, 0)) for k in keys if ns.get(k, 0) > 0]
    if not items:
        return
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    for k, val in items:
        info = DRI[k]
        pct  = min(val / info["dri"] * 100, 100)
        label, badge = classify(pct)
        st.markdown(
            f'<div class="metric-card">'
            f'<span>{info["ar"]}</span>'
            f'<span>{val:.2f} {info["unit"]}</span>'
            f'<span class="{badge}">{label} ({pct:.0f}%)</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.progress(int(pct))

def calc_meal_nutrients(items):
    """يحسب إجمالي العناصر الغذائية لوجبة من قائمة أصناف"""
    total = {}
    for item in items:
        key = item.get("key", "")
        amt = item.get("amount", 100)
        if key in LOCAL_DB:
            scaled = scale(LOCAL_DB[key]["nutrients"], amt)
            for k, v in scaled.items():
                total[k] = total.get(k, 0) + v
    return total

def calc_bmi(weight_kg, height_cm):
    h = height_cm / 100
    return weight_kg / (h * h)

def bmi_category(bmi):
    if bmi < 18.5: return "نقص في الوزن", "#2196f3", "⚠️"
    elif bmi < 25: return "وزن طبيعي ✓",  "#4caf50", "✅"
    elif bmi < 30: return "زيادة في الوزن","#ff9800", "⚠️"
    else:          return "سمنة",           "#f44336", "🚨"

def calc_bmr(weight_kg, height_cm, age, gender):
    if gender == "ذكر":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

ACTIVITY_FACTORS = {
    "مستقر (بدون رياضة)":           1.2,
    "خفيف (رياضة 1-3 أيام/أسبوع)":  1.375,
    "متوسط (رياضة 3-5 أيام/أسبوع)": 1.55,
    "مكثف (رياضة 6-7 أيام/أسبوع)":  1.725,
    "رياضي احترافي":                  1.9,
}

GOAL_ADJUSTMENTS = {
    "خسارة دهون وبناء عضل":    -300,
    "زيادة الوزن والعضل":       +400,
    "الحفاظ على الوزن الحالي":    0,
}

# ===========================================================================
# الواجهة الرئيسية
# ===========================================================================
st.markdown("# 🥗 DNP — التغذية الذكية")
st.markdown("**محلل الغذاء · BMI · السعرات اليومية · الجدول الغذائي**")
st.divider()

tab1, tab2, tab3 = st.tabs([
    "⚖️ BMI والسعرات اليومية",
    "🔍 محلل الغذاء",
    "📋 الجدول الغذائي"
])

# ===========================================================================
# تبويب 1: BMI + السعرات
# ===========================================================================
with tab1:
    st.markdown("### أدخل بياناتك الشخصية")

    col1, col2 = st.columns(2)
    with col1:
        gender = st.radio("الجنس", ["ذكر", "أنثى"], horizontal=True)
        age    = st.number_input("العمر (سنة)", min_value=10, max_value=100, value=25)
    with col2:
        height   = st.number_input("الطول (سم)", min_value=100, max_value=250, value=170)
        weight_p = st.number_input("الوزن (كجم)", min_value=30, max_value=300, value=70)

    activity = st.selectbox("مستوى النشاط البدني", list(ACTIVITY_FACTORS.keys()))
    goal     = st.radio("الهدف", list(GOAL_ADJUSTMENTS.keys()), horizontal=True)

    calc_btn = st.button("احسب الآن", type="primary", use_container_width=True)

    if calc_btn:
        bmi = calc_bmi(weight_p, height)
        cat, color, icon = bmi_category(bmi)
        bmr  = calc_bmr(weight_p, height, age, gender)
        tdee = bmr * ACTIVITY_FACTORS[activity]
        final = tdee + GOAL_ADJUSTMENTS[goal]

        st.divider()
        st.markdown("### نتيجة BMI")
        st.markdown(
            f'<div class="bmi-card" style="background:{color}20; color:{color};">'
            f'{icon} {bmi:.1f} — {cat}'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown("""
        | التصنيف | BMI |
        |---------|-----|
        | نقص في الوزن | أقل من 18.5 |
        | وزن طبيعي | 18.5 – 24.9 |
        | زيادة في الوزن | 25 – 29.9 |
        | سمنة | 30 فأكثر |
        """)

        st.divider()
        st.markdown("### السعرات الحرارية اليومية")
        c1, c2, c3 = st.columns(3)
        c1.metric("🔥 الأساسي (BMR)",    f"{bmr:.0f} kcal",   help="السعرات التي يحرقها جسمك في الراحة التامة")
        c2.metric("⚡ مع النشاط (TDEE)", f"{tdee:.0f} kcal",  help="إجمالي ما تحرقه يومياً")
        c3.metric("🎯 هدفك اليومي",      f"{final:.0f} kcal", help=f"مع تعديل الهدف: {GOAL_ADJUSTMENTS[goal]:+} kcal")

        st.divider()
        st.markdown("### توزيع الماكرو المقترح")
        if goal == "خسارة دهون وبناء عضل":
            p_pct, f_pct, c_pct = 0.35, 0.25, 0.40
        elif goal == "زيادة الوزن والعضل":
            p_pct, f_pct, c_pct = 0.30, 0.25, 0.45
        else:
            p_pct, f_pct, c_pct = 0.25, 0.30, 0.45

        pro_g  = (final * p_pct) / 4
        fat_g  = (final * f_pct) / 9
        carb_g = (final * c_pct) / 4

        m1, m2, m3 = st.columns(3)
        m1.metric("💪 بروتين",     f"{pro_g:.0f} جم/يوم",  f"{p_pct*100:.0f}% من السعرات")
        m2.metric("🥑 دهون",       f"{fat_g:.0f} جم/يوم",  f"{f_pct*100:.0f}% من السعرات")
        m3.metric("🍞 كربوهيدرات", f"{carb_g:.0f} جم/يوم", f"{c_pct*100:.0f}% من السعرات")

        # حفظ النتائج في session للاستخدام في تبويب الجدول
        st.session_state["tdee_result"] = final
        st.session_state["goal_result"] = goal
        st.session_state["pro_g"]       = pro_g
        st.session_state["fat_g"]       = fat_g
        st.session_state["carb_g"]      = carb_g

        st.caption("* المعادلة المستخدمة: Mifflin-St Jeor (2005) — الأدق وفق الأبحاث الحديثة لدى البالغين.")

# ===========================================================================
# تبويب 2: محلل الغذاء
# ===========================================================================
with tab2:
    st.markdown("### حلّل أي طعام")

    col1, col2 = st.columns([3, 1])
    with col1:
        food_input = st.text_input(
            "🔍 اسم الطعام (عربي أو إنجليزي)",
            placeholder="مثال: موز، صدر دجاج، avocado..."
        )
    with col2:
        weight = st.number_input("الكمية (جم)", min_value=1, max_value=2000, value=100, step=10)

    analyze_btn = st.button("تحليل الآن", type="primary", use_container_width=True, key="analyze")

    if analyze_btn and food_input:
        english_q     = translate_query(food_input)
        nutrients_raw = None
        food_name     = food_input
        source        = ""

        with st.spinner("جاري البحث في USDA FoodData Central..."):
            api_results = search_usda(english_q)

        if api_results:
            options      = {i["description"]: i for i in api_results}
            chosen_label = st.selectbox("اختر الطعام الأقرب:", list(options.keys()))
            chosen       = options[chosen_label]
            fdc_id       = chosen["fdcId"]
            food_name    = chosen["description"]
            with st.spinner("جاري جلب التفاصيل..."):
                detail = get_usda_detail(fdc_id)
            nutrients_raw = extract_nutrients(detail)
            source = f"USDA FoodData Central — FDC ID: {fdc_id}"

        if not nutrients_raw:
            local = search_local(english_q) or search_local(food_input)
            if local:
                if len(local) == 1:
                    key, val = local[0]
                else:
                    opts = {v["name_ar"] + f" ({k})": (k, v) for k, v in local}
                    ch   = st.selectbox("اختر من القائمة:", list(opts.keys()))
                    key, val = opts[ch]
                food_name     = val["name_ar"]
                nutrients_raw = val["nutrients"]
                source        = "قاعدة بيانات محلية (USDA-based)"
            else:
                st.error(f"عذراً، لم يُعثر على **{food_input}**. جرب اسماً آخر أو اكتبه بالإنجليزية.")
                st.stop()

        ns = scale(nutrients_raw, weight)
        total_cal = ns.get("Energy", 0) or (
            ns.get("Protein", 0) * 4
            + ns.get("Total lipid (fat)", 0) * 9
            + ns.get("Carbohydrate, by difference", 0) * 4
            + ns.get("Fiber, total dietary", 0) * 2
        )

        st.divider()
        st.markdown(f"### 📋 {food_name} — {weight} جم")
        st.caption(f"المصدر: {source}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔥 سعرات",  f"{total_cal:.0f} kcal")
        c2.metric("💪 بروتين", f"{ns.get('Protein', 0):.1f} g")
        c3.metric("🍞 كارب",   f"{ns.get('Carbohydrate, by difference', 0):.1f} g")
        c4.metric("🥑 دهون",   f"{ns.get('Total lipid (fat)', 0):.1f} g")

        cal_p = ns.get("Protein", 0) * 4
        cal_f = ns.get("Total lipid (fat)", 0) * 9
        cal_c = ns.get("Carbohydrate, by difference", 0) * 4
        if total_cal > 0:
            st.markdown('<div class="section-title">توزيع السعرات</div>', unsafe_allow_html=True)
            a, b, c = st.columns(3)
            a.metric("من البروتين",     f"{cal_p/total_cal*100:.0f}%")
            b.metric("من الدهون",       f"{cal_f/total_cal*100:.0f}%")
            c.metric("من الكربوهيدرات",f"{cal_c/total_cal*100:.0f}%")

        render_section(ns, "🧪 العناصر الكبرى",
                       ["Protein","Total lipid (fat)","Carbohydrate, by difference",
                        "Fiber, total dietary","Sugars, total including NLEA"])
        render_section(ns, "⚗️ المعادن",
                       ["Calcium, Ca","Iron, Fe","Potassium, K","Sodium, Na",
                        "Magnesium, Mg","Phosphorus, P","Zinc, Zn"])
        render_section(ns, "💊 الفيتامينات",
                       ["Vitamin C, total ascorbic acid","Vitamin A, RAE",
                        "Vitamin D (D2 + D3)","Vitamin B-12","Vitamin B-6",
                        "Folate, total","Vitamin K (phylloquinone)",
                        "Vitamin E (alpha-tocopherol)","Thiamin","Riboflavin","Niacin"])
        render_section(ns, "🫀 الدهون المفصّلة",
                       ["Fatty acids, total saturated","Fatty acids, total monounsaturated",
                        "Fatty acids, total polyunsaturated","Cholesterol"])

        notes = smart_notes(ns)
        if notes:
            st.markdown('<div class="section-title">💡 ملاحظات غذائية وصحية</div>', unsafe_allow_html=True)
            for note in notes:
                st.markdown(f'<div class="note-card">{note}</div>', unsafe_allow_html=True)

        st.divider()
        st.caption("* القيم اليومية مبنية على نظام 2000 سعرة — قد تختلف حسب العمر والجنس ومستوى النشاط.")

    elif analyze_btn and not food_input:
        st.warning("من فضلك أدخل اسم الطعام أولاً.")

# ===========================================================================
# تبويب 3: الجدول الغذائي
# ===========================================================================
with tab3:
    st.markdown("### 📋 بناء الجدول الغذائي اليومي")

    # ---- إعدادات الجدول ----
    with st.expander("⚙️ إعدادات الجدول", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            plan_goal = st.selectbox(
                "الهدف الغذائي",
                list(MEAL_PLAN_TEMPLATES.keys()),
                help="اختر هدفك وسيظهر قالب مقترح تلقائياً"
            )
            target_cal = st.number_input(
                "🎯 الهدف اليومي من السعرات (kcal)",
                min_value=1000, max_value=5000,
                value=int(st.session_state.get("tdee_result", 2000)),
                step=50,
                help="يمكنك نقل النتيجة تلقائياً من تبويب BMI"
            )
        with col2:
            num_days   = st.selectbox("عدد أيام الجدول", [1, 3, 5, 7], index=0)
            show_macros = st.checkbox("إظهار تفاصيل الماكرو لكل وجبة", value=True)

    # تلميح إذا كان المستخدم حسب البيانات في tab1
    if "tdee_result" in st.session_state:
        st.markdown(
            f'<div class="info-bar">💡 تم استيراد هدف السعرات تلقائياً من تبويب BMI: '
            f'<strong>{st.session_state["tdee_result"]:.0f} kcal</strong></div>',
            unsafe_allow_html=True
        )

    st.divider()
    st.markdown("### 🍽️ تخصيص الوجبات")
    st.caption("يمكنك تعديل كميات كل صنف أو إضافة أصناف جديدة من قائمة الأطعمة المتاحة.")

    # ---- بناء الجدول اليومي (session state) ----
    template = MEAL_PLAN_TEMPLATES[plan_goal]

    if "meal_plan" not in st.session_state or st.session_state.get("last_goal") != plan_goal:
        import copy
        st.session_state["meal_plan"] = copy.deepcopy(template)
        st.session_state["last_goal"] = plan_goal

    meal_plan = st.session_state["meal_plan"]

    # ---- تعديل الوجبات ----
    all_foods_ar = {v["name_ar"]: k for k, v in LOCAL_DB.items()}
    all_foods_display = list(all_foods_ar.keys())

    for meal_name, items in meal_plan.items():
        icon, card_class = MEAL_ICONS.get(meal_name, ("🍽️", "meal-card"))
        meal_nut = calc_meal_nutrients(items)
        meal_cal = meal_nut.get("Energy", 0)

        with st.expander(f"{icon} {meal_name}  —  {meal_cal:.0f} kcal", expanded=True):
            rows_to_delete = []

            for idx, item in enumerate(items):
                c1, c2, c3 = st.columns([3, 1.5, 0.5])
                with c1:
                    food_choice = st.selectbox(
                        f"الطعام",
                        all_foods_display,
                        index=all_foods_display.index(item["name"]) if item["name"] in all_foods_display else 0,
                        key=f"{meal_name}_{idx}_food",
                        label_visibility="collapsed"
                    )
                    item["name"] = food_choice
                    item["key"]  = all_foods_ar[food_choice]
                with c2:
                    new_amt = st.number_input(
                        "الكمية (جم)",
                        min_value=5, max_value=1000,
                        value=int(item["amount"]),
                        step=5,
                        key=f"{meal_name}_{idx}_amt",
                        label_visibility="collapsed"
                    )
                    item["amount"] = new_amt
                with c3:
                    if st.button("🗑️", key=f"del_{meal_name}_{idx}", help="حذف هذا الصنف"):
                        rows_to_delete.append(idx)

            for idx in sorted(rows_to_delete, reverse=True):
                items.pop(idx)

            # إضافة صنف جديد
            st.markdown("---")
            add_col1, add_col2, add_col3 = st.columns([3, 1.5, 1])
            with add_col1:
                new_food = st.selectbox(
                    "أضف طعاماً",
                    ["-- اختر --"] + all_foods_display,
                    key=f"add_{meal_name}_food",
                    label_visibility="collapsed"
                )
            with add_col2:
                new_food_amt = st.number_input(
                    "كمية",
                    min_value=5, max_value=1000,
                    value=100, step=5,
                    key=f"add_{meal_name}_amt",
                    label_visibility="collapsed"
                )
            with add_col3:
                if st.button("➕ أضف", key=f"add_{meal_name}_btn") and new_food != "-- اختر --":
                    items.append({
                        "name":   new_food,
                        "amount": new_food_amt,
                        "unit":   "جم",
                        "key":    all_foods_ar[new_food]
                    })
                    st.rerun()

            # تفاصيل ماكرو الوجبة
            if show_macros and items:
                mn = calc_meal_nutrients(items)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("🔥 سعرات",  f"{mn.get('Energy',0):.0f}")
                m2.metric("💪 بروتين", f"{mn.get('Protein',0):.1f}g")
                m3.metric("🍞 كارب",   f"{mn.get('Carbohydrate, by difference',0):.1f}g")
                m4.metric("🥑 دهون",   f"{mn.get('Total lipid (fat)',0):.1f}g")

    # ---- ملخص اليوم ----
    st.divider()
    st.markdown("### 📊 ملخص اليوم الغذائي")

    day_totals = {}
    for items in meal_plan.values():
        mn = calc_meal_nutrients(items)
        for k, v in mn.items():
            day_totals[k] = day_totals.get(k, 0) + v

    total_day_cal  = day_totals.get("Energy", 0)
    total_day_pro  = day_totals.get("Protein", 0)
    total_day_fat  = day_totals.get("Total lipid (fat)", 0)
    total_day_carb = day_totals.get("Carbohydrate, by difference", 0)
    total_day_fib  = day_totals.get("Fiber, total dietary", 0)

    diff     = total_day_cal - target_cal
    diff_str = f"+{diff:.0f}" if diff > 0 else f"{diff:.0f}"
    diff_col = "#f44336" if abs(diff) > 200 else "#4caf50"

    st.markdown(
        f'<div class="total-bar">'
        f'<h3>🔥 إجمالي السعرات: {total_day_cal:.0f} kcal</h3>'
        f'<p style="margin:4px 0 0;">الهدف: {target_cal} kcal &nbsp;|&nbsp; '
        f'<span style="color:{"#ffeb3b" if abs(diff)>200 else "#b9f6ca"}">{diff_str} kcal</span></p>'
        f'</div>',
        unsafe_allow_html=True
    )

    # تنبيه إذا بعيد عن الهدف
    if abs(diff) > 300:
        if diff > 0:
            st.markdown(
                f'<div class="warning-bar">⚠️ الجدول يزيد عن هدفك بـ {diff:.0f} kcal — '
                f'حاول تقليل الكميات أو استبدال بعض الأصناف.</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="warning-bar">⚠️ الجدول ينقص عن هدفك بـ {abs(diff):.0f} kcal — '
                f'يمكنك إضافة وجبات أو زيادة الكميات.</div>',
                unsafe_allow_html=True
            )

    # شريط الماكرو
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💪 بروتين",     f"{total_day_pro:.0f} جم",  f"{total_day_pro*4/total_day_cal*100:.0f}% من السعرات" if total_day_cal else "")
    c2.metric("🍞 كارب",       f"{total_day_carb:.0f} جم", f"{total_day_carb*4/total_day_cal*100:.0f}% من السعرات" if total_day_cal else "")
    c3.metric("🥑 دهون",       f"{total_day_fat:.0f} جم",  f"{total_day_fat*9/total_day_cal*100:.0f}% من السعرات" if total_day_cal else "")
    c4.metric("🌿 ألياف",      f"{total_day_fib:.0f} جم",  f"الهدف 28 جم")

    # مقارنة مع الهدف المستورد من tab1
    if "pro_g" in st.session_state:
        st.markdown('<div class="section-title">مقارنة مع التوصيات الشخصية</div>', unsafe_allow_html=True)
        tgt_p = st.session_state["pro_g"]
        tgt_f = st.session_state["fat_g"]
        tgt_c = st.session_state["carb_g"]

        rows = [
            ("💪 بروتين",     total_day_pro,  tgt_p, "جم"),
            ("🥑 دهون",       total_day_fat,  tgt_f, "جم"),
            ("🍞 كربوهيدرات", total_day_carb, tgt_c, "جم"),
        ]
        table_html = '<table class="summary-table"><tr><th>العنصر</th><th>الفعلي</th><th>الهدف</th><th>الفارق</th></tr>'
        for label, actual, target_v, unit in rows:
            diff_v    = actual - target_v
            diff_sign = f"+{diff_v:.0f}" if diff_v > 0 else f"{diff_v:.0f}"
            color     = "#f44336" if abs(diff_v) > target_v * 0.15 else "#2e7d32"
            table_html += (
                f'<tr><td>{label}</td><td>{actual:.0f} {unit}</td>'
                f'<td>{target_v:.0f} {unit}</td>'
                f'<td style="color:{color};font-weight:700;">{diff_sign} {unit}</td></tr>'
            )
        table_html += '</table>'
        st.markdown(table_html, unsafe_allow_html=True)

    # ---- جدول متعدد الأيام ----
    if num_days > 1:
        st.divider()
        st.markdown(f"### 📅 جدول {num_days} أيام")
        st.markdown(
            '<div class="info-bar">💡 الجدول متكرر مع اقتراح تنويع بسيط في المصادر البروتينية كل يوم.</div>',
            unsafe_allow_html=True
        )

        protein_sources = ["chicken breast", "tuna", "beef", "salmon", "egg", "lentils", "falafel", "shrimp"]
        protein_names   = {k: LOCAL_DB[k]["name_ar"] for k in protein_sources if k in LOCAL_DB}

        for day in range(1, num_days + 1):
            st.markdown(f'<div class="plan-day-header">📆 اليوم {day}</div>', unsafe_allow_html=True)
            day_cal = 0
            for meal_name, items in meal_plan.items():
                icon, _ = MEAL_ICONS.get(meal_name, ("🍽️", ""))
                mn = calc_meal_nutrients(items)
                cal = mn.get("Energy", 0)
                day_cal += cal

                # تنويع مصدر البروتين في الغداء والعشاء
                display_items = []
                for it in items:
                    if it["key"] in protein_sources and meal_name in ["الغداء", "العشاء"]:
                        idx_src = (protein_sources.index(it["key"]) + day - 1) % len(protein_sources)
                        alt_key = protein_sources[idx_src]
                        display_items.append({**it, "name": LOCAL_DB[alt_key]["name_ar"], "key": alt_key})
                    else:
                        display_items.append(it)

                items_str = " · ".join(
                    [f"{it['name']} ({it['amount']} {it['unit']})" for it in display_items]
                )
                st.markdown(
                    f'<div class="meal-card">'
                    f'<div class="meal-header"><span>{icon} {meal_name}</span>'
                    f'<span class="cal-badge">{cal:.0f} kcal</span></div>'
                    f'<div style="font-size:0.9em;color:#555;">{items_str}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            st.markdown(
                f'<div style="text-align:left;font-size:0.85em;color:#777;margin-bottom:6px;">'
                f'إجمالي اليوم {day}: <strong>{day_cal:.0f} kcal</strong></div>',
                unsafe_allow_html=True
            )

    st.divider()
    st.caption("* القيم الغذائية مبنية على قاعدة بيانات USDA. الجدول للإرشاد العام — يُنصح بمراجعة أخصائي تغذية.")

import streamlit as st
import requests
import os

# ===========================================================================
# إعدادات الصفحة
# ===========================================================================
st.set_page_config(
    page_title="محلل القيم الغذائية",
    page_icon="🥗",
    layout="centered",
)

# ===========================================================================
# CSS مخصص لدعم العربية والموبايل
# ===========================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
    }
    .main { background-color: #f8f9fa; }
    .block-container { padding: 1rem 1rem 2rem; max-width: 720px; }
    h1 { color: #2e7d32; text-align: center; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 6px 0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        display: flex;
        justify-content: space-between;
        align-items: center;
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
    .stProgress > div > div > div { background-color: #4caf50; }
</style>
""", unsafe_allow_html=True)

# ===========================================================================
# القيم اليومية الموصى بها DRI
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
                         params={"query": query, "pageSize": 8,
                                 "api_key": USDA_API_KEY,
                                 "dataType": "Foundation,SR Legacy"},
                         timeout=10)
        return r.json().get("foods", [])
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
        res = [(k, v) for k, v in LOCAL_DB.items()
               if any(w in k for w in q.split())]
    return res

def scale(nutrients, weight):
    f = weight / 100.0
    return {k: v * f for k, v in nutrients.items()}

def classify(pct):
    if pct >= 20: return "غني",  "badge-rich"
    if pct >= 10: return "متوسط","badge-mid"
    if pct > 0:   return "قليل", "badge-low"
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

# ===========================================================================
# واجهة Streamlit
# ===========================================================================

st.markdown("# 🥗 محلل القيم الغذائية")
st.markdown("**مبني على USDA FoodData Central · معايير WHO/DRI 2023**")
st.divider()

col1, col2 = st.columns([3, 1])
with col1:
    food_input = st.text_input("🔍 اسم الطعام (عربي أو إنجليزي)",
                                placeholder="مثال: موز، صدر دجاج، avocado...")
with col2:
    weight = st.number_input("الكمية (جم)", min_value=1, max_value=2000,
                              value=100, step=10)

analyze_btn = st.button("تحليل الآن", type="primary", use_container_width=True)

if analyze_btn and food_input:
    english_q = translate_query(food_input)
    nutrients_raw = None
    food_name = food_input
    source = ""
    fdc_id = None
    search_results = []

    # --- USDA API ---
    with st.spinner("جاري البحث في USDA FoodData Central..."):
        api_results = search_usda(english_q)

    if api_results:
        search_results = api_results
        options = {f"{i['description']}": i for i in api_results}
        chosen_label = st.selectbox("اختر الطعام الأقرب لما تريده:", list(options.keys()))
        chosen = options[chosen_label]
        fdc_id = chosen["fdcId"]
        food_name = chosen["description"]

        with st.spinner("جاري جلب التفاصيل..."):
            detail = get_usda_detail(fdc_id)
        nutrients_raw = extract_nutrients(detail)
        source = f"USDA FoodData Central — FDC ID: {fdc_id}"

    # --- Fallback محلي ---
    if not nutrients_raw:
        local = search_local(english_q) or search_local(food_input)
        if local:
            if len(local) == 1:
                key, val = local[0]
            else:
                opts = {v["name_ar"] + f" ({k})": (k, v) for k, v in local}
                ch = st.selectbox("اختر من القائمة:", list(opts.keys()))
                key, val = opts[ch]
            food_name = val["name_ar"]
            nutrients_raw = val["nutrients"]
            source = "قاعدة بيانات محلية (USDA-based)"
        else:
            st.error(f"عذراً، لم يُعثر على **{food_input}**. جرب اسماً آخر أو اكتبه بالإنجليزية.")
            st.stop()

    # --- الحساب ---
    ns = scale(nutrients_raw, weight)
    total_cal = ns.get("Energy", 0) or (
        ns.get("Protein", 0) * 4 +
        ns.get("Total lipid (fat)", 0) * 9 +
        ns.get("Carbohydrate, by difference", 0) * 4 +
        ns.get("Fiber, total dietary", 0) * 2
    )

    # --- العرض ---
    st.divider()
    st.markdown(f"### 📋 {food_name} — {weight} جم")
    st.caption(f"المصدر: {source}")

    # السعرات — بطاقات رئيسية
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔥 سعرات",    f"{total_cal:.0f} kcal")
    c2.metric("💪 بروتين",   f"{ns.get('Protein', 0):.1f} g")
    c3.metric("🍞 كارب",     f"{ns.get('Carbohydrate, by difference', 0):.1f} g")
    c4.metric("🥑 دهون",     f"{ns.get('Total lipid (fat)', 0):.1f} g")

    # توزيع السعرات
    cal_p = ns.get("Protein", 0) * 4
    cal_f = ns.get("Total lipid (fat)", 0) * 9
    cal_c = ns.get("Carbohydrate, by difference", 0) * 4
    if total_cal > 0:
        st.markdown('<div class="section-title">توزيع السعرات</div>', unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("من البروتين",      f"{cal_p/total_cal*100:.0f}%")
        col_b.metric("من الدهون",        f"{cal_f/total_cal*100:.0f}%")
        col_c.metric("من الكربوهيدرات", f"{cal_c/total_cal*100:.0f}%")

    def render_section(title, keys):
        items = [(k, ns.get(k, 0)) for k in keys if ns.get(k, 0) > 0]
        if not items:
            return
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
        for k, val in items:
            info = DRI[k]
            pct = min(val / info["dri"] * 100, 100)
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

    render_section("🧪 العناصر الكبرى (Macros)",
                   ["Protein","Total lipid (fat)","Carbohydrate, by difference",
                    "Fiber, total dietary","Sugars, total including NLEA"])
    render_section("⚗️ المعادن",
                   ["Calcium, Ca","Iron, Fe","Potassium, K","Sodium, Na",
                    "Magnesium, Mg","Phosphorus, P","Zinc, Zn"])
    render_section("💊 الفيتامينات",
                   ["Vitamin C, total ascorbic acid","Vitamin A, RAE",
                    "Vitamin D (D2 + D3)","Vitamin B-12","Vitamin B-6",
                    "Folate, total","Vitamin K (phylloquinone)",
                    "Vitamin E (alpha-tocopherol)","Thiamin","Riboflavin","Niacin"])
    render_section("🫀 الدهون المفصّلة",
                   ["Fatty acids, total saturated","Fatty acids, total monounsaturated",
                    "Fatty acids, total polyunsaturated","Cholesterol"])

    # الملاحظات الذكية
    notes = smart_notes(ns)
    if notes:
        st.markdown('<div class="section-title">💡 ملاحظات غذائية وصحية</div>',
                    unsafe_allow_html=True)
        for note in notes:
            st.markdown(f'<div class="note-card">{note}</div>', unsafe_allow_html=True)

    st.divider()
    st.caption("* القيم اليومية مبنية على نظام 2000 سعرة — قد تختلف حسب العمر والجنس ومستوى النشاط.")

elif analyze_btn and not food_input:
    st.warning("من فضلك أدخل اسم الطعام أولاً.")

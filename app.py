# =============================================================================
# NutraX V10 — Professional Edition
# ✅ UI احترافي كامل  ✅ قاعدة بيانات موسعة (100+ صنف)
# ✅ ملاحظات ونصائح لكل صنف  ✅ BMI في الداشبورد
# ✅ تأكيد قبل الحذف  ✅ Safety check كامل
# =============================================================================

import streamlit as st
import sqlite3, hashlib, os, json
from datetime import datetime

st.set_page_config(page_title="NutraX", page_icon="🥗", layout="wide")

# ══════════════════════════════════════════
# CSS
# ══════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;900&display=swap');
*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"]{font-family:'Cairo',sans-serif!important;direction:rtl}
.stApp{background:radial-gradient(ellipse at top left,#0d2137 0%,#071525 40%,#020d18 100%);min-height:100vh}

/* sidebar */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0e2540 0%,#071525 100%)!important;border-left:1px solid rgba(0,210,255,.12)}
[data-testid="stSidebar"] .stButton>button{width:100%;text-align:right;background:transparent;color:#c8e8ff;border:1px solid transparent;border-radius:10px;padding:11px 16px;margin-bottom:4px;font-family:'Cairo',sans-serif;font-size:14.5px;font-weight:500;transition:all .2s ease;letter-spacing:.2px}
[data-testid="stSidebar"] .stButton>button:hover{background:rgba(0,210,255,.1);border-color:rgba(0,210,255,.25);color:#fff;transform:translateX(-4px)}

/* card */
.card{background:linear-gradient(135deg,rgba(255,255,255,.06) 0%,rgba(255,255,255,.02) 100%);border:1px solid rgba(0,210,255,.18);border-radius:18px;padding:22px 24px;backdrop-filter:blur(12px);transition:transform .25s,box-shadow .25s;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,rgba(0,210,255,.5),transparent)}
.card:hover{transform:translateY(-4px);box-shadow:0 12px 30px rgba(0,0,0,.4)}
.card .c-label{color:#7fb8d8;font-size:13px;font-weight:600;margin-bottom:6px;letter-spacing:.5px}
.card .c-value{color:#fff;font-size:30px;font-weight:800;line-height:1}
.card .c-unit{color:#7fb8d8;font-size:12px;margin-top:4px}
.card .c-icon{font-size:28px;margin-bottom:8px}

/* section title */
.sec-title{color:#00d4ff;font-size:22px;font-weight:800;padding-bottom:10px;border-bottom:2px solid rgba(0,212,255,.2);margin-bottom:22px;letter-spacing:.3px}

/* food card */
.food-card{background:rgba(255,255,255,.04);border:1px solid rgba(0,210,255,.16);border-radius:14px;padding:16px 20px;margin-bottom:12px;border-right:4px solid #00b4d8;transition:border-color .2s}
.food-card:hover{border-right-color:#00ffcc}
.food-card .fc-name{color:#fff;font-size:17px;font-weight:700;margin-bottom:10px}
.food-card .fc-note{background:rgba(0,210,255,.07);border-right:3px solid rgba(0,210,255,.4);border-radius:8px;padding:8px 12px;color:#a8d8f0;font-size:13px;margin-top:10px;line-height:1.6}
.food-card .fc-tip{background:rgba(255,200,0,.07);border-right:3px solid rgba(255,200,0,.4);border-radius:8px;padding:8px 12px;color:#ffe082;font-size:13px;margin-top:8px;line-height:1.6}

/* pills */
.pills{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.pill{padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600}
.pill-cal{background:rgba(0,180,216,.18);color:#80d8ff;border:1px solid rgba(0,180,216,.3)}
.pill-p{background:rgba(76,175,80,.18);color:#a5d6a7;border:1px solid rgba(76,175,80,.3)}
.pill-c{background:rgba(255,167,38,.18);color:#ffcc80;border:1px solid rgba(255,167,38,.3)}
.pill-f{background:rgba(244,67,54,.18);color:#ef9a9a;border:1px solid rgba(244,67,54,.3)}

/* progress */
.prog-wrap{background:rgba(255,255,255,.07);border-radius:20px;height:10px;overflow:hidden;margin:5px 0 12px}
.prog-fill{height:10px;border-radius:20px;transition:width .6s}
.prog-cal{background:linear-gradient(90deg,#0096c7,#00d4ff)}
.prog-p{background:linear-gradient(90deg,#388e3c,#66bb6a)}
.prog-c{background:linear-gradient(90deg,#e65100,#ffa726)}
.prog-f{background:linear-gradient(90deg,#c62828,#ef5350)}

/* alerts */
.alert-warn{background:rgba(255,152,0,.1);border:1px solid rgba(255,152,0,.35);border-radius:14px;padding:16px 20px;color:#ffcc80;margin-bottom:18px}
.alert-info{background:rgba(0,180,216,.1);border:1px solid rgba(0,180,216,.3);border-radius:14px;padding:14px 18px;color:#80d8ff;margin-bottom:14px}
.alert-success{background:rgba(76,175,80,.1);border:1px solid rgba(76,175,80,.3);border-radius:14px;padding:14px 18px;color:#a5d6a7;margin-bottom:14px}

/* bmi */
.bmi-badge{display:inline-block;padding:6px 18px;border-radius:30px;font-size:14px;font-weight:700;margin-top:6px}
.bmi-under{background:rgba(33,150,243,.2);color:#90caf9;border:1px solid rgba(33,150,243,.4)}
.bmi-normal{background:rgba(76,175,80,.2);color:#a5d6a7;border:1px solid rgba(76,175,80,.4)}
.bmi-over{background:rgba(255,152,0,.2);color:#ffcc80;border:1px solid rgba(255,152,0,.4)}
.bmi-obese{background:rgba(244,67,54,.2);color:#ef9a9a;border:1px solid rgba(244,67,54,.4)}

/* text */
h1,h2,h3,h4,h5,h6{color:#fff!important}
p,li,span{color:#dceeff}
strong{color:#fff!important}
.stMarkdown p{color:#dceeff!important}
.stMarkdown li{color:#dceeff!important}
.stMarkdown strong{color:#fff!important}
label,.stSelectbox label,.stNumberInput label,.stTextInput label{color:#9cc8e8!important;font-weight:600;font-size:14px}
[data-testid="stCaptionContainer"]{color:#7fb8d8!important}

/* inputs */
input,textarea{background:#0f2030!important;color:#fff!important;border:1px solid rgba(0,180,216,.35)!important;border-radius:10px!important;caret-color:#00d4ff!important}
input::placeholder,textarea::placeholder{color:#456a88!important;opacity:1!important}
input:-webkit-autofill{-webkit-text-fill-color:#fff!important;-webkit-box-shadow:0 0 0px 1000px #0f2030 inset!important}
.stSelectbox>div>div,[data-baseweb="select"]>div{background:#0f2030!important;color:#fff!important;border:1px solid rgba(0,180,216,.35)!important;border-radius:10px!important}
[data-baseweb="select"] span{color:#fff!important}

/* buttons */
.stButton>button{background:linear-gradient(135deg,#005f8a,#0096c7);color:#fff;border:none;border-radius:10px;font-family:'Cairo',sans-serif;font-weight:700;font-size:14px;padding:10px 22px;transition:all .2s}
.stButton>button:hover{background:linear-gradient(135deg,#0077aa,#00b4d8);transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,180,216,.35)}

/* tabs */
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03);border-radius:12px;padding:4px;gap:4px}
.stTabs [data-baseweb="tab"]{color:#7fb8d8;border-radius:8px;font-family:'Cairo',sans-serif;font-weight:600}
.stTabs [aria-selected="true"]{background:rgba(0,180,216,.18)!important;color:#00d4ff!important}

/* expander */
.streamlit-expanderHeader{background:rgba(255,255,255,.04)!important;border-radius:12px!important;color:#c8e8ff!important;font-weight:600!important;border:1px solid rgba(0,180,216,.15)!important}
.streamlit-expanderContent{background:rgba(255,255,255,.02)!important;border:1px solid rgba(0,180,216,.1)!important;border-top:none!important;border-radius:0 0 12px 12px!important}

/* metric */
[data-testid="metric-container"]{background:rgba(255,255,255,.04);border:1px solid rgba(0,180,216,.18);border-radius:14px;padding:14px}
[data-testid="metric-container"] label{color:#7fb8d8!important;font-weight:600}
[data-testid="stMetricValue"]{color:#fff!important;font-weight:800}

/* st alerts */
.stSuccess{background:rgba(76,175,80,.12)!important;color:#a5d6a7!important;border-radius:12px!important;border:1px solid rgba(76,175,80,.3)!important}
.stError{background:rgba(244,67,54,.12)!important;color:#ef9a9a!important;border-radius:12px!important;border:1px solid rgba(244,67,54,.3)!important}
.stWarning{background:rgba(255,152,0,.12)!important;color:#ffcc80!important;border-radius:12px!important;border:1px solid rgba(255,152,0,.3)!important}
.stInfo{background:rgba(0,180,216,.10)!important;color:#80d8ff!important;border-radius:12px!important;border:1px solid rgba(0,180,216,.25)!important}

/* suggestion */
.sug-box{background:linear-gradient(135deg,rgba(0,100,160,.2),rgba(0,180,216,.08));border:1px solid rgba(0,180,216,.28);border-radius:14px;padding:16px 18px;margin-bottom:10px;transition:border-color .2s}
.sug-box:hover{border-color:rgba(0,210,255,.5)}
.sug-box h4{color:#00d4ff;margin:0 0 8px 0;font-size:15px}

hr{border-color:rgba(0,180,216,.15)!important;margin:20px 0!important}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:#071525}
::-webkit-scrollbar-thumb{background:#1a4a6e;border-radius:10px}
::-webkit-scrollbar-thumb:hover{background:#0096c7}

/* login */
.login-logo{text-align:center;padding:50px 0 28px}
.login-logo .logo-icon{font-size:64px;filter:drop-shadow(0 0 20px rgba(0,180,216,.5))}
.login-logo h1{font-size:46px;font-weight:900;background:linear-gradient(90deg,#00b4d8,#00ffcc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:10px 0 4px}
.login-logo p{color:#7fb8d8;font-size:16px;margin:0}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════
DB_FILE = "nutrax_v10.db"
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

# ══════════════════════════════════════════
# FOOD DB — 100+ items with notes & tips
# ══════════════════════════════════════════
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
# ══════════════════════════════════════════
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
for k,v in [("page","login"),("user",None),("targets",None),("confirm_del",None)]:
    if k not in st.session_state: st.session_state[k]=v
REQUIRED={"cal","p","c","f","goal"}

# ══════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════
if st.session_state.page=="login":
    st.markdown("""
    <div class="login-logo">
        <div class="logo-icon">🥗</div>
        <h1>NutraX</h1>
        <p>مساعدك الذكي للتغذية الصحية — تحليل · تخطيط · متابعة</p>
    </div>""", unsafe_allow_html=True)
    _,mid,_ = st.columns([1,2,1])
    with mid:
        t1,t2=st.tabs(["🔑 تسجيل الدخول","✨ حساب جديد"])
        with t1:
            with st.form("lgn"):
                e=st.text_input("📧 البريد الإلكتروني")
                p=st.text_input("🔒 كلمة المرور",type="password")
                if st.form_submit_button("دخول ←",use_container_width=True):
                    c.execute("SELECT * FROM users WHERE email=? AND password=?",(e,hp(p)))
                    u=c.fetchone()
                    if u: st.session_state.user=u; st.session_state.page="dashboard"; st.rerun()
                    else: st.error("البريد أو كلمة المرور غير صحيحة")
        with t2:
            with st.form("reg"):
                n=st.text_input("👤 الاسم الكامل"); e2=st.text_input("📧 البريد الإلكتروني")
                p2=st.text_input("🔒 كلمة المرور",type="password")
                by=st.number_input("📅 سنة الميلاد",1950,2010,1995)
                cn=st.selectbox("🌍 البلد",["Egypt","Saudi Arabia","UAE","Kuwait","Qatar","Bahrain","Jordan","Other"])
                if st.form_submit_button("إنشاء الحساب ←",use_container_width=True):
                    try:
                        c.execute("INSERT INTO users (email,password,name,birth_year,country,is_admin) VALUES (?,?,?,?,?,0)",
                                  (e2,hp(p2),n,by,cn)); conn.commit(); st.success("تم! سجل دخولك.")
                    except: st.error("البريد الإلكتروني مستخدم بالفعل")

# ══════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════
else:
    if st.session_state.user is None or len(st.session_state.user)<5:
        st.session_state.user=None; st.session_state.page="login"; st.rerun()
    if st.session_state.targets and not REQUIRED.issubset(st.session_state.targets.keys()):
        st.session_state.targets=None
    u=st.session_state.user; u_id=u[0]

    # SIDEBAR
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:24px 0 12px">
            <div style="font-size:52px;filter:drop-shadow(0 0 14px rgba(0,180,216,.5))">👤</div>
            <div style="color:#fff;font-size:18px;font-weight:700;margin:8px 0 2px">{u[3]}</div>
            <div style="color:#3a6a8a;font-size:12px">{u[1]}</div>
        </div>""", unsafe_allow_html=True)
        st.divider()
        for icon,label,pg in [("🏠","الرئيسية","dashboard"),("⚙️","الإعدادات والهدف","profile_setup"),
            ("🔍","محلل الطعام","analyzer"),("📅","مصمم الجدول","planner"),
            ("💡","مقترح الوجبات","suggester"),("💾","جداولي المحفوظة","saved"),("📈","سجل الوزن","history"),
            ("📚","المرجع الكلينيكي","clinical")]:
            mark="⬤ " if st.session_state.page==pg else ""
            if st.button(f"{mark}{icon}  {label}",key=f"nav_{pg}"):
                st.session_state.page=pg; st.rerun()
        st.divider()
        if st.button("🚪  خروج",key="logout"):
            st.session_state.user=None; st.session_state.page="login"; st.rerun()
        st.markdown("<div style='text-align:center;color:#1e3a50;font-size:11px;margin-top:16px'>NutraX V10 © 2025</div>",unsafe_allow_html=True)

    # ── DASHBOARD ──
    if st.session_state.page=="dashboard":
        st.markdown("<div class='sec-title'>🏠 الرئيسية</div>",unsafe_allow_html=True)
        if not st.session_state.targets:
            st.markdown("<div class='alert-warn'>⚠️ <b>بياناتك غير مكتملة</b> — أكمل إعداداتك لحساب أهدافك الغذائية.</div>",unsafe_allow_html=True)
            if st.button("⚙️ اذهب للإعدادات"): st.session_state.page="profile_setup"; st.rerun()
        else:
            t=st.session_state.targets
            c.execute("SELECT COUNT(*) FROM saved_plans WHERE user_id=?",(u_id,)); pn=c.fetchone()[0]
            c.execute("SELECT weight FROM tracking WHERE user_id=? ORDER BY id DESC LIMIT 1",(u_id,)); lw=c.fetchone()
            cols=st.columns(4)
            for col,(ic,lb,val,un) in zip(cols,[("🎯","هدف السعرات",t['cal'],"kcal"),
                ("💪","بروتين يومي",t['p'],"جم"),("🍞","كاربوهيدرات",t['c'],"جم"),("🥑","دهون يومية",t['f'],"جم")]):
                col.markdown(f'<div class="card" style="text-align:center"><div class="c-icon">{ic}</div><div class="c-label">{lb}</div><div class="c-value">{val}</div><div class="c-unit">{un}</div></div>',unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            c1,c2,c3=st.columns(3)
            with c1:
                if u[4] and u[5]:
                    bv,bcls,blbl=bmi_info(float(u[5]),float(u[4]))
                    st.markdown(f'<div class="card"><div class="c-label">📏 مؤشر كتلة الجسم (BMI)</div><div class="c-value">{bv}</div><div class="bmi-badge {bcls}">{blbl}</div></div>',unsafe_allow_html=True)
                else:
                    st.markdown("<div class='card'><div class='c-label'>📏 BMI</div><div class='c-unit'>أكمل إعداداتك</div></div>",unsafe_allow_html=True)
            with c2:
                wv=f"{lw[0]} كجم" if lw else "لم يُسجَّل"
                st.markdown(f'<div class="card" style="text-align:center"><div class="c-icon">⚖️</div><div class="c-label">آخر وزن مسجل</div><div class="c-value" style="font-size:22px">{wv}</div></div>',unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="card" style="text-align:center"><div class="c-icon">💾</div><div class="c-label">جداولك المحفوظة</div><div class="c-value">{pn}</div><div class="c-unit">جدول</div></div>',unsafe_allow_html=True)
            gl={"fat_loss":"🔥 خسارة دهون","muscle_gain":"💪 بناء عضل","maintain":"⚖️ ثبات الوزن"}
            st.markdown(f"<div class='alert-info'>هدفك: <b>{gl.get(t['goal'],t['goal'])}</b> | TDEE: <b>{t.get('tdee','—')} kcal</b> | هدف: <b>{t['cal']} kcal/يوم</b></div>",unsafe_allow_html=True)

    # ── PROFILE ──
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
                    format_func=lambda x:{1.2:"مستقر (لا رياضة)",1.375:"خفيف (1-3 أيام)",
                        1.55:"معتدل (3-5 أيام)",1.725:"نشيط (6-7 أيام)",1.9:"رياضي محترف"}[x])
            if st.form_submit_button("💾 حفظ وحساب الأهداف",use_container_width=True):
                c.execute("UPDATE users SET height=?,weight=?,goal=?,birth_year=? WHERE id=?",(h,w,goal,datetime.now().year-age,u_id)); conn.commit()
                st.session_state.targets=calc_targets(w,h,age,goal,act)
                c.execute("SELECT * FROM users WHERE id=?",(u_id,)); st.session_state.user=c.fetchone()
                st.success("✅ تم الحفظ!"); st.session_state.page="dashboard"; st.rerun()

    # ── ANALYZER ──
    elif st.session_state.page=="analyzer":
        st.markdown("<div class='sec-title'>🔍 محلل الطعام</div>",unsafe_allow_html=True)
        cats=sorted(set(v["cat"] for v in LOCAL_DB.values()))
        sel_cat=st.selectbox("📂 تصفية حسب الفئة",["الكل"]+cats)
        search=st.text_input("🔎 ابحث عن طعام بالعربي أو الإنجليزي")
        filtered=dict(LOCAL_DB)
        if sel_cat!="الكل": filtered={k:v for k,v in filtered.items() if v["cat"]==sel_cat}
        if search:
            s=search.lower()
            filtered={k:v for k,v in filtered.items() if s in k.lower() or s in v["name"]}
        if not search and sel_cat!="الكل" and sel_cat in CATEGORY_TIPS:
            st.markdown(f"<div class='alert-info'>💡 <b>نصيحة الفئة:</b> {CATEGORY_TIPS[sel_cat]}</div>",unsafe_allow_html=True)
        st.markdown(f"<div style='color:#3a6a8a;font-size:13px;margin-bottom:12px'>عدد النتائج: {len(filtered)} صنف من أصل {len(LOCAL_DB)}</div>",unsafe_allow_html=True)
        if filtered:
            for k,v in list(filtered.items())[:30]:
                st.markdown(f"""<div class="food-card">
                    <div class="fc-name">{v['name']} <span style="color:#2a5a78;font-size:12px">{v['cat']}</span></div>
                    <div class="pills">
                        <span class="pill pill-cal">🔥 {v['cal']} kcal</span>
                        <span class="pill pill-p">💪 بروتين {v['p']}ج</span>
                        <span class="pill pill-c">🍞 كارب {v['c']}ج</span>
                        <span class="pill pill-f">🥑 دهون {v['f']}ج</span>
                    </div>
                    <div style="color:#2a5070;font-size:11px;margin:4px 0 8px">القيم لكل 100 جرام</div>
                    <div class="fc-note">📋 {v['note']}</div>
                    <div class="fc-tip">{v['tip']}</div>
                </div>""",unsafe_allow_html=True)
            if len(filtered)>30: st.info("يتم عرض أول 30 نتيجة. ابحث بكلمة أدق لتضييق النتائج.")
        else:
            st.markdown("<div class='alert-warn'>لم يتم العثور على نتائج.</div>",unsafe_allow_html=True)

    # ── PLANNER ──
    elif st.session_state.page=="planner":
        st.markdown("<div class='sec-title'>📅 مصمم الجدول الغذائي</div>",unsafe_allow_html=True)
        if not st.session_state.targets:
            st.markdown("<div class='alert-warn'>⚠️ أكمل إعداداتك أولاً.</div>",unsafe_allow_html=True)
            if st.button("⚙️ الإعدادات"): st.session_state.page="profile_setup"; st.rerun()
            st.stop()
        t=st.session_state.targets
        st.markdown(f"<div class='alert-info'>🎯 هدفك اليومي: <b>{t['cal']} kcal</b> | 💪 {t['p']}ج | 🍞 {t['c']}ج | 🥑 {t['f']}ج</div>",unsafe_allow_html=True)
        days=st.number_input("عدد الأيام",1,14,1)
        plan={}; total_cal=total_p=total_c=total_f=0
        food_opts=list(LOCAL_DB.keys())
        food_lbls={k:f"{LOCAL_DB[k]['name']} ({LOCAL_DB[k]['cat']})" for k in food_opts}
        for d in range(days):
            with st.expander(f"📆 يوم {d+1}",expanded=(d==0)):
                plan[d]={}; cols=st.columns(4)
                for i,meal in enumerate(["🌅 فطار","☀️ غداء","🌙 عشاء","🍎 سناك"]):
                    with cols[i]:
                        st.markdown(f"**{meal}**")
                        foods=st.multiselect("اختر",food_opts,format_func=lambda k:food_lbls[k],key=f"ms_{d}_{i}")
                        plan[d][meal]={}
                        for fk in foods:
                            g=st.number_input(f"{LOCAL_DB[fk]['name']} (جم)",0,1000,100,key=f"gi_{d}_{i}_{fk}")
                            if g>0:
                                plan[d][meal][fk]=g; m=macros(fk,g)
                                total_cal+=m["cal"]; total_p+=m["p"]; total_c+=m["c"]; total_f+=m["f"]
                                st.caption(f"🔥{m['cal']} | 💪{m['p']}ج | 🍞{m['c']}ج | 🥑{m['f']}ج")
        st.divider()
        st.markdown("### 📊 ملخص الجدول")
        mc1,mc2=st.columns(2)
        with mc1:
            for lbl,val,tgt,css in [("🔥 سعرات",int(total_cal),t['cal']*days,"prog-cal"),
                ("💪 بروتين",int(total_p),t['p']*days,"prog-p"),
                ("🍞 كارب",int(total_c),t['c']*days,"prog-c"),
                ("🥑 دهون",int(total_f),t['f']*days,"prog-f")]:
                pct=int(val/tgt*100) if tgt>0 else 0
                st.markdown(f"**{lbl}: {val} / {tgt}** ({pct}%)")
                st.markdown(prog(pct,css),unsafe_allow_html=True)
        with mc2:
            diff=total_cal-t['cal']*days
            st.markdown(f"**الفارق:** {diff_badge(diff)}",unsafe_allow_html=True)
            if abs(diff)<100:  st.markdown("<div class='alert-success'>ممتاز! الجدول متوازن تماماً 🎯</div>",unsafe_allow_html=True)
            elif diff>0:       st.markdown(f"<div class='alert-warn'>زيادة {int(diff)} kcal — قلل بعض الكميات.</div>",unsafe_allow_html=True)
            else:              st.markdown(f"<div class='alert-warn'>ناقص {int(abs(diff))} kcal — أضف وجبة.</div>",unsafe_allow_html=True)
        st.divider()
        cn1,cn2=st.columns(2)
        with cn1: pname=st.text_input("📝 اسم الجدول",value=f"جدول {datetime.now().strftime('%d/%m/%Y')}")
        with cn2: ptype=st.selectbox("📁 نوع",["خاص بي","للعميل","عام"])
        if st.button("💾 حفظ الجدول",use_container_width=True):
            c.execute("INSERT INTO saved_plans VALUES (NULL,?,?,?,datetime('now'),?)",
                      (u_id,pname,json.dumps({str(k):v for k,v in plan.items()}),ptype))
            conn.commit(); st.success("✅ تم حفظ الجدول!"); st.rerun()

    # ── SUGGESTER ──
    elif st.session_state.page=="suggester":
        st.markdown("<div class='sec-title'>💡 مقترح الوجبات الذكي</div>",unsafe_allow_html=True)
        if not st.session_state.targets:
            st.warning("أكمل الإعدادات أولاً")
            if st.button("⚙️ الإعدادات"): st.session_state.page="profile_setup"; st.rerun()
            st.stop()
        t=st.session_state.targets
        st.markdown("<div class='alert-info'>أدخل ما أكلته اليوم وسنقترح لك الوجبات المتبقية المناسبة.</div>",unsafe_allow_html=True)
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
                for lb,vl in [("🔥 سعرات",f"{ec} kcal"),("💪 بروتين",f"{ep}ج"),("🍞 كارب",f"{ecc}ج"),("🥑 دهون",f"{ef}ج")]:
                    st.markdown(f"- {lb}: {vl}")
            with r2:
                st.markdown("**🎯 المتبقي:**")
                for lb,vl in [("🔥 سعرات",f"{rem['cal']} kcal"),("💪 بروتين",f"{rem['p']}ج"),("🍞 كارب",f"{rem['c']}ج"),("🥑 دهون",f"{rem['f']}ج")]:
                    st.markdown(f"- {lb}: {vl}")
            st.divider()
            if rem["cal"]<50:
                st.markdown("<div class='alert-success'>🎉 وصلت لهدفك اليومي!</div>",unsafe_allow_html=True)
            else:
                st.markdown("### 🍽️ وجبات مقترحة:")
                for s in smart_suggest(rem["cal"],rem["p"],rem["c"],rem["f"]):
                    m=s["macro"]
                    st.markdown(f"""<div class="sug-box">
                        <h4>🍴 {s['name']} — {s['grams']} جرام &nbsp;<span style="color:#2a5a78;font-size:12px">{s['cat']}</span></h4>
                        <div class="pills">
                            <span class="pill pill-cal">🔥 {m['cal']} kcal</span>
                            <span class="pill pill-p">💪 {m['p']}ج</span>
                            <span class="pill pill-c">🍞 {m['c']}ج</span>
                            <span class="pill pill-f">🥑 {m['f']}ج</span>
                        </div>
                        <div class="fc-note">📋 {LOCAL_DB[s['key']]['note']}</div>
                    </div>""",unsafe_allow_html=True)

    # ── SAVED ──
    elif st.session_state.page=="saved":
        st.markdown("<div class='sec-title'>💾 جداولي المحفوظة</div>",unsafe_allow_html=True)
        ft=st.selectbox("🔎 فلتر",["الكل","خاص بي","للعميل","عام"])
        q="SELECT id,plan_name,created_at,type FROM saved_plans WHERE user_id=?"
        p=[u_id]
        if ft!="الكل": q+=" AND type=?"; p.append(ft)
        c.execute(q,p); rows=c.fetchall()
        if not rows:
            st.markdown("<div class='alert-info'>لا توجد جداول محفوظة. اذهب لمصمم الجدول وابدأ!</div>",unsafe_allow_html=True)
        else:
            for pid,pname,pdate,ptype in rows:
                with st.expander(f"📋 {pname}   |   {ptype}   |   {str(pdate)[:10]}"):
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
                        if st.button("🛒 المشتريات",key=f"sh_{pid}"):
                            shop=shopping(pd_raw)
                            st.markdown("**🛒 قائمة المشتريات:**")
                            for k,v in shop.items():
                                if k in LOCAL_DB: st.markdown(f"- {LOCAL_DB[k]['name']}: **{v} جرام**")
                        if st.session_state.confirm_del==pid:
                            st.warning("⚠️ هل أنت متأكد من الحذف؟")
                            cc1,cc2=st.columns(2)
                            if cc1.button("✅ نعم",key=f"yes_{pid}"):
                                c.execute("DELETE FROM saved_plans WHERE id=?",(pid,)); conn.commit()
                                st.session_state.confirm_del=None; st.rerun()
                            if cc2.button("❌ إلغاء",key=f"no_{pid}"):
                                st.session_state.confirm_del=None; st.rerun()
                        else:
                            if st.button("🗑️ حذف",key=f"del_{pid}"):
                                st.session_state.confirm_del=pid; st.rerun()

    # ── HISTORY ──
    elif st.session_state.page=="history":
        st.markdown("<div class='sec-title'>📈 سجل الوزن</div>",unsafe_allow_html=True)
        with st.form("wf"):
            wc1,_=st.columns([3,1])
            with wc1: w_in=st.number_input("⚖️ وزن اليوم (كجم)",30.0,300.0,70.0,.1)
            if st.form_submit_button("✅ تسجيل",use_container_width=True):
                c.execute("INSERT INTO tracking VALUES (NULL,?,?,datetime('now'))",(u_id,w_in))
                conn.commit(); st.success("تم التسجيل!"); st.rerun()
        c.execute("SELECT date,weight FROM tracking WHERE user_id=? ORDER BY id ASC",(u_id,))
        data=c.fetchall()
        if data:
            weights=[d[1] for d in data]
            m1,m2,m3=st.columns(3)
            m1.metric("📉 أقل وزن",f"{min(weights)} كجم")
            m2.metric("📈 أعلى وزن",f"{max(weights)} كجم")
            m3.metric("📊 آخر وزن",f"{weights[-1]} كجم",
                      delta=f"{round(weights[-1]-weights[0],1)} كجم" if len(weights)>1 else None)
            if st.session_state.targets and u[4]:
                bv,bcls,blbl=bmi_info(weights[-1],float(u[4]))
                st.markdown(f"<div class='alert-info'>📏 BMI الحالي: <b>{bv}</b> — <span class='bmi-badge {bcls}'>{blbl}</span></div>",unsafe_allow_html=True)
            st.line_chart({"الوزن (كجم)":weights})
        else:
            st.markdown("<div class='alert-info'>لم تسجل أي وزن بعد. سجل وزنك اليوم!</div>",unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # ── CLINICAL REFERENCE MODULE ──
    # ══════════════════════════════════════════
    elif st.session_state.page == "clinical":
        st.markdown("<div class='sec-title'>📚 المرجع الكلينيكي</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='alert-info'>📖 <b>مستخلص من:</b> Understanding Normal and Clinical Nutrition, 8th Ed — "
            "Rolfes, Pinna & Whitney | هذه المعلومات للمرجعية المهنية فقط</div>",
            unsafe_allow_html=True
        )

        # ── Condition selector ──
        CONDITIONS_LIST = {
            "🩸 السكري النوع الأول":               "diabetes_t1",
            "🩸 السكري النوع الثاني":              "diabetes_t2",
            "🤰 الحمل":                            "pregnancy",
            "🤱 الرضاعة الطبيعية":                "lactation",
            "🫘 الفشل الكلوي — قبل الديلزة":      "ckd_predialysis",
            "🫘 الفشل الكلوي — غسيل الكلى":       "ckd_hemodialysis",
            "❤️ أمراض القلب والأوعية / ضغط الدم": "cardiovascular",
            "🫀 تليف الكبد":                       "liver_cirrhosis",
            "⚖️ السمنة وزيادة الوزن":             "obesity",
            "🎗️ السرطان":                         "cancer",
            "🔴 HIV/AIDS":                         "hiv_aids",
            "🔥 حرقة المعدة / الارتجاع (GERD)":   "gerd",
            "🫃 القولون العصبي (IBS)":             "ibs",
            "🔬 المتلازمة الأيضية":               "metabolic_syndrome",
        }

        st.markdown("### 🗂️ اختر الحالة أو الأمراض المصاحبة")
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            selected_labels = st.multiselect(
                "يمكنك اختيار أكثر من حالة في نفس الوقت (حالات مركبة)",
                list(CONDITIONS_LIST.keys()),
                help="اختر حالة واحدة أو أكثر — عند اختيار حالتين ستظهر ملاحظات الدمج"
            )
        with col_s2:
            st.markdown("<br>", unsafe_allow_html=True)
            search_ref = st.text_input("🔎 بحث سريع في المرجع", placeholder="مثال: بروتين، حديد، كالسيوم")

        if not selected_labels and not search_ref:
            # Show overview cards
            st.markdown("### 📋 الحالات المتاحة في المرجع")
            cols = st.columns(3)
            for i, (lbl, key) in enumerate(CONDITIONS_LIST.items()):
                with cols[i % 3]:
                    cond = CLINICAL_CONDITIONS[key]
                    st.markdown(f"""
                    <div class="card" style="text-align:center;padding:16px 12px;margin-bottom:10px">
                        <div style="font-size:28px">{cond['icon']}</div>
                        <div style="color:#ffffff;font-size:13px;font-weight:700;margin:6px 0 2px">{cond['name']}</div>
                        <div style="color:#3a6a8a;font-size:11px">{cond['chapter'][:30]}...</div>
                    </div>""", unsafe_allow_html=True)
            st.markdown(
                "<div class='alert-info' style='margin-top:20px'>💡 اختر حالة من القائمة لعرض التوصيات الغذائية الكاملة من المرجع</div>",
                unsafe_allow_html=True
            )

        # ── Search mode ──
        if search_ref:
            sq = search_ref.lower()
            st.markdown(f"### 🔎 نتائج البحث عن: '{search_ref}'")
            found = False
            for key, cond in CLINICAL_CONDITIONS.items():
                hits = []
                for section_val in [str(cond.get('overview', '')), str(cond.get('key_points', '')),
                                    str(cond.get('macros', '')), str(cond.get('key_micronutrients', ''))]:
                    if sq in section_val.lower():
                        hits.append(section_val[:200])
                if hits:
                    found = True
                    st.markdown(f"""
                    <div class="sug-box">
                        <h4>{cond['icon']} {cond['name']}</h4>
                        <div style="color:#7fb8d8;font-size:12px;margin-bottom:8px">{cond['chapter']}</div>
                        <div class="fc-note">📋 {cond['overview'][:300]}...</div>
                    </div>""", unsafe_allow_html=True)
            if not found:
                st.markdown("<div class='alert-warn'>لم يُعثر على نتائج. جرب كلمة مختلفة.</div>", unsafe_allow_html=True)

        # ── Condition detail view ──
        if selected_labels:
            selected_keys = [CONDITIONS_LIST[l] for l in selected_labels]

            # Combination notes
            if len(selected_keys) >= 2:
                st.markdown("---")
                st.markdown("### ⚠️ ملاحظات الحالات المركبة")
                shown_combo = False
                for i in range(len(selected_keys)):
                    for j in range(i+1, len(selected_keys)):
                        pair = (selected_keys[i], selected_keys[j])
                        pair_rev = (selected_keys[j], selected_keys[i])
                        note = COMBINATION_NOTES.get(pair) or COMBINATION_NOTES.get(pair_rev)
                        if note:
                            shown_combo = True
                            st.markdown(f"<div class='alert-warn'>{note}</div>", unsafe_allow_html=True)
                if not shown_combo:
                    st.markdown(
                        "<div class='alert-info'>ℹ️ راجع التوصيات التفصيلية لكل حالة بالأسفل وادمجها بحكمة سريرية.</div>",
                        unsafe_allow_html=True
                    )

            # Individual condition details
            for key in selected_keys:
                cond = CLINICAL_CONDITIONS[key]
                st.markdown("---")
                st.markdown(f"## {cond['icon']} {cond['name']}")
                st.markdown(f"<div style='color:#3a6a8a;font-size:13px;margin-bottom:12px'>📖 {cond['chapter']}</div>", unsafe_allow_html=True)

                # Overview
                st.markdown(f"<div class='fc-note'>📋 <b>نظرة عامة:</b> {cond['overview']}</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                # Goals
                if cond.get('goals'):
                    st.markdown("#### 🎯 أهداف العلاج الغذائي")
                    for g in cond['goals']:
                        st.markdown(f"- {g}")

                # Macros table
                if cond.get('macros'):
                    st.markdown("#### ⚖️ التوصيات الغذائية الكمية")
                    macro_items = cond['macros']
                    mc1, mc2 = st.columns(2)
                    items_list = list(macro_items.items())
                    half = (len(items_list) + 1) // 2
                    with mc1:
                        for k, v in items_list[:half]:
                            label_map = {
                                'energy':'🔥 السعرات','carb':'🍞 الكارب','protein':'💪 البروتين',
                                'fat':'🥑 الدهون','fiber':'🌾 الألياف','sodium':'🧂 الصوديوم',
                                'potassium':'⚡ البوتاسيوم','phosphorus':'🔵 الفوسفور',
                                'calcium':'🦴 الكالسيوم','fluid':'💧 السوائل',
                                'omega3':'🐟 أوميغا 3','zinc':'🔩 الزنك'
                            }
                            lbl = label_map.get(k, k)
                            st.markdown(f"""
                            <div style="background:rgba(0,180,216,.07);border-right:3px solid rgba(0,180,216,.35);
                            border-radius:8px;padding:8px 12px;margin-bottom:8px">
                                <span style="color:#7fb8d8;font-size:12px;font-weight:700">{lbl}</span><br>
                                <span style="color:#dceeff;font-size:13px">{v}</span>
                            </div>""", unsafe_allow_html=True)
                    with mc2:
                        for k, v in items_list[half:]:
                            label_map = {
                                'energy':'🔥 السعرات','carb':'🍞 الكارب','protein':'💪 البروتين',
                                'fat':'🥑 الدهون','fiber':'🌾 الألياف','sodium':'🧂 الصوديوم',
                                'potassium':'⚡ البوتاسيوم','phosphorus':'🔵 الفوسفور',
                                'calcium':'🦴 الكالسيوم','fluid':'💧 السوائل',
                                'omega3':'🐟 أوميغا 3','zinc':'🔩 الزنك'
                            }
                            lbl = label_map.get(k, k)
                            st.markdown(f"""
                            <div style="background:rgba(0,180,216,.07);border-right:3px solid rgba(0,180,216,.35);
                            border-radius:8px;padding:8px 12px;margin-bottom:8px">
                                <span style="color:#7fb8d8;font-size:12px;font-weight:700">{lbl}</span><br>
                                <span style="color:#dceeff;font-size:13px">{v}</span>
                            </div>""", unsafe_allow_html=True)

                # Key micronutrients
                if cond.get('key_micronutrients'):
                    st.markdown("#### 💊 المغذيات الدقيقة الحرجة")
                    for km, kv in cond['key_micronutrients'].items():
                        st.markdown(f"""
                        <div style="background:rgba(255,200,0,.06);border-right:3px solid rgba(255,200,0,.3);
                        border-radius:8px;padding:7px 12px;margin-bottom:6px">
                            <span style="color:#ffe082;font-size:12px;font-weight:700">{km.replace('_',' ').title()}</span>:
                            <span style="color:#dceeff;font-size:13px"> {kv}</span>
                        </div>""", unsafe_allow_html=True)

                # Key points
                if cond.get('key_points'):
                    st.markdown("#### 🔑 نقاط رئيسية للممارسة السريرية")
                    for kp in cond['key_points']:
                        st.markdown(f"""
                        <div class="food-card" style="padding:10px 14px;margin-bottom:6px">
                            <span style="color:#dceeff;font-size:13.5px">{kp}</span>
                        </div>""", unsafe_allow_html=True)

                # Foods recommended / limit
                if cond.get('foods_recommended') or cond.get('foods_limit'):
                    fa, fb = st.columns(2)
                    with fa:
                        if cond.get('foods_recommended'):
                            st.markdown("#### ✅ أطعمة مُشجَّعة")
                            for f in cond['foods_recommended']:
                                st.markdown(f"<div style='color:#a5d6a7;font-size:13px;padding:3px 0'>✔ {f}</div>", unsafe_allow_html=True)
                    with fb:
                        if cond.get('foods_limit'):
                            st.markdown("#### ⛔ أطعمة تُقلَّل أو تُتجنَّب")
                            for f in cond['foods_limit']:
                                st.markdown(f"<div style='color:#ef9a9a;font-size:13px;padding:3px 0'>✖ {f}</div>", unsafe_allow_html=True)

                # DASH diet table (cardiovascular)
                if cond.get('dash_diet'):
                    st.markdown("#### 🥗 حمية DASH — التفاصيل")
                    dd = cond['dash_diet']
                    st.markdown(f"<div class='alert-info'>{dd['description']}: صوديوم {dd['sodium']}</div>", unsafe_allow_html=True)
                    d1, d2 = st.columns(2)
                    with d1:
                        for item in ['fruits','vegetables','grains','dairy_lowfat']:
                            label = {'fruits':'🍎 فاكهة','vegetables':'🥦 خضروات','grains':'🌾 حبوب','dairy_lowfat':'🥛 ألبان قليلة الدسم'}.get(item, item)
                            st.markdown(f"**{label}:** {dd[item]}")
                    with d2:
                        for item in ['lean_meat','nuts_seeds','fats_oils']:
                            label = {'lean_meat':'🍗 لحوم قليلة الدهن','nuts_seeds':'🥜 مكسرات وبذور','fats_oils':'🫙 دهون وزيوت'}.get(item, item)
                            st.markdown(f"**{label}:** {dd[item]}")

                # Weight gain guide (pregnancy)
                if cond.get('weight_gain_guide'):
                    st.markdown("#### ⚖️ الزيادة الوزنية المثالية حسب BMI قبل الحمل")
                    for bmi_range, rec in cond['weight_gain_guide'].items():
                        st.markdown(f"""
                        <div style="background:rgba(76,175,80,.07);border-right:3px solid rgba(76,175,80,.3);
                        border-radius:8px;padding:7px 12px;margin-bottom:6px">
                            <span style="color:#a5d6a7;font-size:13px;font-weight:700">{bmi_range}</span>:
                            <span style="color:#dceeff"> {rec}</span>
                        </div>""", unsafe_allow_html=True)

                # FODMAP lists (IBS)
                if cond.get('high_fodmap_foods'):
                    fi1, fi2 = st.columns(2)
                    with fi1:
                        st.markdown("#### 🔴 أطعمة High-FODMAP (تجنب)")
                        for f in cond['high_fodmap_foods']:
                            st.markdown(f"<div style='color:#ef9a9a;font-size:13px'>✖ {f}</div>", unsafe_allow_html=True)
                    with fi2:
                        st.markdown("#### 🟢 أطعمة Low-FODMAP (مسموح)")
                        for f in cond['low_fodmap_foods']:
                            st.markdown(f"<div style='color:#a5d6a7;font-size:13px'>✔ {f}</div>", unsafe_allow_html=True)

                # High phos/potassium (renal)
                if cond.get('high_phosphorus_foods'):
                    rp1, rp2 = st.columns(2)
                    with rp1:
                        st.markdown("#### 🔵 أطعمة عالية الفوسفور (تحكم)")
                        for f in cond['high_phosphorus_foods']:
                            st.markdown(f"<div style='color:#ffcc80;font-size:13px'>⚠ {f}</div>", unsafe_allow_html=True)
                    with rp2:
                        if cond.get('high_potassium_foods'):
                            st.markdown("#### ⚡ أطعمة عالية البوتاسيوم (تحكم)")
                            for f in cond['high_potassium_foods']:
                                st.markdown(f"<div style='color:#ffcc80;font-size:13px'>⚠ {f}</div>", unsafe_allow_html=True)

                # Meal timing
                if cond.get('meal_timing'):
                    st.markdown(f"<div class='alert-info'>⏰ <b>توقيت الوجبات:</b> {cond['meal_timing']}</div>", unsafe_allow_html=True)

                # Monitoring
                if cond.get('monitoring'):
                    st.markdown(f"<div class='alert-warn'>📊 <b>المتابعة:</b> {cond['monitoring']}</div>", unsafe_allow_html=True)

                # Reference
                st.markdown(f"""
                <div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);
                border-radius:10px;padding:10px 14px;margin-top:16px">
                    <span style="color:#3a6a8a;font-size:12px">📚 المصدر: {cond['reference']}</span>
                </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# CLINICAL DATA (inline — extracted from textbook)
# ══════════════════════════════════════════

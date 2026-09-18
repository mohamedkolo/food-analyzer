# -*- coding: utf-8 -*-
"""بروتوكول ما بعد التكميم: مراحل زمنية، مش قايمة ممنوعات.

الفرق بين ده والنظام الكيميائي:

الكيميائي دورة ستة أيام، كل يوم فيها مختلف عن اللي قبله، والترتيب نفسه جزء
من البروتوكول. هنا العكس: المرحلة الواحدة بتتكرر الأسبوع كله، واللي بيحدد
المرحلة هو عدد الأسابيع اللي فاتت على العملية. مريض في أسبوعه الأول مايقدرش
يبلع أكل مهروس، ومريض في شهره السادس لو اداه حد سوائل صافية بيجوّعه.

فالمدخل الأساسي هنا رقم واحد: **عدد الأسابيع بعد العملية**. ومن غيره مافيش
تخمين -- الملف بيرجع عرض للبروتوكول كله (كل مرحلة ومداها) وتحذير إن ده مش
خطة أسبوع، عشان محدش يبني أسبوع على مرحلة غلط.

حاجة تانية لازم تتقال صريح: **كل المراحل الأولى تحت أي حد سعرات آمن، وده
صح**. أسبوع السوائل الصافية حوالي 150 kcal. ده مش خطأ في الخطة، ده طبيعة
المرحلة -- المعدة لسه بتلتئم. فتحذير "تحت الحد" هنا بيتكتب بصيغة "متوقع في
المرحلة دي" مش بصيغة خطر، وإلا الأخصائي هيتعلّم يتجاهل التحذيرات.

والقواعد الدايمة (بروتين الأول، مفيش غازيات، السوائل بعيد عن الأكل، مفيش
شاليموه، الفيتامينات مدى الحياة) مش مرحلة -- دي بتمشي مع كل المراحل، فهي
في PERMANENT_RULES وبتطلع على كل أسبوع.
"""

from meal_database import safe_for_all, unsafe_keys_for
from zigzag import _floor_for

SLOTS = ["breakfast", "lunch", "dinner", "snack"]

# ‏القواعد اللي مالهاش مرحلة -- بتمشي من أول يوم ولمدى الحياة. مكتوبة مرة
# واحدة عشان ماتتكررش في كل مرحلة وتختلف بينهم بالغلط.
PERMANENT_RULES = [
    {"ar": "البروتين الأول في كل وجبة — الهدف 60-80 جم بروتين يومياً.",
     "en": "Protein first at every meal — target 60-80 g protein per day."},
    {"ar": "مفيش مشروبات غازية خالص، ولا دلوقتي ولا بعدين.",
     "en": "No fizzy drinks at all, now or later."},
    {"ar": "ماتشربش مع الأكل: وقّف السوائل 30 دقيقة قبل الوجبة و30 دقيقة بعدها.",
     "en": "Do not drink with meals: stop fluids 30 minutes before and after eating."},
    {"ar": "مفيش شاليموه — بيدخّل هوا على المعدة.",
     "en": "No straws — they swallow air into the stomach."},
    {"ar": "امضغ كتير وكُل بالراحة: الوجبة تاخد 20-30 دقيقة.",
     "en": "Chew thoroughly and eat slowly: 20-30 minutes per meal."},
    {"ar": "1.5-2 لتر سوائل يومياً، رشفات صغيرة على مدار اليوم.",
     "en": "1.5-2 L of fluid a day, sipped in small amounts throughout."},
    {"ar": "قلّل السكر والدهون — بيسببوا مغص وإسهال ودوخة (dumping).",
     "en": "Keep sugar and fat low — they cause cramping, diarrhoea and "
           "dizziness (dumping syndrome)."},
    {"ar": "الفيتامينات مدى الحياة: مالتي فيتامين + B12 + حديد + كالسيوم "
           "سيترات + فيتامين D، بجرعات من الطبيب.",
     "en": "Vitamins for life: multivitamin + B12 + iron + calcium citrate + "
           "vitamin D, at doses set by the doctor."},
]

# ‏المراحل بالترتيب. weeks = (من، لـ) والـNone معناها مفتوحة.
SLEEVE_PHASES = [
    {
        "key": "clear_liquids",
        "short": "سوائل صافية",
        "short_en": "clear liquids",
        "weeks": (1, 1),
        "name": "المرحلة الأولى — سوائل صافية (الأسبوع الأول)",
        "name_en": "Phase 1 - clear liquids (week 1)",
        "note": "سوائل صافية بس، رشفات صغيرة. مفيش سكر ومفيش حمضيات.",
        "note_en": "Clear liquids only, in small sips. No sugar and nothing acidic.",
        "forbidden": ["سكر", "مشروبات غازية", "قهوة", "برتقال", "ليمون مركز",
                      "حلويات", "لبن كامل"],
        "forbidden_en": ["sugar", "fizzy drinks", "coffee", "orange",
                         "concentrated lemon", "sweets", "whole milk"],
        "meals": {
            "breakfast": [
                {"meal": "💧 ماء رشفات + 🍵 شاي اعشاب خفيف بدون سكر", "cal": 5, "p": 0},
                {"meal": "🍵 شاي بابونج خفيف بدون سكر", "cal": 5, "p": 0},
            ],
            "lunch": [
                {"meal": "🥣 شوربة صافية مصفاة 150مل بدون دهون", "cal": 40, "p": 3},
                {"meal": "🥣 مرقة دجاج مصفاة 150مل", "cal": 35, "p": 3},
            ],
            "dinner": [
                {"meal": "🥣 شوربة خضار مصفاة 150مل", "cal": 35, "p": 2},
                {"meal": "🥣 مرقة صافية 150مل + 💧 ماء", "cal": 30, "p": 2},
            ],
            "snack": [
                {"meal": "🍮 جيلي بدون سكر 100جم", "cal": 10, "p": 1},
                {"meal": "💧 ماء رشفات على مدار اليوم", "cal": 0, "p": 0},
            ],
        },
    },
    {
        "key": "full_liquids",
        "short": "سوائل كاملة",
        "short_en": "full liquids",
        "weeks": (2, 2),
        "name": "المرحلة الثانية — سوائل كاملة (الأسبوع الثاني)",
        "name_en": "Phase 2 - full liquids (week 2)",
        "note": "سوائل كاملة وبروتين شيك. لسه مفيش أي حاجة تتمضغ.",
        "note_en": "Full liquids and protein shakes. Still nothing that needs chewing.",
        "forbidden": ["سكر", "مشروبات غازية", "قهوة", "حلويات", "مقلي",
                      "خبز", "ارز", "لحمة"],
        "forbidden_en": ["sugar", "fizzy drinks", "coffee", "sweets", "fried",
                         "bread", "rice", "meat"],
        "meals": {
            "breakfast": [
                {"meal": "🥛 بروتين شيك بالحليب خالي الدسم 200مل", "cal": 160, "p": 22},
                {"meal": "🥛 لبن رايب خفيف 200مل بدون سكر", "cal": 110, "p": 10},
                # ‏لمريض حساسية اللاكتوز: المرحلة دي كلها لبن، فمن غير البديل
                # ده فطاره وعشاه بيطلعوا فاضيين.
                {"meal": "🥛 بروتين شيك بالماء 200مل", "cal": 130, "p": 24},
                {"meal": "🥛 بروتين شيك بالصويا 200مل", "cal": 150, "p": 20},
            ],
            "lunch": [
                {"meal": "🥣 شوربة عدس مصفاة 200مل", "cal": 140, "p": 9},
                {"meal": "🥣 شوربة دجاج مصفاة 200مل + 🥛 حليب خالي الدسم", "cal": 150, "p": 14},
            ],
            "dinner": [
                {"meal": "🥛 زبادي سائل خالي الدسم 200جم بدون سكر", "cal": 120, "p": 14},
                {"meal": "🥣 شوربة خضار مصفاة 200مل + 🥛 حليب خالي الدسم", "cal": 130, "p": 10},
                {"meal": "🥣 شوربة عدس مصفاة 200مل + 🥛 بروتين شيك بالصويا", "cal": 200, "p": 22},
                {"meal": "🥣 شوربة عدس مصفاة 250مل + 💧 ماء", "cal": 175, "p": 12},
            ],
            "snack": [
                # ‏كل سناك هنا بيحمل بروتين. هدف المرحلة 60-80 جم بروتين،
                # وسناك جيلي وماء بيخلي اليوم يقع تحته.
                {"meal": "🥛 بروتين شيك 150مل", "cal": 120, "p": 18},
                {"meal": "🥛 بروتين شيك بالصويا 150مل", "cal": 115, "p": 17},
            ],
        },
    },
    {
        "key": "pureed",
        "short": "مهروس",
        "short_en": "pureed",
        "weeks": (3, 4),
        "name": "المرحلة الثالثة — أكل مهروس (الأسبوع 3-4)",
        "name_en": "Phase 3 - pureed food (weeks 3-4)",
        "note": "كل حاجة مهروسة ناعمة زي قوام الزبادي. مفيش قطع خالص.",
        "note_en": "Everything pureed smooth, like yoghurt. No pieces at all.",
        "forbidden": ["سكر", "مشروبات غازية", "قهوة", "حلويات", "مقلي",
                      "خبز", "مكسرات", "بالقشر"],
        "forbidden_en": ["sugar", "fizzy drinks", "coffee", "sweets", "fried",
                         "bread", "nuts", "with skins"],
        "meals": {
            "breakfast": [
                {"meal": "🥛 زبادي خالي الدسم 150جم + 🍌 موز مهروس نصف", "cal": 160, "p": 12},
                {"meal": "🧀 جبن قريش مهروس 100جم + 💧 ماء بعدها بساعة", "cal": 110, "p": 17},
                {"meal": "🥚 بيض مسلوق مهروس 2 + 💧 ماء بعدها بساعة", "cal": 150, "p": 13},
                {"meal": "🫘 فول مهروس ناعم 120جم بدون زيت", "cal": 150, "p": 10},
            ],
            "lunch": [
                {"meal": "🍗 دجاج مهروس 60جم + 🥕 جزر مهروس 80جم", "cal": 180, "p": 20},
                {"meal": "🫘 عدس مهروس ناعم 150جم", "cal": 170, "p": 11},
            ],
            "dinner": [
                {"meal": "🐟 سمك مهروس 60جم + 🥔 بطاطس مهروسة 80جم", "cal": 175, "p": 16},
                {"meal": "🫘 حمص مهروس ناعم 100جم", "cal": 160, "p": 8},
            ],
            "snack": [
                {"meal": "🥛 زبادي يوناني خالي الدسم 150جم بدون سكر", "cal": 110, "p": 17},
                {"meal": "🥛 بروتين شيك 150مل", "cal": 120, "p": 18},
                {"meal": "🥛 بروتين شيك بالصويا 150مل", "cal": 115, "p": 17},
            ],
        },
    },
    {
        "key": "soft",
        "short": "لين",
        "short_en": "soft",
        "weeks": (5, 6),
        "name": "المرحلة الرابعة — أكل لين (الأسبوع 5-6)",
        "name_en": "Phase 4 - soft food (weeks 5-6)",
        "note": "أكل لين يتفتت بالشوكة. امضغ كل لقمة لحد ما تبقى ناعمة.",
        "note_en": "Soft food that breaks with a fork. Chew every bite until smooth.",
        "forbidden": ["سكر", "مشروبات غازية", "قهوة", "حلويات", "مقلي",
                      "لحم احمر", "مكسرات", "بالقشر", "خبز"],
        "forbidden_en": ["sugar", "fizzy drinks", "coffee", "sweets", "fried",
                         "red meat", "nuts", "with skins", "bread"],
        "meals": {
            "breakfast": [
                {"meal": "🥚 بيض مخفوق 2 طري + 🍅 طماطم مقشرة", "cal": 190, "p": 14},
                {"meal": "🧀 جبن قريش 100جم + 🥑 افوكادو مهروس 30جم", "cal": 170, "p": 18},
            ],
            "lunch": [
                {"meal": "🍗 دجاج مفروم مطهي طري 80جم + 🥕 خضار مسلوقة طرية 100جم",
                 "cal": 230, "p": 25},
                {"meal": "🐟 سمك مسلوق طري 90جم + 🥔 بطاطس مهروسة 100جم", "cal": 240, "p": 22},
            ],
            "dinner": [
                {"meal": "🥛 زبادي خالي الدسم 150جم + 🍌 موز طري نصف", "cal": 160, "p": 12},
                {"meal": "🫘 عدس مطهي طري 150جم + 🥕 جزر مسلوق", "cal": 200, "p": 12},
            ],
            "snack": [
                {"meal": "🥛 بروتين شيك 150مل", "cal": 120, "p": 18},
                {"meal": "🧀 جبن قريش 80جم", "cal": 90, "p": 14},
            ],
        },
    },
    {
        "key": "regular",
        "short": "عادي بحجم صغير",
        "short_en": "regular, small portions",
        "weeks": (7, None),
        "name": "المرحلة الخامسة — أكل عادي بحجم صغير (من الأسبوع السابع)",
        "name_en": "Phase 5 - regular food, small portions (week 7 onward)",
        "note": "أكل عادي بحجم صغير. البروتين الأول، والحجم يزيد بالراحة.",
        "note_en": "Regular food in small portions. Protein first, and build the "
                   "volume up slowly.",
        "forbidden": ["سكر", "مشروبات غازية", "حلويات", "مقلي", "مقلية", "سمن"],
        "forbidden_en": ["sugar", "fizzy drinks", "sweets", "fried",
                         "deep-fried", "ghee"],
        "meals": {
            "breakfast": [
                {"meal": "🥚 بيض مسلوق 2 + 🧀 جبن قريش 50جم + 🥒 خيار", "cal": 250, "p": 24},
                {"meal": "🥛 زبادي يوناني 150جم + 🍓 توت 50جم", "cal": 190, "p": 16},
                # ‏الاتنين اللي فوق ألبان، ومريض حساسية اللاكتوز فطاره كان
                # بيطلع فاضي في المرحلة دي.
                {"meal": "🥚 بيض مسلوق 2 + 🍞 توست اسمر 1 + 🥒 خيار", "cal": 240, "p": 16},
                {"meal": "🫘 فول مدمس 100جم بدون زيت + 🍞 توست اسمر 1", "cal": 230, "p": 12},
            ],
            "lunch": [
                {"meal": "🍗 صدر دجاج مشوي 100جم + 🥗 سلطة + 🍚 ارز 50جم", "cal": 330, "p": 32},
                {"meal": "🐟 سمك مشوي 100جم + 🥦 خضار مطهية 100جم", "cal": 260, "p": 28},
            ],
            "dinner": [
                {"meal": "🧀 جبن قريش 100جم + 🥗 سلطة صغيرة", "cal": 160, "p": 18},
                {"meal": "🫘 عدس 120جم + 🥗 سلطة صغيرة", "cal": 200, "p": 13},
            ],
            "snack": [
                # ‏تكبير الوجبات مش حل: معدة المريض بتشيل 150 مل. اللي بيوصل
                # بالبروتين لهدف 60-80 جم هو إن السناك نفسه يحمل بروتين --
                # وده الممارسة الفعلية، البروتين شيك بيستمر شهور بعد العملية.
                {"meal": "🥛 زبادي يوناني 150جم", "cal": 110, "p": 17},
                {"meal": "🥛 بروتين شيك 150مل", "cal": 120, "p": 18},
                {"meal": "🥚 بيضة مسلوقة + 🥜 لوز 10جم", "cal": 135, "p": 9},
            ],
        },
    },
]

# ‏تنبيهات بتخص الحالة المرضية مش المرحلة. مفتاحها مفتاح المنع الداخلي زي
# ما unsafe_keys_for بيرجّعه، عشان تتطابق مع اللي المريض مختاره فعلاً.
PHASE_CAUTIONS = {
    "سكري": {"ar": "مريض سكري بعد التكميم: خطر نزول السكر عالي في المراحل "
                   "الأولى لأن الأكل قليل جداً — جرعات الأنسولين أو الحبوب "
                   "محتاجة مراجعة الطبيب فوراً، مش بعدين.",
             "en": "Diabetes after sleeve surgery: the risk of hypoglycaemia is "
                   "high in the early phases because intake is very low — "
                   "insulin or tablet doses need a doctor's review now, not later."},
    "حمل": {"ar": "الحمل بعد التكميم: الحمل في أول سنة بعد العملية مش موصى بيه، "
                  "والحالة دي محتاجة طبيب نسا وأخصائي تغذية مع بعض.",
            "en": "Pregnancy after sleeve surgery: pregnancy within the first "
                  "year is not advised, and this case needs an obstetrician and "
                  "a dietitian together."},
    "نقص الحديد": {"ar": "نقص الحديد بعد التكميم: الامتصاص بيقل بعد العملية، "
                         "فالمكمل لازم يبقى منتظم ومحتاج تحليل متابعة.",
                   "en": "Iron deficiency after sleeve surgery: absorption drops "
                         "after the operation, so the supplement must be regular "
                         "and needs follow-up bloodwork."},
}

# ‏قايمة مسطحة لفحص التغطية في meal_i18n -- نفس سبب CHEMICAL_MEALS: الفحص
# بيمشي على القواميس اللي فيها مفتاح "meal"، ولو مشى على SLEEVE_PHASES كان
# هياخد أسماء المراحل والملاحظات على إنها وجبات.
SLEEVE_MEALS = []
for _phase in SLEEVE_PHASES:
    for _slot in SLOTS:
        SLEEVE_MEALS.extend(_phase["meals"][_slot])

SLEEVE_SYSTEM = {
    "name": "نظام ما بعد التكميم (بالمراحل)",
    "name_en": "Post-sleeve protocol (phased)",
    "meals": ["breakfast", "lunch", "dinner", "snack"],
    "meal_labels": {"breakfast": "الفطار", "lunch": "الغداء",
                    "dinner": "العشاء", "snack": "سناك"},
    "meal_labels_en": {"breakfast": "Breakfast", "lunch": "Lunch",
                       "dinner": "Dinner", "snack": "Snack"},
    "meal_emojis": {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙", "snack": "🍎"},
    "meal_hours": {"breakfast": 8, "lunch": 14, "dinner": 20, "snack": 17},
    "description": "خمس مراحل بعدد الأسابيع: سوائل صافية، سوائل كاملة، مهروس، لين، عادي",
    "description_en": ("Five phases by week: clear liquids, full liquids, "
                       "pureed, soft, then regular"),
}

DAY_NAMES = [
    ("اليوم الأول", "Day 1"), ("اليوم الثاني", "Day 2"), ("اليوم الثالث", "Day 3"),
    ("اليوم الرابع", "Day 4"), ("اليوم الخامس", "Day 5"), ("اليوم السادس", "Day 6"),
    ("اليوم السابع", "Day 7"),
]


def phase_for_week(weeks):
    """المرحلة اللي المريض فيها. None لو الرقم مش منطقي."""
    try:
        w = int(float(weeks))
    except (TypeError, ValueError):
        return None
    if w < 1:
        return None
    for phase in SLEEVE_PHASES:
        lo, hi = phase["weeks"]
        if w >= lo and (hi is None or w <= hi):
            return phase
    return SLEEVE_PHASES[-1]


def _is_allowed(item, cond_keys, exclusions):
    """آمن للحالة المرضية ومش فيه حاجة المريض مستبعدها."""
    if cond_keys and not safe_for_all(item, cond_keys):
        return False
    text = item.get("meal", "") if isinstance(item, dict) else str(item)
    return not any(ex in text for ex in exclusions)


def _phase_entry(phase, cond_keys):
    """الخانات المشتركة بين عرض البروتوكول وخطة الأسبوع."""
    lo, hi = phase["weeks"]
    span = ("من الأسبوع %d" % lo) if hi is None else (
        "الأسبوع %d" % lo if lo == hi else "الأسبوع %d-%d" % (lo, hi))
    span_en = ("week %d onward" % lo) if hi is None else (
        "week %d" % lo if lo == hi else "weeks %d-%d" % (lo, hi))
    return {
        "phase_key": phase["key"],
        "phase_span": span,
        "phase_span_en": span_en,
        "note": phase["note"],
        "note_en": phase["note_en"],
        "forbidden": list(phase["forbidden"]),
        "forbidden_en": list(phase["forbidden_en"]),
        "diet_type": "sleeve",
        "meal_labels": SLEEVE_SYSTEM["meal_labels"],
        "meal_emojis": SLEEVE_SYSTEM["meal_emojis"],
    }


def build_sleeve_plan(weeks=None, symptoms=None, exclusions=None, gender=None):
    """خطة أسبوع في المرحلة اللي المريض فيها.

    بترجع (days, warnings) وكل تحذير له kind:
        needs_weeks   عدد الأسابيع ناقص، فاللي رجع عرض للبروتوكول مش خطة
        unfillable    خانة مقدرناش نأمّنها للحالة دي
        caution       المرحلة اتبنت بس الحالة دي محتاجة مراجعة
        below_floor   مجموع اليوم تحت الحد الآمن -- **متوقع** في المراحل الأولى
        transition    الأسبوع ده آخر أسبوع في المرحلة، الجاية بتبدأ بعده

    من غير عدد الأسابيع مفيش تخمين: مريض أسبوع أول مايقدرش يبلع مهروس،
    ومريض شهر سادس لو اداه حد سوائل صافية بيجوّعه. فالرقم ناقص = عرض
    البروتوكول كله وتحذير واضح.
    """
    exclusions = list(exclusions or [])
    cond_keys = unsafe_keys_for(symptoms or [])
    floor = _floor_for(gender)
    warnings = []

    phase = phase_for_week(weeks)

    # ── الرقم ناقص: نعرض البروتوكول كله ولا نخمّن مرحلة ──────────────────────
    if phase is None:
        warnings.append({
            "kind": "needs_weeks",
            "day": None, "day_en": None, "slot": None,
            "reason": "اكتب عدد الأسابيع اللي فاتت على العملية عشان تطلع خطة "
                      "أسبوع فعلي. اللي ظاهر تحت هو البروتوكول كله بمراحله — "
                      "مش خطة أسبوع.",
            "reason_en": ("Enter how many weeks have passed since surgery to get "
                          "an actual week's plan. What is shown below is the full "
                          "protocol and its phases — not a week's plan."),
        })
        days = []
        for idx, ph in enumerate(SLEEVE_PHASES):
            entry = _phase_entry(ph, cond_keys)
            entry["day"] = "%s — %s" % (ph["name"], entry["phase_span"])
            entry["day_en"] = "%s - %s" % (ph["name_en"], entry["phase_span_en"])
            total_cal = total_p = 0
            for slot in SLOTS:
                options = [o for o in ph["meals"][slot]
                           if _is_allowed(o, cond_keys, exclusions)]
                if not options:
                    continue
                entry[slot] = options[0]["meal"]
                total_cal += options[0].get("cal", 0)
                total_p += options[0].get("p", 0)
            entry["total_cal"] = total_cal
            entry["total_p"] = total_p
            entry["cautions"] = []
            entry["permanent_rules"] = [r["ar"] for r in PERMANENT_RULES]
            days.append(entry)
        return days, warnings

    # ── المرحلة معروفة: أسبوع كامل جواها ────────────────────────────────────
    week = int(float(weeks))
    lo, hi = phase["weeks"]
    if hi is not None and week == hi:
        nxt = SLEEVE_PHASES[SLEEVE_PHASES.index(phase) + 1]
        warnings.append({
            "kind": "transition",
            "day": None, "day_en": None, "slot": None,
            "reason": "ده آخر أسبوع في %s. الأسبوع الجاي يبدأ %s."
                      % (phase["name"], nxt["name"]),
            "reason_en": ("This is the last week of %s. Next week starts %s."
                          % (phase["name_en"], nxt["name_en"])),
        })

    # ‏تنبيهات الحالة المرضية: مرة واحدة على الأسبوع، مش سبع مرات.
    week_cautions = []
    for key, text in PHASE_CAUTIONS.items():
        if key in cond_keys:
            week_cautions.append(text)
            warnings.append({
                "kind": "caution",
                "day": None, "day_en": None, "slot": None,
                "reason": text["ar"], "reason_en": text["en"],
            })

    days = []
    for idx, (day_ar, day_en) in enumerate(DAY_NAMES):
        entry = _phase_entry(phase, cond_keys)
        entry["day"] = "%s — %s (الأسبوع %d)" % (day_ar, phase["short"], week)
        entry["day_en"] = "%s - %s (week %d)" % (day_en, phase["short_en"], week)
        total_cal = total_p = 0
        for slot in SLOTS:
            options = [o for o in phase["meals"][slot]
                       if _is_allowed(o, cond_keys, exclusions)]
            if not options:
                label = SLEEVE_SYSTEM["meal_labels"][slot]
                label_en = SLEEVE_SYSTEM["meal_labels_en"][slot].lower()
                # ‏مرة واحدة للأسبوع كله: نفس المرحلة على السبع أيام، فنفس
                # الخانة هتفضى سبع مرات وتغرق الملاحظات.
                if idx == 0:
                    warnings.append({
                        "kind": "unfillable",
                        "day": phase["name"], "day_en": phase["name_en"],
                        "slot": slot,
                        "reason": "مفيش اختيار آمن لـ%s في %s مع حالة المريض."
                                  % (label, phase["name"]),
                        "reason_en": ("No safe option for %s in %s given this "
                                      "client's conditions."
                                      % (label_en, phase["name_en"])),
                    })
                continue
            # ‏بنلف على الاختيارات عشان الأسبوع مايبقاش سبع أيام متطابقة
            chosen = options[idx % len(options)]
            entry[slot] = chosen["meal"]
            total_cal += chosen.get("cal", 0)
            total_p += chosen.get("p", 0)

        day_cautions = list(week_cautions)

        # ‏المراحل الأولى تحت أي حد سعرات، وده صح مش غلط. لو التحذير اتكتب
        # بصيغة خطر، الأخصائي هيتعلّم يتجاهله -- فالصيغة هنا "متوقع".
        if total_cal < floor:
            # ‏المرحلة لوحدها مش كافية للحكم: مريض أسبوع 7 بياكل 800 kcal
            # وده طبيعي تماماً، وإنه يفضل كده بعد 6 شهور هو اللي مش طبيعي.
            # فالفرق زمني -- 26 أسبوع.
            is_early = (phase["key"] != "regular") or week < 26
            if is_early:
                txt = {
                    "ar": "مجموع اليوم %d kcal — تحت الحد الآمن (%d kcal)، وده "
                          "**متوقع** في %s: المعدة لسه بتلتئم والهدف مش السعرات. "
                          "المهم البروتين والسوائل والفيتامينات."
                          % (total_cal, floor, phase["name"]),
                    "en": "This day totals %d kcal, under the %d kcal floor — "
                          "which is EXPECTED in %s: the stomach is still healing "
                          "and calories are not the target here. What matters is "
                          "protein, fluids and vitamins."
                          % (total_cal, floor, phase["name_en"]),
                }
            else:
                txt = {
                    "ar": "مجموع اليوم %d kcal — تحت الحد الآمن (%d kcal). في "
                          "المرحلة دي المفروض الحجم يكون زاد، فراجع الكميات."
                          % (total_cal, floor),
                    "en": "This day totals %d kcal, under the %d kcal floor. By "
                          "this phase the volume should have increased, so review "
                          "the portions." % (total_cal, floor),
                }
            day_cautions.append(txt)
            if idx == 0:
                warnings.append({
                    "kind": "below_floor",
                    "day": phase["name"], "day_en": phase["name_en"], "slot": None,
                    "kcal": total_cal, "floor": floor, "expected": is_early,
                    "reason": txt["ar"], "reason_en": txt["en"],
                })

        entry["cautions"] = day_cautions
        entry["permanent_rules"] = [r["ar"] for r in PERMANENT_RULES]
        entry["permanent_rules_en"] = [r["en"] for r in PERMANENT_RULES]
        entry["total_cal"] = total_cal
        entry["total_p"] = total_p
        days.append(entry)

    return days, warnings

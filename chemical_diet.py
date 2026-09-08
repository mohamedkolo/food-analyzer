# -*- coding: utf-8 -*-
"""النظام الكيميائي — the six-day chemical diet, as a fixed day-by-day cycle.

Every other system in DIET_PLAN_TYPES is a *shape*: a set of meal slots and a
calorie target, and the engine fills the slots from the goal pool so no two
days look alike. This one is the opposite. The days are the content: day one is
vegetables, day two is fruit, and so on to day six. Ordering is the whole point
of the protocol, so the cycle is six days rather than the usual seven and the
days are not shuffled.

That difference matters for safety. In a normal plan a meal the client cannot
eat is simply not drawn -- there are hundreds of others. Here the category is
fixed, so filtering can only choose *within* the day. Each slot therefore holds
several options from the same category, and the builder keeps whichever survive
filtering.

When nothing in a slot survives, this module does NOT fall back to the
unfiltered list the way the keto branch does. On a fruit-only day that fallback
would hand a kidney patient the exact oranges and kiwi that UNSAFE_FOODS exists
to keep away from them. The day is flagged in `warnings` instead, and the
caller shows it to the dietitian rather than quietly serving it.

Known collisions with UNSAFE_FOODS, all handled by that filtering:
    كلوي   سبانخ (day 1), برتقال and كيوي (days 2 and 6)

Diabetes is a different shape of problem and gets a different answer. Whole
fruit is not on the سكري list and must not be added to it -- that list is
global, so banning fruit there would strip it from every plan on the site. But
the fruit days are open-ended by the protocol's own wording ("بأي كمية"), which
is worth a second look for a diabetic. So those days carry a `cautions` entry:
the day is still built, and the dietitian is told to review it.

Filtering deliberately does NOT go through filter_by_conditions or
filter_meals_by_exclusions. Both are built for a pool of hundreds: the first
*substitutes* an unsafe meal from SAFE_ALTERNATIVES, which on a fruit day
returned "eggs and white bread" -- safe, but no longer the protocol; the second
returns the unfiltered list when every option is excluded. Here the day's
category is the point, so this module drops unsafe options with safe_for_all
and reports an empty slot instead of substituting or falling back.

Public API:
    CHEMICAL_DAYS          the six days, each with its pools and rules
    CHEMICAL_SYSTEM        the DIET_PLAN_TYPES entry
    build_chemical_plan()  -> (days, warnings)
"""

from meal_database import safe_for_all, unsafe_keys_for
# الحد الأدنى الآمن للسعرات متعرّف في zigzag ومستخدم في حساب التدوير. بيتستورد
# من هناك مش متكتوب هنا تاني -- رقم أمان بيتكرر في مكانين هو رقم بيختلف بينهم.
from zigzag import _floor_for

CYCLE_LENGTH = 6

# ترتيب الأيام جزء من البروتوكول نفسه — الأيام دي مش بتتخلط.
#
# كل خانة فيها أكتر من اختيار من نفس تصنيف اليوم، عشان الفلترة الطبية تلاقي
# بديل آمن من غير ما تخرج عن قواعد اليوم. النص عربي بالكامل لأن
# filter_by_conditions بيدوّر على كلمات UNSAFE_FOODS جوّه النص ده.
CHEMICAL_DAYS = [
    {
        "key": "vegetables",
        "name": "اليوم الأول — يوم الخضار الكامل",
        "name_en": "Day 1 - full vegetable day",
        "note": "خضار بأي طريقة: نيئة أو مسلوقة أو مشوية بدون زيوت.",
        "note_en": "Vegetables any way: raw, boiled or grilled with no oil.",
        "forbidden": ["بطاطس", "بطاطا", "ذرة"],
        "forbidden_en": ["potato", "sweet potato", "corn"],
        "meals": {
            "breakfast": [
                {"meal": "🥒 خيار 150جم + 🍅 طماطم 100جم + 🥬 خس 100جم", "cal": 70, "p": 4},
                {"meal": "🥗 سلطة خضراء 250جم بدون زيت + 🍋 ليمون", "cal": 80, "p": 4},
                {"meal": "🥦 بروكلي مسلوق 200جم + 🥕 جزر 100جم", "cal": 110, "p": 7},
            ],
            "lunch": [
                {"meal": "🥒 كوسة مشوية 250جم + 🥗 سلطة خضراء 200جم", "cal": 150, "p": 8},
                {"meal": "🥦 بروكلي 150جم + 🥬 قرنبيط 150جم بالبخار + 🍋 ليمون", "cal": 140, "p": 10},
                {"meal": "🍆 باذنجان مشوي 250جم + 🍅 طماطم 100جم", "cal": 130, "p": 6},
            ],
            "dinner": [
                {"meal": "🥬 سبانخ مطهية 200جم + 🥒 خيار 100جم", "cal": 100, "p": 7},
                {"meal": "🥗 سلطة خضراء كبيرة 300جم بدون زيت", "cal": 110, "p": 5},
                {"meal": "🥒 كوسة مسلوقة 250جم + 🥕 جزر 100جم", "cal": 120, "p": 6},
            ],
            "snack": [
                {"meal": "🥒 خيار 150جم", "cal": 25, "p": 1},
                {"meal": "🥕 جزر 100جم", "cal": 40, "p": 1},
                {"meal": "🍅 طماطم 150جم", "cal": 27, "p": 1},
            ],
        },
    },
    {
        "key": "fruit",
        "name": "اليوم الثاني — يوم الفاكهة الكامل",
        "name_en": "Day 2 - full fruit day",
        "note": "فاكهة طازجة بأي كمية عند الجوع.",
        "note_en": "Fresh fruit in any amount whenever hungry.",
        "forbidden": ["موز", "مانجو", "تمر", "عنب"],
        "forbidden_en": ["banana", "mango", "dates", "grapes"],
        # اليوم ده كميته مفتوحة بنص البروتوكول نفسه ("بأي كمية")، وده اللي
        # بيخلّيه محتاج وقفة مع السكري. الفاكهة الكاملة مش على قايمة
        # UNSAFE_FOODS بتاعة السكري -- وما ينفعش تتحط، لأن ده هيمنعها من كل
        # خطة في الموقع. فبدل ما نمنع، بنقول للأخصائي يراجع.
        "cautions": {
            "سكري": {
                "ar": "يوم فاكهة مفتوح الكمية مع حالة سكري — راجع الكمية "
                      "وتوزيعها على اليوم ومتابعة سكر الدم قبل ما تبعت الخطة.",
                "en": "An open-ended fruit day with diabetes — review the amount, "
                      "how it is spread across the day, and blood-sugar monitoring "
                      "before sending the plan.",
            },
        },
        "meals": {
            "breakfast": [
                {"meal": "🍎 تفاح 2 ثمرة", "cal": 190, "p": 1},
                {"meal": "🍓 فراولة 300جم", "cal": 96, "p": 2},
                {"meal": "🍉 بطيخ 400جم", "cal": 120, "p": 2},
            ],
            "lunch": [
                {"meal": "🍊 برتقال 3 ثمرات", "cal": 190, "p": 4},
                {"meal": "🍎 تفاح 2 ثمرة + 🍓 فراولة 200جم", "cal": 250, "p": 3},
                {"meal": "🍉 بطيخ 500جم", "cal": 150, "p": 3},
            ],
            "dinner": [
                {"meal": "🥝 كيوي 3 ثمرات", "cal": 130, "p": 2},
                {"meal": "🍓 فراولة 300جم + 🍎 تفاح 1", "cal": 190, "p": 2},
                {"meal": "🍎 تفاح 2 ثمرة", "cal": 190, "p": 1},
            ],
            "snack": [
                {"meal": "🍎 تفاح 1", "cal": 95, "p": 0},
                {"meal": "🍓 فراولة 150جم", "cal": 48, "p": 1},
                {"meal": "🍉 بطيخ 250جم", "cal": 75, "p": 1},
            ],
        },
    },
    {
        "key": "fish",
        "name": "اليوم الثالث — البروتين البحري والخضار",
        "name_en": "Day 3 - seafood protein and vegetables",
        "note": "سمك مشوي أو تونة مصفاة من الزيت مع خضار بدون دهون.",
        "note_en": "Grilled fish or drained tuna with fat-free vegetables.",
        # "زيت" لوحدها كانت بتطابق "بدون زيت" وهي مسموحة -- الحظر على
        # الزيت المضاف مش على ذكر الكلمة.
        "forbidden": ["مقلي", "زيت مضاف"],
        "forbidden_en": ["fried", "added oil"],
        "meals": {
            "breakfast": [
                {"meal": "🐟 تونة مصفاة 100جم + 🥒 خيار 100جم", "cal": 160, "p": 26},
                {"meal": "🐟 سمك مشوي 120جم + 🍅 طماطم 100جم", "cal": 180, "p": 25},
                {"meal": "🐟 تونة مصفاة 100جم + 🥬 خس 100جم", "cal": 150, "p": 26},
            ],
            "lunch": [
                {"meal": "🐟 سمك مشوي 180جم + 🥗 سلطة خضراء 250جم", "cal": 330, "p": 38},
                {"meal": "🐟 سمك مشوي 180جم + 🥦 بروكلي بالبخار 200جم", "cal": 320, "p": 40},
                {"meal": "🐟 تونة مصفاة 150جم + 🥗 سلطة خضراء 250جم", "cal": 280, "p": 36},
            ],
            "dinner": [
                {"meal": "🐟 سمك مشوي 150جم + 🥒 كوسة سوتيه بدون زيت 200جم", "cal": 270, "p": 33},
                {"meal": "🐟 تونة مصفاة 100جم + 🥗 سلطة خضراء 200جم", "cal": 210, "p": 27},
                {"meal": "🐟 سمك مشوي 150جم + 🥗 سلطة خضراء 200جم", "cal": 260, "p": 32},
            ],
            "snack": [
                {"meal": "🥒 خيار 150جم", "cal": 25, "p": 1},
                {"meal": "🍅 طماطم 150جم", "cal": 27, "p": 1},
                {"meal": "🥕 جزر 100جم", "cal": 40, "p": 1},
            ],
        },
    },
    {
        "key": "chicken",
        "name": "اليوم الرابع — الدجاج والخضار",
        "name_en": "Day 4 - chicken and vegetables",
        "note": "صدور دجاج بدون جلد، مشوية أو مسلوقة، مع خضار بالبخار أو سلطة.",
        "note_en": "Skinless chicken breast, grilled or boiled, with steamed vegetables or salad.",
        "forbidden": ["مقلي", "بالجلد"],
        "forbidden_en": ["fried", "with the skin"],
        "meals": {
            "breakfast": [
                {"meal": "🍗 صدر دجاج مسلوق 100جم + 🥒 خيار 100جم", "cal": 190, "p": 31},
                {"meal": "🍗 صدر دجاج مشوي 100جم + 🍅 طماطم 100جم", "cal": 190, "p": 31},
                {"meal": "🍗 صدر دجاج مسلوق 100جم + 🥬 خس 100جم", "cal": 180, "p": 31},
            ],
            "lunch": [
                {"meal": "🍗 صدر دجاج مشوي 180جم + 🥒 كوسة بالبخار 200جم", "cal": 360, "p": 56},
                {"meal": "🍗 صدر دجاج مشوي 180جم + 🥗 سلطة جرجير بالخيار 200جم", "cal": 340, "p": 55},
                {"meal": "🍗 صدر دجاج مسلوق 180جم + 🫘 فاصوليا خضراء 200جم", "cal": 370, "p": 57},
            ],
            "dinner": [
                {"meal": "🍗 صدر دجاج مشوي 150جم + 🥗 سلطة خضراء 200جم", "cal": 290, "p": 47},
                {"meal": "🍗 صدر دجاج مسلوق 150جم + 🥦 بروكلي بالبخار 200جم", "cal": 300, "p": 49},
                {"meal": "🍗 صدر دجاج مشوي 150جم + 🥒 خيار 150جم", "cal": 280, "p": 47},
            ],
            "snack": [
                {"meal": "🥒 خيار 150جم", "cal": 25, "p": 1},
                {"meal": "🥗 سلطة جرجير 100جم", "cal": 25, "p": 3},
                {"meal": "🥕 جزر 100جم", "cal": 40, "p": 1},
            ],
        },
    },
    {
        "key": "green",
        "name": "اليوم الخامس — السموذي الأخضر والسوائل",
        "name_en": "Day 5 - green smoothies and liquids",
        "note": "مشروبات وعصائر خضراء طبيعية طوال اليوم.",
        "note_en": "Natural green drinks and juices through the day.",
        "forbidden": ["سكر", "عسل"],
        "forbidden_en": ["sugar", "honey"],
        "meals": {
            "breakfast": [
                {"meal": "🥤 سموذي كرفس بالخيار 300مل + 🍋 ليمون", "cal": 70, "p": 2},
                {"meal": "🥤 عصير اخضر بقدونس بالخيار 300مل", "cal": 65, "p": 2},
                {"meal": "🥤 سموذي سبانخ بالخيار 300مل + 🍋 ليمون", "cal": 80, "p": 3},
            ],
            "lunch": [
                {"meal": "🥤 سموذي كرفس بالبقدونس 400مل + 🫚 زنجبيل", "cal": 95, "p": 3},
                {"meal": "🥤 عصير اخضر خيار بالكرفس 400مل + 🍋 ليمون", "cal": 85, "p": 3},
                {"meal": "🥤 سموذي خيار بالنعناع 400مل", "cal": 80, "p": 2},
            ],
            "dinner": [
                {"meal": "🥤 سموذي كرفس بالخيار 300مل + 🫚 زنجبيل", "cal": 75, "p": 2},
                {"meal": "🥤 عصير اخضر بقدونس بالنعناع 300مل + 🍋 ليمون", "cal": 70, "p": 2},
                {"meal": "🥤 سموذي خيار بالكرفس 300مل", "cal": 70, "p": 2},
            ],
            "snack": [
                {"meal": "🥤 ماء بالنعناع 300مل + 🍋 ليمون", "cal": 10, "p": 0},
                {"meal": "🥤 عصير اخضر خيار 250مل", "cal": 50, "p": 1},
                {"meal": "🫚 مشروب زنجبيل بالليمون 250مل", "cal": 15, "p": 0},
            ],
        },
    },
    {
        "key": "single_fruit",
        "name": "اليوم السادس — صنف فاكهة واحد",
        "name_en": "Day 6 - a single fruit",
        "note": "نوع واحد فقط من الفاكهة طوال اليوم عند الجوع.",
        "note_en": "One kind of fruit only, through the day, whenever hungry.",
        "forbidden": ["موز", "مانجو", "تمر", "عنب"],
        "forbidden_en": ["banana", "mango", "dates", "grapes"],
        # اليوم ده كميته مفتوحة بنص البروتوكول نفسه ("بأي كمية")، وده اللي
        # بيخلّيه محتاج وقفة مع السكري. الفاكهة الكاملة مش على قايمة
        # UNSAFE_FOODS بتاعة السكري -- وما ينفعش تتحط، لأن ده هيمنعها من كل
        # خطة في الموقع. فبدل ما نمنع، بنقول للأخصائي يراجع.
        "cautions": {
            "سكري": {
                "ar": "يوم فاكهة مفتوح الكمية مع حالة سكري — راجع الكمية "
                      "وتوزيعها على اليوم ومتابعة سكر الدم قبل ما تبعت الخطة.",
                "en": "An open-ended fruit day with diabetes — review the amount, "
                      "how it is spread across the day, and blood-sugar monitoring "
                      "before sending the plan.",
            },
        },
        # اليوم ده صنف واحد بس، فالخانات كلها بتتملي من نفس الفاكهة.
        "single_fruit": True,
        "fruits": [
            {"name": "🍎 تفاح", "portions": {"breakfast": "2 ثمرة", "lunch": "2 ثمرة",
                                            "dinner": "2 ثمرة", "snack": "1"},
             "cal": 95, "p": 0},
            {"name": "🍊 برتقال", "portions": {"breakfast": "2 ثمرة", "lunch": "3 ثمرات",
                                              "dinner": "2 ثمرة", "snack": "1"},
             "cal": 62, "p": 1},
            {"name": "🍓 فراولة", "portions": {"breakfast": "250جم", "lunch": "300جم",
                                              "dinner": "250جم", "snack": "150جم"},
             "cal": 32, "p": 1},
            {"name": "🍉 بطيخ", "portions": {"breakfast": "400جم", "lunch": "500جم",
                                            "dinner": "400جم", "snack": "250جم"},
             "cal": 30, "p": 1},
        ],
    },
]

SLOTS = ["breakfast", "lunch", "dinner", "snack"]

# كل نصوص الوجبات في قايمة مسطحة، عشان فحص التغطية في meal_i18n يعدي عليها
# ويقع لو اتضافت وجبة بكلمة مش في القاموس. لازم تفضل مسطحة: الفحص بيمشي على
# القواميس اللي فيها مفتاح "meal"، ولو مشى على CHEMICAL_DAYS نفسها كان هياخد
# أسماء الأيام والملاحظات على إنها وجبات وهي مش كده.
CHEMICAL_MEALS = []
for _day in CHEMICAL_DAYS:
    if _day.get("single_fruit"):
        for _fruit in _day["fruits"]:
            for _portion in _fruit["portions"].values():
                CHEMICAL_MEALS.append({"meal": f"{_fruit['name']} {_portion}",
                                       "cal": _fruit["cal"], "p": _fruit["p"]})
    else:
        for _slot in SLOTS:
            CHEMICAL_MEALS.extend(_day["meals"][_slot])

# مدخل النظام في DIET_PLAN_TYPES. نفس خانات النظام التقليدي عشان القالب
# يعرف يعرضها من غير خانات جديدة.
CHEMICAL_SYSTEM = {
    "name": "النظام الكيميائي (6 أيام)",
    "name_en": "Chemical diet (6 days)",
    "meals": ["breakfast", "lunch", "dinner", "snack"],
    "meal_labels": {"breakfast": "الفطار", "lunch": "الغداء",
                    "dinner": "العشاء", "snack": "سناك"},
    "meal_labels_en": {"breakfast": "Breakfast", "lunch": "Lunch",
                       "dinner": "Dinner", "snack": "Snack"},
    "meal_emojis": {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙", "snack": "🍎"},
    "meal_hours": {"breakfast": 8, "lunch": 14, "dinner": 20, "snack": 17},
    "description": "دورة 6 أيام ثابتة: خضار، فاكهة، سمك، دجاج، سوائل خضراء، صنف فاكهة واحد",
    "description_en": ("A fixed 6-day cycle: vegetables, fruit, fish, chicken, "
                       "green liquids, then a single fruit"),
}


def _is_allowed(item, cond_keys, exclusions):
    """آمن للحالة المرضية ومش فيه حاجة المريض مستبعدها."""
    if cond_keys and not safe_for_all(item, cond_keys):
        return False
    text = item.get("meal", "") if isinstance(item, dict) else str(item)
    return not any(ex in text for ex in exclusions)


def _single_fruit_day(day, cond_keys, exclusions):
    """يوم الصنف الواحد: أول فاكهة آمنة، وبتتكرر على اليوم كله."""
    for fruit in day["fruits"]:
        probe = {"meal": f"{fruit['name']} {fruit['portions']['lunch']}"}
        if _is_allowed(probe, cond_keys, exclusions):
            return fruit
    return None


def build_chemical_plan(symptoms=None, exclusions=None, gender=None):
    """الدورة الست أيام، مفلترة على حالة المريض.

    بترجع (days, warnings) وكل تحذير له kind:
        unfillable    خانة مقدرناش نأمّنها، واتسابت فاضية
        caution       اليوم اتبنى بس محتاج مراجعة للحالة دي
        below_floor   مجموع اليوم تحت الحد الآمن بتاع الموقع

    مفيش نوع فيهم بيمنع حاجة. الأيام بتتبني كلها والقرار للأخصائي.
    """
    exclusions = list(exclusions or [])
    floor = _floor_for(gender)
    cond_keys = unsafe_keys_for(symptoms or [])
    days, warnings = [], []

    for day in CHEMICAL_DAYS:
        entry = {
            "day": day["name"],
            "day_en": day["name_en"],
            "cycle_key": day["key"],
            "note": day["note"],
            "note_en": day["note_en"],
            "forbidden": list(day["forbidden"]),
            "forbidden_en": list(day["forbidden_en"]),
            "diet_type": "chemical",
            "meal_labels": CHEMICAL_SYSTEM["meal_labels"],
            "meal_emojis": CHEMICAL_SYSTEM["meal_emojis"],
        }
        total_cal = total_p = 0

        if day.get("single_fruit"):
            fruit = _single_fruit_day(day, cond_keys, exclusions)
            if fruit is None:
                warnings.append({
                    "kind": "unfillable",
                    "day": day["name"], "day_en": day["name_en"], "slot": None,
                    "reason": "مفيش فاكهة مسموحة تناسب حالة المريض في يوم الصنف الواحد.",
                    "reason_en": ("No permitted fruit fits this client's conditions "
                                  "on the single-fruit day."),
                })
            else:
                for slot in SLOTS:
                    entry[slot] = f"{fruit['name']} {fruit['portions'][slot]}"
                    total_cal += fruit["cal"]
                    total_p += fruit["p"]
        else:
            for slot in SLOTS:
                options = [o for o in day["meals"][slot]
                           if _is_allowed(o, cond_keys, exclusions)]
                if not options:
                    label = CHEMICAL_SYSTEM["meal_labels"][slot]
                    label_en = CHEMICAL_SYSTEM["meal_labels_en"][slot].lower()
                    warnings.append({
                        "kind": "unfillable",
                        "day": day["name"], "day_en": day["name_en"], "slot": slot,
                        "reason": f"مفيش اختيار آمن لـ{label} في {day['name']} "
                                  f"مع حالة المريض.",
                        "reason_en": (f"No safe option for {label_en} on "
                                      f"{day['name_en']} given this client's "
                                      f"conditions."),
                    })
                    continue
                chosen = options[0]
                entry[slot] = chosen["meal"]
                total_cal += chosen.get("cal", 0)
                total_p += chosen.get("p", 0)

        # تنبيهات اليوم للحالات اللي البروتوكول نفسه بيستدعي مراجعتها.
        # دي مش منع -- اليوم اتبنى عادي -- فبتترحّل على اليوم عشان تبان في
        # مكانها، وعلى الملاحظات عشان متتفوتش.
        day_cautions = []
        for cond_key, text in (day.get("cautions") or {}).items():
            if cond_key in cond_keys:
                day_cautions.append(text)
                warnings.append({
                    "kind": "caution",
                    "day": day["name"], "day_en": day["name_en"], "slot": None,
                    "reason": text["ar"], "reason_en": text["en"],
                })
        # الدورة دي أيامها تحت الحد الآمن بطبيعتها -- يوم المشروبات حوالي
        # ربع الحد. البادج بتاع الفرق في المعاينة مش بيشتغل عليها لأن أيامها
        # مالهاش target_cal (النظام ده مش بيعدي على تدوير السعرات)، فالرقم كان
        # بيتعرض عادي من غير أي إشارة إنه تحت الحد.
        if total_cal < floor:
            day_cautions.append({
                "ar": f"مجموع اليوم {total_cal} kcal — تحت الحد الآمن "
                      f"({floor} kcal). الدورة قصيرة بطبيعتها، بس ده محتاج "
                      f"إشراف ومدة محدودة.",
                "en": f"This day totals {total_cal} kcal, under the "
                      f"{floor} kcal floor. The cycle is short by design, but "
                      f"this needs supervision and a limited duration.",
            })
            warnings.append({
                "kind": "below_floor",
                "day": day["name"], "day_en": day["name_en"], "slot": None,
                "kcal": total_cal, "floor": floor,
                "reason": day_cautions[-1]["ar"],
                "reason_en": day_cautions[-1]["en"],
            })

        entry["cautions"] = day_cautions

        entry["total_cal"] = total_cal
        entry["total_p"] = total_p
        days.append(entry)

    return days, warnings

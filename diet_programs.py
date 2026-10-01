# -*- coding: utf-8 -*-
"""برامج التغذية الـ12 — المنطق. الجداول في الملفات التلاتة اللي جنبه.

الدكتور بعت ورقة الشركة الحقيقية (IR Formula: مقاومة الأنسولين /
لو-كارب) وقال: خد منها الأفكار، واعمل أوبشن أختار منه البرنامج زي شاشة
الشركة، وأول ما أدوس يتعمل على طول بالأكل بتاعه.

‏الورقة دي شكلها كان القرار المعماري: سبعة أيام × أربع وجبات، كل وجبة
سطر قصير فيه الحصة والبديل ("سلطة أو خضار مشكل"). فالجداول كلها مكتوبة
بنفس الشكل بالظبط، في:

    diet_program_tables.py    لو-كارب · لو-فات · DASH
    diet_program_plant.py     فيجن · لاكتو · لاكتو-أوفو · أوفو
    diet_program_special.py   ديتوكس · أطفال · رضاعة · Optitect

‏وكيتو موجود قبل كده في meal_extra.NEW_SYSTEMS، فبقى العدد 12.


‏الفرق بين البرامج دي وباقي الأنظمة في DIET_PLAN_TYPES
────────────────────────────────────────────────────────
‏النظام العادي **شكل**: خانات وجبات وهدف سعرات، والمحرّك بيملّي الخانات
من مجموعة وجبات الهدف فمافيش يومين متشابهين. البرامج دي العكس: الأكل
نفسه هو البرنامج.

‏وده كان الفرق الحقيقي في اللو-كارب: اللي كان موجود قبل كده بيفلتر
النشويات من قايمة عامة، فالناتج كان خطة عادية ناقصة حاجة -- مش ورقة
لو-كارب ليها أكلها وترتيبها.


‏الحصص بتتظبّط على هدف العميل
──────────────────────────────
‏ورقة الشركة حصصها ثابتة لكل الناس. ده مايمشيش هنا: الموقع بيحسب هدف
سعرات من وزن العميل وطوله وسنه ونشاطه، وورقة ثابتة معناها إن واحد
هدفه 1400 وواحد هدفه 2600 ياخدوا نفس الأكل.

‏فالجدول بيحدّد **الأكل والترتيب**، وportion_scale بيضرب الحصص في
(الهدف ÷ مجموع اليوم). المعامل محدود بين 0.6 و1.8: أقل من كده الطبق
بيبقى سخيف (30جم دجاج)، وأكتر من كده بيبقى مستحيل ياكله.


‏الفلترة الطبية: بتختار جوّه الخانة، ومابتستبدلش
──────────────────────────────────────────────────
‏نفس قاعدة chemical_diet بالحرف. كل خانة فيها أكتر من اختيار من عائلات
خطر مختلفة، والفلترة بتشيل اللي مش آمن وتاخد **أول اللي فضل**:

    العميل اللي مالوش حالة   ياخد اختيار الورقة الأصلية (الأول)
    اللي عنده حالة           ينزل للبديل الآمن اللي بعده

‏و**مابتقعش على قايمة عامة ولا بتستبدل من SAFE_ALTERNATIVES**: بديل
اللو-كارب من قايمة عامة بيرجع أرز وخبز -- آمن، بس مابقاش لو-كارب.
والخانة اللي مفيش فيها اختيار آمن بترجع تحذير للدكتور، مش أكل مش آمن.


‏برنامجين مش للتخسيس
─────────────────────
‏Kids و Breast Feeding برامج نمو ورضاعة. خطة بعجز سعرات لطفل بيكبر أو
لأم بترضّع دي ضرر، مش خطة -- والموقع كله مبني على إنه يحسب عجز.

‏فالاتنين ليهم حد أدنى في GROWTH_FLOORS، والتظبيط مابينزلش تحته، وفيه
تحذير صريح لو الهدف المختار تخسيس. وده متحقّق منه باختبار بيحاول يعمل
الحالة دي بالظبط.


‏الواجهة العامة:
    PROGRAMS              الـ11 برنامج: المفتاح -> أيامه
    PROGRAM_SYSTEMS       مدخل كل برنامج في DIET_PLAN_TYPES
    PROGRAM_MEALS         كل نصوص الوجبات مسطّحة، لفحص الترجمة
    build_program_plan()  -> (days, warnings)
"""

from meal_database import safe_for_all, unsafe_keys_for
from zigzag import _floor_for

from diet_program_tables import LOW_CARB, LOW_FAT, DASH
from diet_program_plant import (VEGAN, LACTO_VEGETARIAN,
                                LACTO_OVO_VEGETARIAN, OVO_VEGETARIAN)
from diet_program_special import DETOX, KIDS, BREAST_FEEDING, OPTITECT

SLOTS = ["breakfast", "lunch", "dinner", "snack"]

PROGRAMS = {
    "low_carb_program": LOW_CARB,
    "low_fat": LOW_FAT,
    "dash": DASH,
    "detox": DETOX,
    "kids": KIDS,
    "breast_feeding": BREAST_FEEDING,
    "vegan": VEGAN,
    "lacto_vegetarian": LACTO_VEGETARIAN,
    "lacto_ovo_vegetarian": LACTO_OVO_VEGETARIAN,
    "ovo_vegetarian": OVO_VEGETARIAN,
    "optitect": OPTITECT,
}

# ‏حد أدنى للسعرات في البرامج اللي مالهاش عجز أصلاً. _floor_for بيرجّع
# حد الموقع العام للتخسيس؛ دول أعلى منه لأن البرنامج نفسه مش تخسيس.
GROWTH_FLOORS = {
    "kids": 1200,            # ‏طفل 6-12 سنة، الحد اللي تحته النمو بيتأثر
    "breast_feeding": 1800,  # ‏احتياج الأم + 400-500 للرضاعة
}

# ‏الأهداف اللي معناها عجز سعرات
LOSS_GOALS = ("weight_loss", "fat_loss", "cutting")

# ‏حدود تظبيط الحصص. برّه الحدود دي الطبق بيبقى إما سخيف أو مستحيل.
#
# ‏الحد الأعلى 2.2 مش 1.8: ورقة اللو-كارب مكتوبة على حوالي 830 سعر في
# اليوم (دي ورقة تخسيس أصلاً)، و1.8 كانت بتوصّلها 1494 بس -- يعني راجل
# هدفه 1800 كان بياخد خطة تحت الحد الآمن وبتحذير. 2.2 بتوصّلها 1826.
MIN_FACTOR, MAX_FACTOR = 0.6, 2.2


# ═══ ملاحظات كل برنامج ═══════════════════════════════════════════════
#
# ‏دي بتطلع على كل يوم في المعاينة وفي الـPDF، وبتقول للعميل البرنامج
# ماشي على إيه. كل واحدة بالعربي والإنجليزي عشان الـPDF الإنجليزي
# مايطلعش عربي.
PROGRAM_NOTES = {
    "low_carb_program": (
        "نشويات قليلة: نشوية واحدة صغيرة في اليوم بحد أقصى، وبروتين في كل وجبة.",
        "Low carbohydrate: one small starch a day at most, with protein at every meal."),
    "low_fat": (
        "دهون مقلّلة: بروتين قليل الدهن ونشويات معقّدة، وأقل زيت مضاف ممكن.",
        "Reduced fat: lean protein and complex carbohydrates, with as little added oil as possible."),
    "dash": (
        "نظام DASH لضغط الدم: خضار وفاكهة كتير، ألبان قليلة الدسم، وأقل صوديوم ممكن — "
        "فمافيش لحوم مملّحة ولا مصنّعة.",
        "The DASH pattern for blood pressure: plenty of vegetables and fruit, low-fat dairy, "
        "and as little sodium as possible -- so no salted or processed meats."),
    "detox": (
        "أكل كامل: مافيش مصنّع ولا سكر مضاف ولا مقلي. الكبد والكلى هما اللي بينضّفوا "
        "الجسم، والبرنامج ده بيشيل الحمل عنهم مش بيجوّع.",
        "Whole foods: nothing processed, no added sugar, nothing fried. The liver and kidneys "
        "are what clear the body; this pattern lightens their load rather than starving you."),
    "kids": (
        "برنامج نمو للأطفال — مش برنامج تخسيس. كل يوم فيه نشوية ولبن وفاكهة وبروتين، "
        "والسعرات مابتنزلش تحت الحد الآمن للنمو.",
        "A growth programme for children -- not a weight-loss one. Every day carries a starch, "
        "milk, fruit and protein, and calories never drop below the safe floor for growth."),
    "breast_feeding": (
        "برنامج رضاعة: سعرات أعلى، وكالسيوم وحديد وأوميجا 3، وسوائل كتير. "
        "مش برنامج تخسيس.",
        "A lactation programme: higher calories, with calcium, iron and omega-3, and plenty of "
        "fluids. Not a weight-loss programme."),
    "vegan": (
        "نباتي كامل: مافيش أي حاجة من أصل حيواني. فيتامين ب12 مش موجود في النبات "
        "فمحتاج مكمّل، والحديد النباتي امتصاصه أحسن مع فيتامين ج.",
        "Fully plant-based: nothing of animal origin. Vitamin B12 is not present in plants so a "
        "supplement is needed, and plant iron absorbs better alongside vitamin C."),
    "lacto_vegetarian": (
        "نباتي + ألبان، بدون بيض.",
        "Plant-based plus dairy, no eggs."),
    "lacto_ovo_vegetarian": (
        "نباتي + ألبان + بيض.",
        "Plant-based plus dairy and eggs."),
    "ovo_vegetarian": (
        "نباتي + بيض، بدون ألبان. الكالسيوم من الطحينة والسبانخ والبروكلي واللوز.",
        "Plant-based plus eggs, no dairy. Calcium comes from tahini, spinach, broccoli and almonds."),
    # ‏Opti-tect مش جدول: العميل بياخد رصيد نقاط وبيصرفه من كتيّب
    # الشركة. فالملاحظة دي بيتزاد عليها الرصيد والفئة المحسوبين لكل
    # عميل (شوف build_program_plan)، والجدول اللي تحت مثال.
    "optitect": (
        "حمية النقاط: رصيد يومي بالنقاط بتصرفه من دليل الأصناف. "
        "الجدول اللي تحت مثال — الأساس هو الرصيد.",
        "The points system: a daily points allowance spent from the food guide. "
        "The table below is an example; the allowance is what governs."),
}

# ‏البرامج اللي لسه ناقصها حاجة من الشركة.
#
# ‏Optitect بقى متنفّذ من عرض الشركة الحقيقي (optitect.py): المعادلات
# والفئات وقواعد التعديل كلها من العرض. اللي لسه ناقص حاجة واحدة --
# **نقاط كل صنف أكل**، وهي في كتيّب «Opti-tect Diet Guide» مش معانا،
# والعرض مابيكتبش المعادلة اللي بتحوّل الأكل لنقاط.
NEEDS_SOURCE = {
    "optitect": (
        "الحساب كله من عرض الشركة. اللي ناقص نقاط أصناف الأكل — دي في كتيّب "
        "«Opti-tect Diet Guide»، فابعته وهتتحمّل من غير ما يتغيّر أي حرف في الحساب.",
        "The whole calculation comes from the company's deck. What is missing is the "
        "points value of each food, which lives in the Opti-tect Diet Guide booklet -- "
        "send it and the foods load without a line of the calculation changing."),
}

# ═══ سطر المرجع لكل برنامج ═══════════════════════════════════════════
#
# ‏الدكتور بعت كتابين (Clinical Nutrition من Wiley، وكتاب عربي ممسوح من
# موقع بيوزّع كتب) عشان أبني منهم. مانقلتش منهم حاجة -- التطبيق بيتباع
# بفلوس، ونقل جداول من كتاب محفوظ الحقوق بيحوّل المشكلة لحسابه.
#
# ‏واللي هو عايزه متحقّق بطريقة أحسن: كل برنامج هنا مبني على **مرجع
# منشور يقدر يكتبه على الورقة** ويوريه لعميل أو جهة رقابية. ده السند
# اللي كان بيدوّر عليه، وبشكل يقدر يدافع عنه.
PROGRAM_SOURCES = {
    "low_carb_program": (
        "ورقة العيادة (IR Formula) + نطاقات الكربوهيدرات في توصيات ADA لمقاومة الأنسولين",
        "The clinic's own IR Formula sheet, with carbohydrate levels per ADA guidance "
        "on insulin resistance"),
    "low_fat": (
        "توصيات منظمة الصحة العالمية للدهون: 20-25% من السعرات، والمشبعة أقل من 10%",
        "WHO guidance on fat intake: 20-25% of energy, with saturated fat under 10%"),
    "dash": (
        "NHLBI / المعاهد الوطنية للصحة الأمريكية — نظام DASH لضغط الدم",
        "NHLBI / US National Institutes of Health -- the DASH eating plan"),
    "detox": (
        "أكل كامل بسعرات يوم طبيعي — مافيش بروتوكول تنقية معترف بيه، "
        "والكبد والكلى هما اللي بينضّفوا",
        "Whole food at a normal day's energy -- no detox protocol is recognised; the "
        "liver and kidneys do the clearing"),
    "kids": (
        "احتياجات الطاقة للأطفال، منظمة الصحة العالمية ومنظمة الأغذية والزراعة (FAO/WHO/UNU)",
        "Child energy requirements, FAO/WHO/UNU"),
    "breast_feeding": (
        "احتياج الرضاعة الزائد (+330 إلى 400 كالوري) ومرجع الكالسيوم والحديد، "
        "معهد الطب الأمريكي (IOM/NASEM)",
        "The added energy cost of lactation (+330 to 400 kcal) with calcium and iron "
        "references, US Institute of Medicine (IOM/NASEM)"),
    "vegan": (
        "موقف جمعية التغذية الأمريكية من الحميات النباتية — كفاية غذائية مع مكمّل ب12",
        "Academy of Nutrition and Dietetics position on vegetarian diets -- adequate "
        "with a B12 supplement"),
    "lacto_vegetarian": (
        "موقف جمعية التغذية الأمريكية من الحميات النباتية",
        "Academy of Nutrition and Dietetics position on vegetarian diets"),
    "lacto_ovo_vegetarian": (
        "موقف جمعية التغذية الأمريكية من الحميات النباتية",
        "Academy of Nutrition and Dietetics position on vegetarian diets"),
    "ovo_vegetarian": (
        "موقف جمعية التغذية الأمريكية من الحميات النباتية، ومصادر الكالسيوم غير الألبان",
        "Academy of Nutrition and Dietetics position on vegetarian diets, with "
        "non-dairy calcium sources"),
    "optitect": (
        "عرض الشركة «Opti-tect Diet — Dr.Nutrition Team 2023»",
        "The company's own deck, \"Opti-tect Diet -- Dr.Nutrition Team 2023\""),
}

_LABELS = {"breakfast": "الفطار", "lunch": "الغداء",
           "dinner": "العشاء", "snack": "سناك"}
_LABELS_EN = {"breakfast": "Breakfast", "lunch": "Lunch",
              "dinner": "Dinner", "snack": "Snack"}
_EMOJIS = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙", "snack": "🍎"}
_HOURS = {"breakfast": 8, "lunch": 14, "dinner": 20, "snack": 17}

# ‏الاسم والوصف اللي بيبانوا في الفورم. مكتوبين بأسماء شاشة الشركة
# عشان الدكتور يلاقي اللي بيدور عليه بنفس الاسم اللي بيشتغل بيه.
_NAMES = {
    "low_carb_program": ("لو كارب (ورقة العيادة)", "Low Carb Diet",
                         "نشويات قليلة، بروتين في كل وجبة — على شكل ورقة العيادة",
                         "Low carb, protein at every meal -- in the clinic sheet's shape"),
    "low_fat": ("لو فات", "Low Fat Diet",
                "دهون مقلّلة، بروتين قليل الدهن ونشويات معقّدة",
                "Reduced fat, lean protein and complex carbohydrates"),
    "dash": ("DASH (لضغط الدم)", "DASH Diet",
             "خضار وفاكهة كتير وأقل صوديوم — للضغط المرتفع",
             "Plenty of vegetables and fruit, minimal sodium -- for high blood pressure"),
    "detox": ("ديتوكس (أكل كامل)", "Detox Diet",
              "أكل كامل من غير مصنّع ولا سكر مضاف ولا مقلي",
              "Whole foods with nothing processed, no added sugar, nothing fried"),
    "kids": ("أطفال (نمو)", "Kids Diet",
             "برنامج نمو للأطفال — مش تخسيس",
             "A growth programme for children -- not weight loss"),
    "breast_feeding": ("رضاعة طبيعية", "Breast Feeding Diet",
                       "سعرات أعلى وكالسيوم وحديد وأوميجا 3 — مش تخسيس",
                       "Higher calories with calcium, iron and omega-3 -- not weight loss"),
    "vegan": ("فيجن (نباتي كامل)", "Vegan Diet",
              "مافيش أي حاجة من أصل حيواني",
              "Nothing of animal origin"),
    "lacto_vegetarian": ("نباتي + ألبان", "Lacto Vegetarian Diet",
                         "نباتي مع الألبان، بدون بيض",
                         "Plant-based with dairy, no eggs"),
    "lacto_ovo_vegetarian": ("نباتي + ألبان وبيض", "Lacto-Ovo Vegetarian Diet",
                             "نباتي مع الألبان والبيض",
                             "Plant-based with dairy and eggs"),
    "ovo_vegetarian": ("نباتي + بيض", "Ovo Vegetarian Diet",
                       "نباتي مع البيض، بدون ألبان",
                       "Plant-based with eggs, no dairy"),
    "optitect": ("Optitect (نظام النقاط)", "Optitect Diet (points)",
                 "رصيد نقاط من الوزن والهدف — مستني كتيّب نقاط الأصناف",
                 "A points allowance from weight and goal -- awaiting the food-points "
                 "booklet"),
}


def _system_entry(key):
    name_ar, name_en, desc_ar, desc_en = _NAMES[key]
    source_ar, source_en = PROGRAM_SOURCES.get(key, ("", ""))
    return {
        "name": name_ar,
        "name_en": name_en,
        # ‏سطر المرجع: بيبان للدكتور وهو بيختار، وبيروح على الورقة كمان
        "source": source_ar,
        "source_en": source_en,
        "meals": list(SLOTS),
        "meal_labels": dict(_LABELS),
        "meal_labels_en": dict(_LABELS_EN),
        "meal_emojis": dict(_EMOJIS),
        "meal_hours": dict(_HOURS),
        "description": desc_ar,
        "description_en": desc_en,
        # ‏علامة بتقول للمحرّك إن البرنامج ده جداوله هنا، مش خانات
        # بتتملّي من مجموعة وجبات الهدف
        "program": key,
    }


PROGRAM_SYSTEMS = {key: _system_entry(key) for key in PROGRAMS}

# ‏كل نصوص الوجبات في قايمة مسطحة، عشان فحص الترجمة يعدي عليها ويقع لو
# اتضافت وجبة بكلمة مش في القاموس. لازم تفضل مسطحة: الفحص بيمشي على
# القواميس اللي فيها مفتاح "meal"، ولو مشى على PROGRAMS نفسها كان هياخد
# أسماء الأيام على إنها وجبات وهي مش كده.
PROGRAM_MEALS = []
for _days in PROGRAMS.values():
    for _day in _days:
        for _slot in SLOTS:
            PROGRAM_MEALS.extend(_day["meals"][_slot])


def _is_allowed(item, cond_keys, exclusions):
    """آمن للحالة المرضية ومش فيه حاجة العميل مستبعدها."""
    if cond_keys and not safe_for_all(item, cond_keys):
        return False
    text = item.get("meal", "") if isinstance(item, dict) else str(item)
    return not any(ex in text for ex in exclusions)


def _floor_for_program(program, gender):
    """‏الحد الأدنى للسعرات في البرنامج ده.

    ‏برامج النمو والرضاعة حدها أعلى من حد الموقع العام، لأن الحد العام
    محسوب لخطة تخسيس -- ودي مش خطط تخسيس.
    """
    site_floor = _floor_for(gender)
    return max(site_floor, GROWTH_FLOORS.get(program, 0))


def build_program_plan(program, target_cal=0, symptoms=None, exclusions=None,
                       gender=None, goal_type=None, weight=None):
    """‏جدول البرنامج، مفلتر على حالة العميل ومظبوط على هدفه.

    بترجع (days, warnings) وكل تحذير له kind:
        unfillable    خانة مقدرناش نأمّنها، واتسابت فاضية
        not_for_loss  برنامج نمو أو رضاعة والهدف المختار تخسيس
        below_floor   مجموع اليوم تحت الحد الآمن للبرنامج ده
        needs_source  البرنامج هيكل عام ومحتاج ورقة الشركة

    مفيش نوع فيهم بيمنع حاجة. الأيام بتتبني كلها والقرار للأخصائي --
    نفس قاعدة chemical_diet و sleeve_diet.
    """
    days_table = PROGRAMS.get(program)
    if not days_table:
        return [], [{"kind": "unknown_program", "day": None, "slot": None,
                     "reason": "برنامج مش معروف: %s" % program,
                     "reason_en": "Unknown programme: %s" % program}]

    from portion_scale import scale_meal

    exclusions = list(exclusions or [])
    cond_keys = unsafe_keys_for(symptoms or [])
    floor = _floor_for_program(program, gender)
    days, warnings = [], []

    # ‏برنامج نمو أو رضاعة والهدف تخسيس: ده بيتقال مرة واحدة في الأول،
    # مش على كل يوم. والخطة بتتبني عادي -- القرار للدكتور، بس شايف.
    if program in GROWTH_FLOORS and str(goal_type or "") in LOSS_GOALS:
        warnings.append({
            "kind": "not_for_loss", "day": None, "slot": None,
            "reason": "«%s» برنامج نمو مش برنامج تخسيس، والهدف المختار تخسيس. "
                      "السعرات مش هتنزل تحت %d، فراجع الهدف."
                      % (_NAMES[program][0], floor),
            "reason_en": ('"%s" is a growth programme, not a weight-loss one, and the '
                          "goal selected is weight loss. Calories will not go below %d, "
                          "so review the goal." % (_NAMES[program][1], floor)),
        })

    if program in NEEDS_SOURCE:
        reason_ar, reason_en = NEEDS_SOURCE[program]
        warnings.append({"kind": "needs_source", "day": None, "slot": None,
                         "reason": reason_ar, "reason_en": reason_en})

    note_ar, note_en = PROGRAM_NOTES.get(program, ("", ""))
    source_ar, source_en = PROGRAM_SOURCES.get(program, ("", ""))

    # ═══ Opti-tect: الوصفة بالنقاط ═══
    #
    # ‏ده البرنامج الوحيد اللي مش جدول: العميل بياخد رصيد نقاط وبيصرفه
    # من كتيّب الشركة. فالجدول هنا مثال، والرقم اللي الأخصائي محتاجه
    # فعلاً هو الرصيد والفئة -- وده بيتحسب من المعادلات اللي في عرض
    # الشركة، وبيروح في ملاحظة كل يوم عشان يطلع على الورقة.
    # ‏الوصفة بتروح في ملاحظة اليوم (فبتطلع على ورقة العميل)، **ومش**
    # في التحذيرات: التحذيرات بتتكتب في الملاحظات بعلامة ⚠️، ورصيد
    # النقاط مش مشكلة -- ده الوصفة نفسها.
    points_lines = []
    if program == "optitect":
        import optitect
        points_lines, _detail = optitect.prescribe(
            weight, goal_type=goal_type, gender=gender)

    for day in days_table:
        entry = {
            "day": day["name"],
            "day_en": day["name_en"],
            "diet_type": program,
            "program": program,
            "note": note_ar,
            "note_en": note_en,
            # ‏سطر المرجع على كل يوم، فبيطلع على الورقة
            "source": source_ar,
            "source_en": source_en,
            "meal_labels": dict(_LABELS),
            "meal_emojis": dict(_EMOJIS),
        }
        # ‏Opti-tect: الرصيد والفئة في ملاحظة اليوم، لأن ده اللي
        # الأخصائي بيشتغل بيه -- الجدول مثال بس
        if points_lines:
            entry["note"] = note_ar + " " + " ".join(
                ar for ar, _ in points_lines)
            entry["note_en"] = note_en + " " + " ".join(
                en for _, en in points_lines)
        picked = {}
        for slot in SLOTS:
            options = [o for o in day["meals"][slot]
                       if _is_allowed(o, cond_keys, exclusions)]
            if not options:
                warnings.append({
                    "kind": "unfillable",
                    "day": day["name"], "day_en": day["name_en"], "slot": slot,
                    "reason": "مفيش اختيار آمن لـ%s في %s مع حالة العميل."
                              % (_LABELS[slot], day["name"]),
                    "reason_en": ("No safe option for %s on %s given this client's "
                                  "conditions." % (_LABELS_EN[slot].lower(),
                                                   day["name_en"])),
                })
                continue
            # ‏أول اللي فضل: اختيار الورقة الأصلية لو عدّى، وإلا البديل
            picked[slot] = options[0]

        # ═══ تظبيط الحصص على هدف العميل ═══
        #
        # ‏الجدول حصصه ثابتة، وهدف العميل رقم متغيّر. المعامل الواحد
        # بيتحط على كل خانة، وscale_meal بيرجّع المعامل **الفعلي** بعد
        # تقريب الجرامات -- فالسعرات المكتوبة تبقى اللي في الطبق فعلاً،
        # مش اللي كنا عايزينها.
        base_total = sum(item["cal"] for item in picked.values())
        factor = 1.0
        if target_cal and base_total > 0:
            factor = float(target_cal) / base_total
            factor = min(MAX_FACTOR, max(MIN_FACTOR, factor))

        # ‏برامج النمو والرضاعة: الحد الأدنى **بيتنفّذ**، مش بيتحذّر منه.
        #
        # ‏قبل كده التحذير كان بيقول «السعرات مش هتنزل تحت 1500» والتظبيط
        # كان بينزّلها فعلاً لـ886 لطفل هدفه 900 -- يعني الجملة كانت
        # بتكدب، والخطة اللي بتطلع دي بالظبط الحاجة اللي البرنامج مفروض
        # يمنعها. دلوقتي المعامل بيترفع عشان اليوم يوصل الحد.
        if program in GROWTH_FLOORS and base_total > 0:
            factor = max(factor, float(floor) / base_total)

        def _apply(f):
            """‏يظبّط اليوم بالمعامل ده ويرجّع (النصوص، السعرات، البروتين).

            ‏المعامل اللي scale_meal بيرجّعه هو **الفعلي** بعد تقريب
            الجرامات لأقرب 5 أو 10، فالسعرات هنا هي اللي في الطبق
            فعلاً -- مش اللي كنا طالبينها.
            """
            texts, cal, prot = {}, 0.0, 0.0
            for slot_key, chosen in picked.items():
                text, effective = chosen["meal"], 1.0
                if abs(f - 1.0) >= 0.01:
                    text, effective = scale_meal(chosen["meal"], f)
                texts[slot_key] = text
                cal += chosen["cal"] * effective
                prot += chosen["p"] * effective
            return texts, cal, prot

        texts, total_cal, total_p = _apply(factor)

        # ‏برامج النمو والرضاعة: الحد الأدنى **بيتنفّذ**، مش بيتحذّر منه.
        #
        # ‏وتقريب الجرامات بياكل من المعامل، فطلب المعامل المظبوط مش
        # كفاية -- طفل هدفه 600 كان بيطلع له 1483 والحد 1500. فبنرفع
        # المعامل ونقيس تاني لحد ما اليوم يعدّي الحد فعلاً. تلات
        # تمريرات كفاية: كل واحدة بتزوّد 4%، والتقريب بياكل 3% أقصاه.
        if program in GROWTH_FLOORS:
            tries = 0
            while total_cal < floor and factor < MAX_FACTOR and tries < 3:
                factor = min(MAX_FACTOR, factor * 1.04)
                texts, total_cal, total_p = _apply(factor)
                tries += 1

        for slot_key, text in texts.items():
            entry[slot_key] = text

        entry["total_cal"] = int(round(total_cal))
        # ‏الاسم "total_p" مش "total_protein": ده اللي الجدول والـPDF
        # بيقروا منه (نفس اللي chemical_diet بيكتبه). كان بيتكتب
        # بالاسم التاني، فعمود البروتين كان بيطلع صفر في كل يوم.
        entry["total_p"] = int(round(total_p))

        # ‏تحت الحد الآمن: بيتقال، والخطة بتفضل. الدكتور هو اللي يقرر
        # يرفع الهدف ولا يغيّر البرنامج.
        if entry["total_cal"] < floor:
            warnings.append({
                "kind": "below_floor",
                "day": day["name"], "day_en": day["name_en"], "slot": None,
                "reason": "%s مجموعه %d سعر، والحد الآمن لـ«%s» %d."
                          % (day["name"], entry["total_cal"],
                             _NAMES[program][0], floor),
                "reason_en": "%s totals %d kcal against a %d floor for \"%s\"."
                             % (day["name_en"], entry["total_cal"], floor,
                                _NAMES[program][1]),
            })

        days.append(entry)

    return days, warnings

# -*- coding: utf-8 -*-
"""‏ماكروز الوجبة من الأكل اللي فيها، مش من هدف العميل.

المشكلة
───────
‏الورقة بتطبع للعميل: دهون ٦٤ جم، كارب ١٩٣ جم. الرقمين دول **محسوبين
من الهدف**: السعرات × ٣٠٪ ÷ ٩ للدهون، والباقي كارب. يعني لو الأكل في
الجدول فيه ضعف الكارب ده، الورقة مش هتعرف ومش هتقول.

‏الوجبة في قاعدة البيانات بتحمل رقمين بس -- سعرات وبروتين. مافيش دهون
ولا كارب، فمينفعش تثبت إن يوم الـLow Carb كاربه فعلاً قليل.

اللي خلّى ده ممكن
──────────────────
‏جدول الأكل (food_data.FOODS) فيه **٩٣٨ صنف وكل واحد بأرقامه لكل ١٠٠
جرام**: سعرات، بروتين، كارب، دهون. الجدول موجود من الأصل للمحلّل
وصفحات /foods، ومكانش موصول بالوجبات خالص.

‏فالملف ده بيوصلهم: بياخد نص الوجبة، يقسّمه أصناف، يطلّع كمية كل
صنف، يطابقه بالجدول، ويجمع.

تلات حاجات بتخلّي المطابقة تنجح
────────────────────────────────
  ١) ‏تطبيع العربي: الوجبة بتكتب "خبز اسمر" والجدول "خبز أسمر".
     normalize_ar بتوحّدهم، وهي نفس الدالة اللي الفلترة الطبية
     ماشية عليها -- مقياس واحد في المكانين.

  ٢) ‏الأسماء العامة: الوجبة بتكتب "جبن" و"ارز" و"سلطة"، والجدول
     فيه "جبن قريش" و"أرز أبيض مطبوخ" بس. من غير جسر، ٧٢٪ من
     الأصناف مابتتطابقش -- قِسْتها.

  ٣) ‏الحصة الافتراضية: "🥗 سلطة" من غير جرامات. measures.FOOD_MEASURES
     فيه حصة كل صنف بالجرام (كوب أرز = ١٥٠ جم)، وهي اللي بتتحسب.

قاعدة واحدة لازمة
─────────────────
‏الرقم المحسوب **مابيستبدلش** الرقم المكتوب في قاعدة الوجبات. السعرات
والبروتين المكتوبين بإيد الدكتور هما المرجع، والمحسوب بيتقارن بيهم:
لو قريب، الكارب والدهون المحسوبين يتصدّقوا ويتكتبوا على الورقة. لو
بعيد، الوجبة بتترفع إنها "مش مقروءة" والورقة بتفضل على الحساب القديم.

‏ده نفس منطق قراءة ورقة التحليل: الرقم المحسوب لازم يتأكّد من مصدر
تاني قبل ما يتكتب.
"""

import os
import re

# ‏إيموجي الوجبة. بيتشال قبل أي مطابقة.
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿️]+")

# ‏كمية بالجرام أو المليلتر: "150جم" أو "(60جم)" أو "5 مل"
_GRAMS = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:جم|جرام|غ|g|مل|ml)\b")

# ‏عدد مجرّد في آخر الصنف: "بيض 4" أو "موز 1". مابيتاخدش لو الصنف
# فيه جرامات أصلاً.
_COUNT = re.compile(r"(?:^|\s)(\d+(?:[.,]\d+)?)\s*$")

# ‏عدد جوه الصنف وبعده وصف: "بيض اومليت 3 بالسبانخ"، "طعمية بالفرن 5".
# ‏_COUNT لوحده كان بيقرا العدد لو جه في الآخر بس، فأي كلمة بعده بتخلّي
# الصنف حصة افتراضية -- بيضة واحدة مهما كان الرقم. ظهرت لما زرار + بقى
# يزوّد البيض: الرقم على الورقة اتغيّر ومجموع اليوم مااتحركش.
# ‏الرقم لازم يكون لوحده بين مسافات أو قوس: "1/2" مش عدد. ومش سعرات:
# ‏أول نسخة قرت "خبز (390 kcal)" كـ٣٩٠ رغيف -- ١٠٣ ألف سعرة لوجبة واحدة.
_INNER_COUNT = re.compile(
    r"(?:^|[\s(])(\d+(?:[.,]\d+)?)(?=[\s)]|$)(?!\s*(?:kcal|سعر|ك\.?س))")

# ‏كلمات بتوصف الطهي مش الأكل. بتتشال قبل المطابقة عشان "صدر دجاج
# مشوي" يطابق "صدر دجاج" لو ده اللي في الجدول.
_NOISE = ("مشوي", "مشوية", "مسلوق", "مسلوقة", "مطبوخ", "مطبوخة", "بالفرن",
          "في الفرن", "سوتيه", "متبل", "طازج", "طازجة", "بدون ملح",
          "بدون سكر", "لايت", "خالي الدسم", "قليل الدسم", "كامل الدسم")

# ═══════════════════════════════════════════════════════════════════
#  جسر الأسماء العامة
# ═══════════════════════════════════════════════════════════════════
#
# ‏الوجبة بتكتب الاسم العام والجدول فيه المحدد. كل سطر هنا: الاسم
# العام -> الصنف اللي بيمثّله في الجدول.
#
# ‏الاختيار مش عشوائي -- بياخد **الأشيع في المطبخ المصري/الخليجي**:
# الأرز أبيض مطبوخ مش بني، والجبن قريش لأنه الأكتر في جداول التخسيس.
# وكل سطر منهم بيتأكّد إنه موجود في الجدول باختبار.
GENERIC = {
    # ‏"ارز بني" قبل "ارز": الجدول فيه "أرز بني مطبوخ"، بس أسماء الجدول
    # بتتلاقى لما تكون **جوّه** نص الصنف، و"مطبوخ" مش مكتوبة في الوجبة.
    # فـ"ارز بني 140جم" كان بيقع على "ارز" العام ويتحسب أرز أبيض.
    # raw (dry) weight is a different food: 365 vs 130 kcal/100 g for rice.
    # Sourced rows in meal_food_sources (USDA SR Legacy), never the cooked row.
    "ارز نيء": "أرز أبيض نيء", "رز نيء": "أرز أبيض نيء",
    "ارز نيه": "أرز أبيض نيء", "رز نيه": "أرز أبيض نيء",
    "ارز خام": "أرز أبيض نيء", "رز خام": "أرز أبيض نيء",
    "ارز جاف": "أرز أبيض نيء", "رز جاف": "أرز أبيض نيء",
    "معكرونة نيئة": "معكرونة نيئة", "مكرونة نيئة": "معكرونة نيئة",
    "معكرونة جافة": "معكرونة نيئة", "مكرونة جافة": "معكرونة نيئة",
    "معكرونة نيه": "معكرونة نيئة", "مكرونة نيه": "معكرونة نيئة",
    # "سمك سلمون" is salmon, not the generic tilapia reached through "سمك"
    # milk with a stated fat level: the sourced milk rows, not لبن رايب
    "لبن كامل الدسم": "حليب كامل الدسم", "لبن كامل": "حليب كامل الدسم",
    "لبن خالي الدسم": "حليب خالي الدسم", "حليب خالي الدسم": "حليب خالي الدسم",
    "سمك سلمون": "سلمون", "سمك التونة": "تونة معلبة بالماء",
    "ارز بني": "أرز بني مطبوخ",
    "رز بني": "أرز بني مطبوخ",
    "ارز": "أرز أبيض مطبوخ",
    "رز": "أرز أبيض مطبوخ",
    "خبز": "خبز أسمر",
    "عيش": "خبز أسمر",
    "توست": "توست أسمر",
    "جبن": "جبن قريش",
    "جبنة": "جبن قريش",
    "بيض": "بيضة كاملة",
    "بيضة": "بيضة كاملة",
    "بيضتين": "بيضة كاملة",
    "اومليت": "بيضة كاملة",
    "أومليت": "بيضة كاملة",
    "عجة": "بيضة كاملة",
    "دجاج": "صدر دجاج",
    "فراخ": "صدر دجاج",
    "سمك": "سمك بلطي",
    "لحم": "لحم بقري قليل الدهن",
    "لحمة": "لحم بقري قليل الدهن",
    # ‏"كبدة" و"كفتة" من غير وصف: الجدول فيه "كبدة بقري" و"كبدة دجاج"
    # و"كفتة مشوية"، وأسماء الجدول بتتلاقى لما تكون **جوّه** نص الصنف --
    # و"🍗 كبدة 200جم" مكتوبة كده في القاعدة. فالصنفين كانوا بصفر سعرة
    # وفي "مش متعرّف" في قايمة المشتريات، وهما من أكتر الأصناف تكراراً
    # في الجداول المصرية.
    "كبدة": "كبدة بقري",
    "كفتة": "كفتة مشوية",
    "سلطة": "سلطة خضراء",
    "خضار": "خضار مشكل مجمد",
    "فطر": "مشروم",
    "مكسرات": "لوز",
    # almond milk, never the nut (580 kcal) and never cow milk
    "لبن لوز": "حليب لوز غير محلي",
    "لبن اللوز": "حليب اللوز غير محلي",
    # ‏"زبدة فول" = زبدة الفول السوداني. من غيرها كانت بتتحسب زبدة عادية (٧١٧).
    "زبدة فول": "زبدة فول سوداني",
    "زبادي": "زبادي خالي الدسم",
    "لبن": "لبن رايب",
    # ‏"حليب" ماكانتش في الخريطة، و"حليب خالى الدسم" موجود في جدول
    # الأكل بس find_food مابتوصلوش (أسماء الجدول بتتلاقى لما تكون
    # **جوّه** نص الصنف، و"خالى" مش مكتوبة في كل وجبة). والقاعدة مليانة
    # وجبات بتكتب "حليب" -- فكل واحدة فيهم كانت بتتحسب بصفر سعرة، وفي
    # قايمة المشتريات بتروح لـ"مش متعرّف".
    #
    # ‏ولبن النبات **قبل** اللبن العادي: القاعدة "الأقرب لأول الصنف
    # وبعدين الأطول"، والاتنين بيبدأوا من نفس المكان فالأطول بيكسب.
    # من غير السطور دي، "حليب اللوز" كان هيتحسب لبن بقري -- ١٤.٦ سعرة
    # بقت ٤٠، يعني تلات أضعاف على كل وجبة فيها لبن لوز.
    "حليب اللوز": "حليب اللوز غير محلى",
    "حليب لوز": "حليب لوز غير محلى",
    "حليب الصويا": "حليب الصويا",
    "حليب صويا": "حليب الصويا",
    "حليب الرز": "حليب الرز",
    "حليب الأرز": "حليب الرز",
    "حليب": "لبن رايب",
    "شوفان": "شوفان خام",
    "فول": "فول مدمس",
    "عدس": "عدس",
    "بطاطس": "بطاطس مسلوقة",
    "بطاطا": "بطاطا حلوة",
    "مكرونة": "مكرونة مسلوقة",
    "معكرونة": "مكرونة مسلوقة",
    "زيت زيتون": "زيت زيتون",
    "طحينة": "طحينة",
    "عسل": "عسل نحل",
    "تمر": "تمر جاف",
    "موز": "موز",
    "تفاح": "تفاح",
    "خيار": "خيار",
    "طماطم": "طماطم",
    "جرجير": "جرجير",
    "خس": "خس",
    "ملوخية": "ملوخية مطبوخة",
    "كوسة": "كوسة",
    "بروكلي": "بروكلي",
    "تونة": "تونة معلبة بالماء",
    "حمص": "حمص مسلوق",
    "لوز": "لوز",
    "جوز": "عين جمل",
    "افوكادو": "أفوكادو",
    "فاكهة": "تفاح",
    "برتقال": "برتقال",
    "فراولة": "فراولة",
}

# ‏أصناف مكتوبة في الوجبات أقصر من اسمها في الجدول، فكانت بتتحسب **صفر**:
# "كينوا 100جم" والجدول فيه "كينوا مطبوخة"، "فيتا" والجدول فيه "جبنة
# فيتا". صاحب المشروع شافها لما زرار الحذف والكمية مأثّروش على مجموع
# اليوم. الأرقام هي أرقام الجدول نفسه -- السطور دي ربط أسماء بس.
#
# ‏دي بتتطابق **ككلمة كاملة** مش كحروف زي GENERIC. "زيت" جوه "زيتون":
# بالحروف، "زيتون 4" كانت هتبقى ٤ ملاعق زيت (حوالي ٥٠٠ سعرة زيادة).
#
# ‏اختيارات فيها حكم، مكتوبة عشان تتراجع:
#   ‏- "دبس" من غير نوع = دبس تمر (اللي بيتاكل مع الطحينة). الرمان مكتوب
#     باسمه في الوجبات اللي فيها رمان.
#   ‏- "طعمية مشوية" بتاخد رقم الطعمية المقلية -- الجدول مافيهوش غيرها،
#     فالرقم أعلى من الحقيقة. أقرب من صفر، بس مش مظبوط.
#   ‏- "شيش طاووق" = صدر دجاج: قطع صدر متتبّلة ومشوية. التتبيلة فيها
#     زيت مش محسوب.
#   ‏- "ستيك" من غير نوع = لحم بقري قليل الدهن، زي "لحم" في GENERIC.
GENERIC_WORDS = {
    "زيت": "زيت زيتون",
    "فيتا": "جبنة فيتا",
    "كينوا": "كينوا مطبوخة",
    "زعتر": "زعتر ناشف",
    "دبس": "دبس تمر",
    "حريرة": "حريرة مغربية",
    "بارميزان": "جبنة بارميزان",
    "برغل": "برغل مطبوخ",
    "تورتيلا": "عيش تورتيلا",
    "حلوم": "جبنة حلوم",
    "كسكس": "كسكسي مطبوخ",
    "شاي": "شاي بدون سكر",
    "فروج": "فراخ مشوية (ربع فرخة)",
    "فرخة": "فراخ مشوية (ربع فرخة)",
    "طعمية": "فلافل/طعمية",
    "شيش طاووق": "صدر دجاج",
    "ستيك": "لحم بقري قليل الدهن",
    "يوغورت": "زبادى خالى الدسم",
    # ‏صاحب المشروع حدّد الأسماء اللي من غير نوع: "فاصوليا خضرا، والمشاوي
    # فراخ، والفواكه تفاح". والبيضا بأسمها قبل العامة: "بيض" جوه "بيضاء"،
    # فـ"فاصوليا بيضاء 150جم" كانت بتتحسب **بيضة** (١٥٥ سعرة بدل ٢٠٩).
    "فاصوليا بيضاء": "فاصوليا بيضاء مطبوخة",
    "فاصوليا بيضا": "فاصوليا بيضاء مطبوخة",
    "فاصوليا": "فاصوليا خضراء",
    "مشاوي": "فراخ مشوية (ربع فرخة)",
    "فواكه": "تفاح",
}

_WORD_RX = None


def _word_patterns():
    global _WORD_RX
    if _WORD_RX is None:
        _WORD_RX = [(re.compile(r"(?:^|(?<=[\s(]))" + re.escape(_norm(word))
                                + r"(?=$|[\s)،,.])"), word, specific)
                    for word, specific in GENERIC_WORDS.items()]
    return _WORD_RX

# ‏حصة افتراضية (جرام) للصنف اللي مكتوب من غير كمية، لما
# measures.FOOD_MEASURES مافيهوش. الأرقام حصص مطبخ عادية.
FALLBACK_GRAMS = {
    "سلطة": 150, "خضار": 150, "خيار": 100, "طماطم": 100, "خس": 50,
    "جرجير": 50, "فطر": 80, "ملوخية": 150, "كوسة": 150, "بروكلي": 100,
    "جبن": 50, "زبادي": 200, "لبن": 200, "عسل": 15, "طحينة": 15,
    "زيت زيتون": 10, "مكسرات": 20, "لوز": 20, "جوز": 20,
}

# ‏الفرق المسموح بين السعرات المحسوبة والمكتوبة قبل ما نقول "مش
# مقروءة". ٢٥٪ واسع بالقصد: الحصص الافتراضية تقدير، والمقصود نمسك
# القراءة الغلط مش نطابق للجرام.
TOLERANCE = 0.25


def _norm(text):
    from meal_database import normalize_ar
    return normalize_ar(_EMOJI.sub("", str(text or "")))


def _strip_noise(text):
    out = text
    for word in _NOISE:
        out = out.replace(word, " ")
    return re.sub(r"\s+", " ", out).strip()


_TABLE = None


def _table():
    """‏أسماء جدول الأكل مطبّعة ومرتّبة من الأطول للأقصر."""
    global _TABLE
    if _TABLE is None:
        import food_data
        import meal_food_sources
        import meal_option_foods
        import meal_variant_foods
        rows = []
        # source-backed extras go AFTER the main table: a name already in the
        # main table keeps winning, so nothing existing changes.
        have = {_norm(f.get("n")) for f in food_data.FOODS}
        for food in list(food_data.FOODS) + [
                f for f in meal_food_sources.SOURCED_FOODS
                if _norm(f["n"]) not in have] + list(meal_option_foods.OPTION_FOODS) + list(meal_variant_foods.VARIANT_FOODS):
            name = _norm(food.get("n"))
            if name:
                rows.append((name, food))
        rows.sort(key=lambda row: -len(row[0]))
        _TABLE = rows
    return _TABLE


def find_food(item):
    """‏صنف الجدول اللي الصنف ده بيخصه، أو None.

    ‏**الأقرب لأول الصنف** بيكسب، وعند نفس المكان الأطول. والاختيار
    بيتعمل مرة واحدة بين الجدول المحدد والجسر العام مع بعض -- مش
    الجدول الأول وبعدين الجسر.

    ‏الترتيب ده مش تفصيلة، وجرّبت غيره مرتين وفشل:

      ١) "الأطول في أي مكان":
         "فول بطحينة 150جم" -> **طحينة** (٨٩٢ سعرة/١٠٠جم) بدل الفول،
         فالوجبة بقت ١١٧٦ سعرة والمكتوب ٣٦٠.
         "لبن لوز" -> **لوز** (٥٨٠ سعرة) بدل اللبن.

      ٢) "الأقرب، بس الجدول المحدد الأول وبعدين الجسر":
         نفس الغلط بالظبط. "فول" مش في الجدول (فيه "فول مدمس")،
         فالجدول بيلاقي "طحينة" بس ويرجّعها قبل ما الجسر يشوف "فول"
         في أول الصنف.

    ‏واللي بيخلّي الترتيب صح: اسم الطبق بيبدأ بالمكوّن الأساسي، واللي
    بعده وصف -- "فول **ب**طحينة" الطحينة نكهة والفول هو الأكل.

    ‏والنص بيتجرّب **مرتين**: زي ما هو الأول، وبعدين بعد شيل الوصف.
    السبب إن وصف الدسم في قايمة الوصف (_NOISE) وهو في نفس الوقت جزء
    من أسماء في الجدول: "حليب كامل الدسم" كان بيتشال منه "كامل الدسم"
    فيفضل "حليب"، والجسر العام بيوديه على **لبن رايب** (٤٠ سعرة) بدل
    الحليب الكامل (٦١). يعني كوباية لبن لعميلة بتزوّد وزنها كانت بتتحسب
    ناقصة التلت، والوصف اللي بيفرّق هو اللي اتشال.
    """
    raw = _norm(item)
    for clean in (raw, _strip_noise(raw)):
        if not clean:
            continue
        found = _match(clean)
        if found is not None:
            return found
    return None


_PREFIXES = {"ب", "ل", "و", "ال", "بال", "وال", "لل", "فال", "ف"}


def _find_word(clean, name):
    """Position of `name` in `clean` if it starts at a word start, else -1.

    Plain str.find matched "تين" (fig) inside "بروتين" (protein), so a protein
    scoop counted as a fig (22 kcal). The character before the name must be a
    space, a bracket or an Arabic prefix (ب/ل/و/ال): "بحليب" still reads.
    """
    start = 0
    while True:
        at = clean.find(name, start)
        if at < 0:
            return -1
        head = clean[:at]
        frag = head.split(" ")[-1] if head and not head.endswith(" ") else ""
        frag = frag.lstrip("(")
        if not frag or frag in _PREFIXES:
            return at
        start = at + 1


def _match(clean):
    """‏أقرب صنف لأول النص، بين الجدول والجسر العام مع بعض."""
    best = None                       # ((المكان, -الطول), الصنف)
    for name, food in _table():
        at = _find_word(clean, name)
        if at >= 0:
            key = (at, -len(name))
            if best is None or key < best[0]:
                best = (key, food)

    candidates = [(_find_word(clean, _norm(g)), g, sp)
                  for g, sp in GENERIC.items()]
    for rx, word, specific in _word_patterns():
        m = rx.search(clean)
        candidates.append((m.start() if m else -1, word, specific))

    for at, generic, specific in candidates:
        if at < 0:
            continue
        key = (at, -len(generic))
        if best is not None and key >= best[0]:
            continue
        target = _norm(specific)
        for name, food in _table():
            if name == target:
                best = (key, food)
                break

    return best[1] if best else None


def item_grams(item, food=None):
    """‏كمية الصنف بالجرام، وإزاي اتعرفت.

    ‏بترجّع (جرامات, المصدر): "grams" مكتوبة، "count" عدد × وزن
    الوحدة، "default" حصة افتراضية، أو (0, None) لو مش معروفة.
    """
    text = _norm(item)
    match = _GRAMS.search(text)
    if match:
        try:
            return float(match.group(1).replace(",", ".")), "grams"
        except ValueError:
            pass

    named = _named_unit(text, food)
    if named:
        return named, "count"

    unit = _unit_grams(text, food)
    count = _COUNT.search(text) or _INNER_COUNT.search(text)
    if count and unit:
        try:
            return float(count.group(1).replace(",", ".")) * unit, "count"
        except ValueError:
            pass
    if unit:
        return unit, "default"
    for key, grams in sorted(FALLBACK_GRAMS.items(), key=lambda kv: -len(kv[0])):
        if _norm(key) in text:
            return float(grams), "default"
    return 0.0, None


def _named_unit(text, food):
    """‏"زيت زيتون 1 ملعقة صغيرة" -> ٥ جم: الرقم والوحدة المكتوبين في الصنف.

    ‏من غيرها الوحدة كانت بتتاخد أول واحدة في جدول الصنف -- الملعقة الكبيرة
    (١٤ جم) -- والرقم اللي قبلها ماكانش بيتقري أصلاً، لأن العدد كان
    بيتدوّر عليه في آخر الصنف بس. ملعقة زيت صغيرة كانت بتطلع ٨٠ سعرة زيادة
    على يوم العميل.

    ‏الأطول الأول: "ملعقة صغيرة" قبل "ملعقة" لو الجدول فيه الاتنين.
    """
    if not food:
        return None
    rows = []
    for row in (food.get("units") or []):
        try:
            name, grams = _norm(row[0]), float(row[1])
        except (TypeError, ValueError, IndexError):
            continue
        if name and grams > 0:
            rows.append((name, grams))
    for name, grams in sorted(rows, key=lambda r: -len(r[0])):
        found = re.search(r"(\d+(?:[.,]\d+)?)\s*" + re.escape(name), text)
        if found:
            try:
                return float(found.group(1).replace(",", ".")) * grams
            except ValueError:
                return None
    return None


def _unit_grams(text, food=None):
    """‏وزن الوحدة الواحدة، أو None.

    ‏الترتيب: وحدة الصنف اللي اتعرف فعلاً، وبعدين جدول المكاييل.

    ‏والجدول مابيتقراش على عمى: كان أي اسم في جدول المكاييل يظهر في
    النص بياخد وزنه، حتى لو الصنف اللي اتعرف صنف تاني خالص. فـ"رقاق
    أرز 6" الصنف فيها **رقاق** (٣٠جم للرقاقة)، بس كلمة "أرز" في جدول
    المكاييل بـ١٥٠جم -- فستة رقاقات طلعت **٩٠٠جم** في قايمة المشتريات.
    (كيلو رقاق لبنت بتفطر.)

    ‏فالاسم اللي بيطابق لازم يكون نفس الصنف: جوه اسمه أو اسمه جواه.
    """
    if food:
        for row in (food.get("units") or []):
            try:
                grams = float(row[1])
            except (TypeError, ValueError, IndexError):
                continue
            if grams > 0:
                return grams

    try:
        import measures
    except Exception:
        return None
    fname = _norm(food.get("n")) if food else ""
    best = None
    for key, info in measures.FOOD_MEASURES.items():
        name = _norm(key)
        if not name or name not in text:
            continue
        if fname and name not in fname and fname not in name:
            continue
        if best is None or len(name) > best[0]:
            best = (len(name), info.get("g"))
    return best[1] if best else None


def _default_unit_name(text, food):
    """Unit name the default weight of this item belongs to, or None."""
    try:
        import measures
    except Exception:
        return None
    for row in (food.get("units") or []):
        return str(row[0])
    fname = _norm(food.get("n")) if food else ""
    best = None
    for key, info in measures.FOOD_MEASURES.items():
        name = _norm(key)
        if not name or name not in text:
            continue
        if fname and name not in fname and fname not in name:
            continue
        if best is None or len(name) > best[0]:
            best = (len(name), info.get("unit"))
    return best[1] if best else None


AMBIGUOUS_COUNT = {"خبز أسمر", "شكشوكة"}
_UNIT_WORD = re.compile(r"رغيف|ارغفة|شريح|شرايح|توست|قطع|حبة|حبات|ملعقة|كوب")

_DRY_CATS = {"grain", "legume", "nut", "supplement"}
_ML = re.compile(r"\d\s*(?:مل|ml)\b")


def _is_ml(text):
    return bool(_ML.search(_norm(text)))


# Words that name a specific food, cut, fat or cooking method. When the item
# text has one and the matched table food does not, the match is only the
# nearest food, not the written one, so the item is not counted as verified.
QUALIFIERS = ("شيدر", "موزاريلا", "بارميزان", "رومي", "كامل الدسم", "حليب كامل",
              "مقلي", "بالزبدة", "بالسمن", "بلحم", "بالدجاج", "بالجبن", "بالكريمة",
              "محشي", "مدخن")


# Words that describe size, unit or presentation, not which food it is.
# State words (raw/dry, whole/full-fat) are NOT here: they change the nutrient basis, so
# they must appear in the matched row's name (or be settled by the raw/cooked guard).
_HARMLESS = {"كبير", "كبيره", "صغير", "صغيره", "متوسط", "متوسطه", "وسط", "حبه", "حبات", "قطعه",
             "قطع", "شريحه", "شرايح", "كوب", "اكواب", "ملعقه", "ملاعق", "كبيره", "طبق", "صحن",
             "علبه", "رغيف", "نص", "ونص", "ربع", "حفنه", "مشكل", "مشكله", "بسيط", "سادة", "ساده",
             "مع", "من", "في", "ماء", "الماء", "بيضات", "بيضتين", "بيضتان", "بيضه", "حبتين", "فرن", "متنوعه", "متنوع", "مشكله", "بدون", "طازج", "على", "او", "أو", "kcal", "سعره", "سعر"}


# Cooked-weight basis (the user's weights for meat, poultry, fish and rice mean AFTER cooking,
# WhatsApp 27 Nov 2026 "بعد الطبخ"). The basis of a table row comes from the row's OWN name only:
#   cooked   the name states a cooking preparation (مطبوخ، مشوي، مسلوق، cooked, grilled ...)
#   prepared sold already prepared (canned, smoked, cured, dried)
#   raw      the name states raw / fresh / uncooked
#   unknown  single-food row in scope whose name states no preparation
# Only "cooked" and "prepared" qualify. A label qualifies the BASIS only: it is not proof that the
# row's nutrients are the cooked values of that food, and it says nothing about the source.
# Dishes, soups, sausages and other processed rows are out of scope for this rule.
_BASIS_SCOPE_CATS = ("meat", "poultry", "fish")
_BASIS_OUT = re.compile(
    "شوربة|سلطة|curry|soup|salad|sushi|سوشى|سوشي|برياني|بريانى|biryani|مقلوبة|maqlobah|منسف|mansaf|هريس|harees|"
    "ماجى|maggi|مرق|broth|كراكرز|crackers|طحين|flour|سجق|sausage|sujuk|لانشون|luncheon|مرتديلا|مارتيديلا|mortadella|"
    "سلامي|سلامى|salami|بيبرونى|pepperoni|بسطرمة|basturma|برجر|burger|فسيخ|fesikh|ممبار|mombar|صالونة|salona|بانيه|"
    "fillet, breaded|بسمن|ghee|بالفلفل|حليب|milk|كعكة|cakes|نودلز|noodles|بلبن|pudding|رز معمر|معمول|صيادية|sayadieh", re.I)
_BASIS_COOKED = re.compile(
    "مطبوخ|مشوي|مشوى|مسلوق|مطهي|مطهى|محمر|مقلي|مقلى|بالفرن|مسحب|بخار|cooked|grill|roast|boil|fried|baked|steam|broil|stew", re.I)
_BASIS_PREPARED = (("canned", re.compile("معلب|canned", re.I)), ("smoked", re.compile("مدخن|smoked", re.I)),
                   ("cured", re.compile("مملح|salted|cured|مقدد|bacon", re.I)), ("dried", re.compile("مجفف|dried|jerky|قديد", re.I)))
# ready-to-eat products are weighed as sold; cooking does not change their weight. They are NOT "cooked".
_AS_SOLD = ("canned", "smoked", "cured", "dried")
# Candidate USDA matches (food_provenance.MATCHES) never qualify a row: a raw match withholds, a cooked
# candidate leaves a no-preparation row unresolved. There is no switch that simulates a review.
_BASIS_RAW = re.compile(r"نيئ|نئ|نيء|خام|\braw\b|طازج|fresh|uncooked", re.I)
from food_provenance import MATCHES as _PROV, verified as _prov_verified, QUARANTINE as _QUAR


def basis_of(food):
    """'cooked' | 'prepared' | 'raw' | 'unknown' | None (row outside the cooked-weight rule),
    from the row's own Arabic and English names. See the comment above."""
    n = (food.get("n") or "") + " " + (food.get("en") or "")
    cat = food.get("cat")
    is_rice = cat == "grain" and re.search("أرز|رز|rice", n, re.I)
    if not (cat in _BASIS_SCOPE_CATS or is_rice):
        return None
    if _BASIS_OUT.search(n):
        return None
    _m = _PROV.get(food.get("n"))
    if _m and _m[2] == "raw":
        return "raw"                    # USDA row of the same species and numbers is RAW: withhold
    if _BASIS_RAW.search(n):
        return "raw"
    if _BASIS_COOKED.search(n):
        return "cooked"
    for _lab, _rx in _BASIS_PREPARED:
        if _rx.search(n):
            return _lab
    return "unknown"


def _has_proposed_cooked_row(food):
    """With NX_PROPOSED_VARIANTS=1 a row that has a proposed USDA variant (kind variant or new_recipe,
    never a proxy) is replaced by that variant below; the variant row names its own cooked
    preparation and FDC id, so the basis of the library row does not decide the item."""
    if os.environ.get("NX_PROPOSED_VARIANTS") != "1":
        return False
    import meal_proposed
    pv = meal_proposed.PROPOSED.get(food.get("n"))
    return bool(pv) and pv.get("kind") in ("variant", "new_recipe") and basis_of_proposed(pv) == "cooked"


def basis_of_proposed(pv):
    d = (pv.get("usda") or pv.get("en") or "") + " " + (pv.get("name") or "")
    return "cooked" if re.search("cooked|roasted|baked|boiled|مطبوخ|مشوي|مسلوق", d, re.I) else "unknown"


def basis_unresolved(food):
    """Reason string when the row cannot stand for a cooked weight, else None."""
    if food.get("n") in _QUAR:
        return "identity:quarantined, " + _QUAR[food.get("n")]
    b = basis_of(food)
    if b is None or b == "cooked" or b in _AS_SOLD:
        return None
    if b == "raw" and food.get("family") and food.get("fdc") and _BASIS_RAW.search((food.get("n") or "") + " " + (food.get("en") or "")):
        # A named USDA variant whose OWN name says it is raw: the doctor chose it from the list, and the list says
        # "type the grams weighed raw". The weight basis is stated by the row itself, so it is counted. Library rows
        # whose raw state is only a guess from their numbers stay withheld (they have no "family").
        return None
    _m = _PROV.get(food.get("n"))
    if _m and b == "raw":
        return "basis:values match USDA raw row %s (%s)" % (_m[0], _m[1])
    if b == "unknown" and _m and _m[2] == "cooked":
        return "basis:candidate cooked match USDA %s (%s), not yet reviewed" % (_m[0], _m[1])
    return "basis:" + ("row is a raw-weight row" if b == "raw" else "row name states no preparation (cooked or raw unknown)")


def identity_gap(raw, food):
    """First word of the item that names something the matched table row does not
    (chicken in "كفتة دجاج" vs the row "كفتة مشوية", "حلوم" vs the row "جبن قريش"),
    or None. Such an item is not that row: the match is a guess at the head noun
    and its qualifier was dropped, so it must stay unverified, not computed."""
    nr = _strip_noise(_norm(raw))
    nr = re.sub(r"\([^)]*[A-Za-z][^)]*\)", " ", nr)          # "(Greek Yogurt Bowl"
    nr = re.sub(r"[A-Za-z][A-Za-z'\-]*", " ", nr)             # English words in titles
    nr = re.sub(r"\d+(?:[.,]\d+)?\s*(?:جم|جرام|غ|g|ml|kcal|مل(?![\u0600-\u06FF]))?", " ", nr)
    nf = _norm(food.get("n"))
    syn = (("دجاج", "فراخ", "فروج", "فرخه", "فرخة"),)
    allowed = set()
    for g, sp in GENERIC.items():
        if _norm(sp) == nf:
            allowed.update(_norm(g).split())
    for tok in re.split(r"[\s()+،,/-]+", nr):
        if len(tok) < 3:
            continue
        core = re.sub(r"^(?:بال|وال|لل|ال|ب|ل|و)(?=.{3,})", "", tok)
        if core in _HARMLESS or tok in _HARMLESS or core in allowed or tok in allowed:
            continue
        if core in nf or tok in nf:
            continue
        stems = {core[:-1] if core.endswith("ه") else core,
                 core[:-2] if core.endswith(("ات", "ين")) else core}
        if any(len(x) >= 3 and x in nf for x in stems):
            continue    # singular/plural, feminine ending (تفاحة / تفاح)
        if any(core in grp and any(w in nf for w in grp) for grp in syn):
            continue
        # report the word as written (the single-letter prefix strip is only for matching)
        return tok if tok.startswith(("ب", "ل", "و")) and len(tok) - len(core) == 1 else core
    return None


def _exact_identity(text, food):
    """The table row's own name is in the text (or the whole-egg alias)."""
    nf = _norm(food.get("n"))
    for clean in (_norm(text), _strip_noise(_norm(text))):
        if clean and _find_word(clean, nf) >= 0:
            return True
        if nf == _norm("بيضة كاملة") and re.search(r"(?:^|\s)(?:بيضه|بيضتين|بيضتان|بيضات|بيض)(?:$|\s)", clean) \
                and not re.search(_norm("ابيض|صفار|بياض"), clean):
            return True
    return False


def _ok_level(r, kinds):
    """Item is original-exact, or a PROPOSED item of an allowed kind with a stated or proposed quantity.
    Proxies (identity-mismatched stand-ins) are never in a source-matched level."""
    if r.get("exact_identity") and r.get("explicit_quantity"):
        return True
    if not r.get("proposed") or r.get("proposed_kind") not in kinds:
        return False
    return bool(r.get("explicit_quantity") or r.get("proposed_qty"))


def _flag_row(r):
    """Per-item flags (see macros()). Rows without a priced food get all False."""
    if r.get("proposed"):
        # proposed variant: stated quantity only if the text had one; never exact, never original
        r["explicit_quantity"] = bool(r.get("how") in ("grams", "count", "ml*density"))
        r["exact_identity"] = False
        r["sourced"] = True
        return
    food = None
    if r.get("food") and not r.get("unresolved"):
        food = next((f for _n, f in _table() if f.get("n") == r["food"]), None)
    r["explicit_quantity"] = bool(food) and r.get("how") in ("grams", "count", "ml*density")
    r["exact_identity"] = bool(food) and _exact_identity(r["text"], food)
    r["sourced"] = bool(food and (food.get("fdc") or _prov_verified(food)))


def macros(text):
    """‏ماكروز الوجبة كلها من أصنافها.

    ‏بترجّع ديكشنري: cal / p / c / f، ومعاهم items (كل صنف وتفاصيله)
    وcovered (نسبة الأصناف اللي اتعرفت).
    """
    items = []
    known = total = 0
    sums = {"cal": 0.0, "p": 0.0, "c": 0.0, "f": 0.0}
    for raw in str(text or "").split(" + "):
        raw = raw.strip()
        if not raw:
            continue
        total += 1
        food = find_food(raw)
        food_orig_name = food.get("n") if food else None
        grams, how = item_grams(raw, food)
        if food and _is_ml(raw) and food.get("cat") in _DRY_CATS \
                and "زيت" not in str(food.get("n")):
            # ‏"شوفان بحليب 200مل" طبق جاهز، مش ٢٠٠ جم شوفان خام.
            # الأمان إننا مانخمّنش: الصنف بيتعدّ "مش متعرّف" والوجبة
            # بترجع للرقم المكتوب.
            food, grams, how = None, 0.0, None
        row = {"text": raw, "grams": grams, "how": how,
               "food": food.get("n") if food else None}
        if (food and _norm("شوربة") in _norm(raw)
                and _norm("شوربة") not in _norm(food.get("n"))):
            # ‏"شوربة لسان عصفور" مش لسان بقري. الطبق مش في الجدول.
            row["unresolved"] = "dish"
            items.append(row)
            continue
        if food and any(_norm(w) in _norm(raw) and _norm(w) not in _norm(food.get("n"))
                        for w in ("فتة", "فته", "شاورما", "مندي", "مجبوس", "برياني", "كبسة", "كشري")):
            # a named dish (bread, rice, sauce...) is not the single food it
            # contains, e.g. "فتة حمص" is not boiled chickpeas, "شاورما دجاج"
            # is not grilled chicken breast. Dishes the table has under their
            # own name still match (the food name contains the dish word).
            row["unresolved"] = "dish"
            items.append(row)
            continue
        _ml_g = food and __import__("meal_food_sources").ML_G.get(food.get("n"))
        if food and how == "grams" and _is_ml(raw) and _ml_g:
            # household weight from the source (USDA: 1 US cup = 244 g)
            grams = grams * float(_ml_g)
            row["grams"] = round(grams, 1)
            row["how"] = "ml*density"
        # the food's OWN name may contain the word (حليب كامل الدسم "مع" فيتامين د): that is not a second food
        _own = (food or {}).get("n") or ""
        _rest = raw.replace(_own, " ") if _own and _own in raw else raw
        if food and (_norm("&") in _norm(_rest) or "veggies" in _rest.lower()
                     or " مع " in " " + _rest + " "
                     or any(w in _rest for w in ("بالخضار", "بالخضروات", "بالصينية", "بالفلافل"))):
            # a dish title naming more than the matched food (fish AND vegetables)
            row["unresolved"] = "composite"
            items.append(row)
            continue
        if (food and _norm("لبن لوز") in _norm(raw) + " " or
                food and _norm("حليب لوز") in _norm(raw) + " ") and not re.search(
                _norm("غير محلى|بدون سكر|unsweetened|sugar free"), _norm(raw)):
            # sweetened and unsweetened almond milk differ ~2.5x in kcal; the
            # text does not say which
            row["unresolved"] = "variant:sweetened or unsweetened not stated"
            items.append(row)
            continue
        if food and os.environ.get("NX_IDENTITY_STRICT", "1") != "0":
            _gap = identity_gap(raw, food)
            if _gap and os.environ.get("NX_PROPOSED_VARIANTS") == "1":
                import meal_proposed
                _pv0 = meal_proposed.PROPOSED.get(food.get("n"))
                if _pv0 and _pv0.get("overrides_identity") and _norm(_pv0["only_if"]) in _norm(raw):
                    _gap = None             # proposed proxy for this exact phrase (flagged proposed below)
            if _gap:
                row["unresolved"] = "identity:" + _gap
                items.append(row)
                continue
        if food:
            _nr, _nf = _norm(raw), _norm(food.get("n"))
            _q = [w for w in QUALIFIERS if _norm(w) in _nr and _norm(w) not in _nf]
            if _q:
                # ‏الجدول مافيهوش الصنف المحدّد ده (شيدر مش قريش، مقلي مش مسلوق،
                # كامل الدسم مش قليل الدسم): الأقرب مش مرجع، فالصنف غير محسوم.
                row["unresolved"] = "qualifier:" + _q[0]
                items.append(row)
                continue
        if (food and os.environ.get("NX_BASIS_STRICT", "1") != "0" and basis_unresolved(food)
                and not (basis_of(food) == "raw" and _BASIS_RAW.search(raw))
                and not _has_proposed_cooked_row(food)):
            # Design rule: weights written in the table mean AFTER cooking (the user's instruction, 27 Nov 2026; a code comment is not evidence of it).
            # This row's values equal a USDA RAW row and its name states no preparation,
            # so it is not a cooked-weight row. Resemblance, not proof: either way it is
            # not exact, and the total shows it as unresolved.
            row["unresolved"] = basis_unresolved(food)
            items.append(row)
            continue
        if (food and how == "count"
                and food.get("n") in AMBIGUOUS_COUNT
                and not _named_unit(_norm(raw), food)
                and not _UNIT_WORD.search(_norm(raw))):
            # ‏"خبز 2": رغيف ولا شريحة؟ الجدول مافيهوش وزن معتمد،
            # فمانخمّنش. الصنف بيتعدّ "غير محسوم" والحساب ناقص ظاهر.
            row["unresolved"] = "unit"
            items.append(row)
            continue
        if food:
            _nr, _nf = _norm(raw), _norm(food.get("n"))
            _raw_word = re.search(r"(?:^|\s)(?:نيء|نيه|ني|نيئه|نيئة|خام|جاف|جافه|جافة|ناشف)(?:$|\s)", _nr)
            _cooked_food = re.search(r"مطبوخ|مسلوق|مشوي|مشوى", _nf)
            if _raw_word and _cooked_food:
                # raw weight is not cooked weight (rice 365 vs 130 kcal/100 g).
                # The table has no raw row for this food: do not reuse the cooked one.
                row["unresolved"] = "raw/cooked"
                items.append(row)
                continue
            if _nf == _norm("سمك بلطي") and _norm("بلطي") not in _nr and re.search(
                    _norm("سمك") + r"\s+(?!\d)\S+", _nr) and not re.search(_norm("سمك") + r"\s+(?:مشوي|مسلوق|مقلي|بالفرن|مشوى)\b", _nr):
                # "سمك X" names a species the table does not have
                row["unresolved"] = "variant:fish species"
                items.append(row)
                continue
            if "سكر" in _nr and "بدون سكر" not in _nr and "بدون سكر" in _nf:
                row["unresolved"] = "variant:sugar added, table row is unsweetened"
                items.append(row)
                continue
            if (_nf == _norm("لبن رايب") and re.search(_norm("حليب|لبن") + "", _nr)
                    and not re.search(_norm("رايب|زبادي"), _nr)
                    and not re.search(_norm("خالي|كامل"), _nr)):
                # plain milk with no fat level: the table has no single milk row for it
                row["unresolved"] = "variant:milk fat level not stated"
                items.append(row)
                continue
            if how == "default" and _UNIT_WORD.search(_nr):
                _uw = _UNIT_WORD.search(_nr).group(0)
                _du = _default_unit_name(_nr, food)
                if _du and _norm(_uw) not in _norm(_du) and not re.search(r"\d", _nr):
                    # the item states a unit (slice/loaf/spoon...) that is not the unit
                    # the default weight belongs to
                    row["unresolved"] = "unit"
                    items.append(row)
                    continue
        if food and not row.get("unresolved") and os.environ.get("NX_PROPOSED_VARIANTS") == "1":
            # PROPOSED review layer (off by default): a bridged generic phrase is priced from ONE
            # chosen USDA variant, and a missing quantity from the USDA household portion. Neither
            # is the doctor's original text or a verified value: flagged proposed, never exact.
            import meal_proposed
            _pv = meal_proposed.PROPOSED.get(food.get("n"))
            if _pv and _pv.get("only_if") and _norm(_pv["only_if"]) not in _norm(raw):
                _pv = None                          # e.g. mixed nuts only for "مكسرات", not plain almonds
            if _pv and (not _exact_identity(raw, food) or how in (None, "default") or basis_unresolved(food)):
                # basis_unresolved: an explicit amount of a row with no stated preparation is still
                # swapped to the named cooked variant, never kept as the original
                food = _pv
                row["food"] = _pv["n"]
                row["proposed"] = True
                row["proposed_kind"] = _pv.get("kind", "variant")   # variant | proxy | new_recipe
                row["original_food"] = food_orig_name
                if how in (None, "default") or not grams:
                    grams, how = float(_pv["default_g"]), "proposed_default"
                    row["proposed_qty"] = True
                row["grams"], row["how"] = round(grams, 1), how
        if food and grams > 0:
            known += 1
            share = grams / 100.0
            for key, field in (("cal", "cal"), ("p", "p"), ("c", "c"),
                               ("f", "f")):
                try:
                    sums[key] += float(food.get(field) or 0) * share
                except (TypeError, ValueError):
                    pass
            row["cal"] = round(float(food.get("cal") or 0) * share)
        items.append(row)
    unresolved = [r["text"] for r in items
                  if r.get("unresolved") or not (r.get("food") and r.get("grams", 0) > 0)]
    for r in items:
        _flag_row(r)
    # three independent facts, never one flag:
    #   explicit_quantity: the text states the amount (grams / count / ml)
    #   exact_identity:    the table row's own name is in the text, not a generic bridge
    #                      ("جبنة" -> cottage cheese, "لحم" -> lean beef, "لبن" -> laban rayeb)
    #   sourced:           the row is a USDA-sourced row (has an fdc id), not an unsourced
    #                      library row
    # "complete" = every item is priced from some table row. "exact" = priced AND
    # explicit AND exact identity: the only case that counts as calculated from the
    # actual meal. Even then it is a table calculation, not source-verified unless
    # every item is also sourced ("all_sourced").
    _priced = bool(items) and not unresolved
    return {
        # only with NX_PROPOSED_VARIANTS=1: every item is either original-exact or a PROPOSED variant
        # with a stated or USDA-household quantity. A proposal is not the original meal.
        "exact_if_proposed": _priced and all(_ok_level(r, ("variant",)) for r in items),
        "exact_if_proposed_recipe": _priced and all(_ok_level(r, ("variant", "new_recipe")) for r in items),
        "has_proxy": any(r.get("proposed_kind") == "proxy" for r in items),
        "has_new_recipe": any(r.get("proposed_kind") == "new_recipe" for r in items),
        "has_proposed": any(r.get("proposed") for r in items),
        "exact": _priced and all(r.get("explicit_quantity") and r.get("exact_identity") for r in items),
        "all_sourced": _priced and all(r.get("sourced") for r in items),
        "complete": bool(items) and not unresolved,
        "unresolved": unresolved,
        "cal": int(round(sums["cal"])),
        "p": int(round(sums["p"])),
        "c": int(round(sums["c"])),
        "f": int(round(sums["f"])),
        "items": items,
        "covered": (known / float(total)) if total else 0.0,
    }




def trusted(text, stored_cal, stored_p=None):
    """‏الماكروز لو الحساب اتفق مع الرقم المكتوب، وإلا None.

    ‏الرقم المكتوب بإيد الدكتور هو المرجع. المحسوب بيتصدّق لما يبقى
    قريب منه -- وساعتها الكارب والدهون المحسوبين ينفعوا يتكتبوا.
    """
    out = macros(text)
    # an item that is unresolved (unknown food, unstated unit, named variant the
    # table lacks) means the computed total is incomplete: never trust it
    if out["covered"] < 0.6 or not stored_cal or out["unresolved"]:
        return None
    try:
        reference = float(stored_cal)
    except (TypeError, ValueError):
        return None
    if reference <= 0:
        return None
    if abs(out["cal"] - reference) / reference > TOLERANCE:
        return None
    return out

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
        rows = []
        # source-backed extras go AFTER the main table: a name already in the
        # main table keeps winning, so nothing existing changes.
        have = {_norm(f.get("n")) for f in food_data.FOODS}
        for food in list(food_data.FOODS) + [
                f for f in meal_food_sources.SOURCED_FOODS
                if _norm(f["n"]) not in have]:
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
        if food and (_norm("&") in _norm(raw) or "veggies" in raw.lower()
                     or " مع " in " " + raw + " "
                     or any(w in raw for w in ("بالخضار", "بالخضروات", "بالصينية", "بالفلافل"))):
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
        if food:
            _nr, _nf = _norm(raw), _norm(food.get("n"))
            _q = [w for w in QUALIFIERS if _norm(w) in _nr and _norm(w) not in _nf]
            if _q:
                # ‏الجدول مافيهوش الصنف المحدّد ده (شيدر مش قريش، مقلي مش مسلوق،
                # كامل الدسم مش قليل الدسم): الأقرب مش مرجع، فالصنف غير محسوم.
                row["unresolved"] = "qualifier:" + _q[0]
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
    return {
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

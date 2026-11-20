# -*- coding: utf-8 -*-
"""تكبير وتصغير حصص الوجبة عشان اليوم يوصل هدفه.

المشكلة اللي الملف ده بيحلها: وجبات قاعدة البيانات حصصها **ثابتة** لكل هدف
(فطار التخسيس ٣٠٠ سعر، فطار التضخيم ٨٦٠)، وهدف العميل رقم متغيّر بيتحسب من
وزنه وطوله وسنه ونشاطه. الخطة كانت بتجمع الوجبات وتحط المجموع جنب الهدف،
والرقمين مش نفس الرقم. القياس على كل هدف × كل نظام:

    تقليدي:        -١٤٪ لـ -٣٠٪
    خمس وجبات:     -١٤٪ لـ -٢٥٪
    وجبتين:        -٤٤٪ لـ -٥٢٪
    صيام ١٦/٨:     -٤٨٪ لـ -٥٦٪

الأنظمة اللي وجباتها أقل هي الأسوأ، والسبب واضح: بتشيل وجبة وتسيب حصص
الباقي زي ما هي. يعني مريض على نظام وجبتين كان بياخد نص سعراته.

الحل إن الحصص تتضرب في معامل = الهدف ÷ المجموع. الجرامات بتتقرّب لأرقام
يقدر يوزنها (أقرب ٥ أو ١٠)، والحاجات اللي بالعدد (بيض، تمر، فاكهة) لأقرب
واحدة صحيحة. والمعامل الفعلي بيترجّع عشان السعرات المكتوبة تبقى السعرات
اللي في الطبق فعلاً بعد التقريب، مش اللي كنا عايزينها.

بعض الحاجات مابتتغيّرش: القرفة والشاي والليمون والملح والبهارات -- سعراتها
صفر تقريباً، وتكبيرها بيخلي النص سخيف من غير فايدة.
"""

import re

# ‏وحدات الوزن اللي بتتقاس: دي اللي فيها السعرات
_WEIGHT_RX = re.compile(r"(\d+(?:\.\d+)?)\s*(جم|جرام|مل|g|ml)\b")

# ‏حاجات بالعدد: "بيض مسلوق 2"، "تمر 3"، "تفاح 1"
_COUNTABLE = ("بيض", "بيضة", "بياض", "تمر", "بلح", "موز", "موزة", "تفاح",
              "كمثرى", "برتقال", "زيتون", "توست", "رقاق", "عيش", "خبز عربي",
              "ثمرة", "ثمرات", "حبة", "حبات", "شريحة", "شرائح", "قطعة",
              "قطع", "طعمية", "كبة", "سمبوسة")

# ‏سقف العدد في الوجبة الواحدة.
#
# ‏المعامل بيضرب العدد زي ما بيضرب الجرامات، والعدد مالوش سقف -- فوجبة
# أساسها "بيض مسلوق ٣" على يوم ٢٥٠٠ سعرة طلعت **"بيض مسلوق ٧"** على
# ورقة بنت عندها ١٦ سنة. ده مش حصة أكبر، ده صنف تاني: سبع بيضات في
# وجبة واحدة حوالي ١٣٠٠ مجم كوليسترول ومحدش بياكلها.
#
# ‏والجرامات مالهاش نفس المشكلة: ٢٠٠جم أرز بتبقى ٣٠٠جم وتفضل أرز.
# العدد هو اللي بيوصل لحد السخافة بسرعة، فبنوقف عنده ونسيب باقي
# المعامل للأصناف التانية في نفس الوجبة.
COUNT_MAX = (
    ("بياض", 6),       # ‏بياض البيض من غير الصفار -- سقفه أعلى
    ("بيض", 4),
    ("بيضة", 4),
    ("موز", 3),
    ("تمر", 7),
    ("بلح", 7),
    ("توست", 6),
    ("رقاق", 6),
)


# ‏سعراتها صفر تقريباً، فتكبيرها مالوش معنى
_NO_SCALE = ("قرفة", "شاي", "قهوة", "ماء", "ليمون", "ملح", "بهارات", "زعتر",
             "نعناع", "كمون", "كركم", "زنجبيل", "خل", "فلفل", "شطة", "ثوم",
             "بصل", "خيار", "خس", "جرجير", "سلطة", "طماطم", "بقدونس")

# ‏الملاعق بتفضل أرقام صحيحة: "٠.٧٥ ملعقة" مش تعليمة يقدر ينفّذها
_SPOON_RX = re.compile(r"(\d+(?:\.\d+)?)\s*(ملعقة|ملاعق|كوب|كوباية)\b")

# ‏سعرات السناك مكتوبة جنبه، وبشكلين في القاعدة: "(80 kcal)" و"- 80
# kcal". النسخة الأولى كانت بتمسك الأقواس بس، فسناك بشرطة كان بيتكبّر
# والرقم جنبه مايتحركش: "تفاحة 290جم - 80 سعرة" على ورقة عميل
# (التفاحة دي ١٥٠ سعرة). وده **كل** سناكات القاعدة القديمة -- كلها
# بشرطة.
_KCAL_ANY = re.compile(
    r"\(\s*\d+(?:\.\d+)?\s*kcal\s*\)|[-\u2013\u2014]\s*\d+(?:\.\d+)?\s*kcal")
_KCAL_PAREN = re.compile(r"\(\s*(\d+(?:\.\d+)?)\s*kcal\s*\)")
_KCAL_DASH = re.compile(r"([-\u2013\u2014])\s*(\d+(?:\.\d+)?)\s*kcal")

MIN_FACTOR = 0.5
MAX_FACTOR = 3.0


def _round_grams(value):
    """‏رقم يقدر يوزنه: أقرب ٥ تحت الـ٥٠، وأقرب ١٠ فوقها."""
    if value <= 0:
        return 0
    if value < 50:
        return max(5, int(round(value / 5.0) * 5))
    return int(round(value / 10.0) * 10)


def _count_ceiling(segment):
    """‏أعلى عدد مسموح للصنف ده في وجبة واحدة، أو None لو مفيش سقف.

    ‏الكلمة بتتقاس ككلمة مش كحروف: "أرز أبيض" جواها "بيض"، و"توست
    أبيض" كمان -- فالمطابقة الساذجة كانت بتحط عليهم سقف البيض.
    """
    for word, cap in COUNT_MAX:
        if re.search(r"(^|\s)" + re.escape(word) + r"(\s|$|[،,.)])", segment):
            return cap
    return None


def _is_free(segment):
    """‏الصنف اللي سعراته صفر تقريباً.

    الكلمة لازم تتقاس ككلمة مش كحروف: "شوفان بالماء" فيها "ماء" جوه
    "بالماء"، والشوفان هو سعرات الوجبة كلها -- فالمطابقة الساذجة كانت
    بتسيبه من غير تكبير.
    """
    for word in _NO_SCALE:
        if re.search(r"(^|\s)" + re.escape(word) + r"(\s|$|[،,.])", segment):
            return True
    return False


def _scale_segment(segment, factor):
    """‏يرجّع (النص الجديد، القيمة الأصلية، القيمة الجديدة).

    الترتيب مهم وكل فرع بيمنع اللي بعده: "زيت زيتون 1 ملعقة صغيرة" فيها
    "زيتون" اللي في قايمة الحاجات بالعدد، فكانت بتتضرب مرتين -- مرة كعدد
    ومرة كملعقة -- و×٢ طلعت ٤.
    """
    if _is_free(segment):
        return segment, 0.0, 0.0

    before = [0.0]
    after = [0.0]

    def weight(match):
        original = float(match.group(1))
        unit = match.group(2)
        scaled = _round_grams(original * factor)
        before[0] += original
        after[0] += scaled
        return f"{scaled}{unit}" if unit in ("جم", "مل") else f"{scaled} {unit}"

    out = _WEIGHT_RX.sub(weight, segment)
    if before[0] > 0:
        return out, before[0], after[0]

    def spoon(match):
        original = float(match.group(1))
        scaled = max(1, int(round(original * factor)))
        before[0] += original
        after[0] += scaled
        return f"{scaled} {match.group(2)}"

    out = _SPOON_RX.sub(spoon, out)
    if before[0] > 0:
        return out, before[0], after[0]

    if any(word in segment for word in _COUNTABLE):
        ceiling = _count_ceiling(segment)

        def count(match):
            original = float(match.group(1))
            scaled = max(1, int(round(original * factor)))
            if ceiling:
                # ‏السقف مايقلّش عن الحصة الأصلية: لو الوجبة أصلاً فيها
                # أكتر من السقف، ده اختيار اتكتب في القاعدة -- إحنا
                # بنمنع التكبير مش بنعدّل على الوجبة.
                scaled = min(scaled, max(ceiling, int(original)))
            before[0] += original
            after[0] += scaled
            return str(scaled)

        out = re.sub(r"(?<![\d.])(\d+(?:\.\d+)?)(?![\d.])", count, out, count=1)
    return out, before[0], after[0]


def scale_meal(text, factor):
    """‏يكبّر أو يصغّر حصص وجبة. يرجّع (النص، المعامل الفعلي).

    المعامل الفعلي مش اللي دخل: التقريب بيغيّره. "١٥٠جم × ١.٣" = ١٩٥ وبتتقرّب
    لـ٢٠٠، فالفعلي ١.٣٣. السعرات بتتحسب بالفعلي عشان الرقم المكتوب يكون رقم
    الطبق مش رقم النية.
    """
    if not text or not isinstance(text, str):
        return text, 1.0
    factor = max(MIN_FACTOR, min(MAX_FACTOR, float(factor or 1.0)))
    if abs(factor - 1.0) < 0.02:
        return text, 1.0

    tail = ""
    match = _KCAL_ANY.search(text)
    if match:
        tail = text[match.start():]
        text = text[:match.start()]

    total_before = 0.0
    total_after = 0.0
    parts = []
    for segment in text.split(" + "):
        new_segment, before, after = _scale_segment(segment, factor)
        parts.append(new_segment)
        total_before += before
        total_after += after

    effective = (total_after / total_before) if total_before > 0 else 1.0
    out = " + ".join(parts)

    if tail:
        # ‏السناك مكتوب جنبه سعراته، فلازم تتحرك مع الحصة. والشكل
        # زي ما هو: الأقواس تفضل أقواس والشرطة تفضل شرطة.
        def _paren(match):
            return "(%d kcal)" % int(round(float(match.group(1)) * effective))

        def _dash(match):
            return "%s %d kcal" % (match.group(1),
                                   int(round(float(match.group(2))
                                             * effective)))
        out += _KCAL_DASH.sub(_dash, _KCAL_PAREN.sub(_paren, tail))
    return out.strip(), effective


# ── التحكم بالإيد في كمية صنف واحد ─────────────────────────────────
#
# ‏كل اللي فوق ده بيكبّر الوجبة كلها بمعامل. ده العكس: الدكتور بيبص على
# الوجبة الجاهزة ويقول "الجبنة كتير" -- فبيتغيّر رقم الجبنة لوحده، وباقي
# السطر بالحرف زي ما هو. قبل كده كان لازم يفتح النص كله ويكتب الرقم بإيده،
# وأي غلطة كتابة بتبوّظ صنف تاني في نفس السطر.
#
# ‏سقف العدد (COUNT_MAX) مش بيتطبّق هنا: السقف ده اتعمل عشان المعامل
# الأوتوماتيك هو اللي طلّع "بيض ٧"، مش الدكتور. هنا الدكتور هو اللي بيقرّر،
# ومجموع اليوم والتحذير الطبي بيتحدّثوا قدّامه مع كل ضغطة.

_BARE_NUMBER = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)(?![\d.])")


def _split_tail(text):
    match = _KCAL_ANY.search(text)
    if not match:
        return text, ""
    return text[:match.start()], text[match.start():]


def _quantity(segment):
    """‏(بداية الرقم، نهايته، القيمة، الوحدة، بداية الكمية بوحدتها، نهايتها)
    لأول كمية في الصنف، أو None.

    ‏نفس ترتيب _scale_segment: وزن، بعدين ملعقة، بعدين عدد. "زيت زيتون 1
    ملعقة" لو اتقرت عدد الأول كانت هتبقى "زيتون" مش ملعقة.
    """
    for rx in (_WEIGHT_RX, _SPOON_RX):
        m = rx.search(segment)
        if m:
            return (m.start(1), m.end(1), float(m.group(1)), m.group(2),
                    m.start(), m.end())
    m = _BARE_NUMBER.search(segment)
    if m:
        return m.start(1), m.end(1), float(m.group(1)), "", m.start(1), m.end(1)
    return None


def _is_weight(unit):
    return unit in ("جم", "جرام", "مل", "g", "ml")


def _step(value, unit, direction):
    """‏خطوة يقدر يوزنها: ٥ جم لحد الـ٥٠، و١٠ فوقها. العدد والملاعق واحدة."""
    if not _is_weight(unit):
        return 1
    if direction > 0:
        return 5 if value < 50 else 10
    return 5 if value <= 50 else 10


def _floor(unit):
    return 5 if _is_weight(unit) else 1


def _fmt(value):
    return str(int(value)) if float(value).is_integer() else ("%g" % value)


def _item_cal(segment):
    """‏سعرات الصنف لوحده، أو None لو جدول الأكل مايعرفوش.

    ‏None مش صفر: "طعمية" مش في الجدول، وكتابة "٠ سعرة" جنبها كانت
    هتقول إنها مابتتحسبش، وهي بتتحسب -- إحنا اللي مانعرفهاش.
    """
    import meal_macros
    rows = meal_macros.macros(segment)["items"]
    return rows[0].get("cal") if rows and rows[0].get("food") and rows[0].get("grams") else None


def meal_items(text):
    """‏أصناف الوجبة، بترتيبها في النص.

    ‏كل صنف في الوجبة ليه عنصر، واللي من غير رقم qty بتاعه None.
    ‏كل عنصر: index (رقم الصنف في النص بعد التقسيم على " + ")، text، name
    (الصنف من غير الكمية، عشان الرقم يتكتب لوحده جنب الزراير)، qty، unit
    ("" للعدد)، وcan_down (لو النزول خطوة كمان لسه فوق الحد الأدنى).
    """
    if not text or not isinstance(text, str):
        return []
    body, _ = _split_tail(text)
    out = []
    for index, segment in enumerate(body.split(" + ")):
        if not segment.strip():
            continue
        q = _quantity(segment)
        if not q:
            # ‏صنف من غير رقم ("خضار طازة"): مالوش ناقص وزايد، بس ليه شريحة
            # عشان ينفع يتشال -- صاحب المشروع عايز يحذف أي نوع أكل.
            out.append({"index": index, "text": segment.strip(),
                        "name": segment.strip(), "qty": None, "unit": "",
                        "can_down": False, "cal": _item_cal(segment)})
            continue
        value, unit = q[2], q[3]
        name = re.sub(r"\s+", " ", segment[:q[4]] + segment[q[5]:]).strip()
        out.append({
            "index": index, "text": segment.strip(), "name": name,
            "cal": _item_cal(segment),
            "qty": int(value) if value.is_integer() else value, "unit": unit,
            "can_down": value - _step(value, unit, -1) >= _floor(unit),
        })
    return out


def nudge_item(text, index, direction):
    """‏يزوّد (direction > 0) أو ينقّص خطوة واحدة في صنف واحد.

    ‏يرجّع النص الجديد، أو None لو الصنف مالوش كمية، أو الرقم غلط، أو
    النزول هيوصّل تحت الحد الأدنى. مفيش نزول لصفر: الصنف اللي عايز يتشال
    بيتشال بالتعديل العادي، مش بـ"صفر جم" مكتوبة على ورقة العميل.
    """
    if not text or not isinstance(text, str) or not direction:
        return None
    body, tail = _split_tail(text)
    segments = body.split(" + ")
    if not (0 <= index < len(segments)):
        return None
    q = _quantity(segments[index])
    if not q:
        return None
    start, end, value, unit = q[:4]
    sign = 1 if direction > 0 else -1
    new = value + sign * _step(value, unit, sign)
    if new < _floor(unit):
        return None
    return _with_qty(segments, tail, index, new)


def _with_qty(segments, tail, index, new):
    """‏يكتب الرقم الجديد في الصنف، ويحرّك سعرات السناك المكتوبة معاه."""
    start, end, value = _quantity(segments[index])[:3]
    seg = segments[index]
    segments[index] = seg[:start] + _fmt(new) + seg[end:]

    if tail:
        # ‏سعرات السناك المكتوبة جنبه لازم تتحرك مع الحصة. لو فيه أكتر من
        # صنف بكمية، النسبة بتاعة صنف واحد مش نسبة الوجبة، فبنسيبها.
        quantified = [s for s in segments if _quantity(s)]
        if len(quantified) == 1:
            ratio = new / value
            tail = _KCAL_PAREN.sub(
                lambda m: "(%d kcal)" % int(round(float(m.group(1)) * ratio)), tail)
            tail = _KCAL_DASH.sub(
                lambda m: "%s %d kcal" % (m.group(1),
                                          int(round(float(m.group(2)) * ratio))), tail)
    return " + ".join(segments) + tail


# ‏أقصى طول لصنف بيتكتب في خانة الإضافة. الورقة سطر لكل وجبة، وصنف أطول
# من كده غالباً حاجة اتلصقت غلط مش اسم أكل.
MAX_ITEM_LEN = 80


def remove_item(text, index):
    """‏يشيل صنف واحد من الوجبة. يرجّع النص الجديد ("" لو كان آخر صنف)،
    أو None لو الرقم غلط.

    ‏السعرات المكتوبة جنب السناك ("- 99 kcal") بتتشال: كانت بتوصف
    الوجبة قبل ما الصنف يتشال، وسيبها يبقى رقم غلط مكتوب على ورقة العميل.
    مجموع اليوم مابيعتمدش عليها -- بيتحسب من الأصناف.
    """
    if not isinstance(text, str):
        return None
    body, _ = _split_tail(text)
    segments = body.split(" + ")
    if not (0 <= index < len(segments)) or not segments[index].strip():
        return None
    del segments[index]
    return " + ".join(seg.strip() for seg in segments if seg.strip())


def add_item(text, item):
    """‏يضيف صنف في آخر الوجبة. يرجّع النص الجديد، أو None لو الصنف فاضي
    أو أطول من MAX_ITEM_LEN. السعرات المكتوبة بتتشال لنفس سبب remove_item.
    """
    item = re.sub(r"\s+", " ", str(item or "")).strip()
    if not item or len(item) > MAX_ITEM_LEN:
        return None
    body, _ = _split_tail(text or "")
    segments = [seg.strip() for seg in body.split(" + ") if seg.strip()]
    segments.append(item)
    return " + ".join(segments)


# ‏حدود الكمية اللي بتتكتب بالإيد. الهدف إنها تمسك غلطة كتابة (٥٠٠٠ بدل
# ٥٠٠)، مش إنها تقرّر حصة: مجموع اليوم والتحذير قدّام الدكتور.
MAX_WEIGHT = 2000
MAX_COUNT = 30
MAX_SPOONS = 20


def set_item_qty(text, index, value):
    """‏يكتب كمية الصنف زي ما الدكتور كتبها. يرجّع النص الجديد، أو None لو
    الكمية مش حاجة تتقدّم (صفر، نص بيضة، ٥ كيلو) أو الصنف مالوش رقم.

    ‏الصفر مرفوض بالقصد: الحذف ليه زرار ورسالة تأكيد، والخانة دي مش باب
    تاني يمسح من غير ما يسأل.
    """
    if not text or not isinstance(text, str):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    body, tail = _split_tail(text)
    segments = body.split(" + ")
    if not (0 <= index < len(segments)):
        return None
    q = _quantity(segments[index])
    if not q:
        return None
    unit = q[3]
    if _is_weight(unit):
        value = round(value)
        if not (_floor(unit) <= value <= MAX_WEIGHT):
            return None
    elif unit:
        # ‏ملعقة أو كوب: نص ملعقة تتنفّذ، تلت ملعقة لأ
        if value * 2 != int(value * 2) or not (0.5 <= value <= MAX_SPOONS):
            return None
    else:
        if value != int(value) or not (1 <= value <= MAX_COUNT):
            return None
    if value == q[2]:
        return text
    return _with_qty(segments, tail, index, value)

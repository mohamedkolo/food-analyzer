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

# -*- coding: utf-8 -*-
"""‏يطلّع الرقم الضايع من أرقام الورقة نفسها، بالمعادلات اللي بتربطهم.

ليه موجود
─────────
‏ورقة تحليل الجسم أرقامها **مش مستقلة**: الـBMI هو الوزن على مربع الطول،
وكتلة الدهون هي الوزن في نسبتها، وماء الجسم نسبة ثابتة تقريباً من الكتلة
الخالية. فلو القراية شافت الوزن والطول صح وضيّعت الـBMI، الـBMI مش
محتاج تخمين -- محتاج حساب، وبعدين **تأكيد** إن الرقم المحسوب موجود
مطبوع على الورقة فعلاً.

‏والفرق بين ده وبين التخمين فرق جوهري، وهو كل حاجة في الملف:

    تخمين   =  الـBMI مش مقروء، يبقى نحسبه ونحطه
    اللي هنا =  نحسبه، ندوّر على رقم مطبوع على الورقة قريب منه، ولو
                لقينا **واحد بس** نحطه. أكتر من واحد أو ولا واحد = فاضي

‏الشرط التاني (واحد بس) هو الحاجز. ورقة الـInBody فيها ١٠٠+ رقم بين
الرسومات والمعايير والأعمدة، فلو قبلنا أول رقم قريب كنا بنفتح باب لرقم
من مسطرة رسم. الوحدانية بتقفل الباب ده: رقمين قريبين = مانعرفش = فاضي.

‏اللي اتقاس على ورق حقيقي
──────────────────────────
‏ورقة GAIA: القراية شافت الوزن ٦٧.٣ والطول ١٦٢ صح، والـBMI قرأته ١٤٥٠
(رقم من مسطرة الرسم). الحساب بيطلّع ٢٥.٦٤، وفي الورقة كلها **رقم واحد**
في حدود ٠.٢ منه: ٢٥.٦ -- وهو الرقم المطبوع بالظبط.

‏ورقة X-CONTACT: الحساب بيطلّع ٢٥.٢٥، ومافيش ولا رقم في الورقة قريب منه
(القراية ضيّعت ٢٥.٢ خالص). فالنتيجة فاضي، مش ٢٥.٢٥ محسوب. ده المقصود.

‏ورقة DR.NUTRITION بتاعة الدكتور: الملف ده مابيساعدش فيها، ولازم يتقال
بصراحة. أرقامها المهمة مطبوعة بخط رقيق فوق أعمدة الرسم، والقراية
مابتطلّعش منها لا عنوان ولا رقم صح -- يعني مافيش نقطة بداية تتبنى عليها
معادلة. دي مشكلة في **قراءة الصورة** مش في تفسير الأرقام، وحلّها محتاج
الصورة الأصلية.
"""

import re

# ‏الحدود نفسها اللي في lab_report.SANE_RANGES. الاستيراد بيتعمل متأخر
# عشان مافيش استيراد متبادل، والقايمة دي بس للخانات اللي الملف بيشتغل
# عليها.
_RANGES = {
    "weight": (20.0, 400.0),
    "height": (80.0, 250.0),
    "bmi": (8.0, 90.0),
    "fat_pct": (3.0, 75.0),
    "fat_mass": (1.0, 200.0),
    "bmr": (600.0, 4500.0),
    "body_water": (10.0, 90.0),
    "muscle_mass": (10.0, 120.0),
}

# ‏رقم على الورقة. (?<![\d.]) بتمنع قطع رقم من نص رقم أطول ("2.35-2.87"
# مش بتطلّع ٣٥)، و(?![\d]) بتمنع نفس الحاجة من الناحية التانية.
_NUMBER = re.compile(r"(?<![\d.])(\d{1,4}(?:[.,]\d{1,2})?)(?![\d])")

# ‏مياه الجسم نسبة من الكتلة الخالية من الدهون، مش من الوزن. النسبة دي
# ثابت فسيولوجي معروف (~٠.٧٣ من الكتلة الخالية)، والمدى هنا واسع عشان
# الأجهزة بتقيسها بطرق مختلفة.
TBW_LOW, TBW_HIGH = 0.64, 0.80

# ‏معادلة Katch-McArdle للأيض الأساسي من الكتلة الخالية. بتتستخدم هنا
# **للتأكيد بس**: الأجهزة بتطلّع أرقام أقل منها بـ٧-١٥٪ (قِسْتها على
# التلات ورقات: ٨٦.٦٪ و٩٣.٤٪ و٩٩.٩٪)، فالمدى واسع بالقصد.
BMR_LOW, BMR_HIGH = 0.70, 1.35


def numbers_in(lines):
    """‏كل رقم مطبوع على الورقة، من غير تكرار."""
    pool = set()
    for line in lines or []:
        for match in _NUMBER.finditer(str(line).replace(",", ".")):
            try:
                pool.add(float(match.group(1)))
            except ValueError:
                continue
    return pool


def _in_range(field, value):
    low, high = _RANGES.get(field, (None, None))
    if low is None or not isinstance(value, (int, float)):
        return False
    return low <= float(value) <= high


def _known(found, field):
    """‏الرقم المقروء للخانة دي لو كان جوّه المعقول، وإلا None.

    ‏الرقم برّه المعقول = قراءة غلط، فبنتعامل مع الخانة كأنها فاضية
    وندوّر على الصح. ورقة GAIA قرأت الـBMI ١٤٥٠ من مسطرة رسم، ولو
    اعتبرناها "مقروءة" كان الرقم الصح المطبوع (٢٥.٦) مش هيلاقي مكان.
    """
    value = found.get(field)
    return float(value) if _in_range(field, value) else None


def _only(pool, target, tol, field):
    """‏الرقم الوحيد في الورقة اللي في حدود tol من المحسوب، وإلا None.

    ‏الوحدانية هي الحاجز كله. رقمين قريبين معناهم إننا مش عارفين، ومش
    عارفين = الخانة تفضل فاضية والدكتور يكتبها.
    """
    near = [n for n in pool
            if _in_range(field, n) and abs(n - target) <= tol]
    # ‏أرقام متطابقة بعد التقريب (٢٥.٦ و٢٥.٦٠) رقم واحد، مش اتنين
    unique = sorted(set(round(n, 2) for n in near))
    return unique[0] if len(unique) == 1 else None


def _only_in_band(pool, low, high, field):
    """‏الرقم الوحيد في مدى. للخانات اللي معادلتها تقديرية مش محدّدة."""
    near = [n for n in pool if _in_range(field, n) and low <= n <= high]
    unique = sorted(set(round(n, 2) for n in near))
    return unique[0] if len(unique) == 1 else None


def reconcile(found, lines):
    """‏يرجّع الخانات اللي المعادلات أكّدتها، ومنين اتأكّدت.

    ‏مابيلمسش خانة مقروءة وجوّه المعقول -- بيزوّد الفاضي بس. الخانة
    المقروءة ليها فحوصها هي في lab_report._clean (تناسق الـBMI
    والـFFMI)، وهي اللي بتشيل الغلط. الملف ده بيضيف، مابيصححش.

    ‏بيرجّع: {"values": {خانة: رقم}, "why": {خانة: سبب}}
    """
    pool = numbers_in(lines)
    if not pool:
        return {"values": {}, "why": {}}

    values = {}
    why = {}

    def _take(field, value, reason):
        if value is None or field in values:
            return
        values[field] = value
        why[field] = reason

    weight = _known(found, "weight")
    height = _known(found, "height")
    bmi = _known(found, "bmi")
    fat_pct = _known(found, "fat_pct")
    fat_mass = _known(found, "fat_mass")

    # ── مثلث الوزن والطول والـBMI ──
    # ‏أي اتنين منهم بيحدّدوا التالت بالظبط، فالتالت مش تخمين -- حساب،
    # ومحتاج بس يتأكّد إنه مطبوع على الورقة.
    if weight and height and not bmi:
        _take("bmi", _only(pool, weight / ((height / 100.0) ** 2), 0.2, "bmi"),
              "weight_height")
    elif weight and bmi and not height:
        # ‏الطول من الوزن والـBMI. التفاوت أوسع (٠.٦ سم) لأن الـBMI
        # المطبوع مقرّب لخانة عشرية واحدة، والتقريب ده لوحده يحرّك
        # الطول المحسوب نص سنتيمتر.
        if bmi > 0:
            _take("height", _only(pool, ((weight / bmi) ** 0.5) * 100.0, 0.6,
                                  "height"), "weight_bmi")
    elif height and bmi and not weight:
        _take("weight", _only(pool, bmi * ((height / 100.0) ** 2), 0.3,
                              "weight"), "height_bmi")

    bmi = bmi or values.get("bmi")
    weight = weight or values.get("weight")
    height = height or values.get("height")

    # ── الدهون: الكتلة = الوزن × النسبة ──
    if weight and fat_pct and not fat_mass:
        _take("fat_mass", _only(pool, weight * fat_pct / 100.0, 0.3,
                                "fat_mass"), "weight_fatpct")
    elif weight and fat_mass and not fat_pct:
        # ‏النسبة من الكتلة موجودة أصلاً في ocr_report.interpret وبتتحسب
        # هناك. هنا بس بنتأكّد إن الرقم المحسوب مطبوع، ولو مش مطبوع
        # مابنلغيش الحساب -- هو صح رياضياً.
        _take("fat_pct", _only(pool, fat_mass / weight * 100.0, 0.2,
                               "fat_pct"), "weight_fatmass")

    fat_mass = fat_mass or values.get("fat_mass")
    fat_pct = fat_pct or values.get("fat_pct")

    # ── الكتلة الخالية من الدهون: منها الماء والأيض ──
    lean = None
    if weight and fat_mass and 0 < fat_mass < weight:
        lean = weight - fat_mass
    elif weight and fat_pct:
        lean = weight * (1.0 - fat_pct / 100.0)

    if lean and lean > 0:
        if _known(found, "body_water") is None:
            _take("body_water",
                  _only_in_band(pool, lean * TBW_LOW, lean * TBW_HIGH,
                                "body_water"), "lean_water")
        if _known(found, "bmr") is None:
            katch = 370.0 + 21.6 * lean
            _take("bmr", _only_in_band(pool, katch * BMR_LOW, katch * BMR_HIGH,
                                       "bmr"), "lean_bmr")

    return {"values": values, "why": why}

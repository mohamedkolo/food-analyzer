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
            # ‏الـT.E.E. المطبوع بيتشال من المرشحين **قبل** الوحدانية.
            #
            # ‏السبب: الـTDEE دايماً جوّه المدى المقبول للـBMR (هو
            # الـBMR في معامل بين ١.٢ و١.٩)، فوجوده على الورقة كان
            # بيعمل حاجة من اتنين -- يا يبقى هو المرشح الوحيد فيتحط
            # في خانة الـBMR (١٧٣٣ بدل ١١٢٥ في ورقة GAIA)، يا يبقى
            # مرشح تاني جنب الصح فالوحدانية ترفض الاتنين والخانة تفضل
            # فاضية وهي مقروءة. شيله بيحل الحالتين.
            printed_tdee = tdee_on_sheet(lines)
            bmr_pool = pool
            if printed_tdee:
                bmr_pool = set(n for n in pool
                               if abs(n - printed_tdee) > 20)
            _take("bmr", _only_in_band(bmr_pool, katch * BMR_LOW,
                                       katch * BMR_HIGH, "bmr"), "lean_bmr")

    return {"values": values, "why": why}

# ═══════════════════════════════════════════════════════════════════════
#  رفض رقم مقروء بتناقضه معادلة
# ═══════════════════════════════════════════════════════════════════════
#
# ‏لحد هنا الملف بيضيف الخانة الفاضية. الجزء ده بيعمل العكس: بيشيل رقم
# **اتقرا من سطره** لما الجسم نفسه بيقول إنه مستحيل.
#
# ‏اللي خلّى ده لازم: ورقة DR.NUTRITION بتاعة الدكتور بتطبع عمود القيم
# **مزحلق صف واحد لفوق** عن عمود العناوين. قِسْتها على صورة الورقة
# الحقيقية بصناديق المحرّك:
#
#     y~324   Biological Age            1324     ← ده الـBMR فعلاً
#     y~378   Basal Metabolic Rate      2038     ← ده الـTDEE فعلاً
#     y~432   Total Daily Energy Exp.   28.6     ← ده Body Cell Mass
#
# ‏يعني الرقم اللي على صف الـBMR هو الـTDEE. لو القراءتين اتفقوا عليه،
# الفورم كان بياخد BMR = ٢٠٣٨ والصح ١٣٢٤ -- **٧١٤ كالوري غلط** ماشية
# في حساب هدف العميل. اللي منعها كان الحظ: قراءة شافت ٥٠٣٨ وقراءة
# شافت ٢٠٣٨ فاختلفوا واتشال. الحظ مش حاجز.
#
# ‏فحاجزين، والاتنين مقيسين على التلات ورقات الحقيقية:
#
#   ١) الـBMR مقابل الكتلة الخالية (Katch-McArdle). النسب الحقيقية:
#      ٠.٨٧ و٠.٩٣ و١.٠٠. فبرّه ٠.٥٥-١.٤٥ = مستحيل. ده بيمسك ١.٥٤
#      بتاعة ٢٠٣٨ -- وبهامش ضيّق، فهو حاجز مش برهان: TDEE بتاع واحد
#      قليل الحركة (×١.٢) ممكن يعدّي منه.
#
#   ٢) والحاجز اللي مش محتاج هامش: **الـBMR لازم يكون أقل من الـTDEE**.
#      ده مش تقدير، ده تعريف -- الـTDEE هو الـBMR في معامل النشاط،
#      والمعامل أكبر من واحد دايماً. فلو الورقة طابعة الاتنين والرقم
#      اللي على صف الـBMR مش أصغر، يبقى الصفوف مزحلقة وبنشيله.
# ‏(?<![a-z]) على الشمال مهمة: "t.e.e" من غيرها بتطابق جوّه
# "commit**tee**"، فسطر فيه الكلمة ورقم كان بيبقى شاهد TDEE.
_TDEE_LABEL = re.compile(
    r"(?<![a-z])(?:total\s*daily\s*energy"
    r"|total\s*energy\s*expenditure"
    r"|t\.?e\.?e\.?)(?![a-z])", re.I)


def tdee_on_sheet(lines):
    """‏رقم الـTDEE المطبوع، **كشاهد بس** -- مابيروحش الفورم خالص.

    ‏الفورم عنده خانة TDEE بيحسبها من معامل النشاط، والرقم المطبوع على
    الورقة جهاز تاني حسبه بمعامل تاني. فده مش بديل عنه -- ده شاهد
    بيقول إن الـBMR اللي قرينا معقول ولا لأ.
    """
    for line in lines or []:
        text = str(line)
        match = _TDEE_LABEL.search(text)
        if not match:
            continue
        tail = text[match.end():]
        for number in _NUMBER.finditer(tail.replace(",", ".")):
            try:
                value = float(number.group(1))
            except ValueError:
                continue
            # ‏الـTDEE لأي إنسان بين ٨٠٠ و٦٠٠٠ كالوري
            if 800.0 <= value <= 6000.0:
                return value
    return None


# ‏تفاوت مثلث الدهون: الوزن × النسبة = الكتلة. أكتر من نص كيلو فرق =
# واحد من التلاتة اتقرا غلط. (٠.٥ عشان الورقة بتقرّب لخانة عشرية.)
FAT_TOL_KG = 0.5

# ‏تفاوت شاهد الكتلة الخالية. ضيّق بالقصد: مسطرة الـP.B.F. على ورقة
# GAIA فيها علامات ١٠ و١٥ ... و٥٠، والكتلة الخالية المحسوبة من النسبة
# الغلط كانت ٤٩.٧ -- يعني ٠.٣ من علامة الـ٥٠. بتفاوت نص كيلو علامة
# المسطرة كانت هتشهد للرقم الغلط.
LEAN_TOL_KG = 0.2


def _printed_near(pool, target, tol=LEAN_TOL_KG):
    """‏هل فيه رقم **واحد** مطبوع على الورقة في حدود tol من المحسوب؟"""
    near = sorted(set(round(n, 2) for n in pool
                      if abs(n - target) <= tol))
    return len(near) == 1


def contradictions(found, lines):
    """‏الخانات اللي المعادلات تقول إن الرقم المقروء فيها مستحيل.

    ‏بترجّع {خانة: سبب}. النداء بيشيلها ويعرض السبب للدكتور -- خانة
    فاضية بيكتبها بإيده أحسن من رقم غلط ماشي في حساب السعرات.
    """
    out = {}

    weight = _known(found, "weight")
    fat_pct = _known(found, "fat_pct")
    fat_mass = _known(found, "fat_mass")
    bmr = _known(found, "bmr")
    water = _known(found, "body_water")

    lean = None
    if weight and fat_mass and 0 < fat_mass < weight:
        lean = weight - fat_mass
    elif weight and fat_pct:
        lean = weight * (1.0 - fat_pct / 100.0)

    if bmr and lean and lean > 0:
        katch = 370.0 + 21.6 * lean
        ratio = bmr / katch
        if not (0.55 <= ratio <= 1.45):
            out["bmr"] = "lean_bmr"

    if water and lean and lean > 0:
        share = water / lean
        if not (0.50 <= share <= 0.90):
            out["body_water"] = "lean_water"

    # ── مثلث الدهون: الوزن × النسبة = الكتلة ──
    #
    # ‏ده اللي مسك أخطر رقم غلط لحد دلوقتي. ورقة GAIA بتاعة الدكتور
    # (٦٧.٣ كجم، كتلة دهون ٢٤.٣، نسبة ٣٦.١٪) المحرّك قرا فيها
    # "P.B.F. 26.1" -- ٣ اتقرت ٢ -- **في القراءتين مع بعض**، فحاجز
    # الاتفاق بين القراءتين عدّاها. والرقم معقول (٢٦.١٪ نسبة عادية
    # لست)، فحدود المعقول عدّتها. والـFFMI عدّاها كمان (١٨.٩).
    #
    # ‏والفرق مش تفصيلة: ٣٦.١٪ لست عندها ٥٣ سنة = نطاق سمنة، و٢٦.١٪ =
    # نطاق لياقة. عشر نقط مئوية بتغيّر الورقة كلها، والشرح كان بيقول
    # للعميلة "١٧.٦ كجم دهون" والورقة قدامها مكتوب ٢٤.٣.
    #
    # ‏اللي مسكها: الورقة نفسها فيها الشاهد التالت -- **الكتلة الخالية**.
    #
    #     لو النسبة ٢٦.١ صح  ->  الخالية = ٦٧.٣ × ٠.٧٣٩ = ٤٩.٧  -> مش مطبوعة
    #     لو الكتلة ٢٤.٣ صح  ->  الخالية = ٦٧.٣ - ٢٤.٣ = ٤٣.٠  -> مطبوعة (سطر L.B.M.)
    #
    # ‏فاللي الورقة شاهدة له بيفضل، واللي مالوش شاهد بيتشال. ولو
    # الاتنين مالهمش شاهد (أو ليهم)، الاتنين بيتشالوا -- مانعرفش مين.
    if weight and fat_pct and fat_mass:
        if abs(weight * fat_pct / 100.0 - fat_mass) > FAT_TOL_KG:
            pool = numbers_in(lines)
            by_mass = _printed_near(pool, weight - fat_mass)
            by_pct = _printed_near(pool, weight * (1.0 - fat_pct / 100.0))
            if by_mass and not by_pct:
                out["fat_pct"] = "fat_triangle"
            elif by_pct and not by_mass:
                out["fat_mass"] = "fat_triangle"
            else:
                out["fat_pct"] = "fat_triangle"
                out["fat_mass"] = "fat_triangle"

    if bmr and "bmr" not in out:
        tdee = tdee_on_sheet(lines)
        # ‏الـTDEE = الـBMR × معامل النشاط، والمعامل أكبر من واحد. فلو
        # الرقم اللي على صف الـBMR مش أصغر من الـTDEE المطبوع، الصفوف
        # مزحلقة. الهامش (٢٠ كالوري) للتقريب بس.
        if tdee and bmr >= tdee - 20:
            out["bmr"] = "bmr_over_tdee"

    return out


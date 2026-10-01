# -*- coding: utf-8 -*-
"""‏حمية النقاط Opti-tect — من عرض الشركة اللي الدكتور بعته.

‏ده البرنامج الوحيد في الـ12 اللي **مش جدول وجبات**. الباقي كله سبعة
أيام × أربع وجبات، وده نظام **نقاط**: العميل بياخد رصيد نقاط في اليوم،
وبيصرفه من دليل أصناف الطعام زي ما هو عايز.

‏ومن عرض الشركة بالنص: «الحمية لا تعتمد على السعرات الحرارية حيث تعتمد
على الطاقة داخل الجسم و ليست الطاقة خارج الجسم». فالحساب كله هنا
بالنقاط، ومافيش سعرات -- وده عكس كل حاجة تانية في الموقع.


‏اللي العرض بيحدّده بالكامل، وده اللي متنفّذ هنا
──────────────────────────────────────────────────
‏النقاط = الوزن × معامل، والمعامل بيتغيّر على حسب الهدف والمرحلة:

    إنقاص — أول مرحلة دايت      رجال  1.2 : 1.5    سيدات  1.2
    إنقاص — محوّل من حمية تانية   رجال  1.5 : 1.8    سيدات  1.4 : 1.6
    تثبيت                         1.5 : 2  (بتقدير الأخصائي)
    زيادة وزن                     5 : 7
    رياضي — تنشيف وبناء عضل        1.8 : 2.5
    رياضي — تثبيت وتحسين أداء      2.5 : 4
    رياضي — تضخيم وكتلة عضلية      5 : 7

‏وقواعد التعديل بعد المتابعة:

    إنقاص، أول مرحلة   نزل ->  +10 : 15    ثابت ->  -10 : 15
    إنقاص، محوّل        نزل ->  +10        ثابت ->  -10 : 15
    تثبيت              ثابت -> +5 : 15     زاد  ->  -10 : 15
    زيادة              زاد  -> +20 : 30    مازادش -> +50 : 70

‏وثبات أكتر من أسبوعين في الإنقاص -> زجزاج أسبوعين:

    أول 3 أيام في الأسبوع    الوزن × (1 : 1.3)
    آخر 3 أيام               الوزن × (0.8 : 1)

‏وفئة الكربوهيدرات بتتحدد من الوزن (سلايد 9):

    A  لو كارب      أكتر من 90 كجم
    B  ميديم كارب   75 إلى 90
    C  هاي كارب     أقل من 75


‏اللي **مش** متنفّذ، وليه
─────────────────────────
‏نقاط كل صنف أكل. العرض بيقول إن الأصناف محصورة في كتيّب اسمه
«Opti-tect Diet Guide» وإن التحويل بمعادلة خاصة -- والمعادلة نفسها
مش مكتوبة في العرض، والكتيّب مش معانا.

‏اللي معانا خمس أمثلة بس:

    نصف تفاحة 70 جم              9 نقطة
    شريحة توست 20 جم             10.5 نقطة
    صدر دجاج مشوي بدون جلد 200 جم 11 نقطة
    كباب لحم 125 جم              15 نقطة
    تونة معلبة بالماء 85 جم       5.5 نقطة

‏وخمس نقاط مش كفاية أستخرج منها معادلة بتلاتة معاملات (بروتين ودهون
وكربوهيدرات)، خصوصاً إن قيم المكوّنات نفسها عندي تقديرية. أي معادلة
أطلّعها من الخمسة دي هتبقى **تخمين لابس شكل معادلة** -- ورصيد نقاط غلط
معناه عميل بياكل غلط لأسبوع.

‏فالملف ده بيحسب **الرصيد** بالظبط زي العرض، وبيقول صريح إن تقييم
الأصناف محتاج الكتيّب. لو الدكتور بعت الكتيّب، الأصناف بتتحمّل من غير
ما يتغيّر أي حرف في الحساب ده.


‏تناقض في العرض، سايبه بيبان مش بختار فيه
──────────────────────────────────────────
‏سلايد 3 بيقول «Low Carb A & Medium carb B & **Low Fat** C»، وسلايد 7
و9 بيقولوا إن C هي **HIGH CARB**. التلاتة من نفس العرض.

‏الاتنين متوافقين في المعنى (هاي كارب = دهون أقل)، والأغلبية سلايدين
مقابل سلايد، فالمتنفّذ هنا C = HIGH CARB -- ومكتوب في ملاحظة البرنامج
إن العرض فيه السطرين، عشان الدكتور يحسمها مش عشان أنا أحسمها بالسكوت.


‏الواجهة العامة:
    TIERS            فئات الكربوهيدرات بحدود أوزانها
    carb_tier()      -> ("A", "لو كارب") من الوزن
    points_for()     -> رصيد النقاط اليومي، بحدوده الدنيا والعليا
    zigzag_points()  -> نقاط الزجزاج لما يحصل ثبات أسبوعين
    prescribe()      -> الوصفة كاملة: نقاط وفئة وقواعد التعديل
"""

# ‏فئات الكربوهيدرات من الوزن. (الحد الأدنى للوزن, المفتاح, عربي, إنجليزي)
# ‏مرتّبة من الأتقل للأخف عشان أول واحدة بتنطبق هي الصح.
TIERS = [
    (90.0, "A", "لو كارب", "Low carb"),
    (75.0, "B", "ميديم كارب", "Medium carb"),
    (0.0, "C", "هاي كارب", "High carb"),
]

# ‏المعاملات: المفتاح -> (من, إلى, عربي, إنجليزي)
#
# ‏اللي ليه قيمة واحدة في العرض بيتكتب بنفس الرقم مرتين (سيدات أول
# مرحلة = الوزن × 1.2 بالظبط، مافيش نطاق) -- عشان الكود يتعامل مع
# الكل بنفس الشكل من غير حالة خاصة.
MULTIPLIERS = {
    "loss_first_male": (1.2, 1.5, "إنقاص — أول مرحلة (رجال)",
                        "Weight loss - first phase (men)"),
    "loss_first_female": (1.2, 1.2, "إنقاص — أول مرحلة (سيدات)",
                          "Weight loss - first phase (women)"),
    "loss_switch_male": (1.5, 1.8, "إنقاص — محوّل من حمية تانية (رجال)",
                         "Weight loss - switching from another diet (men)"),
    "loss_switch_female": (1.4, 1.6, "إنقاص — محوّل من حمية تانية (سيدات)",
                           "Weight loss - switching from another diet (women)"),
    "maintain": (1.5, 2.0, "تثبيت الوزن", "Weight maintenance"),
    "gain": (5.0, 7.0, "زيادة الوزن", "Weight gain"),
    "athlete_cut": (1.8, 2.5, "رياضي — تنشيف وبناء عضل",
                    "Athlete - cutting fat and building muscle"),
    "athlete_perform": (2.5, 4.0, "رياضي — تثبيت وتحسين الأداء",
                        "Athlete - maintenance and performance"),
    "athlete_bulk": (5.0, 7.0, "رياضي — تضخيم وكتلة عضلية",
                     "Athlete - bulking and muscle mass"),
}

# ‏قواعد التعديل بعد المتابعة: المفتاح -> (عربي, إنجليزي)
ADJUSTMENTS = {
    "loss_first": (
        "لو نزل: زوّد 10 إلى 15 نقطة. لو ثابت: قلّل 10 إلى 15 نقطة.",
        "If they lost: add 10 to 15 points. If stalled: cut 10 to 15 points."),
    "loss_switch": (
        "لو نزل: زوّد 10 نقاط. لو ثابت: قلّل 10 إلى 15 نقطة.",
        "If they lost: add 10 points. If stalled: cut 10 to 15 points."),
    "maintain": (
        "لو ثابت: زوّد 5 إلى 15 نقطة. لو زاد: قلّل 10 إلى 15 نقطة. "
        "فترة التثبيت من شهرين لتلاتة.",
        "If stalled: add 5 to 15 points. If they gained: cut 10 to 15 points. "
        "The maintenance period runs two to three months."),
    "gain": (
        "بعد أسبوع: لو زاد زوّد 20 إلى 30 نقطة، ولو مازادش زوّد 50 إلى 70.",
        "After a week: if they gained, add 20 to 30 points; if not, add 50 to 70."),
}

# ‏الزجزاج لما يحصل ثبات أكتر من أسبوعين مع عميل إنقاص
ZIGZAG_HIGH = (1.0, 1.3)    # أول 3 أيام في الأسبوع
ZIGZAG_LOW = (0.8, 1.0)     # آخر 3 أيام
ZIGZAG_WEEKS = 2

# ‏البرامج في الكتيّب: 105 برنامج من 40 لـ300 نقطة
BOOK_MIN_POINTS = 40
BOOK_MAX_POINTS = 300
BOOK_PROGRAMMES = 105
BOOK_SWAPS_PER_DAY = 5

# ‏نقاط الأصناف الخمسة اللي العرض ضارب بيها مثال. دي **كل** اللي معانا،
# ومش كفاية لمعادلة -- موجودة هنا كمرجع وعشان الدكتور يشوف الشكل.
EXAMPLE_POINTS = [
    ("نصف ثمرة تفاح 70 جم", "Half an apple, 70 g", 9.0),
    ("شريحة توست 20 جم", "A slice of toast, 20 g", 10.5),
    ("صدر دجاج مشوي بدون جلد 200 جم",
     "Skinless grilled chicken breast, 200 g", 11.0),
    ("كباب لحم 125 جم", "Beef kebab, 125 g", 15.0),
    ("تونة معلبة بالماء 85 جم", "Canned tuna in water, 85 g", 5.5),
]


def _num(value, default=0.0):
    try:
        out = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default
    return out


def carb_tier(weight):
    """‏فئة الكربوهيدرات من الوزن -> (المفتاح, عربي, إنجليزي).

    ‏None لو الوزن مش مكتوب: الفئة بتتحدد من الوزن وبس، ومن غيره
    مانخمّنش -- فئة غلط معناها جدول كربوهيدرات غلط.
    """
    kilos = _num(weight)
    if kilos <= 0:
        return None
    for floor, key, name_ar, name_en in TIERS:
        if kilos > floor:
            return key, name_ar, name_en
    return TIERS[-1][1], TIERS[-1][2], TIERS[-1][3]


def _multiplier_key(goal_type, gender, phase, athlete):
    """‏أنهي معامل ينطبق على الحالة دي."""
    if athlete in ("cut", "perform", "bulk"):
        return "athlete_" + athlete
    female = "نث" in str(gender or "") or str(gender or "").lower().startswith(
        ("f", "w", "female", "woman"))
    goal = str(goal_type or "weight_loss")
    if goal in ("maintenance", "maintain"):
        return "maintain"
    if goal in ("muscle_gain", "bulking", "gain", "weight_gain"):
        return "gain"
    # ‏الباقي إنقاص. المرحلة: أول دايت ولا محوّل من حمية تانية؟
    stage = "switch" if str(phase or "") == "switch" else "first"
    return "loss_%s_%s" % (stage, "female" if female else "male")


def points_for(weight, goal_type="weight_loss", gender=None, phase="first",
               athlete=None):
    """‏رصيد النقاط اليومي.

    بيرجّع ديكشنري فيه:
        low, high     حدود الرصيد (النطاق اللي العرض بيحدده)
        points        الوسط، للعرض كرقم واحد
        key           أنهي معامل اتطبّق
        label         اسم الحالة بالعربي والإنجليزي
        factor_low/high  المعاملات نفسها

    بيرجّع None لو الوزن مش مكتوب.
    """
    kilos = _num(weight)
    if kilos <= 0:
        return None
    key = _multiplier_key(goal_type, gender, phase, athlete)
    low_factor, high_factor, label_ar, label_en = MULTIPLIERS[key]
    low = kilos * low_factor
    high = kilos * high_factor
    return {
        "key": key,
        "label": label_ar,
        "label_en": label_en,
        "factor_low": low_factor,
        "factor_high": high_factor,
        "low": int(round(low)),
        "high": int(round(high)),
        "points": int(round((low + high) / 2.0)),
    }


def zigzag_points(weight):
    """‏نقاط الزجزاج لما يحصل ثبات أكتر من أسبوعين مع عميل إنقاص."""
    kilos = _num(weight)
    if kilos <= 0:
        return None
    return {
        "weeks": ZIGZAG_WEEKS,
        "high_low": int(round(kilos * ZIGZAG_HIGH[0])),
        "high_high": int(round(kilos * ZIGZAG_HIGH[1])),
        "low_low": int(round(kilos * ZIGZAG_LOW[0])),
        "low_high": int(round(kilos * ZIGZAG_LOW[1])),
    }


def _adjust_key(points_key):
    if points_key.startswith("loss_first"):
        return "loss_first"
    if points_key.startswith("loss_switch"):
        return "loss_switch"
    if points_key == "maintain":
        return "maintain"
    if points_key in ("gain", "athlete_bulk"):
        return "gain"
    return None


def prescribe(weight, goal_type="weight_loss", gender=None, phase="first",
              athlete=None, stalled_two_weeks=False):
    """‏وصفة Opti-tect كاملة للعميل ده.

    بترجع (lines, detail): lines أزواج (عربي، إنجليزي) تنفع تتكتب على
    الورقة زي ما هي، وdetail الأرقام نفسها لو حد عايز يبني عليها.

    ‏الأزواج مش نص واحد: الـPDF الإنجليزي بياخد التاني، وبرّه كده
    بيطلع عربي في ورقة إنجليزي.
    """
    detail = {
        "points": points_for(weight, goal_type, gender, phase, athlete),
        "tier": carb_tier(weight),
        "zigzag": zigzag_points(weight) if stalled_two_weeks else None,
    }
    lines = []
    allowance = detail["points"]
    if allowance is None:
        lines.append((
            "اكتب الوزن عشان نحسب رصيد النقاط — حمية النقاط كلها "
            "بتتحسب من الوزن.",
            "Enter the weight so the points allowance can be computed -- "
            "the whole points system is derived from it."))
        return lines, detail

    if allowance["low"] == allowance["high"]:
        amount_ar = "%d نقطة" % allowance["low"]
        amount_en = "%d points" % allowance["low"]
    else:
        amount_ar = "%d إلى %d نقطة" % (allowance["low"], allowance["high"])
        amount_en = "%d to %d points" % (allowance["low"], allowance["high"])
    lines.append((
        "رصيد النقاط اليومي: %s (%s)." % (amount_ar, allowance["label"]),
        "Daily points allowance: %s (%s)." % (amount_en, allowance["label_en"])))

    tier = detail["tier"]
    if tier:
        lines.append((
            "فئة الكربوهيدرات: %s — %s (من وزن %s كجم)."
            % (tier[0], tier[1], _fmt(weight)),
            "Carbohydrate tier: %s - %s (from a weight of %s kg)."
            % (tier[0], tier[2], _fmt(weight))))

    adjust = _adjust_key(allowance["key"])
    if adjust:
        lines.append(ADJUSTMENTS[adjust])

    if detail["zigzag"]:
        z = detail["zigzag"]
        lines.append((
            "ثبات أكتر من أسبوعين — زجزاج لمدة %d أسبوع: أول 3 أيام %d إلى %d "
            "نقطة، وآخر 3 أيام %d إلى %d نقطة."
            % (z["weeks"], z["high_low"], z["high_high"],
               z["low_low"], z["low_high"]),
            "Stalled more than two weeks - zigzag for %d weeks: %d to %d points "
            "on the first three days, %d to %d on the last three."
            % (z["weeks"], z["high_low"], z["high_high"],
               z["low_low"], z["low_high"])))

    lines.append((
        "العميل يقدر يستبدل %d بدائل في اليوم، متباعدة ومش من نفس الوجبة، "
        "وبنفس عدد النقاط تقريباً." % BOOK_SWAPS_PER_DAY,
        "The client may swap %d items a day, spaced apart and not from the same "
        "meal, at roughly the same points." % BOOK_SWAPS_PER_DAY))

    # ‏الرصيد خارج نطاق الكتيّب؟
    #
    # ‏العرض بيقول 105 برنامج من 40 لـ300 نقطة. ومعادلة الزيادة (الوزن ×
    # 5 إلى 7) بتطلّع 300 إلى 420 نقطة لعميل 60 كجم، و400 إلى 560 لرياضي
    # تضخيم 80 كجم -- يعني فوق أعلى برنامج في الكتيّب.
    #
    # ‏ده تناقض جوّه أرقام العرض نفسه، مش حاجة أقدر أحلها: يا إما معامل
    # الزيادة مقصود بيه حاجة تانية، يا إما الكتيّب مابيغطّيش الزيادة.
    # فبيتقال للأخصائي ويقرّر، وماينفعش يتسكت عنه -- الأخصائي هيدوّر على
    # برنامج 420 نقطة في كتيّب أقصاه 300 ومش هيلاقيه.
    detail["out_of_book"] = False
    if allowance["high"] > BOOK_MAX_POINTS or allowance["low"] < BOOK_MIN_POINTS:
        detail["out_of_book"] = True
        lines.append((
            "الرصيد ده برّه نطاق الكتيّب (%d إلى %d نقطة في %d برنامج) — "
            "راجع المعامل أو اسأل الشركة عن برنامج للرصيد ده."
            % (BOOK_MIN_POINTS, BOOK_MAX_POINTS, BOOK_PROGRAMMES),
            "This allowance falls outside the booklet's range (%d to %d points "
            "across %d programmes) -- review the multiplier, or ask the company "
            "which programme covers it."
            % (BOOK_MIN_POINTS, BOOK_MAX_POINTS, BOOK_PROGRAMMES)))

    return lines, detail


def _fmt(value):
    number = _num(value)
    if abs(number - round(number)) < 0.05:
        return str(int(round(number)))
    return "%.1f" % number

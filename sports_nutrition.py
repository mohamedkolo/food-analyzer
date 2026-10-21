# -*- coding: utf-8 -*-
"""‏أهداف الرياضي: كارب وبروتين حسب نوع الرياضة وحِمل التمرين.

‏الموجود قبل كده
───────────────
‏البرنامج فيه "رياضي / بناء عضل" كمستوى نشاط، ومعامل بروتين ٢.٠ جم/كجم،
ونظام اسمه workout فيه خانة قبل التمرين وخانة بعده. وده كل حاجة.

‏والمشكلة إن ده مش تغذية رياضيين، ده تغذية عادية برقم بروتين أعلى:

  ١) ‏**مافيش فرق بين يوم تمرين ويوم راحة.** ودي أهم حاجة في الموضوع
     كله: الكارب هو وقود التمرين، ويوم الراحة محتاج أقل منه. جدول
     واحد للاتنين معناه إما نقص وقود يوم التمرين أو فائض يوم الراحة.

  ٢) ‏**مافيش نوع رياضة.** لاعب حديد ولاعب ماراثون احتياجهم من الكارب
     بيختلف الضعف تقريباً (٤-٧ مقابل ٦-١٢ جم/كجم). جدول واحد للاتنين
     غلط لواحد فيهم على الأقل.

  ٣) ‏**خانة قبل التمرين سطر ثابت مكتوب في الكود** -- "موزة + زبدة فول
     سوداني + قهوة"، نفس الكلام سبع أيام، مابيتظبطش على وزن الرياضي
     ولا بيتفلتر على حساسية ولا حالة.

الأرقام هنا منقولة مش مخترعة
────────────────────────────
‏الكارب من بيان ACSM / Academy of Nutrition and Dietetics / Dietitians
of Canada المشترك (٢٠١٦)، والبروتين من بيان ISSN (٢٠١٧)، وأرقام رياضات
النزال من بيان ISSN لرياضات النزال (٢٠٢٥). الروابط في README الوحدة
وفي الاختبارات.

‏وكلها **نطاقات مش أرقام مفردة**. البيانات نفسها بتقول نطاق، وطباعة رقم
واحد بتدّعي دقة مش موجودة -- والدكتور هو اللي بيختار من جوه النطاق على
حسب اللي قدامه.
"""

# ── الكارب: جرام لكل كيلو من وزن الجسم في اليوم ──────────────────────
#
# ‏ACSM 2016 (البيان المشترك): الحِمل بيتقاس بساعات التمرين وشدّته.
CARB_BY_LOAD = {
    # (الأدنى، الأعلى)
    "light":     (3, 5),    # ‏تمرين خفيف أو مهارات
    "moderate":  (5, 7),    # ‏حوالي ساعة في اليوم
    "high":      (6, 10),   # ‏تحمّل، ١-٣ ساعات شدة متوسطة لعالية
    "very_high": (8, 12),   # ‏التزام متطرف، +٤-٥ ساعات
}

LOAD_LABELS = {
    "light":     ("تمرين خفيف أو مهارات", "Light or skill-based"),
    "moderate":  ("حوالي ساعة يومياً", "About an hour a day"),
    "high":      ("تحمّل ١-٣ ساعات", "Endurance, 1-3 hours"),
    "very_high": ("+٤ ساعات يومياً", "4+ hours a day"),
}

# ‏رياضات القوة ليها نطاقها هي. الحديد مش بيستهلك جليكوجين زي التحمّل،
# فنطاق التحمّل عليه بيبقى فائض سعرات مالوش لازمة.
STRENGTH_CARB = (4, 7)

# ‏أرضية رياضات النزال في المعسكر (ISSN 2025): الكارب مايقلّش عن كده حتى
# وهو بينزل وزن. ده أكتر سياق بيحصل فيه تجويع فعلي.
COMBAT_CARB_FLOOR = 3

# ── البروتين: جرام لكل كيلو في اليوم ────────────────────────────────
#
# ‏ISSN 2017: ١.٤-٢.٠ لمعظم اللي بيتمرنوا.
PROTEIN_RANGE = (1.4, 2.0)

# ‏ونفس البيان: ٢.٣-٣.١ لمدرَّبي المقاومة **في عجز سعري**، للحفاظ على
# الكتلة العضلية. الرقم ده أعلى من سقف البرنامج العام (٣.٠ جم/كجم في
# protein_need.DELIVERED_MAX_PER_KG) -- وده مقصود: السقف ده موضوع
# يمسك المبالغة، والحالة دي مبالغة **موثّقة ومقصودة**، فبتتعامل
# كاستثناء باسمه مش بكسر السقف للكل.
PROTEIN_CUT_RESISTANCE = (2.3, 3.1)

# ‏رياضات النزال في عجز (ISSN 2025)
PROTEIN_COMBAT_CUT = (1.2, 2.2)

SPORTS = {
    "strength":  ("قوة (حديد / كمال أجسام / رفع)", "Strength (lifting, bodybuilding)"),
    "endurance": ("تحمّل (جري / دراجة / سباحة)", "Endurance (running, cycling, swimming)"),
    "mixed":     ("مختلط (كورة / سلة / كروس فيت)", "Mixed (football, basketball, CrossFit)"),
    "combat":    ("نزال (ملاكمة / مصارعة / MMA)", "Combat (boxing, wrestling, MMA)"),
}

# ‏الكارب يوم الراحة: نسبة من يوم التمرين.
#
# ‏ليه ٠.٧ مش صفر ومش واحد: يوم الراحة مش يوم صيام -- الجليكوجين بيتعوّض
# فيه، وده نص شغل الراحة. وفي نفس الوقت مافيش تمرين يستهلكه، فالحفاظ
# على نفس كارب يوم التمرين بيبقى فائض. النسبة دي بتخلي متوسط الأسبوع
# قريب من النطاق الموصى به مع إن الأيام مختلفة.
REST_DAY_CARB = 0.70

# ‏والبروتين **مابيتغيّرش** يوم الراحة. بناء العضل بيحصل في الراحة مش في
# التمرين، فتقليل البروتين يوم الراحة بيضرب اللي التمرين عمله.
REST_DAY_PROTEIN = 1.0


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def carb_range(sport, load):
    """‏نطاق الكارب جم/كجم/يوم حسب الرياضة والحِمل.

    ‏رياضات القوة ليها نطاقها هي مهما كان الحِمل: لاعب الحديد اللي
    بيتمرن ساعتين مش محتاج كارب عدّاء بيجري ساعتين -- الشغل مختلف
    ومصدر الطاقة مختلف.
    """
    if sport == "strength":
        return STRENGTH_CARB
    return CARB_BY_LOAD.get(load or "moderate", CARB_BY_LOAD["moderate"])


def protein_range(sport, in_deficit=False):
    """‏نطاق البروتين جم/كجم/يوم.

    in_deficit = الخطة فيها عجز سعري. ساعتها البروتين بيرتفع للحفاظ على
    العضل -- وده اللي البيانات بتقوله، مش تشديد منّنا.
    """
    if not in_deficit:
        return PROTEIN_RANGE
    if sport == "combat":
        return PROTEIN_COMBAT_CUT
    if sport == "strength":
        return PROTEIN_CUT_RESISTANCE
    # ‏تحمّل ومختلط في عجز: أعلى من العادي، أقل من مدرَّب المقاومة
    return (1.6, 2.2)


def targets(weight, sport="strength", load="moderate", in_deficit=False,
            training_day=True):
    """‏أهداف يوم واحد بالجرام، مش بالجرام/كجم.

    بترجّع: carb_g و protein_g (نطاق لكل واحد)، ومعاهم الأساس اللي
    اتحسبوا منه عشان الدكتور يراجعه.
    """
    w = _num(weight)
    if w <= 0:
        return None

    c_lo, c_hi = carb_range(sport, load)
    p_lo, p_hi = protein_range(sport, in_deficit)

    if not training_day:
        c_lo *= REST_DAY_CARB
        c_hi *= REST_DAY_CARB
        p_lo *= REST_DAY_PROTEIN
        p_hi *= REST_DAY_PROTEIN

    # ‏أرضية النزال بتتطبّق **بعد** خصم يوم الراحة: البيان بيتكلم عن
    # أقل كارب يومي في المعسكر، مش عن متوسط الأسبوع.
    if sport == "combat":
        c_lo = max(c_lo, COMBAT_CARB_FLOOR)
        c_hi = max(c_hi, COMBAT_CARB_FLOOR)

    return {
        "carb_g": (int(round(c_lo * w)), int(round(c_hi * w))),
        "protein_g": (int(round(p_lo * w)), int(round(p_hi * w))),
        "carb_per_kg": (round(c_lo, 1), round(c_hi, 1)),
        "protein_per_kg": (round(p_lo, 2), round(p_hi, 2)),
        "sport": sport,
        "load": load,
        "training_day": bool(training_day),
        "in_deficit": bool(in_deficit),
    }


def week(weight, sport="strength", load="moderate", in_deficit=False,
         training_days=4):
    """‏الأسبوع: أيام تمرين وأيام راحة، وكل نوع بأهدافه.

    بترجّع قايمة سبع عناصر بالترتيب (تمرين/راحة)، ومعاها متوسط الكارب
    عشان يتقارن بالنطاق الموصى به.
    """
    try:
        n = int(training_days)
    except (TypeError, ValueError):
        n = 4
    n = max(0, min(7, n))

    # ‏التوزيع مش أول أربع أيام وبعدين راحة: الراحة بتتوزّع على الأسبوع
    # عشان ماييجيش تلات أيام راحة ورا بعض.
    pattern = [False] * 7
    if n:
        step = 7.0 / n
        for i in range(n):
            pattern[int(round(i * step)) % 7] = True
        # ‏التقريب ممكن يدّي نفس اليوم مرتين، فنكمّل الناقص
        while sum(pattern) < n:
            for i in range(7):
                if not pattern[i]:
                    pattern[i] = True
                    break

    days = [targets(weight, sport, load, in_deficit, training_day=t)
            for t in pattern]
    days = [d for d in days if d]
    if not days:
        return None
    avg_lo = sum(d["carb_g"][0] for d in days) / float(len(days))
    avg_hi = sum(d["carb_g"][1] for d in days) / float(len(days))
    return {
        "days": days,
        "training_days": sum(pattern),
        "avg_carb_g": (int(round(avg_lo)), int(round(avg_hi))),
    }

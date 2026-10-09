# -*- coding: utf-8 -*-
"""‏هدف البروتين: على وزن مين بالظبط؟

‏الموقع كان بيحسبه **وزن العميل × جرام/كجم**، وده صح للبالغ الطبيعي
وغلط خطير في حالتين: الطفل، والسمنة الشديدة.

ورقة نورة -- دي الورقة اللي الدكتور بعتها
──────────────────────────────────────────
    ‏العمر   ١٠ سنين
    ‏الطول   ١٥٢ سم
    ‏الوزن   ١٠٨.٨ كجم
    BMI     ٤٧.١

‏الموقع طبع لها "بروتين مستهدف: ١.٣ جم/كجم = **١٤١ جم**"، والأكل في
الجدول طلّع بين ١٣٣ و**٢٢٢** جم. وزيادة البروتين اللي اتعملت إمبارح
زوّدت لها ١٤٥ جم بياض بيض عشان توصّلها للـ١٤١.

‏والمفروض لبنت عندها ١٠ سنين: التوصية (DRI) **٠.٩٥ جم/كجم**، وعلى
وزن مرجعي لطولها -- مش على ١٠٨.٨. يعني حوالي **٣٦-٤٠ جم**. الورقة
كانت بتطلب **تلات أضعاف**، والأكل بيوصل **خمس أضعاف**.

ليه الوزن المرجعي مش الوزن الفعلي
──────────────────────────────────
‏الدهون الزيادة مش نسيج نشط بيحتاج بروتين. فحساب البروتين على وزن
فيه ٦٠ كيلو دهون بيطلّع رقم مالوش علاقة باحتياج الجسم -- وده معروف
في تغذية الأطفال، والحساب بيتعمل على **الوزن عند منتصف منحنى النمو
لنفس الطول والسن**.

‏الجدول تحت متوسط الـBMI عند منتصف المنحنى لكل سن (CDC/WHO، تقريب
لخانة عشرية واحدة). مش بديل عن منحنى النمو نفسه -- بس بيمنع الرقم
المستحيل.

‏البالغ مابيتغيّرش هنا بالقصد: ١.٨ جم/كجم لبالغ ١٠٠ كجم رقم كبير بس
هو اختيار إكلينيكي معروف، والدكتور هو اللي يقرره. الطفل لأ.
"""

# ‏متوسط الـBMI عند منتصف منحنى النمو، سن 4-18. بنت وولد قريبين جداً
# في السن ده، فجدول واحد -- الفرق بينهم أقل من خطأ التقريب نفسه.
_MEDIAN_BMI = {
    4: 15.3, 5: 15.2, 6: 15.3, 7: 15.5, 8: 15.8, 9: 16.1, 10: 16.6,
    11: 17.2, 12: 17.8, 13: 18.4, 14: 19.0, 15: 19.6, 16: 20.2,
    17: 20.8, 18: 21.3,
}

# ‏التوصية اليومية للبروتين (جم/كجم) حسب السن -- DRI
_CHILD_RDA = ((3, 1.05), (8, 0.95), (13, 0.95), (18, 0.85))

# ‏أقصى جرام/كجم مقبول لطفل حتى في إدارة الوزن. فوق كده مافيش توصية
# بتسنده، والحمل على الكلى في سن النمو مش حاجة نجرّبها.
CHILD_MAX_PER_KG = 2.0

# ‏الوزن الفعلي بيتجاهل لما يعدّي الوزن المرجعي بالنسبة دي. تحتها
# الفرق صغير ومالوش لازمة نلخبط الحساب عشانه.
OBESE_RATIO = 1.2


def is_child(age):
    try:
        return 0 < float(age) < 18
    except (TypeError, ValueError):
        return False


def child_rda(age):
    """‏التوصية اليومية (جم/كجم) للسن ده."""
    try:
        years = float(age)
    except (TypeError, ValueError):
        return 0.95
    for top, value in _CHILD_RDA:
        if years <= top:
            return value
    return 0.85


def median_bmi(age):
    """‏الـBMI عند منتصف منحنى النمو للسن ده."""
    try:
        years = int(round(float(age)))
    except (TypeError, ValueError):
        return None
    if years in _MEDIAN_BMI:
        return _MEDIAN_BMI[years]
    if years < 4:
        return _MEDIAN_BMI[4]
    return None


def reference_weight(height_cm, age):
    """‏وزن الطفل عند منتصف منحنى النمو لطوله وسنه، أو None."""
    bmi = median_bmi(age)
    try:
        metres = float(height_cm) / 100.0
    except (TypeError, ValueError):
        return None
    if not bmi or metres <= 0:
        return None
    return round(bmi * metres * metres, 1)


def target_grams(weight, height, age, per_kg):
    """‏هدف البروتين باليوم، ومعاه على إيه اتحسب.

    ‏بترجّع (جرامات, الوزن اللي اتحسب عليه, سبب, الجرام/كجم المستخدم).
    السبب بيتكتب على الورقة -- مافيش رقم بيتغيّر في صمت.

      None          ‏بالغ، أو طفل الحساب ليه زي ما هو
      "rate"        ‏الجرام/كجم اتظبط على حدود سن النمو
      "reference"   ‏الحساب على الوزن المرجعي لطوله وسنه
      "rate+reference"  ‏الاتنين
    """
    try:
        actual = float(weight or 0)
        rate = float(per_kg or 0)
    except (TypeError, ValueError):
        return 0, 0.0, None, 0.0
    if actual <= 0 or rate <= 0:
        return 0, actual, None, rate

    if not is_child(age):
        return int(round(actual * rate)), actual, None, rate

    # ‏طفل: الجرام/كجم مايقلّش عن التوصية وماي��دّيش السقف المطلق
    rda = child_rda(age)
    used = min(max(rate, rda), CHILD_MAX_PER_KG)

    basis = actual
    reasons = []
    if abs(used - rate) > 0.01:
        reasons.append("rate")

    ref = reference_weight(height, age)
    if ref and actual > ref * OBESE_RATIO:
        basis = ref
        reasons.append("reference")

    why = "+".join(reasons) if reasons else None
    return int(round(basis * used)), basis, why, used


def note(age, height, weight, per_kg, is_ar=True):
    """‏سطر يتكتب على الورقة لو الحساب اتغيّر، وإلا None.

    ‏السطر بيقول **الرقم اللي اتحسب بيه فعلاً**. أول نسخة كانت بتكتب
    توصية السن (٠.٩٥) والحساب ماشي على ١.٣، فالسطر بيقول رقم والحساب
    بيقول رقم تاني -- نفس العيب اللي الشغل كله بيتصلّح عشانه.
    """
    grams, basis, why, used = target_grams(weight, height, age, per_kg)
    if not why:
        return None
    parts = []
    if is_ar:
        if "reference" in why:
            parts.append("اتحسب على الوزن المرجعي لطول وسن الطفل (%s كجم) "
                         "مش على الوزن الحالي" % _fmt(basis))
        if "rate" in why:
            parts.append("والجرام/كجم اتظبط على حدود سن النمو (%.2f)" % used)
        return "‏البروتين %s = **%d جم**." % ("، ".join(parts), grams)
    if "reference" in why:
        parts.append("was computed on the reference weight for this child's "
                     "height and age (%s kg), not the current weight"
                     % _fmt(basis))
    if "rate" in why:
        parts.append("and the g/kg was held to the growth range (%.2f)" % used)
    return "Protein %s = %d g." % (" ".join(parts), grams)


def _fmt(value):
    return ("%g" % round(float(value), 1))

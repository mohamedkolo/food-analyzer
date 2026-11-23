# -*- coding: utf-8 -*-
"""‏محلل الواي بروتين: من ضهر العلبة لتقييم من ١٠٠.

‏المستخدم بيصوّر الـSupplement Facts وجدول الأحماض الأمينية. القراءة
(OCR) بتحصل في موبايله بـTesseract.js -- نفس اللي بيقرا ورق التحليل --
فالصورة مابتخرجش منه. السيرفر بياخد النص ويطلّع الأرقام (parse_label)،
والمستخدم بيراجعها ويصلّحها، وبعدين analyze بتحسب.

‏المعادلات ونظام النقط من صاحب المشروع بالحرف، ومقيسة على علبته التجريبية
(DEMO): Total AA 89.5%، Leucine 10.29%، EAA 47%، BCAA 22.2%، Score 100.

‏Leucine% وEAA% وBCAA% نسب من مجموع الأحماض، فمابتفرقش الأرقام مكتوبة
لكل ١٠٠ جم بروتين ولا للحصة. اللي بيفرق هو Total AA%: لازم يتحوّل
للحصة الأول -- ولو الوحدة اتقرت غلط بيطلع مجموع أكبر من الحصة نفسها.
"""

import re

AMINO = ("Alanine", "Arginine", "Aspartic", "Cystine", "Glutamine", "Glycine",
         "Histidine", "Isoleucine", "Leucine", "Lysine", "Methionine",
         "Phenylalanine", "Proline", "Serine", "Threonine", "Tryptophan",
         "Tyrosine", "Valine")
EAA = ("Histidine", "Isoleucine", "Leucine", "Lysine", "Methionine",
       "Phenylalanine", "Threonine", "Tryptophan", "Valine")
BCAA = ("Leucine", "Isoleucine", "Valine")

AMINO_AR = {
    "Alanine": "ألانين", "Arginine": "أرجينين", "Aspartic": "حمض الأسبارتيك",
    "Cystine": "سيستين", "Glutamine": "جلوتامين / حمض الجلوتاميك", "Glycine": "جلايسين",
    "Histidine": "هيستيدين", "Isoleucine": "أيزوليوسين", "Leucine": "ليوسين",
    "Lysine": "لايسين", "Methionine": "ميثيونين", "Phenylalanine": "فينيل ألانين",
    "Proline": "برولين", "Serine": "سيرين", "Threonine": "ثريونين",
    "Tryptophan": "تريبتوفان", "Tyrosine": "تيروزين", "Valine": "فالين",
}

# ‏العلبة التجريبية من صاحب المشروع: الأحماض بالمللي لكل ١٠٠ جم بروتين.
DEMO = {
    "serving_g": 31, "protein_g": 28,
    "amino": {"Alanine": 5000, "Arginine": 2100, "Aspartic": 11000, "Cystine": 2200,
              "Glutamine": 18100, "Glycine": 1400, "Histidine": 1700, "Isoleucine": 6100,
              "Leucine": 10200, "Lysine": 9600, "Methionine": 2200, "Phenylalanine": 3000,
              "Proline": 5500, "Serine": 4600, "Threonine": 6700, "Tryptophan": 1400,
              "Tyrosine": 2600, "Valine": 5700},
}

# ‏نظام النقط: (الحد الأدنى، النقط) من الأعلى للأقل. الحدود من الجدول:
# 85 / 75-84.9 / 65-74.9 / أقل -- يعني 84.95 لسه 22 مش 30.
SCALE = {
    "total_aa": ((85, 30), (75, 22), (65, 12)),
    "leucine": ((10, 30), (9, 24), (8, 14)),
    "eaa": ((45, 20), (40, 15), (35, 8)),
    "bcaa": ((20, 20), (18, 15), (15, 8)),
}
MAX_POINTS = {"total_aa": 30, "leucine": 30, "eaa": 20, "bcaa": 20}

GRADES = (
    (90, "excellent", "ممتاز", "Excellent",
     "Whey نضيف جداً، اشتريه وانت مطمن", "A very clean whey. Buy it with confidence."),
    (75, "good", "جيد", "Good",
     "بروتين كويس، ينفع للاستخدام اليومي", "A good protein, fine for daily use."),
    (50, "fair", "مقبول", "Acceptable",
     "فيه حشو، ممكن تستخدمه بس سعره لازم يكون رخيص",
     "It has filler. Usable, but only at a low price."),
    (0, "bad", "غير مقبول", "Not acceptable",
     "ده مش Whey حقيقي، متشتريهوش - احتمال Amino Spiking",
     "This is not real whey. Don't buy it - likely amino spiking."),
)


def points(metric, value):
    for floor, pts in SCALE[metric]:
        if value >= floor:
            return pts
    return 0


def grade(score):
    for floor, key, ar, en, note_ar, note_en in GRADES:
        if score >= floor:
            return {"key": key, "ar": ar, "en": en, "note_ar": note_ar, "note_en": note_en}
    return grade(0)


def _tier(metric, pts):
    """‏كلمة لكل معادلة لوحدها، من النقط اللي خدتها."""
    full = MAX_POINTS[metric]
    if pts == full:
        return "excellent"
    if pts == 0:
        return "bad"
    return "good" if pts >= full * 0.7 else "fair"


def analyze(serving_g, protein_g, amino, unit="per100"):
    """‏الحساب كله. unit: "per100" (لكل ١٠٠ جم بروتين) أو "serving".

    ‏بترفع ValueError برسالة عربي لو الأرقام مستحيلة -- مايتقيّمش منتج
    على أرقام غلط.
    """
    serving_g = float(serving_g or 0)
    protein_g = float(protein_g or 0)
    if serving_g <= 0 or protein_g <= 0:
        raise ValueError("اكتب حجم الحصة والبروتين في الحصة")
    if protein_g > serving_g:
        raise ValueError("البروتين في الحصة أكبر من الحصة نفسها -- راجع الرقمين")
    aa = {k: float(amino.get(k) or 0) for k in AMINO}
    total_mg = sum(aa.values())
    if total_mg <= 0:
        raise ValueError("مفيش أرقام للأحماض الأمينية")

    if unit == "per100":
        factor = protein_g / 100.0
        total_g = (total_mg / 1000.0) * factor
        leucine_g = (aa["Leucine"] / 1000.0) * factor
    else:
        total_g = total_mg / 1000.0
        leucine_g = aa["Leucine"] / 1000.0
    if total_g > serving_g * 1.05:
        raise ValueError("مجموع الأحماض أكبر من الحصة نفسها -- غالباً الأرقام لكل ١٠٠ جم بروتين مش للحصة")

    eaa_mg = sum(aa[k] for k in EAA)
    bcaa_mg = sum(aa[k] for k in BCAA)
    out = {
        "unit": unit, "total_aa_mg": total_mg,
        "total_aa_g": total_g, "leucine_g": leucine_g,
        "total_aa_pct": total_g / serving_g * 100,
        "leucine_pct": aa["Leucine"] / total_mg * 100,
        "eaa_pct": eaa_mg / total_mg * 100,
        "bcaa_pct": bcaa_mg / total_mg * 100,
        "protein_pct": protein_g / serving_g * 100,
        "missing": [k for k in AMINO if not aa[k]],
    }
    rows = []
    for metric, key in (("total_aa", "total_aa_pct"), ("leucine", "leucine_pct"),
                        ("eaa", "eaa_pct"), ("bcaa", "bcaa_pct")):
        # ‏النقط على الرقم مقرّب لعُشر، زي ما الجدول مكتوب (84.9 مش 84.96)
        pts = points(metric, round(out[key], 1) if metric != "leucine" else round(out[key], 2))
        rows.append({"metric": metric, "value": out[key], "points": pts,
                     "max": MAX_POINTS[metric], "ideal": SCALE[metric][0][0],
                     "tier": _tier(metric, pts)})
    out["rows"] = rows
    out["score"] = sum(r["points"] for r in rows)
    out["grade"] = grade(out["score"])
    out["warnings"] = []
    if out["leucine_pct"] < 8 or out["eaa_pct"] < 35:
        out["warnings"].append("احتمال غش - Amino Spiking")
    return out


# ── قراءة النص اللي طلع من الصورة ──────────────────────────────────

_ALIASES = {
    "Alanine": r"alanine", "Arginine": r"arginine",
    "Aspartic": r"aspartic\s*acid|aspartate|aspartic",
    "Cystine": r"cystine|cysteine",
    "Glutamine": r"glutamic\s*acid|glutamine|glutamate",
    "Glycine": r"glycine", "Histidine": r"histidine", "Isoleucine": r"isoleucine",
    "Leucine": r"leucine", "Lysine": r"lysine", "Methionine": r"methionine",
    "Phenylalanine": r"phenylalanine", "Proline": r"proline", "Serine": r"serine",
    "Threonine": r"threonine", "Tryptophan": r"tryptophan", "Tyrosine": r"tyrosine",
    "Valine": r"valine",
}
_NUM = r"(\d+(?:\.\d+)?)"
_PER100 = re.compile(r"per\s*100\s*g\s*(?:of\s*)?protein|/\s*100\s*g\s*(?:of\s*)?protein|"
                     r"لكل\s*100\s*(?:جم|جرام|غ)\s*بروتين", re.I)
_PERSERVING = re.compile(r"per\s*serving|per\s*scoop|لكل\s*(?:حصة|سكوب)", re.I)


def _clean(text):
    text = str(text or "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789."))
    # ‏"10,200mg" -> "10200mg": فاصلة الآلاف. والـOCR ساعات بيقرا O مكان 0.
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    return re.sub(r"(?<=\d)[oO](?=\d|\s*m?g)", "0", text)


def parse_label(text):
    """‏الأرقام من نص ضهر العلبة. يرجّع serving_g، protein_g، amino (مللي)،
    unit، وmissing (اللي مالقاهوش -- بيتملا بالإيد)."""
    t = _clean(text)
    low = t.lower()
    out = {"serving_g": None, "protein_g": None, "amino": {}, "unit": None, "missing": []}

    m = re.search(r"serving\s*size[^\n]*?" + _NUM + r"\s*g\b", low)
    if m:
        out["serving_g"] = float(m.group(1))
    else:
        # ‏Tesseract على صورة حقيقية قرا "(31g)" كـ"(319)": الـg والـ9 شبه
        # بعض. رقم آخره 9 جوه قوس في سطر الحصة، ومن غيره الحصة مستحيلة
        # (٣١٩ جم) -> الـ9 كانت g.
        m = re.search(r"serving\s*size[^\n]*?\(\s*(\d+)9\s*\)", low)
        if m and 5 <= int(m.group(1)) <= 150:
            out["serving_g"] = float(m.group(1))
    for line in low.splitlines():
        if "protein" in line and not _PER100.search(line):
            m = re.search(r"protein[^\d\n]{0,25}" + _NUM + r"\s*g\b", line)
            if m:
                out["protein_g"] = float(m.group(1))
                break

    units = {}
    for name, alias in _ALIASES.items():
        # ‏(?<![a-z]): "alanine" جوه "phenylalanine" و"leucine" جوه "isoleucine"
        m = re.search(r"(?<![a-z])(?:" + alias + r")[^\d\n]{0,12}" + _NUM + r"\s*(mg|g)?\b", low)
        if m:
            out["amino"][name] = float(m.group(1))
            units[name] = m.group(2)
    # ‏أرقام بالجرام ("Leucine 2.7g") -> مللي. ومن غير وحدة: لو كلها صغيرة فهي جرامات.
    no_unit_small = all(v < 50 for v in out["amino"].values()) if out["amino"] else False
    for name, value in list(out["amino"].items()):
        if units.get(name) == "g" or (units.get(name) is None and no_unit_small):
            out["amino"][name] = round(value * 1000)
        else:
            out["amino"][name] = round(value)

    total_g = sum(out["amino"].values()) / 1000.0
    if _PER100.search(t):
        out["unit"] = "per100"
    elif out["serving_g"] and total_g > out["serving_g"] * 1.05:
        out["unit"] = "per100"      # ‏مجموع أكبر من الحصة: مستحيل يكون للحصة
    elif _PERSERVING.search(t):
        out["unit"] = "serving"
    else:
        out["unit"] = "per100" if total_g >= 60 else "serving"

    out["missing"] = ([k for k in ("serving_g", "protein_g") if not out[k]] +
                      [k for k in AMINO if k not in out["amino"]])
    return out

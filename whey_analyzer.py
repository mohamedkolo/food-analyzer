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


# ‏البروتين أقل من كده من الحصة يبقى المنتج مش واي: علبة Body Builder اللي
# صاحب المشروع صوّرها (نوفمبر) جينر -- ٢٢ جم بروتين في حصة ١٠٠ جم، والباقي
# مالتودكسترين. معادلات الواي هتظلمه في Total AA% وهو مش معمول عشانها.
# ‏أقل واي Concentrate بيبقى حوالي ٧٠٪، فالـ٦٠ فيها مسافة.
LOW_PROTEIN_PCT = 60


def _score(out, added=None):
    """‏النقط والتقييم والتحذيرات -- واحدة للجدول الكامل وللملخص.

    ‏معادلة رقمها مش مكتوب على العلبة (None) مابتتحسبش صفر: بتتشال، ومفيش
    تقييم نهائي من ١٠٠ -- بيبان النقط اللي اتحسبت من أصلها (points/max_score).
    علبة كاتبة EAA وBCAA بس كانت هتطلع "غير مقبول" على رقم مش موجود."""
    rows, partial = [], []
    for metric, key in (("total_aa", "total_aa_pct"), ("leucine", "leucine_pct"),
                        ("eaa", "eaa_pct"), ("bcaa", "bcaa_pct")):
        if out.get(key) is None:
            partial.append(metric)
            continue
        # ‏النقط على الرقم مقرّب، زي ما الجدول مكتوب (84.9 مش 84.96)
        pts = points(metric, round(out[key], 2 if metric == "leucine" else 1))
        rows.append({"metric": metric, "value": out[key], "points": pts,
                     "max": MAX_POINTS[metric], "ideal": SCALE[metric][0][0],
                     "tier": _tier(metric, pts)})
    out["rows"] = rows
    out["partial"] = partial
    out["points"] = sum(r["points"] for r in rows)
    out["max_score"] = sum(r["max"] for r in rows)
    out["score"] = None if partial else out["points"]
    out["grade"] = None if partial else grade(out["score"])
    out["warnings"], out["alerts"] = [], []
    leu, eaa = out.get("leucine_pct"), out.get("eaa_pct")
    if (leu is not None and leu < 8) or (eaa is not None and eaa < 35):
        out["warnings"].append("احتمال غش - Amino Spiking")
        out["alerts"].append({"key": "spiking"})
    added = [a for a in (added or []) if a]
    if added:
        out["warnings"].append(
            "المكونات فيها أحماض أمينية مضافة (%s) -- علامة Amino Spiking: بتعلّي رقم "
            "البروتين على الورق من غير بروتين حقيقي" % "، ".join(added))
        out["alerts"].append({"key": "added", "items": added})
    if out["protein_pct"] < LOW_PROTEIN_PCT:
        out["alerts"].append({"key": "low_protein"})
    out["added"] = added
    return out


def analyze(serving_g, protein_g, amino, unit="per100", added=None):
    """‏الحساب كله من جدول الأحماض. unit: "per100" (لكل ١٠٠ جم بروتين) أو "serving".

    ‏بترفع ValueError برسالة عربي لو الأرقام مستحيلة -- مايتقيّمش منتج
    على أرقام غلط.
    """
    serving_g, protein_g = _check_basics(serving_g, protein_g)
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
    out = {
        "mode": "profile", "unit": unit, "total_aa_mg": total_mg,
        "total_aa_g": total_g, "leucine_g": leucine_g,
        "total_aa_pct": total_g / serving_g * 100,
        "leucine_pct": aa["Leucine"] / total_mg * 100,
        "eaa_pct": sum(aa[k] for k in EAA) / total_mg * 100,
        "bcaa_pct": sum(aa[k] for k in BCAA) / total_mg * 100,
        "protein_pct": protein_g / serving_g * 100,
        "missing": [k for k in AMINO if not aa[k]],
    }
    return _score(out, added)


def analyze_summary(serving_g, protein_g, total_aa_g, eaa_g, bcaa_g, leucine_g, added=None):
    """‏علبة كاتبة ملخص بس (زي Dymatize: "25g total amino acids, 11.9g EAAs,
    5.5g BCAAs, leucine 2.6g") والجدول الكامل ورا QR. نفس المعادلات: النسب
    من مجموع الأحماض، والمجموع بالجرام للحصة على طول.

    ‏أي رقم ممكن يبقى مش مكتوب. علب كتير كاتبة EAA وBCAA من غير المجموع:
    ساعتها البروتين بيتاخد مكانه (approx_total) -- البروتين في الجدول هو
    مجموع الأحماض تقريبًا. وعلبة مفيهاش ولا رقم بتطلع نسبة البروتين
    والتحذيرات بس."""
    serving_g, protein_g = _check_basics(serving_g, protein_g)
    total, eaa, bcaa, leu = [float(v) if v else None for v in (total_aa_g, eaa_g, bcaa_g, leucine_g)]
    approx = total is None and any(v is not None for v in (eaa, bcaa, leu))
    if approx:
        total = protein_g
    if total is not None and total > serving_g * 1.05:
        raise ValueError("مجموع الأحماض أكبر من الحصة نفسها -- راجع الرقم")
    chain = [v for v in (leu, bcaa, eaa, total) if v is not None]
    if chain != sorted(chain):
        raise ValueError("الأرقام مش منطقية: الليوسين جوّه الـBCAA، والـBCAA جوّه الـEAA، والـEAA جوّه المجموع")

    def pct(v):
        return v / total * 100 if v is not None and total else None
    out = {
        "mode": "summary", "unit": "serving", "approx_total": approx,
        "total_aa_mg": total * 1000 if total else None,
        "total_aa_g": total, "leucine_g": leu,
        "total_aa_pct": total / serving_g * 100 if total else None,
        "leucine_pct": pct(leu), "eaa_pct": pct(eaa), "bcaa_pct": pct(bcaa),
        "protein_pct": protein_g / serving_g * 100,
        "missing": [],
    }
    return _score(out, added)


def _check_basics(serving_g, protein_g):
    serving_g = float(serving_g or 0)
    protein_g = float(protein_g or 0)
    if serving_g <= 0 or protein_g <= 0:
        raise ValueError("اكتب حجم الحصة والبروتين في الحصة")
    if protein_g > serving_g:
        raise ValueError("البروتين في الحصة أكبر من الحصة نفسها -- راجع الرقمين")
    return serving_g, protein_g


# ── قراءة النص اللي طلع من الصورة ──────────────────────────────────
#
# ‏اتجرّب على صور حقيقية صاحب المشروع صوّرها في المحل (tests/data/
# whey_ocr_real.json). Tesseract على علبة مقوّسة ولامعة وجدولها أبيض على
# أسود بيزحلق الأرقام على الأسامي اللي جنبها: "Aspartic 1748"، "Lysine
# 2200" (دي بتاعة Methionine)، "Threonine 14008" (1400mg و الـg اتقرت 8).
# ‏ورقم غلط أسوأ من خانة فاضية: بيدخل في الحساب من غير ما حد يشوفه. فالرقم
# بيتاخد بس لو:
#   ‏- بعده وحدة (mg أو g، أو أشكالها الغلط المعروفة m8/m9/mq/rng)،
#   ‏- وقيمته في حدود منطقية لجدول واي (RANGE)،
#   ‏- وقرايتين على الأقل من قرايات الصورة متفقين عليه (parse_passes).
#     اللي اتشاف في قراية واحدة بس بيرجع اقتراح (hints) مش رقم.

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
# ‏حدود منطقية بالمللي لكل حمض لوحده. لكل ١٠٠ جم بروتين: أقل حمض في الواي
# (التريبتوفان) ~١٤٠٠ وأكبرهم (الجلوتامين) ~١٨٠٠٠. للحصة (٢٠-٣٥ جم بروتين).
# ‏الحدود واسعة بالقصد: هدفها تمسك غلطة القراية (٧٠٠ مكان ٦٧٠٠)، مش تحكم
# على المنتج -- ده شغل analyze.
RANGE = {"per100": (800, 25000), "serving": (100, 8000)}
_NUM = r"(\d+(?:\.\d+)?)"
_UNIT = r"(mg|m9|m8|mq|rng|g)(?![a-z])"
_PER100 = re.compile(r"per\s*100\s*/?\s*g\s*(?:of\s*)?protein|/\s*100\s*g\s*(?:of\s*)?protein|"
                     r"لكل\s*100\s*(?:جم|جرام|غ)\s*بروتين", re.I)
_PERSERVING = re.compile(r"per\s*serving|per\s*scoop|لكل\s*(?:حصة|سكوب)", re.I)
# ‏أحماض مضافة في المكونات: ده الـAmino Spiking نفسه -- أحماض رخيصة بتتحسب
# بروتين في التحليل. بتتعدّ بس لو مش بعدها رقم (يعني في المكونات، مش في
# جدول الأحماض: "Glycine 1400mg" جدول، "L-Glycine, L-Taurine" مكونات).
_ADDED = (("Amino acid blend", r"amino\s*acids?\s*blend"), ("Glycine", r"glycine"),
          ("Glutamine", r"glutamine"), ("Taurine", r"taurine"), ("Creatine", r"creatine"))
# ‏وأي حمض تاني مكتوب "L-" في المكونات حمض حر اتضاف: جينر Body Builder
# كاتب "L-Alanine, L-Lysine" جنب الـL-Glycine. الـ"L-" شرط هنا عشان
# "alanine" جوه "phenylalanine" وعشان ده اللي بيفرق المكوّن عن اسم في الجدول.
_ADDED += tuple((n, r"l\s*-\s*" + n.lower()) for n in
                ("Alanine", "Lysine", "Arginine", "Leucine", "Isoleucine", "Valine",
                 "Serine", "Proline", "Threonine", "Histidine", "Methionine"))


def _clean(text):
    text = str(text or "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789."))
    # ‏"10,200mg" -> "10200mg": فاصلة الآلاف. والـOCR ساعات بيقرا O مكان 0.
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    return re.sub(r"(?<=\d)[oO](?=\d|\s*m?g)", "0", text)


def _basics(low):
    serving = protein = None
    m = re.search(r"serving\s*size[^\n]*?" + _NUM + r"\s*g\b", low)
    if m:
        serving = float(m.group(1))
    else:
        # ‏Tesseract قرا "(31g)" كـ"(319)": الـg والـ9 شبه بعض. رقم آخره 9
        # جوه قوس في سطر الحصة، ومن غيره الحصة مستحيلة -> الـ9 كانت g.
        m = re.search(r"serving\s*size[^\n]*?\(\s*(\d+)9\s*\)", low)
        if m and 5 <= int(m.group(1)) <= 150:
            serving = float(m.group(1))
    if serving is not None and not (5 <= serving <= 150):
        serving = None
    for line in low.splitlines():
        if "protein" in line and not _PER100.search(line):
            m = re.search(r"protein[^\d\n]{0,25}" + _NUM + r"\s*g\b", line)
            if m and 3 <= float(m.group(1)) <= 100:
                protein = float(m.group(1))
                break
    return serving, protein


def _amino_raw(low):
    """‏{اسم: مللي} من سطر واحد من غير حكم على الوحدة."""
    found = {}
    for name, alias in _ALIASES.items():
        # ‏(?<![a-z]): "alanine" جوه "phenylalanine" و"leucine" جوه "isoleucine"
        m = re.search(r"(?<![a-z])(?:" + alias + r")(?![a-z])[^\d\n]{0,12}?" + _NUM + r"\s*" + _UNIT, low)
        if m:
            value = float(m.group(1))
            found[name] = round(value * 1000) if m.group(2) == "g" else round(value)
    return found


def _added(low):
    tail = low
    m = re.search(r"ingr|redient", low)
    if m:
        tail = low[m.start():]
    out = []
    for label, rx in _ADDED:
        for hit in re.finditer(r"(?<![a-z])" + rx, tail):
            after = tail[hit.end():hit.end() + 14]
            if not re.search(r"\d", after) or label == "Taurine":
                out.append(label)
                break
    return out


def _summary(low, amino):
    def grab(rx):
        m = re.search(_NUM + r"\s*g\s*" + rx, low)
        return float(m.group(1)) if m else None
    total = grab(r"total\s*amino")
    if not total:
        return None
    leu = amino.get("Leucine")
    return {"total_aa_g": total, "eaa_g": grab(r"eaas?(?![a-z])"),
            "bcaa_g": grab(r"bcaas?(?![a-z])"),
            "leucine_g": (leu / 1000.0) if leu and leu < 10000 else None}


def _unit(text, serving, amino):
    total_g = sum(amino.values()) / 1000.0
    if _PER100.search(text):
        return "per100"
    if serving and total_g > serving * 1.05:
        return "per100"      # ‏مجموع أكبر من الحصة: مستحيل يكون للحصة
    if amino and max(amino.values()) > RANGE["serving"][1]:
        return "per100"      # ‏حمض واحد أكتر من ٨ جم: مايبقاش في حصة واحدة
    if _PERSERVING.search(text):
        return "serving"
    return "per100" if total_g >= 60 else "serving"


# ‏حمض واحد مايبقاش أغلب البروتين: في الواي أكبر حمض (الليوسين) ~١١٪ من
# البروتين، والجلوتامين والأسبارتيك أكتر شوية. اتقاس على صورة Dymatize:
# "Valine 5000" (٢٠٪ من ٢٥ جم بروتين) والصح ١.٤ جم -- الـ5 جاية من "5.5g
# BCAAs" جنبه. الجلايسين معاهم عشان العلب "المنفوخة" بيطبعوه عالي.
_SHARE = 0.14
_BIG_SHARE = {"Glutamine": 0.25, "Aspartic": 0.25, "Glycine": 0.25}


def _cap(name, unit, protein_g):
    share = _BIG_SHARE.get(name, _SHARE)
    if unit == "per100":
        return 100000 * share          # ‏مللي لكل ١٠٠ جم بروتين
    if protein_g:
        return protein_g * 1000 * share
    return RANGE[unit][1]


def _in_range(amino, unit, protein_g=None):
    lo, hi = RANGE[unit]
    return {k: v for k, v in amino.items() if lo <= v <= min(hi, _cap(k, unit, protein_g))}


def _finish(out):
    out["missing"] = ([k for k in ("serving_g", "protein_g") if not out[k]] +
                      [k for k in AMINO if k not in out["amino"]])
    out["no_profile"] = not out["amino"] and not out.get("hints") and not out.get("summary")
    return out


def parse_label(text):
    """‏قراية واحدة: الأرقام من نص ضهر العلبة. يرجّع serving_g، protein_g،
    amino (مللي)، unit، summary (لو العلبة كاتبة ملخص)، added (أحماض مضافة
    في المكونات)، hints، وmissing (اللي يتملا بالإيد)."""
    t = _clean(text)
    low = t.lower()
    serving, protein = _basics(low)
    raw = _amino_raw(low)
    unit = _unit(t, serving, raw)
    # ‏البروتين مش متقري؟ الحصة حد أعلى ليه (البروتين جوّه الحصة)
    amino = _in_range(raw, unit, protein or serving)
    return _finish({"serving_g": serving, "protein_g": protein, "amino": amino, "unit": unit,
                    "summary": _summary(low, raw), "added": _added(low), "hints": {}})


def parse_passes(passes):
    """‏كذا قراية لنفس الصورة (عادية، متحسّنة، ألوانها معكوسة). الرقم بيتاخد
    لو قرايتين متفقين عليه؛ اللي اتشاف مرة واحدة بس بيبقى اقتراح."""
    passes = [p for p in (passes or []) if p is not None]
    if len(passes) <= 1:
        return parse_label(passes[0] if passes else "")
    reads = [parse_label(p) for p in passes]
    whole = _clean("\n".join(passes))
    out = {"amino": {}, "hints": {}, "summary": None, "added": []}

    def vote(values):
        values = [v for v in values if v is not None]
        for v in values:
            if values.count(v) >= 2:
                return v, None
        return None, (values[0] if len(set(values)) == 1 else None)

    for key in ("serving_g", "protein_g"):
        out[key], hint = vote([r[key] for r in reads])
        if hint is not None:
            out["hints"][key] = hint
    raw = {}
    for text in passes:
        for k, v in _amino_raw(_clean(text).lower()).items():
            raw.setdefault(k, []).append(v)
    unit = _unit(whole, out["serving_g"] or out["hints"].get("serving_g"),
                 {k: v[0] for k, v in raw.items()})
    protein = (out["protein_g"] or out["hints"].get("protein_g")
               or out["serving_g"] or out["hints"].get("serving_g"))
    lo, hi = RANGE[unit]
    for k, vals in raw.items():
        vals = [v for v in vals if lo <= v <= min(hi, _cap(k, unit, protein))]
        val, hint = vote(vals)
        if val is not None:
            out["amino"][k] = val
        elif hint is not None:
            out["hints"][k] = hint
    out["unit"] = unit
    out["summary"] = next((r["summary"] for r in reads if r["summary"]), None)
    for r in reads:
        out["added"] += [a for a in r["added"] if a not in out["added"]]
    return _finish(out)

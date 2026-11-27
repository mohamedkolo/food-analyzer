# -*- coding: utf-8 -*-
"""Suggestions shown while the doctor types a food name.

Only rows whose identity is source-qualified are offered: the named cooked options (meal_option_foods) and the library rows
whose source was reviewed against USDA (food_provenance.REVIEWED). Each suggestion says what it is (USDA description and
preparation) and its per-100 g values, so the choice is explicit. Choosing one only puts its name in the text box; the amount in
grams (after cooking) is typed by the doctor, and nothing is replaced or saved until the doctor saves the line as usual.
"""
import re

MAX = 8

# Arabic wording for each preparation note shown to the doctor (the English USDA text stays in "usda"/"basis" for the record).
BASIS_AR = {
    "breaded and fried": "مقلي بالبقسماط",
    "cooked": "مطبوخ",
    "cooked (roasted, meat and skin)": "مطبوخ مشوي، لحم مع الجلد",
    "cooked weight, dry heat": "الوزن بعد الطبخ، حرارة جافة (شوي/فرن)",
    "cooked weight, hard-boiled, whole egg without shell (100 g = about 2 large eggs)": "الوزن بعد السلق، بدون القشر (100 جم تقريبًا بيضتين كبار)",
    "cooked weight, moist heat": "الوزن بعد الطبخ، بالبخار/السلق",
    "cooked weight, moist heat; Alaska king crab, species may differ from the one meant": "الوزن بعد الطبخ بالبخار، كابوريا ألاسكا (النوع قد يختلف)",
    "cooked weight, pan-fried": "الوزن بعد الطبخ، مقلي في المقلاة",
    "cooked weight, roasted, meat only (no skin, no bone)": "الوزن بعد الشوي، لحم فقط بدون جلد وعظم",
    "cooked weight": "الوزن بعد الطبخ",
    "cooked (stewed, meat and skin)": "مطبوخ مطهي، لحم مع الجلد",
    "cooked (stewed, meat only)": "مطبوخ مطهي، لحم فقط",
    "nonfat milk, as sold": "حليب خالي الدسم",
    "whole milk, as sold": "حليب كامل الدسم",
    "cooked, boiled, without salt": "مسلوق بدون ملح",
    "cooked, dry heat": "مطبوخ بحرارة جافة",
    "dried seeds": "بذور جافة",
    "nuts, as sold": "مكسرات كما تُباع",
    "olive oil, as sold": "زيت زيتون",
    "plain whole-milk yogurt, as sold": "زبادي سادة كامل الدسم",
    "raw": "نيّء",
    "raw, with peel": "نيّء بقشره",
    "raw, with skin": "نيّء بجلده",
    "smoked as sold (lox)": "مدخن كما يُباع",
}
_AMOUNT = re.compile(r"^[\s\d\.\u0660-\u0669٫,/]*(?:جم|جرام|غ|g|gm|gram|grams)?\s*", re.I)


def split_query(text):
    """The part of the line being typed: after the last '+' or line break, without the leading amount."""
    seg = re.split(r"[+\n،]", str(text or ""))[-1]
    return _AMOUNT.sub("", seg, count=1).strip()


def _catalog():
    import food_data
    import food_provenance as P
    import meal_option_foods as O
    rows = []
    for f in O.OPTION_FOODS:
        rows.append({"text": f["n"], "also": [f.get("option_for", ""), f.get("en", "")], "usda": f["usda"], "fdc": f["fdc"], "basis": f["basis"],
                     "kind": "option", "per100": [f["cal"], f["p"], f["c"], f["f"]]})
    for f in food_data.FOODS:
        r = P.REVIEWED.get(f.get("n"))
        if r:
            rows.append({"text": f["n"], "also": [f.get("en", "")], "usda": r[1], "fdc": int(r[0]), "basis": r[2],
                         "kind": "verified", "per100": [r[3], r[4], r[5], r[6]]})
    return rows


_CAT = None


def suggest(text):
    global _CAT
    from meal_macros import _norm
    q = _norm(split_query(text))
    if len(q) < 2:
        return []
    if _CAT is None:
        _CAT = _catalog()
    out = []
    for r in _CAT:
        hay = [_norm(r["text"])] + [_norm(a) for a in r["also"] if a]
        # a word must START with what was typed ("بيض" must not match "أبيض")
        pos = [m.start() for h in hay for m in [re.search(r"(?:^|[\s(\-/])" + re.escape(q), h)] if m]
        if pos:
            out.append((min(pos), len(r["text"]), r))
    out.sort(key=lambda x: (x[0], x[1]))
    return [dict(r, basis_ar=BASIS_AR.get(r["basis"], ""), label_en=("named USDA option" if r["kind"] == "option" else "reviewed USDA source"), label=("خيار مسمّى من USDA" if r["kind"] == "option" else "مصدر USDA مراجَع"))
            for _, _, r in out[:MAX]]

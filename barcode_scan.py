# -*- coding: utf-8 -*-
"""‏الباركود: من صورة لرقم (zxing-cpp)، ومن رقم لمنتج (Open Food Facts).

‏ليه الصورة بتتقرا على السيرفر مش في المتصفح: صاحب المشروع على آيفون،
وSafari مفيهوش BarcodeDetector. zxing-cpp عجلة جاهزة من غير مكتبات نظام،
فبتتركّب على Render بـpip زي أي حاجة في requirements.txt.

‏Open Food Facts بيملاه مستخدمين: اللي مش مكتوب يفضل None، مش صفر (زي
_barcode_food في app.py). وأرقامه لكل ١٠٠ جم بتتحوّل للحصة بس لو حجم
الحصة معروف.
"""

import io
import json
import re
import urllib.request
import urllib.error

_OFF = "https://world.openfoodfacts.org/api/v2/product/%s.json"
# ‏Open Food Facts بيطلب من أي برنامج يعرّف نفسه في الـUser-Agent
_UA = "NutraX-FoodAnalyzer/1.0 (contact: admin@nutrax.com)"
MAX_BYTES = 8 * 1024 * 1024


def clean_code(code):
    return re.sub(r"\D", "", str(code or ""))[:20]


def decode(image_bytes):
    """‏رقم أول باركود منتجات (EAN/UPC) في الصورة، أو None."""
    if not image_bytes or len(image_bytes) > MAX_BYTES:
        return None
    try:
        import zxingcpp
        from PIL import Image, ImageOps
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
        # ‏صورة الموبايل ٤٠٠٠ بكسل: أبطأ من غير فايدة لخطوط الباركود
        img.thumbnail((1600, 1600))
        found = zxingcpp.read_barcodes(img)
    except Exception:  # noqa: BLE001 -- صورة بايظة أو المكتبة مش متركّبة: مفيش رقم
        return None
    for b in found:
        code = clean_code(b.text)
        if len(code) in (8, 12, 13, 14):
            return code
    return None


def fetch_product(code):
    """‏المنتج من Open Food Facts، أو None لو مش موجود. غلطة الشبكة بتطلع Exception."""
    req = urllib.request.Request(_OFF % clean_code(code), headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    if data.get("status") != 1 or not data.get("product"):
        return None
    return data["product"]


def _num(value):
    try:
        v = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return v if v >= 0 else None


def supplement_fields(product):
    """‏اللي ينفع يتملا في محلل المكملات: الاسم، الحصة، البروتين والسكر للحصة،
    والأحماض المضافة من المكونات. جدول الأحماض مش في Open Food Facts --
    لازم صورة ضهر العلبة."""
    import whey_analyzer as W
    nutr = product.get("nutriments") or {}
    serving = _num(product.get("serving_quantity"))
    if serving is not None and not (1 <= serving <= 300):
        serving = None

    def per_serving(key):
        v = _num(nutr.get(key + "_serving"))
        if v is None and serving:
            per100 = _num(nutr.get(key + "_100g"))
            v = round(per100 * serving / 100, 1) if per100 is not None else None
        return v if v is None or not serving or v <= serving else None

    name = " ".join(x for x in (product.get("brands", "").split(",")[0].strip(),
                                product.get("product_name") or "") if x).strip()
    return {"name": name, "serving_g": serving, "protein_g": per_serving("proteins"),
            "sugar_g": per_serving("sugars"),
            "added": W._added("ingredients: " + (product.get("ingredients_text") or "").lower())}


# ── أوميجا ٣: EPA/DHA من قاعدة NIH DSLD (مجانية، من غير مفتاح) ────────────
# ‏نفس الباركود ممكن يبقى له أكتر من تركيبة (علبة قديمة وعلبة جديدة). فمفيش
# "الأحدث بيكسب": بنرجّع كل تركيبة بتاريخها وحجم حصتها ورابطها، والمستخدم
# هو اللي يختار. الرقم اللي مش على الملصق بيفضل None، مش صفر.

_DSLD = "https://api.ods.od.nih.gov/dsld/v9/"
DSLD_LABEL_URL = "https://dsld.od.nih.gov/label/%s"
_DSLD_MAX_LABELS = 8


def _dsld_get(path, **query):
    from urllib.parse import urlencode
    url = _DSLD + path + ("?" + urlencode(query) if query else "")
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())


def _upc_label_form(code):
    """‏EAN-13 بصفر في الأول أو UPC-A -> "0 39442 03058 0" (شكل DSLD)."""
    c = clean_code(code)
    if len(c) == 13 and c.startswith("0"):
        c = c[1:]
    if len(c) != 12:
        return None
    return "%s %s %s %s" % (c[0], c[1:6], c[6:11], c[11])


def _dsld_rows(rows):
    for r in rows or []:
        yield r
        yield from _dsld_rows(r.get("nestedRows"))


def _dsld_mg(label, names):
    for r in _dsld_rows(label.get("ingredientRows")):
        if (r.get("name") or "").strip().lower() in names:
            for q in r.get("quantity") or []:
                try:
                    amount = float(q.get("quantity"))
                except (TypeError, ValueError):
                    continue
                unit = (q.get("unit") or "").strip().lower()
                if amount > 0 and unit == "mg":
                    return amount
                if amount > 0 and unit in ("gram(s)", "g"):
                    return amount * 1000
    return None


def _dsld_serving(label):
    out = []
    for s in label.get("servingSizes") or []:
        lo, hi, unit = s.get("minQuantity"), s.get("maxQuantity"), s.get("unit") or ""
        if lo is None:
            continue
        out.append(("%g" % lo if lo == hi or hi is None else "%g-%g" % (lo, hi)) + " " + unit)
    return "; ".join(out)


def _dsld_entered(label):
    dates = [e.get("date") for e in label.get("events") or []
             if "entered" in (e.get("type") or "").lower() and e.get("date")]
    return min(dates) if dates else None


def omega_candidates(code, others=None):
    """‏كل تركيبات أوميجا ٣ المتسجلة على نفس الباركود بالظبط، الأحدث أولًا.
    كل واحدة: epa_mg، dha_mg (None لو مش على الملصق)، الاسم، تاريخ التسجيل،
    الحصة، رقم الملصق ورابطه. الملصقات المتطابقة في الأرقام بتتدمج. بترفع
    Exception لو الشبكة وقعت (المنادي يقول ده بوضوح بدل ما يسكت).
    others: لو اتبعتت list، بتتملا بالملصقات التانية على نفس الباركود اللي مفيهاش
    صف EPA/DHA منفصل (اسم وتاريخ بس)، عشان الواجهة تقول إنها موجودة."""
    upc = _upc_label_form(code)
    if not upc:
        return []
    hits = _dsld_get("search-filter", q='"%s"' % upc).get("hits") or []
    hits.sort(key=lambda h: str((h.get("_source") or {}).get("entryDate") or ""), reverse=True)
    groups = {}
    for h in hits[:_DSLD_MAX_LABELS]:
        label = _dsld_get("label/" + str(h["_id"]))
        if label.get("upcSku") != upc:        # ‏نفس الباركود بالظبط بس
            continue
        epa = _dsld_mg(label, ("eicosapentaenoic acid", "epa"))
        dha = _dsld_mg(label, ("docosahexaenoic acid", "dha"))
        if epa is None and dha is None:
            if others is not None:
                others.append({"label_name": label.get("fullName"), "entered": _dsld_entered(label),
                               "label_id": label.get("id"), "url": DSLD_LABEL_URL % label.get("id"),
                               "serving": _dsld_serving(label)})
            continue
        serving = _dsld_serving(label)
        key = (epa, dha, serving)
        entered = _dsld_entered(label)
        c = groups.setdefault(key, {
            "epa_mg": epa, "dha_mg": dha, "serving": serving,
            "label_name": label.get("fullName"), "entered": entered,
            "label_id": label.get("id"), "url": DSLD_LABEL_URL % label.get("id"),
            "same_numbers_labels": 0})
        c["same_numbers_labels"] += 1
        if (entered or "") > (c["entered"] or ""):
            c.update(entered=entered, label_id=label.get("id"), url=DSLD_LABEL_URL % label.get("id"),
                     label_name=label.get("fullName"))
    return sorted(groups.values(), key=lambda c: c["entered"] or "", reverse=True)


def mark_name_match(candidates, product_name):
    """‏"Animal Advanced Omega" في DSLD = "Animal Advanced Omega …" في Open Food Facts:
    علامة 'name_matches' للعرض بس. مش بتملا حاجة لوحدها."""
    norm = lambda x: " ".join(re.findall(r"[a-z0-9]+", (x or "").lower()))
    full = " " + norm(product_name) + " "
    for c in candidates:
        name = norm(c.get("label_name"))
        c["name_matches"] = bool(name) and (" " + name + " ") in full   # ‏عبارة متتالية، مش كلمات متفرقة
    return candidates

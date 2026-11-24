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

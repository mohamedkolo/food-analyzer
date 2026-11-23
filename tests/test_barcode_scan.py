# -*- coding: utf-8 -*-
"""‏تصوير الباركود: في محلل المكملات وفي محلل الطعام.

‏صاحب المشروع على آيفون (Safari)، ومفيهوش BarcodeDetector في المتصفح.
فالصورة بتتبعت للسيرفر، وzxing-cpp بيطلّع الرقم، وOpen Food Facts بيجيب
المنتج. محلل الطعام كان بيطلب الرقم مكتوب بالإيد بس.

Run with:  python3 tests/test_barcode_scan.py
"""

import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_barcode_scan_test.db"

import app as A          # noqa: E402
import barcode_scan as B  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO = os.path.join(HERE, "data", "barcode_ean13.jpg")   # ‏مايل ومغبّش شوية


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_off(product, seen=None):
    def urlopen(req, timeout=None):
        if seen is not None:
            seen.append((req.full_url, dict(req.header_items())))
        if product is None:
            return _Resp(json.dumps({"status": 0}).encode())
        return _Resp(json.dumps({"status": 1, "product": product}).encode())
    return urlopen


def _with_off(product, fn, seen=None):
    real = B.urllib.request.urlopen
    B.urllib.request.urlopen = _fake_off(product, seen)
    try:
        return fn()
    finally:
        B.urllib.request.urlopen = real


WHEY = {"product_name": "Iso Whey Zero", "brands": "Body Builder", "serving_quantity": "28.5",
        "nutriments": {"proteins_serving": 25, "sugars_serving": 0.4, "proteins_100g": 87.7},
        "ingredients_text": "Whey Protein Isolate, Amino Acid Blend (L-Glycine, L-Taurine), Cocoa"}


def test_a_photo_of_a_barcode_gives_its_number():
    assert B.decode(open(PHOTO, "rb").read()) == "6221024240195"
    assert B.decode(b"not an image") is None


def test_the_server_reads_a_barcode_photo():
    c = A.app.test_client()
    r = c.post("/barcode/read", data={"image": (open(PHOTO, "rb"), "b.jpg", "image/jpeg")},
               content_type="multipart/form-data")
    assert r.status_code == 200 and r.get_json()["code"] == "6221024240195", r.get_json()
    r = c.post("/barcode/read", data={"image": (io.BytesIO(b"x" * 50), "b.jpg", "image/jpeg")},
               content_type="multipart/form-data")
    assert r.status_code == 422 and not r.get_json()["ok"]


def test_a_supplement_barcode_fills_what_open_food_facts_knows():
    seen = []
    got = _with_off(WHEY, lambda: A.app.test_client().get("/whey/barcode/6221024240195").get_json(), seen)
    assert got["ok"], got
    p = got["product"]
    assert p["name"] == "Body Builder Iso Whey Zero" and p["serving_g"] == 28.5 and p["protein_g"] == 25, p
    assert p["sugar_g"] == 0.4 and {"Amino acid blend", "Glycine", "Taurine"} <= set(p["added"]), p
    url, headers = seen[0]
    assert "6221024240195" in url and "NutraX" in headers.get("User-agent", ""), seen


def test_per_100g_values_become_per_serving():
    prod = {"product_name": "Gainer", "serving_quantity": 100,
            "nutriments": {"proteins_100g": 22, "sugars_100g": 6.7}}
    p = _with_off(prod, lambda: A.app.test_client().get("/whey/barcode/123456789012").get_json())["product"]
    assert p["protein_g"] == 22 and p["sugar_g"] == 6.7, p
    # ‏من غير حجم حصة مفيش تحويل -- رقم لكل ١٠٠ جم مايتحطش في خانة الحصة
    prod = {"product_name": "X", "nutriments": {"proteins_100g": 80}}
    p = _with_off(prod, lambda: A.app.test_client().get("/whey/barcode/123456789012").get_json())["product"]
    assert p["protein_g"] is None and p["serving_g"] is None, p


def test_an_unknown_barcode_is_said_plainly():
    r = _with_off(None, lambda: A.app.test_client().get("/whey/barcode/123456789012"))
    assert r.status_code == 404 and not r.get_json()["ok"]
    r = A.app.test_client().get("/whey/barcode/abc")
    assert r.status_code == 400


def test_the_supplement_page_offers_the_barcode_after_the_type():
    html = A.app.test_client().get("/whey?kind=whey").get_data(as_text=True)
    assert re.search(r'<input[^>]*id="wyCode"[^>]*type="file"|<input[^>]*type="file"[^>]*id="wyCode"', html)
    assert re.search(r'<input[^>]*id="wyCodeNum"', html) and 'for="wyCodeNum"' in html


def test_the_food_analyzer_can_photograph_a_barcode():
    from datetime import datetime
    from werkzeug.security import generate_password_hash
    if not A.db_row("SELECT id FROM users WHERE email='bcscan@x.test'"):
        A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) VALUES (?,?,?,'admin',1,?)",
                 ("أدمن", "bcscan@x.test", generate_password_hash("pw123456"), datetime.now()))
    c = A.app.test_client()
    c.post("/login", data={"action": "login", "email": "bcscan@x.test", "password": "pw123456"})
    html = c.get("/analyzer").get_data(as_text=True)
    assert re.search(r'<input[^>]*type="file"[^>]*id="barcodePhoto"[^>]*capture="environment"', html), \
        "محلل الطعام لسه بيطلب الرقم بالإيد بس"
    assert "/barcode/read" in html


def test_the_creatine_form_does_not_assume_monohydrate():
    """‏أول اختيار في القايمة كان Monohydrate: اللي ماختارش حاجة كان بياخد
    "كويس" على نوع مش مكتوب على العلبة."""
    html = A.app.test_client().get("/whey?kind=creatine").get_data(as_text=True)
    first = re.search(r'<select[^>]*name="form"[^>]*>\s*<option value="([^"]*)"', html)
    assert first and first.group(1) == "", "أول اختيار في القايمة نوع كرياتين"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, "--", repr(e)[:300])
    print("\n%d passed, %d failed" % (len(tests) - failed, failed))
    sys.exit(1 if failed else 0)

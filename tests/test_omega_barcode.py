# -*- coding: utf-8 -*-
"""‏باركود أوميجا ٣: EPA/DHA من ملصقات NIH DSLD، من غير تخمين.

‏الباركود 039442030580 (Animal) عليه ٦ ملصقات في DSLD وتركيبتين مختلفتين:
القديمة (EPA 450 / DHA 350 في النسخة المكتوبة نص) والجديدة "Advanced Omega"
(EPA 1055 / DHA 769). فمفيش "الأحدث بيكسب" ولا ملا صامت: الواجهة بتعرض
الاختيارات والمستخدم يختار. الاختبارات مابتنادّيش الشبكة: بتشغّل ردود DSLD
الحقيقية المحفوظة في tests/data/dsld_animal_omega.json.

Run with:  python3 tests/test_omega_barcode.py
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_omega_barcode_test.db"

import app as A           # noqa: E402
import barcode_scan as B  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "data", "dsld_animal_omega.json"), encoding="utf-8"))
OFF = {"product_name": "Advanced Omega Omega-3 & Efas", "brands": "Animal", "nutriments": {}}


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _urlopen(dsld="ok", off=OFF):
    def fake(req, timeout=None):
        url = req.full_url
        if "openfoodfacts" in url:
            return _Resp(json.dumps({"status": 1, "product": off} if off else {"status": 0}).encode())
        if dsld == "down":
            raise OSError("down")
        if "search-filter" in url:
            return _Resp(json.dumps({"hits": FIX["hits"] if dsld == "ok" else []}).encode())
        return _Resp(json.dumps(FIX["labels"][url.rsplit("/", 1)[1]]).encode())
    return fake


def _get(url, **kw):
    real = B.urllib.request.urlopen
    B.urllib.request.urlopen = _urlopen(**kw)
    try:
        return A.app.test_client().get(url)
    finally:
        B.urllib.request.urlopen = real


def test_only_labels_with_epa_dha_rows_are_candidates_and_the_rest_are_listed():
    j = _get("/whey/barcode/039442030580?kind=omega3").get_json()
    c = j["omega_candidates"]
    assert [(x["epa_mg"], x["dha_mg"]) for x in c] == [(1055.0, 769.0)], c
    x = c[0]
    assert x["label_name"] == "Animal Advanced Omega" and x["entered"] == "2024-11-22", x
    assert x["url"] == "https://dsld.od.nih.gov/label/319467" and x["serving"], x
    assert x["name_matches"] is True, x           # ‏OFF: "Animal Advanced Omega..."
    others = j["omega_other_labels"]
    assert len(others) == 5 and all(o["label_name"] == "Animal Omega" and o["serving"] for o in others), others


def test_two_formulas_with_different_numbers_both_come_back():
    labels = json.loads(json.dumps(FIX["labels"]))
    old = labels["246134"]
    rows = old["ingredientRows"]
    rows.append({"name": "Eicosapentaenoic Acid", "quantity": [{"quantity": 450, "unit": "mg"}]})
    rows.append({"name": "Docosahexaenoic Acid", "quantity": [{"quantity": 350, "unit": "mg"}]})
    saved = dict(FIX["labels"]); FIX["labels"].update(labels)
    try:
        c = _get("/whey/barcode/039442030580?kind=omega3").get_json()["omega_candidates"]
    finally:
        FIX["labels"].update(saved)
    assert [(x["epa_mg"], x["dha_mg"]) for x in c] == [(1055.0, 769.0), (450.0, 350.0)], c
    assert c[0]["name_matches"] and not c[1]["name_matches"], c   # ‏الواجهة مش بتملا لوحدها لما فيه اتنين


def test_fish_oil_is_never_invented():
    j = _get("/whey/barcode/039442030580?kind=omega3").get_json()
    assert all("oil_mg" not in x for x in j["omega_candidates"])
    assert "oil_mg" not in j["product"]


def test_other_supplement_kinds_do_not_call_dsld():
    seen = []
    real = B.urllib.request.urlopen
    inner = _urlopen()
    B.urllib.request.urlopen = lambda req, timeout=None: (seen.append(req.full_url), inner(req, timeout))[1]
    try:
        j = A.app.test_client().get("/whey/barcode/039442030580").get_json()
    finally:
        B.urllib.request.urlopen = real
    assert j["ok"] and "omega_candidates" not in j
    assert not any("nih.gov" in u for u in seen), seen


def test_a_barcode_dsld_does_not_know_gives_no_candidates():
    j = _get("/whey/barcode/039442030580?kind=omega3", dsld="none").get_json()
    assert j["ok"] and j["omega_candidates"] == [] and j["omega_source_error"] is False


def test_dsld_down_is_said_and_the_rest_still_works():
    j = _get("/whey/barcode/039442030580?kind=omega3", dsld="down").get_json()
    assert j["ok"] and j["omega_candidates"] == [] and j["omega_source_error"] is True
    assert j["product"]["name"].startswith("Animal")


def test_a_label_for_another_barcode_is_ignored():
    labels = json.loads(json.dumps(FIX["labels"]))
    for l in labels.values():
        l["upcSku"] = "9 99999 99999 9"
    real = dict(FIX["labels"]); FIX["labels"].update(labels)
    try:
        assert B.omega_candidates.__name__
        real_open = B.urllib.request.urlopen
        B.urllib.request.urlopen = _urlopen()
        try:
            assert B.omega_candidates("039442030580") == []
        finally:
            B.urllib.request.urlopen = real_open
    finally:
        FIX["labels"].update(real)


def test_ean13_with_leading_zero_maps_to_the_dsld_form():
    assert B._upc_label_form("0039442030580") == "0 39442 03058 0"
    assert B._upc_label_form("039442030580") == "0 39442 03058 0"
    assert B._upc_label_form("123") is None


def test_the_page_makes_the_user_pick_when_formulas_differ():
    html = A.app.test_client().get("/whey?kind=omega3").get_data(as_text=True)
    assert "?kind=omega3" in html and "omegaFromLabels" in html
    assert "setVal('epa_mg', c.epa_mg)" in html and "b => { setVal" in html
    assert "cands.length === 1" not in html     # ‏مفيش ملا تلقائي حتى لو نسخة واحدة


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

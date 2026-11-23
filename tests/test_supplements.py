# -*- coding: utf-8 -*-
"""‏محلل المكملات: نوع المنتج الأول، وبعدين الصورة، وبعدين التقييم.

‏صاحب المشروع طلب يفصل Isolate عن Whey عن Mass، ويختار النوع قبل ما
يصوّر، ويضيف باقي المكملات (كرياتين، أوميجا ٣، مالتي فيتامين، بري وورك
أوت، EAA/BCAA). معادلات الواي بتاعته زي ما هي. باقي المكملات مالهاش
درجة من ١٠٠: كل بند ليه قاعدة من مصدر (docs/supplements-sources.md)،
ونتيجته كويس / ملاحظة / مش كويس، والحكم النهائي أسوأ بند.

Run with:  python3 tests/test_supplements.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_supp_test.db"

import app as A               # noqa: E402
import supplements as SP      # noqa: E402
import whey_analyzer as W     # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False


def _status(res, key):
    return next(c["status"] for c in res["checks"] if c["key"] == key)


# ── اختيار النوع قبل الصورة ─────────────────────────────────────────

def test_the_type_is_chosen_before_the_photo():
    html = A.app.test_client().get("/whey").get_data(as_text=True)
    for kind in ("isolate", "whey", "mass", "creatine", "omega3", "multi", "preworkout", "eaa"):
        assert 'href="/whey?kind=%s"' % kind in html, kind
    assert 'type="file"' not in html, "الكاميرا ظهرت قبل اختيار النوع"


def test_a_whey_type_shows_the_camera_and_the_amino_form():
    html = A.app.test_client().get("/whey?kind=isolate").get_data(as_text=True)
    assert re.search(r'<input[^>]*type="file"[^>]*capture="environment"', html)
    assert re.search(r'<input[^>]*name="kind"[^>]*value="isolate"', html)
    assert re.search(r'<input[^>]*name="Leucine"', html)


def test_a_supplement_type_shows_its_own_fields():
    html = A.app.test_client().get("/whey?kind=creatine").get_data(as_text=True)
    assert re.search(r'<input[^>]*type="file"', html)
    assert re.search(r'<input[^>]*name="creatine_g"', html) and 'name="Leucine"' not in html
    # ‏كل حقل ليه label (اختبارات الشكل في المشروع)
    for m in re.finditer(r'<(?:input|select)[^>]*id="(sp_[a-z0-9_]+)"', html):
        assert 'for="%s"' % m.group(1) in html, m.group(1)


def test_an_unknown_type_goes_back_to_the_picker():
    html = A.app.test_client().get("/whey?kind=nope").get_data(as_text=True)
    assert 'type="file"' not in html and 'href="/whey?kind=whey"' in html


# ── Isolate / Whey / Mass ───────────────────────────────────────────

def test_an_isolate_with_too_little_protein_is_called_out():
    r = W.analyze(31, 22, W.DEMO["amino"], "per100", kind="isolate")
    assert "not_isolate" in [a["key"] for a in r["alerts"]], r["alerts"]
    r = W.analyze(31, 28, W.DEMO["amino"], "per100", kind="isolate")
    assert "not_isolate" not in [a["key"] for a in r["alerts"]]
    r = W.analyze(31, 22, W.DEMO["amino"], "per100", kind="whey")
    assert "not_isolate" not in [a["key"] for a in r["alerts"]]


def test_a_mass_gainer_is_judged_on_its_protein_only():
    r = W.analyze_summary(100, 22, None, 9.9, 5.085, 2.155, kind="mass", sugar_g=30)
    assert [x["metric"] for x in r["rows"]] == ["leucine", "eaa", "bcaa"], r["rows"]
    assert r["score"] is None and r["points"] == 64 and r["max_score"] == 70
    keys = [a["key"] for a in r["alerts"]]
    assert "low_protein" not in keys and "sugar" in keys, keys
    r = W.analyze_summary(100, 22, None, 9.9, 5.085, 2.155, kind="mass", sugar_g=10)
    assert "sugar" not in [a["key"] for a in r["alerts"]]


def test_the_whey_form_carries_the_type():
    c = A.app.test_client()
    html = c.post("/whey", data={"kind": "mass", "mode": "summary", "serving_g": "100", "protein_g": "22",
                                 "eaa_g": "9.9", "bcaa_g": "5.085", "leucine_g": "2.155",
                                 "sugar_g": "30"}).get_data(as_text=True)
    # ‏الجينر مابيتحذّرش إنه جينر -- صاحبه اختاره كده
    assert "64/70" in html and "غالباً Mass Gainer مش واي" not in html
    assert re.search(r'name="kind"[^>]*value="mass"', html)


def test_an_empty_amino_table_still_gives_what_is_known():
    """‏صاحب المشروع اختار ماس جينر ودوس احسب بالحصة والبروتين بس (الفورم
    على "جدول الأحماض كامل" افتراضيًا) -- طلعله "مفيش أرقام للأحماض
    الأمينية" ومفيش نتيجة خالص. اللي معروف يتعرض: نسبة البروتين والسكر
    والمكونات."""
    html = A.app.test_client().post("/whey", data={
        "kind": "mass", "mode": "profile", "unit": "per100", "serving_g": "100",
        "protein_g": "22", "sugar_g": "30", "added": "Glycine"}).get_data(as_text=True)
    assert "مفيش أرقام للأحماض" not in html, "لسه بيرفض"
    assert 'id="wyPartial"' in html and "Glycine" in html and "30 جم سكر" in html, "النتيجة الناقصة مابانتش"


def test_added_bcaas_are_a_note_not_cheating():
    """‏صاحب المشروع صوّر علبة مكوّناتها فيها L-Leucine وL-Isoleucine
    وL-Valine، وطلعله تحذير أحمر "Amino Spiking". دول أحماض أساسية
    بتتضاف تقوية -- الغش هو الرخيص غير الأساسي (Glycine، Taurine…)."""
    r = W.analyze_summary(32, 24, None, None, None, None, ["Leucine", "Isoleucine", "Valine"])
    keys = {a["key"]: a for a in r["alerts"]}
    assert "added" not in keys and keys["fortified"]["items"] == ["Leucine", "Isoleucine", "Valine"], r["alerts"]
    assert not any("Spiking" in w for w in r["warnings"]), r["warnings"]
    r = W.analyze_summary(32, 24, None, None, None, None, ["Glycine", "Leucine"])
    keys = {a["key"]: a for a in r["alerts"]}
    assert keys["added"]["items"] == ["Glycine"] and keys["fortified"]["items"] == ["Leucine"], r["alerts"]
    html = A.app.test_client().post("/whey", data={"kind": "whey", "mode": "summary", "serving_g": "32",
                                                   "protein_g": "24", "added": "Leucine,Isoleucine,Valine"}).get_data(as_text=True)
    assert "Amino Spiking" not in html.split('id="wyResult"', 1)[1].split("<form", 1)[0] and "BCAA" in html


# ── باقي المكملات ───────────────────────────────────────────────────

def test_creatine():
    r = SP.evaluate("creatine", {"creatine_g": 5, "form": "monohydrate", "blend": False})
    assert r["verdict"] == "pass", r
    r = SP.evaluate("creatine", {"creatine_g": 1.5, "form": "hcl", "blend": False})
    assert _status(r, "dose") == "warn" and _status(r, "form") == "warn" and r["verdict"] == "warn"
    r = SP.evaluate("creatine", {"creatine_g": None, "form": "monohydrate", "blend": True})
    assert _status(r, "blend") == "fail" and r["verdict"] == "fail"


def test_omega3():
    r = SP.evaluate("omega3", {"oil_mg": 1000, "epa_mg": 180, "dha_mg": 120})
    assert r["verdict"] == "pass", r
    r = SP.evaluate("omega3", {"oil_mg": 1000, "epa_mg": 90, "dha_mg": 60})
    assert _status(r, "dose") == "warn" and _status(r, "purity") == "warn"
    r = SP.evaluate("omega3", {"oil_mg": 8000, "epa_mg": 3500, "dha_mg": 2500})
    assert _status(r, "upper") == "warn"


def test_a_multivitamin_over_the_upper_limit_fails():
    r = SP.evaluate("multi", {"vit_d_ug": 25, "zinc_mg": 15, "vit_c_mg": 500})
    assert r["verdict"] == "pass", r
    r = SP.evaluate("multi", {"vit_d_ug": 125, "zinc_mg": 15})
    assert _status(r, "vit_d_ug") == "fail" and r["verdict"] == "fail"


def test_preworkout():
    r = SP.evaluate("preworkout", {"caffeine_mg": 150, "beta_alanine_g": 4, "blend": False})
    assert r["verdict"] == "pass", r
    r = SP.evaluate("preworkout", {"caffeine_mg": 300, "beta_alanine_g": 2, "blend": True})
    assert {_status(r, "caffeine"), _status(r, "beta_alanine"), _status(r, "blend")} == {"warn"}
    r = SP.evaluate("preworkout", {"caffeine_mg": 450, "blend": False})
    assert _status(r, "caffeine") == "fail"


def test_eaa_and_bcaa():
    r = SP.evaluate("eaa", {"leucine_g": 2.5, "bcaa_only": False})
    assert r["verdict"] == "pass", r
    r = SP.evaluate("eaa", {"leucine_g": 0.5, "bcaa_only": True})
    assert _status(r, "leucine") == "warn" and _status(r, "bcaa_only") == "warn"


def test_nothing_entered_is_explained_not_judged():
    try:
        SP.evaluate("omega3", {})
    except ValueError:
        pass
    else:
        raise AssertionError("حكم على منتج من غير أرقام")


def test_every_rule_has_its_source_written_down():
    doc = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "docs", "supplements-sources.md"), encoding="utf-8").read()
    for key in SP.SOURCES:
        assert "`%s`" % key in doc, key
    for kind, spec in SP.TYPES.items():
        for rule in spec.get("rules", []):
            assert rule in SP.SOURCES, (kind, rule)


def test_a_supplement_form_is_judged_on_the_page():
    html = A.app.test_client().post("/whey", data={
        "kind": "preworkout", "caffeine_mg": "450", "beta_alanine_g": "3.2"}).get_data(as_text=True)
    assert 'id="spResult"' in html and 'data-g="bad"' in html, "البري وورك أوت مااتقيّمش"
    assert "EFSA" in html, "المصدر مش ظاهر"


def test_the_reader_gets_the_supplement_fields():
    import whey_vision
    p = whey_vision.prompt_for("omega3")
    assert "epa_mg" in p and "dha_mg" in p and "oil_mg" in p
    got = whey_vision.normalize_supplement("omega3", {"oil_mg": 1000, "epa_mg": 180, "dha_mg": 120000})
    assert got["fields"] == {"oil_mg": 1000, "epa_mg": 180}, got   # ‏رقم مستحيل بيتشال
    assert got["kind"] == "omega3" and got["engine"] == "vision"


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

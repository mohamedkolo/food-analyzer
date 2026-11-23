# -*- coding: utf-8 -*-
"""‏محلل الواي بروتين: صورة ضهر العلبة -> الأحماض الأمينية -> تقييم من ١٠٠.

‏المعادلات ونظام النقط من صاحب المشروع بالحرف. العلبة التجريبية بتاعته
(حصة ٣١ جم، بروتين ٢٨ جم، الأحماض لكل ١٠٠ جم بروتين) نتيجتها المتوقعة:
Total AA 89.5%، Leucine 10.29%، EAA 47%، BCAA 22.2%، Score 100 ممتاز.

Run with:  python3 tests/test_whey_analyzer.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_whey_test.db"

import app as A          # noqa: E402
import whey_analyzer as W  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False

DEMO = dict(W.DEMO)


def _close(a, b, tol=0.05):
    return abs(a - b) <= tol


# ── المعادلات ────────────────────────────────────────────────────────

def test_the_owners_demo_box_comes_out_as_expected():
    r = W.analyze(DEMO["serving_g"], DEMO["protein_g"], DEMO["amino"], unit="per100")
    assert _close(r["total_aa_pct"], 89.5), r["total_aa_pct"]
    assert _close(r["leucine_pct"], 10.29, 0.01), r["leucine_pct"]
    assert _close(r["eaa_pct"], 47.0, 0.1), r["eaa_pct"]
    assert _close(r["bcaa_pct"], 22.2), r["bcaa_pct"]
    assert _close(r["protein_pct"], 90.3), r["protein_pct"]
    assert r["score"] == 100 and r["grade"]["key"] == "excellent", (r["score"], r["grade"])
    assert not r["warnings"]


def test_per_serving_numbers_give_the_same_percentages():
    per_serving = {k: v * 28 / 100 for k, v in DEMO["amino"].items()}
    a = W.analyze(31, 28, per_serving, unit="serving")
    b = W.analyze(31, 28, DEMO["amino"], unit="per100")
    for key in ("total_aa_pct", "leucine_pct", "eaa_pct", "bcaa_pct"):
        assert _close(a[key], b[key], 0.01), (key, a[key], b[key])
    assert _close(a["leucine_g"], b["leucine_g"], 0.01)


def test_the_points_follow_the_table_exactly():
    pts = W.points
    assert [pts("total_aa", v) for v in (85, 84.9, 75, 74.9, 65, 64.9)] == [30, 22, 22, 12, 12, 0]
    assert [pts("leucine", v) for v in (10, 9.9, 9, 8.9, 8, 7.9)] == [30, 24, 24, 14, 14, 0]
    assert [pts("eaa", v) for v in (45, 44.9, 40, 39.9, 35, 34.9)] == [20, 15, 15, 8, 8, 0]
    assert [pts("bcaa", v) for v in (20, 19.9, 18, 17.9, 15, 14.9)] == [20, 15, 15, 8, 8, 0]


def test_the_grade_bands():
    assert [W.grade(s)["key"] for s in (100, 90, 89, 75, 74, 50, 49, 0)] == [
        "excellent", "excellent", "good", "good", "fair", "fair", "bad", "bad"]


def test_amino_spiking_is_called_out():
    """‏علبة "منفوخة" بجلايسين رخيص مكان جزء من الليوسين: المجموع لسه
    عالي (Total AA بيبان كويس) والليوسين واطي."""
    spiked = dict(DEMO["amino"], Glycine=15000, Leucine=5000)
    r = W.analyze(31, 28, spiked, unit="per100")
    assert r["leucine_pct"] < 8 and r["warnings"], r
    assert any("Amino Spiking" in w for w in r["warnings"])


def test_impossible_numbers_are_refused_not_scored():
    try:
        W.analyze(31, 40, DEMO["amino"], unit="per100")   # ‏بروتين أكتر من الحصة
    except ValueError:
        pass
    else:
        raise AssertionError("بروتين ٤٠ جم في حصة ٣١ جم اتقبل")
    try:
        W.analyze(31, 28, {"Leucine": 0}, unit="per100")
    except ValueError:
        pass
    else:
        raise AssertionError("مفيش أحماض أمينية واتقيّمت")


# ── قراءة الصورة ─────────────────────────────────────────────────────

LABEL = """SUPPLEMENT FACTS
Serving Size 1 Scoop (31g)
Servings Per Container 74
Amount Per Serving
Calories 120
Protein 28g
TYPICAL AMINO ACID PROFILE (per 100g of protein)
L-Alanine 5,000mg   L-Arginine 2,100 mg
Aspartic Acid 11,000mg  L-Cystine 2,200mg
Glutamic Acid 18,100mg  Glycine 1,400mg
L-Histidine 1,700mg  L-Isoleucine* 6,100mg
L-Leucine* 10,200mg  L-Lysine 9,600mg
L-Methionine 2,200mg  L-Phenylalanine 3,000mg
L-Proline 5,500mg  L-Serine 4,600mg
L-Threonine 6,700mg  L-Tryptophan 1,400mg
L-Tyrosine 2,600mg  L-Valine* 5,700mg
"""


def test_a_label_is_read_into_numbers():
    got = W.parse_label(LABEL)
    assert got["serving_g"] == 31 and got["protein_g"] == 28, got
    assert got["unit"] == "per100", got["unit"]
    assert got["amino"]["Leucine"] == 10200 and got["amino"]["Glutamine"] == 18100, got["amino"]
    assert not got["missing"], got["missing"]


def test_the_unit_is_found_without_the_words():
    """‏من غير "per 100g protein": مجموع ٩٩ جم مايدخلش في حصة ٣١ جم."""
    text = LABEL.replace("(per 100g of protein)", "")
    assert W.parse_label(text)["unit"] == "per100"
    small = "Serving Size 31g\nProtein 28g\nPer serving\n" + "\n".join(
        "%s %dmg" % (k, round(v * 0.28)) for k, v in DEMO["amino"].items())
    assert W.parse_label(small)["unit"] == "serving"


def test_a_g_read_as_9_is_still_the_serving():
    """‏صورة حقيقية في المتصفح: "(31g)" اتقرت "(319)" -- الـg والـ9 شبه بعض."""
    got = W.parse_label("Serving Size 1 Scoop (319)\nProtein 28g\nLeucine 10,200mg")
    assert got["serving_g"] == 31, got["serving_g"]
    # ‏بس رقم حقيقي من غير g مايتلمسش
    assert W.parse_label("Serving Size (45 g)\nProtein 36g")["serving_g"] == 45


def test_grams_are_turned_into_milligrams():
    text = "Serving size 30 g\nProtein 24 g\nLeucine 2.7g\nIsoleucine 1.5 g\nValine 1.4g"
    got = W.parse_label(text)
    assert got["amino"]["Leucine"] == 2700 and got["amino"]["Valine"] == 1400, got["amino"]


def test_what_the_photo_did_not_show_is_listed():
    got = W.parse_label("Serving Size 31g\nLeucine 10200mg")
    assert "protein_g" in got["missing"] and "Valine" in got["missing"], got["missing"]


# ── الصفحات ─────────────────────────────────────────────────────────

def test_the_page_offers_camera_and_upload():
    html = A.app.test_client().get("/whey").get_data(as_text=True)
    assert re.search(r'<input[^>]*type="file"[^>]*capture="environment"', html), "مفيش زرار صوّر العلبة"
    files = re.findall(r'<input[^>]*type="file"[^>]*>', html)
    assert len(files) == 2 and all("aria-label" in f or 'id="' in f for f in files), files
    for name in ("serving_g", "protein_g", "Leucine", "Valine"):
        assert re.search(r'<input[^>]*name="%s"' % name, html), name


def test_the_server_reads_ocr_text():
    r = A.app.test_client().post("/whey/parse", json={"text": LABEL})
    got = r.get_json()
    assert r.status_code == 200 and got["amino"]["Leucine"] == 10200, got


def test_the_demo_page_shows_the_expected_result():
    html = A.app.test_client().get("/whey/demo").get_data(as_text=True)
    assert re.search(r'class="wy-score"[^>]*>\s*100', html), "السكور مش ١٠٠"
    assert "ممتاز" in html and "89.5" in html and "10.29" in html and "22.2" in html
    assert 'class="wy-warn"' not in html, "تحذير غش على علبة نضيفة"


def test_a_posted_form_is_scored_and_impossible_input_is_explained():
    c = A.app.test_client()
    form = {"serving_g": "31", "protein_g": "28", "unit": "per100"}
    form.update({k: str(v) for k, v in DEMO["amino"].items()})
    html = c.post("/whey", data=form).get_data(as_text=True)
    assert re.search(r'class="wy-score"[^>]*>\s*100', html)
    bad = dict(form, protein_g="45")
    r = c.post("/whey", data=bad)
    assert r.status_code == 200 and "wy-error" in r.get_data(as_text=True)



def test_the_menus_lead_to_it():
    """‏صاحب المشروع فتح القايمة ومالقاهوش: "فين بقى". الصفحة كانت شغالة
    على /whey ومفيش لينك ليها في أي مكان."""
    from datetime import datetime
    from werkzeug.security import generate_password_hash
    if not A.db_row("SELECT id FROM users WHERE email='wheyclient@x.test'"):
        A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) VALUES (?,?,?,'client',1,?)",
                 ("عميل", "wheyclient@x.test", generate_password_hash("pw123456"), datetime.now()))
    for email in ("admin@nutrax.com", "wheyclient@x.test"):
        c = A.app.test_client()
        c.post("/login", data={"action": "login", "email": email, "password": "pw123456"})
        html = c.get("/whey").get_data(as_text=True)
        side = html.split('class="sidebar', 1)[1].split("</aside>", 1)[0] if 'class="sidebar' in html else html
        # ‏وصفحة الواي نفسها بالقايمة، والزرار بتاعها منوّر
        assert re.search(r'<a href="/whey" class="nav-item active[^"]*lq"', side), email
    footer = A.app.test_client().get("/foods").get_data(as_text=True)
    assert 'href="/whey"' in footer.split("nx-footer", 1)[1], "مفيش لينك في الفوتر"


# ── صور حقيقية (صاحب المشروع صوّرها في المحل) ────────────────────────
#
# ‏tests/data/whey_ocr_real.json: اللي Tesseract قراه في المتصفح فعلاً من
# ٣ صور علب، كل قراية لوحدها. العلبة الأولى هي نفس العلبة التجريبية
# (DEMO)؛ والقراية الأولى سجّلت أرقام في خانات غلط ("Aspartic 1748"،
# "Lysine 2200" -- دي بتاعة Methionine). رقم غلط أسوأ من خانة فاضية:
# بيدخل في الحساب من غير ما حد يشوفه.

def _real(name):
    import json
    root = os.path.dirname(os.path.abspath(__file__))
    return json.load(open(os.path.join(root, "data", "whey_ocr_real.json"), encoding="utf-8"))[name]


def test_a_real_photo_never_fills_a_wrong_number():
    got = W.parse_passes(_real("box1.jpg"))
    for k, v in got["amino"].items():
        assert v == DEMO["amino"][k], (k, v, DEMO["amino"][k])
    for k in ("serving_g", "protein_g"):
        assert got[k] in (None, DEMO[k + ""] if k in DEMO else None), (k, got[k])


def test_numbers_need_two_readings_that_agree():
    one = W.parse_passes(["Leucine 10200mg", "Leucine 10200 mg", "nothing here"])
    assert one["amino"].get("Leucine") == 10200, one
    clash = W.parse_passes(["Leucine 10200mg", "Leucine 10800mg", "x"])
    assert "Leucine" not in clash["amino"], clash
    lone = W.parse_passes(["x", "y", "Tyrosine 5700mg"])
    # ‏قراية واحدة بس: مش في الخانة، بس اقتراح تحتها
    assert "Tyrosine" not in lone["amino"] and lone["hints"].get("Tyrosine") == 5700, lone


def test_a_number_without_a_unit_or_out_of_range_is_not_taken():
    got = W.parse_label("Threonine 14008\nCystine 7\nSerine 700mg\nLeucine 10200mg")
    assert set(got["amino"]) == {"Leucine"}, got["amino"]


def test_a_label_with_no_profile_but_added_amino_acids_is_called_out():
    got = W.parse_passes(_real("box2.jpg"))
    assert not got["amino"], got["amino"]
    assert {"Glycine", "Taurine"} <= set(got["added"]), got["added"]
    r = W.analyze(31, 28, DEMO["amino"], unit="per100", added=["Glycine", "Taurine"])
    assert any("Glycine" in w and "Taurine" in w for w in r["warnings"]), r["warnings"]


# ── علبة كاتبة ملخص بس (Dymatize) ──────────────────────────────────

DYMATIZE = """Serving size 1 Scoop (32g)
Protein 25g
TYPICAL AMINO ACID PROFILE
25g TOTAL AMINO ACIDS PER SERVING
11.9 g EAAs
ISOLEUCINE 1.4g VALINE 1.4g LEUCINE 2.6g
5.5 g BCAAs
13.4 g NON-EAAs
GLUTAMINE 4.4g"""


def test_a_summary_label_is_read_and_scored():
    got = W.parse_label(DYMATIZE)
    assert got["summary"] == {"total_aa_g": 25, "eaa_g": 11.9, "bcaa_g": 5.5, "leucine_g": 2.6}, got["summary"]
    r = W.analyze_summary(32, 25, 25, 11.9, 5.5, 2.6)
    assert _close(r["total_aa_pct"], 78.1) and _close(r["leucine_pct"], 10.4)
    assert _close(r["eaa_pct"], 47.6) and _close(r["bcaa_pct"], 22.0)
    assert r["score"] == 92 and r["grade"]["key"] == "excellent", r["score"]


def test_the_summary_form_is_scored():
    c = A.app.test_client()
    html = c.post("/whey", data={"mode": "summary", "serving_g": "32", "protein_g": "25",
                                 "total_aa_g": "25", "eaa_g": "11.9", "bcaa_g": "5.5",
                                 "leucine_g": "2.6"}).get_data(as_text=True)
    assert re.search(r'class="wy-score"[^>]*>\s*92', html), "ملخص Dymatize مااتقيّمش"


# ── القراية بالذكاء الاصطناعي لو فيه مفتاح ──────────────────────────

def test_without_a_key_the_page_falls_back_to_the_phone():
    os.environ.pop("ANTHROPIC_API_KEY", None)
    import whey_vision
    assert not whey_vision.available()
    r = A.app.test_client().post("/whey/read", data={})
    assert r.status_code == 503 and r.get_json()["fallback"] is True


def test_what_the_model_returns_goes_through_the_same_checks():
    import whey_vision
    raw = {"serving_g": 31, "protein_g": 28, "unit": "per100",
           "amino": dict(DEMO["amino"], Threonine=67000),   # ‏غلطة: صفر زيادة
           "summary": {"total_aa_g": None, "eaa_g": None, "bcaa_g": None, "leucine_g": None},
           "added": ["L-Taurine"]}
    got = whey_vision.normalize(raw)
    assert got["amino"]["Leucine"] == 10200 and "Threonine" not in got["amino"], got["amino"]
    assert "Threonine" in got["missing"] and got["added"] == ["Taurine"], got
    assert got["engine"] == "vision"


def test_one_amino_acid_cannot_be_most_of_the_protein():
    """‏Dymatize على صورة حقيقية: "Valine 5000" اتسجّل والصح 1.4 جم -- الـ5
    جاية من "5.5g BCAAs" جنبه. حمض واحد (غير الجلوتامين والأسبارتيك) بيبقى
    تحت ١٤٪ من البروتين؛ ٥ جم في حصة ٢٥ جم بروتين = ٢٠٪."""
    got = W.parse_passes(["Serving size 1 Scoop (32g)\nProtein 25g\nValine 5g\nLeucine 2.6g"] * 2)
    assert "Valine" not in got["amino"] and got["amino"].get("Leucine") == 2600, got["amino"]
    per100 = W.parse_label("Protein 28g\nper 100g of protein\nThreonine 14008mg\nGlutamine 18100mg")
    assert "Threonine" not in per100["amino"] and per100["amino"]["Glutamine"] == 18100, per100["amino"]


def test_equal_readings_are_not_mixed_up():
    """‏قرايتين نتيجتهم شبه بعض كانوا بيتلخبطوا (reads.index) فالاقتراحات ضاعت."""
    got = W.parse_passes(["x", "x", "Alanine 5000mg"])
    assert got["hints"].get("Alanine") == 5000, got


# ── Gemini (المفتاح المجاني من Google AI Studio) ────────────────────

class _Resp:
    def __init__(self, body):
        import json
        self._b = json.dumps(body).encode()
    def read(self):
        return self._b
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _fake_google(answer, seen):
    import json
    models = {"models": [
        {"name": "models/gemini-embedding-1", "supportedGenerationMethods": ["embedContent"]},
        {"name": "models/gemini-9-pro", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-9-flash", "supportedGenerationMethods": ["generateContent"]},
    ]}

    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else req
        seen.append(url)
        if url.split("?")[0].endswith("/models"):
            return _Resp(models)
        body = json.loads(req.data.decode())
        assert body["contents"][0]["parts"][0]["inline_data"]["mime_type"] == "image/jpeg"
        return _Resp({"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}]})
    return urlopen


def test_a_gemini_key_turns_the_reader_on():
    import whey_vision
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ["GEMINI_API_KEY"] = "test-key"
    try:
        assert whey_vision.available()
    finally:
        os.environ.pop("GEMINI_API_KEY", None)


def test_gemini_reads_the_label_through_the_same_checks():
    import whey_vision
    answer = {"serving_g": 31, "protein_g": 28, "unit": "per100",
              "amino": dict(DEMO["amino"]), "summary": None, "added": []}
    seen = []
    os.environ["GEMINI_API_KEY"] = "test-key"
    whey_vision._MODEL_CACHE.clear()
    real = whey_vision.urllib.request.urlopen
    whey_vision.urllib.request.urlopen = _fake_google(answer, seen)
    try:
        got = whey_vision.read_label(b"\xff\xd8fakejpeg", "image/jpeg")
    finally:
        whey_vision.urllib.request.urlopen = real
        os.environ.pop("GEMINI_API_KEY", None)
    assert got["amino"] == DEMO["amino"] and got["serving_g"] == 31, got
    # ‏الموديل اتختار من القايمة: flash، وبيعمل generateContent
    assert any("gemini-9-flash:generateContent" in u for u in seen), seen
    r = W.analyze(got["serving_g"], got["protein_g"], got["amino"], got["unit"])
    assert r["score"] == 100


def test_a_gemini_failure_falls_back_to_the_phone():
    import whey_vision
    os.environ["GEMINI_API_KEY"] = "test-key"
    whey_vision._MODEL_CACHE.clear()
    real = whey_vision.urllib.request.urlopen

    def boom(req, timeout=None):
        raise OSError("quota")
    whey_vision.urllib.request.urlopen = boom
    try:
        try:
            whey_vision.read_label(b"\xff\xd8x", "image/jpeg")
        except whey_vision.VisionError:
            pass
        else:
            raise AssertionError("الغلطة مااتحوّلتش لـVisionError")
    finally:
        whey_vision.urllib.request.urlopen = real
        os.environ.pop("GEMINI_API_KEY", None)


def test_gemini_tries_the_next_model_and_says_why_it_failed():
    """‏على Render القراية رجعت للموبايل ساكتة، ومحدش عرف ليه. دلوقتي لو
    موديل رفض (حد مجاني صفر عليه مثلاً) بيجرّب اللي بعده، ولو كلهم فشلوا
    الرسالة فيها السبب -- عشان تبان في الصفحة وفي سجل Render."""
    import json
    import urllib.error
    import whey_vision
    answer = {"serving_g": 31, "protein_g": 28, "unit": "per100", "amino": dict(DEMO["amino"]),
              "summary": None, "added": []}
    tried = []

    def urlopen(req, timeout=None):
        url = req.full_url
        if url.split("?")[0].endswith("/models"):
            return _Resp({"models": [
                {"name": "models/gemini-9-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-flash-latest", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-9-flash-lite", "supportedGenerationMethods": ["generateContent"]}]})
        tried.append(url.split("/models/")[1].split(":")[0])
        if len(tried) == 1:
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
        return _Resp({"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}]})

    os.environ["GEMINI_API_KEY"] = "test-key"
    whey_vision._MODEL_CACHE.clear()
    real = whey_vision.urllib.request.urlopen
    whey_vision.urllib.request.urlopen = urlopen
    try:
        got = whey_vision.read_label(b"\xff\xd8x", "image/jpeg")
        assert got["amino"]["Leucine"] == 10200 and len(tried) == 2, tried
        assert tried[0] == "gemini-flash-latest", tried      # ‏الـlatest الأول

        def always(req, timeout=None):
            if req.full_url.split("?")[0].endswith("/models"):
                return urlopen(req)
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)
        whey_vision._MODEL_CACHE.clear()
        whey_vision.urllib.request.urlopen = always
        try:
            whey_vision.read_label(b"\xff\xd8x", "image/jpeg")
        except whey_vision.VisionError as e:
            assert "403" in str(e), str(e)
        else:
            raise AssertionError("مفيش غلطة")
    finally:
        whey_vision.urllib.request.urlopen = real
        os.environ.pop("GEMINI_API_KEY", None)


def test_the_page_says_who_read_it_and_the_phone_only_suggests():
    html = A.app.test_client().get("/whey").get_data(as_text=True)
    assert "byVision" in html and "byPhone" in html, "الصفحة مابتقولش مين قرا"
    # ‏قراية الموبايل: كل الأرقام اقتراحات (Isoleucine 10200 اتسجّل لوحده
    # على صورة حقيقية والصح 6100 -- الـ10200 بتاعة Leucine تحته)
    assert "phoneOnlySuggests" in html

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

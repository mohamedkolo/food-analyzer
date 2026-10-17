# -*- coding: utf-8 -*-
"""‏قراءة ورقة التحليل من PDF، مش من صورة بس.

‏المعامل بتبعت التحاليل PDF على الواتس. الدكتور كان بيطبعها ويصوّرها
عشان البرنامج يقراها -- والصورة دي أسوأ مصدر ممكن: الـPDF اللي جاي من
المعمل نصّه مكتوب جوّاه أصلاً، والتصوير بيرميه ويخلّي القراءة تخمين
من بكسلات.

‏تلات حاجات الملف ده بيحميها:

  * **الـPDF بيتبعت مستند، مش صورة.** لو اتبعت كبلوك image الـAPI
    بيرفضه، ولو اتحوّل لصورة بنرجع لنفس التخمين اللي بنهرب منه.
  * **الصور فضلت زي ما هي.** الصورة المتصوّرة بالكاميرا بتتقرا في
    المتصفح والصورة مابتطلعش من الجهاز. لو الإضافة كسرت الطريق ده،
    يبقى كل ورقة بقت بتترفع لسيرفر -- وده ملف مريض.
  * **الحدود.** ملف ٣٠ ميجا على نت موبايل بيقعد دقايق وبعدين يفشل.

Run with:  python3 tests/test_report_pdf.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_pdf_test.db"

import lab_report      # noqa: E402

# ‏أصغر PDF سليم. المحتوى مش مهم -- اللي بيتفحص هو إزاي بيتبعت.
PDF = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
       b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
       b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
       b"trailer<</Root 1 0 R>>\n%%EOF\n")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class _Block:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Reply:
    stop_reason = "end_turn"

    def __init__(self, text):
        self.content = [_Block(text)]


class _Spy:
    """‏بيمسك الطلب اللي كان هيروح للـAPI من غير ما يروح."""

    sent = None

    def __init__(self, *a, **kw):
        pass

    @property
    def messages(self):
        return self

    def create(self, **kw):
        _Spy.sent = kw
        return _Reply('{"is_body_report": true, '
                      '"weight": 88.0, "height": 162.0}')


def _send(data, content_type, key="sk-test"):
    """‏بينادي read_report بمفتاح مزيّف وبيرجّع الطلب اللي اتبنى."""
    import types
    fake = types.ModuleType("anthropic")
    fake.Anthropic = _Spy
    for name in ("AuthenticationError", "RateLimitError", "APIConnectionError",
                 "APIStatusError"):
        setattr(fake, name, type(name, (Exception,), {}))
    old_mod = sys.modules.get("anthropic")
    old_key = os.environ.get("ANTHROPIC_API_KEY")
    sys.modules["anthropic"] = fake
    if key is None:
        os.environ.pop("ANTHROPIC_API_KEY", None)
    else:
        os.environ["ANTHROPIC_API_KEY"] = key
    _Spy.sent = None
    try:
        out = lab_report.read_report(data, content_type)
    finally:
        if old_mod is not None:
            sys.modules["anthropic"] = fake and old_mod
        else:
            sys.modules.pop("anthropic", None)
        if old_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = old_key
    return out, _Spy.sent


def _first_source(sent):
    return sent["messages"][0]["content"][0]


# ── الـPDF ───────────────────────────────────────────────────────────

def test_a_pdf_is_accepted():
    data, _sent = _send(PDF, "application/pdf")
    assert data.get("weight") == 88.0, data


def test_a_pdf_goes_as_a_document_not_an_image():
    """‏لو اتبعت كبلوك image الـAPI بيرفضه."""
    _data, sent = _send(PDF, "application/pdf")
    block = _first_source(sent)
    assert block["type"] == "document", block["type"]
    assert block["source"]["media_type"] == "application/pdf", block["source"]


def test_the_pdf_itself_is_sent_not_a_picture_of_it():
    """‏تحويل الـPDF لصورة بيرمي النص المكتوب جوّاه ويرجّعنا للتخمين."""
    import base64
    _data, sent = _send(PDF, "application/pdf")
    raw = base64.standard_b64decode(_first_source(sent)["source"]["data"])
    assert raw == PDF, "‏اللي اتبعت مش الملف نفسه"


def test_the_document_comes_before_the_question():
    _data, sent = _send(PDF, "application/pdf")
    kinds = [b["type"] for b in sent["messages"][0]["content"]]
    assert kinds[0] in ("document", "image"), kinds
    assert kinds[-1] == "text", kinds


def test_a_pdf_with_a_content_type_charset_suffix_still_works():
    """‏بعض المتصفحات بتبعت "application/pdf; charset=binary"."""
    data, sent = _send(PDF, "application/pdf; charset=binary")
    assert data.get("weight") == 88.0, data
    assert _first_source(sent)["type"] == "document"


# ── الصور ما اتكسرتش ────────────────────────────────────────────────

def test_an_image_still_goes_as_an_image():
    """‏لو الصور بقت مستندات، كل ورقة متصوّرة هتترفض."""
    _data, sent = _send(PNG, "image/png")
    block = _first_source(sent)
    assert block["type"] == "image", block["type"]
    assert block["source"]["media_type"] == "image/png", block["source"]


def test_an_unsupported_type_is_still_refused():
    """‏ملف Word أو zip مش ورقة تحليل."""
    for bad in ("application/msword", "application/zip", "text/html", ""):
        try:
            _send(b"xx", bad)
        except lab_report.ReportError as e:
            assert "مدعوم" in str(e), str(e)
        else:
            raise AssertionError("‏%s عدّى" % bad)


# ── الحدود ───────────────────────────────────────────────────────────

def test_a_pdf_may_be_bigger_than_an_image_but_not_unlimited():
    """‏ورقة متصوّرة سكانر بتطلع أكبر من صورة كاميرا، بس مش بلا حد."""
    assert lab_report.MAX_PDF_BYTES > lab_report.MAX_IMAGE_BYTES
    try:
        _send(b"%PDF-" + b"0" * lab_report.MAX_PDF_BYTES, "application/pdf")
    except lab_report.ReportError as e:
        assert "كبير" in str(e), str(e)
    else:
        raise AssertionError("‏ملف فوق الحد عدّى")


def test_an_image_keeps_its_own_smaller_limit():
    try:
        _send(b"0" * (lab_report.MAX_IMAGE_BYTES + 1), "image/png")
    except lab_report.ReportError as e:
        assert "كبيرة" in str(e), str(e)
    else:
        raise AssertionError("‏صورة فوق الحد عدّت")


def test_an_empty_file_is_refused_before_anything_else():
    try:
        _send(b"", "application/pdf")
    except lab_report.ReportError as e:
        assert "مافيش" in str(e), str(e)
    else:
        raise AssertionError("‏ملف فاضي عدّى")


# ── من غير مفتاح ────────────────────────────────────────────────────

def test_a_pdf_without_an_api_key_says_what_to_do_instead():
    """‏المحرّك المحلي بياخد بكسلات مش PDF. الرسالة لازم تقول للدكتور
    الطريق التاني (يصوّر الورقة)، مش تقوله "مش متاح" وخلاص."""
    try:
        _send(PDF, "application/pdf", key=None)
    except lab_report.ReportError as e:
        assert "صوّر" in str(e), str(e)
    else:
        raise AssertionError("‏PDF من غير مفتاح عدّى")


# ── الواجهة ─────────────────────────────────────────────────────────

def _page():
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "templates", "generate.html"),
            encoding="utf-8") as f:
        return f.read()


def test_the_page_offers_a_pdf_upload():
    html = _page()
    assert 'accept="application/pdf,image/*"' in html, "‏مافيش مدخل بياخد PDF"


def test_the_camera_button_still_opens_the_camera():
    """‏لو اتحطّ accept للـPDF على زرار الكاميرا، الكاميرا مابتفتحش على
    طول على الموبايل -- والحالة الشائعة هي الكاميرا."""
    html = _page()
    assert 'id="rpFile" accept="image/*" capture="environment"' in html, (
        "‏زرار الكاميرا اتغيّر")


def test_the_page_says_a_pdf_leaves_the_device():
    """‏الصورة بتتقرا في المتصفح، الـPDF بيترفع. دي ملفات مرضى --
    فالفرق ده لازم يكون مكتوب، مش مفاجأة."""
    html = _page()
    # ‏وقت الرفع
    assert "برفع الملف وبقراه على السيرفر" in html, (
        "‏مافيش أي كلام بيقول إن الـPDF بيترفع")
    # ‏وقبل الرفع كمان: الجملة اللي تحت الزرار. القرار ده قرار الدكتور،
    # فلازم يكون قدامه **قبل** ما يختار الملف مش بعده.
    assert "بيترفع للسيرفر" in html, "‏الجملة اللي تحت الزرار مابتقولش الفرق"
    assert "الصورة المتصوّرة مابتطلعش" in html, (
        "‏الجملة بقت بتقول إن كل حاجة بتترفع، وده غلط على الكاميرا")


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {str(e)[:300]}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

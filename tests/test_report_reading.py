# -*- coding: utf-8 -*-
"""قراءة ورقة تحليل الجسم من صورة.

الدكتور بيكتب نفس الأرقام اللي مطبوعة قدامه. الميزة دي بتصوّر الورقة
وتملّيها. والقاعدة اللي كل حرف فيها مبني عليها:

    **مايخمّنش ولا رقم.**

رقم مخمّن في ورقة تغذية أسوأ من خانة فاضية: الفاضية بتبان للدكتور، والغلط
بيمشي في حساب السعرات لحد ما يوصل للعميل. فالاختبارات دي أغلبها عن الحالات
اللي المفروض القراية **ترفض** فيها تملّي.

النداء نفسه مش بيتعمل هنا: العميل مزيّف، والمقيس هو كل اللي حوله -- الحماية
والتنضيف وتحليل الرد وشكل الجواب للواجهة.

Run with:  python3 tests/test_report_reading.py
"""

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_report_test.db"

import lab_report      # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64

GOOD = {
    "is_body_report": True, "name": "نورة سيد", "gender": "female", "age": 29,
    "height": 165.0, "weight": 78.4, "fat_pct": 38.2, "bmi": 28.8, "bmr": 1420,
    "muscle_mass": 24.1, "visceral_fat": 9.0, "body_water": 33.0,
    "extras": [{"label": "الوزن المثالي", "value": "60 كجم"}],
    "unreadable": [],
}


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Response:
    def __init__(self, payload, stop_reason="end_turn"):
        self.content = [_Block(payload if isinstance(payload, str)
                               else json.dumps(payload, ensure_ascii=False))]
        self.stop_reason = stop_reason


def _stub(payload, stop_reason="end_turn", raises=None):
    """‏يحط عميل مزيّف مكان الحقيقي، ويرجّع اللي اتبعت للـAPI."""
    sent = {}

    class Messages:
        def create(self, **kwargs):
            sent.update(kwargs)
            if raises is not None:
                raise raises
            return _Response(payload, stop_reason)

    class Client:
        def __init__(self, **kwargs):
            self.messages = Messages()

    import anthropic
    real = anthropic.Anthropic
    anthropic.Anthropic = Client
    os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
    return sent, (lambda: setattr(anthropic, "Anthropic", real))


def test_a_clean_sheet_comes_back_as_numbers():
    sent, undo = _stub(GOOD)
    try:
        data = lab_report.read_report(PNG, "image/png")
    finally:
        undo()
    assert data["weight"] == 78.4 and data["height"] == 165.0, data
    assert data["fat_pct"] == 38.2 and data["bmi"] == 28.8, data
    assert data["age"] == 29 and isinstance(data["age"], int), data
    assert data["gender"] == "female" and data["name"] == "نورة سيد", data
    assert data["bmr"] == 1420, data
    assert data["extras"] == [{"label": "الوزن المثالي", "value": "60 كجم"}], data
    # ‏والصورة اتبعتت كصورة، والرد مقيّد بشكل JSON مش نص حر
    assert sent["model"] == "claude-opus-5", sent.get("model")
    blocks = sent["messages"][0]["content"]
    assert blocks[0]["type"] == "image", blocks[0]
    assert blocks[0]["source"]["media_type"] == "image/png", blocks[0]
    assert sent["output_config"]["format"]["type"] == "json_schema", sent


def test_an_unreadable_field_comes_back_empty_not_guessed():
    """‏ده جوهر الميزة: الخانة المش واضحة بتفضل فاضية ويتقال إنها فاضية."""
    payload = dict(GOOD, bmi=None, fat_pct=None, unreadable=["BMI", "نسبة الدهون"])
    sent, undo = _stub(payload)
    try:
        data = lab_report.read_report(PNG, "image/png")
    finally:
        undo()
    assert data["bmi"] is None and data["fat_pct"] is None, data
    assert "BMI" in data["unreadable"], data
    # ‏وماحسبهاش من الطول والوزن: الحساب مش قراية
    assert data["weight"] and data["height"], data


def test_a_number_outside_the_possible_is_thrown_away():
    """‏موديل بيقرا صورة مشوشة ممكن يطلّع "الوزن ٧٥٠ كجم". الرقم ده مايتحطش
    في خانة، بيتشال ويتقال للدكتور إنه اتشال."""
    payload = dict(GOOD, weight=750.0, height=16.0, age=340, bmr=99000)
    sent, undo = _stub(payload)
    try:
        data = lab_report.read_report(PNG, "image/png")
    finally:
        undo()
    for field in ("weight", "height", "age", "bmr"):
        assert data[field] is None, "%s = %r اتحط وهو مستحيل" % (field, data[field])
        assert field in data["dropped"], data["dropped"]
    # ‏وباقي الأرقام المعقولة لسه موجودة
    assert data["fat_pct"] == 38.2, data


def test_a_photo_that_is_not_a_report_is_refused():
    """‏صورة أي حاجة تانية مالهاش تملّي الفورم بأي رقم."""
    payload = dict((k, None) for k in GOOD)
    payload.update({"is_body_report": False, "extras": [], "unreadable": []})
    sent, undo = _stub(payload)
    try:
        lab_report.read_report(PNG, "image/png")
    except lab_report.ReportError as e:
        assert "مش ورقة تحليل" in str(e), str(e)
    else:
        assert False, "‏قبل صورة مش ورقة تحليل"
    finally:
        undo()


def test_a_sheet_with_nothing_readable_is_refused():
    payload = dict(GOOD)
    for field in ("weight", "height", "fat_pct", "bmi", "bmr", "age"):
        payload[field] = None
    sent, undo = _stub(payload)
    try:
        lab_report.read_report(PNG, "image/png")
    except lab_report.ReportError as e:
        assert "مقدرتش أقرا" in str(e), str(e)
    else:
        assert False, "‏قبل ورقة مقراش منها ولا رقم"
    finally:
        undo()


def test_a_refusal_or_broken_reply_does_not_become_data():
    sent, undo = _stub(GOOD, stop_reason="refusal")
    try:
        lab_report.read_report(PNG, "image/png")
    except lab_report.ReportError as e:
        assert "رفضت" in str(e), str(e)
    else:
        assert False, "‏رفض الخدمة اتعامل معاه كأنه بيانات"
    finally:
        undo()

    sent, undo = _stub("this is not json at all")
    try:
        lab_report.read_report(PNG, "image/png")
    except lab_report.ReportError as e:
        assert "مش مفهوم" in str(e), str(e)
    else:
        assert False, "‏رد مش JSON اتعامل معاه كأنه بيانات"
    finally:
        undo()


def test_the_guards_speak_arabic_and_come_before_the_call():
    """‏الرسايل دي الدكتور هو اللي بيقراها، ولازم تقوله يعمل إيه."""
    os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        lab_report.read_report(PNG, "image/png")
    except lab_report.ReportError as e:
        assert "ANTHROPIC_API_KEY" in str(e), str(e)
    else:
        assert False, "‏نادى الخدمة من غير مفتاح"

    os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
    try:
        lab_report.read_report(b"x" * (lab_report.MAX_IMAGE_BYTES + 1), "image/png")
    except lab_report.ReportError as e:
        assert "كبيرة" in str(e), str(e)
    else:
        assert False, "‏قبل صورة أكبر من الحد"

    try:
        lab_report.read_report(PNG, "application/pdf")
    except lab_report.ReportError as e:
        assert "صورة مدعومة" in str(e), str(e)
    else:
        assert False, "‏قبل ملف مش صورة"
    os.environ.pop("ANTHROPIC_API_KEY", None)


def test_the_schema_is_a_valid_schema_that_allows_nulls():
    """‏لو خانة مش بتقبل null، الموديل هيضطر يحط رقم -- يعني يخمّن."""
    schema = lab_report._SCHEMA
    assert schema["additionalProperties"] is False
    for field in ("weight", "height", "fat_pct", "bmi", "bmr", "age", "name"):
        types = schema["properties"][field]["type"]
        assert "null" in types, "‏%s مش بتقبل فاضي -- الموديل هيخمّن" % field
        assert field in schema["required"], field
    # ‏والـprompt نفسه لازم يقول القاعدة صريحة
    assert "never guess" in lab_report._PROMPT.lower(), "‏الـprompt مش بيمنع التخمين"
    assert "Do not compute" in lab_report._PROMPT, "‏الـprompt مش بيمنع الحساب"


def test_the_route_is_staff_only_and_answers_in_json():
    import app as A
    A.app.config["WTF_CSRF_ENABLED"] = False
    anon = A.app.test_client()
    r = anon.post("/api/read-report",
                  data={"image": (io.BytesIO(PNG), "s.png")})
    assert r.status_code in (301, 302, 401, 403), (
        "‏أي حد من برّه قدر يرفع صورة: %s" % r.status_code)

    import re
    staff = A.app.test_client()
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                    staff.get("/login").get_data(as_text=True)).group(1)
    staff.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                               "password": "pw123456", "csrf_token": tok})
    r = staff.post("/api/read-report", data={})
    assert r.status_code == 400 and r.get_json()["ok"] is False, r.status_code

    sent, undo = _stub(GOOD)
    try:
        r = staff.post("/api/read-report",
                       data={"image": (io.BytesIO(PNG), "sheet.png")})
    finally:
        undo()
        os.environ.pop("ANTHROPIC_API_KEY", None)
    body = r.get_json()
    assert r.status_code == 200 and body["ok"], body
    assert body["fields"]["weight"] == 78.4, body
    # ‏الـBMR بيرجع باسمه: الفورم عنده TDEE، والاتنين مش نفس الحاجة
    assert body["fields"].get("bmr") == 1420, body
    assert "tdee" not in body["fields"], "‏الـBMR اتحط مكان الـTDEE"


def test_the_form_offers_the_camera_and_never_silently_fills():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html = open(os.path.join(here, "templates", "generate.html"),
                encoding="utf-8").read()
    assert 'id="rpFile"' in html, "‏مافيش خانة رفع صورة"
    assert 'capture="environment"' in html, (
        "‏مش بيفتح الكاميرا على الموبايل -- الدكتور هيدوّر في معرض الصور")
    assert 'accept="image/*"' in html, "‏بيقبل أي ملف"
    script = html[html.index("// ═══ قراءة ورقة التحليل من صورة"):]
    script = script[:script.index("// ===== معاينة تدوير السعرات")]
    for word in ("data.missing", "dropped", "لسه ناقص"):
        assert word in script, (
            "‏الواجهة مش بتعرض %s -- الدكتور هيفترض إن كله اتملى" % word)
    assert "راجع الأرقام قبل التوليد" in script, (
        "‏مافيش تنبيه يراجع -- القراءة من صورة مش معصومة")


def test_it_never_says_it_could_not_read_a_field_that_is_filled():
    """‏الرسالة كانت بتقول "مقدرتش أقرا BMI" والخانة فيها ٢٨.٨.

    الصفحة بتحسب الـBMI من الطول والوزن، فالخانة بتتملى لوحدها. الرسالة
    اللي بتقول للدكتور "اكتبه إنت" وهو مكتوب قدامه بتخليه يشك في اللي
    شايفه -- وده نفس نوع الغلط اللي كان في ورقة السيلياك: الجدول بيقول
    حاجة والنصيحة جنبه بتقول عكسها.

    الواجهة بقت بتفلتر على اللي **لسه فاضي فعلاً** بعد الملء.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html = open(os.path.join(here, "templates", "generate.html"),
                encoding="utf-8").read()
    script = html[html.index("// ═══ قراءة ورقة التحليل من صورة"):]
    script = script[:script.index("// ===== معاينة تدوير السعرات")]
    assert "data.missing" in script, (
        "‏الواجهة لسه بتعرض كلام الموديل الحر بدل الخانات الفاضية فعلاً")
    assert "=== ''" in script or '=== \'\'' in script, (
        "‏مافيش فلترة على اللي لسه فاضي")

    # ‏والسيرفر لازم يبعت أسماء الخانات، مش نص حر
    src = open(os.path.join(here, "routes_plans.py"), encoding="utf-8").read()
    block = src[src.index("def read_report_image"):]
    block = block[:block.index("@bp.route", 10)]
    assert '"missing"' in block, "‏الراوت مش بيبعت الخانات الفاضية بأسمائها"
    assert '"bmi"' in block, "‏الـBMI مش في القايمة"


def test_the_bmr_is_offered_not_written_into_the_tdee_box():
    """‏الـBMR طاقة السكون، والـTDEE هو BMR × معامل النشاط. لو حطينا الرقم
    المطبوع في خانة الـTDEE، الخطة تتحسب على طاقة السكون -- يعني العميل
    ياكل أقل من احتياجه بحوالي الثلث."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html = open(os.path.join(here, "templates", "generate.html"),
                encoding="utf-8").read()
    script = html[html.index("// ═══ قراءة ورقة التحليل من صورة"):]
    script = script[:script.index("// ===== معاينة تدوير السعرات")]
    assert "tdeeField" not in script, (
        "‏الواجهة بتكتب في خانة الـTDEE -- الرقم المطبوع BMR مش TDEE")
    assert "recomputeTdee()" in script, "‏الصفحة مش بتحسب الـTDEE بعد الملء"
    assert "f.bmr" in script, "‏الـBMR مش معروض للدكتور يقارن"


def test_the_page_says_it_is_off_before_you_waste_a_photo():
    """‏الزرار الشغّال اللي بيرد "مش مفعّلة" بعد الرفع معناه إن الدكتور صوّر
    ورفع واستنى -- مقابل معلومة السيرفر عارفها قبل ما الصفحة تتحمّل."""
    import re
    import app as A
    A.app.config["WTF_CSRF_ENABLED"] = False
    client = A.app.test_client()
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                    client.get("/login").get_data(as_text=True)).group(1)
    client.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                                "password": "pw123456", "csrf_token": tok})

    os.environ.pop("ANTHROPIC_API_KEY", None)
    off = client.get("/generate").get_data(as_text=True)
    assert 'id="rpFile"' not in off, (
        "‏الزرار ظاهر وهو مش مفعّل -- الدكتور هيصوّر ويرفع بلا فايدة")
    assert "مش مفعّلة" in off, "‏الصفحة مش بتقول إنها مش مفعّلة"
    assert "ANTHROPIC_API_KEY" in off, "‏مش بتقول الحل"

    os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
    try:
        on = client.get("/generate").get_data(as_text=True)
    finally:
        os.environ.pop("ANTHROPIC_API_KEY", None)
    assert 'id="rpFile"' in on, "‏المفتاح متحط والزرار مش ظاهر"
    assert "مش مفعّلة" not in on, "‏لسه بيقول مش مفعّلة والمفتاح متحط"


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
            print(f"  FAIL  {name}\n        {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

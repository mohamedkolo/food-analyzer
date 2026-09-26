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


def _sheet_bytes(tilt=-2.0, blur=0.9, quality=70):
    """‏ورقة InBody للاختبار: مايلة ومشوشة ومضغوطة زي صورة موبايل."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
        bold = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception:
        font = bold = None
    rows = [("ID", "Ahmed Ali"), ("Gender", "Male"), ("Age", "41"),
            ("Height", "174.0 cm"), ("Weight", "95.6 kg"),
            ("PBF Percent Body Fat", "31.4 %"), ("BMI", "31.6 kg/m2"),
            ("BMR Basal Metabolic Rate", "1850 kcal"),
            ("Target Weight", "72.0 kg"), ("Weight Control", "-23.6 kg")]
    img = Image.new("RGB", (760, 120 + 48 * len(rows)), "white")
    draw = ImageDraw.Draw(img)
    draw.text((30, 25), "InBody 270 - Body Composition Analysis",
              fill="black", font=bold)
    draw.line([(25, 60), (735, 60)], fill="black", width=2)
    y = 85
    for label, value in rows:
        draw.text((35, y), label, fill="black", font=font)
        draw.text((470, y), value, fill="black", font=font)
        y += 48
    if tilt:
        img = img.rotate(tilt, expand=True, fillcolor="white")
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


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
    # ‏والمشيل بيرجع ومعاه **الرقم اللي اتقرا**، مش اسم الخانة بس: الدكتور
    # كان بيشوف "height, muscle_mass" وبس، فمش هو ولا أنا نعرف القراية
    # شافت إيه ولا إيه اللي محتاج يتصلّح.
    thrown = {d["field"]: d for d in data["dropped"]}
    for field in ("weight", "height", "age", "bmr"):
        assert data[field] is None, "%s = %r اتحط وهو مستحيل" % (field, data[field])
        assert field in thrown, data["dropped"]
        assert thrown[field]["value"] == payload[field], thrown[field]
        assert thrown[field]["low"] is not None, thrown[field]
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


def test_a_corrupt_upload_gets_a_sentence_not_a_crash():
    """‏الرفع من الموبايل بيتقطع عادي. الملف الناقص كان بيرفع OSError من
    جوّه محرّك القراءة ويطلع خطأ 500 فاضي."""
    os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        lab_report.read_report(PNG, "image/png")   # ‏ترويسة PNG وبس
    except lab_report.ReportError as e:
        assert "مش سليمة" in str(e) or "مقدرتش أقرا" in str(e), str(e)
    else:
        assert False, "‏قبل صورة تالفة"


def test_the_guards_speak_arabic_and_come_before_the_call():
    """‏الرسايل دي الدكتور هو اللي بيقراها، ولازم تقوله يعمل إيه."""
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
    # ‏وصورة حقيقية من غير أي مفتاح: القراءة المحلية بترد ٢٠٠
    os.environ.pop("ANTHROPIC_API_KEY", None)
    r = staff.post("/api/read-report",
                   data={"image": (io.BytesIO(_sheet_bytes()), "s.jpg")})
    body = r.get_json()
    assert r.status_code == 200 and body["ok"], body
    assert body["fields"]["weight"] == 95.6, body

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
    import re
    whole = html[html.index("// ═══ قراءة ورقة التحليل من صورة"):]
    whole = whole[:whole.index("// ===== معاينة تدوير السعرات")]
    # ‏القراءة نفسها مالهاش أي شغل بخانة الـTDEE
    script = whole[:whole.index("// ═══ اشرح الفحص للعميل")]
    assert "tdeeField" not in script, (
        "‏القراءة بتلمس خانة الـTDEE -- الرقم المطبوع BMR مش TDEE")
    assert "recomputeTdee()" in script, "‏الصفحة مش بتحسب الـTDEE بعد الملء"
    assert "f.bmr" in script, "‏الـBMR مش معروض للدكتور يقارن"
    # ‏شرح الفحص **بيقرا** الـTDEE عشان يقوله للعميل، وده مطلوب. اللي
    # ممنوع هو الكتابة فيه: الشرط الأول كان بيمنع أي ذكر، فكان بيمنع
    # القراءة كمان. ده بيمنع الكتابة بالظبط.
    for hit in re.finditer("tdeeField", whole):
        after = whole[hit.end():hit.end() + 40]
        assert not re.match(r"""['"]?\s*\)?\s*\.?value\s*=[^=]""", after), (
            "‏حاجة بتكتب في خانة الـTDEE: %s" % after[:40])


def test_the_camera_works_without_any_api_key():
    """‏الميزة كانت مقفولة لحد ما الدكتور يعمل حساب ويحط مفتاح API.

    المفتاح مربوط بحسابه وفيزته، فمكانش فيه حاجة أقدر أعملها -- الميزة
    تفضل مقفولة. القراءة بقت بتحصل على السيرفر نفسه، مجاناً، والصورة
    مابتخرجش منه، فالزرار شغّال من غير أي مفتاح.
    """
    import re
    import app as A
    import ocr_report
    # ‏المكتبة في ملف لوحدها (requirements-ocr.txt)، فمش مضمون إنها متركّبة
    # على كل جهاز. الاختبار بيقيس الحالتين: متركّبة -> زرار، مش متركّبة ->
    # سطر بيقول مش مفعّلة. اللي مايصحّش هو الزرار اللي مايشتغلش.
    installed = ocr_report.available()

    A.app.config["WTF_CSRF_ENABLED"] = False
    client = A.app.test_client()
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                    client.get("/login").get_data(as_text=True)).group(1)
    client.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                                "password": "pw123456", "csrf_token": tok})

    os.environ.pop("ANTHROPIC_API_KEY", None)
    html = client.get("/generate").get_data(as_text=True)
    if installed:
        assert 'id="rpFile"' in html, "‏الزرار مش ظاهر والقراءة المحلية شغالة"
        assert "مش مفعّلة" not in html, "‏لسه بيقول مش مفعّلة وهي مفعّلة"
    else:
        assert 'id="rpFile"' not in html, (
            "‏زرار شغّال والقراءة مش متركّبة -- الدكتور هيصوّر بلا فايدة")
        assert "مش مفعّلة" in html, "‏مش بيقول إنها مش مفعّلة"


def test_the_local_reading_is_the_default_and_the_key_upgrades_it():
    """‏الطريقين لازم يرجّعوا نفس الشكل، والافتراضي هو المحلي."""
    os.environ.pop("ANTHROPIC_API_KEY", None)
    data = lab_report.read_report(_sheet_bytes(), "image/jpeg")
    assert data["engine"] == "local", data.get("engine")
    assert data["weight"] == 95.6 and data["height"] == 174.0, data

    sent, undo = _stub(GOOD)          # ‏بيحط مفتاح
    try:
        data = lab_report.read_report(PNG, "image/png")
    finally:
        undo()
        os.environ.pop("ANTHROPIC_API_KEY", None)
    assert data["engine"] == "api", data.get("engine")
    assert set(("weight", "height", "unreadable", "dropped")) <= set(data), data



def test_a_photo_cannot_take_the_whole_site_down():
    """‏النموذج بياخد ~٢٥٦ ميجا، والاستضافة المجانية عندها ٥١٢ والتطبيق
    ماشي فيهم. لو القراءة اتعملت جوّه السيرفر، أول صورة ممكن توصل للحد
    فالنظام يقتل العملية -- يعني الموقع كله يقع، مش القراءة بس.

    فالقراءة بتتعمل في عملية منفصلة: رامها بتموت معاها، وعملية الموقع
    مابتكبرش.
    """
    import resource
    import ocr_report

    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    ocr_report.read(_sheet_bytes())
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    grew = (after - before) // 1024
    assert grew < 80, (
        "‏عملية الموقع كبرت %d ميجا -- القراءة بتحصل جوّاها" % grew)


def test_the_system_killing_the_reader_is_a_sentence_not_a_crash():
    """‏لو النظام قتل العملية (رام)، الموقع لسه واقف والدكتور يفهم."""
    import subprocess
    import ocr_report

    class Killed:
        returncode = -9
        stdout = b""
        stderr = b""

    real = subprocess.run
    subprocess.run = lambda *a, **k: Killed()
    try:
        ocr_report.read(_sheet_bytes())
    except RuntimeError as e:
        assert "رام" in str(e), str(e)
    else:
        assert False, "‏العملية اتقتلت والكود كمّل كأن مافيش حاجة"
    finally:
        subprocess.run = real


def test_a_reading_that_hangs_gives_up_with_a_message():
    import subprocess
    import ocr_report

    real = subprocess.run

    def hang(*a, **k):
        raise subprocess.TimeoutExpired("cmd", ocr_report.READ_TIMEOUT)

    subprocess.run = hang
    try:
        ocr_report.read(_sheet_bytes())
    except RuntimeError as e:
        assert "وقت" in str(e), str(e)
    else:
        assert False, "‏القراءة علّقت ومافيش مهلة"
    finally:
        subprocess.run = real


# ═══════════════════════════════════════════════════════════════════════
# ‏القراءة في المتصفح
#
# ‏الميزة فضلت مقفولة مرتين: مرة عشان محتاجة مفتاح API مربوط بحساب وفيزة،
# ومرة عشان مكتبة القراءة على السيرفر بتاخد ~٢٨٠ ميجا رام والاستضافة
# عندها ٥١٢. القراءة بقت في متصفح الدكتور: مافيش مفتاح ولا تركيب ولا
# إعداد استضافة، والصورة مابتخرجش من موبايله خالص.
#
# ‏اللي بيوصل للسيرفر هو الكلام المقروء، والتفسير كله هنا -- فالحواجز
# اللي بتمنع الرقم الغلط بتتقاس هنا مرة واحدة لكل المحرّكات.
# ═══════════════════════════════════════════════════════════════════════

def _fixture():
    """‏كلام حقيقي طلع من محرّك المتصفح (Chromium) على ١١ صورة.

    مش مكتوب بإيدي: ده مخرج المحرّك الفعلي على نفس الصور، متسجّل عشان
    الاختبار يقيس القراءة الحقيقية من غير ما يفتح متصفح.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    with io.open(os.path.join(here, "data", "browser_passes.json"),
                 encoding="utf-8") as fh:
        return json.load(fh)


TRUTH = {"age": 29, "height": 165.0, "weight": 78.4, "fat_pct": 38.2,
         "bmi": 28.8, "bmr": 1420, "gender": "female"}


def test_the_camera_works_with_no_key_and_nothing_installed():
    data = lab_report.read_browser([[
        ["Gender", "Female"], ["Age", "29"], ["Height", "165.0", "cm"],
        ["Weight", "78.4", "kg"], ["PBF", "Percent", "Body", "Fat", "38.2%"],
        ["BMI", "28.8", "kg/m2"], ["BMR", "Basal", "Metabolic", "Rate",
                                   "1420", "kcal"],
    ]])
    for key, want in TRUTH.items():
        assert data.get(key) == want, "‏%s قريت %r بدل %r" % (key, data.get(key), want)
    assert data["engine"] == "browser", data["engine"]


def test_a_target_weight_is_never_taken_as_the_weight():
    """‏"Target Weight 60.0" لو اتقرت كوزن، الخطة تتحسب على وزن العميل
    المستهدف مش وزنه -- ١٨ كيلو فرق في المثال ده."""
    data = lab_report.read_browser([[
        ["Weight", "78.4", "kg"], ["Target", "Weight", "60.0", "kg"],
        ["Ideal", "Weight", "58.0", "kg"], ["Weight", "Control", "-18.4", "kg"],
    ]])
    assert data["weight"] == 78.4, data["weight"]


def test_two_labels_on_one_line_do_not_swap_the_numbers():
    """‏القراءة ساعات بتلزق سطرين في واحد. الرقم بيتاخد **بعد** العنوان."""
    import ocr_report
    found = ocr_report.parse_lines([
        ["Height", "165.0", "cm", "Weight", "78.4", "kg"]])
    assert found.get("weight") == 78.4, found
    found = ocr_report.parse_lines([
        ["Weight", "78.4", "kg", "Height", "165.0", "cm"]])
    assert found.get("weight") == 78.4, found


def test_a_unit_is_not_a_reading():
    """‏"kg/m2" فيها رقم ٢. لولا الشرط، الـBMI كان يبقى ٢."""
    import ocr_report
    for unit in ("kg/m2", "kg", "cm", "kcal", "m2", "%"):
        assert ocr_report._value_word(unit) is None, unit
    for value, want in (("38.2%", 38.2), ("33.0L", 33.0), ("9", 9.0),
                        ("(78.4", 78.4), ("1420", 1420.0)):
        assert ocr_report._value_word(value) == want, value
    found = ocr_report.parse_lines([["BMI", "kg/m2", "28.8"]])
    assert found.get("bmi") == 28.8, found


def test_the_two_readings_must_agree_or_the_field_is_dropped():
    """‏الصورة بتتقرا مرتين بمعالجتين. اختلفوا في رقم؟ يتشال.

    ليه: النقطة العشرية هي أول حاجة بتضيع، و"38.2" بتبقى "382". لو واحدة
    قالت ٣٨.٢ والتانية ٣٨٢، إحنا مانعرفش مين الصح -- والدكتور يكتبها
    بإيده أحسن ألف مرة من رقم غلط ماشي في خطة.
    """
    import ocr_report
    agree = ocr_report.merge_found([{"weight": 78.4}, {"weight": 78.4}])
    assert agree["weight"] == 78.4, agree
    clash = ocr_report.merge_found([{"weight": 78.4}, {"weight": 87.4}])
    assert "weight" not in clash, clash
    # ‏واحدة قرأت والتانية لأ -> بتتاخد. مافيش خلاف هنا.
    one = ocr_report.merge_found([{"bmi": 28.8}, {}])
    assert one["bmi"] == 28.8, one
    sex = ocr_report.merge_found([{"gender": "female"}, {"gender": "male"}])
    assert "gender" not in sex, sex


def test_an_arabic_sheet_says_so_instead_of_guessing():
    """‏محرّك المتصفح بيقرا إنجليزي. ورقة عربية = أرقام بدون عناوين،
    ومانعرفش الرقم ده الوزن ولا الطول -- فمابنخمّنش."""
    try:
        lab_report.read_browser([[["78.4"], ["165.0"], ["29"]]])
    except lab_report.ReportError as e:
        assert "مش عارف" in str(e) or "مش إنجليزي" in str(e), str(e)
    else:
        raise AssertionError("‏ورقة بأرقام بدون عناوين اتقرت")


def test_the_real_engine_output_never_produces_a_wrong_number():
    """‏أهم اختبار في الملف: مخرج المحرّك الحقيقي على ١١ صورة.

    الصور: ورقة نضيفة، صورة موبايل مايلة، ميل ١.٥ و٣ و٦ درجات، صورة
    مهزوزة، صورة في ضلمة بتشويش، ظل متدرّج، نص دقة، وورقة عربية.

    المقياس **صفر رقم غلط**، مش عدد الخانات اللي اتملت. الخانة الفاضية
    الدكتور بيشوفها ويكتبها؛ الرقم الغلط بيمشي في حساب السعرات لحد ما
    يوصل للعميل.
    """
    wrong, filled, refused = [], 0, []
    fixture = _fixture()
    for name in sorted(fixture):
        try:
            data = lab_report.read_browser(fixture[name]["passes"])
        except lab_report.ReportError:
            refused.append(name)
            continue
        for key, want in TRUTH.items():
            got = data.get(key)
            if got is None:
                continue
            if got != want:
                wrong.append("%s: %s=%r (الصح %r)" % (name, key, got, want))
            else:
                filled += 1
    assert not wrong, "‏أرقام غلط: " + " | ".join(wrong)
    assert refused == ["sheet_ar"], refused
    # ‏٧ خانات × ١٠ صور. الرقم ده بيقع لو معالجة الصورة أو التفسير رجعوا
    # لورا، من غير ما رقم غلط يظهر.
    assert filled >= 60, "‏القراءة رجعت لورا: %d خانة بس من ٧٠" % filled


def test_a_full_inbody_sheet_does_not_read_a_leg_as_the_height():
    """‏ورقة الدكتور الحقيقية، والباج اللي ظهر منها.

    ‏ورقة الـInBody الكاملة فيها صفوف للأطراف وصفوف متوسطات. والعنوان
    كان بيتطابق كـ**جزء من أي كلمة**، فطلع الآتي على ورقته:

        Right Leg 6.01   ->  الطول = ٦.٠١     ("ht" جوّه "right")
        Average 1324     ->  العمر = ١٣٢٤     ("age" جوّه "average")

    ‏وحدود المعقول شالت الاتنين، فالنتيجة إن ولا خانة اتملت وهو مش عارف
    ليه. الأرقام دي مش مفترضة -- دي اللي الرسالة عرضتها على ورقته.
    """
    import ocr_report
    sheet = [
        ["InBody", "770", "Body", "Composition", "Analysis"],
        ["ID", "Noura", "Sayed"],
        ["Gender", "Female"],
        ["Age", "29"],
        ["Height", "165.0", "cm"],
        ["Weight", "78.4", "kg"],
        ["PBF", "Percent", "Body", "Fat", "38.2", "%"],
        ["BMI", "28.8", "kg/m2"],
        ["SMM", "Skeletal", "Muscle", "Mass", "24.1", "kg"],
        ["BMR", "1420", "kcal"],
        ["Visceral", "Fat", "Level", "9"],
        ["Total", "Body", "Water", "33.0", "L"],
        # ‏الصفوف اللي كانت بتلخبط القراية
        ["Segmental", "Lean", "Analysis"],
        ["Right", "Arm", "2.34", "kg"],
        ["Left", "Arm", "2.28", "kg"],
        ["Trunk", "21.4", "kg"],
        ["Right", "Leg", "6.01", "kg"],
        ["Left", "Leg", "5.94", "kg"],
        ["Average", "1324"],
        ["Percentage", "of", "Standard", "104", "%"],
        ["Weight", "Control", "-18.4", "kg"],
        ["Target", "Weight", "60.0", "kg"],
    ]
    found = ocr_report.parse_lines(sheet)
    assert found.get("height") == 165.0, "‏الطول: %r" % found.get("height")
    assert found.get("age") == 29, "‏العمر: %r" % found.get("age")
    assert found.get("weight") == 78.4, "‏الوزن: %r" % found.get("weight")
    assert found.get("fat_pct") == 38.2, found.get("fat_pct")
    assert found.get("bmi") == 28.8, found.get("bmi")
    assert found.get("muscle_mass") == 24.1, found.get("muscle_mass")
    assert found.get("body_water") == 33.0, found.get("body_water")
    assert found.get("visceral_fat") == 9, found.get("visceral_fat")
    assert found.get("bmr") == 1420, found.get("bmr")

    # ‏وكل الخانات دي بتعدّي حدود المعقول، فالدكتور بيلاقيها متملّية فعلاً
    data = lab_report.read_browser([sheet])
    assert data["dropped"] == [], data["dropped"]
    for field, want in (("height", 165.0), ("weight", 78.4), ("age", 29),
                        ("fat_pct", 38.2), ("bmi", 28.8)):
        assert data[field] == want, (field, data[field])


def test_a_label_inside_another_word_is_not_a_label():
    """‏الحدود دي هي التصليح، فمقفولة باختبار لكل عنوان قصير."""
    import ocr_report
    for line in ("Right Leg 6.01", "Average 1324", "Percentage of Standard 104",
                 "Weight Control -18.4", "Usage 5", "Highlight 12"):
        field, _ = ocr_report._label_form(line)
        assert field is None, "‏%r اتقرا كـ%s" % (line, field)
    # ‏والعناوين القصيرة الحقيقية لسه بتتقرا
    for line, want in (("Ht 165", "height"), ("Wt 78.4", "weight"),
                       ("Age 29", "age"), ("SMM 24.1", "muscle_mass"),
                       ("TBW 33.0", "body_water"), ("BMI 28.8", "bmi"),
                       ("PBF 38.2 %", "fat_pct"), ("VFA 9", "visceral_fat")):
        field, _ = ocr_report._label_form(line)
        assert field == want, "‏%r -> %s (المتوقع %s)" % (line, field, want)


def test_what_the_browser_sends_is_cut_to_known_limits():
    """‏الطلب مفتوح لأي حساب موظف، فالحدود على السيرفر مش في الجافاسكربت."""
    huge = [[["Weight", "78.4", "kg"]] * 5000] * 9
    tidy = lab_report._tidy_passes(huge)
    assert len(tidy) <= lab_report.MAX_PASSES, len(tidy)
    assert len(tidy[0]) <= lab_report.MAX_LINES, len(tidy[0])
    long_word = lab_report._tidy_passes([[["W" * 500, "1"]]])
    assert len(long_word[0][0][0]) <= lab_report.MAX_WORD
    wide = lab_report._tidy_passes([[["x"] * 500]])
    assert len(wide[0][0]) <= lab_report.MAX_WORDS
    for junk in (None, "nope", 5, {"a": 1}):
        try:
            lab_report._tidy_passes(junk)
        except lab_report.ReportError:
            pass
        else:
            raise AssertionError("‏شكل غريب عدّى: %r" % (junk,))
    # ‏سطور فاضية = مافيش قراءة، وبترد جملة مش استثناء
    try:
        lab_report._tidy_passes([[], [[""]]])
    except lab_report.ReportError as e:
        assert "مقدرتش أقرا" in str(e), str(e)
    else:
        raise AssertionError("‏سطور فاضية عدّت")


def test_the_route_takes_the_browser_reading_and_not_the_image():
    import re
    import app as A
    A.app.config["WTF_CSRF_ENABLED"] = False
    anon = A.app.test_client()
    r = anon.post("/api/read-report", json={"passes": [[["Weight", "78.4"]]]})
    assert r.status_code in (301, 302, 401, 403), r.status_code

    staff = A.app.test_client()
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                    staff.get("/login").get_data(as_text=True)).group(1)
    staff.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                               "password": "pw123456", "csrf_token": tok})
    os.environ.pop("ANTHROPIC_API_KEY", None)
    r = staff.post("/api/read-report", json={"passes": _fixture()["sheet_clean"]["passes"]})
    body = r.get_json()
    assert r.status_code == 200 and body["ok"], body
    assert body["fields"]["weight"] == 78.4, body
    assert body["fields"]["height"] == 165.0, body
    assert body["fields"].get("bmr") == 1420, body
    # ‏طلب فاضي: جملة مفهومة، مش ٥٠٠
    r = staff.post("/api/read-report", json={})
    assert r.status_code == 400 and r.get_json()["ok"] is False, r.status_code


def test_the_engine_files_are_in_the_deploy_and_served_compressed():
    """‏لو ملف من دول ناقص، الزرار بيظهر ويفضل بيلف. فبنقيسه."""
    import routes_plans
    assert routes_plans.report_engine_ready(), "‏ملفات المحرّك ناقصة"

    import app as A
    client = A.app.test_client()
    for name in ("tesseract.min.js", "worker.min.js",
                 "tesseract-core-simd-lstm.wasm.js",
                 "tesseract-core-lstm.wasm.js"):
        r = client.get("/ocr/" + name)
        assert r.status_code == 200, (name, r.status_code)
        assert r.headers.get("Content-Encoding") == "gzip", name
        assert len(r.get_data()) > 5000, (name, len(r.get_data()))
        assert "max-age" in (r.headers.get("Cache-Control") or ""), name
    # ‏ملف اللغة بيتبعت مضغوط **كما هو**: المكتبة بتفكّه بنفسها وبتدوّر
    # على بصمة الـgzip جوّه الملف. Content-Encoding كان بيضيّعها.
    lang = client.get("/ocr/eng.traineddata.gz")
    assert lang.status_code == 200 and "Content-Encoding" not in lang.headers
    assert lang.get_data()[:2] == b"\x1f\x8b", "‏ملف اللغة مش gzip"


def test_the_asset_route_serves_nothing_but_the_engine():
    import app as A
    client = A.app.test_client()
    for path in ("/ocr/nope.js", "/ocr/../core.py", "/ocr/../../etc/passwd",
                 "/ocr/", "/ocr/SOURCE.txt"):
        r = client.get(path)
        assert r.status_code in (301, 308, 404), (path, r.status_code)


def test_the_security_policy_lets_the_engine_run():
    """‏المتصفح بيرفض WebAssembly من غير 'wasm-unsafe-eval'، والرفض
    صامت: الزرار يفضل بيلف والدكتور مش عارف ليه."""
    import core
    assert "'wasm-unsafe-eval'" in core.CSP, core.CSP
    assert "worker-src" in core.CSP, core.CSP


def test_the_page_reads_in_the_browser_and_keeps_the_image_there():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(here, "templates", "generate.html"),
                 encoding="utf-8") as fh:
        page = fh.read()
    assert "js/report_ocr.js" in page, "‏الصفحة مش بتحمّل محرّك القراءة"
    assert "window.ReportOCR.read" in page, "‏الصفحة مش بتنادي القراءة"
    # ‏الصورة عمرها ما تتبعت: الطلب JSON فيه الكلام بس
    assert "body.append('image'" not in page, "‏الصورة لسه بتتبعت للسيرفر"
    assert "JSON.stringify({passes:" in page, "‏الطلب مش بيبعت الكلام"
    # ‏والدكتور لازم يعرف إن الصورة مش بتخرج من جهازه
    assert "مابتطلعش من الموبايل" in page, "‏الصفحة مش بتقول إن الصورة مابتخرجش"

    with io.open(os.path.join(here, "static", "js", "report_ocr.js"),
                 encoding="utf-8") as fh:
        js = fh.read()
    # ‏كل حاجة من نفس الموقع: مافيش CDN يقع ولا خدمة تشوف الصورة
    assert "cdn" not in js.lower(), "‏المحرّك بينزّل من خدمة برّه"
    assert "workerBlobURL: false" in js, "‏الـworker من blob بيتخانق مع CSP"
    # ‏قراءتين: واحدة للصورة كما هي وواحدة بعد تحديد الحدود
    assert "sharpenCanvas" in js and "passes.push" in js


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

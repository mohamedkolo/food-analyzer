# -*- coding: utf-8 -*-
"""‏شرح ورقة التحليل للعميل.

الدكتور طلب خطوة زيادة: بعد ما الورقة تتقرا، «تقولى السيناريو -- اشرح
الورقه ازاى للعميل، ايه النقاط الى اركز عليها».

القاعدة هنا زي قاعدة القراءة: **مافيش رقم مخمّن، ومافيش حكم مش متحسوب.**
كل نتيجة بتيجي ومعاها الرقم والنطاق اللي اتقارن بيه، وأي نطاق بيفرق بين
الذكر والأنثى مابيتحكمش فيه لو النوع مش مختار -- حكم بالغلط أسوأ من
مفيش حكم.

Run with:  python3 tests/test_report_explaining.py
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_explain_test.db"

import body_read      # noqa: E402

WOMAN = {"gender": "انثى", "weight": 78.4, "height": 165.0, "age": 29,
         "fat_pct": 38.2, "bmi": 28.8, "bmr": 1420, "muscle_mass": 24.1,
         "visceral_fat": 9, "body_water": 33.0}


def _row(result, needle):
    for row in result["rows"]:
        if needle in row["label"]:
            return row
    return None


def _text(result):
    return body_read.as_text(result)


def test_the_weight_is_split_by_arithmetic_not_by_opinion():
    """‏أهم سطر في الشرح: الوزن ده كام دهون وكام غير دهون.

    الرقمين لازم يجمعوا الوزن بالظبط، وإلا الدكتور بيقول للعميل رقم
    مش صح قدامه على الورقة.
    """
    out = body_read.explain(WOMAN)
    row = _row(out, "نسبة الدهون")
    assert row is not None, out["rows"]
    fat = 78.4 * 38.2 / 100.0
    assert "%.1f" % fat in row["means"], (row["means"], fat)
    assert "%.1f" % (78.4 - fat) in row["means"], row["means"]
    # ‏والجملة الأولى بتقول نفس الرقمين
    assert "%.1f" % fat in out["headline"], out["headline"]


def test_the_ranges_are_the_ones_for_that_sex():
    """‏٣٠٪ دهون: مقبولة للأنثى، ونطاق سمنة للذكر. نفس الرقم وحكم مختلف."""
    she = body_read.explain(dict(WOMAN, fat_pct=30.0))
    he = body_read.explain(dict(WOMAN, gender="ذكر", fat_pct=30.0))
    assert _row(she, "نسبة الدهون")["kind"] == "watch", _row(she, "نسبة الدهون")
    assert _row(he, "نسبة الدهون")["kind"] == "high", _row(he, "نسبة الدهون")


def test_without_the_sex_it_shows_the_number_and_refuses_the_verdict():
    """‏النطاقات بتفرق ١٠٪ بين الذكر والأنثى. من غير النوع مانحكمش."""
    out = body_read.explain({k: v for k, v in WOMAN.items() if k != "gender"})
    row = _row(out, "نسبة الدهون")
    assert row["value"] == "38.2", row
    assert row["band"] is None, row
    assert out["targets"] == [], out["targets"]
    assert any("النوع مش مختار" in c for c in out["caveats"]), out["caveats"]
    # ‏وبرضه بيقسّم الوزن: التقسيم حساب مش نطاق
    assert "29.9" in out["headline"], out["headline"]


def test_the_goal_is_the_weight_at_a_fat_percent_not_a_guess():
    """‏الوزن عند نسبة دهون معيّنة = الكتلة الخالية ÷ (١ - النسبة).

    ده الرقم اللي بيحوّل «عايز أنزل» لهدف محدد، ولازم يبقى محسوب مش مقرّب.
    """
    out = body_read.explain(WOMAN)
    assert out["targets"], out
    lean = 78.4 - (78.4 * 38.2 / 100.0)
    first = out["targets"][0]
    want = lean / (1.0 - float(first["fat_pct"]) / 100.0)
    assert abs(float(first["weight"]) - want) < 0.1, (first, want)
    assert abs(float(first["drop"]) - (78.4 - want)) < 0.1, first
    # ‏هدفين: يخرج من نطاق السمنة، وبعده وسط النطاق الصحي
    assert len(out["targets"]) == 2, out["targets"]
    assert float(out["targets"][1]["fat_pct"]) < float(first["fat_pct"])


def test_a_goal_already_reached_is_not_offered():
    """‏عميلة نسبتها ٢٤٪: مانقولهاش «انزلي لـ٣١٪»."""
    out = body_read.explain(dict(WOMAN, fat_pct=24.0))
    for target in out["targets"]:
        assert float(target["fat_pct"]) < 24.0, out["targets"]


def test_visceral_fat_comes_first_when_it_is_high():
    """‏دي الرقم المرتبط بالسكر والضغط ودهون الكبد، فبيبقى أول نقطة."""
    out = body_read.explain(dict(WOMAN, visceral_fat=12))
    assert out["focus"], out
    assert "الحشوية" in out["focus"][0]["title"], out["focus"][0]
    # ‏ولو طبيعي، مابيبقاش نقطة تركيز خالص
    calm = body_read.explain(dict(WOMAN, visceral_fat=6))
    assert not any("الحشوية" in f["title"] for f in calm["focus"]), calm["focus"]


def test_a_normal_weight_with_high_fat_is_not_missed():
    """‏الحالة اللي الميزان بيخفيها تماماً: BMI طبيعي ودهون عالية.

    من غير السطر ده الدكتور ممكن يقول «وزنك تمام» والدهون ٣٥٪.
    """
    out = body_read.explain(dict(WOMAN, weight=60.0, height=163.0,
                                 bmi=None, fat_pct=35.0))
    titles = " ".join(f["title"] for f in out["focus"])
    assert "وزنه طبيعي ودهونه عالية" in titles, out["focus"]


def test_muscle_carrying_the_weight_is_not_called_obesity():
    """‏ذكر BMI ٢٩ ودهون ١٤٪: الزيادة عضل. مانشتغلش على رقم الـBMI."""
    out = body_read.explain({"gender": "ذكر", "weight": 92.0, "height": 178.0,
                             "fat_pct": 14.0})
    titles = " ".join(f["title"] for f in out["focus"])
    assert "BMI" in titles, out["focus"]
    assert "وزنه طبيعي ودهونه عالية" not in titles, out["focus"]


def test_low_muscle_becomes_protect_the_muscle():
    """‏العضل القليل نسبةً للطول بيغيّر الخطة: بروتين ومقاومة، مش كارديو بس."""
    out = body_read.explain(dict(WOMAN, muscle_mass=15.0))
    titles = " ".join(f["title"] for f in out["focus"])
    assert "حماية العضل" in titles, out["focus"]
    do = " ".join(f["do"] for f in out["focus"])
    assert "بروتين" in do and "مقاومة" in do, do


def test_the_water_is_read_against_lean_mass_not_the_weight():
    """‏الدهون فيها ماء قليل، فنسبة الماء من الوزن بتبان قليلة غلط.

    ٣٣ لتر من ٧٨.٤ كجم = ٤٢٪ وشكلها مرعب. ومن الكتلة الخالية = ٦٨٪
    وده قريب من الطبيعي. المقياس التاني هو الصح.
    """
    out = body_read.explain(WOMAN)
    row = _row(out, "ماء الجسم")
    lean = 78.4 - (78.4 * 38.2 / 100.0)
    assert "%.1f" % (33.0 / lean * 100.0) in row["means"], row["means"]
    assert "42" not in row["means"], row["means"]
    assert "الكتلة الخالية" in row["means"], row["means"]


def test_a_missing_number_is_said_not_filled_in():
    out = body_read.explain({"gender": "انثى", "weight": 78.4, "height": 165.0})
    assert _row(out, "نسبة الدهون") is None, out["rows"]
    assert any("نسبة الدهون مش مدخّلة" in c for c in out["caveats"]), out["caveats"]
    assert out["targets"] == [], out["targets"]
    # ‏والـBMI بيتحسب من الوزن والطول، فمش ناقص
    assert _row(out, "BMI") is not None, out["rows"]
    body = "".join(str(r) for r in out["rows"])
    assert "38" not in body, "‏رقم مش مدخّل ظهر في الشرح"


def test_every_step_is_a_sentence_to_say_not_an_instruction():
    """‏الدكتور بيقرا من الشاشة والعميل قاعد قدامه.

    ‏الخطوات كانت تعليمات ("ابدأ بالوزن وقوله...")، فكان لازم يترجمها
    بنفسه وسط الكلام. بقت كلام مقول: عنوان (إحنا فين)، والجملة بين
    قوسين، وملاحظة قصيرة له هو.
    """
    for mode in ("free", "first"):
        out = body_read.explain(WOMAN, mode=mode)
        assert len(out["script"]) >= 4, (mode, out["script"])
        for step in out["script"]:
            assert set(step) >= {"label", "say", "note"}, step
            assert step["label"], step
            # ‏الجملة بين قوسين عربية: علامة إنها كلام يتقال زي ما هو
            assert step["say"].startswith("«") and step["say"].rstrip().endswith("»"), \
                step["say"]
            assert len(step["say"]) > 25, step["say"]
    # ‏والترتيب: يفتح، وبعدين يقسّم الوزن، ويقفل بالخطوة الجاية
    free = body_read.explain(WOMAN, mode="free")
    assert "الميزان" in free["script"][0]["say"], free["script"][0]
    assert free["script"][-1]["label"] == "الخطوة الجاية", free["script"][-1]


def test_each_language_stays_in_its_own_language():
    english = body_read.explain(WOMAN, is_ar=False)
    blob = body_read.as_text(english, is_ar=False)
    assert not re.search(r"[؀-ۿ]", blob), [
        line for line in blob.splitlines() if re.search(r"[؀-ۿ]", line)][:3]
    arabic = body_read.as_text(body_read.explain(WOMAN))
    assert re.search(r"[؀-ۿ]", arabic)


def test_the_copy_text_carries_everything_on_the_screen():
    """‏الدكتور بينسخ الشرح ويبعته واتساب. لازم يكون كامل مش نصه."""
    out = body_read.explain(WOMAN)
    blob = _text(out)
    assert out["headline"] in blob
    for row in out["rows"]:
        assert row["label"] in blob, row["label"]
    for item in out["focus"]:
        assert item["title"] in blob and item["do"] in blob, item
    for step in out["script"]:
        assert step["say"] in blob, step["say"]
        assert step["label"] in blob, step["label"]
    for target in out["targets"]:
        assert target["weight"] in blob, target


def test_it_never_claims_to_diagnose():
    out = body_read.explain(WOMAN)
    assert any("مابتشخّص" in c for c in out["caveats"]), out["caveats"]
    assert any("القرار قرارك" in c for c in out["caveats"]), out["caveats"]


def test_junk_numbers_do_not_become_readings():
    for bad in ("", None, "abc", 0, -5, "-3"):
        out = body_read.explain({"gender": "انثى", "weight": 78.4,
                                 "height": 165.0, "fat_pct": bad})
        assert _row(out, "نسبة الدهون") is None, (bad, out["rows"])
    # ‏ومن غير وزن ولا طول: بيقول مش كفاية بدل ما يطلّع صفحة فاضية
    empty = body_read.explain({})
    assert "مش كفاية" in empty["headline"], empty["headline"]
    assert empty["rows"] == [], empty["rows"]


# ═══════════════════════════════════════════════════════════════════════
# ‏السيناريو بيختلف على حسب الحالة
#
#   «لو مفهاش رقم ولا اسم يبقى فحص مجانى يبقى طريقة شرحها يبقى عشان
#    يشترك معايا. اما لو فيها رقم واسم وبيتابع اصلا يبقى السينايرو
#    بيختلف: ايه الى نزل ايه الى حصل وايه الى نمشى عليه صح»
# ═══════════════════════════════════════════════════════════════════════

FOLLOW_PREV = {"weight": 78.4, "height": 165.0, "age": 29, "gender": "انثى",
               "fat_pct": 38.2, "activity": 1.55, "goal_type": "weight_loss",
               "goal_cal": 1400, "visit_no": 2,
               "created_at": "2026-08-20 10:00:00"}
FOLLOW_NOW = {"weight": 74.0, "height": 165.0, "age": 29, "gender": "انثى",
              "fat_pct": 35.0, "activity": 1.55, "goal_type": "weight_loss",
              "goal_cal": 1400}


def _progress(previous=None, current=None):
    import followup
    return followup.assess(previous or FOLLOW_PREV, current or FOLLOW_NOW, "ar")


def _said(out):
    return " ".join(step["say"] for step in out["script"])


def test_a_free_check_ends_by_inviting_them_to_start():
    """‏فحص سريع: العميل ماعندوش خطة، والكلام بيقفل بدعوة محددة."""
    out = body_read.explain(WOMAN, mode="free")
    last = out["script"][-1]
    assert last["label"] == "الخطوة الجاية", last
    assert "نبدأ" in last["say"] and "خطة" in last["say"], last["say"]
    # ‏وفيه خطوة بتقول الفرق بين إنه يعملها لوحده وإنه يعملها معاك
    said = _said(out)
    assert "لوحدك" in said, "‏مافيش كلام عن الفرق اللي بتقدّمه"
    assert "نقيس" in said and "نعدّل" in said, "‏الفرق مش مشروح بالقياس والتعديل"


def test_the_free_check_sells_on_the_numbers_not_on_fear():
    """‏الإقناع من أرقامه اللي قدامه. مافيش كلام عن مرض ولا خطر، ومافيش
    وعد بمدة أقصر من الواقع."""
    out = body_read.explain(WOMAN, mode="free")
    said = _said(out)
    for scare in ("خطر", "مرض", "سرطان", "هتموت", "مضمون", "نهائي", "أسبوع واحد"):
        assert scare not in said, "‏تهويل أو وعد في الكلام: %s" % scare
    # ‏المدة الحقيقية موجودة، والمعدل مذكور
    assert "أسبوع" in said, said
    assert "نص في المية" in said or "٠.٥" in said, "‏المعدل الواقعي مش مذكور"
    # ‏والهدف رقم محسوب، وبيقول إنه محسوب
    assert "محسوب" in said, "‏مش بيقول إن الرقم محسوب مش تقدير"


def test_a_follow_up_opens_with_the_result_and_says_what_moved():
    """‏«ايه الى نزل ايه الى حصل» -- الرقم الأول، وقبل أي كلام."""
    out = body_read.explain(FOLLOW_NOW, mode="followup",
                            progress=_progress(), visit_no=3)
    assert out["mode"] == "followup" and out["visit_no"] == 3, out["mode"]
    assert out["script"][0]["label"] == "الافتتاح", out["script"][0]
    assert "النتيجة" in out["script"][0]["say"], out["script"][0]["say"]

    moved = out["script"][1]
    assert moved["label"] == "اللي حصل", moved
    # ‏الأرقام جاية من followup.assess، مش محسوبة تاني
    assert "4.4" in moved["say"], moved["say"]
    assert "38" in moved["say"], "‏المدة مش مذكورة: %s" % moved["say"]

    said = _said(out)
    assert "3.2" in said, "‏نزول نسبة الدهون مش مذكور"
    assert "دهون فعلاً" in said, "‏مش بيقول إن النازل دهون"
    # ‏«وايه الى نمشى عليه صح»
    assert "شغّال" in said and "مش هنقلبه" in said, "‏مافيش كلام عن اللي ماشي صح"


def test_a_follow_up_says_a_bad_month_plainly():
    """‏لو نسبة الدهون زادت، الكلام يقولها -- السكوت عليها بيخلي القياس
    الجاي مفاجأة."""
    worse = dict(FOLLOW_NOW, weight=77.0, fat_pct=39.5)
    out = body_read.explain(worse, mode="followup",
                            progress=_progress(current=worse))
    said = _said(out)
    assert "زادت" in said, "‏الزيادة مش مذكورة: %s" % said[:200]
    assert "هنظبّطها" in said or "هنصلّحها" in said, said[:200]


def test_the_three_scenarios_do_not_borrow_each_other_s_lines():
    """‏كل حالة هدفها مختلف، فالكلام مايتكررش بينهم."""
    free = _said(body_read.explain(WOMAN, mode="free"))
    first = _said(body_read.explain(WOMAN, mode="first"))
    follow = _said(body_read.explain(FOLLOW_NOW, mode="followup",
                                     progress=_progress()))
    # ‏دعوة الاشتراك في الفحص السريع بس
    assert "لو تحب نبدأ" in free
    assert "لو تحب نبدأ" not in first and "لو تحب نبدأ" not in follow
    # ‏وكلام المتابعة مابيظهرش لحد مالوش تاريخ
    assert "النتيجة من آخر مرة" in follow
    assert "النتيجة من آخر مرة" not in free and "النتيجة من آخر مرة" not in first
    # ‏وأول زيارة بتقول إن دي نقطة البداية
    assert "نقطة البداية" in first, first[:120]


def test_a_missing_number_drops_its_step_instead_of_inventing_one():
    """‏من غير نسبة دهون، مافيش تقسيم ومافيش هدف -- ومافيش رقم مخترع."""
    thin = {"gender": "انثى", "weight": 78.4, "height": 165.0}
    out = body_read.explain(thin, mode="free")
    labels = [step["label"] for step in out["script"]]
    assert "التقسيم" not in labels, labels
    assert "الهدف بالأرقام" not in labels, labels
    # ‏والافتتاح والخطوة الجاية لسه موجودين: الكلام مايبقاش فاضي
    assert labels[0] == "الافتتاح" and labels[-1] == "الخطوة الجاية", labels
    said = _said(out)
    assert "38" not in said and "29.9" not in said, "‏رقم مش مدخّل ظهر في الكلام"


def test_every_scenario_stays_in_one_language():
    for mode in ("free", "first"):
        blob = body_read.as_text(
            body_read.explain(WOMAN, is_ar=False, mode=mode), is_ar=False)
        assert not re.search(r"[\u0600-\u06FF]", blob), [
            line for line in blob.splitlines()
            if re.search(r"[\u0600-\u06FF]", line)][:3]
    english = body_read.as_text(
        body_read.explain(FOLLOW_NOW, is_ar=False, mode="followup",
                          progress=_progress(current=FOLLOW_NOW)), is_ar=False)
    # ‏قراءة followup.assess نفسها بتيجي باللغة المطلوبة، فالمفروض تفضل إنجليزي
    assert not re.search(r"[\u0600-\u06FF]", english), [
        line for line in english.splitlines()
        if re.search(r"[\u0600-\u06FF]", line)][:3]


def test_the_route_picks_the_scenario_from_the_name_and_the_history():
    """‏الصفحة مابتقولش السيرفر يعمل أنهي سيناريو -- السيرفر بيعرف."""
    import re as _re
    import app as A
    import core
    A.app.config["WTF_CSRF_ENABLED"] = False

    def staff():
        client = A.app.test_client()
        token = _re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                           client.get("/login").get_data(as_text=True)).group(1)
        client.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                                    "password": "pw123456", "csrf_token": token})
        return client

    numbers = {"gender": "انثى", "weight": "78.4", "height": "165",
               "age": "29", "fat_pct": "38.2"}
    client = staff()
    # ‏الاختبار بينضّف قاعدته بنفسه. الملف ده بيستخدم قاعدة ثابتة في
    # /tmp، فزيارة سابقة من تشغيل قديم كانت بتخلي "أول زيارة" تبان
    # "متابعة" -- الاختبار عدّى لوحده وفشل في الطقم الكامل.
    uid = core.db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")["id"]
    core.db_run("DELETE FROM plan_visits WHERE user_id=?", (uid,))
    # ‏مافيش اسم -> فحص سريع
    free = client.post("/api/explain-report", json=dict(numbers)).get_json()
    assert free["mode"] == "free", free["mode"]
    # ‏اسم ملوش تاريخ -> أول زيارة
    first = client.post("/api/explain-report",
                        json=dict(numbers, name="سلمى فتحي",
                                  phone="01088887777")).get_json()
    assert first["mode"] == "first", first["mode"]

    # ‏زيارة محفوظة -> متابعة، والأرقام من المقارنة الحقيقية
    plan = {"age": "29", "gender": "انثى", "height": "165", "weight": "78.4",
            "goal_cal": "1400", "tdee": "2000", "activity_mult": "1.55",
            "protein_per_kg": "1.6", "fat_pct_cal": "30", "fat_pct": "38.2",
            "goal_type": "weight_loss", "culture": "مصري",
            "zigzag_mode": "classic", "diet_plan_type": "standard",
            "name": "سلمى فتحي", "phone": "01088887777"}
    maker = staff()
    maker.post("/generate", data=plan)
    maker.post("/api/save-plan")

    later = staff()
    follow = later.post("/api/explain-report",
                        json=dict(numbers, name="سلمى فتحي", phone="01088887777",
                                  weight="74.0", fat_pct="35.0",
                                  activity="1.55", goal_type="weight_loss",
                                  goal_cal="1400")).get_json()
    assert follow["mode"] == "followup", follow["mode"]
    assert follow.get("visit_no") == 2, follow.get("visit_no")
    said = " ".join(step["say"] for step in follow["script"])
    assert "4.4" in said, said[:200]


def test_the_route_is_staff_only_and_needs_a_weight_and_height():
    import app as A
    A.app.config["WTF_CSRF_ENABLED"] = False
    anon = A.app.test_client()
    r = anon.post("/api/explain-report", json=WOMAN)
    assert r.status_code in (301, 302, 401, 403), r.status_code

    staff = A.app.test_client()
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                    staff.get("/login").get_data(as_text=True)).group(1)
    staff.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                               "password": "pw123456", "csrf_token": tok})
    r = staff.post("/api/explain-report", json=WOMAN)
    body = r.get_json()
    assert r.status_code == 200 and body["ok"], body
    assert "29.9" in body["headline"], body["headline"]
    assert body["targets"] and body["script"] and body["text"], body
    # ‏من غير وزن: جملة بتقول اعمل إيه، مش ٥٠٠ ولا صفحة فاضية
    r = staff.post("/api/explain-report", json={"height": 165})
    assert r.status_code == 400, r.status_code
    assert "اكتب الوزن والطول" in r.get_json()["error"], r.get_json()
    for junk in ("nope", [1, 2], None):
        r = staff.post("/api/explain-report", json=junk)
        assert r.status_code == 400, (junk, r.status_code)


def test_the_page_offers_the_step_without_submitting_the_form():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(here, "templates", "generate.html"),
                 encoding="utf-8") as fh:
        page = fh.read()
    assert 'id="brBtn"' in page, "‏مافيش زرار للشرح"
    # ‏زرار جوّه <form> من غير type="button" بيبعت الفورم ويولّد خطة
    button = page[page.index('id="brBtn"') - 200:page.index('id="brBtn"') + 40]
    assert 'type="button"' in button, button
    assert 'id="brCopy"' in page, "‏مافيش زرار نسخ"
    # ‏أرقام الورقة اللي مالهاش خانة: حالة صفحة، مش بيانات بتتبعت مع الخطة
    for box in ("brMuscle", "brVisceral", "brWater", "brBmr"):
        assert 'id="%s"' % box in page, box
    hidden = page[page.index('id="brMuscle"') - 120:page.index('id="brBmr"') + 30]
    assert "name=" not in hidden, hidden
    # ‏وبعد ما الورقة تتقرا، الشرح بيفتح لوحده -- دي الخطوة اللي بعدها
    assert "window.explainReport" in page


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

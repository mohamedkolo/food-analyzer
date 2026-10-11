# -*- coding: utf-8 -*-
"""‏السمنة: عامل خطر، ولا مرض قائم بذاته؟

‏لجنة Lancet (يناير ٢٠٢٥، مدعومة من أكتر من ٧٥ منظمة طبية) قسّمت
السمنة لقسمين:

    ‏ما قبل إكلينيكية -- دهون زيادة والأعضاء شغالة. عامل خطر.
    ‏إكلينيكية        -- الدهون مسبّبة خلل عضو أو قصور وظيفي. مرض.

‏يعني شخصين نفس الـBMI ممكن يكونوا حالتين مختلفتين، والخطة والإلحاح
مش واحد. والموقع كان بيطبع "سمنة درجة تانية" وخلاص -- حكم بيتقرا
كتشخيص وهو مش تشخيص.

‏واللي اتعمل **مش تشخيص** برضه: بيقرا اللي الدكتور دخّله ويقوله
الحالة دي من معايير القسم التاني، بُص عليها.

Run with:  python3 tests/test_obesity_staging.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_staging_test.db"

import app as A            # noqa: E402
import body_read           # noqa: E402
import meal_database as MD  # noqa: E402
import plan_engine         # noqa: E402
import zigzag              # noqa: E402

WOMAN = {"gender": "انثى", "weight": 95, "height": 162, "fat_pct": 42.0,
         "bmi": 36.2, "muscle_mass": 24.0, "visceral_fat": 13,
         "body_water": 42.0, "age": 38}


def test_a_healthy_bmi_is_not_staged_at_all():
    """‏السؤال مالوش محل تحت ٣٠ -- ومايتسألش."""
    out = body_read.explain(dict(WOMAN, weight=62, bmi=23.6, fat_pct=27.0))
    assert out.get("stage") is None, out.get("stage")


def test_obesity_with_no_recorded_condition_is_a_risk_factor():
    out = body_read.explain(dict(WOMAN, symptoms=["قولون عصبي"]))
    stage = out["stage"]
    assert stage["key"] == "preclinical", stage
    assert not stage["markers"], stage


def test_obesity_with_an_organ_condition_is_an_illness():
    """‏ضغط أو سكري أو كبد دهني مسجّل = الدهون بقت مأثرة فعلاً."""
    for cond in ("ضغط الدم المرتفع", "سكري النوع الثاني", "الكبد الدهني",
                 "انقطاع النفس النومي"):
        out = body_read.explain(dict(WOMAN, symptoms=[cond]))
        stage = out["stage"]
        assert stage["key"] == "clinical", (cond, stage)
        assert stage["markers"], (cond, stage)


def test_every_marker_is_a_condition_the_form_actually_offers():
    """‏علامة مكتوبة بإملاء مختلف عن الفورم مابتتطابقش أبداً، والقراءة
    بتقول "عامل خطر" لعميل عنده سكري -- في صمت."""
    offered = set(MD.CONDITION_MAP)
    unknown = [c for c in body_read._CLINICAL_MARKERS if c not in offered]
    assert not unknown, "‏علامات مش موجودة في قايمة الفورم: %s" % unknown


def test_a_condition_that_is_not_adiposity_driven_does_not_stage_it_up():
    """‏الروماتويد والهشاشة والزلاقي أمراض مش ناتجة عن الدهون. لو
    عدّوا، كل عميل سمين تقريباً هيطلع "مرض قائم" والتقسيم يبقى
    بلا معنى."""
    for cond in ("التهاب المفاصل الروماتويدي", "هشاشة العظام",
                 "الداء الزلاقي", "الربو", "ثلاسيميا"):
        out = body_read.explain(dict(WOMAN, symptoms=[cond]))
        assert out["stage"]["key"] == "preclinical", (cond, out["stage"])


def test_it_never_presents_itself_as_the_diagnosis():
    """‏ده أهم سطر في الملف. التشخيص تقييم إكلينيكي، والكود بيقرا
    خانات متعلّمة -- فلازم يقول كده بوضوح."""
    out = body_read.explain(dict(WOMAN, symptoms=["ضغط الدم المرتفع"]))
    stage = out["stage"]
    assert "على اللي مسجّل" in stage["title"], stage["title"]
    assert "أكّدها إكلينيكياً" in stage["line"], stage["line"]


def test_the_risk_factor_wording_does_not_read_as_reassurance():
    """‏"ما قبل إكلينيكية" مش معناها تمام. لو العميل قراها كده،
    التقسيم بيضر بدل ما ينفع."""
    out = body_read.explain(dict(WOMAN, symptoms=[]))
    line = out["stage"]["line"]
    assert "مش معناه إنه تمام" in line, line


def test_the_criteria_the_form_cannot_ask_about_are_handed_over_as_questions():
    """‏ضيق النفس وألم الركبة والسلس من معايير اللجنة، والفورم
    مابيسألش عنهم -- فبيتكتبوا أسئلة مش بيتفترضوا."""
    out = body_read.explain(dict(WOMAN, symptoms=[]))
    ask = out["stage"]["ask"]
    assert len(ask) >= 3, ask
    joined = " ".join(ask)
    for word in ("نفس", "ركبة", "سلس"):
        assert word in joined, (word, ask)


def test_high_body_fat_stages_even_when_bmi_is_under_thirty():
    """‏نسبة الدهون أدق من BMI. عضل قليل ودهون عالية = BMI تحت ٣٠
    والجسم في نطاق السمنة فعلاً."""
    out = body_read.explain(dict(WOMAN, weight=76, bmi=29.0, fat_pct=40.0))
    assert out["stage"] is not None, "‏دهون ٤٠٪ عدّت من غير سؤال"


def test_the_staging_reaches_the_panel_through_the_endpoint():
    """‏الدالة ممكن تبقى صح والراوت مش بيبعت الحالات -- وساعتها كل
    عميل بيطلع "عامل خطر"."""
    A.app.config["WTF_CSRF_ENABLED"] = False
    client = A.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = 1
        sess["role"] = "admin"
        sess["lang"] = "ar"
    body = {"gender": "انثى", "weight": 95, "height": 162, "fat_pct": 42,
            "bmi": 36.2, "age": 38, "symptoms": ["ضغط الدم المرتفع"]}
    res = client.post("/api/explain-report", json=body)
    assert res.status_code == 200, res.status_code
    stage = (res.get_json() or {}).get("stage") or {}
    assert stage.get("key") == "clinical", stage


def test_the_whatsapp_text_carries_it_before_the_numbers():
    """‏الدكتور بينسخ النص ده ويبعته. لو التصنيف مش فيه، الجزء
    اللي بيتبعت فعلاً مابيقولوش."""
    out = body_read.explain(dict(WOMAN, symptoms=["سكري النوع الثاني"]))
    text = body_read.as_text(out)
    assert "سمنة إكلينيكية" in text, text[:300]
    assert "**" not in text.split("\n\n")[1], "‏نجوم الماركداون اتطبعت"


def test_the_plan_sheet_stops_printing_bmi_as_a_verdict():
    """‏ورقة العميل بتطبع BMI رقم عريان. من ٣٠ وفوق الرقم لوحده
    بيتقرا كتشخيص."""
    data = {"name": "ع", "age": "38", "gender": "انثى", "culture": "مصري",
            "diet_plan_type": "standard", "fat_pct_cal": "30",
            "symptoms": [], "allergies": [], "zigzag_mode": "classic",
            "activity_level": "light", "goal_type": "weight_loss",
            "weight": "95", "height": "162", "tdee": "1900",
            "goal_cal": "1500", "bmi": "36.2"}
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        html = plan_engine.plan_html(data)
    found = re.search(r"BMI:</b>([^<]*)", html)
    assert found and "مش تشخيص" in found.group(1), found

    # ‏وBMI طبيعي مايتعلّقش عليه -- السطر ده بيتقال لما يكون له لازمة
    data2 = dict(data, bmi="23.4")
    data2["zigzag"] = zigzag.zigzag_from_data(data2)
    with A.app.test_request_context("/"):
        html2 = plan_engine.plan_html(data2)
    found2 = re.search(r"BMI:</b>([^<]*)", html2)
    assert found2 and "مش تشخيص" not in found2.group(1), found2


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

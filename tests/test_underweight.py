# -*- coding: utf-8 -*-
"""‏النحافة: حالة كاملة، مش خانة في قايمة.

‏الفورم كان فيه السمنة ومفيهوش النحافة -- والعيادة بتشوف الاتنين.

‏والنحافة **مش عكس السمنة** في التعامل: أول سؤال فيها طبي مش غذائي
(غدة، سوء امتصاص، سيلياك، سكري، اكتئاب، دواء). والمشكلة الغذائية
بعدها مش "إيه الممنوع" -- هي إن المعدة بتشبع **قبل** ما السعرات
تدخل. فاللي بيتقدّم هو الأكل الكثيف، واللي بيتأخّر هو اللي بيملا من
غير ما يغذّي.

‏وفيه حالة بتحصل بالغلط وبتعدّي: الهدف الافتراضي في الفورم "تخسيس"،
فعميل نحيف ممكن ياخد ورقة **بتنزّله**. الورقة بتطلع صح شكلاً وغلط في
اتجاهها كله -- والـBMI بيقول كده من غير ما حد يعلّم.

Run with:  python3 tests/test_underweight.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_thin_test.db")

import app as A            # noqa: E402
import plan_engine         # noqa: E402
import zigzag              # noqa: E402

_BASE = {"name": "ع", "gender": "انثى", "age": "26", "height": "165",
         "weight": "45", "culture": "مصري", "diet_plan_type": "standard",
         "goal_type": "weight_loss", "activity_level": "light",
         "tdee": "1800", "goal_cal": "1400", "protein_per_kg": "1.6",
         "fat_pct_cal": "30", "allergies": [], "symptoms": [],
         "zigzag_mode": "off"}


def _notes(**over):
    data = dict(_BASE)
    data.update(over)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data, seed="t")
        plan_engine.plan_html(data, plan)
    return [n for n in (data.get("sheet_notes") or [])]


def _text(notes):
    return " ".join(n["full"] or n["short"] for n in notes)


# ── الخانة ───────────────────────────────────────────────────────────

def test_the_form_offers_it():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "templates", "generate.html"),
              encoding="utf-8") as fh:
        page = fh.read()
    assert "'نحافة','Underweight'" in page, "‏النحافة مش في قايمة الحالات"


def test_it_carries_the_medical_question_first():
    """‏النحافة غالباً عرض مش تشخيص. خطة أكل من غير السؤال ده بتعالج
    العرض وتسيب السبب."""
    from meal_database import get_nutrient_boost_notes
    ar = " ".join(get_nutrient_boost_notes(["نحافة"], "ar"))
    assert "سبب طبي" in ar, ar[:200]
    for cause in ("غدة", "سوء امتصاص", "سيلياك"):
        assert cause in ar, cause
    en = " ".join(get_nutrient_boost_notes(["نحافة"], "en"))
    assert "medical cause" in en, en[:200]


# ── بتحرّك الخطة، مش بتطبع كلام ─────────────────────────────────────

def test_it_actually_moves_the_plan():
    """‏قاعدة المشروع: أي حالة بتتعرض لازم تحرّك الخطة. الكلام لوحده
    مش أثر."""
    from meal_extra import CONDITION_FOODS, conditions_to_keys
    keys = conditions_to_keys(["نحافة"])
    assert keys == ["underweight"], keys
    entry = CONDITION_FOODS["underweight"]
    assert entry["good"], entry
    assert entry["bad"], entry


def test_what_it_prefers_is_energy_dense():
    """‏المشكلة إن المعدة بتشبع قبل ما السعرات تدخل."""
    from meal_extra import CONDITION_FOODS
    good = CONDITION_FOODS["underweight"]["good"]
    for food in ("مكسرات", "زبدة فول سوداني", "تمر", "افوكادو", "زيت زيتون"):
        assert food in good, food


def test_what_it_pushes_down_fills_without_feeding():
    from meal_extra import CONDITION_FOODS
    bad = CONDITION_FOODS["underweight"]["bad"]
    for food in ("شوربة خضار", "سلطة خضراء", "خيار"):
        assert food in bad, food


# ── التناقض: نحافة وخطة بتنزّل ──────────────────────────────────────

def test_a_thin_client_on_a_deficit_plan_is_flagged():
    """‏الهدف الافتراضي "تخسيس". عميل نحيف ممكن ياخد ورقة بتنزّله."""
    notes = _notes(symptoms=["نحافة"], weight="60", height="165")
    warn = [n for n in notes if n["kind"] == "warn" and "نحافة" in n["short"]]
    assert warn, _text(notes)[:300]
    assert "عجز" in warn[0]["short"], warn[0]["short"]


def test_the_bmi_says_it_even_when_nobody_ticked_the_box():
    """‏الرقم موجود في الورقة أصلاً -- مش محتاج حد يفتكر يعلّم."""
    notes = _notes()          # ‏٤٥ كجم / ١٦٥ سم = BMI ١٦.٥، وخطة تخسيس
    warn = [n for n in notes if n["kind"] == "warn" and "BMI" in n["short"]]
    assert warn, _text(notes)[:300]
    assert "16.5" in warn[0]["short"], warn[0]["short"]


def test_a_thin_client_on_a_surplus_plan_is_not_scolded():
    """‏ده الصح -- مايتقالش عليه تحذير."""
    notes = _notes(goal_cal="2100", goal_type="muscle_gain")
    warn = [n for n in notes if n["kind"] == "warn" and "BMI" in n["short"]]
    assert not warn, [n["short"] for n in warn]
    info = [n for n in notes if "BMI" in n["short"]]
    assert info, "‏الـBMI المنخفض مالوش أي ذكر"
    # ‏short أول جملة بس -- الدعوة للتعليم في full
    assert "علّم عليها" in info[0]["full"], info[0]["full"]


def test_a_normal_client_hears_nothing_about_it():
    notes = _notes(weight="70", height="165")
    assert not [n for n in notes if "نحافة" in n["short"]
                or "تحت ١٨.٥" in n["short"]], _text(notes)[:300]


def test_it_is_a_note_not_a_block():
    data = dict(_BASE, symptoms=["نحافة"])
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data, seed="t")
    assert len(plan) == 7, len(plan)


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

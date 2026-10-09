# -*- coding: utf-8 -*-
"""‏هدف البروتين لطفل: على وزن مين؟

الدكتور بعت ورقة نورة وسأل "ينفع النسب دي لطفل ولا لا":

    ‏العمر ١٠ سنين · الطول ١٥٢ سم · الوزن ١٠٨.٨ كجم · BMI ٤٧.١

الموقع طبع لها "بروتين مستهدف ١.٣ جم/كجم = **١٤١ جم**"، والأكل طلّع
بين ١٣٣ و**٢٢٢** جم. وزيادة البروتين اللي اتعملت قبلها بيوم كانت
بتزوّد لها ١٤٥ جم بياض بيض عشان توصّلها لـ١٤١.

التوصية لبنت عندها ١٠ سنين ٠.٩٥ جم/كجم، وعلى وزن مرجعي لطولها --
مش على ١٠٨.٨. الدهون الزيادة مش نسيج نشط بيحتاج بروتين.

Run with:  python3 tests/test_child_protein.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_child_test.db"

import app as A            # noqa: E402
import plan_engine         # noqa: E402
import protein_need        # noqa: E402
import zigzag              # noqa: E402

# ‏بيانات نورة زي ما هي على الورقة اللي الدكتور بعتها
NOURA = {"name": "طفلة", "age": "10", "gender": "انثى", "height": "152",
         "weight": "108.8", "tdee": "1912", "goal_cal": "1912",
         "goal_type": "weight_loss", "culture": "مصري",
         "diet_plan_type": "standard", "protein_per_kg": "1.3",
         "fat_pct_cal": "30", "bmi": "47.1", "symptoms": [], "allergies": [],
         "zigzag_mode": "classic", "activity_level": "light"}


def _plan(data):
    data = dict(data)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
        html = plan_engine.plan_html(data, plan)
    return data, plan, html


def test_a_child_is_not_given_an_adults_protein_load():
    """‏١٤١ جم بروتين لبنت عندها ١٠ سنين = تلات أضعاف التوصية."""
    grams, basis, why, used = protein_need.target_grams(108.8, 152, 10, 1.3)
    assert why, "‏الحساب عدّى زي ما هو على وزن ١٠٨.٨"
    assert basis < 60, "‏لسه بيحسب على الوزن الحالي: %s" % basis
    assert 30 <= grams <= 70, "‏الهدف %d جم -- برّه المعقول لطفلة ١٠ سنين" % grams


def test_the_weight_it_computes_on_is_the_reference_for_height_and_age():
    """‏الوزن المرجعي = BMI منتصف منحنى النمو × مربع الطول."""
    ref = protein_need.reference_weight(152, 10)
    assert ref is not None
    assert abs(ref - 16.6 * 1.52 * 1.52) < 0.2, ref
    # ‏وطفل وزنه قريب من المرجعي مابيتغيّرش عليه حاجة
    _g, basis, why, _u = protein_need.target_grams(45, 150, 12, 1.2)
    assert basis == 45 and not why, (basis, why)


def test_an_adult_is_left_alone():
    """‏١.٨ جم/كجم لبالغ ١٠٠ كجم رقم كبير بس هو قرار الدكتور."""
    grams, basis, why, used = protein_need.target_grams(90, 175, 30, 1.8)
    assert grams == 162 and basis == 90 and why is None, (grams, basis, why)


def test_the_growth_range_caps_both_ends():
    """‏لا تحت التوصية ولا فوق السقف -- سن النمو مش مكان للتجربة."""
    # ‏فوق السقف
    _g, _b, why, used = protein_need.target_grams(70, 165, 16, 2.5)
    assert used == protein_need.CHILD_MAX_PER_KG and "rate" in why
    # ‏تحت التوصية
    _g2, _b2, why2, used2 = protein_need.target_grams(40, 145, 10, 0.5)
    assert used2 == protein_need.child_rda(10) and "rate" in why2


def test_the_top_up_does_not_push_a_child_toward_an_adult_target():
    """‏الزيادة بتشتغل على الهدف. لو الهدف غلط، الزيادة بتكبّر الغلط --
    وده اللي كان بيحصل: ١٤٥ جم بياض بيض لطفلة عشان توصل ١٤١."""
    _data, plan, _html = _plan(NOURA)
    for day in plan:
        tu = day.get("protein_topup")
        assert not tu, ("‏اتزوّد بروتين لطفلة بروتينها أصلاً فوق الاحتياج: "
                        "%s %s" % (day["day"], tu))


def test_the_paper_and_the_engine_agree_on_one_number():
    """‏كانوا اتنين: المحرّك على protein_need والورقة على وزن × جرام/كجم.
    فورقة نورة طبعت ١٤١ والجدول اللي تحتها متبني على ٥٠."""
    data, _plan_days, html = _plan(NOURA)
    target = data["protein_basis"]["grams"]
    assert target < 70, target
    # ‏الرقم اللي على الورقة هو نفسه
    assert re.search(r"%d\s*(?:جم|g)" % target, html), (
        "‏الورقة مش بتطبع %d" % target)
    assert "141" not in html, "‏الورقة لسه بتطبع الرقم القديم"


def test_the_sheet_says_what_it_computed_on():
    """‏الدكتور شايف "٥٠ جم" لطفلة ١٠٨ كجم -- لازم يعرف الرقم جه منين."""
    _data, _plan_days, html = _plan(NOURA)
    notes = re.findall(r'<div class="pnote"[^>]*>(.*?)</div>', html, re.S)
    joined = " ".join(notes)
    assert "الوزن المرجعي" in joined, notes
    assert "38" in joined, "‏مش بيقول الوزن اللي اتحسب عليه: %s" % notes


def test_the_sheet_flags_that_the_food_is_still_far_above_a_child():
    """‏الهدف اتصلّح، بس الأكل في القاعدة بحصص بالغين -- ١٤٩ جم/يوم
    لطفلة محتاجة ٥٠. الورقة لازم تقول كده بدل ما تعدّي."""
    _data, _plan_days, html = _plan(NOURA)
    notes = " ".join(re.findall(r'<div class="pnote"[^>]*>(.*?)</div>',
                                html, re.S))
    assert "أعلى من" in notes, "‏الأكل فوق الاحتياج بكتير والورقة ساكتة"


def test_a_missing_age_does_not_break_anything():
    """‏العمر اختياري في الفورم."""
    for age in (None, "", "غير معروف", 0):
        grams, basis, why, used = protein_need.target_grams(80, 170, age, 1.6)
        assert grams == 128 and why is None, (age, grams, why)


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

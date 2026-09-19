# -*- coding: utf-8 -*-
"""نسخة الجدول من غير اسم العيادة.

الدكتور بيشتغل في أكتر من مكان. لو سلّم عميل في عيادة تانية ورقة مكتوب
عليها اسم عيادة غيرها، دي مشكلة مع المكان اللي هو فيه -- فلازم يكون فيه
تحميل بيشيل الهوية.

اللي بيتشال **هوية بس**: اسم العيادة، اسم المُعِد، رقم الملف. الكلام الطبي
كله بيفضل: بيانات العميل، الجدول، المسموح والممنوع، والماء. ورقة ناقصة
الكلام الطبي مش "نضيفة"، دي ورقة ناقصة.

Run with:  python3 tests/test_pdf_unbranded.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")

import app as A          # noqa: E402
import plan_engine       # noqa: E402
import zigzag            # noqa: E402

DATA = {
    "name": "عميل الاختبار", "age": "30", "gender": "ذكر", "height": "175",
    "weight": "90", "tdee": "2400", "goal_cal": "2000",
    "goal_type": "weight_loss", "culture": "مصري",
    "diet_plan_type": "standard", "protein_per_kg": "1.8", "fat_pct_cal": "30",
    "symptoms": [], "allergies": [], "zigzag_mode": "classic",
}

_CACHE = {}


def _html(clean):
    """‏الصفحة نفسها، مش نص مستخرج من PDF.

    استخراج النص من PDF عربي بيلغبط شكل الحروف، فالبحث عن "الاسم" جواه
    بيفشل وإن كان مكتوب -- فالاختبار عليه كان بيقول إن الاسم اختفى وهو
    موجود. الـHTML هو اللي فيه الحقيقة.
    """
    if clean not in _CACHE:
        data = dict(DATA)
        data["zigzag"] = zigzag.zigzag_from_data(data)
        with A.app.test_request_context("/"):
            plan = plan_engine.generate_weekly_plan(data)
            _CACHE[clean] = plan_engine.plan_html(data, plan, clean=clean)
    return _CACHE[clean]


def test_the_unbranded_copy_carries_no_clinic_identity():
    html = _html(True)
    assert "NutraX" not in html, "‏اسم العيادة لسه في النسخة النضيفة"
    assert "Clinical Nutrition" not in html, "‏وصف العيادة لسه موجود"
    assert "NX-" not in html, "‏رقم الملف لسه موجود"
    assert "د. محمد" not in html, "‏اسم المُعِد لسه موجود"


def test_the_normal_copy_still_carries_it():
    """‏لو الوضع النضيف بقى هو الافتراضي، العيادة فقدت اسمها على كل ورقة."""
    html = _html(False)
    assert "NutraX" in html, "‏النسخة العادية مابقاش عليها اسم العيادة"
    assert "NX-" in html, "‏رقم الملف اختفى من النسخة العادية"
    assert "د. محمد" in html, "‏اسم المُعِد اختفى من النسخة العادية"


def test_the_unbranded_copy_keeps_every_bit_of_the_medicine():
    """‏شيلنا هوية، مش محتوى."""
    clean, full = _html(True), _html(False)

    assert DATA["name"] in clean, "‏اسم العميل اختفى"
    for label in ("BMI", "kcal", "مسموح", "ممنوع", "الماء", "المراجعة بعد"):
        assert label in clean, "‏%s اختفى من النسخة النضيفة" % label
    for day in ("الاحد", "الاثنين", "الثلاثاء", "الاربعاء", "الخميس",
                "الجمعة", "السبت"):
        assert day in clean, "‏يوم %s ناقص من النسخة النضيفة" % day
    assert clean.count("<tr>") == full.count("<tr>"), "‏صف اختفى من الجدول"
    # ‏الفرق بين النسختين لازم يبقى الهوية بس -- حاجة في حدود سطرين
    diff = len(full) - len(clean)
    assert 0 < diff < 400, (
        "‏الفرق بين النسختين %d حرف -- ده أكبر من هوية عيادة" % diff)


def test_the_pdf_still_comes_out_of_the_same_page():
    """‏لو الاتنين اتفرقوا، الاختبارات فوق بتقيس صفحة والعميل بياخد غيرها."""
    import inspect
    src = inspect.getsource(plan_engine.build_pdf)
    assert "plan_html(" in src, "‏build_pdf مابقتش بتستخدم نفس الصفحة"
    data = dict(DATA)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
        raw = plan_engine.build_pdf(data, plan, clean=True)
    assert raw[:4] == b"%PDF", "‏الناتج مش PDF"
    assert len(raw) > 20000, "‏الـPDF طلع فاضي تقريباً"


def test_the_route_asks_for_it_explicitly():
    """‏?clean=1 هو اللي بيطلبها. من غيره الورقة بتطلع باسم العيادة."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "app.py"), encoding="utf-8").read()
    block = src[src.index("def download_pdf"):]
    block = block[:block.index("@app.route", 10)]
    assert 'request.args.get("clean")' in block, "‏الراوت مش بيقرا clean"
    assert "clean=clean" in block, "‏الراوت مش بيمرّرها لـbuild_pdf"
    # ‏واسم الملف نفسه مالوش يحمل اسم العيادة
    assert 'f"{name}.pdf"' in block, (
        "‏اسم الملف النضيف لسه فيه NutraX -- الاسم بيظهر في الواتس")


def test_the_preview_offers_it():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html = open(os.path.join(here, "templates", "preview.html"),
                encoding="utf-8").read()
    assert html.count("/download_pdf?clean=1") >= 2, (
        "‏الزرار ناقص في نسخة الموبايل أو الكمبيوتر")


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

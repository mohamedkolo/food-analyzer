# -*- coding: utf-8 -*-
"""‏صفحة إنشاء الخطة: الرقم جنب الحاجة، والباقي مطوي.

‏الورقة اللي بتطلع من الصفحة دي بسيطة -- جدول وسطر لكل حاجة -- والصفحة
نفسها ماكانتش. قبل أول خانة كان فيه **تلات فقرات شرح**، وبعدها أربع
صناديق ملوّنة، وصندوقين مفتوحين على الآخر لحاجات بتتحط **تلقائياً**
(الماكروز والتدوير) وفيهم سبع أعمدة بتترسم كل مرة. ستة أرقام قصيرة
(سن، طول، وزن، دهون، BMI، TDEE) كانوا بياخدوا شاشة كاملة على الموبايل
لأنهم بينزلوا اتنين واحد.

‏فالقاعدة بقت قاعدة الورقة: **سطر واحد لكل حاجة والرقم جنبها**، واللي
مش بيتقري كل مرة بيتطوي.

‏وفيه حاجتين الطيّ ماينفعش يلمسهم، والملف ده موجود عشانهم:

  ١) الرقم لازم يفضل مقروء والصندوق مقفول. طيّ بيخفي الرقم يبقى
     إخفاء مش تبسيط.
  ٢) تحذير التدوير بيفتح الصندوق لوحده. تحذير جوه حاجة مقفولة مش تحذير.

Run with:  python3 tests/test_form_simpler.py
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = io.open(os.path.join(HERE, "templates", "generate.html"),
               encoding="utf-8").read()


def _step_one():
    """‏خطوة العميل بس -- دي اللي بتتملى كل زيارة."""
    start = PAGE.index('data-step="1"')
    end = PAGE.index('data-step="2"')
    return PAGE[start:end]


# ── المطوي ───────────────────────────────────────────────────────────

def test_the_auto_set_boxes_are_folded():
    """‏الماكروز والتدوير بيتحطوا تلقائياً حسب النظام. فتحهم على طول
    معناه إن اللي بيتقري كل مرة (الأرقام) بينزل تحت اللي مابيتقريش."""
    step = _step_one()
    for fold in ('id="mxFold"', 'id="zzFold"'):
        assert fold in step, fold
        at = step.index(fold)
        assert "<details" in step[max(0, at - 120):at], fold
    assert "<details class=\"wz-fold\" id=\"mxFold\" open" not in step
    assert "<details class=\"wz-fold\" id=\"zzFold\" open" not in step


def test_the_number_is_readable_while_the_box_is_shut():
    """‏سطر العنوان هو اللي بيحمل الرقم -- زي الورقة بالظبط."""
    step = _step_one()
    for sid in ('id="mxSum"', 'id="zzSum"'):
        assert sid in step, sid
        head = step[:step.index(sid)]
        assert head.rfind("<summary") > head.rfind("</summary"), (
            "‏%s مش جوه سطر العنوان، فمش هيبان والصندوق مقفول" % sid)


def test_the_macro_summary_follows_the_fields():
    """‏رقم قديم في سطر العنوان أسوأ من مافيش رقم."""
    assert "function mxSay()" in PAGE
    for field in ("proteinPerKg", "fatPctCal", "carbPctCal"):
        assert field in PAGE
    block = PAGE[PAGE.index("function mxSay()"):]
    block = block[:block.index("function renderZigzag")]
    assert "addEventListener('input', mxSay)" in block, (
        "‏الملخّص مش بيتحدّث لما الخانة تتغيّر")


def test_the_cycling_summary_carries_the_weekly_average():
    assert "zzSay(zzName" in PAGE, "‏سطر التدوير مش بيتكتب"
    assert "zzMean" in PAGE, "‏المتوسط الأسبوعي مش في السطر"


def test_the_warning_opens_the_box_it_lives_in():
    """‏التدوير بيبقى مستحيل لو الهدف عند الحد الآمن أو تحته. التحذير
    ده جوه صندوق مطوي، فلو مافتحش الصندوق الدكتور فاكر التدوير شغال."""
    at = PAGE.index("zzWarn.hidden = !noRoom")
    near = PAGE[at:at + 400]
    assert "zzFold.open = true" in near, (
        "‏التحذير بيظهر جوه صندوق مقفول من غير ما يفتحه")


# ── اللي اتشال واللي **مايتشالش** ───────────────────────────────────

def test_the_two_facts_that_change_the_doctors_choice_are_still_there():
    """‏الشرح اتقصّر، بس مش على حساب اللي بيغيّر القرار: دي ملفات مرضى،
    والفرق بين الكاميرا والـPDF لازم يكون قدامه **قبل** ما يدوس."""
    step = _step_one()
    assert "مابتطلعش من الموبايل" in step, "‏اختفى إن الصورة مابتخرجش"
    assert "بيترفع للسيرفر" in step, "‏اختفى إن الـPDF بيخرج"
    assert "مش هيتعمل ملف متابعة" in step, "‏اختفت نتيجة سيبان الاسم فاضي"


def _rendered():
    """‏الصفحة زي ما المتصفح بيشوفها -- تعليقات Jinja مش بتتعرض،
    فعدّها مع الكلام بيدّي رقم مالوش معنى."""
    os.environ.setdefault("SECRET_KEY", "test-only")
    os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
    os.environ["NUTRAX_DB"] = "/tmp/nutrax_simpler_test.db"
    import app as A
    c = A.app.test_client()
    with c.session_transaction() as sess:
        sess["uid"] = 1
        sess["role"] = "admin"
        sess["lang"] = "ar"
    return c.get("/generate").get_data(as_text=True)


def test_the_page_opens_on_the_fields_not_on_three_paragraphs():
    """‏الكلام اللي الدكتور بيقراه قبل ما يوصل لأول خانة. كان تلات
    فقرات عن القراءة وفقرة عن الشرح -- وهو بيملا الصفحة دي كل زيارة
    وعارفهم."""
    page = _rendered()
    head = page[page.index('id="rpBox"'):page.index('id="nameField"')]
    head = re.sub(r"<[^>]+>", " ", head)
    words = [w for w in head.split() if len(w) > 1]
    assert len(words) < 60, "‏لسه فيه %d كلمة قبل أول خانة" % len(words)


def test_the_short_numbers_stay_three_in_a_row_on_a_phone():
    """‏ستة أرقام من تلات خانات كانوا بياخدوا شاشة كاملة."""
    assert ".grid-3.nums" in PAGE, "‏مافيش صف للأرقام القصيرة"
    at = PAGE.index("@media(max-width:768px){\n    .grid-3.nums")
    assert "grid-template-columns:1fr 1fr 1fr" in PAGE[at:at + 220], (
        "‏الأرقام لسه بتنزل اتنين واحد على الموبايل")
    step = _step_one()
    assert step.count('class="grid-3 nums"') >= 2, (
        "‏صفوف الأرقام مش متعلّمة")


# ── اللي ماينفعش يتكسر ──────────────────────────────────────────────

def test_every_field_the_server_reads_is_still_in_the_form():
    """‏التبسيط شكل، مش حذف. أي خانة تضيع يبقى الخطة اتولدت بقيمة
    افتراضية والدكتور مش عارف."""
    for name in ("name", "gender", "phone", "visit_notes", "age", "height",
                 "weight", "fat_pct", "bmi", "tdee", "activity_mult",
                 "goal_cal", "protein_per_kg", "fat_pct_cal", "carb_pct_cal",
                 "zigzag_mode"):
        assert 'name="%s"' % name in PAGE, "‏خانة %s ضاعت" % name


def test_the_hidden_file_inputs_can_still_be_reached_from_their_labels():
    """‏المدخل مخفي بصرياً بس لازم يفضل في الشجرة -- display:none بيقطع
    الوصول من اللابل ومن الكيبورد."""
    at = PAGE.index(".wz-file {")
    css = PAGE[at:at + 220]
    assert "display:none" not in css, "‏المدخل اتشال من الشجرة"
    assert "clip:rect(0 0 0 0)" in css or "opacity:0" in css, css
    for fid in ("rpFile", "rpUpload"):
        assert 'id="%s"' % fid in PAGE and 'for="%s"' % fid in PAGE, fid


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

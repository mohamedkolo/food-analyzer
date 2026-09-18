# -*- coding: utf-8 -*-
"""الملء التلقائي وشكل الخطوات.

الاتنين دول غيروا فورم توليد الخطة، وفيهم حاجات لو اتكسرت مش هتبان بسهولة:

  * الرقم لوحده لازم يلاقي العميل. client_key مبني على الاسم (اسم|آخر٦أرقام)
    فالبحث بيه مستحيل من غير اسم -- والدكتور بيكتب الرقم الأول. والمقارنة
    لازم تبقى على الأرقام المجرّدة: الموبايل متخزّن "+20 100 429 4521"،
    والمسافة واقعة جوه آخر ٦ أرقام، فـLIKE '%294521' مابيلاقيهاش. ده باگ
    وقعنا فيه فعلاً واتصلح.

  * الاسم لازم يتملّى مع الباقي. الحقل required، فلو فضل فاضي المتصفح بيرفض
    الإرسال من غير رسالة مفهومة -- وده اللي حصل أول تجربة.

  * الخطوة المخفية display:none، وحقولها لسه جوه الـ<form>. لو حد غيّرها
    لإزالة من الـDOM، بيانات الخطوات اللي مادخلتهاش هتضيع في صمت.

Run with:  python3 tests/test_form_prefill.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORM = os.path.join(HERE, "templates", "generate.html")


def _form():
    with open(FORM, encoding="utf-8") as fh:
        return fh.read()


def test_the_phone_finds_a_client_in_every_way_it_gets_typed():
    """‏الموبايل بيتكتب بأي شكل، والمقارنة على آخر ٦ أرقام مجرّدة."""
    os.environ.setdefault("SECRET_KEY", "test-only")
    os.environ["NUTRAX_DB"] = "/tmp/nutrax_prefill_test.db"
    if os.path.exists("/tmp/nutrax_prefill_test.db"):
        os.remove("/tmp/nutrax_prefill_test.db")
    import core

    core.db_run(
        """INSERT INTO plan_visits (user_id, client_key, client_name, phone,
             visit_no, age, gender, height, conditions)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (99, "test|294521", "عميل اختبار", "+20 100 429 4521", 2,
         41, "ذكر", 174.0, json.dumps(["سكري النوع الثاني"], ensure_ascii=False)))

    # ‏كل دي نفس الرقم مكتوب بشكل مختلف
    for typed in ("01004294521", "+20 100 429 4521", "0100 429 4521",
                  "429-4521", "4294521", "٤٢٩٤٥٢١".translate(
                      str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))):
        rows = core.visits_by_phone(99, typed, limit=5)
        assert rows, "‏الرقم %r مالقاش العميل" % typed

    # ‏ورقم تاني مايلاقيهوش
    assert not core.visits_by_phone(99, "01111111111", limit=5), \
        "‏رقم مختلف لاقى العميل"
    # ‏وأقل من ٦ أرقام مش تعريف كافي
    assert not core.visits_by_phone(99, "4521", limit=5), \
        "‏٤ أرقام اعتبرها تعريف كافي"
    # ‏ودكتور تاني مايشوفش عملاء غيره
    assert not core.visits_by_phone(98, "01004294521", limit=5), \
        "‏دكتور تاني شاف عميل مش بتاعه"


def test_the_lookup_endpoint_accepts_a_phone_with_no_name():
    """‏الدكتور بيكتب الرقم قبل الاسم، فالـendpoint لازم يقبله لوحده."""
    src = open(os.path.join(HERE, "routes_plans.py"), encoding="utf-8").read()
    block = src[src.index("def followup_lookup"):src.index("def followups")]
    assert "visits_by_phone" in block, "‏البحث بالرقم مش مستخدم في الـendpoint"
    # ‏البحث بالرقم لازم يجي قبل شرط طول الاسم، وإلا بيرجع found:False قبله
    i_phone = block.index("visits_by_phone")
    i_name_guard = block.index("fold_name(name)")
    assert i_phone < i_name_guard, (
        "‏شرط الاسم بيسبق البحث بالرقم، فالرقم لوحده هيرجع مفيش نتيجة")
    assert "matched_by" in block, "‏الواجهة مش بتعرف لقاه بالرقم ولا بالاسم"


def test_the_autofill_fills_the_name_because_the_field_is_required():
    """‏لو الاسم فضل فاضي، المتصفح بيرفض الإرسال والدكتور مش فاهم ليه."""
    html = _form()
    assert 'name="name" id="nameField" required' in html, \
        "‏شكل حقل الاسم اتغير -- الاختبار ده محتاج تحديث"
    assert "setIfEmpty(nameField, d.name" in html, \
        "‏الملء التلقائي مش بيملّي الاسم، والحقل required"


def test_the_autofill_never_overwrites_what_was_typed():
    """‏الرقم بيتكتب وسط الكتابة، فالملء مايصحش يمسح شغل الدكتور."""
    html = _form()
    fn = html[html.index("function fuFillEmpty"):html.index("const btn=")]
    assert "if(String(el.value||'').trim()!=='') return;" in fn, \
        "‏حماية 'المكتوب مايتغيرش' مش موجودة"
    # ‏الوزن مالوش يتملّى: ده اللي جاي يتقاس في الزيارة دي
    assert "setIfEmpty(w," not in fn and "setIfEmpty(wField" not in fn, \
        "‏الوزن بيتملّى من زيارة قديمة -- ده اللي المفروض يتقاس"


def test_saying_different_person_clears_only_what_was_autofilled():
    html = _form()
    skip = html[html.index("document.getElementById('fuSkip').onclick"):]
    skip = skip[:skip.index("fuLastKey='__skipped__")]
    assert "fuAutoFilled" in skip and "fuAutoConds" in skip, \
        "‏'ده شخص تاني' مش بيشيل اللي اتملى تلقائي"


def test_the_conditions_come_back_and_stay_until_changed():
    """‏اللي إنت طلبته: الحالات بتفضل متسجلة لحد ما تغيّرها.

    الحالات بتتخزّن مع كل زيارة (conditions في plan_visits)، والملء بيجيبها
    من آخر زيارة. فلو الدكتور غيّرها، الزيارة الجديدة بتسجّل الجديد، والمرة
    الجاية الجديد هو اللي بيرجع.
    """
    core_src = open(os.path.join(HERE, "core.py"), encoding="utf-8").read()
    ins = core_src[core_src.index("INSERT INTO plan_visits"):]
    ins = ins[:ins.index(")\"\"\"") + 4] if ")\"\"\"" in ins[:900] else ins[:900]
    assert "conditions" in ins, "‏الحالات مش بتتسجل مع الزيارة"

    html = _form()
    fn = html[html.index("function fuFillEmpty"):html.index("const btn=")]
    assert 'name="symptoms"' in fn, "‏الملء مش بيعلّم الحالات"
    assert "cb.checked" in fn, "‏الملء مش بيعلّم الحالات"


def test_the_form_is_four_steps_and_hidden_steps_still_submit():
    """‏الخطوة المخفية display:none -- حقولها لسه بتتبعت.

    لو حد شالها من الـDOM بدل ما يخفيها، بيانات الخطوات اللي الدكتور
    مادخلهاش هتضيع من غير أي رسالة.
    """
    html = _form()
    assert html.count('class="wz-step"') == 4, (
        "‏عدد الخطوات مش 4: %d" % html.count('class="wz-step"'))
    assert html.count('class="wz-tab"') == 4, "‏شريط الخطوات مش 4"
    assert ".wz-step { display:none }" in html, "‏الخطوة بتتخفي بطريقة تانية"
    assert "remove()" not in html.split(".wz-step")[1][:2000], \
        "‏في كود بيشيل الخطوة من الصفحة -- البيانات هتضيع"
    # ‏الأقسام العشرة كلها لسه موجودة
    assert html.count('class="wz-card"') == 10, (
        "‏قسم ضاع في التقسيم: %d من 10" % html.count('class="wz-card"'))


def test_every_step_lives_inside_the_form():
    """‏خطوة برّه الـ<form> = بياناتها مابتتبعتش."""
    html = _form()
    form_start = html.index('<form method="POST" action="/generate">')
    form_end = html.index("</form>", form_start)
    inside = html[form_start:form_end]
    assert inside.count('class="wz-step"') == 4, \
        "‏في خطوة برّه الفورم -- بياناتها هتضيع"


def test_a_required_field_in_a_hidden_step_is_surfaced():
    """‏المتصفح بيرفض الإرسال في صمت لو الحقل المطلوب في خطوة مخفية."""
    html = _form()
    assert "querySelector(':invalid')" in html, \
        "‏مفيش معالجة للحقل المطلوب المخفي"
    assert "reportValidity" in html, "‏الدكتور مش هيعرف الحقل الناقص فين"


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

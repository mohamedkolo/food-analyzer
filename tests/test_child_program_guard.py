# -*- coding: utf-8 -*-
"""‏طفل + برنامج تغذية = البرنامج بيتشال.

‏الدكتور بعت ورقتين حقيقيتين لطفل، واحدة من برنامج الكارب المنخفض
وواحدة من برنامج "أطفال (نمو)". الاتنين غلط، وبسبب واحد:

‏الـ11 برنامج كلهم **جداول بالغين بتتكبّر بالسعرات**. البرنامج بيحدّد
الأكل، وdiet_programs بيضرب الحصص في (الهدف ÷ مجموع اليوم). مافيش في
السلسلة دي أي حاجة بتعرف إن اللي قدامها طفل -- والسبب إن فرع البرامج
في generate_weekly_plan بيعمل return **قبل** منطق الأطفال كله.

‏المقاس على طفل ١٠ سنين (توصيته ٥٢ جم بروتين، سقف سنه ١٣٥):

    كارب منخفض   ١٣٥-١٦٩ جم/يوم   فوق السقف كل يوم
    أطفال (نمو)  ١٢٠-١٣٤ جم/يوم   قاعد على السقف كل يوم
    العادي       ٥٣-١٠٠ جم/يوم    في النطاق

‏وتلات حاجات الملف ده بيحميها:

  * البرنامج بيتشال للطفل، والبالغ مابيتلمسش.
  * سطور السمنة المكتوبة لبالغ ("عجز سعري معتدل + بروتين عالي")
    مابتوصلش لورقة طفل.
  * اللي اتغيّر بيتكتب **على الورقة** مش في المعاينة بس -- الدكتور
    اختار برنامج وخد غيره، ولو ده في المعاينة بس ممكن يسلّم الورقة
    وهو فاكر إنها البرنامج.

Run with:  python3 tests/test_child_program_guard.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_kidprog_test.db"

import app as A            # noqa: E402
import plan_engine         # noqa: E402
import protein_need        # noqa: E402
import zigzag              # noqa: E402

KID = {"name": "سيف", "age": "10", "gender": "ذكر", "height": "140",
       "weight": "58", "tdee": "1900", "goal_cal": "1900",
       "goal_type": "weight_loss", "culture": "مصري", "protein_per_kg": "1.6",
       "fat_pct_cal": "30", "symptoms": ["السمنة"], "allergies": [],
       "zigzag_mode": "classic", "activity_level": "light", "bmi": "29.6"}


def _sheet(**over):
    data = dict(KID)
    data.update(over)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
        html = plan_engine.plan_html(data, plan)
    return data, plan, html


def _allowed(html):
    m = re.search(r'fbox ok"><h4>.*?</h4><ul>(.*?)</ul>', html, re.S)
    return [re.sub(r"<[^>]+>", "", x).strip()
            for x in re.findall(r"<li>(.*?)</li>", m.group(1) if m else "", re.S)]


def _alert(html):
    m = re.search(r'<div class="alert">(.*?)</div>', html, re.S)
    return re.sub(r"<[^>]+>", " ", m.group(1)).strip() if m else ""


def _programs():
    from diet_programs import PROGRAMS
    return list(PROGRAMS.keys())


# ── الشيل ────────────────────────────────────────────────────────────

def test_every_one_of_the_programs_is_dropped_for_a_child():
    """‏مش برنامج بعينه -- الـ11 كلهم جداول بالغين."""
    for key in _programs():
        data, _plan, _html = _sheet(diet_plan_type=key)
        assert data.get("kid_program_swap"), "‏%s فضل شغّال على طفل" % key
        assert data["diet_plan_type"] == "standard", data["diet_plan_type"]


def test_the_growth_program_is_dropped_too():
    """‏"أطفال (نمو)" اسمه للأطفال، بس حصصه بتتظبط بالسعرات زي الباقي --
    فطلّع ١٢٠-١٣٤ جم بروتين لطفل توصيته ٥٢."""
    data, _plan, _html = _sheet(diet_plan_type="kids")
    assert data.get("kid_program_swap"), "‏برنامج الأطفال فضل شغّال"


def test_an_adult_keeps_the_program_they_chose():
    """‏الشيل للأطفال. لو مسّ بالغ، كل الـ11 برنامج بقوا بلا فايدة."""
    for key in ("kids", "low_carb_program", "dash"):
        data, _plan, _html = _sheet(age="34", weight="95", height="175",
                                    diet_plan_type=key)
        assert not data.get("kid_program_swap"), "‏%s اتشال من بالغ" % key
        assert data["diet_plan_type"] == key, data["diet_plan_type"]


def test_the_child_plan_lands_inside_the_protein_band():
    """‏ده اللي الشيل كله موجود عشانه."""
    for key in ("kids", "low_carb_program"):
        _data, plan, _html = _sheet(diet_plan_type=key)
        lo, hi = protein_need.band(58, 140, 10, 1.6,
                                  plan[0].get("total_cal") or 1900)
        ps = [d.get("total_p") or 0 for d in plan]
        assert max(ps) <= hi, "‏%s: أعلى يوم %d والسقف %d" % (key, max(ps), hi)


def test_the_child_pool_is_what_actually_fills_the_table():
    """‏مش بس إن البرنامج اتشال -- لازم اللي جه مكانه يبقى أكل أطفال."""
    import child_meals
    _data, plan, _html = _sheet(diet_plan_type="low_carb_program")
    pool = child_meals.pool_for("10", "مصري")
    assert pool, "‏مافيش جداول أطفال أصلاً"
    # ‏الوجبة في الجدول ديكشنري ونصّها تحت المفتاح "meal". والمقارنة على
    # **أول صنف من غير كمية**: المقياس بيغيّر الجرامات، فمقارنة النص
    # كامل بتفشل على وجبة سليمة.
    import re as _re
    def _head(text):
        first = _re.split(r"\s*\+\s*", str(text or ""))[0]
        return _re.sub(r"[\d\s]+(?:جم|مل|كوب|ملعقة|ملاعق)?$", "",
                       first).strip()
    known = set()
    for slot in ("breakfast", "lunch", "dinner"):
        known |= {_head(m.get("meal")) for m in (pool.get(slot) or [])}
    known.discard("")
    hits = sum(1 for d in plan for k in ("breakfast", "lunch", "dinner")
               if _head(d.get(k)) in known)
    assert hits >= 7, "‏الجدول مش من جداول الأطفال (%d خانة بس من 21)" % hits


# ── المسموح والممنوع ────────────────────────────────────────────────

# ── الورقة لازم تقول اللي بتعمله ─────────────────────────────────────
#
# ‏الدكتور سأل: "ده أديله الجدول ده إزاي وهو بينزل وزن؟" -- وكان محق.
# أول نسخة من الشيل حطّت "تثبيت الوزن مع زيادة الطول" على **كل** ورقة
# طفل، والبرنامج بيبني على رقم السعرات اللي اتكتب زي ما هو. فورقة فيها
# عجز ٦٠٠ سعرة كانت بتتطبع ومكتوب عليها "تثبيت" -- يعني الورقة بتقول
# عكس اللي بتعمله. الاختبارات دي بتقفل الباب ده.

def test_a_sheet_with_a_real_deficit_does_not_claim_to_be_maintenance():
    """‏أسوأ حالة: الكلام يقول تثبيت والأكل عجز ٦٠٠ سعرة."""
    _data, plan, html = _sheet(diet_plan_type="standard",
                               tdee="1900", goal_cal="1300")
    joined = " ".join(_allowed(html))
    assert "تثبيت" not in joined, (
        "‏الورقة بتقول تثبيت والأكل عجز: %s" % joined)
    assert "عجز" in joined, joined
    avg = sum(d.get("total_cal") or 0 for d in plan) / float(len(plan))
    assert avg < 1500, "‏الاختبار مالوش معنى من غير عجز فعلي (%d)" % avg


def test_a_sheet_at_maintenance_says_maintenance():
    """‏والعكس: من غير عجز، "عجز محسوب" كلام مالوش محل."""
    _data, _plan, html = _sheet(diet_plan_type="standard",
                                tdee="1900", goal_cal="1900")
    joined = " ".join(_allowed(html))
    assert "تثبيت" in joined, joined
    assert "عجز" not in joined, joined


def test_a_small_gap_is_not_called_a_deficit():
    """‏فرق ١٠٠ سعرة جوّه خطأ تقدير الـTDEE نفسه (Mifflin ±١٠٪)، فتسميته
    "عجز" على ورقة أهل طفل ادّعاء بدقة مش موجودة."""
    _data, _plan, html = _sheet(diet_plan_type="standard",
                                tdee="1900", goal_cal="1820")
    joined = " ".join(_allowed(html))
    assert "تثبيت" in joined, joined


def test_the_deficit_reaches_the_specialist_with_its_number():
    """‏"السعرات لازم تكفي النمو" جملة عامة مافيهاش رقم. عجز ٦٠٠ سعرة
    على ابن ١٠ سنين كان بيعدّي بيها ساكت."""
    data, _plan, _html = _sheet(diet_plan_type="standard",
                                tdee="1900", goal_cal="1300")
    warns = " ".join(n["short"] for n in (data.get("sheet_notes") or [])
                     if n.get("kind") == "warn")
    assert "600" in warns, "‏رقم العجز مش في التحذيرات: %s" % warns
    assert "10" in warns, "‏السن مش مذكور: %s" % warns


def test_the_doctors_own_number_is_not_changed_behind_his_back():
    """‏عجز مقصود لحالة سمنة شديدة بمتابعة قرار إكلينيكي. اللي بيتعمل
    إننا نحط الرقم قدامه، مش إننا نغيّره."""
    data, plan, _html = _sheet(diet_plan_type="standard",
                               tdee="1900", goal_cal="1300")
    assert str(data.get("goal_cal")) == "1300", data.get("goal_cal")
    avg = sum(d.get("total_cal") or 0 for d in plan) / float(len(plan))
    assert abs(avg - 1300) < 150, "‏الأكل مابيتبعش الهدف: %d" % avg


def test_an_adult_on_a_deficit_is_not_given_the_child_wording():
    _data, _plan, html = _sheet(age="34", weight="95", height="175",
                                diet_plan_type="standard",
                                tdee="2400", goal_cal="1800")
    joined = " ".join(_allowed(html))
    assert "عجز سعري معتدل" in joined, joined
    assert "من نفسكم" not in joined, joined


def test_a_childs_sheet_never_tells_the_parents_to_cut_calories():
    """‏"عجز سعري معتدل + بروتين عالي" مكتوبة لبالغ. على ورقة طفل الأولى
    بتقول للأهل قلّلوا أكل طفل بيكبر، والتانية بتخليهم يزوّدوا بروتين
    فوق حمل عالي أصلاً."""
    # ‏"عجز سعري معتدل + بروتين عالي" الجملة بتاعت البالغين. الورقة لو
    # فيها عجز فعلي بتقول عجز بصيغتها هي (الاختبار اللي فوق)، بس
    # عمرها مابتقول الجملتين دول.
    for over in ({"goal_cal": "1900"}, {"goal_cal": "1300"}):
        _data, _plan, html = _sheet(diet_plan_type="standard",
                                    tdee="1900", **over)
        joined = " ".join(_allowed(html))
        assert "عجز سعري معتدل" not in joined, joined
        assert "بروتين عالي" not in joined, joined


def test_the_childs_sheet_says_what_to_do_instead():
    """‏شيل من غير بديل بيسيب ورقة سمنة مافيهاش أي توجيه."""
    _data, _plan, html = _sheet(diet_plan_type="standard",
                                tdee="1900", goal_cal="1900")
    joined = " ".join(_allowed(html))
    assert "النمو" in joined, joined
    assert "الطول" in joined, "‏مافيش ذكر لتثبيت الوزن مع زيادة الطول: %s" % joined


def test_an_adult_with_obesity_still_gets_the_deficit_advice():
    """‏ده السطر الصح لبالغ. لو اتشال منه كمان، يبقى شيلنا نصيحة سليمة."""
    _data, _plan, html = _sheet(age="34", weight="95", height="175",
                                diet_plan_type="standard")
    joined = " ".join(_allowed(html))
    assert "عجز سعري معتدل" in joined, joined


def test_the_function_still_works_without_an_age():
    """‏get_allowed_forbidden بتتنادى من الاختبارات ومن أماكن تانية من
    غير سن. من غير سن = بالغ، مش انفجار."""
    allowed, _forbidden = plan_engine.get_allowed_forbidden(["السمنة"])
    assert any("عجز سعري" in a for a in allowed), allowed


# ── سطر الورقة ──────────────────────────────────────────────────────

def test_the_swap_is_printed_on_the_sheet_not_only_in_the_preview():
    """‏الدكتور اختار برنامج وخد غيره. لو ده في المعاينة بس، ممكن يسلّم
    الورقة وهو فاكر إنها البرنامج."""
    _data, _plan, html = _sheet(diet_plan_type="low_carb_program")
    line = _alert(html)
    assert line, "‏مافيش سطر على الورقة"
    assert "جداول الأطفال" in line, line


def test_the_line_says_the_reason_not_a_verdict():
    """‏أول صياغة كانت "«أطفال (نمو)» مش مناسب لسن النمو" -- جملة
    بتناقض نفسها على برنامج اسمه نمو. السبب الحقيقي الحصص."""
    _data, _plan, html = _sheet(diet_plan_type="kids")
    line = _alert(html)
    assert "مش مناسب لسن النمو" not in line, line
    assert "بالسعرات" in line, line


def test_a_program_that_fights_its_own_goal_is_printed_for_an_adult_too():
    """‏بالغ اختار برنامج الأطفال بهدف تخسيس: التناقض قايم والبرنامج
    مابيتشالش. التحذير كان في المعاينة، والورقة اللي بتوصل البيت
    بتقول "عجز سعري" على برنامج أرضيته ١٥٠٠ سعرة."""
    _data, _plan, html = _sheet(age="34", weight="95", height="175",
                                goal_cal="1800", diet_plan_type="kids")
    line = _alert(html)
    assert "تخسيس" in line, line


def test_an_ordinary_sheet_carries_no_extra_line_at_all():
    """‏"مفهوش أي إضافات غير الممنوع والمسموح". السطر لما يكون فيه سبب بس."""
    for over in ({"diet_plan_type": "standard"},
                 {"diet_plan_type": "standard", "age": "34",
                  "weight": "95", "height": "175"}):
        _data, _plan, html = _sheet(**over)
        assert 'class="alert"' not in html, "‏سطر زيادة على ورقة عادية: %s" % over


def test_the_sheet_is_still_one_page():
    """‏السطر الزيادة مايزحّفش المسموح والممنوع لصفحة تانية."""
    from weasyprint import HTML
    _data, _plan, html = _sheet(diet_plan_type="low_carb_program")
    assert len(HTML(string=html).render().pages) == 1, "‏الورقة بقت صفحتين"


def test_the_english_sheet_says_it_in_english():
    from flask import session
    data = dict(KID, diet_plan_type="low_carb_program")
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        session["lang"] = "en"
        plan = plan_engine.generate_weekly_plan(data)
        html = plan_engine.plan_html(data, plan)
    line = _alert(html)
    assert line, "‏مافيش سطر على الورقة الإنجليزي"
    assert not re.search(r"[؀-ۿ]", line.replace("«", "")
                         .replace("»", "")), "‏عربي على ورقة إنجليزية: %s" % line


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

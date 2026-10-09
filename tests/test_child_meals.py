# -*- coding: utf-8 -*-
"""‏جداول الأطفال: حصص طفل، وماكروز محسوبة من المكوّنات.

‏الدكتور قال "اعملي جداول للأطفال" بعد ورقة نورة. اللي كان موجود:
قاعدة أطباق بالغين، وأقل كثافة بروتين في قايمة الغدا ٠.٠٤٤ جم لكل
سعر -- وكثافة احتياج نورة ٠.٠٢٦. فترتيب الاختيار على الكثافة نزّل
أسبوعها من ١٤٨ جم متوسط لـ١١٦، وده أقصى اللي القاعدة القديمة تقدر
عليه. الباقي محتاج أطباق مكتوبة لطفل.

Run with:  python3 tests/test_child_meals.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_child_meals_test.db"

import app as A              # noqa: E402
import child_meals as CM     # noqa: E402
import meal_database as MD   # noqa: E402
import plan_engine           # noqa: E402
import protein_need          # noqa: E402
import zigzag                # noqa: E402

SLOTS = ("breakfast", "lunch", "dinner")

CHILD = {"name": "طفل", "age": "10", "gender": "انثى", "height": "152",
         "weight": "108.8", "tdee": "1912", "goal_cal": "1912",
         "goal_type": "weight_loss", "culture": "مصري",
         "diet_plan_type": "standard", "protein_per_kg": "1.3",
         "fat_pct_cal": "30", "symptoms": [], "allergies": [],
         "zigzag_mode": "classic", "activity_level": "light"}


def _plan(data):
    data = dict(data)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
        html = plan_engine.plan_html(data, plan)
    return data, plan, html


def _all_meals():
    for culture, pool in CM.CHILD_MEALS.items():
        for slot in SLOTS:
            for meal in pool[slot]:
                yield culture, slot, meal


def test_every_number_is_computed_from_the_ingredients():
    """‏أرقام القاعدة القديمة مكتوبة بالإيد، فرقم غلط مافيش حاجة
    تمسكه. هنا الوجبة (صنف، جرامات) والأرقام مشتقة -- والاختبار
    بيعيد الحساب من بره ويقارن."""
    for culture, slot, meal in _all_meals():
        assert meal["cal"] > 0 and meal["p"] >= 0, (culture, slot, meal)
        # ‏طاقة الماكروز لازم تقرب من السعرات: ٤/٤/٩
        energy = meal["p"] * 4 + meal["c"] * 4 + meal["f"] * 9
        off = abs(energy - meal["cal"]) / float(meal["cal"])
        assert off < 0.12, (
            "‏%s/%s: الماكروز بتطلّع %d سعرة والمكتوب %d -- %s"
            % (culture, slot, energy, meal["cal"], meal["meal"]))


def test_every_meal_knows_its_carbs_and_fat():
    """‏ده اللي القاعدة القديمة مش بتعرفه، وعشانه الورقة بتقول
    "دهون مُقدّرة"."""
    for culture, slot, meal in _all_meals():
        assert "c" in meal and "f" in meal, (culture, slot, meal)
        assert meal["c"] > 0, meal["meal"]


def test_the_portions_are_a_childs_not_an_adults():
    """‏المشكلة الأصلية: المعامل اللي بيوصّل اليوم لسعراته بيضرب
    البروتين مع السعرات، فطبق بقى "جمبري ٢٩٠جم"."""
    limit = {"breakfast": 360, "lunch": 440, "dinner": 360}
    for culture, slot, meal in _all_meals():
        assert meal["cal"] <= limit[slot], (
            "‏%s/%s %d سعرة -- حصة بالغ: %s"
            % (culture, slot, meal["cal"], meal["meal"]))
        assert meal["p"] <= 26, (
            "‏%s/%s %d جم بروتين في طبق واحد: %s"
            % (culture, slot, meal["p"], meal["meal"]))


def test_the_fat_is_in_the_growth_range():
    """‏أول نسخة طلّعت أسبوع دهونه ١٧٪ من السعرات، والتوصية لسن
    النمو ٢٥-٣٥٪ -- وهي مكتوبة في ملاحظات الموقع نفسه. السبب إن
    أطباق الطفل البسيطة دهونها شبه صفر، والعيب بان لما الوجبات بقت
    تعرف دهونها."""
    for culture, slot, meal in _all_meals():
        pct = meal["f"] * 9 / float(meal["cal"]) * 100
        assert 22 <= pct <= 38, (
            "‏%s/%s دهونه %.0f%%: %s" % (culture, slot, pct, meal["meal"]))


def test_no_slot_is_thin_enough_to_be_replaced_by_the_adult_list():
    """‏المحرّك بيستبدل أي طابور أقل من ٧ وجبات. والخليجي كان ٦ لكل
    خانة، فطفل ٨ سنين خليجي كان بياخد ٦٤-١١٠ جم بروتين بدل ٣٣ --
    جداول الأطفال كانت بتتلغي من غير صوت."""
    for culture, pool in CM.CHILD_MEALS.items():
        for slot in SLOTS:
            assert len(pool[slot]) >= 7, (culture, slot, len(pool[slot]))
        assert len(pool["snack"]) >= 7, (culture, "snack")


def test_no_single_condition_empties_a_slot():
    """‏الدهن كان لوز في ٧ وجبات، وG6PD بيمنع المكسرات كلها --
    فطابور فطار الطفل نزل من ١٢ لـ٣، والباقي اتجاب من قايمة
    البالغين. و"زيت زيتون" جوّاها "زيتون" اللي التليف الكبدي بيمنعها،
    فغدا التليف نزل لواحد.

    ‏أربعة هو الحد اللي الفلترة بتبدأ تجيب بدايل تحته."""
    thin = []
    for label in sorted(set(MD.CONDITION_MAP)):
        for culture, pool in CM.CHILD_MEALS.items():
            for slot in SLOTS:
                kept = MD.filter_by_conditions(list(pool[slot]), [label], slot)
                own = sum(1 for m in kept if m.get("child"))
                if own < 4:
                    thin.append((culture, label, slot, own))
    assert not thin, thin


def test_a_childs_plan_is_built_from_these_tables():
    _data, plan, _html = _plan(CHILD)
    for day in plan:
        for slot in day["meal_labels"]:
            text = day.get(slot)
            if not text:
                continue
            assert plan_engine is not None
            assert day.get("total_c") is not None, (
                "‏يوم %s فيه خانة مش من جداول الأطفال" % day["day"])


def test_the_week_lands_in_the_published_range():
    """‏قبل الجداول دي: ٩٤-١٥٤ جم لطفلة هدفها ٥٠."""
    _data, plan, _html = _plan(CHILD)
    worst = max(d["total_p"] for d in plan)
    assert worst <= 110, "‏أعلى يوم %d جم" % worst
    for day in plan:
        band = protein_need.band(108.8, 152, 10, 1.3, day["total_cal"])
        assert band[0] <= day["total_p"] <= band[1], (
            "‏%s: %d جم على %d سعرة، النطاق %s"
            % (day["day"], day["total_p"], day["total_cal"], band))


def test_the_sheet_says_the_carbs_and_fat_came_from_the_food():
    """‏ورقة البالغ بتقول "مُقدّرة" وهي صح. ورقة الطفل بقت تعرف."""
    _data, _plan_days, html = _plan(CHILD)
    assert "من الأكل" in html, "‏لسه بتقول مُقدّرة والأكل يعرف أرقامه"
    assert "مُقدّر" not in html


def test_the_adult_sheet_still_says_estimated():
    """‏البالغ مااتغيّرش: قاعدته مافيهاش كارب ولا دهون."""
    adult = dict(CHILD, age="30", weight="90", height="175", tdee="2400",
                 goal_cal="2000", protein_per_kg="1.8")
    _data, plan, html = _plan(adult)
    assert "مُقدّر" in html
    assert all(d.get("total_c") is None for d in plan)


def test_a_fourteen_year_old_eats_from_the_adult_pool():
    """‏التوصية بتفصل ٤-١٣ عن ١٤-١٨، والفرق مش في الرقم بس: ولد
    ١٥ سنة بياكل طبق بالغ فعلاً."""
    assert CM.pool_for(13, "مصري") is not None
    assert CM.pool_for(14, "مصري") is None
    assert CM.pool_for(30, "مصري") is None
    assert CM.pool_for(None, "مصري") is None


def test_an_unknown_culture_falls_back_to_child_food_not_adult_food():
    for culture in ("شامي", "مغربي", "عالمي", "", None):
        pool = CM.pool_for(10, culture)
        assert pool is CM.CHILD_MEALS["مصري"], culture
    assert CM.pool_for(10, "خليجي") is CM.CHILD_MEALS["خليجي"]


def test_the_gulf_child_gets_gulf_food():
    data, plan, _html = _plan(dict(CHILD, culture="خليجي", age="8",
                                   weight="30", height="128", tdee="1600",
                                   goal_cal="1600", protein_per_kg="1.1"))
    text = " ".join(d.get(k, "") for d in plan for k in d["meal_labels"])
    assert ("خبز عربي" in text or "خبز تميس" in text
            or "هريس" in text or "كبسة" in text or "مجبوس" in text), text[:200]
    assert all(d.get("total_c") is not None for d in plan)


def test_the_snack_protein_is_a_childs_not_an_adults():
    """‏المحرّك كان بيفترض ٨ جم لكل سناك، وده سناك بالغ -- يعني
    اليوم بيكسب ٥ جم بروتين من العدم."""
    assert CM.SNACK_P <= 4
    for line, nums in sorted(CM.MACROS.items()):
        if "kcal" in line:
            assert nums[1] <= 6, (line, nums)


def test_each_meal_reads_as_an_instruction_someone_can_follow():
    """‏النص هو اللي العميل بيقراه، فلازم كل صنف يكون معاه كميته."""
    for _culture, _slot, meal in _all_meals():
        for part in meal["meal"].split(" + "):
            assert re.search(r"\d", part), (
                "‏صنف من غير كمية: %r في %r" % (part, meal["meal"]))


def test_the_childs_sheet_is_one_page():
    """‏ورقة الشركة ورقة واحدة. وجبات الأطفال أصنافها أكتر (مصدر
    الدهن صنف زيادة)، فالجدول طال وزحّف الملاحظات لصفحة تانية فيها
    فقرة وتوقيع -- ٤ من ٧ أوراق أطفال طلعت ورقتين."""
    from weasyprint import HTML
    cases = [
        dict(CHILD),
        dict(CHILD, culture="خليجي", age="8", weight="30", height="128",
             tdee="1600", goal_cal="1600", protein_per_kg="1.1"),
        dict(CHILD, age="11", weight="50", height="145", tdee="1800",
             goal_cal="1700", protein_per_kg="1.2",
             diet_plan_type="five_meals"),
        dict(CHILD, age="12", weight="55", height="150", tdee="1900",
             goal_cal="1800", protein_per_kg="1.2", diet_plan_type="ramadan"),
        dict(CHILD, age="9", weight="35", height="135", tdee="1500",
             goal_cal="1500", protein_per_kg="1.1",
             symptoms=["سكري النوع الأول", "قولون عصبي",
                       "حساسية اللاكتوز"]),
        # ‏والبالغ برضه -- الضغط بيتحسب من المحتوى، فمايصحّش يكون
        # صلّح الطفل وخرّب اللي كان ماشي
        dict(CHILD, age="30", weight="90", height="170", tdee="2200",
             goal_cal="1800", protein_per_kg="1.6"),
    ]
    for case in cases:
        _data, _plan_days, html = _plan(case)
        pages = len(HTML(string=html).render().pages)
        assert pages == 1, (
            "‏%s سنة / %s / %s طلعت %d صفحات"
            % (case["age"], case["culture"], case["diet_plan_type"], pages))


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

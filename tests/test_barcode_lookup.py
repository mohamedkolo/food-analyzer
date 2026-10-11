# -*- coding: utf-8 -*-
"""‏الباركود: الناقص كان بيرفض المنتج، والصفر كان هيكدب.

‏قاعدة Open Food Facts بيملاها مستخدمون، فمنتجات كتير فيها سعرات
وبروتين والكارب أو الدهون مش مكتوبة. والكود كان بيرفض المنتج لو **أي**
واحدة من الأربعة ناقصة، ويقول "البيانات الغذائية ناقصة".

‏والحل السهل (نحط صفر) أسوأ من المشكلة: "دهون 0 جم" على كارت بيتقرا
قدام مريض مرارة أو كبد دهني كدب. فاللي مش معروف بيفضل مكتوب إنه مش
معروف -- في الكارت، وفي المقارنة، وفي الـAPI.

‏الاختبارات دي مابتنادّيش الشبكة: بتدي الدالة نفس شكل الرد اللي
بيجي من القاعدة.

Run with:  python3 tests/test_barcode_lookup.py
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_barcode_test.db"

import app as A  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _product(**nutriments):
    return {"product_name": "Test product", "nutriments": nutriments}


def test_a_complete_product_reads_as_before():
    food = A._barcode_food(_product(**{
        "energy-kcal_100g": 116, "proteins_100g": 26,
        "carbohydrates_100g": 0, "fat_100g": 1}), "123")
    assert food["cal"] == 116 and food["p"] == 26.0
    assert food["c"] == 0.0 and food["f"] == 1.0
    assert food["missing"] == []


def test_a_missing_macro_no_longer_throws_the_whole_product_away():
    """‏ده اللي كان بيحصل: المنتج كله يترفض عشان خانة واحدة."""
    food = A._barcode_food(_product(**{
        "energy-kcal_100g": 250, "proteins_100g": 5,
        "carbohydrates_100g": 40}), "123")
    assert food is not None, "‏المنتج اترفض عشان الدهون مش مكتوبة"
    assert food["cal"] == 250


def test_a_missing_macro_comes_back_as_nothing_not_as_zero():
    """‏الفرق ده هو كل الموضوع: منتج دهونه صفر حقيقي (مياه) غير منتج
    الشركة مامَلتش خانة دهونه."""
    food = A._barcode_food(_product(**{
        "energy-kcal_100g": 250, "proteins_100g": 5,
        "carbohydrates_100g": 40}), "123")
    assert food["f"] is None, food["f"]
    assert "دهون" in food["missing"], food["missing"]

    zero = A._barcode_food(_product(**{
        "energy-kcal_100g": 0, "proteins_100g": 0,
        "carbohydrates_100g": 0, "fat_100g": 0}), "123")
    assert zero["f"] == 0.0 and zero["missing"] == [], zero


def test_the_note_warns_that_a_blank_is_not_a_zero():
    food = A._barcode_food(_product(**{
        "energy-kcal_100g": 250, "proteins_100g": 5}), "123")
    assert "مش صفر" in food["note"], food["note"]
    assert "كارب" in food["note"] and "دهون" in food["note"], food["note"]


def test_energy_in_kilojoules_only_is_converted():
    """‏منتجات أوروبية كتير بتكتب الطاقة بالكيلوجول بس، وكانت
    بتترفض كأنها بدون سعرات."""
    food = A._barcode_food(_product(**{
        "energy_100g": 1046, "proteins_100g": 3}), "123")
    assert food is not None and 245 <= food["cal"] <= 255, food


def test_a_product_with_no_energy_at_all_is_still_refused():
    """‏السعرات هي الحد الأدنى -- من غيرها الكارت مالوش معنى."""
    assert A._barcode_food(_product(proteins_100g=3), "123") is None
    assert A._barcode_food({"nutriments": {}}, "123") is None


def test_rubbish_values_do_not_become_numbers():
    for bad in ("", None, "abc", -5):
        food = A._barcode_food(_product(**{
            "energy-kcal_100g": 100, "fat_100g": bad}), "123")
        assert food["f"] is None, (bad, food["f"])


def test_the_card_never_prints_a_missing_value_as_a_number():
    """‏الكارت بيكتب food.p مباشرة، فلو جه None كان هيطبع "nullg".
    والمقارنة أسوأ: Number(null) بيطلع صفر، فالمنتج اللي الشركة مش
    كاتبة دهونه كان هيكسب "أقل دهون"."""
    page = io.open(os.path.join(os.path.dirname(HERE), "templates",
                                "analyzer.html"), encoding="utf-8").read()
    for raw in ("${food.p}g", "${food.c}g", "${food.f}g",
                "(food.p * ratio)", "(food.c * ratio)", "(food.f * ratio)"):
        assert raw not in page, "‏الكارت لسه بيطبع %s على طول" % raw
    assert "macroVal(" in page and "function scaled(" in page, (
        "‏دوال التعامل مع الناقص مش موجودة")
    # ‏المقارنة بتقف قبل Number()
    row = page[page.index("function cmpRow"):]
    row = row[:row.index("\n}")]
    assert row.index("missA") < row.index("Number(a)"), (
        "‏المقارنة لسه بتحوّل الناقص لرقم قبل ما تتأكد")


def test_the_developer_api_says_a_blank_comes_back_as_null():
    """‏الـAPI عليه مشتركين بيكتبوا كود على الرد. تغيير الشكل من
    غير ما يتكتب بيكسر عندهم في صمت."""
    docs = io.open(os.path.join(os.path.dirname(HERE), "templates",
                                "api_docs.html"), encoding="utf-8").read()
    section = docs[docs.index("/api/v1/food/barcode"):][:1200]
    assert "null" in section, "‏التوثيق مش بيقول إن الناقص بيرجع null"


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

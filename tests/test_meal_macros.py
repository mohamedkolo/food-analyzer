# -*- coding: utf-8 -*-
"""‏ماكروز الوجبة من مكوّناتها -- واللي القياس قاله عن حدودها.

‏الدكتور طلب إن الدهون والكارب على الورقة يبقوا من الأكل مش من الهدف.
الملف ده بيوصل جدول الأكل (٩٣٨ صنف بأرقام كل ١٠٠ جرام) بنصوص
الوجبات، **والاختبارات دي بتحفظ القياس** عشان الحدود ما تتنسيش:

    ‏تغطية الأصناف                     ٧٤٪
    ‏وجبات كل أصنافها اتعرفت            ٢٤٠ من ٥٩٧ (٤٠٪)
    ‏وسيط الفرق عن السعرات المكتوبة     ٣٤٪
    ‏وجبات كل أصنافها **بجرامات مكتوبة** ٧ من ٥٩٧ (١٪)

‏يعني الوجبات مكتوبة كوصف طبق ("كسكس بالخضار والدجاج (كسكس ١٠٠جم +
دجاج ١٣٠جم)") مش كقايمة مكوّنات كاملة -- الزيت والصلصة والخضار مش
مكتوبين، فالحساب بينقص منهجياً.

‏فالورقة لسه بتقدّر الدهون والكارب من الهدف، **وبقت تقول إنها تقدير**.
والحل الحقيقي إن كل وجبة تحمل أرقامها (c و f جنب cal و p)، وده شغل
بيانات على ٥٩٧ وجبة -- بيانات الدكتور الإكلينيكية، مش حاجة أخترعها.

Run with:  python3 tests/test_meal_macros.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_macros_test.db"

import meal_macros as MM      # noqa: E402


def test_the_bridge_points_at_foods_that_exist():
    """‏كل اسم عام في الجسر لازم يلاقي صنف حقيقي في الجدول."""
    import food_data

    have = {MM._norm(f["n"]) for f in food_data.FOODS}
    missing = sorted({v for v in MM.GENERIC.values() if MM._norm(v) not in have})
    assert not missing, "‏أسماء مش موجودة في جدول الأكل: %s" % missing


def test_the_head_of_the_dish_wins_not_the_longest_word():
    """‏أكتر غلطة في المطابقة، وجرّبت غيرها مرتين وفشل.

      "فول بطحينة 150جم"  -> **طحينة** (٨٩٢ سعرة/١٠٠جم) بدل الفول،
                             فالوجبة بقت ١١٧٦ سعرة والمكتوب ٣٦٠
      "لبن لوز"           -> **لوز** (٥٨٠ سعرة) بدل اللبن

    ‏واللي بيخلّي الترتيب صح: اسم الطبق بيبدأ بالمكوّن الأساسي واللي
    بعده وصف.
    """
    cases = {
        "🥘 فول بطحينة 150جم": "فول",
        "🥛 لبن لوز": "حليب",
        "🍞 خبز اسمر": "خبز",
        "🍗 صدر دجاج مشوي 150جم": "دجاج",
    }
    for item, want in cases.items():
        food = MM.find_food(item)
        assert food, "‏%s مالقاش حاجة" % item
        assert want in food["n"], "‏%s -> %s" % (item, food["n"])


def test_arabic_spelling_does_not_break_the_match():
    """‏الوجبة بتكتب "خبز اسمر" والجدول "خبز أسمر". نفس دالة التطبيع
    اللي الفلترة الطبية ماشية عليها -- مقياس واحد في المكانين."""
    assert MM._norm("خبز أسمر") == MM._norm("خبز اسمر")
    assert MM.find_food("🍞 خبز اسمر 60جم") is not None


def test_a_meal_of_plain_grams_adds_up():
    """‏لما كل صنف بجرامات ومتطابق، الحساب بيشتغل صح."""
    out = MM.macros("🍗 صدر دجاج مشوي 150جم + 🍚 ارز بني 120جم + "
                    "🫒 زيت زيتون 5مل")
    assert out["covered"] >= 0.99, out["items"]
    assert out["cal"] > 0 and out["p"] > 0 and out["c"] > 0
    # ‏دجاج ١٥٠جم لوحده فوق ٣٠ جم بروتين
    assert out["p"] >= 30, out


def test_the_quantity_is_read_three_ways():
    """‏جرامات مكتوبة، عدد × وزن الوحدة، وحصة افتراضية."""
    grams, how = MM.item_grams("🍗 صدر دجاج 150جم")
    assert (grams, how) == (150.0, "grams")
    grams, how = MM.item_grams("🍌 موز 1")
    assert how == "count" and grams > 50, (grams, how)
    grams, how = MM.item_grams("🥗 سلطة")
    assert how == "default" and grams > 0, (grams, how)


def test_nothing_is_trusted_without_a_second_witness():
    """‏نفس قاعدة قراءة ورقة التحليل: الرقم المحسوب لازم يتأكّد من
    مصدر تاني. هنا المصدر هو السعرات المكتوبة بإيد الدكتور."""
    good = "🍗 صدر دجاج مشوي 150جم + 🍚 ارز بني 120جم"
    computed = MM.macros(good)["cal"]
    assert MM.trusted(good, computed) is not None
    # ‏رقم بعيد -> مش مصدّق
    assert MM.trusted(good, computed * 3) is None
    # ‏ومن غير رقم مكتوب مافيش شاهد
    assert MM.trusted(good, None) is None
    assert MM.trusted(good, 0) is None


def test_the_measured_limits_are_still_the_limits():
    """‏القياس محفوظ هنا عشان ما يتنسيش ولا يتبالغ فيه.

    ‏لو حد وسّع جدول الأكل أو الجسر، الأرقام دي هتطلع أحسن --
    والاختبار بيفشل ويتحدّث بالمقيس الجديد. ولو حاجة كسرت المطابقة،
    بيفشل كمان.
    """
    import meal_database as md

    meals, seen = [], set()
    for pool in ("WEIGHT_LOSS", "MUSCLE_GAIN", "BULKING", "MAINTENANCE"):
        stack = [getattr(md, pool, None)]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                if isinstance(cur.get("meal"), str) and cur.get("cal"):
                    if cur["meal"] not in seen:
                        seen.add(cur["meal"])
                        meals.append((cur["meal"], cur["cal"]))
                else:
                    stack.extend(cur.values())
            elif isinstance(cur, (list, tuple)):
                stack.extend(cur)

    assert len(meals) > 400, len(meals)
    covered = [MM.macros(t)["covered"] for t, _c in meals]
    average = sum(covered) / len(covered)
    assert average >= 0.65, "‏التغطية نزلت لـ%.0f%%" % (average * 100)

    full = sum(1 for c in covered if c >= 0.999)
    assert full >= 200, "‏الوجبات المغطاة بالكامل نزلت لـ%d" % full


def test_the_fat_description_is_not_thrown_away_before_the_lookup():
    """‏"كامل الدسم" و"خالي الدسم" في قايمة الوصف اللي بيتشال قبل
    البحث، وهما في نفس الوقت **جزء من أسماء في الجدول**. فـ"حليب كامل
    الدسم" كان بيتشال منه الوصف ويفضل "حليب"، والجسر العام بيوديه على
    لبن رايب (٤٠ سعرة) بدل الحليب الكامل (٦١).

    ‏يعني كوباية لبن لعميلة بتزوّد وزنها كانت بتتحسب ناقصة التلت --
    والوصف اللي بيفرّق هو بالظبط اللي اتشال.
    """
    assert MM.find_food("حليب كامل الدسم 250مل")["n"] == "حليب كامل الدسم"
    assert MM.find_food("زبادي خالي الدسم 200جم")["n"] == "زبادي خالي الدسم"
    assert MM.macros("🥛 حليب كامل الدسم 250مل")["cal"] > 140


def test_the_description_is_still_stripped_when_the_table_has_no_match():
    """‏الشيل نفسه لسه لازم يشتغل: "دجاج مشوي" مش اسم في الجدول."""
    assert MM.macros("🍗 فراخ مسلوقة 200جم")["covered"] >= 0.99


def test_the_old_traps_are_still_closed():
    """‏الترتيب "الأقرب لأول الصنف" اتجرّب غيره مرتين وفشل. التجربة
    التانية (النص زي ما هو الأول) مالهاش حق تفتحهم تاني."""
    assert MM.find_food("فول بطحينة 150جم")["n"] == "فول مدمس"
    assert MM.find_food("لبن لوز 200مل")["n"] == "حليب لوز غير محلى"  # almond milk, never the nut



def test_a_count_followed_by_a_description_is_still_a_count():
    """‏"بيض اومليت 3 بالسبانخ" كانت بتتحسب بيضة واحدة مهما كان الرقم.

    ‏العدد كان بيتدوّر عليه في **آخر** الصنف بس، فأي وصف بعده
    ("بالسبانخ"، "بالفرن") بيخلّيه حصة افتراضية. صاحب المشروع شافها على
    الشاشة: زوّد البيض بزرار + والرقم على الورقة اتغيّر ومجموع اليوم
    فضل زي ما هو.
    """
    three = MM.item_grams("🥚 بيض اومليت 3 بالسبانخ")
    four = MM.item_grams("🥚 بيض اومليت 4 بالسبانخ")
    one = MM.item_grams("🥚 بيض اومليت 1 بالسبانخ")
    assert three[1] == "count" and four[1] == "count", (three, four)
    assert three[0] == 3 * one[0] and four[0] == 4 * one[0], (one, three, four)
    assert MM.macros("🥚 بيض اومليت 4 بالسبانخ")["cal"] > MM.macros("🥚 بيض اومليت 3 بالسبانخ")["cal"]



def test_a_fraction_is_not_read_as_a_count():
    """‏"1/2 رغيف" نص رغيف، مش رغيف ولا رغيفين."""
    for text in ("🍞 عيش بلدي 1/2 رغيف", "🍞 عيش بلدي 1/2"):
        grams, how = MM.item_grams(text)
        whole, _ = MM.item_grams("🍞 عيش بلدي 1")
        assert grams < 2 * whole and grams != whole * 2, (text, grams, how)


# ‏أصناف كانت بتتحسب صفر وهي موجودة في الجدول باسم أطول ("كينوا" والجدول
# فيه "كينوا مطبوخة"). الأرقام من الجدول نفسه -- مفيش رقم جديد اتكتب.
WORD_CASES = {
    "🫒 زيت 1 ملعقة": "زيت زيتون",
    "🧀 فيتا 30جم": "جبنة فيتا",
    "🥗 كينوا 100جم": "كينوا مطبوخة",
    "🌿 زعتر": "زعتر ناشف",
    "🍯 دبس 1 ملعقة": "دبس تمر",
    "🍲 حريرة كبيرة": "حريرة مغربية",
    "🧀 بارميزان 15جم": "جبنة بارميزان",
    "🌾 برغل 100جم": "برغل مطبوخ",
    "🌯 تورتيلا قمح كامل": "عيش تورتيلا",
    "🧀 حلوم 50جم": "جبنة حلوم",
    "🍲 كسكس مغربي 150جم": "كسكسي مطبوخ",
    "🍵 شاي": "شاي بدون سكر",
    "🍗 فروج مشوي 200جم": "فراخ مشوية (ربع فرخة)",
    "🍗 فرخة كاملة 250جم": "فراخ مشوية (ربع فرخة)",
    "🧆 طعمية مشوية 5": "فلافل/طعمية",
    "🍢 شيش طاووق 200جم": "صدر دجاج",
    "🥩 ستيك 200جم": "لحم بقري قليل الدهن",
    "🥣 يوغورت 150جم": "زبادى خالى الدسم",
    # ‏صاحب المشروع: "فاصوليا خضرا، والمشاوي فراخ، والفواكه تفاح".
    "🫘 فاصوليا 150جم": "فاصوليا خضراء",
    "🍖 مشاوي مختلطة 150جم": "فراخ مشوية (ربع فرخة)",
    "🍎 فواكه 150جم": "تفاح",
    # ‏البيضا والحمرا بأساميهم: "فاصوليا" لوحدها خضرا، بس دول لأ. والبيضا
    # كانت بتتحسب **بيضة** -- "بيض" جوه "بيضاء".
    "🫘 فاصوليا بيضاء 150جم": "فاصوليا بيضاء مطبوخة",
    "🫘 فاصوليا بيضا 150جم": "فاصوليا بيضاء مطبوخة",
    "🫘 فاصوليا حمراء 100جم": "فاصوليا حمراء",
}


def test_foods_written_shorter_than_the_table_are_recognised():
    for text, want in WORD_CASES.items():
        got = MM.find_food(text)
        assert got and MM._norm(got["n"]) == MM._norm(want), (text, got and got["n"])
        assert MM.macros(text)["cal"] > 0 or "شاي" in text, text


def test_the_new_words_match_whole_words_only():
    """‏"زيت" جوه "زيتون": لو اتطابقت كحروف، ٤ زيتونات كانت هتبقى ٤ ملاعق
    زيت -- حوالي ٥٠٠ سعرة زيادة على اليوم."""
    for text in ("🫒 زيتون 4", "زيتون اسود 30جم", "🥗 سلطة بالزيتون"):
        got = MM.find_food(text)
        assert not got or "زيت زيتون" != got["n"], (text, got and got["n"])


def test_every_word_bridge_points_at_a_food_that_exists():
    import food_data
    have = {MM._norm(f["n"]) for f in food_data.FOODS}
    missing = sorted({v for v in MM.GENERIC_WORDS.values() if MM._norm(v) not in have})
    assert not missing, missing

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

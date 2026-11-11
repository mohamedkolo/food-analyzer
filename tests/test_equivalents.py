# -*- coding: utf-8 -*-
"""‏بدائل الأصناف للعميل: إيه اللي ينفع يتاكل بدل صنف في الخطة.

‏الميزة دي بتدّي العميل إذن ياكل حاجة الأخصائي ماكتبهاش بإيده، فكل
اختبار هنا على سؤال من اتنين:

  ‏١) **هل البديل آمن للعميل ده؟** حالته المرضية، حساسيته، واللي طلب
     يبعد عنه -- ولو الحالة مسجّلة في مكان واحد بس من الاتنين.
  ‏٢) **هل البديل فعلاً بديل؟** نفس السعرات ونفس البروتين والكارب
     والدهون، مش السعرات لوحدها.

‏ولما مانقدرش نتأكد، الإجابة الصح هي "مفيش بديل" -- مش بديل بالتخمين.

Run with:  python3 tests/test_equivalents.py
"""

import json
import os
import sys
from datetime import datetime

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_equivalents.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A              # noqa: E402
import equivalents as E      # noqa: E402
import food_data             # noqa: E402
import meal_database as md   # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False


def _cond(key):
    return next(c for c, k in md.CONDITION_MAP.items() if k == key)


DIABETES, PRESSURE, KIDNEY, COLON, HEART = (
    _cond("سكري"), _cond("ضغط"), _cond("كلوي"), _cond("قولون"), _cond("قلب"))

# ‏أصناف بتتكتب في الخطط فعلاً، بكميات محددة.
ITEMS = ["ارز بني 140جم", "صدر دجاج مشوي 150جم", "بيض مسلوق 3",
         "خبز اسمر 100جم", "تفاح 230جم", "تونة بالماء 215جم",
         "زبادي يوناني 150جم", "لوز 30جم", "خيار 100جم", "فول مدمس 200جم",
         "بطاطس مسلوقة 200جم", "شوفان 50جم", "موز 1", "جبن قريش 100جم",
         "سمك مشوي 200جم", "عدس 150جم", "برتقال 200جم"]


def _alts(text, **data):
    return E.alternatives(text, E.profile_from(data))


def _names(text, **data):
    got = _alts(text, **data)
    return [o["name"] for o in (got or {}).get("options", [])]


def _food(name):
    return next(f for f in food_data.FOODS if f["n"] == name)


def _flag_required(food, key):
    """Must this food carry the table's "safe for" flag for this condition?

    Always -- with one exception the books forced: a diabetic's starches.
    The table marks no starch at all as safe for diabetes, and both books
    say starch is necessary for diabetics; there the carbohydrate match and
    the refined-white ban do the protecting instead.
    """
    return not (key == "سكري" and E.group_of(food) == E.BREAD)


def _all_options(**data):
    """Every option offered for every item, with the food row behind it."""
    out = []
    for item in ITEMS:
        for name in _names(item, **data):
            out.append((item, _food(name)))
    return out


# ── ٢) البديل فعلاً بديل ────────────────────────────────────────────

def test_every_swap_matches_calories_and_all_three_macros():
    checked = 0
    for item in ITEMS:
        got = _alts(item)
        if not got:
            continue
        want = got["original"]
        for o in got["options"]:
            checked += 1
            assert abs(o["cal"] - want["cal"]) <= E.CAL_TOLERANCE * want["cal"] + 1, (item, o)
            for key in ("p", "c", "f"):
                allowed = max(E.MACRO_ABS_G, E.MACRO_REL * want[key]) + 0.1
                assert abs(o[key] - want[key]) <= allowed, (item, key, want, o)
    assert checked >= 30, "almost nothing was offered (%d) -- the test proves nothing" % checked


def test_matching_calories_alone_is_not_enough():
    """‏١٥٠جم صدر دجاج = ٢٤٨ سعرة. نفس السعرات من لحم مفروم دهني أو من
    مكسرات موجودة في الجدول -- بس بنص البروتين وأضعاف الدهون."""
    names = _names("صدر دجاج مشوي 150جم")
    assert names, "nothing offered for chicken breast"
    for name in names:
        food = _food(name)
        assert food["p"] / max(food["cal"], 1) > 0.12, (name, "is not lean protein")
        assert E.group_of(food) == E.MEAT, name


def test_a_swap_stays_in_the_same_kind_of_food():
    for item, food in _all_options():
        source = E.read_item(item)["food"]
        assert E.group_of(food) == E.group_of(source), (item, food["n"])


def test_the_same_food_is_not_offered_as_its_own_swap():
    assert not any("ارز" in md.normalize_ar(n) for n in _names("ارز بني 140جم"))
    assert not any("بيض" in md.normalize_ar(n) for n in _names("بيض مسلوق 3"))
    assert "صدر دجاج" not in " ".join(_names("صدر دجاج مشوي 150جم"))


def test_processed_and_raw_foods_are_never_offered():
    for item, food in _all_options():
        plain = md.normalize_ar(food["n"]) + " "
        for word in E._NOT_A_SWAP:
            assert md.normalize_ar(word) not in plain, (item, food["n"])


def test_an_item_with_no_exact_amount_gets_no_swap():
    """‏"سلطة" من غير جرامات: الكمية تخمين، فبديل محسوب عليها رقم واثق
    فوق كمية غلط."""
    for vague in ("سلطة", "خضار مشكل", "وجبة حرة", "", "شاي"):
        assert _alts(vague) is None, vague
    assert _alts("تفاح 230جم") is not None


def test_half_of_a_composite_dish_is_not_read_as_an_item():
    """‏"🥗 سلطة تونة كبيرة (تونة 150جم + خضار 230جم)" بتتقسم على " + " من
    نص القوس. القطعة الأولى كانت بتتقرا "سلطة 150جم" -- والـ١٥٠ بتاعة
    التونة."""
    meal = "🥗 سلطة تونة كبيرة (تونة 150جم + خضار 230جم) + 🍞 خبز اسمر 100جم"
    parts = [p.strip() for p in meal.split(" + ")]
    assert _alts(parts[0]) is None, parts[0]
    assert _alts(parts[1]) is None, parts[1]
    assert _alts(parts[2]) is not None, parts[2]
    assert _alts("🍎 تفاح 230جم - 119 kcal") is not None


def test_amounts_are_ones_a_person_can_measure():
    for item in ITEMS:
        for o in (_alts(item) or {}).get("options", []):
            assert "جم" in o["amount"], o
            assert not o["amount"].startswith("0 "), o
    assert "جم)" in next(o["amount"] for o in _alts("بيض مسلوق 3")["options"]
                         if "(" in o["amount"])


# ── ١) البديل آمن ───────────────────────────────────────────────────

def test_no_swap_breaks_a_condition_on_either_list():
    """‏الفحص مرتين من قايمتين اتكتبوا لوحدهم: UNSAFE_FOODS (بتاعة
    المولّد) وعلامة "آمن لـ" في جدول الأكل. البديل لازم يعدّي الاتنين."""
    for condition in (DIABETES, PRESSURE, KIDNEY, COLON, HEART):
        key = md.CONDITION_MAP[condition]
        offered = _all_options(symptoms=[condition])
        for item, food in offered:
            assert not md._contains_unsafe(food["n"], key), (condition, item, food["n"])
            if _flag_required(food, key):
                assert E.SAFE_KEY[key] in (food.get("safe") or []), \
                    (condition, item, food["n"], food.get("safe"))


def test_a_food_nobody_reviewed_is_not_offered_to_a_patient():
    """‏١٨٧ صنف في الجدول مالهمش علامات "آمن لـ" خالص. السكوت مش موافقة:
    لمريض سكر مايتعرضوش، حتى لو مافيش حاجة بتقول إنهم ممنوعين."""
    unreviewed = [f for f in food_data.FOODS if not f.get("safe")
                  and E.group_of(f)]
    assert len(unreviewed) > 50
    profile = E.profile_from({"symptoms": [DIABETES]})
    assert not any(E.allowed_for(f, profile) for f in unreviewed
                   if _flag_required(f, "سكري"))
    for condition in (KIDNEY, PRESSURE, HEART, COLON):
        strict = E.profile_from({"symptoms": [condition]})
        assert not any(E.allowed_for(f, strict) for f in unreviewed), condition
    healthy = E.profile_from({})
    assert any(E.allowed_for(f, healthy) for f in unreviewed)


def test_two_conditions_must_both_be_satisfied():
    both = _all_options(symptoms=[DIABETES, PRESSURE])
    for item, food in both:
        need = {"dm", "htn"} if _flag_required(food, "سكري") else {"htn"}
        assert need <= set(food.get("safe") or []), (item, food["n"])
    smoked = _food("صدور فراخ مدخنة")
    assert "htn" not in smoked["safe"]
    assert not E.allowed_for(smoked, E.profile_from({"symptoms": [PRESSURE]}))


def test_a_condition_shrinks_the_list_and_never_grows_it():
    for item in ITEMS:
        for condition in (DIABETES, KIDNEY):
            profile = E.profile_from({"symptoms": [condition]})
            for name in _names(item, symptoms=[condition]):
                assert E.allowed_for(_food(name), profile)
            # ‏الحالة ماتضيفش صنف ماكانش معروض من غيرها إلا لو اللي قبله اتشال
            assert len(_names(item, symptoms=[condition])) <= E.MAX_RESULTS
    assert len(_all_options(symptoms=[DIABETES])) < len(_all_options())


def test_an_allergy_closes_the_whole_category_not_just_matching_names():
    """‏"مابياكلش سمك" لازم تمنع البلطي والباسا والجمبري -- ومافيش واحد
    فيهم اسمه فيه كلمة "سمك"."""
    free = [_food(n)["cat"] for n in _names("صدر دجاج مشوي 150جم")]
    assert "fish" in free, "the test needs fish to be on offer without the allergy"
    for data in ({"allergies": ["الأسماك"]}, {"disliked_foods": "سمك"},
                 {"notes": "بدون سمك"}):
        cats = [_food(n)["cat"] for n in _names("صدر دجاج مشوي 150جم", **data)]
        assert cats and "fish" not in cats, (data, cats)
    assert _names("لوز 30جم", allergies=["المكسرات"]) == []
    assert _names("تونة بالماء 215جم", allergies=["الأسماك"]) == [] or all(
        _food(n)["cat"] != "fish" for n in _names("تونة بالماء 215جم",
                                                  allergies=["الأسماك"]))


def test_lactose_does_not_ban_eggs_and_gluten_does_not_ban_rice():
    profile = E.profile_from({"allergies": ["اللاكتوز"]})
    assert E.allowed_for(_food("بيضة كاملة"), profile)
    assert not E.allowed_for(_food("جبن قريش"), profile)
    assert not E.allowed_for(_food("زبادي يوناني"), profile)
    gluten = E.profile_from({"allergies": ["الجلوتين"]})
    assert E.allowed_for(_food("أرز أبيض مطبوخ"), gluten)
    for wheat in ("عيش بلدي", "مكرونة مسلوقة", "توست أسمر", "برغل مطبوخ"):
        assert not E.allowed_for(_food(wheat), gluten), wheat
    egg = E.profile_from({"allergies": ["البيض"]})
    assert not E.allowed_for(_food("بيضة كاملة"), egg)


def test_a_keto_client_only_gets_keto_foods():
    for item, food in _all_options(diet_plan_type="keto"):
        assert "keto" in (food.get("safe") or []), (item, food["n"])


# ── القواعد اللي من الكتاب ──────────────────────────────────────────
# ‏[خ] = د. منى خليل عبد القادر، «التغذية العلاجية»، ط٢ ٢٠٠٤.

def test_the_groups_are_the_books_six_exchange_groups():
    """‏[خ] ص ٢٩-٣٥. تلات حاجات مختلفة عن فئات جدول الأكل، وكل واحدة
    بتغيّر مين يتبدّل بمين: البيض والجبن مع اللحوم (مش الألبان)، البقول
    والبطاطس مع الخبز، والمكسرات والزبدة مع الدهن."""
    want = {"بيضة كاملة": E.MEAT, "جبن قريش": E.MEAT, "صدر دجاج": E.MEAT,
            "بلطي فيليه": E.MEAT, "حليب خالي الدسم": E.MILK,
            "زبادي يوناني": E.MILK, "عيش بلدي": E.BREAD,
            "أرز أبيض مطبوخ": E.BREAD, "فول مدمس": E.BREAD,
            "بطاطس مسلوقة": E.BREAD, "تفاح": E.FRUIT, "خيار": E.VEG,
            "لوز": E.FAT, "زيت زيتون": E.FAT}
    got = {name: E.group_of(_food(name)) for name in want}
    assert got == want, {k: (got[k], want[k]) for k in want if got[k] != want[k]}
    assert "بيضة كاملة" in _names("جبن قريش 100جم"), \
        "egg and cheese are one exchange group and did not swap"


def test_a_kidney_patient_gets_no_high_potassium_swap_and_no_milk_swap():
    """‏[خ] ص ١٩٤-١٩٦: البوتاسيوم محدد، ووحدة الألبان أعلى مجموعة (٣٤٠ ملجم).
    ‏[UN] p.885 بيسمّي الفواكه والخضروات اللي "regular use is discouraged":
    الموز والبرتقال والتمر والفواكه المجففة والشمام والطماطم والسبانخ
    والبطاطس والبطاطا والكوسة والبقول... وبيقول إن الباقي مسموح بكميات
    محدودة. فالألبان مقفولة كمجموعة، والمسمّين مقفولين، والباقي لازم يكون
    متعلّم عليه "آمن للكلى" كمان."""
    assert _alts("زبادي يوناني 150جم", symptoms=[KIDNEY])["options"] == []
    kidney = E.profile_from({"symptoms": [KIDNEY]})
    for name in ("موز", "برتقال", "تمر جاف", "زبيب", "طماطم", "سبانخ",
                 "بطاطس مسلوقة", "بطاطا حلوة", "كوسة", "فول مدمس"):
        assert not E.allowed_for(_food(name), kidney), name
    offered = 0
    for item in ("تفاح 230جم", "خيار 100جم", "برتقال 200جم", "موز 1",
                 "بطاطس مسلوقة 200جم"):
        for name in _names(item, symptoms=[KIDNEY]):
            offered += 1
            food = _food(name)
            assert "ckd" in food["safe"], (item, name)
            assert not E._banned_by_book(food, "كلوي"), (item, name)
    assert offered, "no fruit or vegetable swap at all for a kidney patient"
    # ‏قبل الكتاب التالت الموز كان ممكن يطلع؛ وقبل التاني العنب والتين
    assert "موز" not in " ".join(_names("تفاح 230جم", symptoms=[KIDNEY]))
    assert "تين" not in " ".join(_names("تفاح 230جم", symptoms=[KIDNEY]))


def test_a_kidney_patient_never_gets_more_protein_than_the_plan_gave():
    """‏[خ] ص ١٩٢ و[CN] p.243: البروتين محدد بـ٠٫٦-٠٫٨ جم/كجم. هامش الـ٢٥٪
    بتاع الماكروز كان بيسمح بديك رومي فيه ٩ جم بروتين زيادة عن الأصل."""
    checked = 0
    for item in ITEMS:
        got = _alts(item, symptoms=[KIDNEY])
        for o in (got or {}).get("options", []):
            checked += 1
            assert o["p"] <= got["original"]["p"] + E.KIDNEY_PROTEIN_SLACK_G, (item, o)
    assert checked, "nothing was offered to a kidney patient at all"
    turkey = [o for o in _alts("صدر دجاج مشوي 150جم")["options"] if o["name"] == "ديك رومي"]
    assert turkey and turkey[0]["p"] > 50, "the test needs turkey to be the high-protein swap"
    assert "ديك رومي" not in _names("صدر دجاج مشوي 150جم", symptoms=[KIDNEY])


def test_a_kidney_patient_is_not_offered_phosphorus_rich_or_processed_food():
    """‏[خ] ص ١٩٨: "اللبن، الجبن، البقول الجافة، الكولا، المكسرات وزبدة
    الفول السوداني". وص ١٩٧: الأطعمة المعلبة والمجمدة والمصنعة (صوديوم)."""
    profile = E.profile_from({"symptoms": [KIDNEY]})
    for name in ("جبن قريش", "جبنة رومي", "لوز", "فستق", "سمسم", "طحينة",
                 "تونة معلبة بالماء"):
        assert not E.allowed_for(_food(name), profile), name
    assert _names("لوز 30جم", symptoms=[KIDNEY]) == []


def test_a_heart_patient_is_kept_to_the_books_allowed_list():
    """‏[خ] ص ١٧٨، جدول "الأطعمة الممنوعة / المسموح بها"."""
    heart = E.profile_from({"symptoms": [HEART]})
    banned = ("لحم ضأن", "كبدة بقري", "جمبري", "سردين", "تونة معلبة بالماء",
              "كابوريا", "صفار بيض", "بيضة كاملة", "حليب كامل الدسم",
              "زبادي كامل الدسم", "جبنة رومي", "جبنة شيدر")
    for name in banned:
        assert not E.allowed_for(_food(name), heart), name
    for name in ("بلطي فيليه", "بياض بيض", "حليب خالي الدسم", "جبن قريش",
                 "زيت زيتون"):
        food = _food(name)
        assert not E._banned_by_book(food, "قلب"), name
    # ‏"ريش" (لحم الريش، ممنوع) مش آخر "قريش" (الجبن القريش، مسموح)
    assert E._banned_by_book({"n": "لحم ريش ضاني"}, "قلب")
    for item, food in _all_options(symptoms=[HEART]):
        assert not E._banned_by_book(food, "قلب"), (item, food["n"])
    # ‏نفس القايمة للكوليسترول
    chol = _cond("كوليسترول")
    assert not E.allowed_for(_food("لحم ضأن"), E.profile_from({"symptoms": [chol]}))


def test_high_blood_pressure_closes_salted_and_processed_food():
    """‏[خ] ص ١٧١-١٧٢: ٣٠ جم جبنة شيدر = ٤٠٠ ملجم صوديوم، زيتونة كبيرة =
    ١٣٠، والمعلّب والمصنّع مصدر أغلب الصوديوم."""
    profile = E.profile_from({"symptoms": [PRESSURE]})
    for name in ("جبنة شيدر", "جبنة رومي", "تونة معلبة بالماء"):
        assert not E.allowed_for(_food(name), profile), name
    for item, food in _all_options(symptoms=[PRESSURE]):
        assert not E._banned_by_book(food, "ضغط"), (item, food["n"])


def test_a_diabetic_gets_fresh_fruit_not_dried_fruit_or_juice():
    """‏[خ] ص ١٥٩: فواكه طازجة، مش العصائر ولا المعلبة ولا المجففة."""
    names = _names("تفاح 230جم", symptoms=[DIABETES])
    assert names, "no fruit at all for a diabetic"
    for name in names:
        for word in ("زبيب", "تمر", "عصير", "قراصيا"):
            assert word not in name, name
    assert "زبيب" in " ".join(_names("تفاح 230جم")), \
        "the test needs raisins to be on offer without diabetes"


def test_a_pregnant_client_is_not_offered_feta_tuna_or_mackerel():
    """‏[UN] p.499: الفيتا والأجبان الزرقاء (ليستيريا)، والتونة والماكريل
    (زئبق، وليهم حد أسبوعي مانقدرش نعدّه من هنا)."""
    pregnant = E.profile_from({"symptoms": [_cond("حامل")]})
    for name in ("جبنة فيتا", "جبنة فيتا لايت", "ماكريل",
                 "تونة طازجة (ستيك)", "تونة معلبة بالماء"):
        assert not E.allowed_for(_food(name), pregnant), name
    for name in ("صدر دجاج", "بلطي فيليه", "جبن قريش", "بيضة كاملة"):
        assert E.allowed_for(_food(name), pregnant), name
    offered = _names("بيض مسلوق 3")
    assert any("فيتا" in n for n in offered), \
        "the test needs feta to be on offer when not pregnant"
    assert not any("فيتا" in n for n in
                   _names("بيض مسلوق 3", symptoms=[_cond("حامل")]))


def test_a_diabetic_gets_starch_swaps_with_the_carbohydrate_held_steady():
    """‏الكتابين بيقولوا النشويات لمريض السكر مفيدة وضرورية ([خ] ص ١٥٧)،
    واللي بيحكم سكر الدم هو **كمية** الكارب، ولازم تبقى ثابتة من وجبة
    لوجبة ([UN] p.821). جدول الأكل ماكانش معلّم على ولا نشا إنه آمن للسكري،
    فمريض السكر ماكانش بيطلعله بديل للخبز خالص."""
    checked = 0
    for item in ("خبز اسمر 100جم", "ارز بني 140جم", "فول مدمس 200جم",
                 "شوفان 50جم", "تفاح 230جم"):
        got = _alts(item, symptoms=[DIABETES])
        for o in got["options"]:
            checked += 1
            want = got["original"]["c"]
            assert abs(o["c"] - want) <= max(E.DIABETES_CARB_ABS_G,
                                             E.DIABETES_CARB_REL * want) + 0.1, (item, o)
            food = _food(o["name"])
            assert not md._contains_unsafe(food["n"], "سكري"), (item, o)
            assert not E._banned_by_book(food, "سكري"), (item, o)
    assert _names("خبز اسمر 100جم", symptoms=[DIABETES]), "still no bread swap"
    assert checked >= 8, checked
    diabetic = E.profile_from({"symptoms": [DIABETES]})
    for refined in ("توست أبيض", "أرز أبيض مطبوخ", "عيش فينو", "خبز أبيض"):
        assert not E.allowed_for(_food(refined), diabetic), refined
    # ‏الاستثناء للنشويات بس: صنف من مجموعة تانية من غير علامة لسه مقفول
    assert not E.allowed_for(_food("جبنة بارميزان"), diabetic)


def test_gout_closes_the_high_purine_foods():
    """‏[UN] p.890، Table 28-8."""
    gout = E.profile_from({"symptoms": [_cond("نقرس")]})
    for name in ("كبدة بقري", "كبدة دجاج", "سردين", "ماكريل"):
        assert not E.allowed_for(_food(name), gout), name
    assert E.allowed_for(_food("صدر دجاج"), gout)
    for item, food in _all_options(symptoms=[_cond("نقرس")]):
        assert not E._banned_by_book(food, "نقرس"), (item, food["n"])


def test_reflux_and_gallbladder_never_get_a_fattier_swap():
    """‏الارتجاع: [UN] p.736، Table 23-3 (high-fat foods، والشوكولاتة والثوم
    والبصل والنعناع والكافيين). المرارة: [UN] p.801، نظام قليل الدهن."""
    for key, slack in (("ارتجاع", E.REFLUX_FAT_SLACK_G),
                       ("مرارة", E.GALLBLADDER_FAT_SLACK_G)):
        checked = 0
        for item in ITEMS:
            got = _alts(item, symptoms=[_cond(key)])
            for o in (got or {}).get("options", []):
                checked += 1
                assert o["f"] <= got["original"]["f"] + slack + 0.05, (key, item, o)
        assert checked >= 10, (key, checked)
    reflux = E.profile_from({"symptoms": [_cond("ارتجاع")]})
    for name in ("بصل", "ثوم"):
        assert not E.allowed_for(_food(name), reflux), name


def test_irritable_bowel_is_not_offered_the_gas_forming_foods():
    """‏[UN] p.775 وTable 24-2 p.758: تتجنب "unless they can tolerate these
    foods" -- ومانعرفش العميل ده بيستحمل إيه."""
    names = _names("تفاح 230جم", symptoms=[COLON]) + _names(
        "خيار 100جم", symptoms=[COLON]) + _names("خبز اسمر 100جم", symptoms=[COLON])
    assert names
    for name in names:
        for word in ("كمثر", "بروكلي", "قرنبيط", "كرنب", "ذرة", "بصل", "فول"):
            assert word not in name, name
    assert "كمثرى" in _names("تفاح 230جم"), "the test needs pear on offer otherwise"


def test_gluten_and_lactose_work_as_conditions_not_only_as_allergies():
    """‏[UN] p.768، Table 24-6. نفس القفل سواء اتسجّلت حساسية أو حالة."""
    gluten = E.profile_from({"symptoms": [_cond("جلوتين")]})
    for wheat in ("عيش بلدي", "مكرونة مسلوقة", "برغل مطبوخ", "توست أسمر"):
        assert not E.allowed_for(_food(wheat), gluten), wheat
    for ok in ("أرز بسمتي مطبوخ", "كينوا مطبوخة"):
        assert E.allowed_for(_food(ok), gluten), ok
    lactose = E.profile_from({"symptoms": [_cond("لاكتوز")]})
    assert not E.allowed_for(_food("زبادي يوناني"), lactose)
    assert not E.allowed_for(_food("جبن قريش"), lactose)
    assert E.allowed_for(_food("بيضة كاملة"), lactose)


def test_salt_restricted_conditions_get_cottage_cheese_only():
    """‏الضغط ([خ] ص ١٧٢) وتليف الكبد بالاستسقاء ([UN] p.795-796، ٢٠٠٠ ملجم
    صوديوم). "لايت" معناها دسم أقل مش ملح أقل: الفيتا اللايت لسه مالحة."""
    for key in ("ضغط", "تليف"):
        profile = E.profile_from({"symptoms": [_cond(key)]})
        for salty in ("جبنة فيتا لايت", "جبن شيدر قليل الدسم", "جبنة رومي",
                      "تونة معلبة بالماء"):
            assert not E.allowed_for(_food(salty), profile), (key, salty)
        assert not E._banned_by_book(_food("جبن قريش"), key)


def test_a_cooked_dish_is_never_offered_as_a_swap_for_one_food():
    """‏"مكرونة بالصلصة" و"بيتزا" أطباق، مش أصناف: مكوّناتها مابتتفحصش
    واحد واحد على حالة العميل."""
    for item, food in _all_options():
        plain = md.normalize_ar(food["n"]) + " "
        assert not E._DISH.search(plain), (item, food["n"])
    for item in ("خبز اسمر 100جم", "صدر دجاج مشوي 150جم", "بيض مسلوق 3"):
        for name in _names(item, symptoms=[KIDNEY]) + _names(item):
            assert "بيتزا" not in name and "بال" not in name, (item, name)


# ── المسار ──────────────────────────────────────────────────────────

def _mk(email, role="client", **cols):
    keys = ["name", "email", "password", "role", "active",
            "onboarded_at"] + list(cols)
    vals = [email.split("@")[0], email, generate_password_hash("pw123456"),
            role, 1, datetime.now()] + list(cols.values())
    A.db_run("INSERT INTO users (%s) VALUES (%s)"
             % (",".join(keys), ",".join("?" * len(keys))), tuple(vals))
    return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]


ADMIN = _mk("boss@e.test", "admin", is_admin=1)
HEALTHY = _mk("healthy@e.test")
SICK = _mk("sick@e.test")


def _as(uid=None, lang="ar"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["lang"] = lang
        if uid:
            s["uid"] = uid
    return c


def _plan_for(uid, **data):
    A.db_run("DELETE FROM plan_requests WHERE client_id=?", (uid,))
    week = [{"day": "الاحد", "lunch": "صدر دجاج مشوي 150جم + ارز بني 140جم"}]
    A.db_run("INSERT INTO plan_requests (client_id, client_name, status, "
             "request_data, plan_data) VALUES (?,?,?,?,?)",
             (uid, "x", "approved", "{}",
              json.dumps({"data": data, "plan": week}, ensure_ascii=False)))


def _ask(c, item):
    return c.get("/api/alternatives", query_string={"item": item})


def test_the_api_answers_with_the_askers_own_conditions():
    _plan_for(HEALTHY)
    _plan_for(SICK, symptoms=[DIABETES, PRESSURE])
    free = _ask(_as(HEALTHY), "خبز اسمر 100جم").get_json()
    sick = _ask(_as(SICK), "خبز اسمر 100جم").get_json()
    assert free["ok"] and free["readable"] and free["options"], free
    for o in sick["options"]:
        food = _food(o["name"])
        need = {"dm", "htn"} if _flag_required(food, "سكري") else {"htn"}
        assert need <= set(food["safe"]), o
    assert [o["name"] for o in sick["options"]] != [o["name"] for o in free["options"]], \
        "the sick client was answered as if healthy"
    assert "توست أبيض" in [o["name"] for o in free["options"]]
    assert "توست أبيض" not in [o["name"] for o in sick["options"]]


def test_a_condition_on_the_account_counts_even_when_the_plan_has_none():
    """‏الحالة ممكن تكون مسجّلة في بيانات الخطة أو في حساب العميل (استبيان
    التسجيل). واحدة منهم كفاية -- لو اتاخدت الخطة بس، عميل كتب في
    الاستبيان إنه مريض كلى وخطته اتعملت من غير الحالة ياخد بدائل مش ليه."""
    uid = _mk("kidney@e.test", conditions=json.dumps([KIDNEY], ensure_ascii=False))
    _plan_for(uid)                               # the plan knows nothing
    user = A.get_user_by_id(uid)
    import client_app
    assert "كلوي" in client_app.swap_profile(user)["conditions"]
    got = _ask(_as(uid), "خبز اسمر 100جم").get_json()
    assert got["options"], got
    for o in got["options"]:
        assert "ckd" in _food(o["name"])["safe"], o
    fruit = _ask(_as(uid), "تفاح 230جم").get_json()["options"]
    for o in fruit:
        assert "ckd" in _food(o["name"])["safe"], o
    assert "موز" not in " ".join(o["name"] for o in fruit)
    # ‏والعكس: الحالة في الخطة بس
    uid2 = _mk("kidney2@e.test")
    _plan_for(uid2, symptoms=[KIDNEY])
    assert "كلوي" in client_app.swap_profile(A.get_user_by_id(uid2))["conditions"]


def test_an_allergy_on_the_account_reaches_the_swaps():
    uid = _mk("fish@e.test", allergies=json.dumps(["الأسماك"], ensure_ascii=False))
    _plan_for(uid)
    got = _ask(_as(uid), "صدر دجاج مشوي 150جم").get_json()
    assert got["options"], got
    assert all(_food(o["name"])["cat"] != "fish" for o in got["options"])


def test_the_api_is_for_signed_in_clients_only():
    assert _ask(_as(), "تفاح 230جم").status_code == 302
    assert _ask(_as(ADMIN), "تفاح 230جم").status_code == 403
    assert _ask(_as(HEALTHY), "").status_code == 400


def test_the_nutritionist_can_turn_swaps_off_for_one_client():
    _plan_for(HEALTHY)
    c = _as(HEALTHY)
    assert _ask(c, "تفاح 230جم").get_json()["options"]
    assert 'id="swapBox"' in c.get("/my-plan").get_data(as_text=True)
    _as(ADMIN).post("/admin/users/%d/recommendations" % HEALTHY,
                    data={"action": "swaps", "allow": "0"})
    assert _ask(c, "تفاح 230جم").get_json() == {"ok": False, "reason": "off"}
    assert 'id="swapBox"' not in c.get("/my-plan").get_data(as_text=True)
    # ‏العميل مايقدرش يرجّعها لنفسه
    c.post("/admin/users/%d/recommendations" % HEALTHY,
           data={"action": "swaps", "allow": "1"})
    assert _ask(c, "تفاح 230جم").get_json()["ok"] is False
    _as(ADMIN).post("/admin/users/%d/recommendations" % HEALTHY,
                    data={"action": "swaps", "allow": "1"})
    assert _ask(c, "تفاح 230جم").get_json()["ok"] is True


def test_an_unreadable_item_says_so_instead_of_guessing():
    got = _ask(_as(HEALTHY), "سلطة").get_json()
    assert got == {"ok": True, "readable": False, "options": []}, got


def test_the_plan_page_marks_each_meal_with_its_stored_text():
    """‏data-swap لازم يشيل العربي المخزّن حتى والصفحة إنجليزي: المطابقة
    وفحص الممنوعات ماشيين على العربي."""
    _plan_for(HEALTHY)
    pid = A.db_row("SELECT id FROM plan_requests WHERE client_id=?", (HEALTHY,))["id"]
    for lang in ("ar", "en"):
        page = _as(HEALTHY, lang).get("/my-plans-history/%d" % pid).get_data(as_text=True)
        assert 'data-swap="صدر دجاج مشوي 150جم + ارز بني 140جم"' in page, lang
        assert 'id="swapBox"' in page


def test_english_swaps_carry_english_names():
    got = E.alternatives("تفاح 230جم", E.profile_from({}), ar=False)
    assert got["options"]
    with_units = E.alternatives("بيض مسلوق 3", E.profile_from({}), ar=False)
    for o in got["options"] + with_units["options"]:
        assert not E._ARABIC.search(o["name"]), o
        assert not E._ARABIC.search(o["amount"]), o


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
        except Exception as e:
            print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

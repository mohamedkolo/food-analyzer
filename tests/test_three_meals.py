# -*- coding: utf-8 -*-
"""‏تلات وجبات والعشا نصّه، والعدد اللي كان بيكبر لحد السخافة.

‏الحالة اللي النظام ده اتعمل عشانها حالة حقيقية في العيادة: عميلة
**بتاكل وجبة واحدة في اليوم** ومحتاجة تزوّد وزنها. أقرب نظام كان
موجود "تقليدي" (أربع خانات بسناك) أو "وجبتين" (من غير عشا خالص) --
ومفيش حاجة بينهم.

‏والعشا الكامل في أول أسبوع مش هيتاكل. يتكتب على الورق ومايتاكلش
معناه إن الورقة مالهاش علاقة باليوم الحقيقي، والعميلة بتوصل لآخر
الأسبوع وهي فاكرة إنها فشلت وهي أصلاً ماخدتش خطة تنفّذ.

‏وطلع كمان وإحنا بنعملها إن تكبير الحصص مالوش سقف على **العدد**:
نفس المعامل اللي بيحوّل ٢٠٠جم أرز لـ٣٠٠جم (أرز برضه) بيحوّل "بيض
مسلوق ٣" لـ**"بيض مسلوق ٧"** -- ودي مش حصة أكبر، دي حاجة تانية خالص.

Run with:  python3 tests/test_three_meals.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_three_meals_test.db"

import app as A              # noqa: E402
import meal_macros           # noqa: E402
import plan_engine           # noqa: E402
import portion_scale         # noqa: E402
import zigzag                # noqa: E402
from meal_database import DIET_PLAN_TYPES, get_diet_plan_info  # noqa: E402


def _plan(**over):
    data = {"name": "ع", "gender": "انثى", "age": "16", "culture": "مصري",
            "height": "160", "weight": "52.1", "tdee": "1903",
            "goal_cal": "2200", "goal_type": "muscle_gain",
            "diet_plan_type": "three_meals", "activity_level": "light",
            "protein_per_kg": "1.3", "fat_pct_cal": "30",
            "allergies": [], "symptoms": [], "zigzag_mode": "off"}
    data.update(over)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        return data, plan_engine.generate_weekly_plan(data)


# ── النظام نفسه ──────────────────────────────────────────────────────

def test_the_plan_type_exists_between_standard_and_two_meals():
    """‏كان فيه أربع وجبات أو وجبتين، ومفيش تلاتة."""
    assert "three_meals" in DIET_PLAN_TYPES
    info = get_diet_plan_info("three_meals")
    assert info["meals"] == ["breakfast", "lunch", "dinner"], info["meals"]


def test_there_is_no_snack_slot():
    """‏اللي بياكل وجبة واحدة في اليوم مش هياكل سناك. لو الخانة اتكتبت
    الورقة بتبقى خمس حاجات بدل تلاتة."""
    _, plan = _plan()
    for day in plan:
        assert not day.get("snack"), day
        assert not day.get("snack1"), day


def test_the_dinner_is_named_a_light_one():
    info = get_diet_plan_info("three_meals")
    assert "خفيف" in info["meal_labels"]["dinner"], info["meal_labels"]
    assert "Light" in info["meal_labels_en"]["dinner"], info["meal_labels_en"]


def _calc_days():
    """Generated days across goals and weights. Returns (all_days, fully_calculable_days). A day is
    fully calculable only when every meal is complete under the default settings (cooked-weight rule on)."""
    import random
    days, ok = [], []
    for goal in ("1500", "1800", "2200", "2600", "3000"):
        for weight in ("52.1", "65", "80"):
            random.seed("%s-%s" % (goal, weight))
            _, plan = _plan(goal_cal=goal, weight=weight)
            for day in plan:
                days.append(day)
                ms = [meal_macros.macros(day[s]) for s in ("breakfast", "lunch", "dinner")]
                if all(m["complete"] for m in ms):
                    ok.append((day, ms))
    return days, ok


def test_the_dinner_really_is_the_small_meal():
    """The target invariant, unchanged: on a fully calculated day the dinner is at most 30% of the day's
    calories. Measured on every fully calculable generated day (several goals and weights)."""
    days, ok = _calc_days()
    assert len(ok) >= 3, "too few calculable days to say anything: %d of %d" % (len(ok), len(days))
    big = [d["day"] for d, ms in ok if sum(m["cal"] for m in ms) and ms[2]["cal"] > sum(m["cal"] for m in ms) * 0.30]
    assert not big, "‏العشا مش خفيف في %d يوم: %s" % (len(big), big)


def test_the_dinner_scaling_halves_an_explicit_calculable_dinner():
    """Explicit fixture for the mechanism: a fully calculable dinner is scaled by DINNER_HALF before it is placed."""
    text = "🥚 بيضة كاملة 2 + 🥗 طماطم 150جم"
    full = meal_macros.macros(text)
    assert full["complete"] and full["cal"] > 0, full
    scaled, eff = portion_scale.scale_meal(text, plan_engine.DINNER_HALF)
    half = meal_macros.macros(scaled)
    assert half["complete"] and half["cal"] <= full["cal"] * 0.65, (full["cal"], half["cal"], scaled)


def test_days_that_are_not_fully_calculable_are_counted_not_tested_for_dinner_share():
    """Separate on purpose: the generated week still has incomplete days (library meals with no stated
    preparation). They are labelled as estimates and are NOT claimed to pass the dinner-share rule."""
    days, ok = _calc_days()
    incomplete = [d for d in days if d not in [x for x, _ in ok]]
    assert incomplete, "expected incomplete days under the default rule"
    for d in incomplete[:20]:
        assert (d.get("calc") or {}).get("basis") == "label", d.get("calc")
    print("        calculable %d of %d generated days; incomplete %d" % (len(ok), len(days), len(incomplete)))


def test_the_dinner_share_is_a_named_number_not_a_magic_one():
    assert 0.4 <= plan_engine.DINNER_HALF <= 0.7, plan_engine.DINNER_HALF


def test_the_week_lands_on_the_target():
    """‏النظام بيشيل خانة، والخانات الباقية لازم تاخد نصيبها -- وإلا
    العميلة اللي عايزة تزوّد وزنها تاخد سعرات أقل من حرقها."""
    data, plan = _plan()
    avg = sum(d["total_cal"] for d in plan) / float(len(plan))
    goal = float(data["goal_cal"])
    assert abs(avg - goal) < goal * 0.05, "‏متوسط %d والهدف %d" % (avg, goal)


# ── سقف العدد ────────────────────────────────────────────────────────

def _count_of(text, word):
    """‏الكلمة ككلمة: "أرز أبيض" جواها "بيض"."""
    rx = re.compile(r"(^|\s)" + re.escape(word) + r"(\s|$|[،,.)])")
    for seg in text.split(" + "):
        if rx.search(seg):
            m = re.search(r"(?<![\d.])(\d+)(?![\d.])", seg)
            if m:
                return int(m.group(1))
    return None


def test_a_big_factor_does_not_turn_three_eggs_into_seven():
    """‏سبع بيضات في وجبة واحدة حوالي ١٣٠٠ مجم كوليسترول، ومحدش
    بياكلها. ده كان على ورقة بنت عندها ١٦ سنة."""
    out, _ = portion_scale.scale_meal("🥚 بيض مسلوق 3 + 🥗 سلطة 150جم", 2.5)
    assert _count_of(out, "بيض") <= 4, out


def test_the_ceiling_works_inside_brackets_too():
    """‏"عجة بالجزر (٣ بيض)" نفس الحكاية، والعدد جوه قوسين."""
    out, _ = portion_scale.scale_meal("🥚 عجة بالجزر (3 بيض)", 3.0)
    assert _count_of(out, "بيض") <= 4, out


def test_grams_are_not_capped_because_grams_stay_food():
    """‏٢٠٠جم أرز بتبقى ٣٠٠جم وتفضل أرز. السقف للعدد بس."""
    out, _ = portion_scale.scale_meal("🍚 ارز 150جم", 2.0)
    assert "300جم" in out, out


def test_the_ceiling_never_shrinks_what_the_table_wrote():
    """‏لو وجبة في القاعدة أصلاً فوق السقف، ده اختيار اتكتب -- إحنا
    بنمنع التكبير مش بنعدّل على الوجبة."""
    out, _ = portion_scale.scale_meal("🥚 بيض مسلوق 6 + 🥗 سلطة 150جم", 1.2)
    assert _count_of(out, "بيض") >= 6, out


def test_no_day_in_the_week_prints_an_unreal_egg_count():
    for goal in ("muscle_gain", "maintenance", "bulking", "weight_loss"):
        _, plan = _plan(goal_type=goal)
        for day in plan:
            for slot in ("breakfast", "lunch", "dinner"):
                n = _count_of(day.get(slot) or "", "بيض")
                assert n is None or n <= 6, "%s: %s" % (goal, day[slot])


# ── وزن الوحدة ───────────────────────────────────────────────────────

def test_the_unit_weight_comes_from_the_food_that_was_identified():
    """‏كان أي اسم في جدول المكاييل يظهر في النص بياخد وزنه، حتى لو
    الصنف المتعرّف صنف تاني. "رقاق أرز 6" الصنف فيها **رقاق** (٣٠جم
    للرقاقة)، بس "أرز" في جدول المكاييل بـ١٥٠جم -- فستة رقاقات طلعت
    ٩٠٠جم في قايمة المشتريات. كيلو رقاق لبنت بتفطر."""
    text = "🫓 رقاق أرز 6"
    food = meal_macros.find_food(text)
    assert food and food["n"] == "رقاق", food
    grams, how = meal_macros.item_grams(text, food)
    assert how == "count", how
    assert grams <= 250, grams


def test_a_plain_liver_or_kofta_is_known_to_the_food_table():
    """‏الجدول فيه "كبدة بقري" و"كفتة مشوية"، وأسماء الجدول بتتلاقى لما
    تكون **جوّه** نص الصنف -- والقاعدة بتكتب "كبدة 200جم" كده. فالصنفين
    كانوا بصفر سعرة وفي "مش متعرّف" في قايمة المشتريات."""
    # "كبدة" matches the beef-liver row, whose name states no preparation: it is KNOWN to the table but
    # withheld by the cooked-weight rule (basis reason), not priced. Kofta is priced.
    liver = meal_macros.macros("🍗 كبدة 200جم")["items"][0]
    assert liver["food"] == "كبدة بقري" and str(liver["unresolved"]).startswith("basis:"), liver
    for text in ("🥩 كفتة 240جم",):
        mac = meal_macros.macros(text)
        assert mac["covered"] >= 0.99, "%s: تغطية %.0f%%" % (
            text, mac["covered"] * 100)
        assert mac["cal"] > 0, text


def test_a_named_cut_still_beats_the_generic_one():
    """‏الخريطة العامة مالهاش حق تسحب صنف الجدول المحدد."""
    assert meal_macros.find_food("🍗 كبدة دجاج 150جم")["n"] == "كبدة دجاج"


# ── المياه ───────────────────────────────────────────────────────────

def test_the_client_water_number_shows_inside_the_allowed_list():
    """‏صندوق الماء اتشال من الورقة بطلب الدكتور. فلما الرقم رجع
    لعميلة معيّنة، رجع **جوه المسموح** -- الورقة زي ما هي والرقم وصل."""
    data, plan = _plan(water_l=1.8)
    with A.app.test_request_context("/"):
        html = plan_engine.plan_html(data, plan)
    assert "مياه 1.8 لتر" in html, "‏رقم المياه مش في الورقة"


def test_no_water_number_means_no_water_line():
    """‏مش كل عميل معاه ورقة تحليل. من غير رقم مابنخترعش واحد."""
    data, plan = _plan()
    with A.app.test_request_context("/"):
        html = plan_engine.plan_html(data, plan)
    assert "لتر يومياً" not in html, "‏سطر مياه اتكتب من غير رقم"


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
            print(f"  FAIL  {name}\n        {str(e)[:400]}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

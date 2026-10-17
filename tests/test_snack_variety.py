# -*- coding: utf-8 -*-
"""‏السناك: عدد كفاية، بجرامات، وسعرات محسوبة من الأكل.

‏الأسبوع فيه ١٤ خانة سناك (سناكين × سبع أيام) والسناك كان ١٠ أصناف،
فالتكرار كان حتمي -- تنويع العميل الراجع وقف على ٣٣٪.

‏وطلع إن المحتوى مش السبب الوحيد: الكود كان بيقص السناك على ١٠
(`pool_snacks[:10]`)، يعني جداول الأطفال فيها ٢٤ و١٠ بس بيوصلوا.
فزيادة المحتوى لوحدها ماكانتش هتعمل حاجة.

‏والسناكات كانت مكتوبة **من غير جرامات** ("حمص + خبز + زيتون"). ده
بيعمل تلات حاجات: العميل مايعرفش ياكل قد إيه، وقايمة المشتريات
مابتعرفش تجمعه، والسعرات المكتوبة مينفعش تتراجع على الأكل.

Run with:  python3 tests/test_snack_variety.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_snack_test.db"

import app as A            # noqa: E402
import child_meals         # noqa: E402
import meal_macros         # noqa: E402
import plan_engine         # noqa: E402
import zigzag              # noqa: E402
from meal_database import get_snacks_for_goal  # noqa: E402

GOALS = ("weight_loss", "muscle_gain", "bulking", "maintenance")

# ‏الأسبوع: سناكين × سبع أيام
WEEKLY_SLOTS = 14


def _text(s):
    return s if isinstance(s, str) else (s or {}).get("meal", "")


def _said_kcal(s):
    m = re.search(r"(\d+)\s*(?:kcal|سعرة)", _text(s))
    return int(m.group(1)) if m else None


def _body(s):
    """‏نص السناك من غير ذيل السعرات."""
    return re.sub(r"[-(]\s*\d+\s*(?:kcal|سعرة)\s*\)?", "", _text(s)).strip()


# ── العدد ────────────────────────────────────────────────────────────

def test_every_goal_has_more_snacks_than_the_week_has_slots():
    """‏أقل من ١٤ معناه تكرار حتمي مهما كان الكود."""
    for goal in GOALS:
        rows = get_snacks_for_goal(goal)
        assert len(rows) > WEEKLY_SLOTS, "‏%s فيه %d سناك بس" % (goal, len(rows))


def test_the_child_pool_has_more_snacks_than_the_week_has_slots():
    for culture in ("مصري", "خليجي"):
        pool = child_meals.pool_for("10", culture)
        assert len(pool["snack"]) > WEEKLY_SLOTS, (
            "‏%s: %d سناك" % (culture, len(pool["snack"])))


def test_the_engine_does_not_throw_the_extra_snacks_away():
    """‏كان `pool_snacks[:10]`: أي زيادة في المحتوى بتتقص قبل ما توصل."""
    import inspect
    src = inspect.getsource(plan_engine.generate_weekly_plan)
    assert "pool_snacks[:10]" not in src, "‏القص رجع"


# ── الجرامات والسعرات ───────────────────────────────────────────────

def test_every_snack_says_how_much():
    """‏"حمص + خبز + زيتون" مش حصة -- دي أسماء."""
    for goal in GOALS:
        for s in get_snacks_for_goal(goal):
            body = _body(s)
            assert re.search(r"\d", body), "‏%s: سناك من غير كمية: %s" % (goal, s)


def test_every_snack_prints_its_calories():
    for goal in GOALS:
        for s in get_snacks_for_goal(goal):
            assert _said_kcal(s), "‏%s: سناك من غير سعرات: %s" % (goal, s)


def test_the_printed_calories_match_the_food():
    """‏السعرات محسوبة من جدول الأكل مش مكتوبة بالإيد. لو سطر اتزوّد
    بالإيد بعدين، ده بيمسكه."""
    off = []
    for goal in GOALS:
        for s in get_snacks_for_goal(goal):
            said = _said_kcal(s)
            mac = meal_macros.macros(_body(s))
            if mac["covered"] < 0.99 or not said:
                continue
            if abs(mac["cal"] - said) > max(12, said * 0.10):
                off.append("%s: مكتوب %d محسوب %d" % (s[:40], said, mac["cal"]))
    assert not off, "\n   ".join(off)


def test_every_ingredient_is_known_to_the_food_table():
    """‏صنف مش في الجدول = صفر سعرة في الحساب، و"مش متعرّف" في قايمة
    المشتريات. مافيش داعي نضيف سناك بالعيب ده."""
    bad = []
    for goal in GOALS:
        for s in get_snacks_for_goal(goal):
            mac = meal_macros.macros(_body(s))
            if mac["covered"] < 0.99:
                bad.append("%s (تغطية %.0f%%)" % (s[:42], mac["covered"] * 100))
    assert not bad, "\n   ".join(bad)


def test_the_child_snacks_carry_grams_and_calories():
    pool = child_meals.pool_for("10", "مصري")
    for s in pool["snack"]:
        text = _text(s)
        assert re.search(r"\d", text), text
        assert _said_kcal(s), text


# ── التنويع ─────────────────────────────────────────────────────────

def _plan(avoid=None, **over):
    data = {"name": "ع", "gender": "انثى", "culture": "مصري",
            "diet_plan_type": "standard", "fat_pct_cal": "30",
            "allergies": [], "activity_level": "light", "symptoms": [],
            "zigzag_mode": "classic", "protein_per_kg": "1.6",
            "age": "34", "weight": "88", "height": "160", "tdee": "2100",
            "goal_cal": "1600", "goal_type": "weight_loss"}
    data.update(over)
    if avoid:
        data["avoid_meals"] = avoid
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        return plan_engine.generate_weekly_plan(data)


def test_a_week_does_not_repeat_the_same_snack():
    """‏سبع خانات سناك في الأسبوع، وكلهم مختلفين."""
    plan = _plan()
    keys = [plan_engine._dish_key(d.get("snack")) for d in plan if d.get("snack")]
    assert len(keys) >= 7, keys
    assert len(set(keys)) == len(keys), "‏سناك اتكرر في نفس الأسبوع: %s" % keys


def test_a_returning_client_gets_mostly_new_snacks():
    """‏التنويع للعميل الراجع. كان ٣٣٪ تكرار."""
    import followup
    first = _plan()
    prev = followup.meals_in_plan(first)
    cur = [d.get("snack") for d in _plan(avoid=prev) if d.get("snack")]
    seen = {plan_engine._dish_key(x) for x in prev}
    rep = sum(1 for x in cur if plan_engine._dish_key(x) in seen)
    assert rep <= len(cur) * 0.30, "‏%d من %d سناك اتكرروا" % (rep, len(cur))


# ── الحالات ─────────────────────────────────────────────────────────

def test_no_single_condition_empties_the_snack_slot():
    """‏لو كل السناكات من مجموعة واحدة، حالة واحدة بتقفلها كلها."""
    from meal_database import filter_by_conditions
    for cond in ("حساسية اللاكتوز", "السيلياك", "G6PD", "تليف الكبد",
                 "النقرس", "حساسية المكسرات", "السكري النوع الثاني"):
        kept = filter_by_conditions(get_snacks_for_goal("weight_loss"), [cond])
        assert len(kept) >= WEEKLY_SLOTS, "‏%s سابت %d سناك" % (cond, len(kept))


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

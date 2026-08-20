# -*- coding: utf-8 -*-
"""The safety filtering is the part of this product that can hurt someone.

Run with:  python3 -m pytest tests/ -q      (or just: python3 tests/test_medical_filtering.py)

These lock in three fixes:

MED-1  A meal blocked by one condition used to be swapped for an alternative
       taken from the patient's FIRST condition, not the one that blocked it,
       and nothing checked the replacement against the patient's other
       conditions. 32 of the 102 two-condition combinations produced a replacement that
       was unsafe -- a celiac patient handed wheat bread, a diabetic handed
       white rice.

MED-2  Bans are matched as Arabic substrings, so "ارز ابيض" was caught and
       "أرز أبيض" was not. No meal in the database was spelled the escaping
       way, so nothing was harmed yet -- but the next meal someone typed with
       a hamza would have walked past a diabetic's ban silently.

MED-3  Eight of the 23 conditions the plan forms offer changed nothing at
       all -- no filtering, no guidance. Ticking them was decorative.
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meal_database as md  # noqa: E402

# the conditions the plan forms actually offer, and how they map to ban lists
FORM_CONDITIONS = [
    "قولون عصبي", "سكري النوع الثاني", "سكري النوع الاول", "ضغط الدم المرتفع",
    "امراض القلب", "الفشل الكلوي المزمن", "الحمل", "الرضاعة الطبيعية", "G6PD",
    "ثلاسيميا", "حساسية اللاكتوز", "الداء الزلاقي", "الكبد الدهني",
    "حصوات المرارة", "التهاب الأمعاء",
]
CONDITION_KEYS = {
    "قولون عصبي": "قولون", "سكري النوع الثاني": "سكري", "سكري النوع الاول": "سكري",
    "ضغط الدم المرتفع": "ضغط", "امراض القلب": "قلب", "الفشل الكلوي المزمن": "كلوي",
    "الحمل": "حامل", "الرضاعة الطبيعية": "حامل", "G6PD": "g6pd",
    "ثلاسيميا": "ثلاسيميا", "حساسية اللاكتوز": "لاكتوز", "الداء الزلاقي": "جلوتين",
    "الكبد الدهني": "دهني", "حصوات المرارة": "مرارة", "التهاب الأمعاء": "قولون",
}


def keys_for(conditions):
    out = []
    for c in conditions:
        k = CONDITION_KEYS.get(c)
        if k and k not in out:
            out.append(k)
    return out


def every_meal():
    pool = []
    for base in (md.WEIGHT_LOSS, md.MUSCLE_GAIN, md.BULKING, md.MAINTENANCE):
        for culture in base.values():
            for slot in culture.values():
                pool.extend(slot)
    return pool


def _unsafe_in(meals, condition_keys):
    """Every (meal, condition) pair that should not have survived filtering."""
    bad = []
    for m in meals:
        text = md._meal_text(m)
        for k in condition_keys:
            if md._contains_unsafe(text, k):
                bad.append((text, k))
                break
    return bad


# ── MED-1 ────────────────────────────────────────────────────────────────────

def test_no_unsafe_meal_survives_any_two_conditions():
    pool = every_meal()
    failures = []
    for combo in itertools.combinations(FORM_CONDITIONS, 2):
        ks = keys_for(combo)
        if len(ks) < 2:
            continue
        bad = _unsafe_in(md.filter_by_conditions(list(pool), list(combo)), ks)
        if bad:
            failures.append((combo, bad[0]))
    assert not failures, f"{len(failures)} combinations still serve unsafe food: {failures[:3]}"


def test_no_unsafe_meal_survives_any_three_conditions():
    pool = every_meal()
    failures = []
    for combo in itertools.combinations(FORM_CONDITIONS, 3):
        ks = keys_for(combo)
        if len(ks) < 2:
            continue
        bad = _unsafe_in(md.filter_by_conditions(list(pool), list(combo)), ks)
        if bad:
            failures.append((combo, bad[0]))
    assert not failures, f"{len(failures)} combinations still serve unsafe food: {failures[:3]}"


def test_replacement_comes_from_the_blocking_condition():
    """A celiac diabetic must not be handed wheat bread as the 'safe' swap."""
    conds = ["الداء الزلاقي", "سكري النوع الثاني"]
    ks = keys_for(conds)
    out = md.filter_by_conditions(every_meal(), conds)
    assert out, "filtering emptied the pool"
    assert not _unsafe_in(out, ks)


def test_filtering_never_empties_the_pool():
    """Callers do `filter_by_conditions(...) or meals`, so an empty result
    silently falls back to the unfiltered list. It must never come back empty."""
    pool = every_meal()
    for combo in itertools.combinations(FORM_CONDITIONS, 2):
        if len(keys_for(combo)) < 2:
            continue
        assert md.filter_by_conditions(list(pool), list(combo)), \
            f"empty pool for {combo} would fall back to unfiltered meals"


def test_string_meals_do_not_break_filtering():
    """Some pools hold plain strings. These used to raise, and every caller
    catches the error and falls back to the unfiltered list."""
    meals = ["🍚 ارز ابيض 150جم + 🍗 دجاج", {"meal": "🥗 سلطة خضراء", "cal": 100, "p": 3}]
    out = md.filter_by_conditions(meals, ["سكري النوع الثاني"])
    assert out
    assert not _unsafe_in(out, ["سكري"])


# ── MED-2 ────────────────────────────────────────────────────────────────────

def test_hamza_spelling_does_not_dodge_a_ban():
    for text in ("🍚 ارز ابيض 150جم", "🍚 أرز أبيض 150جم",
                 "🍚 أرز ابيض 150جم", "🍚 ارز أبيض 150جم"):
        assert md._contains_unsafe(text, "سكري"), f"white rice slipped past: {text}"


def test_normalize_folds_the_variants_together():
    assert md.normalize_ar("أرز") == md.normalize_ar("ارز") == md.normalize_ar("إرز")
    assert md.normalize_ar("مخبوزة") == md.normalize_ar("مخبوزه")


def test_safe_food_is_not_banned_by_normalisation():
    """Folding must not make unrelated foods collide."""
    assert not md._contains_unsafe("🥗 سلطة خضراء + 🥒 خيار", "سكري")
    assert not md._contains_unsafe("🍗 صدر دجاج مشوي 150جم", "سكري")


# ── MED-3 ────────────────────────────────────────────────────────────────────
# Every condition the plan forms offer has to change something the patient can
# see. Eight of them filtered nothing and carried no guidance, so ticking them
# was purely decorative.

FORM_CONDITIONS_ALL = FORM_CONDITIONS + [
    "السمنة", "نقص الحديد", "نقص فيتامين D3", "حرق بطيء", "امساك مزمن",
    "اضطراب في الأكل", "هشاشة العظام", "الوقاية من السرطان",
]


def test_every_offered_condition_does_something():
    """Either it filters meals, or it contributes a guidance note."""
    silent = []
    for c in FORM_CONDITIONS_ALL:
        filters = c in CONDITION_KEYS
        guides = bool(md.get_nutrient_boost_notes([c]))
        if not filters and not guides:
            silent.append(c)
    assert not silent, f"these conditions change nothing at all: {silent}"


def test_guidance_notes_are_bilingual():
    for c, pair in md.NUTRIENT_BOOST_NOTES.items():
        assert isinstance(pair, tuple) and len(pair) == 2, f"{c} is not bilingual"
        ar, en = pair
        assert ar.strip() and en.strip(), f"{c} has an empty side"
        assert md.translate_boost_note(ar) == en, f"{c} does not map back to English"


def test_free_text_notes_pass_through_untouched():
    assert md.translate_boost_note("ملاحظة من الدكتور") == "ملاحظة من الدكتور"


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

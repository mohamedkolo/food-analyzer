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
# Read from the source rather than kept as a second copy here -- a copy is
# what lets a condition be offered in the form while quietly filtering nothing.
CONDITION_KEYS = md.CONDITION_MAP


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
    "حرقة المعدة (GERD)",
]


def _conditions_in_the_form():
    """The condition labels generate.html actually renders checkboxes for."""
    import os
    import re
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html = open(os.path.join(here, "templates", "generate.html"),
                encoding="utf-8").read()
    start = html.index("<i class=\"fa-solid fa-stethoscope\"></i>")
    block = html[start:html.index("{% endfor %}", start)]
    # only the Arabic side is matched: an English label can carry an escaped
    # quote ("IBD (Crohn\'s/Colitis)"), which a pattern for both sides trips on
    found = re.findall(r"\('([^']+)'\s*,", block)
    assert found, "could not read the condition list out of generate.html"
    return found


def test_the_form_and_this_file_list_the_same_conditions():
    # FORM_CONDITIONS_ALL is maintained by hand, so it can drift from the form
    # -- and a condition missing from it is a condition nothing below checks
    in_form = set(_conditions_in_the_form())
    listed = set(FORM_CONDITIONS_ALL)
    assert in_form == listed, (
        f"in the form but not checked here: {sorted(in_form - listed)}; "
        f"checked here but not in the form: {sorted(listed - in_form)}")


def test_every_offered_condition_does_something():
    """Either it filters meals, or it contributes a guidance note."""
    silent = []
    for c in FORM_CONDITIONS_ALL:
        filters = c in CONDITION_KEYS
        guides = bool(md.get_nutrient_boost_notes([c]))
        if not filters and not guides:
            silent.append(c)
    assert not silent, f"these conditions change nothing at all: {silent}"


def test_reflux_removes_every_trigger_the_document_lists():
    # reflux is the first condition that both filters and advises, and the
    # trigger list is long enough to strip a pool bare if it were careless --
    # an emptied pool makes filter_by_conditions hand back the UNFILTERED list
    GERD = "حرقة المعدة (GERD)"
    triggers = md.UNSAFE_FOODS["ارتجاع"]
    combos = [[GERD], [GERD, "الفشل الكلوي المزمن"], [GERD, "قولون عصبي"],
              [GERD, "سكري النوع الثاني", "ضغط الدم المرتفع"]]
    for culture in ("مصري", "خليجي", "شامي"):
        pool = md.get_meal_pool("weight_loss", culture)
        for symptoms in combos:
            for slot in ("breakfast", "lunch", "dinner"):
                before = list(pool.get(slot, []))
                after = md.filter_by_conditions(before, symptoms)
                assert after, f"{culture}/{slot}/{symptoms}: the pool came back empty"
                assert len(after) == len(before), (
                    f"{culture}/{slot}: {len(before)} meals became {len(after)}")
                for meal in after:
                    text = md.normalize_ar(
                        meal["meal"] if isinstance(meal, dict) else meal)
                    hit = [t for t in triggers if md.normalize_ar(t) in text]
                    assert not hit, f"{culture}/{slot}: {text[:50]!r} still has {hit}"


def test_reflux_both_filters_and_advises():
    # the bans cannot say "smaller meals" or "do not lie down after eating"
    GERD = "حرقة المعدة (GERD)"
    assert md.unsafe_keys_for([GERD]) == ["ارتجاع"], "reflux does not resolve to a ban list"
    assert md.get_nutrient_boost_notes([GERD]), "reflux contributes no guidance note"


def test_what_reflux_swaps_in_is_itself_reflux_safe():
    triggers = md.UNSAFE_FOODS["ارتجاع"]
    alts = md.SAFE_ALTERNATIVES.get("ارتجاع")
    assert alts, "reflux has nothing to swap in"
    for alt in alts:
        text = md.normalize_ar(alt["meal"])
        hit = [t for t in triggers if md.normalize_ar(t) in text]
        assert not hit, f"the replacement {alt['meal']!r} carries {hit}"


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

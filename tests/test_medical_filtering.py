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
    "حرقة المعدة (GERD)", "تكيس المبايض (PCOS/PMOS)",
    "مضادات تخثر الدم (وارفارين)", "جرثومة المعدة (H. pylori)",
    "فرط نمو بكتيريا الأمعاء (SIBO)", "الإسهال",
    "الصدفية", "الذئبة الحمراء", "التهاب المفاصل الروماتويدي",
    "بعد استئصال المرارة", "بعد عمليات التكميم",
    "بطانة الرحم المهاجرة", "انقطاع النفس النومي", "الربو",
    "الوذمة الشحمية", "التصلب اللويحي المتعدد", "متلازمة شوغرن",
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


def test_pcos_never_empties_a_slot_in_any_cuisine():
    # the document's full list -- dairy-free AND gluten-free on top of these --
    # strips 69% of the database and empties five slots outright, and an
    # emptied slot makes filter_by_conditions hand back the UNFILTERED list.
    # So only the affordable half is banned here, and that has to stay true as
    # meals are added.
    PCOS = "تكيس المبايض (PCOS/PMOS)"
    triggers = md.UNSAFE_FOODS["تكيس"]
    for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
        for goal in ("weight_loss", "muscle_gain", "bulking", "maintenance"):
            pool = md.get_meal_pool(goal, culture)
            for slot in ("breakfast", "lunch", "dinner"):
                before = list(pool.get(slot, []))
                if not before:
                    continue
                survivors = [
                    m for m in before
                    if not any(md.normalize_ar(t) in md.normalize_ar(
                        m["meal"] if isinstance(m, dict) else m)
                        for t in triggers)]
                assert len(survivors) >= 3, (
                    f"{culture}/{goal}/{slot}: only {len(survivors)} of "
                    f"{len(before)} meals survive -- the week would repeat")
                after = md.filter_by_conditions(before, [PCOS])
                assert after, f"{culture}/{goal}/{slot}: the pool came back empty"
                for meal in after:
                    text = md.normalize_ar(
                        meal["meal"] if isinstance(meal, dict) else meal)
                    hit = [t for t in triggers if md.normalize_ar(t) in text]
                    assert not hit, f"{culture}/{slot}: {text[:46]!r} kept {hit}"


def test_pcos_points_at_the_conditions_that_carry_the_rest():
    # the dairy-free and gluten-free halves are real, they just cannot be
    # applied automatically -- the note has to say how to get them
    note_ar, note_en = md.NUTRIENT_BOOST_NOTES["تكيس المبايض (PCOS/PMOS)"]
    assert "حساسية اللاكتوز" in note_ar and "الداء الزلاقي" in note_ar, (
        "the note does not name the conditions that apply the rest of the protocol")
    for name in ("حساسية اللاكتوز", "الداء الزلاقي"):
        assert name in md.CONDITION_MAP, f"the note points at {name}, which is not a condition"
    assert "lactose" in note_en.lower() and "celiac" in note_en.lower(), (
        "the English note does not name them")


def test_what_pcos_swaps_in_is_itself_pcos_safe():
    triggers = md.UNSAFE_FOODS["تكيس"]
    alts = md.SAFE_ALTERNATIVES.get("تكيس")
    assert alts, "PCOS has nothing to swap in"
    for alt in alts:
        text = md.normalize_ar(alt["meal"])
        hit = [t for t in triggers if md.normalize_ar(t) in text]
        assert not hit, f"the replacement {alt['meal']!r} carries {hit}"


def test_a_growing_client_gets_the_age_guidance():
    # not a condition anyone ticks -- it fires off the client's own age, so the
    # boundaries are the whole behaviour
    from plan_engine import _apply_clinical_safety_caps  # noqa: E402

    MARK = "سن النمو"
    for age, expected in ((3, False), (4, True), (12, True), (18, True),
                          (19, False), (40, False)):
        data = {"age": str(age), "symptoms": [], "notes": ""}
        _apply_clinical_safety_caps(data)
        fired = MARK in data.get("notes", "")
        assert fired is expected, f"age {age}: guidance fired={fired}"

    # junk in the age field must not raise or fire
    for junk in ("", None, "abc", "-5"):
        data = {"age": junk, "symptoms": [], "notes": ""}
        _apply_clinical_safety_caps(data)
        assert MARK not in data.get("notes", ""), f"age {junk!r} fired the guidance"

    # and it rides along with a real condition rather than replacing it
    data = {"age": "12", "symptoms": ["نقص الحديد"], "notes": ""}
    _apply_clinical_safety_caps(data)
    assert MARK in data["notes"] and "الحديد" in data["notes"], (
        f"the two notes did not coexist: {data['notes']}")


def test_the_age_guidance_is_not_offered_as_a_condition():
    # it must not appear as a checkbox -- age already drives it
    assert "عمر 4-18" not in _conditions_in_the_form()
    assert "عمر 4-18" in md.NUTRIENT_BOOST_NOTES, "the note is gone"


def test_fatty_liver_bans_the_added_sugars_the_sheet_names():
    # honey rode along in plans for a condition whose whole point is cutting
    # fructose
    banned = md.UNSAFE_FOODS["دهني"]
    for food in ("عسل", "مربى", "كيك", "مرتديلا", "سجق"):
        assert food in banned, f"fatty liver still allows {food}"
    # and it still leaves a week's worth of variety everywhere
    for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
        for goal in ("weight_loss", "muscle_gain", "bulking", "maintenance"):
            pool = md.get_meal_pool(goal, culture)
            for slot in ("breakfast", "lunch", "dinner"):
                before = list(pool.get(slot, []))
                if not before:
                    continue
                survivors = [
                    m for m in before
                    if not any(md.normalize_ar(t) in md.normalize_ar(
                        m["meal"] if isinstance(m, dict) else m) for t in banned)]
                assert len(survivors) >= 3, (
                    f"{culture}/{goal}/{slot}: only {len(survivors)} of "
                    f"{len(before)} survive fatty-liver filtering")


def test_ticking_a_condition_promotes_its_helpful_foods():
    """Filtering is only half of it -- the plan should also lean helpful.

    The ranking machinery (_rank_by_condition over CONDITION_FOODS) already
    existed, but a condition with no entry there filtered and preferred
    nothing: the plan simply avoided the bad and picked at random from the
    rest. These three now carry a "good" side taken from their own sheets.
    """
    import os
    os.environ.setdefault("SECRET_KEY", "test-key")
    from core import app  # noqa: E402
    from flask import session  # noqa: E402
    from meal_extra import conditions_to_keys, tag_meal  # noqa: E402
    from plan_engine import generate_weekly_plan  # noqa: E402

    SLOTS = ("breakfast", "lunch", "dinner")

    def _counts(symptoms):
        data = {
            "name": "tst", "age": "30", "gender": "أنثى", "height": "165",
            "weight": "80", "tdee": "2200", "goal_cal": "1700",
            "goal_type": "weight_loss", "culture": "مصري",
            "diet_plan_type": "standard", "symptoms": symptoms,
            "allergies": [], "notes": "", "disliked_foods": "", "user_id": 1,
        }
        with app.test_request_context("/"):
            session["uid"] = 1
            plan = generate_weekly_plan(data)
        keys = conditions_to_keys(symptoms)
        assert keys, f"{symptoms} resolves to no ranking key"
        good = bad = 0
        for day in plan:
            for slot in SLOTS:
                statuses = [v for k, v in tag_meal(day.get(slot, "")).items()
                            if k in keys]
                if "bad" in statuses:
                    bad += 1
                elif "good" in statuses:
                    good += 1
        return good, bad, len(plan) * len(SLOTS)

    for label in ("حرقة المعدة (GERD)", "تكيس المبايض (PCOS/PMOS)",
                  "الكبد الدهني"):
        good, bad, total = _counts([label])
        assert bad == 0, f"{label}: {bad} of {total} meals are bad for it"
        assert good >= total * 2 // 3, (
            f"{label}: only {good} of {total} meals are helpful -- the "
            f"condition is filtering but not preferring")


def test_the_new_conditions_have_both_sides():
    from meal_extra import CONDITION_FOODS, conditions_to_keys  # noqa: E402

    for label, key in (("حرقة المعدة (GERD)", "reflux"),
                       ("تكيس المبايض (PCOS/PMOS)", "pcos")):
        assert conditions_to_keys([label]) == [key], (
            f"{label} does not resolve to {key}")
        entry = CONDITION_FOODS[key]
        assert entry["good"] and entry["bad"], f"{key} is missing a side"
        # the bans and the ranking must not contradict each other
        unsafe_key = md.CONDITION_MAP[label]
        for food in entry["good"]:
            assert not any(md.normalize_ar(b) in md.normalize_ar(food)
                           for b in md.UNSAFE_FOODS[unsafe_key]), (
                f"{key} calls {food!r} helpful while banning it")


GUT_CONDITIONS = {
    "جرثومة المعدة (H. pylori)": ("جرثومة", "hpylori"),
    "فرط نمو بكتيريا الأمعاء (SIBO)": ("سيبو", "sibo"),
    "الإسهال": ("اسهال", "diarrhea"),
}


def test_the_gut_conditions_filter_without_emptying_a_slot():
    # SIBO's dairy ban alone drops a slot to one meal and empties five when
    # combined, so it is deliberately not in UNSAFE_FOODS. These lists are the
    # measured half, and they have to stay measured as meals are added.
    from meal_extra import conditions_to_keys  # noqa: E402

    for label, (unsafe_key, rank_key) in GUT_CONDITIONS.items():
        triggers = md.UNSAFE_FOODS[unsafe_key]
        assert md.unsafe_keys_for([label]) == [unsafe_key], f"{label} does not resolve"
        assert conditions_to_keys([label]) == [rank_key], f"{label} does not rank"
        for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
            for goal in ("weight_loss", "muscle_gain", "bulking", "maintenance"):
                pool = md.get_meal_pool(goal, culture)
                for slot in ("breakfast", "lunch", "dinner"):
                    before = list(pool.get(slot, []))
                    if not before:
                        continue
                    survivors = [
                        m for m in before
                        if not any(md.normalize_ar(t) in md.normalize_ar(
                            m["meal"] if isinstance(m, dict) else m)
                            for t in triggers)]
                    assert survivors, (
                        f"{label} empties {culture}/{goal}/{slot} -- filtering would "
                        f"fall back to the unfiltered list")
                    after = md.filter_by_conditions(before, [label])
                    for meal in after:
                        text = md.normalize_ar(
                            meal["meal"] if isinstance(meal, dict) else meal)
                        hit = [t for t in triggers if md.normalize_ar(t) in text]
                        assert not hit, f"{label}: {text[:44]!r} kept {hit}"


def test_h_pylori_keeps_avoid_and_with_care_apart():
    # the sheet bans spicy and fried but only cautions against coffee, tea,
    # chocolate and citrus -- banning those would overreach
    from meal_extra import CONDITION_FOODS  # noqa: E402

    banned = md.UNSAFE_FOODS["جرثومة"]
    ranked_bad = CONDITION_FOODS["hpylori"]["bad"]
    for careful in ("قهوة", "شاي", "شوكولاتة", "برتقال", "كيوي"):
        assert careful not in banned, f"{careful} is 'with care', not banned"
        assert careful in ranked_bad, f"{careful} is neither banned nor ranked down"
    for avoid in ("حار", "مقلي", "مرتديلا", "مشروبات غازية"):
        assert avoid in banned, f"the sheet says avoid {avoid}"


def test_anticoagulants_rank_rather_than_ban():
    # the sheet asks for one portion of vitamin K food daily, not none, so an
    # outright ban would be wrong -- and would empty slots besides
    from meal_extra import CONDITION_FOODS, conditions_to_keys  # noqa: E402

    W = "مضادات تخثر الدم (وارفارين)"
    assert md.unsafe_keys_for([W]) == [], (
        "anticoagulants became an outright ban")
    assert conditions_to_keys([W]) == ["anticoag"], "anticoagulants do not rank"
    assert md.get_nutrient_boost_notes([W]), "no guidance for anticoagulants"
    bad = CONDITION_FOODS["anticoag"]["bad"]
    for food in ("سبانخ", "بروكلي", "ملفوف", "جرجير", "ثوم", "توت", "كبدة"):
        assert food in bad, f"{food} is high in vitamin K and is not ranked down"


def test_anticoagulants_beat_a_condition_that_promotes_greens():
    # fatty liver, PCOS and reflux all promote leafy greens. For a client on
    # warfarin that promotion must lose.
    import os
    os.environ.setdefault("SECRET_KEY", "test-key")
    from core import app  # noqa: E402
    from flask import session  # noqa: E402
    from meal_extra import tag_meal  # noqa: E402
    from plan_engine import generate_weekly_plan  # noqa: E402

    W = "مضادات تخثر الدم (وارفارين)"

    def _vitamin_k_meals(symptoms):
        data = {
            "name": "tst", "age": "50", "gender": "ذكر", "height": "175",
            "weight": "90", "tdee": "2400", "goal_cal": "1900",
            "goal_type": "weight_loss", "culture": "مصري",
            "diet_plan_type": "standard", "symptoms": symptoms,
            "allergies": [], "notes": "", "disliked_foods": "", "user_id": 1,
        }
        with app.test_request_context("/"):
            session["uid"] = 1
            plan = generate_weekly_plan(data)
        return sum(1 for day in plan for slot in ("breakfast", "lunch", "dinner")
                   if tag_meal(day.get(slot, "")).get("anticoag") == "bad")

    for other in ("الكبد الدهني", "تكيس المبايض (PCOS/PMOS)", "حرقة المعدة (GERD)"):
        with_warfarin = _vitamin_k_meals([other, W])
        assert with_warfarin <= 2, (
            f"{other} + warfarin still served {with_warfarin} of 21 meals high "
            f"in vitamin K")


AUTOIMMUNE = {
    "الصدفية": ("صدفية", "psoriasis"),
    "الذئبة الحمراء": ("ذئبة", "lupus"),
    "التهاب المفاصل الروماتويدي": ("روماتويد", "ra"),
    "بعد استئصال المرارة": ("بعد المرارة", "postchole"),
}


def test_the_autoimmune_batch_filters_and_prefers_without_emptying():
    from meal_extra import CONDITION_FOODS, conditions_to_keys  # noqa: E402

    for label, (unsafe_key, rank_key) in AUTOIMMUNE.items():
        assert md.unsafe_keys_for([label]) == [unsafe_key], f"{label} does not resolve"
        assert conditions_to_keys([label]) == [rank_key], f"{label} does not rank"
        assert md.get_nutrient_boost_notes([label]), f"{label} has no note"
        assert md.SAFE_ALTERNATIVES.get(unsafe_key), f"{label} has nothing to swap in"
        triggers = md.UNSAFE_FOODS[unsafe_key]
        entry = CONDITION_FOODS[rank_key]
        assert entry["good"] and entry["bad"], f"{rank_key} is missing a side"
        # nothing may be helpful and banned at once
        for food in entry["good"]:
            assert not any(md.normalize_ar(b) in md.normalize_ar(food)
                           for b in triggers), (
                f"{rank_key} calls {food!r} helpful while banning it")
        # replacements must be safe for the condition they replace for
        for alt in md.SAFE_ALTERNATIVES[unsafe_key]:
            hit = [t for t in triggers
                   if md.normalize_ar(t) in md.normalize_ar(alt["meal"])]
            assert not hit, f"{label}: the replacement {alt['meal']!r} carries {hit}"
        for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
            for goal in ("weight_loss", "muscle_gain", "bulking", "maintenance"):
                pool = md.get_meal_pool(goal, culture)
                for slot in ("breakfast", "lunch", "dinner"):
                    before = list(pool.get(slot, []))
                    if not before:
                        continue
                    survivors = [
                        m for m in before
                        if not any(md.normalize_ar(t) in md.normalize_ar(
                            m["meal"] if isinstance(m, dict) else m)
                            for t in triggers)]
                    assert len(survivors) >= 3, (
                        f"{label} leaves {len(survivors)} meals in "
                        f"{culture}/{goal}/{slot}")


def test_lupus_bans_the_two_immune_stimulants():
    # alfalfa and royal jelly are specific to lupus: they stimulate the immune
    # system, which is exactly what is attacking the patient
    banned = md.UNSAFE_FOODS["ذئبة"]
    for food in ("برسيم", "الفلفا", "غذاء ملكات النحل"):
        assert food in banned, f"lupus still allows {food}"


def test_rheumatoid_does_not_ban_the_sweet_potato_it_recommends():
    # the sheet lists nightshades to avoid AND recommends sweet potato for
    # carotenoids -- banning it would contradict the same page
    from meal_extra import CONDITION_FOODS  # noqa: E402

    banned = md.UNSAFE_FOODS["روماتويد"]
    assert "باذنجان" in banned, "aubergine is the one nightshade the sheet is firm on"
    for hedged in ("طماطم", "بطاطا"):
        assert hedged not in banned, f"{hedged} is hedged in the sheet, not banned"
    assert "بطاطا حلوة" in CONDITION_FOODS["ra"]["good"], (
        "sweet potato is recommended by the sheet and is not preferred")
    assert "طماطم" in CONDITION_FOODS["ra"]["bad"], (
        "tomato is neither banned nor ranked down")


BATCH_THREE = {
    "بطانة الرحم المهاجرة": ("بطانة الرحم", "endo"),
    "انقطاع النفس النومي": ("نفس نومي", "apnea"),
    "الربو": ("ربو", "asthma"),
    "الوذمة الشحمية": ("وذمة", "lipoedema"),
    "بعد عمليات التكميم": ("بعد التكميم", "sleeve"),
}


def test_the_third_batch_filters_prefers_and_never_empties():
    from meal_extra import CONDITION_FOODS, conditions_to_keys  # noqa: E402

    for label, (unsafe_key, rank_key) in BATCH_THREE.items():
        assert md.unsafe_keys_for([label]) == [unsafe_key], f"{label} does not resolve"
        assert conditions_to_keys([label]) == [rank_key], f"{label} does not rank"
        assert md.get_nutrient_boost_notes([label]), f"{label} has no note"
        triggers = md.UNSAFE_FOODS[unsafe_key]
        entry = CONDITION_FOODS[rank_key]
        assert entry["good"] and entry["bad"], f"{rank_key} is missing a side"
        for food in entry["good"]:
            assert not any(md.normalize_ar(b) in md.normalize_ar(food)
                           for b in triggers), (
                f"{rank_key} calls {food!r} helpful while banning it")
        for alt in md.SAFE_ALTERNATIVES[unsafe_key]:
            hit = [t for t in triggers
                   if md.normalize_ar(t) in md.normalize_ar(alt["meal"])]
            assert not hit, f"{label}: the replacement {alt['meal']!r} carries {hit}"
        for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
            for goal in ("weight_loss", "muscle_gain", "bulking", "maintenance"):
                pool = md.get_meal_pool(goal, culture)
                for slot in ("breakfast", "lunch", "dinner"):
                    before = list(pool.get(slot, []))
                    if not before:
                        continue
                    survivors = [
                        m for m in before
                        if not any(md.normalize_ar(t) in md.normalize_ar(
                            m["meal"] if isinstance(m, dict) else m)
                            for t in triggers)]
                    assert len(survivors) >= 3, (
                        f"{label} leaves {len(survivors)} in {culture}/{goal}/{slot}")


def test_asthma_does_not_ban_the_fish_and_nuts_it_recommends():
    # the sheet names milk, nuts and fish as allergy triggers and recommends
    # nuts and fish on the same page -- an individual allergy, not a rule. The
    # allergies field is where a real one gets removed.
    from meal_extra import CONDITION_FOODS  # noqa: E402

    banned = md.UNSAFE_FOODS["ربو"]
    for food in ("سمك", "مكسرات", "حليب"):
        assert food not in banned, (
            f"asthma banned {food}, which the same sheet recommends or hedges")
    good = CONDITION_FOODS["asthma"]["good"]
    assert "سمك" in good and "مكسرات" in good, (
        "the sheet recommends fish and nuts and they are not preferred")


def test_sleeve_note_carries_the_phases_and_the_numbers():
    # the protocol is weeks and portion caps, none of which a food filter can
    # express -- so the note has to hold them
    note_ar, note_en = md.NUTRIENT_BOOST_NOTES["بعد عمليات التكميم"]
    for fact in ("230", "65-75", "50-60"):
        assert fact in note_ar, f"the note lost {fact}"
        assert fact in note_en, f"the English note lost {fact}"
    assert "نص ساعة" in note_ar, "the fluid-timing rule is missing"


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

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
    # ‏العيادة بتستقبل حالات التليف والفيروسات، فلازم يكون لها نظام -- مش
    # تحذير تحويل. والتليف مختلف عن الكبد الدهني: محوره الصوديوم لا السكر.
    "تليف الكبد", "فيروس الكبد بي", "فيروس الكبد سي",
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
    "النقرس", "قصور الغدة الدرقية", "نشاط الغدة الدرقية",
    "ارتفاع الكوليسترول",
    # ‏الإبر مش أمراض، بس بتغيّر الخطة زيها -- بتبعت على نفس خانة symptoms
    # فبتدخل في نفس كل الاختبارات اللي تحت.
    "ويجوفي / أوزمبيك (سيماجلوتايد)",
    "مونجارو / زيباوند (تيرزيباتايد)",
    "ساكسيندا (ليراجلوتايد)",
]


def _conditions_in_the_form():
    """The condition labels generate.html actually renders checkboxes for."""
    import os
    import re
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html = open(os.path.join(here, "templates", "generate.html"),
                encoding="utf-8").read()
    # Read EVERY loop in the form that renders a name="symptoms" checkbox, not
    # just the conditions section. The medications section is a separate block
    # that posts to the same field -- scraping one section by its icon let the
    # three GLP-1 entries sit in the form unchecked by anything here.
    found = []
    for m in re.finditer(r"{%\s*for\s+\w+\s+in\s*\[(.*?)\]\s*%}(.*?){%\s*endfor\s*%}",
                         html, re.S):
        items, body = m.group(1), m.group(2)
        if 'name="symptoms"' not in body:
            continue
        # only the Arabic side is matched: an English label can carry an escaped
        # quote ("IBD (Crohn\'s/Colitis)"), which a pattern for both sides trips on
        found += re.findall(r"\('([^']+)'\s*,", items)
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
                # ‏الفلترة بتشيل الممنوع، فالطول بيقل -- وده المطلوب: النسخ
                # بيخلي القايمة كلها نسخ من أكتر وجبة نجت. اللي يهم إن اللي
                # بيفضل يكفي أسبوع من غير تكرار. أقل حالة مقيسة في التركيبات
                # دي ١٣ وجبة.
                assert len(after) >= 7, (
                    f"{culture}/{slot}: {len(before)} meals became {len(after)}"
                    f" -- less than a week")
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


def test_g6pd_never_serves_fava_beans_in_any_form():
    """The one that actually mattered.

    Fava beans trigger acute haemolysis in G6PD deficiency. The ban list was
    five words and caught "فول" -- so ful passed, but ta'meya and falafel,
    which are made of fava beans, did not match at all: 11 meals in the
    database contain them and 5 came through the filter. Lentils, beans and
    nuts were getting through too.
    """
    banned = md.UNSAFE_FOODS["g6pd"]
    for food in ("فول", "طعمية", "فلافل", "عدس", "حمص", "فاصوليا", "لوبيا",
                 "ترمس", "فول سوداني", "صويا", "مكسرات", "لوز", "جوز",
                 "كاجو", "باذنجان", "توت بري", "خل", "مخلل", "جمبري"):
        assert food in banned, f"G6PD still allows {food}"

    # and nothing carrying them survives the filter, in any cuisine
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
                        for t in banned)]
                assert survivors, f"G6PD empties {culture}/{goal}/{slot}"
                for meal in md.filter_by_conditions(before, ["G6PD"]):
                    text = md.normalize_ar(
                        meal["meal"] if isinstance(meal, dict) else meal)
                    hit = [t for t in banned if md.normalize_ar(t) in text]
                    assert not hit, f"G6PD was served {text[:44]!r} carrying {hit}"


def test_iron_deficiency_and_thalassaemia_pull_opposite_ways():
    # one needs iron, the other accumulates it -- and the same sheet warns the
    # two get confused, because thalassaemia can look like iron deficiency
    from meal_extra import CONDITION_FOODS, conditions_to_keys  # noqa: E402

    assert conditions_to_keys(["نقص الحديد"]) == ["iron_def"]
    assert conditions_to_keys(["ثلاسيميا"]) == ["thal"]
    iron, thal = CONDITION_FOODS["iron_def"], CONDITION_FOODS["thal"]
    # liver is the clearest case: the richest iron source there is
    assert "كبدة" in iron["good"], "iron deficiency does not prefer liver"
    assert "كبدة" in thal["bad"], "thalassaemia does not rank liver down"
    # and tea, which blocks absorption, is read the opposite way by each
    assert "شاي" in iron["bad"], "tea blocks iron absorption and is not ranked down"
    assert "شاي" in thal["good"], "tea blocks iron absorption, which helps here"
    # ticking both must not serve the contested food: bad beats good
    both = ["نقص الحديد", "ثلاسيميا"]
    from meal_extra import tag_meal  # noqa: E402
    keys = conditions_to_keys(both)
    tags = tag_meal("🍖 كبدة مشوية 120جم")
    statuses = [tags.get(k) for k in keys if k in tags]
    assert "bad" in statuses, (
        "with both conditions ticked, liver is not flagged as harmful")


FIVE_UNLOCKED = {
    "قصور الغدة الدرقية": ("غدة خمول", "hypothyroid"),
    "نشاط الغدة الدرقية": ("غدة نشاط", "hyperthyroid"),
    "النقرس": ("نقرس", "gout"),
    "ارتفاع الكوليسترول": ("كوليسترول", "chol"),
}


def test_the_five_engine_ready_conditions_are_now_reachable():
    """These were built and unreachable.

    Each already had a good/bad food list in CONDITION_FOODS and allowed and
    forbidden guidance in get_allowed_forbidden -- and no checkbox anywhere, so
    nobody could tick them. This is the state that the form-versus-test drift
    check was written to catch.
    """
    from meal_extra import CONDITION_FOODS, conditions_to_keys  # noqa: E402
    from plan_engine import get_allowed_forbidden  # noqa: E402

    in_form = set(_conditions_in_the_form())
    for label, (unsafe_key, rank_key) in FIVE_UNLOCKED.items():
        assert label in in_form, f"{label} is still not offered"
        assert md.unsafe_keys_for([label]) == [unsafe_key], f"{label} does not filter"
        assert conditions_to_keys([label]) == [rank_key], f"{label} does not rank"
        assert md.SAFE_ALTERNATIVES.get(unsafe_key), f"{label} has nothing to swap in"
        # the guidance that was already written must actually reach a plan now
        allowed, forbidden = get_allowed_forbidden([label])
        assert allowed and forbidden, f"{label} produces no allowed/forbidden text"
        # bans came out of the ranking list, so they must not contradict it
        triggers = md.UNSAFE_FOODS[unsafe_key]
        for food in CONDITION_FOODS[rank_key]["good"]:
            assert not any(md.normalize_ar(b) in md.normalize_ar(food)
                           for b in triggers), (
                f"{rank_key} calls {food!r} helpful while banning it")
        for alt in md.SAFE_ALTERNATIVES[unsafe_key]:
            hit = [t for t in triggers
                   if md.normalize_ar(t) in md.normalize_ar(alt["meal"])]
            assert not hit, f"{label}: replacement {alt['meal']!r} carries {hit}"
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


def test_ibd_is_answered_by_its_own_list_not_the_ibs_one():
    # "التهاب الأمعاء" is IBD and was mapped to the IBS ban list, so the uc
    # entry -- written for colitis and Crohn's, with the inverted whole-grain
    # rule -- was never reached. One checkbox, the right list behind it.
    assert md.CONDITION_MAP["التهاب الأمعاء"] == "تقرحي"
    assert md.CONDITION_MAP["كرون"] == "تقرحي"
    assert md.CONDITION_MAP["قولون عصبي"] == "قولون"
    assert md.UNSAFE_FOODS["تقرحي"] != md.UNSAFE_FOODS["قولون"], (
        "IBD and IBS share a list, which defeats having both")
    assert "القولون التقرحي وكرون" not in _conditions_in_the_form(), (
        "two checkboxes for the same disease")


def test_colitis_inverts_the_whole_grain_rule():
    # low residue: refined grains are preferred here and whole grains removed,
    # the opposite of every other condition in this file. Easy to "fix" by
    # mistake later, so it is pinned.
    banned = md.UNSAFE_FOODS["تقرحي"]
    for whole in ("نخالة", "شوفان", "ارز بني", "خبز اسمر", "كينوا", "برغل"):
        assert whole in banned, f"colitis should exclude {whole} during a flare"
    # while other conditions prefer exactly those
    from meal_extra import CONDITION_FOODS  # noqa: E402
    assert "شوفان" in CONDITION_FOODS["chol"]["good"], (
        "cholesterol no longer prefers oats -- check this is deliberate")
    note_ar, _ = md.NUTRIENT_BOOST_NOTES["التهاب الأمعاء"]
    assert "النوبة" in note_ar, "the note must say this is flare-time advice"


def test_ibs_and_asthma_notes_point_at_the_fields_that_can_act():
    # both sheets describe triggers that vary by person. The plan cannot guess
    # them, but the form has fields that remove them -- the notes have to say so
    ibs_ar, ibs_en = md.NUTRIENT_BOOST_NOTES["قولون عصبي"]
    assert "الأطعمة المرفوضة" in ibs_ar, "the IBS note does not name the field"
    assert "disliked-foods" in ibs_en, "the English IBS note does not name it"
    asthma_ar, asthma_en = md.NUTRIENT_BOOST_NOTES["الربو"]
    assert "الحساسية" in asthma_ar and "allergies" in asthma_en


def test_thalassaemia_note_states_what_the_centre_accepts():
    # the sheet says the centre takes carriers, not transfusion-dependent
    # patients -- a dietitian should not learn that from the filing cabinet
    note_ar, note_en = md.NUTRIENT_BOOST_NOTES["ثلاسيميا"]
    assert "حامل" in note_ar, "the note drops the carriers-only limit"
    assert "carrier" in note_en.lower()
    assert "مكملات الحديد ممنوعة" in note_ar, "the iron-supplement ban is missing"


def test_every_offered_condition_changes_the_plan_not_just_the_notes():
    """The audit that prompted this: advice alone is not an effect.

    Fourteen conditions filtered without preferring anything -- the plan
    avoided the harmful and then picked at random. Six more printed advice and
    changed nothing at all: ticking osteoporosis produced words about calcium
    and not one extra calcium-rich meal. Every condition the form offers now
    has to move the plan in at least one direction.
    """
    from meal_extra import CONDITION_FOODS, conditions_to_keys  # noqa: E402

    silent = []
    for label in _conditions_in_the_form():
        bans = md.unsafe_keys_for([label])
        keys = conditions_to_keys([label])
        # a bad-only list still moves the plan: anticoagulants has no good side
        # on purpose, and ranking vitamin K last is the whole intervention
        entry = CONDITION_FOODS.get(keys[0], {}) if keys else {}
        moves = bool(entry.get("good") or entry.get("bad"))
        if not bans and not moves:
            silent.append(label)
    # eating disorders are the one exception: they act by capping the calorie
    # target rather than by touching the food
    assert silent == ["اضطراب في الأكل"], (
        f"these conditions still do not change a plan: {silent}")


def test_the_conditions_that_only_advised_now_prefer_food():
    from meal_extra import CONDITION_FOODS, conditions_to_keys  # noqa: E402

    expected = {
        "هشاشة العظام": "حليب",      # calcium
        "امساك مزمن": "شوفان",        # fibre
        "نقص فيتامين D3": "سلمون",    # vitamin D
        "الوقاية من السرطان": "بروكلي",
        "حرق بطيء": "بروتين",
        "السمنة": "خضار",
    }
    for label, food in expected.items():
        keys = conditions_to_keys([label])
        assert keys, f"{label} still resolves to no ranking key"
        good = CONDITION_FOODS[keys[0]]["good"]
        assert food in good, f"{label} does not prefer {food}"


def test_every_ban_list_has_something_to_swap_in():
    for label in _conditions_in_the_form():
        for key in md.unsafe_keys_for([label]):
            assert md.SAFE_ALTERNATIVES.get(key), (
                f"{label} bans food with no replacement, so filtering just "
                f"shrinks the pool")


def test_guidance_notes_are_bilingual():
    for c, pair in md.NUTRIENT_BOOST_NOTES.items():
        assert isinstance(pair, tuple) and len(pair) == 2, f"{c} is not bilingual"
        ar, en = pair
        assert ar.strip() and en.strip(), f"{c} has an empty side"
        assert md.translate_boost_note(ar) == en, f"{c} does not map back to English"


def test_free_text_notes_pass_through_untouched():
    assert md.translate_boost_note("ملاحظة من الدكتور") == "ملاحظة من الدكتور"


def test_cirrhosis_never_bans_grilled_food():
    """‏"مش" (جبنة مش) بيمسك "مشوي" كـsubstring.

    القياس قال 10 وجبات مشوية -- وهي بالظبط اللي مريض التليف المفروض ياكلها.
    التوكن ده لازم يفضل برّه القايمة.
    """
    ban = md.UNSAFE_FOODS["تليف"]
    assert "مش" not in ban, "‏التوكن ده بيمنع كل المشوي"
    grilled = [
        {"meal": "🍗 دجاج مشوي 150جم + 🍚 ارز + 🥗 سلطة", "cal": 420, "p": 44},
        {"meal": "🐟 سمك مشوي + 🥗 سلطة", "cal": 380, "p": 40},
    ]
    for item in grilled:
        assert md.safe_for_all(item, ["تليف"]), "‏اتمنع بالغلط: " + item["meal"]


def test_cirrhosis_bans_no_protein_source():
    """‏تقييد البروتين في التليف خرافة قديمة وخطرة -- بيسرّع فقدان العضل.

    فلو حد ضاف مصدر بروتين لقايمة المنع، ده مش تشديد، ده ضرر.
    """
    protein = ["فول", "عدس", "بيض", "دجاج", "فراخ", "سمك", "زبادي", "لبن",
               "جبن قريش", "لحم", "حمص", "فاصوليا", "تونة", "بروتين"]
    ban = md.UNSAFE_FOODS["تليف"]
    hits = [p for p in protein if p in ban]
    assert not hits, "‏مصدر بروتين في قايمة منع التليف: %s" % hits


def test_the_liver_conditions_filter_without_emptying_a_slot():
    """‏لو خانة فضيت، filter بيرجّع القايمة غير المفلترة -- يعني بيقدّم الممنوع."""
    for cond in ("تليف الكبد", "فيروس الكبد بي", "فيروس الكبد سي"):
        keys = md.unsafe_keys_for([cond])
        assert keys, "‏%s مش مربوطة بقايمة منع" % cond
        for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
            for goal in ("تخسيس", "مكتنز", "زيادة عضل", "تضخيم"):
                pool = md.get_meal_pool(goal, culture)
                for slot, items in pool.items():
                    if not items:
                        continue
                    left = [i for i in items if md.safe_for_all(i, keys)]
                    assert len(left) >= 3, (
                        "‏%s / %s / %s / %s سابت %d وجبة بس"
                        % (cond, culture, goal, slot, len(left)))


def test_cirrhosis_note_carries_the_late_snack_and_the_protein_correction():
    """‏دول التدخلين اللي الفلترة ماتقدرش تعبّر عنهم، فلازم يكونوا في الملاحظة."""
    ar = " ".join(md.get_nutrient_boost_notes(["تليف الكبد"], "ar"))
    en = " ".join(md.get_nutrient_boost_notes(["تليف الكبد"], "en"))
    assert ar and en, "‏مفيش ملاحظة للتليف"
    assert "سناك متأخر" in ar, "‏السناك الليلي أقوى تدخل في التليف ومش مكتوب"
    assert "مش* ممنوع" in ar or "مش ممنوع" in ar, "‏تصحيح خرافة البروتين ناقص"
    assert "NOT restricted" in en, "‏النص الإنجليزي مش بيوضّح إن البروتين مسموح"
    assert "1.2" in ar and "1.2" in en, "‏الجرعة المطلوبة مش مذكورة"


def test_hepatitis_c_warns_about_iron():
    """‏اللي بيفرّق C عن B هو الحديد: زيادته بتسرّع التليّف."""
    ar = " ".join(md.get_nutrient_boost_notes(["فيروس الكبد سي"], "ar"))
    en = " ".join(md.get_nutrient_boost_notes(["فيروس الكبد سي"], "en"))
    assert "حديد" in ar, "‏تحذير الحديد ناقص في C"
    assert "iron" in en.lower(), "‏تحذير الحديد ناقص في النص الإنجليزي"
    assert "كبدة" in md.UNSAFE_FOODS["فيروسي"], "‏الكبدة مصدر حديد مركّز ولازم تتمنع"


def test_the_liver_conditions_prefer_and_not_only_forbid():
    """‏زي ما طلبت: الحالة لازم تمنع الضار *وتقدّم* المفيد."""
    import meal_extra as me
    for cond in ("تليف الكبد", "فيروس الكبد بي", "فيروس الكبد سي"):
        key = me.CONDITION_KEYS.get(cond)
        assert key, "‏%s مالهاش مفتاح ترتيب" % cond
        foods = me.CONDITION_FOODS.get(key) or {}
        assert foods.get("good"), "‏%s مابتقدّمش أي أكل" % cond
        assert foods.get("bad"), "‏%s مابتأخّرش أي أكل" % cond


GLP1 = ["ويجوفي / أوزمبيك (سيماجلوتايد)",
        "مونجارو / زيباوند (تيرزيباتايد)",
        "ساكسيندا (ليراجلوتايد)"]


def test_the_injections_carry_their_intervention_in_the_note_not_the_ban():
    """‏قايمة المنع بتمسك 3 وجبات بس من 926 -- القاعدة نضيفة أصلاً.

    فلو حد جه بعدين وشال الملاحظات فاكر إن المنع هو الشغل، الإبرة بتبقى
    مالهاش أي تأثير تقريباً. الاختبار ده بيثبّت إن الملاحظة هي الحمل.
    """
    for med in GLP1:
        ar = " ".join(md.get_nutrient_boost_notes([med], "ar"))
        en = " ".join(md.get_nutrient_boost_notes([med], "en"))
        assert ar and en, "‏%s من غير ملاحظة" % med
        for needed in ("وجبات صغيرة", "البروتين", "1.2-1.5", "سوائل بين الوجبات"):
            assert needed in ar, "‏%s: ناقص '%s'" % (med, needed)
        for needed in ("small meals", "Protein first", "1.2-1.5"):
            assert needed in en, "‏%s: الإنجليزي ناقص '%s'" % (med, needed)


def test_the_injections_warn_about_what_sends_a_patient_to_hospital():
    """‏التهاب البنكرياس والحصوات مش تفاصيل -- دول اللي بيودّوا الطوارئ."""
    for med in GLP1:
        ar = " ".join(md.get_nutrient_boost_notes([med], "ar"))
        en = " ".join(md.get_nutrient_boost_notes([med], "en"))
        assert "بنكرياس" in ar, "‏%s: تحذير البنكرياس ناقص" % med
        assert "مرارة" in ar, "‏%s: تحذير الحصوات ناقص" % med
        assert "الحمل" in ar, "‏%s: الإبر ممنوعة في الحمل ولازم تتكتب" % med
        assert "pancreatitis" in en.lower(), "‏%s: الإنجليزي ناقص" % med
        assert "pregnancy" in en.lower(), "‏%s: الإنجليزي ناقص الحمل" % med


def test_the_injections_put_protein_first_in_the_ranking():
    """‏المريض بيشبع بعد لقمتين، فاللي جوه الحجم الصغير ده يحدد عضل ولا دهون."""
    import meal_extra as me
    for med in GLP1:
        key = me.CONDITION_KEYS.get(med)
        assert key == "glp1", "‏%s مش مربوطة بترتيب الإبر" % med
        good = me.CONDITION_FOODS["glp1"]["good"]
        for protein in ("دجاج", "سمك", "بيض", "زبادي", "عدس"):
            assert protein in good, "‏%s مش في قايمة التقديم" % protein


def test_the_injections_never_empty_a_slot():
    for med in GLP1:
        keys = md.unsafe_keys_for([med])
        assert keys, "‏%s مش مربوطة بقايمة منع" % med
        for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
            for goal in ("تخسيس", "مكتنز", "زيادة عضل", "تضخيم"):
                for slot, items in md.get_meal_pool(goal, culture).items():
                    if not items:
                        continue
                    left = [i for i in items if md.safe_for_all(i, keys)]
                    assert len(left) >= 3, (
                        "‏%s / %s / %s / %s سابت %d" % (med, culture, goal, slot, len(left)))


def test_the_stronger_injection_says_it_is_stronger():
    """‏تيرزيباتايد أقوى فالنزول أسرع وخطر العضل أعلى -- فرق يستاهل يتكتب."""
    tirz = " ".join(md.get_nutrient_boost_notes(["مونجارو / زيباوند (تيرزيباتايد)"], "ar"))
    sema = " ".join(md.get_nutrient_boost_notes(["ويجوفي / أوزمبيك (سيماجلوتايد)"], "ar"))
    assert "أقوى" in tirz, "‏فرق القوة مش مكتوب"
    assert tirz != sema, "‏النصين متطابقين -- يعني الفرق مش مذكور"


def test_every_condition_has_enough_safe_meals_in_every_slot():
    """‏الرقم ده كان ١ للسيلياك في الفطار، و**صفر** في العشا.

    القياس الأصلي، على كل حالة × هدف × مطبخ:

        السيلياك واللاكتوز، الفطار:  ١ من ١٢
        السيلياك، العشا:             صفر في (مغربي/تثبيت) و(شامي/تضخيم)
        السيلياك، العشا:             ١ في (مصري/تثبيت)
        اللاكتوز، العشا:             ٣ من ١٣
        G6PD و SIBO والإسهال، العشا: ٤ من ١٣
        كرون والتقرحي، الغدا:        ٥ من ١٣

    صفر معناها إن الخطة بتتبني من SAFE_ALTERNATIVES -- قايمة مش عارفة
    الخانة. وواحدة معناها نفس الوجبة سبع مرات.

    عشرة مش سبعة: سبعة تعني وجبة لكل يوم بالعدد وصفر تنويع، فأي استثناء
    أكل أو تكرار بيرجّعنا لنفس المشكلة.
    """
    import plan_engine  # noqa: F401  -- بيحمّل meal_extra
    from meal_database import get_meal_pool, _contains_unsafe, _meal_text

    conds = _all_conditions()
    assert conds, "‏مافيش حالات مرضية أصلاً -- الاختبار مش بيقيس حاجة"
    short = []
    for ar, keys in conds.items():
        for goal in ("weight_loss", "maintenance", "muscle_gain", "bulking"):
            for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
                for slot in ("breakfast", "lunch", "dinner"):
                    pool = get_meal_pool(goal, culture).get(slot, [])
                    safe = [m for m in pool
                            if not any(_contains_unsafe(_meal_text(m), k)
                                       for k in keys)]
                    if len(safe) < _MIN_SAFE_BREAKFASTS:
                        short.append("%s / %s / %s / %s: %d"
                                     % (ar, goal, culture, slot, len(safe)))
    assert not short, (
        "‏الخانات دي أقل من %d وجبة آمنة:\n   %s"
        % (_MIN_SAFE_BREAKFASTS, "\n   ".join(short[:12])))


# ‏شكل الفطار. أطباق الغدا دي مالهاش لازمة في عمود الفطار، ولا لأي حالة
# مرضية. الاستثناءات مقصودة: "رقاق أرز" فطار خالي من الجلوتين، و"لحم ديك
# رومي" لحمة فطار (بيكون في الفطار الأمريكي).
_NOT_BREAKFAST = ("ارز", "أرز", "رز ", "مكرونة", "معكرونة", "كشري",
                  "تونة", "سردين", "دجاج", "فراخ", "سمك", "سلمون", "جمبري",
                  "لحم بقري", "لحم مفروم", "كفتة", "شاورما", "كبسة",
                  "برياني", "ملوخية", "بامية", "طاجن", "محشي", "شوربة",
                  "بطاطس مسلوقة", "بطاطس مهروسة")
_BREAKFAST_ANYWAY = ("رقاق أرز", "لحم ديك رومي")


def _breakfast_shape_offence(text):
    """‏الحاجات اللي بتخلي الوجبة دي طبق غدا، أو لستة فاضية لو شكلها فطار."""
    t = text
    for ok in _BREAKFAST_ANYWAY:
        t = t.replace(ok, "")
    return [w for w in _NOT_BREAKFAST if w in t]


def test_no_breakfast_in_the_database_is_a_lunch_plate():
    """‏ده اللي الدكتور شافه في ورقة عميل حقيقية.

    أول محاولة مني لحل مشكلة الفطار زوّدت "أرز أبيض + تونة + جزر مسلوق"
    و"سردين مصفّى + بطاطس مسلوقة" -- آمنة طبياً، مظبوطة في السعرات، وشكلها
    غدا. فالمشكلة اللي اتصلحت في الفلترة رجعت من باب الداتا. الاختبار ده
    بيقف على الشكل نفسه، مش على الفلترة.
    """
    import plan_engine  # noqa: F401
    from meal_database import get_meal_pool, _meal_text

    offenders = []
    for goal in ("weight_loss", "maintenance", "muscle_gain", "bulking"):
        for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
            for meal in get_meal_pool(goal, culture).get("breakfast", []):
                text = _meal_text(meal)
                hits = _breakfast_shape_offence(text)
                if hits:
                    offenders.append("%s  <- %s" % (text[:64], ", ".join(hits[:3])))
    assert not offenders, (
        "‏فطار شكله طبق غدا:\n   %s" % "\n   ".join(sorted(set(offenders))[:10]))


def test_a_banned_breakfast_is_replaced_by_a_breakfast():
    """‏الاستبدال لازم يفضل في نفس خانة الوجبة.

    SAFE_ALTERNATIVES قايمة واحدة لكل حالة، مش عارفة هي بتقف مكان فطار ولا
    غدا -- فكانت بتحط طبق غدا في الفطار. الفلترة بقت بتملّي الفراغ من نفس
    القايمة الأول، والقايمة دي فطار كلها.
    """
    import plan_engine  # noqa: F401
    from meal_database import get_meal_pool, filter_by_conditions, _meal_text

    offenders = []
    for ar in _all_conditions():
        for goal in ("weight_loss", "muscle_gain"):
            for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
                pool = get_meal_pool(goal, culture).get("breakfast", [])
                out = filter_by_conditions(pool, [ar])
                assert out, "‏فطار %s/%s/%s طلع فاضي" % (ar, goal, culture)
                for meal in out:
                    text = _meal_text(meal)
                    hits = _breakfast_shape_offence(text)
                    if hits:
                        offenders.append("%s: %s" % (ar, text[:58]))
    assert not offenders, (
        "‏فطار طلع طبق غدا بعد الفلترة:\n   %s"
        % "\n   ".join(sorted(set(offenders))[:8]))


def test_the_new_breakfasts_all_read_in_english_too():
    """‏الوجبة اللي مش مترجمة بتطلع عربي في PDF إنجليزي."""
    import meal_extra
    from meal_i18n import translate_meal, untranslated_terms

    missing = []
    for source, slots in ((meal_extra.EXTRA_BREAKFASTS, ("breakfast",)),
                          (meal_extra.EXTRA_MAIN_MEALS, ("lunch", "dinner"))):
        for goal, cultures in source.items():
            for slot in slots:
                for meal in cultures["مصري"][slot]:
                    text = meal["meal"]
                    if translate_meal(text) == text:
                        missing.append("%s -> %s"
                                       % (text[:45], untranslated_terms(text)))
    assert not missing, "‏وجبات مش مترجمة:\n   %s" % "\n   ".join(missing)


def test_the_four_portion_tiers_stay_in_step():
    """‏الوجبة مكتوبة مرة واحدة بحصص لكل هدف، عشان النسخ ما تختلفش.

    ولازم السعرات تكبر مع الهدف: التخسيس أقل من التثبيت أقل من العضل أقل من
    التضخيم. لو حد عدّل حصة ونسي سعراتها، الترتيب بيتكسر هنا.
    """
    import meal_extra
    order = ("weight_loss", "maintenance", "muscle_gain", "bulking")
    for source, slots in ((meal_extra.EXTRA_BREAKFASTS, ("breakfast",)),
                          (meal_extra.EXTRA_MAIN_MEALS, ("lunch", "dinner"))):
        for slot in slots:
            lists = [source[g]["مصري"][slot] for g in order]
            assert len({len(x) for x in lists}) == 1, (
                "‏%s: الأهداف مش ليها نفس عدد الوجبات" % slot)
            for i in range(len(lists[0])):
                cals = [lst[i]["cal"] for lst in lists]
                assert cals == sorted(cals), (
                    "‏وجبة %r سعراتها مش بتكبر مع الهدف: %s"
                    % (lists[0][i]["meal"][:40], cals))
                prots = [lst[i]["p"] for lst in lists]
                assert prots == sorted(prots), (
                    "‏وجبة %r بروتينها مش بيكبر مع الهدف: %s"
                    % (lists[0][i]["meal"][:40], prots))


# ═══════════════════════════════════════════════════════════════════════════
# ‏الفطار: العدد الآمن، وإن البديل يفضل فطار
# ═══════════════════════════════════════════════════════════════════════════

_MIN_SAFE_BREAKFASTS = 10


def _all_conditions():
    from meal_database import CONDITION_MAP, unsafe_keys_for
    out = {}
    for ar in sorted(set(CONDITION_MAP)):
        keys = unsafe_keys_for([ar])
        if keys:
            out[ar] = keys
    return out


def test_the_week_does_not_repeat_one_ingredient_in_any_slot():
    """‏٥ أيام بيض من ٧ مش تنويع، وده اللي كان بيحصل.

    سببين اتجمعوا: قايمة الفطار فيها بيض كتير (لأنه المصدر الوحيد اللي
    بيعدّي الجلوتين واللاكتوز والبقوليات مع بعض)، والترتيب بالبروتين بيطلّعه
    فوق -- فأول ٧ كلهم بيض. وكان فيه سبب تالت أسوأ: الفلترة كانت بتملّي
    الوجبة الممنوعة بنسخة من الآمن، فقايمة فطار ٣٥ وجبة بعد فلترة اللاكتوز
    بقت ٣٣ بيض و٢ شوفان.

    القياس على كل الحالات × الأهداف × المطابخ: أقصى تكرار لمكوّن واحد ٣.
    """
    import random
    import app as A
    import plan_engine
    from collections import Counter
    from meal_database import CONDITION_MAP

    base = {"name": "اختبار", "age": "30", "gender": "انثى", "height": "165",
            "weight": "80", "tdee": "2000", "goal_cal": "1600",
            "protein_per_kg": "1.6", "fat_pct_cal": "30", "allergies": [],
            "diet_plan_type": "standard", "zigzag_mode": "off"}
    conds = [[], ["حساسية اللاكتوز"], ["حساسية الجلوتين"], ["سكري النوع الثاني"],
             ["قولون عصبي"], ["الفشل الكلوي المزمن"]]
    worst = (0, None)
    random.seed(11)
    for symptoms in conds:
        for goal in ("weight_loss", "maintenance", "muscle_gain", "bulking"):
            for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
                data = dict(base, culture=culture, goal_type=goal,
                            symptoms=symptoms)
                with A.app.test_request_context("/"):
                    week = plan_engine.generate_weekly_plan(data)
                for slot, base_of in (("breakfast", plan_engine._bf_base),
                                      ("lunch", plan_engine._main_base),
                                      ("dinner", plan_engine._main_base)):
                    counts = Counter(base_of(day.get(slot, "")) for day in week)
                    top, n = counts.most_common(1)[0]
                    if n > worst[0]:
                        worst = (n, (slot, symptoms, goal, culture, top))
    assert worst[0] <= 4, (
        "‏مصدر واحد اتكرر %d مرات في الأسبوع: %s" % worst)


def test_the_filter_drops_what_it_bans_instead_of_cloning_a_survivor():
    """‏الشيل بيسيب التوزيع زي ما الفلترة سابته. النسخ بيضخّم أكتر حاجة نجت."""
    import plan_engine  # noqa: F401
    from meal_database import get_meal_pool, filter_by_conditions, _meal_text

    pool = get_meal_pool("maintenance", "مصري").get("breakfast", [])
    out = filter_by_conditions(pool, ["حساسية اللاكتوز"])
    assert out, "‏الفلترة فضّت القايمة"
    texts = [_meal_text(m) for m in out]
    assert len(texts) == len(set(texts)), (
        "‏في وجبات مكرّرة بعد الفلترة -- الاستبدال بينسخ بدل ما يشيل")
    assert len(out) < len(pool), (
        "‏اللاكتوز مامنعتش أي وجبة -- الاختبار مش بيقيس حاجة")


def test_no_slot_is_ever_left_empty_after_dropping():
    """‏الشيل خطر: خانة فاضية = يوم من غير وجبة.

    ولو الفلترة رجعت لستة فاضية، الكود اللي بيناديها بيرجع للقايمة **قبل**
    الفلترة -- يعني بيقدّم للمريض الأكل اللي المنع موجود عشانه.
    """
    import plan_engine  # noqa: F401
    from meal_database import get_meal_pool, filter_by_conditions

    empty = []
    for ar in _all_conditions():
        for goal in ("weight_loss", "maintenance", "muscle_gain", "bulking"):
            for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
                for slot in ("breakfast", "lunch", "dinner"):
                    pool = get_meal_pool(goal, culture).get(slot, [])
                    if pool and not filter_by_conditions(pool, [ar]):
                        empty.append("%s / %s / %s / %s" % (ar, goal, culture, slot))
    assert not empty, "‏خانات فضيت:\n   %s" % "\n   ".join(empty[:10])


def test_no_meal_carries_the_same_unit_twice():
    """‏"زيت زيتون ملعقة 1 ملعقة" -- ده اللي طلع في ورقة عميل.

    add_grams بتزوّد كمية لأي صنف مكتوب من غير رقم. فلما كتبت الحصة
    "ملعقة" من غير رقم، الدالة شافت صنف بلا كمية وضافت "1 ملعقة" جنبها.
    الحصص كلها بقى فيها رقم، والاختبار ده بيمسك أي وجبة جديدة تتكتب
    من غير رقم فتتكرر عليها الوحدة تاني.
    """
    import re
    import plan_engine  # noqa: F401
    from meal_database import get_meal_pool, _meal_text

    # ‏الوحدة الواحدة مالهاش تتكرر في نفس الصنف. بنعدّ جوه كل صنف لوحده،
    # لأن الوجبة كلها فيها ملاعق كتير عادي، وبنشيل ال(kcal) الآخر.
    #
    # ‏"جم" لازم تتقاس كوحدة مش كحروف: "عين جمل 10جم" و"جمبري 150جم" فيهم
    # "جم" جوه الكلمة نفسها، فالعدّ الساذج كان بيبلّغ عليهم غلط.
    UNITS = (r"\d\s*جم(?![\u0600-\u06FF])",
             r"ملعقة(?![\u0600-\u06FF])",
             r"ملاعق(?![\u0600-\u06FF])",
             r"كوب(?![\u0600-\u06FF])")
    offenders = set()
    for goal in ("weight_loss", "maintenance", "muscle_gain", "bulking"):
        for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
            for slot in ("breakfast", "lunch", "dinner"):
                for meal in get_meal_pool(goal, culture).get(slot, []):
                    text = re.sub(r"\([^)]*kcal[^)]*\)", "", _meal_text(meal))
                    for segment in text.split(" + "):
                        if any(len(re.findall(u, segment)) > 1 for u in UNITS):
                            offenders.add(segment.strip()[:60])
    assert not offenders, (
        "‏وجبات مكتوب فيها الوحدة مرتين:\n   %s"
        % "\n   ".join(sorted(offenders)[:8]))


def test_the_advice_panel_never_allows_what_the_filter_bans():
    """‏ورقة مريض السيلياك كانت بتقوله "شوفان + خبز أسمر + أرز بني: مسموح".

    الفلترة في نفس الوقت شايلة كل وجبة فيها خبز من جدوله. فالجدول صح
    والنصيحة اللي جنبه غلط -- والمريض بياخد الورقتين مع بعض.

    السبب إن قايمة المسموح/الممنوع مكتوبة بإيد وبفرع لكل حالة، ومافيش
    فرع للسيلياك، فبياخد القايمة العامة. ونفس الحاجة في G6PD: "عدس أصفر"
    مكتوب مسموح والعدس في قايمة منعه.

    القايمة بقت بتتعرض على نفس قوايم المنع، على مستوى الصنف مش السطر.
    """
    import plan_engine
    from meal_database import unsafe_keys_for, _contains_unsafe

    offenders = []
    for ar, keys in _all_conditions().items():
        for goal in ("weight_loss", "maintenance", "muscle_gain", "bulking"):
            allowed, _forbidden = plan_engine.get_allowed_forbidden([ar], goal)
            for line in allowed:
                for item in str(line).split(" + "):
                    if any(_contains_unsafe(item, k) for k in keys):
                        offenders.append("%s / %s: %s" % (ar, goal, item.strip()))
    assert not offenders, (
        "‏بنود ممنوعة مكتوبة 'مسموح':\n   %s"
        % "\n   ".join(sorted(set(offenders))[:10]))


def test_filtering_the_advice_does_not_empty_it():
    """‏ورقة من غير نصيحة مش ورقة. الفلترة بتشيل الصنف لا السطر."""
    import plan_engine

    for ar in _all_conditions():
        for goal in ("weight_loss", "muscle_gain"):
            allowed, forbidden = plan_engine.get_allowed_forbidden([ar], goal)
            assert len(allowed) >= 3, (
                "‏%s / %s: المسموح بقى %d سطر بس" % (ar, goal, len(allowed)))
            assert forbidden, "‏%s / %s: مافيش ممنوع" % (ar, goal)


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

# -*- coding: utf-8 -*-
"""Calorie cycling has one promise it must never break.

The whole point of a zigzag is that the week averages out to the target the
plan was built on. If the swing quietly loses or gains calories -- because a
day got clamped at the safety floor and nobody redistributed the difference --
the client is on a different plan than the one on the PDF, and neither they
nor the doctor can see it.

These lock in that the weekly total survives every mode, every target, and
every clamp, and that no single day is ever pushed below the clinical floor.

Run with:  python3 tests/test_zigzag.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import zigzag as zz  # noqa: E402

TARGETS = [1200, 1400, 1600, 1800, 2000, 2400, 3000, 3500]
GENDERS = ["ذكر", "أنثى"]


def test_every_mode_preserves_the_weekly_total():
    for mode in zz.ZIGZAG_MODES:
        for gender in GENDERS:
            for target in TARGETS:
                z = zz.build_zigzag(target, mode, gender=gender, weight=75,
                                    protein_per_kg=1.6, fat_pct=30, tdee=target * 1.3)
                got = z["weekly_total"]
                want = target * 7
                assert got == want, (
                    f"{mode}/{gender}/{target}: weekly total {got} != {want}")


def test_no_day_falls_below_the_clinical_floor():
    for mode in zz.ZIGZAG_MODES:
        for gender in GENDERS:
            floor = zz._floor_for(gender)
            for target in TARGETS:
                z = zz.build_zigzag(target, mode, gender=gender, weight=75, tdee=target * 1.3)
                # a target already at or under the floor cannot be cycled at all;
                # in that case every day is left equal to the target
                limit = min(floor, target)
                for d in z["days"]:
                    assert d["kcal"] >= limit - 5, (
                        f"{mode}/{gender}/{target}: {d['day_ar']} at {d['kcal']} "
                        f"is below the floor {limit}")


def test_a_target_at_the_floor_disables_cycling():
    z = zz.build_zigzag(1200, "strong", gender="أنثى", weight=60)
    assert z["floor_disabled"] is True
    assert z["low"] == z["high"] == 1200, "a floor-level target must not swing"


def test_protein_is_constant_and_carbs_carry_the_swing():
    z = zz.build_zigzag(2000, "classic", gender="ذكر", weight=80,
                        protein_per_kg=1.8, fat_pct=30, tdee=2600)
    proteins = {d["protein_g"] for d in z["days"]}
    assert len(proteins) == 1, f"protein moved across the week: {proteins}"
    assert proteins.pop() == round(80 * 1.8)

    carbs = [d["carb_g"] for d in z["days"]]
    assert max(carbs) > min(carbs), "carbs did not absorb the calorie swing"

    # the high day must carry more carbs than the low day, not fewer
    high = max(z["days"], key=lambda d: d["kcal"])
    low = min(z["days"], key=lambda d: d["kcal"])
    assert high["carb_g"] > low["carb_g"]


def test_macros_add_up_to_the_day_calories():
    for mode in ("gentle", "classic", "strong", "refeed", "training"):
        z = zz.build_zigzag(2200, mode, gender="ذكر", weight=85,
                            protein_per_kg=2.0, fat_pct=30, tdee=2800)
        for d in z["days"]:
            kcal = d["protein_g"] * 4 + d["carb_g"] * 4 + d["fat_g"] * 9
            # rounding to whole grams costs a few kcal; anything more is a bug
            assert abs(kcal - d["kcal"]) <= 12, (
                f"{mode}/{d['day_ar']}: macros total {kcal} vs {d['kcal']} kcal")


def test_fat_never_drops_below_the_hormonal_minimum():
    # a hard cut with a big swing is where fat gets squeezed
    z = zz.build_zigzag(1400, "strong", gender="ذكر", weight=90,
                        protein_per_kg=2.2, fat_pct=25, tdee=2200)
    floor_g = round(90 * zz.MIN_FAT_PER_KG)
    for d in z["days"]:
        assert d["fat_g"] >= floor_g, (
            f"{d['day_ar']}: fat {d['fat_g']}g is below the {floor_g}g minimum")


def test_an_impossible_prescription_is_flagged_not_hidden():
    # 1400 kcal with 2.2 g/kg protein on a 90 kg client leaves nothing for fat
    z = zz.build_zigzag(1400, "strong", gender="ذكر", weight=90,
                        protein_per_kg=2.2, fat_pct=25, tdee=2200)
    assert z["fat_floor_applied"] is True, "the fat floor was not applied"
    assert z["min_fat_g"] == round(90 * zz.MIN_FAT_PER_KG)

    # and a prescription that cannot fit at all must say so
    hard = zz.build_zigzag(1000, "off", gender="ذكر", weight=100,
                           protein_per_kg=2.5, fat_pct=30)
    assert hard["macro_conflict"] is True, (
        "protein plus the fat floor exceeded the day's calories without a flag")
    assert all(d["carb_g"] == 0 for d in hard["days"]), "carbs went negative"

    # a sane prescription raises neither flag
    ok = zz.build_zigzag(2200, "classic", gender="ذكر", weight=80,
                         protein_per_kg=1.6, fat_pct=30, tdee=2800)
    assert ok["fat_floor_applied"] is False and ok["macro_conflict"] is False


def test_custom_percentages_are_recentred_on_the_target():
    # seven days all asking for +50% cannot mean a 50% surplus week --
    # the pattern is an offset around the target, so it gets recentred
    z = zz.build_zigzag(2000, custom=[50] * 7, gender="ذكر", weight=80)
    assert z["weekly_total"] == 2000 * 7
    assert all(d["pct"] == 0 for d in z["days"])


def test_custom_percentages_survive_a_round_trip():
    pattern = [20, -20, 10, -10, 0, 15, -15]
    z = zz.build_zigzag(2000, custom=pattern, gender="ذكر", weight=80, tdee=2600)
    assert z["weekly_total"] == 2000 * 7
    assert [d["pct"] for d in z["days"]] == pattern


def test_bad_input_returns_nothing_instead_of_crashing():
    assert zz.build_zigzag(0) is None
    assert zz.build_zigzag(None) is None
    assert zz.build_zigzag("") is None
    assert zz.build_zigzag("not a number") is None
    # an unknown mode falls back to the default rather than raising
    z = zz.build_zigzag(2000, "no-such-mode", gender="ذكر")
    assert z["mode"] == zz.DEFAULT_MODE


def test_every_mode_is_bilingual_and_sums_to_zero():
    for key, m in zz.ZIGZAG_MODES.items():
        for field in ("ar", "en", "desc_ar", "desc_en"):
            assert m.get(field, "").strip(), f"{key} is missing {field}"
        assert len(m["pattern"]) == 7, f"{key} does not have seven days"
        assert abs(sum(m["pattern"])) < 0.001, (
            f"{key} sums to {sum(m['pattern'])}, so it would shift the weekly total")


def test_zigzag_from_data_reads_the_plan_form():
    assert zz.zigzag_from_data({"zigzag_mode": "off"}) is None
    assert zz.zigzag_from_data({}) is None

    z = zz.zigzag_from_data({
        "zigzag_mode": "refeed", "goal_cal": "1800", "weight": "75",
        "gender": "ذكر", "tdee": "2400", "protein_per_kg": "1.6", "fat_pct_cal": "30",
    })
    assert z is not None and z["weekly_total"] == 1800 * 7
    assert z["days"][0]["protein_g"] == round(75 * 1.6)

    # the form posts custom percentages as one comma-separated string
    z2 = zz.zigzag_from_data({
        "zigzag_mode": "custom", "zigzag_custom": "10,-10,10,-10,0,5,-5",
        "goal_cal": "2000", "weight": "80", "gender": "ذكر",
    })
    assert [d["pct"] for d in z2["days"]] == [10, -10, 10, -10, 0, 5, -5]


def test_the_plan_carries_the_targets_onto_its_days():
    os.environ.setdefault("SECRET_KEY", "test-key")
    from core import app  # noqa: E402
    from plan_engine import generate_weekly_plan  # noqa: E402

    data = {
        "name": "تست", "age": "30", "gender": "ذكر", "height": "175", "weight": "85",
        "tdee": "2400", "goal_cal": "1900", "protein_per_kg": "1.8", "fat_pct_cal": "30",
        "goal_type": "weight_loss", "culture": "مصري", "diet_plan_type": "standard",
        "symptoms": [], "allergies": [], "notes": "", "disliked_foods": "",
        "zigzag_mode": "classic", "user_id": 1,
    }
    with app.test_request_context("/"):
        plan = generate_weekly_plan(data)

    assert data["zigzag"], "the plan did not build a zigzag"
    assert sum(d["target_cal"] for d in plan) == 1900 * 7
    for d in plan:
        for key in ("target_cal", "zigzag_pct", "zigzag_level",
                    "target_p", "target_c", "target_f"):
            assert key in d, f"{d['day']} is missing {key}"

    # and with cycling off, the days stay clean of zigzag fields
    off = dict(data, zigzag_mode="off")
    with app.test_request_context("/"):
        plan_off = generate_weekly_plan(off)
    assert off["zigzag"] is None
    assert "target_cal" not in plan_off[0]


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

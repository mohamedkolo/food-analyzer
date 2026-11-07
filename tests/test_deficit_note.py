# -*- coding: utf-8 -*-
"""‏العجز: قد إيه بالنسبة، ومعناه إيه بالكيلو.

‏الدكتور بيكتب هدف السعرات بإيده، والفرق لوحده مابيقولش حاجة:

    ‏ناقص ٥٠٠ على حرق ٣٠٠٠  = ١٧٪  → مظبوط
    ‏ناقص ٥٠٠ على حرق ١٨٠٠  = ٢٨٪  → قاسي

‏نفس الرقم، وحالتين مختلفتين. فاللي بيتقاس هو **النسبة** مش الفرق.

‏والحتة التانية: العجز ده معناه إيه بالكيلو في الأسبوع. ٧٧٠٠ سعرة ≈
كيلو دهون، والمعدل الآمن ٠.٥-١٪ من وزن الجسم أسبوعياً. أسرع من كده
معناه إن جزء من النازل **عضل** -- وده مابيبانش في الميزان، وبيتكشف
بعد شهرين لما الحرق يكون نزل والعميل يكون فقد ثقته في الخطة.

‏والاتنين **ملاحظة مش منع**: الدكتور ممكن يكون عارف وقاصد، والورقة
بتتولّد عادي.

Run with:  python3 tests/test_deficit_note.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_deficit_test.db")

import app as A            # noqa: E402
import plan_engine         # noqa: E402
import zigzag              # noqa: E402

_BASE = {"name": "ع", "gender": "انثى", "age": "34", "height": "163",
         "weight": "82", "culture": "مصري", "diet_plan_type": "standard",
         "goal_type": "weight_loss", "activity_level": "light",
         "tdee": "1800", "goal_cal": "1300", "protein_per_kg": "1.6",
         "fat_pct_cal": "30", "allergies": [], "symptoms": [],
         "zigzag_mode": "off"}


def _notes(**over):
    data = dict(_BASE)
    data.update(over)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data, seed="g")
        plan_engine.plan_html(data, plan)
    return data, [n for n in (data.get("sheet_notes") or [])
                  if "العجز" in n["short"]]


# ── نفس الرقم، حالتين ────────────────────────────────────────────────

def test_the_same_five_hundred_is_a_warning_for_one_and_fine_for_another():
    """‏ده بيت القصيد كله."""
    _d1, small = _notes(tdee="1800", goal_cal="1300")
    assert small and small[0]["kind"] == "warn", small
    assert "28%" in small[0]["short"], small[0]["short"]

    _d2, big = _notes(gender="ذكر", weight="95", height="178",
                      tdee="3000", goal_cal="2500")
    assert big and big[0]["kind"] == "info", big
    assert "17%" in big[0]["short"], big[0]["short"]


def test_a_sensible_deficit_is_not_nagged_about():
    _d, notes = _notes(goal_cal="1500")
    assert notes and notes[0]["kind"] == "info", notes


# ── الكيلو في الأسبوع ───────────────────────────────────────────────

def test_the_note_says_what_the_deficit_means_in_kilos():
    """‏النسبة رقم مجرّد. الكيلو في الأسبوع هو اللي الدكتور والعميل
    بيتكلموا بيه."""
    _d, notes = _notes(goal_cal="1500")
    assert "كجم في الأسبوع" in notes[0]["short"], notes[0]["short"]


def test_losing_faster_than_one_percent_a_week_is_flagged():
    """‏أسرع من ١٪ من وزن الجسم أسبوعياً = جزء من النازل عضل."""
    _d, notes = _notes(weight="55", height="160", tdee="2200",
                       goal_cal="1300")
    assert notes and notes[0]["kind"] == "warn", notes
    assert "من وزنه" in notes[0]["short"] or "الآمن" in notes[0]["full"], notes[0]


def test_a_deep_and_fast_deficit_says_both_things():
    _d, notes = _notes(weight="55", height="160", tdee="2200",
                       goal_cal="1300")
    full = notes[0]["full"]
    assert "من الحرق" in full, full
    assert "في الأسبوع" in full, full


# ── حدود الملاحظة ───────────────────────────────────────────────────

def test_a_surplus_gets_no_deficit_note():
    _d, notes = _notes(goal_cal="2100", goal_type="muscle_gain")
    assert not notes, notes


def test_a_missing_tdee_says_nothing_instead_of_dividing_by_zero():
    _d, notes = _notes(tdee="")
    assert not notes, notes


def test_it_is_a_note_not_a_block():
    """‏الدكتور ممكن يكون عارف وقاصد. الورقة بتتولّد عادي."""
    data, notes = _notes(tdee="1800", goal_cal="1200")
    assert notes and notes[0]["kind"] == "warn", notes
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data, seed="g")
    assert len(plan) == 7, len(plan)
    assert all(d.get("total_cal") for d in plan), plan


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

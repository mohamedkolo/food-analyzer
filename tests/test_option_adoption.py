# -*- coding: utf-8 -*-
"""A named source-backed cooked option is OFFERED in the doctor preview, never applied automatically.
The doctor presses the button to replace that one entry in the draft; before that the written text is untouched.
Run with:  ADMIN_PASSWORD=pw123456 python3 tests/test_option_adoption.py"""
import os
import re
import sys

os.environ.setdefault("SECRET_KEY", "k")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_household_measures as H


def _buttons(html):
    return re.findall(r'class="use-option"[^>]*data-day="(\d+)" data-type="(\w+)"\s+data-old="([^"]*)" data-new="([^"]*)"', html)


def test_option_is_offered_then_adopted_only_on_the_doctor_action():
    c = H._staff()
    c.get("/preview")
    r = c.post("/edit_meal", data={"day_idx": 0, "meal_type": "lunch", "new_text": "150 جم صدر دجاج + 150 جم أرز أبيض مطبوخ"})
    assert r.get_json()["ok"], r.get_json()
    html = c.get("/preview").get_data(as_text=True)
    b = [x for x in _buttons(html) if x[0] == "0" and x[1] == "lunch"]
    assert b and b[0][2] == "150 جم صدر دجاج" and b[0][3] == "150 جم صدر دجاج مشوي بدون جلد (USDA 171477)", b
    assert "150 جم صدر دجاج + 150 جم أرز أبيض مطبوخ" in html            # the original text is still what is written
    # the doctor adopts it: only that entry changes
    new = "150 جم صدر دجاج مشوي بدون جلد (USDA 171477) + 150 جم أرز أبيض مطبوخ"
    assert c.post("/edit_meal", data={"day_idx": 0, "meal_type": "lunch", "new_text": new}).get_json()["ok"]
    html = c.get("/preview").get_data(as_text=True)
    assert not [x for x in _buttons(html) if x[0] == "0" and x[1] == "lunch"], "still offered after adoption"


def test_entry_carries_the_option_and_the_input_is_untouched():
    import plan_engine
    d = {"breakfast": "150 جم صدر دجاج", "lunch": "x", "dinner": "y", "total_cal": 1700, "total_p": 100}
    c = plan_engine.day_calc(d)
    ent = [e for s in c["slots"].values() for e in s["entries"]]
    assert ent and ent[0]["option"]["name"].endswith("(USDA 171477)"), ent
    assert d["breakfast"] == "150 جم صدر دجاج"                         # the input is untouched


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn(); print(f"  PASS  {name}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}"); failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

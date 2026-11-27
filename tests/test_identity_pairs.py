# -*- coding: utf-8 -*-
"""Identity pairs: (written item) -> (matched row, state, quantity, outcome).

Each case states what the matched table row is and whether the item may be
priced from it. "computed" here means "calculated from the matched table row".
It is NOT source-verified: that needs identity AND nutrient provenance.
Raw/dry/whole-grain words are state words: they change the nutrient basis, so
they are never ignored by the identity check.
Run with:  python3 tests/test_identity_pairs.py
"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "k")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meal_macros as MM

# (text, matched row name or None, expected: "priced" | "identity" | "nomatch")
PAIRS = [
    ("100 جم أرز نيء", "أرز أبيض نيء", "priced"),
    ("150 جم أرز ابيض مسلوق", "أرز أبيض مطبوخ", "priced"),
    ("200 مل حليب كامل الدسم", "حليب كامل الدسم", "priced"),
    ("40 جم شوفان خام", "شوفان خام", "priced"),
    ("150 جم دجاج مشوى", "دجاج مشوى", "priced"),     # row name states "مشوى"
    ("150 جم جبنة قريش", "جبنة قريش", "priced"),
    ("200 جم دجاج نيء", "صدر دجاج", "identity"),      # raw chicken vs the cooked row
    ("50 جم عدس جاف", "عدس", "identity"),             # dry lentils vs the cooked row
    ("150 جم كفتة دجاج", "كفتة مشوية", "identity"),    # chicken kofta vs generic kofta
    ("50 جم جبن حلوم", None, None),                   # halloumi: see below
    ("150 جم سمك هامور", None, None),                 # hamour: never the tilapia row
]


def _first(text):
    r = MM.macros(text)
    return r, r["items"][0]


def test_pairs_state_row_and_outcome():
    for text, row, outcome in PAIRS:
        if outcome is None:
            continue
        f = MM.find_food(text)
        assert f and f["n"] == row, (text, f and f["n"], row)
        r, i = _first(text)
        if outcome == "priced":
            assert r["complete"] and r["cal"] > 0 and not i.get("unresolved"), (text, r)
        else:
            assert not r["complete"] and r["cal"] == 0 and (i.get("unresolved") or "").startswith("identity"), (text, r)


def test_a_different_food_is_never_priced_from_a_row_with_another_name():
    for text in ("50 جم جبن حلوم", "150 جم سمك هامور"):
        f = MM.find_food(text)
        if f is None:
            continue
        r, i = _first(text)
        name = MM._norm(f["n"])
        head = "حلوم" if "حلوم" in text else "هامور"
        assert head in name or not r["complete"], (text, f["n"], r)


def test_state_words_are_not_ignored_by_the_identity_check():
    for w in ("نيء", "خام", "جاف", "كامل"):
        assert w not in MM._HARMLESS


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

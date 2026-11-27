# -*- coding: utf-8 -*-
"""Suggestions while typing a food name: only source-qualified named foods, read-only, staff only.
Run with:  ADMIN_PASSWORD=pw123456 python3 tests/test_food_suggest.py"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "k")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_household_measures as H
import food_suggest as F
import meal_option_foods as O
import food_provenance as P


def _names(q):
    return [i["text"] for i in F.suggest(q)]


def test_the_part_being_typed_is_the_last_item_without_its_amount():
    assert F.split_query("150 جم دجاج") == "دجاج"
    assert F.split_query("150 جم صدر دجاج + 200 جم ارز") == "ارز"
    assert F.split_query("2") == ""


def test_typing_chicken_offers_named_cooked_chicken_with_its_source_and_values():
    got = {i["text"]: i for i in F.suggest("150 جم دجاج")}
    opt = got["صدر دجاج مشوي بدون جلد (USDA 171477)"]
    row = next(f for f in O.OPTION_FOODS if f["fdc"] == 171477)
    assert opt["kind"] == "option" and opt["fdc"] == 171477 and "cooked" in opt["basis"]
    assert opt["per100"] == [row["cal"], row["p"], row["c"], row["f"]]
    assert "صدر دجاج بالجلد مطبوخ أو مشوى" in got and got["صدر دجاج بالجلد مطبوخ أو مشوى"]["kind"] == "verified"


def test_every_suggestion_is_source_qualified_and_nothing_unverified_is_offered():
    ok = {f["n"] for f in O.OPTION_FOODS} | set(P.REVIEWED)
    for q in ["دجاج", "ارز", "سمك", "بيض", "عدس", "حمص", "لبن", "موز", "تفاح", "لحم", "تونه", "جبن"]:
        for i in F.suggest(q):
            assert i["text"] in ok and i["fdc"] and i["usda"] and i["basis"], (q, i)
    assert F.suggest("تونه") == [] and F.suggest("جبن") == [], "unverified rows must not be suggested"


def test_every_suggestion_has_an_arabic_preparation_line():
    import re
    for r in F._catalog():
        assert F.BASIS_AR.get(r["basis"]), ("no Arabic wording for", r["text"], r["basis"])
        assert not re.search(r"[A-Za-z]", F.BASIS_AR[r["basis"]]), r["basis"]
    assert all(i["basis_ar"] and i["label"] for i in F.suggest("دجاج"))


def test_a_word_must_start_with_what_is_typed():
    assert _names("بيض") == ["بيض مسلوق صلب (USDA 173424)"], _names("بيض")    # not 'أبيض'


def test_the_endpoint_is_staff_only_and_changes_nothing():
    anon = H.A.app.test_client()
    r = anon.get("/api/food_suggest", query_string={"q": "دجاج"})
    assert r.status_code in (302, 401, 403), r.status_code
    c = H._staff()
    before = c.get("/preview").get_data(as_text=True)
    j = c.get("/api/food_suggest", query_string={"q": "150 جم دجاج"}).get_json()
    assert j["ok"] and j["q"] == "دجاج" and len(j["items"]) >= 2
    assert c.get("/preview").get_data(as_text=True) == before, "asking for suggestions changed the draft"


def test_editing_starts_from_the_stored_text_not_the_translated_display():
    import html as _h
    c = H._staff()
    stored = "100 جم موز + 200 جم حليب كامل الدسم"
    j = c.post("/edit_meal", data={"day_idx": 0, "meal_type": "breakfast", "new_text": stored}).get_json()
    assert j["ok"] and j["new_meal"] == stored and j["display"], j
    c.get("/lang/en")
    page = c.get("/preview").get_data(as_text=True)
    assert 'data-raw="%s"' % _h.escape(stored, quote=True) in page, "stored text missing from the English page"
    shown = page.split('data-type="breakfast"', 1)[1].split('cursor:text">', 1)[1].split("</div>", 1)[0]
    assert "banana" in shown and "موز" not in shown, shown          # display is translated, the stored record is not
    assert "storedMeal(this)" in page and "function showMeal" in page and "textContent.trim().replace(ob.dataset.old" not in page


def test_the_meal_list_cannot_widen_past_its_card_on_a_phone():
    page = H._staff().get("/preview").get_data(as_text=True)
    assert 'grid-template-columns:minmax(0,1fr);gap:8px' in page and ".meal-row{min-width:0;" in page


def test_the_preview_wires_suggestions_to_the_editor_and_the_add_box():
    html = H._staff().get("/preview").get_data(as_text=True)
    assert "function attachSuggest" in html and "attachSuggest(textarea)" in html
    assert "form.add-item input[name=\"text\"]" in html


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn(); print(f"  PASS  {name}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {str(e)[:600]}"); failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

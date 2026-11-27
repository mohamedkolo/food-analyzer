# -*- coding: utf-8 -*-
"""Source-verified variants offered while typing (meal_variant_foods): counts, identity words, resolution in the analysis, no rewriting.
Run with:  ADMIN_PASSWORD=pw123456 python3 tests/test_variant_foods.py"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "k")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import food_data
import food_provenance as P
import food_suggest as F
import meal_macros as M
import meal_option_foods as O
import meal_variant_foods as V
from collections import Counter


def test_exact_counts_by_family():
    got = Counter(f["family"] for f in V.VARIANT_FOODS)
    assert len(V.VARIANT_FOODS) == 132, len(V.VARIANT_FOODS)
    assert dict(got) == {"fish": 22, "chicken": 21, "milk": 14, "veg": 14, "rice": 9, "oil": 8, "fruit": 8, "egg": 7, "shellfish": 7,
                         "legumes": 7, "nuts": 6, "yogurt": 5, "liver": 4}, dict(got)


def test_every_variant_has_its_own_source_identity():
    names, ids = set(), set()
    for f in V.VARIANT_FOODS:
        assert f["n"].endswith("(USDA %d)" % f["fdc"]), f["n"]
        assert f["usda"] and f["usda"] == f["en"] and f["basis_ar"] and f["fdc"] not in ids and f["n"] not in names, f["n"]
        names.add(f["n"]); ids.add(f["fdc"])
    taken = {int(r[0]) for r in P.REVIEWED.values()} | {f["fdc"] for f in O.OPTION_FOODS}
    assert not (ids & taken), "a variant repeats an already offered source row"
    assert not (names & {f["n"] for f in food_data.FOODS}), "a variant name collides with a library row"


def test_values_are_plausible_per_100g_and_the_yogurt_rows_are_pinned():
    for f in V.VARIANT_FOODS:
        atwater = 4 * f["p"] + 4 * f["c"] + 9 * f["f"]
        assert 0 <= f["p"] + f["c"] + f["f"] <= 100.5, f["n"]
        assert abs(atwater - f["cal"]) <= max(0.25 * f["cal"], 25), (f["n"], atwater, f["cal"])
    want = {170886: (63, 5.25, 7.04, 1.55), 170887: (56, 5.73, 7.68, 0.18), 171304: (97, 9.0, 3.98, 5.0),
            170903: (73, 9.95, 3.94, 1.92), 170894: (59, 10.19, 3.6, 0.39)}
    got = {f["fdc"]: (f["cal"], f["p"], f["c"], f["f"]) for f in V.VARIANT_FOODS if f["family"] == "yogurt"}
    assert got == want, got


def test_identity_words_in_the_name_agree_with_the_usda_description():
    rules = [("raw", "نيّ"), ("smoked", "مدخن"), ("fried", "مقلي"), ("roasted", "مشوي"), ("skim", "خالي"), ("nonfat", "خالي"),
             ("Greek", "يوناني"), ("lowfat", "قليل"), ("low fat", "قليل"), ("whole", "كامل")]
    for f in V.VARIANT_FOODS:
        d = f["usda"]
        for en, ar in rules:
            if en in d.split(",")[-1] or (en in ("Greek",) and en in d) or (en in ("skim", "nonfat", "lowfat", "low fat") and en in d and f["family"] == "yogurt"):
                assert ar in f["n"], (f["n"], d, ar)
        if f["family"] == "yogurt":
            assert ("Greek" in d) == ("يوناني" in f["n"]), (f["n"], d)


def test_each_variant_is_suggested_when_its_family_word_is_typed_and_resolves_to_itself_in_the_analysis():
    for f in V.VARIANT_FOODS:
        word = f["n"].split()[0]
        offered = {i["text"] for i in F.suggest(word)}
        # 28 Nov 2026: raw cooked-weight rows (meat, poultry, fish, rice, dry legumes) are no longer offered; the engine still computes them
        _hidden = M.basis_of(f) == "raw" or (f.get("cat") in ("legume", "egg") and F.weigh_state(f["usda"], f["basis"]) == "raw")
        assert (f["n"] not in offered) if _hidden else (f["n"] in offered), (word, f["n"])
        row = M.find_food("100 جم " + f["n"])
        assert row and row["n"] == f["n"] and (row["cal"], row["p"], row["c"], row["f"]) == (f["cal"], f["p"], f["c"], f["f"]), f["n"]
        if _hidden:
            continue
        sug = next(i for i in F.suggest(f["n"]) if i["text"] == f["n"])
        assert sug["kind"] == "option" and sug["basis_ar"] == f["basis_ar"] and sug["per100"] == [f["cal"], f["p"], f["c"], f["f"]]


def test_typing_yogurt_offers_all_documented_variants_and_nothing_unverified():
    got = {i["fdc"] for i in F.suggest("زبادي")}
    assert got == {171284, 170886, 170887, 171304, 170903, 170894}, got
    for bad in ("زبادى يونانى كامل الدسم", "زبادى كامل الدسم", "زبادي بالفواكه"):
        assert bad not in {i["text"] for i in F.suggest("زبادى")} | {i["text"] for i in F.suggest("زبادي")}


def test_the_result_cap_never_hides_a_match_for_any_arabic_food_word_prefix():
    import re
    cat = F._catalog()
    ws = set()
    for r in cat:
        for h in [r["text"]] + [a for a in r["also"] if a]:
            for w in re.split(r"[\s(),\-/]+", M._norm(h)):
                if re.match(r"^[\u0600-\u06FF]+$", w):
                    ws.update(w[:k] for k in range(2, len(w) + 1))
    assert len(ws) > 500
    worst = max((F.total(w), w) for w in ws)
    assert worst[0] <= F.MAX, ("the cap would hide matches for", worst)
    for w in ("دجاج", "سمك", "حليب", "بيض", "ارز", "زبادي", "زيت", "لوز", "طماطم", "تفاح", "سلمون", "جمبري"):
        assert F.total(w) == len(F.suggest(w)), w
    assert len(F.suggest("USDA")) == F.MAX and F.total("USDA") > F.MAX, "English filler words are cut, and total() says so"


def test_cooked_variants_are_offered_and_raw_cooked_weight_rows_are_not():
    import re
    for q, fdcs, gone in (("دجاج", (171477,), (171474,)), ("سلمون", (171998,), (173686,)), ("ارز", (169704,), (168877,)), ("بيض", (173424,), (171287, 172183, 172184)),
                          ("حمص", (173757,), (173756,)), ("عدس", (172421,), (172420,))):
        got = {i["fdc"]: i for i in F.suggest(q)}
        assert all(x in got for x in fdcs), (q, fdcs)
        assert not any(x in got for x in gone), (q, gone)
    raw = [f for f in V.VARIANT_FOODS if re.search(r"\braw\b", f["usda"]) and "cooked" not in f["usda"]]
    assert raw and all("نيّ" in f["n"] or "نيء" in f["n"] for f in raw), [f["n"] for f in raw if "نيّ" not in f["n"]]


def test_the_grams_guidance_follows_the_selected_preparation_not_a_blanket_rule():
    import re
    rows = {r["fdc"]: r for r in F._catalog()}
    pins = {170393: "raw", 171477: "cooked", 168878: "cooked", 173424: "cooked",
            171998: "cooked", 173928: "cooked", 172421: "cooked", 171413: "as_sold", 170886: "as_sold", 173712: "as_sold", 168567: "as_sold"}
    for fdc, want in pins.items():
        assert rows[fdc]["weigh"] == want, (fdc, rows[fdc]["text"], rows[fdc]["weigh"])
    for r in rows.values():
        d = r["usda"].lower()
        assert (r["weigh"] == "cooked") == bool(re.search(r"\b(cooked|boiled|roasted|fried|stewed|poached|scrambled|omelet|steamed|prepared|baked|simmered)\b", d)), r["text"]
    for q in ("دجاج", "سلمون", "ارز", "بيض", "حمص", "زبادي", "زيت"):
        for i in F.suggest(q):
            if i["weigh"] == "raw":
                assert "نيّء" in i["grams_ar"] and "بعد الطبخ" not in i["grams_ar"] and "RAW" in i["grams_en"], i["text"]
            elif i["weigh"] == "cooked":
                assert "بعد الطبخ" in i["grams_ar"] and "AFTER cooking" in i["grams_en"], i["text"]
            else:
                assert "كما يُباع" in i["grams_ar"] and i["grams_en"] == "Type the grams as sold" and "غير مطبوخ" not in i["grams_ar"], i["text"]
    assert {i["weigh"] for i in F.suggest("ارز")} == {"cooked"}, "only cooked rice is offered (28 Nov 2026)"


def test_the_page_shows_the_guidance_per_choice_and_the_endpoint_carries_it():
    import test_household_measures as H
    c = H._staff()
    j = c.get("/api/food_suggest", query_string={"q": "150 جم ارز"}).get_json()
    assert j["ok"] and j["items"] and all(i["grams_ar"] and i["grams_en"] and i["weigh"] for i in j["items"]) and j["total"] == len(j["items"])
    page = c.get("/preview").get_data(as_text=True)
    assert "it.grams_ar" in page and "it.grams_en" in page
    import json
    assert json.dumps("حسب التحضير المكتوب تحت كل خيار")[1:-1].lower() in page.lower() or "حسب التحضير المكتوب تحت كل خيار" in page
    c.get("/lang/en")
    en = c.get("/preview").get_data(as_text=True)
    assert "as the preparation under each choice says" in en and "Type the amount in grams after cooking" not in en, "the blanket after-cooking hint is back"
    c.get("/lang/ar")


def test_library_rows_and_original_options_are_not_rewritten():
    pinned = {"زبادى كامل الدسم": (61.0, 3.5, 3.7, 2.3), "زبادى يونانى كامل الدسم": (132.0, 6.0, 4.5, 10.0),
              "زبادي يوناني": (97.0, 9.0, 3.6, 5.0), "حليب قليل الدسم": (42.0, 3.3, 4.9, 1.0)}
    rows = {f["n"]: (f["cal"], f["p"], f["c"], f["f"]) for f in food_data.FOODS}
    for n, v in pinned.items():
        assert rows[n] == v, n
    assert len(O.OPTION_FOODS) == 9 and len(P.REVIEWED) == 33 and len(food_data.FOODS) == 938


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

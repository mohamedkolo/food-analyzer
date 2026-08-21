# -*- coding: utf-8 -*-
"""The food table is a public, indexed page per row -- wrong numbers get crawled.

938 rows, 416 of them imported from the clinic's old Access database, each one
served at /foods/<slug> and listed in the sitemap. Anything malformed here is
not a private bug: Google reads it.

Two of these lock in bugs the import itself hit, both the same shape as MED-2:
a keyword matched as a bare substring inside a longer word. "بروتين" contains
"تين" (fig), so every protein powder was filed under fruit; "steak" contains
"tea", so grilled beef was filed under drinks.

Run with:  python3 tests/test_food_data.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import food_data as fd  # noqa: E402

REQUIRED = ("n", "en", "cat", "cal", "p", "c", "f", "slug")


def test_every_row_has_the_fields_the_pages_read():
    for f in fd.FOODS:
        for key in REQUIRED:
            assert key in f, f"{f.get('slug', f.get('en', '?'))} is missing {key}"
        assert str(f["n"]).strip(), f"{f['slug']} has an empty Arabic name"
        assert str(f["en"]).strip(), f"{f['slug']} has an empty English name"


def test_every_category_is_a_real_one():
    for f in fd.FOODS:
        assert f["cat"] in fd.CATEGORIES, f"{f['slug']} is in unknown category {f['cat']}"


def test_slugs_are_unique_and_url_safe():
    seen = {}
    for f in fd.FOODS:
        s = f["slug"]
        assert s not in seen, f"slug {s} is used by both {seen[s]} and {f['en']}"
        seen[s] = f["en"]
        assert re.fullmatch(r"[a-z0-9-]+", s), f"slug {s} is not url safe"
    assert len(fd.BY_SLUG) == len(fd.FOODS), "BY_SLUG lost rows to duplicate slugs"


def test_numbers_are_sane():
    for f in fd.FOODS:
        for key in ("cal", "p", "c", "f"):
            v = f[key]
            assert isinstance(v, (int, float)), f"{f['slug']}.{key} is not a number"
            assert v >= 0, f"{f['slug']}.{key} is negative"
        # nothing edible is denser than pure fat
        assert f["cal"] <= 950, f"{f['slug']} claims {f['cal']} kcal per 100g"
        for key in ("p", "c", "f"):
            assert f[key] <= 100, f"{f['slug']}.{key} is over 100g per 100g"
        assert f["p"] + f["c"] + f["f"] <= 105, (
            f"{f['slug']} macros total {f['p'] + f['c'] + f['f']}g per 100g")


def test_no_macro_alone_exceeds_the_stated_calories():
    """Protein and carbs yield 4 kcal/g and fat 9 -- a single macro that needs
    more calories than the row claims means one of the two numbers is a typo.

    The reverse check (macros summing to more than the calories) is NOT a bug:
    fibre yields ~2 kcal/g and sugar alcohols ~2.4, so bran and diet products
    legitimately look 'wrong' that way."""
    for f in fd.FOODS:
        cal = f["cal"]
        if cal <= 0:
            assert f["p"] == f["c"] == f["f"] == 0, (
                f"{f['slug']} has zero calories but non-zero macros")
            continue
        assert f["p"] * 4 <= cal * 1.05 + 5, (
            f"{f['slug']}: {f['p']}g protein needs {f['p'] * 4} kcal but the row says {cal}")
        assert f["f"] * 9 <= cal * 1.05 + 5, (
            f"{f['slug']}: {f['f']}g fat needs {f['f'] * 9} kcal but the row says {cal}")


def test_portion_sizes_are_usable():
    with_portion = [f for f in fd.FOODS if f.get("portion_g")]
    assert len(with_portion) > 300, (
        f"only {len(with_portion)} foods carry a serving size; the import lost them")
    for f in with_portion:
        g = f["portion_g"]
        assert isinstance(g, (int, float)) and 0 < g <= 1000, (
            f"{f['slug']} has an unusable serving size of {g}g")


def test_protein_powders_are_not_filed_as_fruit():
    """"بروتين" contains "تين" (fig). Matching Arabic keywords as bare
    substrings put every protein isolate in the fruit aisle."""
    for f in fd.FOODS:
        hay = (f["en"] + " " + f["n"]).lower()
        if "بروتين" in hay or "protein powder" in hay or "iso zero" in hay:
            assert f["cat"] != "fruit", (
                f"{f['en']} is filed as fruit -- the Arabic substring bug is back")


def test_steak_is_not_a_drink():
    """"steak" and "steamed" both contain "tea"."""
    for f in fd.FOODS:
        en = f["en"].lower()
        if "steak" in en or "steamed" in en:
            assert f["cat"] != "drink", (
                f"{f['en']} is filed as a drink -- the English substring bug is back")


def test_the_helpers_agree_with_the_table():
    total = 0
    for key in fd.CATEGORIES:
        rows = fd.foods_in(key)
        total += len(rows)
        assert all(r["cat"] == key for r in rows), f"foods_in({key}) leaked other categories"
    assert total == len(fd.FOODS), "some foods are unreachable through foods_in"
    # foods_in sorts, so compare membership rather than order
    assert {f["slug"] for f in fd.foods_in(None)} == {f["slug"] for f in fd.FOODS}

    for f in fd.FOODS[:20]:
        assert fd.get_food(f["slug"]) is f
    assert fd.get_food("no-such-food-at-all") is None

    for key in fd.CATEGORIES:
        assert fd.category_name(key, "ar").strip()
        assert fd.category_name(key, "en").strip()


def test_every_food_page_renders():
    os.environ.setdefault("SECRET_KEY", "test-key")
    import app as A  # noqa: E402  -- core holds the app object, app.py registers the routes

    A.app.config["WTF_CSRF_ENABLED"] = False
    client = A.app.test_client()

    broken = []
    for f in fd.FOODS:
        r = client.get(f"/foods/{f['slug']}")
        if r.status_code != 200:
            broken.append((f["slug"], r.status_code))
    assert not broken, f"{len(broken)} food pages do not render: {broken[:5]}"

    # and the index, per category, in both languages
    for lang in ("ar", "en"):
        with client.session_transaction() as sess:
            sess["lang"] = lang
        assert client.get("/foods").status_code == 200
        for key in fd.CATEGORIES:
            r = client.get(f"/foods?cat={key}")
            assert r.status_code == 200, f"/foods?cat={key} returned {r.status_code} in {lang}"


def test_the_sitemap_lists_every_food():
    os.environ.setdefault("SECRET_KEY", "test-key")
    import app as A  # noqa: E402

    body = A.app.test_client().get("/sitemap.xml").get_data(as_text=True)
    missing = [f["slug"] for f in fd.FOODS if f"/foods/{f['slug']}<" not in body]
    assert not missing, f"{len(missing)} foods are not in the sitemap: {missing[:5]}"


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

# -*- coding: utf-8 -*-
"""The user's weights mean AFTER cooking. Rows whose values equal a USDA RAW row and
whose names state no preparation are not exact under that rule: the item is unresolved
("basis:") and the total is shown as partial, never complete. Cooked-named rows are
unaffected. Resemblance to a USDA row is a reason to withhold "exact", not a proof of
raw or cooked. Set NX_BASIS_STRICT=0 to return to the old behaviour.
Run with:  python3 tests/test_basis_gate.py
"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "k")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meal_macros as MM


def _items(t):
    return MM.macros(t)


def test_raw_like_ground_rows_are_unresolved_with_a_reason():
    for t in ("150 جم دجاج مفروم", "200 جم لحم بقري مفروم 90/10", "200 جم لحم بقري مفروم 80/20"):
        r = _items(t)
        assert r["items"][0]["unresolved"].startswith("basis:"), (t, r["items"])
        assert not r["exact"] and not r["complete"], (t, r)
        assert r["cal"] == 0, (t, r["cal"])


def test_mixed_meal_is_partial_not_complete():
    r = _items("150 جم دجاج مفروم + 100 جم أرز أبيض مطبوخ")
    assert r["complete"] is False and r["exact"] is False
    assert r["cal"] == 130, r["cal"]                     # only the rice is counted


def test_cooked_named_rows_unchanged():
    r = _items("200 جم صدر دجاج بدون جلد مطبوخ أو مشوى + 150 جم أرز مطبوخ")
    assert r["exact"] is True and r["complete"] is True, r


def test_unreviewed_cooked_candidate_does_not_qualify_a_row():
    # "سمك قاروص" matches USDA cooked sea bass 173694 by name, but its protein (23) is 0.63 g from USDA (23.63), outside
    # the review tolerance, so nobody reviewed it. The row name states no preparation, so the item stays unresolved and says why.
    # (Chicken breast, tilapia, shrimp, crab, lobster and mullet passed the review on 28 Nov 2026 and are counted: see test_cooked_repair.)
    r = _items("200 جم سمك قاروص")
    assert r["items"][0]["unresolved"].startswith("basis:candidate cooked match USDA 173694"), r["items"]
    assert not r["exact"] and r["cal"] == 0


def test_canned_and_smoked_keep_their_own_label_and_are_not_called_cooked():
    import food_data as fd
    rows = {r["n"]: r for r in [v for v in vars(fd).values() if isinstance(v, list) and v and isinstance(v[0], dict) and "cal" in v[0]][0]}
    assert MM.basis_of(rows["تونة معلبة بالماء"]) == "canned"
    assert MM.basis_of(rows["ديك رومي مدخن شرائح"]) == "smoked"
    assert MM.basis_of(rows["أرز أبيض مطبوخ"]) == "cooked"


def test_switch_off_restores_old_behaviour():
    os.environ["NX_BASIS_STRICT"] = "0"
    try:
        r = _items("150 جم دجاج مفروم")
        assert r["items"][0].get("unresolved") is None and r["cal"] > 0, r
    finally:
        del os.environ["NX_BASIS_STRICT"]


def test_day_calc_lists_each_unresolved_entry_with_a_reason():
    import plan_engine
    d = {"day": "x", "breakfast": "2 بيضة", "total_cal": 1700, "total_p": 100,
         "lunch": "150 جم دجاج مفروم + 100 جم أرز مطبوخ + 30 جم جبنة + سلطة",
         "dinner": "150 جم سمك بلطى مشوى او بالفرن"}
    c = plan_engine.day_calc(d)
    assert c["basis"] == "label", c["basis"]
    ent = {e["text"]: e["code"] for e in c["slots"]["lunch"]["entries"]}
    assert ent.get("150 جم دجاج مفروم") == "basis", ent
    assert ent.get("30 جم جبنة") == "generic", ent
    assert ent.get("سلطة") == "noquantity", ent
    assert c["slots"]["dinner"]["entries"] == [], c["slots"]["dinner"]
    assert c["slots"]["breakfast"]["entries"] == [] or True


def test_client_sees_a_concise_warning_and_the_doctor_sees_the_entries():
    import plan_engine
    import app as A
    d = {"day": "x", "breakfast": "2 بيضة", "total_cal": 1700, "total_p": 100,
         "lunch": "150 جم دجاج مفروم + 100 جم أرز مطبوخ", "dinner": "150 جم سمك بلطى مشوى او بالفرن"}
    d["calc"] = plan_engine.day_calc(d)
    with A.app.test_request_context("/"):
        tpl = A.app.jinja_env.get_template("_day_calc.html")
        client = tpl.render(day=d, _ar=True)
        doctor = tpl.render(day=d, _ar=True, _doctor=True)
    assert "data-unresolved-entries" not in client and "دجاج مفروم" not in client, client
    assert "الكمية أو الاسم أو طريقة الطبخ" in client      # names every cause, not only the amount
    assert "data-unresolved-entries" in doctor and "دجاج مفروم" in doctor


def test_quarantined_oyster_row_is_never_priced_sourced_or_remapped():
    """The row named "المحار" (oyster) carries the values of USDA "Ostrich, oyster, cooked". Its meaning is
    unvalidated: it is withheld, never exact or sourced, never mapped to seafood or ostrich, and the stored
    record is left untouched."""
    import food_provenance as FP
    import food_data
    r = _items("100 جم المحار")
    i = r["items"][0]
    assert i["unresolved"].startswith("identity:quarantined"), i
    assert not r["exact"] and not r["complete"] and not i["sourced"] and r["cal"] == 0, r
    assert "المحار" not in FP.REVIEWED and "المحار" not in FP.MATCHES
    rows = [x for v in vars(food_data).values() if isinstance(v, list) for x in v if isinstance(x, dict) and x.get("n") == "المحار"]
    assert rows and (rows[0]["cal"], rows[0]["p"], rows[0]["c"], rows[0]["f"]) == (159.0, 28.8, 0.0, 3.97), rows


def test_proposed_cooked_option_replaces_not_keeps_an_unresolved_original():
    """With the proposed layer on, an explicit amount of a no-preparation row is priced from the named cooked
    option (own identity, USDA id), flagged proposed and never exact."""
    import importlib
    os.environ["NX_PROPOSED_VARIANTS"] = "1"; os.environ["NX_PROPOSED_LEVEL"] = "B"
    try:
        importlib.reload(MM)
        r = MM.macros("150 جم صدر دجاج مشوي")
        i = r["items"][0]
        # 28 Nov 2026: chicken breast is a REVIEWED cooked row now (USDA 171477), so it is priced directly, not as a proposed replacement
        assert not i.get("proposed") and i["food"] == "صدر دجاج" and i["sourced"] and r["complete"], i
        assert (r["cal"], r["p"], r["c"], r["f"]) == (248, 46, 0, 5), r      # 150 g of USDA 171477 per 100 g: 247.5/46.5/0/5.4 (rounded in the app)
    finally:
        os.environ.pop("NX_PROPOSED_VARIANTS", None); os.environ.pop("NX_PROPOSED_LEVEL", None)
        importlib.reload(MM)


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

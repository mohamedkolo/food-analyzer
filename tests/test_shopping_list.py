# -*- coding: utf-8 -*-
"""‏قايمة مشتريات الأسبوع، من جرامات الجدول.

‏الجدول بيقول "صدر دجاج ١٦٠جم" أربع مرات و"فول ١٠٠جم" تلاتة. العميل
بيمسك الورقة ويروح السوق ويقف: يشتري كام؟ الجمع ده شغل على ٢٨ خانة،
فبيشتري بالتخمين -- أكتر فيبوظ، أو أقل فالجدول يقف نص الأسبوع.

‏والحاجة الوحيدة اللي محتاجة حرص هنا: meal_macros بترجّع الكمية
**ومصدرها**. "grams" يعني الرقم مكتوب، و"count" عدد × وزن الوحدة،
و"default" يعني **حصة افتراضية** -- الصنف مالوش رقم خالص.

‏والتالت مينفعش يتجمع. "قرفة" و"ليمون" مالهمش كمية مكتوبة، فلو جمعنا
لهم الحصة الافتراضية على سبع أيام القايمة هتقول "قرفة ٣٥ جم" -- رقم
إحنا اللي اخترعناه، والعميل هيشتري على أساسه. نفس قاعدة الباركود:
خانة فاضية أحسن من رقم مخترع.

Run with:  python3 tests/test_shopping_list.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_shopping_test.db"

import app as A            # noqa: E402
import shopping_list       # noqa: E402


def _day(**meals):
    d = {"day": "الاحد", "meal_labels": {}, "meal_emojis": {},
         "total_cal": 1600, "total_p": 90}
    d.update(meals)
    return d


def _flat(out):
    return {it["name"]: it for g in out["groups"] for it in g["items"]}


def _qty_grams(text):
    """‏"1.5 كجم" -> 1500، "450 جم" -> 450"""
    import re
    m = re.search(r"([\d.]+)\s*(كجم|جم|kg|g)", str(text))
    if not m:
        return None
    val = float(m.group(1))
    return val * 1000 if m.group(2) in ("كجم", "kg") else val


# ── الجمع ────────────────────────────────────────────────────────────

def test_the_same_food_across_days_is_added_up():
    """‏ده اللي الصفحة كلها موجودة عشانه."""
    plan = [_day(lunch="🍗 صدر دجاج مشوي 100جم"),
            _day(lunch="🍗 صدر دجاج مشوي 200جم"),
            _day(dinner="🍗 صدر دجاج مشوي 150جم")]
    row = _flat(shopping_list.build(plan)).get("صدر دجاج")
    assert row, _flat(shopping_list.build(plan)).keys()
    assert _qty_grams(row["qty"]) >= 450, row
    assert row["days"] == 3, row


def test_different_wordings_of_one_food_land_on_one_line():
    """‏"صدر دجاج مشوي" و"شرائح دجاج" الاتنين دجاج. لو اتكتبوا سطرين،
    العميل هيشتري مرتين."""
    plan = [_day(lunch="🍗 صدر دجاج مشوي 100جم"),
            _day(lunch="🍗 صدر دجاج مسلوق 100جم")]
    rows = _flat(shopping_list.build(plan))
    chicken = [k for k in rows if "دجاج" in k]
    assert len(chicken) == 1, chicken


def test_a_week_of_small_amounts_becomes_a_shopping_amount():
    """‏١٠٤٧ جم مش كمية حد بيشتريها -- بيشتري كيلو."""
    plan = [_day(lunch="🍗 صدر دجاج مشوي 149جم") for _ in range(7)]
    row = _flat(shopping_list.build(plan))["صدر دجاج"]
    assert "كجم" in row["qty"], row
    grams = _qty_grams(row["qty"])
    assert grams >= 1043, "‏التقريب نزل تحت اللي الجدول محتاجه: %s" % row
    assert grams <= 1200, row


def test_the_rounding_never_goes_below_what_the_plan_needs():
    """‏ناقص ٥٠ جم في آخر الأسبوع = وجبة ناقصة. وزيادة ٥٠ جم = ولا حاجة."""
    for grams in (30, 110, 260, 515, 1010, 1999):
        plan = [_day(lunch="🍚 أرز أبيض مطبوخ %dجم" % grams)]
        row = _flat(shopping_list.build(plan))
        got = _qty_grams(list(row.values())[0]["qty"])
        assert got >= grams, "‏%d اتقرّب لـ%s" % (grams, got)
        assert got - grams <= 100, "‏%d اتقرّب لـ%s -- زيادة كتير" % (grams, got)


# ── اللي مينفعش يتجمع ───────────────────────────────────────────────

def test_a_food_with_no_written_amount_gets_no_invented_number():
    """‏"قرفة" مالهاش كمية. الحصة الافتراضية × ٧ أيام = رقم مخترع."""
    plan = [_day(breakfast="🥣 شوفان 40جم + قرفة") for _ in range(7)]
    out = shopping_list.build(plan)
    rows = _flat(out)
    assert not any("قرفة" in k for k in rows), (
        "‏القايمة حطّت كمية للقرفة: %s" % rows)
    assert any("قرفة" in x["name"] for x in out["loose"]), out["loose"]


def test_a_food_listed_by_name_is_not_also_listed_with_a_quantity():
    """‏زيت الزيتون بييجي بكمية في يوم وبالافتراضي في يوم -- كان بيتعرض
    مرتين، مرة برقمه ومرة تحت "حسب الحاجة"."""
    plan = [_day(lunch="🥗 سلطة خضراء 150جم + 🫒 زيت زيتون 10جم"),
            _day(lunch="🥗 سلطة خضراء 150جم + 🫒 زيت زيتون")]
    out = shopping_list.build(plan)
    named = {x["name"] for x in out["loose"]}
    assert not (set(_flat(out)) & named), set(_flat(out)) & named


def test_an_emoji_on_its_own_is_not_an_item():
    """‏٣٥ وجبة في القاعدة آخرها إيموجي لوحده ("... + 🍋")."""
    plan = [_day(lunch="🐟 سمك مشوي 150جم + 🍋")]
    out = shopping_list.build(plan)
    for bucket in ("loose", "unknown"):
        for x in out[bucket]:
            assert x["name"].strip() not in ("🍋", ""), (bucket, x)


def test_a_food_outside_the_table_is_surfaced_not_dropped():
    """‏لو اتشال في صمت، العميل هيكتشف النقص في السوق."""
    plan = [_day(lunch="🛸 حاجة مش موجودة في أي جدول 200جم")]
    out = shopping_list.build(plan)
    assert out["unknown"], out


# ── العدد مقابل الوزن ───────────────────────────────────────────────

def test_eggs_are_counted_not_weighed():
    """‏"٤ بيضات" أوضح من "٢٢٠ جم بيض" في السوق."""
    plan = [_day(breakfast="🥚 بيض مسلوق 3"), _day(breakfast="🥚 بيض مسلوق 2")]
    rows = _flat(shopping_list.build(plan))
    egg = [v for k, v in rows.items() if "بيض" in k]
    assert egg, rows
    assert "حبة" in egg[0]["qty"], egg[0]


def test_grams_stay_grams_for_things_sold_by_weight():
    plan = [_day(lunch="🍗 صدر دجاج مشوي 200جم")]
    row = _flat(shopping_list.build(plan))["صدر دجاج"]
    assert "جم" in row["qty"] and "حبة" not in row["qty"], row


# ── الشكل ────────────────────────────────────────────────────────────

def test_items_are_grouped_the_way_a_shop_is_walked():
    plan = [_day(breakfast="🥚 بيض مسلوق 2 + 🍞 خبز أسمر 60جم",
                 lunch="🍗 صدر دجاج مشوي 150جم + 🥗 سلطة خضراء 150جم")]
    out = shopping_list.build(plan)
    titles = [g["title"] for g in out["groups"]]
    assert len(titles) >= 2, titles
    assert len(set(titles)) == len(titles), "‏مجموعة اتكررت: %s" % titles


def test_an_empty_plan_does_not_throw():
    for empty in ([], None, [{}], [{"day": "الاحد"}]):
        out = shopping_list.build(empty)
        assert out["groups"] == [], out


def test_the_english_list_is_english():
    plan = [_day(lunch="🍗 صدر دجاج مشوي 150جم")]
    out = shopping_list.build(plan, lang="en")
    import re
    for g in out["groups"]:
        assert not re.search(r"[؀-ۿ]", g["title"]), g["title"]
        for it in g["items"]:
            assert not re.search(r"[؀-ۿ]", it["name"]), it


# ── الصفحة ───────────────────────────────────────────────────────────

def _page():
    """‏الصفحة الحقيقية. بتقرا المسودّة، فلازم تتكتب الأول **جوّه نفس
    جلسة العميل** -- set_draft بتحط رقم المسودّة في الـsession."""
    import draft_store
    import plan_engine
    import zigzag
    data = {"name": "ريم", "age": "34", "gender": "انثى", "height": "160",
            "weight": "88", "tdee": "2100", "goal_cal": "1600",
            "goal_type": "weight_loss", "culture": "مصري",
            "diet_plan_type": "standard", "protein_per_kg": "1.6",
            "fat_pct_cal": "30", "symptoms": [], "allergies": [],
            "zigzag_mode": "classic", "activity_level": "light"}
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
    c = A.app.test_client()
    with c.session_transaction() as sess:
        sess["uid"] = 1
        sess["role"] = "admin"
        sess["lang"] = "ar"
    # ‏مفتاح الجلسة اسمه "draft" مش "draft_id" (draft_store.KEY) --
    # أول نسخة كتبت الاسم التاني، فالصفحة ماشافتش المسودّة ورجّعت
    # تحويل لـ/generate، والاختبار كان بيقول إن الصفحة مش شغالة.
    with A.app.test_request_context("/"):
        from flask import session as _s
        _s["uid"] = 1
        draft_store.set_draft(data, plan, user_id=1)
        token = _s.get(draft_store.KEY)
    assert token, "‏المسودّة ماخدتش رقم"
    with c.session_transaction() as sess:
        sess[draft_store.KEY] = token
    return c.get("/shopping")


def test_the_page_renders_the_list():
    r = _page()
    assert r.status_code == 200, "‏الصفحة ردّت %s" % r.status_code
    html = r.get_data(as_text=True)
    assert "قايمة المشتريات" in html, html[:300]
    assert "دواجن" in html or "نشويات" in html, (
        "‏مافيش ولا مجموعة على الصفحة")


def test_the_page_prints_a_real_quantity():
    """‏صفحة فيها أسماء من غير كميات مش قايمة مشتريات."""
    import re
    html = _page().get_data(as_text=True)
    body = html[html.index("sl-grid"):]
    assert re.search(r'class="q">\s*[\d.]+\s*(?:جم|كجم|حبة)', body), (
        "‏مافيش أي كمية مطبوعة")


def test_the_preview_offers_the_list():
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "templates", "preview.html"),
            encoding="utf-8") as f:
        html = f.read()
    assert "/shopping" in html, "‏مافيش زرار للقايمة في المعاينة"


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

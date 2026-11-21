# -*- coding: utf-8 -*-
"""‏جنب كل صنف في الجدول مكياله: "ارز بني 150جم (≈ كوب)".

‏صاحب المشروع: "عايز كل حاجة في الجدول تتكتب قد إيه جنبها بمكيال، يعني
تعادل كام معلقة أو كوب". العميل مش معاه ميزان؛ "150جم" مش تعليمة يقدر
ينفّذها في المطبخ.

‏measures.py كان مكتوب من زمان ومعاه فلتر في core -- ومحدش استخدمه.
ولما اتجرّب طلع فيه عيب كان هيبوّظ الورقة لو اتوصّل:

    "زيت زيتون 1 ملعقة"  ->  "زيت زيتون 1 مل (≈ ملعقة صغيرة)عقة"

‏كان بيقرا "مل" اللي جوه "ملعقة" كأنها مليلتر، وبيقطع الكلمة.

‏اللي الاختبارات دي بتحرسه:
  ‏- الجرامات والملّي بياخدوا مكيال، والكلمة اللي بعدهم ماتتقطعش.
  ‏- الصنف المكتوب بالعدد أو بالملعقة مابياخدش مكيال تاني فوقه.
  ‏- المكيال بيظهر على ورقة العميل (اللينك والـPDF) وفي المعاينة،
    **والنص المتخزّن مابيتغيّرش** -- المكيال عرض بس.

Run with:  python3 tests/test_household_measures.py
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_measures_test.db"

import app as A            # noqa: E402
import core                # noqa: E402
import draft_store         # noqa: E402
import measures            # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False

FORM = {
    "action": "generate", "name": "عميل المكاييل", "phone": "01044443333",
    "age": "32", "gender": "ذكر", "height": "176", "weight": "95",
    "tdee": "2350", "goal_cal": "1750", "goal_type": "weight_loss",
    "culture": "مصري", "diet_plan_type": "standard", "activity_mult": "1.55",
    "protein_per_kg": "1.8", "fat_pct_cal": "30", "zigzag_mode": "off",
}
MEAL = "🍚 ارز بني 150جم + 🫒 زيت زيتون 1 ملعقة + 🍌 موز 1"


# ── التحويل ─────────────────────────────────────────────────────────

def test_grams_and_ml_get_a_household_measure():
    assert measures.annotate("🍚 ارز بني 150جم") == "🍚 ارز بني 150جم (≈ كوب)"
    assert "(≈" in measures.annotate("🥛 حليب 200مل")


def test_a_spoon_is_not_read_as_millilitres():
    """‏"مل" جوه "ملعقة" -- الكلمة كانت بتتقطع نصين على ورقة العميل."""
    assert measures.annotate("🫒 زيت زيتون 1 ملعقة") == "🫒 زيت زيتون 1 ملعقة"
    assert measures.annotate("🥜 طحينة 2 ملعقة كبيرة") == "🥜 طحينة 2 ملعقة كبيرة"


def test_a_counted_item_is_not_measured_twice():
    """‏"موز 1 (≈ حبة)" بتقول نفس الحاجة مرتين."""
    for text in ("🍌 موز 1", "🥚 بيض مسلوق 2", "🍞 توست 2"):
        assert measures.annotate(text) == text, measures.annotate(text)


def test_a_snacks_written_calories_stay_where_they_were():
    assert measures.annotate("🍎 تفاح 150جم - 78 kcal") == "🍎 تفاح 150جم (≈ حبة) - 78 kcal"


def test_the_whole_meal_keeps_its_shape():
    got = measures.annotate(MEAL)
    assert got == "🍚 ارز بني 150جم (≈ كوب) + 🫒 زيت زيتون 1 ملعقة + 🍌 موز 1", got


# ── على الورقة ──────────────────────────────────────────────────────

def _staff():
    c = A.app.test_client()
    c.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                           "password": "pw123456"})
    c.post("/generate", data=FORM)
    assert c.post("/edit_meal", data={"day_idx": 0, "meal_type": "breakfast",
                                      "new_text": MEAL}).get_json()["ok"]
    return c


def _stored(c):
    with c.session_transaction() as s:
        ident = s.get(draft_store.KEY)
    row = core.db_row("SELECT * FROM plan_drafts WHERE id=?", (ident,))
    return json.loads(row["plan_json"])[0]["breakfast"]


def test_the_clients_link_shows_the_measures():
    c = _staff()
    token = c.post("/api/plan-link").get_json()["url"].rstrip("/").rsplit("/", 1)[-1]
    body = A.app.test_client().get("/p/" + token).get_data(as_text=True)
    assert "ارز بني 150جم (≈ كوب)" in body, "اللينك اللي بيوصل للعميل مافيهوش المكيال"
    assert "زيت زيتون 1 ملعقة" in body and ")عقة" not in body


def test_the_printed_sheet_shows_the_measures():
    import plan_engine
    c = _staff()
    with c.session_transaction() as s:
        ident = s.get(draft_store.KEY)
    row = core.db_row("SELECT * FROM plan_drafts WHERE id=?", (ident,))
    data, plan = json.loads(row["data_json"]), json.loads(row["plan_json"])
    with A.app.test_request_context():
        from flask import session
        session["lang"] = "ar"
        html = plan_engine.plan_html(data, plan)
    # ‏الـPDF بيكتب الكمية بخط عريض: "ارز بني <b>150جم</b> (≈ كوب)"
    assert re.search(r"ارز بني <b>150جم</b> \(≈ كوب\)", html), "الـPDF مافيهوش المكيال"
    # ‏ونفس فخ "مل" كان في الخط العريض بتاع الـPDF من قبل المكاييل:
    # "زيت زيتون <b>1 مل</b>عقة" -- الكلمة مقطوعة في كل ورقة مطبوعة.
    assert "زيت زيتون <b>1 ملعقة</b>" in html, re.findall(r"زيت زيتون[^<]*<b>[^<]*</b>\S*", html)


def test_the_preview_shows_the_measure_beside_the_amount():
    c = _staff()
    html = c.get("/preview").get_data(as_text=True)
    m = re.search(r'<div class="qty-row"[^>]*data-day="0"[^>]*data-type="breakfast"[^>]*>(.*?)</div>\s*<!--/qty-row-->',
                  html, re.S)
    assert m and re.search(r'class="qty-measure"[^>]*>\s*≈ كوب', m.group(1)), m and m.group(1)[:400]


def test_the_stored_meal_never_carries_the_measure():
    """‏المكيال عرض بس. لو اتخزّن، أي تعديل بعده كان هيلاقي "(≈ كوب)" جوه
    النص -- ورقم جوه قوس ممكن يتقري كمية."""
    c = _staff()
    c.get("/preview")
    token = c.post("/api/plan-link").get_json()["url"].rstrip("/").rsplit("/", 1)[-1]
    A.app.test_client().get("/p/" + token)
    assert _stored(c) == MEAL, _stored(c)


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
        except Exception as e:
            print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

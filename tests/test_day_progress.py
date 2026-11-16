# -*- coding: utf-8 -*-
"""‏دواير الماكروز ونصايح النهارده في "خطتي".

‏العميل بيشوف: سعرات / بروتين / كارب / دهون -- المتاكل قصاد المستهدف من
خطة الدكتور. وتحتهم تلميح من الخطة نفسها ("فاضلك ٤٠ جم بروتين: كمّل الغدا").

‏اللي الاختبارات دي بتحرسه:
  ‏- المستهدف هو مجموع اليوم اللي الدكتور كتبه، مش رقم محسوب من برّه.
  ‏- نصيب كل وجبة من الجدول، بس مجموع الأنصبة = مجموع اليوم بالظبط.
  ‏- الوجبة المتخطّية ("ماكلتهاش") مش متاكلة ومش فاضلة.
  ‏- النصايح كلها من الخطة: أرقام ووجبات فيها، من غير نصيحة أكل جديدة.

Run with:  python3 tests/test_day_progress.py
"""

import json
import os
import re
import sys
from datetime import datetime

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_day_progress.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A              # noqa: E402
import day_progress as DP    # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
ARABIC = re.compile(r"[؀-ۿ]")

DAY = {
    "day": "الأحد",
    "breakfast": "بيض مسلوق 2 + عيش بلدي 1 رغيف",
    "lunch": "صدر دجاج مشوي 200جم + أرز أبيض مطبوخ 150جم",
    "snack": "زبادي 150جم",
    "dinner": "جبن قريش 100جم + خيار",
    "total_cal": 1600, "total_p": 120, "total_c": 150, "total_f": 50,
}
KEYS = ["breakfast", "lunch", "snack", "dinner"]
LABELS = {"breakfast": "الفطار", "lunch": "الغدا", "snack": "سناك", "dinner": "العشا"}


def _b(checked=(), skipped=(), hour=13, is_ar=True, day=DAY):
    return DP.build(day, KEYS, set(checked), set(skipped), LABELS, is_ar=is_ar, hour=hour)


# ═══ الأرقام ═══

def test_target_is_the_days_own_totals():
    t = _b()["target"]
    assert (t["cal"], t["p"], t["c"], t["f"]) == (1600, 120, 150, 50)


def test_a_zigzag_day_uses_its_own_target():
    day = dict(DAY, target_cal=1400, target_p=115, target_c=120, target_f=45)
    t = _b(day=day)["target"]
    assert (t["cal"], t["p"], t["c"], t["f"]) == (1400, 115, 120, 45)


def test_meal_shares_add_up_to_the_day_exactly():
    meals = _b()["meals"]
    for k in ("cal", "p", "c", "f"):
        assert sum(m[k] for m in meals.values()) == DAY["total_" + k], k


def test_the_bigger_meal_gets_the_bigger_share():
    meals = _b()["meals"]
    assert meals["lunch"]["p"] > meals["snack"]["p"]
    assert meals["lunch"]["cal"] > meals["dinner"]["cal"]


def test_eaten_is_the_sum_of_ticked_meals():
    r = _b(checked={"breakfast", "lunch"})
    m = r["meals"]
    assert r["eaten"]["cal"] == m["breakfast"]["cal"] + m["lunch"]["cal"]
    assert r["eaten"]["p"] == m["breakfast"]["p"] + m["lunch"]["p"]
    assert _b()["eaten"]["cal"] == 0


def test_an_old_plan_without_carbs_and_fat_reads_them_from_the_food():
    day = {k: v for k, v in DAY.items() if k not in ("total_c", "total_f")}
    t = _b(day=day)["target"]
    assert t["cal"] == 1600 and t["p"] == 120
    assert t["c"] and t["f"]          # ‏من جدول الأكل


def test_a_day_with_no_numbers_shows_no_rings():
    day = {k: v for k, v in DAY.items() if not k.startswith("total_")}
    day = {k: ("حاجة مش معروفة" if k in KEYS else v) for k, v in day.items()}
    assert _b(day=day) is None


# ═══ النصايح ═══

def test_all_done_says_so():
    hints = _b(checked=set(KEYS))["hints"]
    assert any("خلّصت" in h for h in hints), hints


def test_what_is_left_is_spelled_out_with_the_plans_numbers():
    r = _b(checked={"breakfast"})
    left_p = r["target"]["p"] - r["eaten"]["p"]
    left_cal = r["target"]["cal"] - r["eaten"]["cal"]
    text = " ".join(r["hints"])
    assert str(left_p) in text and str(left_cal) in text, text


def test_the_heaviest_protein_meal_left_is_named():
    text = " ".join(_b(checked={"breakfast"})["hints"])
    assert "الغدا" in text, text


def test_a_skipped_meal_is_neither_eaten_nor_left():
    r = _b(checked={"breakfast"}, skipped={"lunch"})
    assert r["eaten"]["cal"] == r["meals"]["breakfast"]["cal"]
    assert "الغدا" not in " ".join(r["hints"])


def test_late_with_meals_left_asks_to_mark_skipped():
    text = " ".join(_b(checked={"breakfast"}, hour=22)["hints"])
    assert "ماكلتهاش" in text, text


def test_english_hints_are_english():
    r = _b(checked={"breakfast"}, is_ar=False)
    labels_en = {"breakfast": "Breakfast", "lunch": "Lunch", "snack": "Snack", "dinner": "Dinner"}
    r = DP.build(DAY, KEYS, {"breakfast"}, set(), labels_en, is_ar=False, hour=13)
    assert not ARABIC.search(" ".join(r["hints"])), r["hints"]


# ═══ الصفحة ═══

def _client_with_plan():
    A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) VALUES (?,?,?,'client',1,?)",
             ("Rana", "rana@x.test", generate_password_hash("pw123456"), datetime.now()))
    uid = A.db_row("SELECT id FROM users WHERE email='rana@x.test'")["id"]
    plan = {"plan": [DAY] * 7, "data": {"diet_plan_type": "standard"}}
    A.db_run("INSERT INTO plan_requests (client_id,client_name,status,plan_data,updated_at) VALUES (?,?,'approved',?,?)",
             (uid, "Rana", json.dumps(plan), datetime.now()))
    return uid


UID = _client_with_plan()


def _as(uid, lang="ar"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = uid
        s["lang"] = lang
    return c


def test_my_plan_shows_four_rings_with_targets():
    html = _as(UID).get("/my-plan").get_data(as_text=True)
    rings = re.findall(r'class="dp-ring"[^>]*data-k="(\w+)"[^>]*data-target="(\d+)"', html)
    assert [k for k, _ in rings] == ["cal", "p", "c", "f"], rings
    assert dict(rings)["cal"] == "1600"


def test_ticking_a_meal_moves_the_rings():
    c = _as(UID)
    before = c.get("/my-plan/progress").get_json()
    assert before["eaten"]["cal"] == 0
    c.post("/track/meal", data={"meal_key": "lunch", "checked": "1"})
    after = c.get("/my-plan/progress").get_json()
    assert after["eaten"]["cal"] > 0 and after["hints"]


def test_progress_needs_a_session():
    r = A.app.test_client().get("/my-plan/progress")
    assert r.status_code in (302, 401)


if __name__ == "__main__":
    tests = [(n, f) for n, f in list(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, "--", repr(e)[:300])
    print("\n%d passed, %d failed" % (len(tests) - failed, failed))
    sys.exit(1 if failed else 0)

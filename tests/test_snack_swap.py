# -*- coding: utf-8 -*-
"""‏السناك بيتبدّل زي باقي الوجبات -- ومن طابور الأسناك، مفلتر على حالة العميل.

‏صاحب المشروع: "عايز تعمل تغيير في الأسناك يبقى قابل للتغيير". صفحة
المعاينة كانت بتحط زرار التبديل والقايمة جنب الفطار والغدا والعشا بس؛
السناك كان يتغيّر بالكتابة بس.

‏ولما اتبصّ على ده طلع اللي أخطر منه: **المولّد نفسه** مكانش بيعدّي
الأسناك على الفلترة الطبية. الفطار والغدا والعشا بيعدّوا على
filter_by_conditions، والأسناك على المرفوضات بس. فعميل عنده فشل كلوي
خد كيوي، وعميل عنده حساسية لاكتوز خد جبن قريش -- في ١٠ خطط من ١٠ اتجرّبوا.
الصفحة كانت بتعلّم عليهم بالأحمر، بس اتولّدوا.

‏وكمان زرار التبديل العشوائي كان بيقرا snack1/snack2 كخانة فطار، فلو
اتضاف من غير ما يتصلّح كان هيحط طبق فطار كامل مكان سناك.

Run with:  python3 tests/test_snack_swap.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_snack_swap_test.db"

import app as A               # noqa: E402
import core                   # noqa: E402
import draft_store            # noqa: E402
import plan_engine            # noqa: E402
import plan_tools as T        # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False

KIDNEY = "الفشل الكلوي المزمن"
LACTOSE = "حساسية اللاكتوز"
FORM = {
    "action": "generate", "name": "عميل الأسناك", "phone": "01066665555",
    "age": "40", "gender": "ذكر", "height": "176", "weight": "95",
    "tdee": "2350", "goal_cal": "1750", "goal_type": "weight_loss",
    "culture": "مصري", "diet_plan_type": "standard", "activity_mult": "1.55",
    "protein_per_kg": "1.2", "fat_pct_cal": "30", "zigzag_mode": "off",
}
SNACK_KEYS = ("snack", "snack1", "snack2")


def _staff(**over):
    c = A.app.test_client()
    c.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                           "password": "pw123456"})
    r = c.post("/generate", data=dict(FORM, **over))
    assert r.status_code in (200, 302), r.status_code
    return c


def _draft(c):
    with c.session_transaction() as s:
        ident = s.get(draft_store.KEY)
    row = core.db_row("SELECT * FROM plan_drafts WHERE id=?", (ident,))
    return json.loads(row["data_json"]), json.loads(row["plan_json"])


def _text(m):
    return m if isinstance(m, str) else m.get("meal", "")


def _snack_texts(data):
    return {_text(m) for m in plan_engine.snack_queue(data)}


def _condition_problems(data, text):
    return [p for p in T.meal_problems(data, text) if p["kind"] == "condition"]


# ── المولّد ─────────────────────────────────────────────────────────

def test_generated_snacks_are_filtered_for_the_clients_conditions():
    for cond in (KIDNEY, LACTOSE):
        for system in ("standard", "five_meals"):
            for _ in range(3):
                data, plan = _draft(_staff(symptoms=cond, diet_plan_type=system))
                for i, day in enumerate(plan):
                    for key in SNACK_KEYS:
                        if day.get(key):
                            bad = _condition_problems(data, day[key])
                            assert not bad, (cond, system, i, key, day[key])


def test_the_snack_queue_is_filtered_and_never_empty():
    for cond in (KIDNEY, LACTOSE, [KIDNEY, LACTOSE]):
        data = dict(FORM, symptoms=cond if isinstance(cond, list) else [cond])
        queue = plan_engine.snack_queue(data)
        assert queue, cond
        for m in queue:
            assert not _condition_problems(data, _text(m)), (cond, _text(m))


# ── التبديل من الصفحة ───────────────────────────────────────────────

def _post(c, path, **data):
    return c.post(path, data=data)


def _a_snack_slot(plan):
    for key in SNACK_KEYS:
        if plan[0].get(key):
            return key
    raise AssertionError("الخطة مافيهاش سناك في أول يوم")


def test_a_random_swap_brings_another_snack_not_a_breakfast():
    for system in ("standard", "five_meals"):
        c = _staff(symptoms=KIDNEY, diet_plan_type=system)
        data, plan = _draft(c)
        key = _a_snack_slot(plan)
        before = plan[0][key]
        r = _post(c, "/swap_meal", day_idx=0, meal_type=key)
        got = r.get_json()
        assert r.status_code == 200 and got["ok"], (system, key, got)
        assert got["new_meal"] != before
        assert got["new_meal"] in _snack_texts(data), (system, key, got["new_meal"])
        assert not got["check"]["warning"], got["check"]
        assert _draft(c)[1][0][key] == got["new_meal"]


def test_the_pick_list_for_a_snack_is_the_safe_snack_list():
    c = _staff(symptoms=LACTOSE, diet_plan_type="five_meals")
    data, plan = _draft(c)
    for key in ("snack1", "snack2"):
        got = _post(c, "/get_meal_options", meal_type=key).get_json()
        assert got["ok"] and got["options"], (key, got)
        safe = _snack_texts(data)
        for o in got["options"]:
            assert o["meal"] in safe, (key, o["meal"])
            assert not _condition_problems(data, o["meal"]), o["meal"]


def test_the_preview_puts_swap_and_pick_next_to_each_snack():
    for system in ("standard", "five_meals"):
        c = _staff(diet_plan_type=system)
        _, plan = _draft(c)
        html = c.get("/preview").get_data(as_text=True)
        for key in SNACK_KEYS:
            if not plan[0].get(key):
                continue
            for cls in ("swap-btn", "pick-btn"):
                assert re.search(r'class="%s"[^>]*data-day="0"[^>]*data-type="%s"' % (cls, key),
                                 html), (system, key, cls)
            # ‏السناك مايتنقلش فوق الغدا: الترتيب بين الوجبات الرئيسية بس
            assert not re.search(r'class="move-btn"[^>]*data-day="0"[^>]*data-type="%s"' % key,
                                 html), (system, key)


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

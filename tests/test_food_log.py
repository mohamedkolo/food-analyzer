# -*- coding: utf-8 -*-
"""‏"أكلت حاجة برّه الخطة؟": العميل بيسجّل أكل زيادة من جدول الأكل المصري.

‏قبل كده العميل اللي أكل طعمية برّه الخطة ماكانش عنده مكان يقول، والدكتور
مايعرفش ليه الوزن واقف. دلوقتي بيدوّر في جدول الأكل (٩٣٨ صنف)، يختار
الكمية، والأرقام بتتحسب في السيرفر من الجدول -- مش من المتصفح.

‏اللي الاختبارات دي بتحرسه:
  ‏- الأرقام من الجدول × الجرامات، والسيرفر مابيصدّقش أرقام جاية من برّه.
  ‏- العميل يمسح أكله هو بس.
  ‏- الدواير ورسم الأسبوع بيحسبوا الزيادة، والنصيحة بتقولها.
  ‏- الدكتور بيشوف الأكل الزيادة في ملف العميل.

Run with:  python3 tests/test_food_log.py
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_food_log.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A             # noqa: E402
import food_data as F       # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
ADMIN = A.db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")["id"]
FOOL = next(f for f in F.FOODS if f["n"] == "فول مدمس")
DAY = {"breakfast": "بيض مسلوق 2", "lunch": "صدر دجاج مشوي 200جم", "dinner": "زبادي 150جم",
       "total_cal": 1200, "total_p": 100, "total_c": 80, "total_f": 40}


def _mk(email, plan=True):
    A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) VALUES (?,?,?,'client',1,?)",
             (email.split("@")[0], email, generate_password_hash("pw123456"), datetime.now()))
    uid = A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]
    if plan:
        A.db_run("INSERT INTO plan_requests (client_id,client_name,status,plan_data,updated_at) VALUES (?,?,'approved',?,?)",
                 (uid, "x", json.dumps({"plan": [DAY] * 7, "data": {"diet_plan_type": "standard"}}),
                  datetime.now() - timedelta(days=20)))
    return uid


AMR = _mk("amr@x.test")
LAYLA = _mk("layla@x.test")


def _as(uid, lang="ar"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = uid
        s["lang"] = lang
    return c


def _add(c, slug, grams, **extra):
    return c.post("/food-log/add", data=dict({"slug": slug, "grams": str(grams)}, **extra))


# ═══ البحث ═══

def test_search_finds_egyptian_food_with_its_numbers():
    rows = _as(AMR).get("/api/food/search?q=فول").get_json()
    names = [r["n"] for r in rows]
    assert "فول مدمس" in names, names
    r = rows[names.index("فول مدمس")]
    assert r["cal"] == FOOL["cal"] and r["p"] == FOOL["p"] and r["slug"] == FOOL["slug"]
    assert len(rows) <= 8


def test_search_reads_loose_arabic():
    # ‏"طعميه" بالهاء، و"بيض" لوحدها
    assert _as(AMR).get("/api/food/search?q=طعميه").get_json()
    assert _as(AMR).get("/api/food/search?q=egg").get_json()


def test_a_short_query_returns_nothing():
    assert _as(AMR).get("/api/food/search?q=ف").get_json() == []


# ═══ الإضافة ═══

def test_adding_computes_the_numbers_on_the_server():
    A.db_run("DELETE FROM food_log")
    c = _as(AMR)
    r = _add(c, FOOL["slug"], 200, cal="1", p="999")       # ‏أرقام من برّه بتتجاهل
    assert r.status_code == 200 and r.get_json()["ok"]
    row = A.db_row("SELECT * FROM food_log WHERE user_id=?", (AMR,))
    assert row["grams"] == 200
    assert row["cal"] == round(FOOL["cal"] * 2) and abs(row["p"] - round(FOOL["p"] * 2, 1)) < 0.01


def test_unknown_food_or_silly_grams_are_refused():
    c = _as(AMR)
    assert _add(c, "no-such-food", 100).status_code == 400
    assert _add(c, FOOL["slug"], 0).status_code == 400
    assert _add(c, FOOL["slug"], 5000).status_code == 400


def test_you_delete_only_your_own():
    A.db_run("DELETE FROM food_log")
    _add(_as(AMR), FOOL["slug"], 100)
    fid = A.db_row("SELECT id FROM food_log WHERE user_id=?", (AMR,))["id"]
    assert _as(LAYLA).post("/food-log/%d/delete" % fid).status_code == 404
    assert A.db_row("SELECT id FROM food_log WHERE id=?", (fid,))
    assert _as(AMR).post("/food-log/%d/delete" % fid).get_json()["ok"]
    assert not A.db_row("SELECT id FROM food_log WHERE id=?", (fid,))


def test_logging_needs_a_session():
    assert A.app.test_client().post("/food-log/add", data={"slug": FOOL["slug"], "grams": "100"}).status_code in (302, 401)


# ═══ الدواير والأسبوع ═══

def test_extras_count_in_todays_rings_and_hints():
    A.db_run("DELETE FROM food_log")
    c = _as(AMR)
    before = c.get("/my-plan/progress").get_json()
    _add(c, FOOL["slug"], 200)
    after = c.get("/my-plan/progress").get_json()
    assert after["eaten"]["cal"] - before["eaten"]["cal"] == round(FOOL["cal"] * 2)
    assert after["extra"]["cal"] == round(FOOL["cal"] * 2)
    assert any("برّه الخطة" in h for h in after["hints"]), after["hints"]


def test_extras_count_in_the_week():
    import client_app
    A.db_run("DELETE FROM food_log")
    _add(_as(AMR), FOOL["slug"], 100)
    w = client_app.week_progress(A.get_user_by_id(AMR))
    assert w["days"][-1]["cal"] >= round(FOOL["cal"])


# ═══ الصفحات ═══

def test_my_plan_no_longer_carries_the_food_search():
    """‏الدكتور (٢٦ نوفمبر): صفحة العميل أربع وجهات بس — بحث تسجيل الأكل
    ‏اتشال من الرئيسية. تسجيل الأكل نفسه شغال (الاختبارات فوق بتضيف منه)."""
    html = _as(AMR).get("/my-plan").get_data(as_text=True)
    assert 'id="flBox"' not in html and 'id="flQ"' not in html


def test_the_doctor_sees_food_eaten_outside_the_plan():
    A.db_run("DELETE FROM food_log")
    _add(_as(AMR), FOOL["slug"], 150)
    html = _as(ADMIN).get("/admin/users/%d" % AMR).get_data(as_text=True)
    assert 'id="clientFoodLog"' in html and "فول مدمس" in html


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

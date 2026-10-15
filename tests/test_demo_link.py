# -*- coding: utf-8 -*-
"""‏لينك العيّنة: ورقة شغالة من غير قاعدة بيانات.

‏الدكتور طلب إن كل شغل يخلص يبقى معاه لينك يفتحه ويشوف الناتج بنفسه.
لينك /p/<token> العادي مابينفعش للغرض ده: التوكن صف في قاعدة البيانات،
والقاعدة اللي الشغل بيتعمل عليها مش قاعدة الموقع -- فأي توكن بيتعمل
بره السيرفر بيطلّع 404 عنده.

‏فاللينك ده بيتبني من التوكن نفسه. وتلات حاجات الملف ده بيحميها:

  * **بيانات العيّنة مخترعة.** ده رابط عام من غير تسجيل دخول. لو اتبنى
    من عميل حقيقي يبقى تسريب ملف مريض لأي حد عنده اللينك.
  * **بيان إنها عيّنة.** لو حد فتحها وفكرها ورقته، هيمشي على أكل مش
    مبني على حالته.
  * **نفس اللينك = نفس الورقة.** لينك بيتغيّر كل مرة تفتحه مش مرجع،
    ومينفعش أقول عليه "شوف ده".

Run with:  python3 tests/test_demo_link.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_demo_test.db"

import app as A          # noqa: E402

TOKEN = "k7n2xq"


def _get(path="/demo/" + TOKEN, lang="ar"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["lang"] = lang
    return c.get(path)


def test_the_link_opens_with_no_row_in_the_database():
    """‏ده السبب اللي اللينك ده موجود عشانه."""
    import core
    with A.app.app_context():
        core.db_run("DELETE FROM plan_links")
    r = _get()
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    assert "404" not in html[:200], html[:200]


def test_the_sheet_carries_seven_days_of_food():
    """‏لينك بيفتح صفحة فاضية مش أحسن من 404."""
    html = _get().get_data(as_text=True)
    for day in ("الاحد", "الاثنين", "الثلاثاء", "الاربعاء", "الخميس",
                "الجمعة", "السبت"):
        assert day in html, "‏يوم %s ناقص من ورقة العيّنة" % day


def test_the_same_link_gives_the_same_sheet_every_time():
    """‏لينك بيتغيّر كل refresh مش مرجع -- مينفعش أقول عليه "شوف ده"."""
    a = _get().get_data(as_text=True)
    b = _get().get_data(as_text=True)
    assert a == b, "‏نفس اللينك دّى ورقتين مختلفين"


def test_two_different_links_are_two_different_clients():
    """‏لو كل اللينكات نفس الورقة، التوكن مالوش لازمة."""
    seen = {}
    for tok in ("aaa1", "bbb2", "ccc3", "ddd4", "eee5", "fff6", "ggg7"):
        html = _get("/demo/" + tok).get_data(as_text=True)
        seen[tok] = re.search(r'<b>(\d{3,4})</b><span>سعرة', html)
    vals = {m.group(1) for m in seen.values() if m}
    assert len(vals) > 1, "‏كل اللينكات طلعت نفس العميل: %s" % vals


def test_the_page_says_it_is_a_sample():
    """‏لو حد فتحها وفكرها ورقته، هيمشي على أكل مش مبني على حالته."""
    html = _get().get_data(as_text=True)
    assert "عيّنة" in html, "‏مافيش أي كلمة بتقول إنها عيّنة"
    en = _get(lang="en").get_data(as_text=True)
    assert "Sample" in en, "‏النسخة الإنجليزي مش بتقول إنها عيّنة"


def test_the_sample_name_is_not_a_real_looking_name():
    """‏اسم زي "أحمد محمد" على رابط عام بيتقرا كملف مريض."""
    import routes_plans
    with A.app.test_request_context("/"):
        name = routes_plans._demo_data(TOKEN)["name"]
    assert "عيّنة" in name or "Sample" in name, name


def test_the_sample_is_not_built_from_anybody_in_the_database():
    """‏الرابط عام. لو البيانات جت من عميل حقيقي يبقى تسريب ملف."""
    import inspect
    import routes_plans
    src = inspect.getsource(routes_plans._demo_data)
    for reach in ("db_row", "db_rows", "last_visit", "visits_for",
                  "recent_clients", "all_visits", "SELECT"):
        assert reach not in src, "‏العيّنة بتقرا من القاعدة: %s" % reach


def test_the_pdf_button_points_at_the_sample_pdf():
    """‏الزرار كان مربوط بـ/p/<token>/pdf، واللي هو مش موجود للعيّنة."""
    html = _get().get_data(as_text=True)
    assert "/demo/%s/pdf" % TOKEN in html, "‏زرار الـPDF لسه على الراوت القديم"
    assert "/p/%s/pdf" % TOKEN not in html, "‏الزرار بيوّدي على لينك مش موجود"


def test_the_sample_pdf_downloads():
    r = _get("/demo/%s/pdf" % TOKEN)
    assert r.status_code == 200, r.status_code
    assert r.data[:4] == b"%PDF", r.data[:20]


def test_a_real_plan_link_still_uses_its_own_pdf_route():
    """‏العيّنة ضافت pdf_url للقالب. لو الافتراضي اتكسر، كل عميل حقيقي
    فقد زرار التحميل بتاعه."""
    import core
    import json
    with A.app.app_context():
        core.db_run("DELETE FROM plan_links")
        core.db_run("""INSERT INTO plan_links (token, user_id, client_name,
                                               plan_json, data_json)
                       VALUES (?,?,?,?,?)""",
                    ("realtok", 1, "عميل حقيقي",
                     json.dumps([{"day": "الاحد", "meal_labels": ["breakfast"],
                                  "meal_emojis": {}, "breakfast": "بيض 2",
                                  "total_cal": 400, "total_p": 20}]),
                     json.dumps({"name": "عميل حقيقي", "goal_cal": "1600"})))
    html = _get("/p/realtok").get_data(as_text=True)
    assert "/p/realtok/pdf" in html, "‏زرار التحميل ضاع من ورقة العميل الحقيقي"
    assert "عيّنة" not in html, "‏لافتة العيّنة ظهرت على ورقة عميل حقيقي"


def test_the_sample_seed_does_not_make_other_plans_repeat():
    """‏اللينك بيزرع العشوائية ببذرة ثابتة. السؤال: هل ده بيأثر على
    الخطط التانية؟

    النسخة الأولى من الاختبار ده كانت بتفحص إن حالة random العامة
    رجعت زي ما كانت بعد الطلب -- وده كان فحص غلط: المولّد نفسه
    بيزرع random العام في **كل** خطة من ساعة ما البرنامج اتكتب،
    للينك ولغيره. فكنت بطالب اللينك بصفة مافيش حاجة في البرنامج
    عندها.

    واللي ممكن يبقى خطر فعلاً -- إن توكن رابط عميل يبقى متوقع لأن
    العشوائية مزروعة -- مش موجود: التوكنات بتتعمل بـsecrets، وده
    مصدر تاني خالص مالوش علاقة بـrandom.

    فاللي الاختبار ده بيفحصه هو اللي بيفرق: إن خطة عادية بعد اللينك
    لسه بتطلع جديدة.
    """
    from plan_engine import generate_weekly_plan
    base = {"name": "ع", "age": "30", "gender": "ذكر", "height": "175",
            "weight": "90", "tdee": "2400", "goal_cal": "2000",
            "goal_type": "weight_loss", "culture": "مصري",
            "diet_plan_type": "standard", "protein_per_kg": "1.6",
            "fat_pct_cal": "30", "symptoms": [], "allergies": [],
            "zigzag_mode": "off"}
    _get()
    with A.app.test_request_context("/"):
        a = generate_weekly_plan(dict(base))
        b = generate_weekly_plan(dict(base))
    assert a != b, "‏خطتين عاديتين ورا بعض طلعوا متطابقين — البذرة علقت"


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

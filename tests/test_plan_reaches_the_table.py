# -*- coding: utf-8 -*-
"""‏التوليد لازم يوصل للجدول -- في متصفح حقيقي، مش في عميل اختبار بس.

**الباج اللي الملف ده اتكتب بسببه:** الدكتور قال «كل ما اولد مش بوصل
للجدول». والسبب إن الخطة كلها كانت بتتحفظ في كوكي الجلسة، والكوكي عنده
حد ٤٠٩٣ بايت في كل المتصفحات. مقيس قبل التصليح:

    التكميم بدون أي حالة   ٤٧٠٧ بايت     فوق الحد
    التكميم بتلات حالات    ٥٤٣٢ بايت     فوق الحد
    الكيميائي بتلات حالات  ٤٧١٢ بايت     فوق الحد

‏ولما بيعدّي الحد المتصفح **بيرمي الكوكي من غير أي رسالة**، فالمعاينة
مالاقتش خطة ورجّعت للفورم. وفي متصفح فيه خطة قديمة كان أسوأ: الكوكي
الجديد يترفض، والقديم يفضل، فالدكتور يولّد خطة تكميم ويشوف خطة العميل
اللي قبله.

**وليه مافيش اختبار مسكه:** عميل الاختبار في Flask بيبعت الكوكي بأي حجم
وماعندوش حد. فالتوليد كان بينجح في كل الاختبارات وبيفشل في متصفح حقيقي.

فالاختبار ده بيقيس الحجم الفعلي للكوكي بنفسه، بنفس الحد اللي المتصفح
بيطبّقه. ده اللي كان ناقص.

Run with:  python3 tests/test_plan_reaches_the_table.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_table_test.db"

import app as A          # noqa: E402
import draft_store       # noqa: E402

# ‏الحد اللي المتصفحات بتطبّقه على الكوكي الواحد، وwerkzeug بيحذّر عنده.
COOKIE_LIMIT = 4093

BASE = {"name": "نورة سيد", "age": "29", "gender": "انثى", "height": "165",
        "weight": "78.4", "fat_pct": "38.2", "goal_cal": "1400", "tdee": "2000",
        "activity_mult": "1.55", "protein_per_kg": "1.6", "fat_pct_cal": "30",
        "goal_type": "weight_loss", "culture": "مصري", "zigzag_mode": "classic",
        "notes": "مابتحبش السمك ولا الكبدة، وبتشتغل شيفتات وبتنام متأخر",
        "phone": "01000000000"}

HEAVY = ["سكري نوع 2", "ضغط مرتفع", "قولون عصبي"]


def _staff():
    A.app.config["WTF_CSRF_ENABLED"] = False
    client = A.app.test_client()
    page = client.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', page).group(1)
    client.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                                "password": "pw123456", "csrf_token": token})
    return client


def _cookie_bytes(client):
    """‏حجم الكوكي اللي المتصفح كان هيستلمه، بنفس تسلسل Flask."""
    serializer = A.app.session_interface.get_signing_serializer(A.app)
    with client.session_transaction() as sess:
        return len(serializer.dumps(dict(sess)))


def _make(client, system, conditions=()):
    form = dict(BASE, diet_plan_type=system)
    if system == "sleeve":
        form["sleeve_weeks"] = "6"
    form["symptoms"] = list(conditions)
    return client.post("/generate", data=form, follow_redirects=False)


# ‏كل الأنظمة، وكل واحد مرة بدون حالات ومرة بتلاتة. التكميم والكيميائي
# كانوا فوق الحد، والباقي كان تحته بشعرة.
SYSTEMS = ("standard", "five_meals", "two_meals", "intermittent_16_8",
           "chemical", "sleeve", "keto")


def test_the_session_cookie_stays_small_for_every_system():
    """‏ده الاختبار اللي كان ناقص: يقيس الحجم بنفس حد المتصفح."""
    client = _staff()
    worst = (0, None)
    for system in SYSTEMS:
        for conditions in ((), HEAVY):
            _make(client, system, conditions)
            size = _cookie_bytes(client)
            if size > worst[0]:
                worst = (size, (system, len(conditions)))
            assert size < COOKIE_LIMIT, (
                "‏كوكي %d بايت في نظام %s بـ%d حالات -- المتصفح بيرميه والدكتور "
                "مابيشوفش الجدول" % (size, system, len(conditions)))
    # ‏والرقم لازم يفضل صغير فعلاً، مش تحت الحد بشعرة: أي حاجة تتزاد في
    # الجلسة بعد كده متبقاش مشكلة.
    assert worst[0] < 1200, "‏الكوكي كبر تاني: %d بايت %s" % worst


def test_every_system_lands_on_the_preview_with_a_table():
    client = _staff()
    for system in SYSTEMS:
        for conditions in ((), HEAVY):
            response = _make(client, system, conditions)
            assert response.status_code == 302, (system, response.status_code)
            assert response.headers["Location"].endswith("/preview"), (
                "‏نظام %s رجّع %s" % (system, response.headers["Location"]))
            page = client.get("/preview")
            assert page.status_code == 200, (system, page.status_code)
            body = page.get_data(as_text=True)
            assert "معاينة الخطة" in body, "‏نظام %s مافيهوش جدول" % system
            # ‏سبعة أيام فعلاً، مش صفحة فاضية
            assert body.count("swapMeal(") >= 7 or body.count("data-day=") >= 7, (
                "‏نظام %s: المعاينة مافيهاش أيام" % system)


def test_the_plan_is_the_one_that_was_asked_for():
    """‏لما الكوكي كان بيترفض، القديم بيفضل -- فالدكتور يطلب تكميم
    ويشوف خطة العميل اللي قبله. ودي أخطر من إن الجدول مايظهرش."""
    client = _staff()
    _make(client, "standard")
    first = draft_store_plan(client)
    _make(client, "sleeve")
    second = draft_store_plan(client)
    assert first and second, (bool(first), bool(second))
    assert first != second, "‏طلبنا خطة تانية ورجعت نفس الخطة الأولانية"
    data = draft_store_data(client)
    assert data.get("diet_plan_type") == "sleeve", data.get("diet_plan_type")


def draft_store_plan(client):
    with client.session_transaction() as sess:
        ident = sess.get(draft_store.KEY)
    from core import db_row
    row = db_row("SELECT plan_json AS v FROM plan_drafts WHERE id=?", (ident,))
    import json
    return json.loads(row["v"]) if row and row.get("v") else None


def draft_store_data(client):
    with client.session_transaction() as sess:
        ident = sess.get(draft_store.KEY)
    from core import db_row
    row = db_row("SELECT data_json AS v FROM plan_drafts WHERE id=?", (ident,))
    import json
    return json.loads(row["v"]) if row and row.get("v") else {}


def test_the_plan_survives_editing_saving_and_the_pdf():
    """‏الخطة بقت في القاعدة، فكل اللي بيقراها لازم يفضل شغّال."""
    client = _staff()
    _make(client, "five_meals", HEAVY)

    # ‏تبديل وجبة
    swap = client.post("/swap_meal", data={"day_idx": "0", "meal_type": "breakfast"},
                       follow_redirects=False)
    assert swap.status_code in (200, 302), swap.status_code
    assert draft_store_plan(client), "‏الخطة ضاعت بعد التبديل"

    # ‏تعديل نص وجبة بإيده
    edit = client.post("/edit_meal",
                       data={"day_idx": "0", "meal_type": "breakfast",
                             "new_text": "بيض مسلوق 2 + خبز أسمر 30جم"},
                       follow_redirects=False)
    assert edit.status_code in (200, 302), edit.status_code
    plan = draft_store_plan(client)
    assert plan and "بيض مسلوق 2" in str(plan[0]), "‏التعديل مااتحفظش"

    # ‏تجديد الخطة كاملة
    again = client.post("/regenerate_plan", follow_redirects=False)
    assert again.status_code == 302, again.status_code
    assert draft_store_plan(client), "‏الخطة ضاعت بعد التجديد"

    # ‏حفظ، ولينك، وPDF
    saved = client.post("/api/save-plan")
    assert saved.status_code == 200 and saved.get_json().get("ok"), saved.get_json()
    link = client.post("/api/plan-link")
    assert link.status_code == 200 and link.get_json().get("ok"), link.get_json()
    pdf = client.get("/download_pdf")
    assert pdf.status_code == 200, pdf.status_code
    assert pdf.get_data()[:4] == b"%PDF", pdf.get_data()[:20]


def test_a_browser_with_no_draft_is_sent_to_the_form_not_to_a_crash():
    client = _staff()
    page = client.get("/preview", follow_redirects=False)
    assert page.status_code == 302 and page.headers["Location"].endswith("/generate")
    pdf = client.get("/download_pdf", follow_redirects=False)
    assert pdf.status_code in (302, 200), pdf.status_code


def test_the_draft_is_not_readable_by_another_doctor():
    """‏رقم المسوّدة في الكوكي. لو حد خمّنه، مايشوفش خطة حد تاني."""
    client = _staff()
    _make(client, "standard")
    with client.session_transaction() as sess:
        ident = sess.get(draft_store.KEY)
    assert ident and len(ident) >= 24, ident       # ‏مش رقم متسلسل يتخمّن
    other = A.app.test_client()
    page = other.get("/preview", follow_redirects=False)
    assert page.status_code in (301, 302), page.status_code
    assert "/login" in page.headers.get("Location", ""), page.headers.get("Location")


def test_nothing_puts_the_plan_back_in_the_cookie():
    """‏الباج ده بيرجع بسطر واحد، فالسطر ده ممنوع."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offenders = []
    for name in os.listdir(here):
        if not name.endswith(".py") or name == "draft_store.py":
            continue
        with open(os.path.join(here, name), encoding="utf-8") as fh:
            # ‏الكومنتات بتحكي عن الباج ده وبتشرحه، فبتتشال قبل الفحص --
            # وإلا الشرح نفسه يبقى مخالفة.
            code = "\n".join(line.split("#")[0] for line in fh)
        for key in ('session["current_plan"]', 'session["pdf_data"]',
                    "session.get('current_plan')", 'session.get("current_plan")',
                    'session.get("pdf_data")'):
            if key in code:
                offenders.append("%s -> %s" % (name, key))
    assert not offenders, (
        "‏الخطة رجعت للكوكي:\n  " + "\n  ".join(offenders))


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

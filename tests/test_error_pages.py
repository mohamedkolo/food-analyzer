# -*- coding: utf-8 -*-
"""صفحات الغلط، ونقطة الحالة.

الموقع رد "Internal Server Error" على ورقة بيضاء. الصفحة دي بتقول حاجة
واحدة: في غلطة. ومابتقولش:

  * للزائر يعمل إيه
  * ولا لينا وقع فين
  * ولا -- وده الأهم -- إذا كان التطبيق هو اللي واقع ولا قاعدة البيانات

الفرق التالت ده هو اللي بيحدد الإجراء: كود واقع معناه نصلّح وننشر، وقاعدة
واقعة معناها نفتح لوحة الاستضافة. من غير الفرق ده التخمين هو كل اللي فاضل.

Run with:  python3 tests/test_error_pages.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_errors_test.db"

import app as A       # noqa: E402
import core           # noqa: E402


@A.app.route("/__test_boom_db")
def _boom_db():
    raise RuntimeError("psycopg2.OperationalError: could not connect to server")


@A.app.route("/__test_boom_other")
def _boom_other():
    raise ValueError("something silly")


_CLIENT = A.app.test_client()


def test_health_answers_even_when_the_database_is_down():
    """‏دي الصفحة الوحيدة اللي تفرّق بين "التطبيق واقع" و"القاعدة واقعة"،
    فلازم ترد في الحالتين -- ولو هي كمان بتلمس القاعدة، بتقع معاها."""
    ok = _CLIENT.get("/health")
    assert ok.status_code == 200, ok.status_code
    assert ok.get_json().get("db") == "ok", ok.get_json()

    real = core.db_row
    core.db_row = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("could not connect to server"))
    try:
        down = _CLIENT.get("/health")
    finally:
        core.db_row = real
    assert down.status_code == 200, (
        "‏نقطة الحالة وقعت مع القاعدة، فمابقى فيه حاجة تدل على السبب")
    body = down.get_json()
    assert body.get("db", "").startswith("down"), body
    assert body.get("ok") is False, body
    assert body.get("commit"), "‏الكوميت الشغال ناقص -- مش هنعرف المنشور إيه"


def test_a_broken_page_says_so_and_carries_a_reference():
    r = _CLIENT.get("/__test_boom_other")
    assert r.status_code == 500, r.status_code
    html = r.get_data(as_text=True)
    assert "في حاجة وقعت" in html, "‏لسه صفحة Werkzeug الفاضية"
    assert re.search(r"<b>[0-9a-f]{8}</b>", html), (
        "‏مافيش رقم مرجعي -- مش هنعرف نلاقي السطر في اللوج")


def test_the_page_never_leaks_the_traceback():
    """‏الصفحة دي بيشوفها أي حد، والتفاصيل مكانها اللوج."""
    for path in ("/__test_boom_db", "/__test_boom_other"):
        html = _CLIENT.get(path).get_data(as_text=True)
        for leak in ("Traceback", "psycopg2", "File \"", "RuntimeError"):
            assert leak not in html, "‏%s ظاهرة في الصفحة (%s)" % (leak, path)


def test_a_database_failure_is_named_as_one():
    """‏الإجراء مختلف: كود واقع = نصلّح وننشر، قاعدة واقعة = لوحة الاستضافة."""
    db = _CLIENT.get("/__test_boom_db").get_data(as_text=True)
    other = _CLIENT.get("/__test_boom_other").get_data(as_text=True)
    assert "قاعدة البيانات" in db, "‏غلطة القاعدة مش مكتوب إنها غلطة قاعدة"
    assert "قاعدة البيانات" not in other, (
        "‏أي غلطة بقت بتقول إن القاعدة واقعة -- فالرسالة مابقى لها معنى")


def test_a_missing_page_is_still_a_missing_page():
    """‏errorhandler(Exception) مايخدش الأكواد اللي ليها معنى."""
    assert _CLIENT.get("/__no_such_page_here").status_code == 404
    assert _CLIENT.get("/login").status_code == 200, "‏الدخول اتكسر"


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

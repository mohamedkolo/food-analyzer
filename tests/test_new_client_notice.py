# -*- coding: utf-8 -*-
"""‏إشعار للدكتور لما حد يعمل حساب جديد.

‏فيه طريقين للتسجيل: الاستبيان الطويل (/register) وتبويب "إنشاء حساب" في
صفحة الدخول. الاستبيان كان بيبعت إشعار "عميل جديد"، والتبويب لأ -- فعميل
يسجّل من التبويب كان بيدخل من غير ما الدكتور يعرف.

Run with:  python3 tests/test_new_client_notice.py
"""

import os
import sys

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_new_client_notice.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False


def _notices(email):
    return A.db_rows("SELECT * FROM notifications WHERE type='new_client' AND message LIKE ?",
                     ("%" + email + "%",))


def test_signup_tab_on_login_page_tells_the_doctor():
    c = A.app.test_client()
    c.post("/login", data={
        "action": "register", "name": "Tab Signup", "age": "30", "country": "مصر",
        "phone": "+201000000009", "reg_email": "tab@x.test", "reg_password": "pw123456"})
    rows = _notices("tab@x.test")
    assert len(rows) == 1, rows
    u = A.db_row("SELECT id FROM users WHERE email='tab@x.test'")
    assert rows[0]["related_user_id"] == u["id"]
    assert "Tab Signup" in rows[0]["title"]


def test_long_signup_form_still_tells_the_doctor():
    c = A.app.test_client()
    c.post("/register", data={
        "name": "Wiz Signup", "email": "wiz@x.test", "password": "pw123456",
        "phone": "01011112222", "country": "مصر", "age": "30",
        "gender": "انثى", "height": "165", "weight": "70"})
    assert len(_notices("wiz@x.test")) == 1


def test_a_taken_email_does_not_notify():
    c = A.app.test_client()
    data = {"action": "register", "name": "Twice", "age": "30", "country": "مصر",
            "phone": "+201000000008", "reg_email": "twice@x.test", "reg_password": "pw123456"}
    c.post("/login", data=data)
    c.post("/login", data=data)
    assert len(_notices("twice@x.test")) == 1


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

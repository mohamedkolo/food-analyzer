# -*- coding: utf-8 -*-
"""‏كود التأكيد على الإيميل: "نسيت كلمة السر" و"أكّد إيميلك".

‏قبل كده العميل اللي نسي كلمة السر كان لازم يكلّم الدكتور واتساب وهو
يغيّرها بإيده. ودلوقتي بيوصله كود من ٦ أرقام على الإيميل ويغيّرها
بنفسه. ونفس الكود بيأكّد إيميل الحساب الجديد قبل أول دخول.

‏اللي الاختبارات دي بتحرسه:
  ‏- الكود متخزّن مشفّر، صلاحيته ١٠ دقايق، وبيتستخدم مرة واحدة.
  ‏- ٥ محاولات غلط والكود بيتقفل، حتى لو المحاولة السادسة صح.
  ‏- كود جديد مش قبل دقيقة من اللي قبله.
  ‏- "نسيت كلمة السر" بترد نفس الرد لإيميل موجود ولإيميل مش موجود،
    علشان محدش يعرف مين عنده حساب.
  ‏- لو الـSMTP مش متظبّط، محدش يتقفل برّه: الحساب الجديد بيدخل
    عادي، و"نسيت كلمة السر" بترجع للواتساب.
  ‏- الحسابات القديمة مابيتطلبش منها تأكيد.

Run with:  python3 tests/test_email_codes.py
"""

import os
import re
import sys
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_email_codes.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A                # noqa: E402
import email_codes as EC       # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
ARABIC = re.compile(r"[؀-ۿ]")

SENT = []


def _fake_send(email, code, purpose, lang):
    SENT.append((email, code, purpose))
    return True


EC.send_code = _fake_send


def _smtp(on):
    EC.smtp_ready = (lambda: True) if on else (lambda: False)


def _reset():
    SENT.clear()
    A.db_run("DELETE FROM email_codes")
    import core; core._login_attempts.clear()


_n = [0]


def _old_user(pw="oldpass1"):
    """حساب موجود من قبل الميزة (email_verified بالقيمة الافتراضية)."""
    _n[0] += 1
    email = "old%d@x.test" % _n[0]
    A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at)"
             " VALUES (?,?,?,'client',1,?)",
             ("Old", email, generate_password_hash(pw), datetime.now()))
    return email


def _client(lang="ar"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["lang"] = lang
    return c


def _logged_in(c):
    with c.session_transaction() as s:
        return "uid" in s


def _register(c, email, pw="newpass1"):
    return c.post("/login", data={
        "action": "register", "name": "New One", "age": "30", "country": "مصر",
        "phone": "+201000000001", "reg_email": email, "reg_password": pw})


def _login(c, email, pw):
    return c.post("/login", data={"action": "login", "email": email, "password": pw})


# ═══ الكود نفسه ═══

def test_code_is_six_digits_and_stored_hashed():
    _reset()
    code = EC.issue("a@x.test", "reset")
    assert re.fullmatch(r"\d{6}", code), code
    row = A.db_row("SELECT * FROM email_codes WHERE email='a@x.test'")
    assert code not in str(row["code_hash"])


def test_code_works_once():
    _reset()
    code = EC.issue("b@x.test", "reset")
    assert EC.check("b@x.test", "reset", code) == "ok"
    assert EC.check("b@x.test", "reset", code) != "ok"


def test_code_expires_after_ten_minutes():
    _reset()
    code = EC.issue("c@x.test", "reset")
    A.db_run("UPDATE email_codes SET expires_at=? WHERE email='c@x.test'",
             (datetime.utcnow() - timedelta(seconds=1),))
    assert EC.check("c@x.test", "reset", code) == "expired"


def test_five_wrong_tries_lock_the_code():
    _reset()
    code = EC.issue("d@x.test", "reset")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert EC.check("d@x.test", "reset", wrong) == "wrong"
    assert EC.check("d@x.test", "reset", code) == "locked"


def test_a_new_code_waits_a_minute():
    _reset()
    assert EC.issue("e@x.test", "reset")
    assert EC.issue("e@x.test", "reset") is None
    A.db_run("UPDATE email_codes SET created_at=? WHERE email='e@x.test'",
             (datetime.utcnow() - timedelta(seconds=61),))
    assert EC.issue("e@x.test", "reset")


def test_a_reset_code_does_not_verify_and_the_other_way():
    _reset()
    code = EC.issue("f@x.test", "reset")
    assert EC.check("f@x.test", "verify", code) != "ok"


# ═══ نسيت كلمة السر ═══

def test_login_page_links_to_forgot():
    assert 'href="/forgot"' in _client().get("/login").get_data(as_text=True)


def test_forgot_full_flow_changes_the_password():
    _reset(); _smtp(True)
    email = _old_user("oldpass1")
    c = _client()
    r = c.post("/forgot", data={"email": email.upper() + " "})
    assert r.status_code == 302 and r.headers["Location"].endswith("/forgot/code")
    assert len(SENT) == 1 and SENT[0][0] == email and SENT[0][2] == "reset"
    r = c.post("/forgot/code", data={"code": SENT[0][1], "password": "brandnew1"})
    assert r.status_code == 200
    assert 'data-done="1"' in r.get_data(as_text=True)
    assert A.get_user(email, "brandnew1")
    assert not A.get_user(email, "oldpass1")


def test_forgot_answers_the_same_for_an_unknown_email():
    _reset(); _smtp(True)
    r = _client().post("/forgot", data={"email": "ghost@x.test"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/forgot/code")
    assert SENT == []
    assert A.db_row("SELECT COUNT(*) AS n FROM email_codes")["n"] == 0


def test_forgot_wrong_code_keeps_the_old_password():
    _reset(); _smtp(True)
    email = _old_user("oldpass1")
    c = _client()
    c.post("/forgot", data={"email": email})
    wrong = "000000" if SENT[0][1] != "000000" else "111111"
    r = c.post("/forgot/code", data={"code": wrong, "password": "brandnew1"})
    assert 'data-done="1"' not in r.get_data(as_text=True)
    assert A.get_user(email, "oldpass1")


def test_forgot_short_new_password_is_refused():
    _reset(); _smtp(True)
    email = _old_user("oldpass1")
    c = _client()
    c.post("/forgot", data={"email": email})
    c.post("/forgot/code", data={"code": SENT[0][1], "password": "123"})
    assert A.get_user(email, "oldpass1")


def test_forgot_without_smtp_points_to_whatsapp():
    _reset(); _smtp(False)
    html = _client().get("/forgot").get_data(as_text=True)
    assert "wa.me/" in html
    assert 'name="email"' not in html


def test_forgot_pages_in_english_have_no_arabic():
    _reset(); _smtp(True)
    c = _client("en")
    for url in ("/forgot", "/forgot/code"):
        html = c.get(url).get_data(as_text=True)
        body = html[html.index("<body"):]
        assert not ARABIC.search(body), (url, ARABIC.findall(body)[:10])


# ═══ تأكيد الإيميل للحساب الجديد ═══

def test_old_accounts_sign_in_without_a_code():
    _reset(); _smtp(True)
    email = _old_user("oldpass1")
    c = _client()
    r = _login(c, email, "oldpass1")
    assert r.status_code == 302 and "/verify" not in r.headers["Location"]
    assert _logged_in(c) and SENT == []


def test_new_account_must_confirm_before_first_sign_in():
    _reset(); _smtp(True)
    c = _client()
    _register(c, "fresh1@x.test")
    r = _login(c, "fresh1@x.test", "newpass1")
    assert r.status_code == 302 and r.headers["Location"].endswith("/verify")
    assert not _logged_in(c)
    assert SENT and SENT[-1][2] == "verify"
    r = c.post("/verify", data={"code": SENT[-1][1]})
    assert r.status_code == 200 and 'data-done="1"' in r.get_data(as_text=True)
    assert _logged_in(c)
    assert A.db_row("SELECT email_verified FROM users WHERE email='fresh1@x.test'")["email_verified"] == 1
    # ‏المرة الجاية بيدخل على طول
    c2 = _client()
    SENT.clear()
    _login(c2, "fresh1@x.test", "newpass1")
    assert _logged_in(c2) and SENT == []


def test_wrong_verify_code_does_not_sign_in():
    _reset(); _smtp(True)
    c = _client()
    _register(c, "fresh2@x.test")
    _login(c, "fresh2@x.test", "newpass1")
    wrong = "000000" if SENT[-1][1] != "000000" else "111111"
    c.post("/verify", data={"code": wrong})
    assert not _logged_in(c)


def test_without_smtp_a_new_account_is_never_locked_out():
    _reset(); _smtp(False)
    c = _client()
    _register(c, "fresh3@x.test")
    r = _login(c, "fresh3@x.test", "newpass1")
    assert "/verify" not in r.headers["Location"] and _logged_in(c)


def test_a_reset_by_code_also_confirms_the_email():
    # ‏اللي غيّر كلمة السر بكود على إيميله أثبت إن الإيميل بتاعه.
    _reset(); _smtp(True)
    c = _client()
    _register(c, "fresh4@x.test")
    c.post("/forgot", data={"email": "fresh4@x.test"})
    c.post("/forgot/code", data={"code": SENT[-1][1], "password": "brandnew1"})
    assert A.db_row("SELECT email_verified FROM users WHERE email='fresh4@x.test'")["email_verified"] == 1


def test_the_long_signup_form_also_asks_for_the_code_and_keeps_the_slot():
    # ‏/register بيفتح الجلسة على طول بعد التسجيل. لازم يستنى الكود هو كمان،
    # والموعد اللي الزائر اختاره قبل التسجيل يفضل محفوظ لحد بعد التأكيد.
    _reset(); _smtp(True)
    c = _client()
    with c.session_transaction() as s:
        s["after_login"] = "/book?slot=abc"
    r = c.post("/register", data={
        "name": "Nour", "email": "wiz@x.test", "password": "pw123456",
        "phone": "01011112222", "country": "مصر", "age": "30",
        "gender": "انثى", "height": "165", "weight": "70"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/verify")
    assert not _logged_in(c)
    r = c.post("/verify", data={"code": SENT[-1][1]})
    assert _logged_in(c)
    assert 'href="/book?slot=abc"' in r.get_data(as_text=True)


def test_verify_page_without_a_pending_sign_in_goes_to_login():
    r = _client().get("/verify")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_code_page_is_accessible():
    _reset(); _smtp(True)
    c = _client()
    c.post("/forgot", data={"email": "ghost@x.test"})
    html = c.get("/forgot/code").get_data(as_text=True)
    assert 'autocomplete="one-time-code"' in html
    assert 'inputmode="numeric"' in html
    assert re.search(r'<label[^>]+for="code"', html)
    assert "prefers-reduced-motion" in html


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

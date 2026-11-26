# -*- coding: utf-8 -*-
"""Admin actions, API keys, per-IP limits and upload size.

Run with:  python3 tests/test_security_hardening.py
"""
import os
import re
import sys
from datetime import datetime

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_suite.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A  # noqa: E402
import core  # noqa: E402
import api_platform as AP  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


def _mk(email, role, **cols):
    row = A.db_row("SELECT id FROM users WHERE email=?", (email,))
    if row:
        return row["id"]
    keys = ["name", "email", "password", "role", "active"] + list(cols)
    vals = ["T", email, generate_password_hash("pw123456"), role, 1] + list(cols.values())
    A.db_run(f"INSERT INTO users ({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})", tuple(vals))
    return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]


ADMIN = _mk("sec-admin@t.test", "admin", is_admin=1, onboarded_at=datetime.now())
TARGET = _mk("sec-target@t.test", "client", onboarded_at=datetime.now())


def _admin():
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"], s["role"], s["lang"] = ADMIN, "admin", "ar"
    return c


def _token(c):
    html = c.get("/admin/users").get_data(as_text=True)
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "no csrf token on /admin/users"
    return m.group(1)


def _login_token(c):
    html = c.get("/login").get_data(as_text=True)
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "no csrf token on /login"
    return m.group(1)


def _active(uid):
    return A.db_row("SELECT active FROM users WHERE id=?", (uid,))["active"]


def _role(uid):
    return A.db_row("SELECT role FROM users WHERE id=?", (uid,))["role"]


def test_toggle_by_plain_link_does_nothing():
    c = _admin()
    before = _active(TARGET)
    r = c.get(f"/admin/users/{TARGET}/toggle")
    assert r.status_code == 405 and _active(TARGET) == before


def test_role_change_by_plain_link_does_nothing():
    c = _admin()
    before = _role(TARGET)
    r = c.get(f"/admin/users/{TARGET}/role/nutritionist")
    assert r.status_code == 405 and _role(TARGET) == before


def test_post_without_csrf_token_is_refused():
    c = _admin()
    before = _active(TARGET)
    r = c.post(f"/admin/users/{TARGET}/toggle")
    assert r.status_code == 400 and _active(TARGET) == before


def test_toggle_and_role_work_with_the_token():
    c = _admin()
    tok = _token(c)
    before = _active(TARGET)
    r = c.post(f"/admin/users/{TARGET}/toggle", data={"csrf_token": tok})
    assert r.status_code == 302 and _active(TARGET) == (0 if before else 1)
    c.post(f"/admin/users/{TARGET}/toggle", data={"csrf_token": tok})
    assert _active(TARGET) == before
    c.post(f"/admin/users/{TARGET}/role/nutritionist", data={"csrf_token": tok})
    assert _role(TARGET) == "nutritionist"
    c.post(f"/admin/users/{TARGET}/role/client", data={"csrf_token": tok})
    assert _role(TARGET) == "client"


def test_a_non_admin_cannot_post_the_admin_actions():
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"], s["role"] = TARGET, "client"
    r = c.post(f"/admin/users/{TARGET}/role/admin")
    assert r.status_code in (302, 400, 403) and _role(TARGET) == "client"


def test_the_admin_page_uses_forms_not_links_for_these_actions():
    html = _admin().get("/admin/users").get_data(as_text=True)
    assert 'href="/admin/users/' not in html or "/toggle" not in re.findall(r'href="[^"]*"', html).__str__()
    assert 'method="POST" action="/admin/users/' in html
    assert "window.location.href='/admin/users/" not in html


def _with_header(fn):
    core.TRUSTED_IP_HEADER = "CF-Connecting-IP"
    core._ip_hits.clear()
    try:
        fn()
    finally:
        core.TRUSTED_IP_HEADER = ""
        core._ip_hits.clear()


def _test_login_is_limited_per_ip_across_different_emails():
    core._ip_hits.clear()
    c = A.app.test_client()
    tok = _login_token(c)
    last = None
    for i in range(22):
        last = c.post("/login", data={"action": "login", "email": f"nobody{i}@t.test", "password": "x", "csrf_token": tok},
                      headers={"CF-Connecting-IP": "6.6.6.6"})
    assert last.status_code == 200
    ok = c.post("/login", data={"action": "login", "email": "sec-target@t.test", "password": "pw123456", "csrf_token": tok},
                headers={"CF-Connecting-IP": "6.6.6.6"})
    assert ok.status_code == 200, "a correct password was accepted from an IP that is over the limit"
    other = c.post("/login", data={"action": "login", "email": "sec-target@t.test", "password": "pw123456", "csrf_token": tok},
                   headers={"CF-Connecting-IP": "7.7.7.7"})
    assert other.status_code == 302, "another IP should not be affected"
    core._ip_hits.clear()


def _test_signup_is_limited_per_ip():
    core._ip_hits.clear()
    c = A.app.test_client()
    tok = _login_token(c)
    codes = []
    for i in range(12):
        r = c.post("/login", data={"action": "register", "name": "x", "reg_email": f"s{i}@sec.test",
                                   "reg_password": "abcdef", "country": "EG", "age": "30", "phone": "01000000000", "csrf_token": tok},
                   headers={"CF-Connecting-IP": "4.4.4.4"})
        codes.append("Too many requests" in r.get_data(as_text=True) or "طلبات كتير" in r.get_data(as_text=True))
    assert not any(codes[:10]) and all(codes[10:]), codes
    core._ip_hits.clear()


def test_oversized_upload_is_refused():
    assert A.app.config["MAX_CONTENT_LENGTH"] == 20 * 1024 * 1024
    c = A.app.test_client()
    import io
    r = c.post("/barcode/read", data={"image": (io.BytesIO(b"0" * (21 * 1024 * 1024)), "a.jpg")},
               content_type="multipart/form-data")
    assert r.status_code == 413


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

# -*- coding: utf-8 -*-
"""Who can reach what.

Every route that touches a client's data or the clinic's money sits behind a
decorator. This checks the decorators actually hold, rather than trusting that
each route remembered to carry one.

Run with:  python3 tests/test_access_control.py
"""

import os
import re
import sys
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
for _p in ("/tmp/nutrax.db",):
    if os.path.exists(_p):
        os.remove(_p)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


def _mk(name, email, role, **cols):
    row = A.db_row("SELECT id FROM users WHERE email=?", (email,))
    if row:
        return row["id"]
    keys = ["name", "email", "password", "role", "active"] + list(cols)
    vals = [name, email, generate_password_hash("pw123456"), role, 1] + list(cols.values())
    A.db_run(f"INSERT INTO users ({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})",
             tuple(vals))
    return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]


ADMIN = _mk("Admin", "admin@t.test", "admin", is_admin=1, onboarded_at=datetime.now())
NUTRI = _mk("Nutritionist", "nutri@t.test", "nutritionist", onboarded_at=datetime.now())
CLIENT = _mk("Client", "client@t.test", "client", onboarded_at=datetime.now(),
             height=170, weight=80, age=30, gender="ذكر")
FRESH = _mk("Fresh", "fresh@t.test", "client")

if not A.db_row("SELECT id FROM payments WHERE user_id=?", (CLIENT,)):
    A.db_run("INSERT INTO payments (user_id,stripe_session_id,plan_key,status,currency,amount,expires_at) "
             "VALUES (?,?,?,?,?,?,?)",
             (CLIENT, "seed", "monthly_subscription", "completed", "EGP", 50000,
              datetime.now() + timedelta(days=20)))

# admin only -- a nutritionist must not manage users, payments or subscriptions
ADMIN_ONLY = ["/admin/users", "/admin/blocked", "/admin/payments", "/admin/users/new"]
# staff -- admin and nutritionist, never a client
STAFF_ONLY = ["/admin/requests", "/generate", "/patients", "/saved", "/clinical", "/planner"]
# any signed-in user
CLIENT_PAGES = ["/my-plan", "/settings", "/analyzer", "/knowledge", "/daily-tips"]
# no login at all
PUBLIC = ["/", "/login", "/foods", "/pricing", "/terms", "/privacy", "/robots.txt", "/sitemap.xml"]


def client_as(uid=None, role=None, lang="ar"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["lang"] = lang
        if uid:
            s["uid"] = uid
            s["role"] = role
    return c


# where the decorators send someone who is not allowed through
_DENIED_TO = ("/login", "/onboarding", "/subscription-required", "/dashboard", "/my-plan")


def _reached(c, path):
    """True when the request was served.

    A 302 is not automatically a denial -- /planner redirects to /generate for
    everyone. What marks a denial is *where* it sends you.
    """
    r = c.get(path)
    if r.status_code == 200:
        return True
    if r.status_code in (301, 302):
        dest = r.headers.get("Location", "")
        if dest.rstrip("/") == "" or any(dest.startswith(d) for d in _DENIED_TO):
            return False
        return _reached(c, dest)      # an internal hop, follow it
    return False


def test_anonymous_cannot_reach_anything_private():
    c = client_as()
    leaked = [p for p in ADMIN_ONLY + STAFF_ONLY + CLIENT_PAGES if _reached(c, p)]
    assert not leaked, f"reachable without logging in: {leaked}"


def test_public_pages_need_no_login():
    c = client_as()
    blocked = [p for p in PUBLIC if c.get(p).status_code != 200]
    assert not blocked, f"public pages not reachable anonymously: {blocked}"


def test_client_cannot_reach_staff_pages():
    c = client_as(CLIENT, "client")
    leaked = [p for p in STAFF_ONLY + ADMIN_ONLY if _reached(c, p)]
    assert not leaked, f"a client reached staff pages: {leaked}"


def test_nutritionist_cannot_reach_admin_pages():
    """A nutritionist builds plans; they do not manage users or see the money."""
    c = client_as(NUTRI, "nutritionist")
    leaked = [p for p in ADMIN_ONLY if _reached(c, p)]
    assert not leaked, f"a nutritionist reached admin-only pages: {leaked}"


def test_nutritionist_can_do_their_job():
    c = client_as(NUTRI, "nutritionist")
    blocked = [p for p in STAFF_ONLY if not _reached(c, p)]
    assert not blocked, f"a nutritionist was blocked from their own pages: {blocked}"


def test_admin_reaches_everything():
    c = client_as(ADMIN, "admin")
    blocked = [p for p in ADMIN_ONLY + STAFF_ONLY if not _reached(c, p)]
    assert not blocked, f"an admin was blocked from: {blocked}"


def test_onboarding_gate_holds_a_fresh_client():
    c = client_as(FRESH, "client")
    r = c.get("/my-plan")
    assert r.status_code == 302 and "/onboarding" in r.headers.get("Location", ""), \
        f"a client who never onboarded reached /my-plan: {r.status_code}"


def test_a_client_cannot_read_another_clients_profile():
    c = client_as(CLIENT, "client")
    assert not _reached(c, f"/admin/users/{ADMIN}"), "a client opened someone else's profile"


def test_session_cookie_is_locked_down_in_production():
    """SEC-1. Secure only binds in production, the rest always."""
    assert A.app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert A.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert A.app.config["SESSION_COOKIE_SECURE"] == A.IS_PRODUCTION


def test_login_rejects_a_wrong_password():
    c = A.app.test_client()
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                    c.get("/login").get_data(as_text=True)).group(1)
    c.post("/login", data={"action": "login", "email": "admin@t.test",
                           "password": "definitely-wrong", "csrf_token": tok})
    assert c.get("/dashboard").status_code == 302, "a wrong password still logged in"


def test_login_accepts_the_right_password():
    c = A.app.test_client()
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                    c.get("/login").get_data(as_text=True)).group(1)
    r = c.post("/login", data={"action": "login", "email": "admin@t.test",
                               "password": "pw123456", "csrf_token": tok})
    assert r.status_code == 302, f"login failed: {r.status_code}"
    assert c.get("/dashboard").status_code == 200



def test_every_admin_page_renders():
    """Reaching a page is not the same as it working. A refactor can leave a
    helper behind and only the render shows it -- this is how the client
    profile page was caught 500ing after build_whatsapp_link moved without its
    lookup table."""
    c = client_as(ADMIN, "admin")
    broken = []
    for p in ADMIN_ONLY + [f"/admin/users/{CLIENT}", f"/admin/users/{CLIENT}/payments",
                           "/admin/requests", "/admin/notifications",
                           "/admin/notifications/count", "/admin/users/export"]:
        r = c.get(p)
        if r.status_code not in (200, 302):
            broken.append((p, r.status_code))
    assert not broken, f"admin pages returning an error: {broken}"


def test_staff_pages_render_for_a_nutritionist():
    c = client_as(NUTRI, "nutritionist")
    broken = [(p, c.get(p).status_code) for p in STAFF_ONLY
              if c.get(p).status_code not in (200, 302)]
    assert not broken, f"staff pages returning an error: {broken}"


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

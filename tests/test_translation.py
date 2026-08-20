# -*- coding: utf-8 -*-
"""No Arabic on the screen when the reader picked English.

The site is bilingual, and the way it drifts is always the same: a new string
gets added on one side only. This renders every page in both languages and
fails on any Arabic that reaches an English page.

Three things are deliberately allowed through: the toggle that switches back
to Arabic, stored values (a client's own name, a cuisine key inside a form
value), and the paired name on the food pages, which show the English name
with the Arabic beneath it because that table is a bilingual reference. Meal text and condition names are NOT allowed: those are stored in
Arabic on purpose and have to be translated on the way out.

Run with:  python3 tests/test_translation.py
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
if os.path.exists("/tmp/nutrax.db"):
    os.remove("/tmp/nutrax.db")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A  # noqa: E402
import meal_database as md  # noqa: E402
from meal_i18n import translate_meal, untranslated_terms  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

ARABIC = re.compile(r"[؀-ۿ]")
# the language toggle names the other language in its own script, as it should
ALLOWED = {"عربي", "العربية", "ذكر", "أنثى"}


def _mk(name, email, role, **cols):
    row = A.db_row("SELECT id FROM users WHERE email=?", (email,))
    if row:
        return row["id"]
    keys = ["name", "email", "password", "role", "active"] + list(cols)
    vals = [name, email, generate_password_hash("pw"), role, 1] + list(cols.values())
    A.db_run(f"INSERT INTO users ({','.join(keys)}) VALUES ({','.join(['?']*len(keys))})",
             tuple(vals))
    return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]


ADMIN = _mk("Admin", "a@t.test", "admin", is_admin=1, onboarded_at=datetime.now())
CLIENT = _mk("Client", "c@t.test", "client", onboarded_at=datetime.now(),
             height=170, weight=80, age=30, gender="ذكر",
             conditions=json.dumps(["سكري النوع الثاني"], ensure_ascii=False))

if not A.db_row("SELECT id FROM payments WHERE user_id=?", (CLIENT,)):
    A.db_run("INSERT INTO payments (user_id,stripe_session_id,plan_key,status,currency,amount,expires_at) "
             "VALUES (?,?,?,?,?,?,?)",
             (CLIENT, "seed", "monthly_subscription", "completed", "EGP", 50000,
              datetime.now() + timedelta(days=20)))

if not A.db_row("SELECT id FROM plan_requests WHERE client_id=?", (CLIENT,)):
    _d = {"goal_type": "weight_loss", "culture": "مصري", "goal_cal": 1600,
          "gender": "ذكر", "height": 170, "weight": 80, "age": 30,
          "diet_plan_type": "standard", "symptoms": ["سكري النوع الثاني"], "notes": ""}
    A.db_run("INSERT INTO plan_requests (client_id,client_name,status,request_data,plan_data) "
             "VALUES (?,?,?,?,?)",
             (CLIENT, "Client", "approved", json.dumps(_d, ensure_ascii=False),
              json.dumps({"data": _d, "plan": []}, ensure_ascii=False)))

ADMIN_PAGES = ["/dashboard", "/admin/requests", "/admin/users", "/admin/payments",
               "/admin/blocked", "/admin/notifications", "/patients", "/generate",
               "/saved", "/settings", "/clinical", "/knowledge", "/analyzer",
               "/history", "/daily-tips", "/change-password"]
CLIENT_PAGES = ["/my-plan", "/request-plan", "/my-plans-history", "/settings",
                "/analyzer", "/knowledge", "/daily-tips", "/pricing"]
PUBLIC_PAGES = ["/", "/login", "/foods", "/foods/chicken-breast", "/pricing",
                "/terms", "/privacy"]


def visible_arabic(html):
    """Arabic in text the reader actually sees."""
    h = re.sub(r"<(script|style).*?</\1>", "", html, flags=re.S)
    # <option value="مصري"> keeps a stored key; the label is what matters
    h = re.sub(r'<option[^>]*value="[^"]*"[^>]*>.*?</option>', "", h, flags=re.S)
    # the food pages are a bilingual reference: each food shows the English name
    # with the Arabic beneath it on purpose. Those two labels are the only place
    # the other language is meant to appear.
    h = re.sub(r'<[^>]+class="(?:pf-sub|fd-alt)"[^>]*>.*?</[a-z]+>', "", h, flags=re.S)
    out = []
    for line in re.sub(r"<[^>]+>", "\n", h).split("\n"):
        line = " ".join(line.split())
        if line and ARABIC.search(line) and line not in ALLOWED:
            out.append(line)
    return out


def _client(uid=None, role=None, lang="en"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["lang"] = lang
        if uid:
            s["uid"] = uid
            s["role"] = role
    return c


def _sweep(uid, role, paths):
    c = _client(uid, role, "en")
    leaks = {}
    for p in paths:
        r = c.get(p, follow_redirects=True)
        assert r.status_code == 200, f"{p} returned {r.status_code} in English"
        found = visible_arabic(r.get_data(as_text=True))
        if found:
            leaks[p] = found[:3]
    return leaks


def test_public_pages_are_english():
    leaks = _sweep(None, None, PUBLIC_PAGES)
    assert not leaks, f"Arabic left on public pages in English mode: {leaks}"


def test_client_pages_are_english():
    leaks = _sweep(CLIENT, "client", CLIENT_PAGES)
    assert not leaks, f"Arabic left on client pages in English mode: {leaks}"


def test_staff_pages_are_english():
    leaks = _sweep(ADMIN, "admin", ADMIN_PAGES)
    assert not leaks, f"Arabic left on staff pages in English mode: {leaks}"


def test_arabic_mode_still_arabic():
    """The other direction: English mode must not have flattened the Arabic."""
    c = _client(ADMIN, "admin", "ar")
    for p in ("/dashboard", "/generate", "/daily-tips"):
        html = c.get(p, follow_redirects=True).get_data(as_text=True)
        assert visible_arabic(html), f"{p} lost its Arabic"


def test_every_meal_in_the_database_translates():
    """A meal with no English falls back to Arabic, which would show up as a
    leak on an English plan. The glossary has to cover the whole database."""
    meals = set()
    for pool in ("WEIGHT_LOSS", "MUSCLE_GAIN", "BULKING", "MAINTENANCE",
                 "SAFE_ALTERNATIVES", "KETO_MEALS", "KETO_SNACKS"):
        node = getattr(md, pool, None)
        if node is None:
            try:
                import meal_extra
                node = getattr(meal_extra, pool, None)
            except ImportError:
                node = None
        stack = [node]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                if isinstance(cur.get("meal"), str):
                    meals.add(cur["meal"])
                else:
                    stack.extend(cur.values())
            elif isinstance(cur, (list, tuple)):
                stack.extend(cur)
            elif isinstance(cur, str) and ARABIC.search(cur):
                meals.add(cur)
    assert meals, "found no meals to check"
    missing = {m: untranslated_terms(m) for m in meals if untranslated_terms(m)}
    assert not missing, f"{len(missing)} meals have untranslated terms, e.g. {list(missing.items())[:2]}"


def test_translated_meals_keep_their_numbers():
    """Quantities must survive translation -- a plan is useless without them."""
    for meal in ("🍗 صدر دجاج مشوي 150جم + 🍚 ارز بني 100جم",
                 "🥚 بيض مسلوق 2 + 🧀 جبن قريش 60جم"):
        en = translate_meal(meal)
        assert not ARABIC.search(en), f"not fully translated: {en}"
        for num in re.findall(r"\d+", meal):
            assert num in en, f"quantity {num} lost from {en}"


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

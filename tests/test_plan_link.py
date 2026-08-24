# -*- coding: utf-8 -*-
"""A plan link is health data behind nothing but an unguessable string.

/p/<token> shows a named client's weekly plan, their calorie target and the
conditions it was filtered for, to anyone holding the link -- no account, no
login. That is deliberate: sharing a URL works on every browser, while
sharing a file quietly does not. But it means the token IS the security, and
these lock in what that requires.

Run with:  python3 tests/test_plan_link.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")

import app as A  # noqa: E402
import core  # noqa: E402

DATA = {
    "name": "أحمد على", "phone": "01012345678", "age": "32", "gender": "ذكر",
    "height": "176", "weight": "95", "tdee": "2350", "goal_cal": "1750",
    "goal_type": "weight_loss", "culture": "مصري", "diet_plan_type": "standard",
    "symptoms": ["سكري النوع الثاني"], "client_key": "احمد علي|345678",
    "visit_notes": "ملاحظة داخلية للدكتور", "avoid_meals": ["بيض مسلوق 2"],
}
PLAN = [{"day": "الاحد", "breakfast": "بيض مسلوق 2", "lunch": "دجاج مشوي",
         "dinner": "زبادي", "snack": "تفاحة", "total_cal": 1200, "total_p": 90}]


def _link():
    with A.app.test_request_context("/"):
        return core.create_plan_link(1, DATA, PLAN)


def test_a_token_is_short_but_not_guessable():
    token = _link()
    assert token, "no link was created"
    assert len(token) == core._LINK_LEN
    assert re.fullmatch(r"[A-Za-z0-9]+", token), "token is not url-safe"

    # no characters that get misread when someone reads a link aloud
    assert not (set(token) & set("0O1lI")), f"ambiguous characters in {token}"

    # the search space has to be far beyond guessing: this is medical data
    import math
    bits = core._LINK_LEN * math.log2(len(core._LINK_ALPHABET))
    assert bits >= 64, f"only {bits:.0f} bits of entropy in a token"

    # and two links must never collide
    assert len({_link() for _ in range(40)}) == 40


def test_the_link_shows_the_plan_to_someone_with_no_account():
    token = _link()
    c = A.app.test_client()          # no session at all
    r = c.get(f"/p/{token}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "أحمد على" in body
    assert "بيض مسلوق 2" in body, "the meals are missing"
    assert "1750" in body, "the calorie target is missing"


def test_a_shared_plan_never_carries_the_private_fields():
    """The link travels through WhatsApp and gets forwarded. Anything not
    shown on the page has no business being stored in it."""
    token = _link()
    row = core.get_plan_link(token)
    stored = json.loads(row["data_json"])
    for leaked in ("phone", "client_key", "visit_notes", "avoid_meals"):
        assert leaked not in stored, f"{leaked} was stored in a public link"

    body = A.app.test_client().get(f"/p/{token}").get_data(as_text=True)
    assert "01012345678" not in body, "the client's phone number is on the page"
    assert "ملاحظة داخلية للدكتور" not in body, "a private note is on the page"


def test_the_page_refuses_to_be_indexed():
    token = _link()
    body = A.app.test_client().get(f"/p/{token}").get_data(as_text=True)
    robots = re.search(r'<meta name="robots" content="([^"]+)"', body)
    assert robots and "noindex" in robots.group(1), "the plan page allows indexing"
    assert "nofollow" in robots.group(1)

    txt = A.app.test_client().get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /p/" in txt, "crawlers are not told to stay out of /p/"

    sitemap = A.app.test_client().get("/sitemap.xml").get_data(as_text=True)
    assert "/p/" not in sitemap, "a plan link leaked into the sitemap"


def test_a_wrong_token_gives_nothing_away():
    c = A.app.test_client()
    for bad in ("aaaaaaaaaaaa", "x", "../../etc/passwd", "%00", "a" * 200, ""):
        r = c.get(f"/p/{bad}")
        assert r.status_code in (404, 308, 405), f"{bad!r} returned {r.status_code}"
        if r.status_code == 404:
            assert "أحمد" not in r.get_data(as_text=True)


def test_a_revoked_or_expired_link_stops_working():
    import datetime as dt

    token = _link()
    assert core.get_plan_link(token) is not None
    core.db_run("UPDATE plan_links SET revoked=1 WHERE token=?", (token,))
    assert core.get_plan_link(token) is None, "a revoked link still opens"
    assert A.app.test_client().get(f"/p/{token}").status_code == 404

    token2 = _link()
    past = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    core.db_run("UPDATE plan_links SET expires_at=? WHERE token=?", (past, token2))
    assert core.get_plan_link(token2) is None, "an expired link still opens"
    assert A.app.test_client().get(f"/p/{token2}").status_code == 404


def test_the_client_can_download_the_pdf_without_logging_in():
    token = _link()
    r = A.app.test_client().get(f"/p/{token}/pdf")
    assert r.status_code == 200, f"pdf download returned {r.status_code}"
    assert r.mimetype == "application/pdf"
    assert r.get_data()[:5] == b"%PDF-", "that is not a PDF"


def test_only_staff_can_mint_a_link():
    before = core.db_row("SELECT COUNT(*) AS c FROM plan_links")["c"]

    # without a CSRF token the request never reaches the view at all
    c = A.app.test_client()
    assert c.post("/api/plan-link").status_code == 400

    # and with a valid one it still has to get past the login wall
    c2 = A.app.test_client()
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                    c2.get("/login").get_data(as_text=True)).group(1)
    r = c2.post("/api/plan-link", data={"csrf_token": tok})
    assert r.status_code in (302, 401, 403), (
        f"an anonymous visitor reached the link endpoint ({r.status_code})")

    after = core.db_row("SELECT COUNT(*) AS c FROM plan_links")["c"]
    assert after == before, "an anonymous request created a plan link"


def test_views_are_counted_so_the_doctor_knows_it_arrived():
    token = _link()
    c = A.app.test_client()
    for _ in range(3):
        c.get(f"/p/{token}")
    assert core.get_plan_link(token)["views"] == 3


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

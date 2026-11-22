# -*- coding: utf-8 -*-
"""‏صفحة الإشعارات: مرتبة بالأيام، ووقت مفهوم، وكل صف بيفتح.

‏صاحب المشروع: "ظبط شكل صفحة الإشعارات". اللي كان فيها:
  ‏- كل إشعار كارت كبير لوحده؛ سبع إشعارات ملوا الصفحة.
  ‏- النوع مكتوب مرتين (شارة "طلب خطة" فوق عنوان "طلب خطة جديدة").
  ‏- الوقت "2026-11-22 09:29" -- وبتوقيت جرينتش: الإشعار بيتسجّل
    CURRENT_TIMESTAMP، فاللي حصل الساعة ١١ في القاهرة كان مكتوب ٩.
  ‏- أسماء الأنواع عربي بس حتى في الصفحة الإنجليزي.
  ‏- رابط "افتح ←" صغير، والكارت نفسه مابيفتحش.

Run with:  python3 tests/test_notifications_page.py
"""

import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_notif_page_test.db"
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

import app as A  # noqa: E402
import notifications as N  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
TZ = "Africa/Cairo"                       # ‏+٢ طول السنة
NOW_UTC = datetime(2026, 11, 22, 10, 0)   # ‏١٢ الضهر في القاهرة


def _row(type_, minutes_ago, read=0, link="/x", title="عنوان", message="رسالة"):
    return {"id": minutes_ago, "type": type_, "title": title, "message": message,
            "link": link, "is_read": read, "created_at": NOW_UTC - timedelta(minutes=minutes_ago)}


# ── التجهيز ─────────────────────────────────────────────────────────

def test_grouped_by_day_in_the_users_timezone():
    rows = [_row("plan_request", 12), _row("new_message", 60 * 9),
            # ‏١١:٣٠ مساءً جرينتش امبارح = ١:٣٠ صباحاً النهارده في القاهرة
            _row("new_client", 60 * 10 + 30),
            _row("booking_request", 60 * 24), _row("other", 60 * 24 * 4), _row("other", 60 * 24 * 30)]
    groups = N.present(rows, TZ, "ar", now_utc=NOW_UTC)
    assert [g["label"] for g in groups] == ["النهارده", "امبارح", "الأسبوع ده", "أقدم"], groups
    assert len(groups[0]["items"]) == 3, [i["title"] for i in groups[0]["items"]]


def test_time_reads_like_a_person_would_say_it():
    rows = [_row("plan_request", 12), _row("plan_request", 60 * 3), _row("plan_request", 60 * 24)]
    items = [i for g in N.present(rows, TZ, "ar", now_utc=NOW_UTC) for i in g["items"]]
    assert items[0]["when"] == "من 12 دقيقة", items[0]["when"]
    assert items[1]["when"] == "من 3 ساعات", items[1]["when"]
    assert re.match(r"^\d{1,2}:\d{2} (ص|م)$", items[2]["when"]), items[2]["when"]
    en = [i for g in N.present(rows, TZ, "en", now_utc=NOW_UTC) for i in g["items"]]
    assert en[0]["when"] == "12 min ago" and en[1]["when"] == "3 h ago", en[:2]


def test_every_type_has_a_label_in_both_languages_and_a_line_icon():
    for type_ in list(N.NOTIF_TYPES) + ["something_new"]:
        ar = N.present([_row(type_, 5)], TZ, "ar", now_utc=NOW_UTC)[0]["items"][0]
        en = N.present([_row(type_, 5)], TZ, "en", now_utc=NOW_UTC)[0]["items"][0]
        assert ar["label"] and en["label"] and ar["label"] != en["label"], type_
        assert re.match(r"^[\x00-\x7f]+$", en["label"]), en["label"]
        assert ar["icon"].startswith("fa-"), ar["icon"]
        assert ar["cat"] in ("requests", "messages", "bookings", "clients", "payments", "other")


# ── الصفحة ──────────────────────────────────────────────────────────

def _seed():
    A.db_run("DELETE FROM notifications")
    for t, title, link, read in (("plan_request", "طلب خطة جديدة", "/admin/requests", 0),
                                 ("new_message", "رسالة جديدة من كريم", "/messages", 1),
                                 ("payment_click", "ضغط دفع", None, 1)):
        A.db_run("INSERT INTO notifications (type,title,message,link,is_read) VALUES (?,?,?,?,?)",
                 (t, title, "تفاصيل", link, read))


def _page():
    c = A.app.test_client()
    c.post("/login", data={"action": "login", "email": "admin@nutrax.com", "password": "pw123456"})
    return c, c.get("/admin/notifications").get_data(as_text=True)


def test_a_row_with_a_link_opens_by_itself():
    _seed()
    _c, html = _page()
    assert re.search(r'<a class="nt-row[^"]*"[^>]*href="/admin/requests"', html), "الصف مابيفتحش"
    assert re.search(r'<div class="nt-row[^"]*"', html), "الإشعار اللي من غير لينك اختفى"
    assert "افتح ←" not in html


def test_new_is_said_not_only_coloured():
    _seed()
    _c, html = _page()
    row = re.search(r'<a class="nt-row unread"[^>]*>(.*?)</a>', html, re.S)
    assert row and re.search(r'class="sr-only"[^>]*>\s*جديد', row.group(1)), row and row.group(1)[:300]


def test_filters_by_kind():
    _seed()
    _c, html = _page()
    chips = re.findall(r'<button[^>]*class="nt-chip[^"]*"[^>]*>', html)
    assert len(chips) >= 3 and all("aria-pressed" in c for c in chips), chips
    assert re.search(r'data-cat="requests"', html)


def test_no_emoji_icons_left():
    _seed()
    _c, html = _page()
    body = html.split('class="nt-wrap"', 1)[1].split("<footer", 1)[0]
    for e in ("📋", "💬", "💰", "🔔", "🔕", "🆕", "📅", "💵"):
        assert e not in body, e


def test_the_empty_page_still_says_so():
    A.db_run("DELETE FROM notifications")
    _c, html = _page()
    assert "مفيش إشعارات لسه" in html


def test_marking_all_read_still_works():
    _seed()
    c, _html = _page()
    c.post("/admin/notifications/read")
    assert A.db_row("SELECT COUNT(*) AS n FROM notifications WHERE is_read=0")["n"] == 0


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
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

# -*- coding: utf-8 -*-
"""‏الرسائل: قايمة مترتبة بآخر رسالة، ومحادثة بتقرا زي برامج الشات.

‏صاحب المشروع: "ظبط شكل صفحة الرسائل، عايزها احترافية". اللي كان فيها:
  ‏- القايمة كل العملاء بالترتيب الأبجدي -- اللي بعت دلوقتي ممكن يبقى
    في الآخر -- ومن غير وقت ولا بحث. وكانت بتعمل استعلامين لكل عميل:
    ٢٠٠ عميل = ٤٠٠ طلب للقاعدة في كل فتحة.
  ‏- خانة الكتابة سطر واحد، والرسالة اللي فيها سطور بتتلزق.
  ‏- الوقت بتوقيت جرينتش ومن غير فاصل أيام، ومفيش علامة إن الرسالة اتقرت
    مع إن is_read متسجّل.
  ‏- دور العميل مكتوب "client" بالإنجليزي في الصفحة العربي.
  ‏- الدكتور بيرجع للقايمة عشان يفتح محادثة تانية.

Run with:  python3 tests/test_messages_page.py
"""

import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_messages_page_test.db"
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

import app as A  # noqa: E402
import messages_view as MV  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
A.db_run("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, "
         "receiver_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
ADMIN = A.db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")["id"]


def _mk(name, email):
    A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) VALUES (?,?,?,'client',1,?)",
             (name, email, generate_password_hash("pw123456"), datetime.now()))
    uid = A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]
    A.db_run("INSERT INTO subscriptions (user_id,status,current_period_end) VALUES (?,?,?)",
             (uid, "active", datetime.now() + timedelta(days=30)))
    return uid


AYA = _mk("آية", "aya@m.test")        # ‏أبجدياً الأولى، وآخر رسالة منها قديمة
ZEINAB = _mk("زينب", "zeinab@m.test")  # ‏أبجدياً الأخيرة، وبعتت دلوقتي
OMAR = _mk("عمر", "omar@m.test")      # ‏مفيش رسائل خالص
NOW = datetime.utcnow()


def _say(frm, to, text, minutes_ago, read=0):
    A.db_run("INSERT INTO messages (sender_id,receiver_id,message,is_read,created_at) VALUES (?,?,?,?,?)",
             (frm, to, text, read, (NOW - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")))


_say(AYA, ADMIN, "صباح الخير يا دكتور", 60 * 30, read=1)
_say(ADMIN, AYA, "صباح النور", 60 * 29, read=1)
_say(ADMIN, AYA, "ابعتيلي وزن النهارده", 60 * 28, read=0)
_say(ZEINAB, ADMIN, "دكتور ينفع أبدّل العشا؟\nعندي عزومة", 5)


def _unread_again():
    """‏فتح محادثة بيعلّم رسايلها مقروءة -- فالاختبارات اللي بتعدّ غير
    المقروء بترجّع رسالة زينب لحالتها الأول."""
    A.db_run("UPDATE messages SET is_read=0 WHERE sender_id=?", (ZEINAB,))


def _as(email):
    c = A.app.test_client()
    c.post("/login", data={"action": "login", "email": email, "password": "pw123456"})
    return c


def _names_in_order(html):
    return re.findall(r'class="ms-name"[^>]*>([^<]+)<', html)


# ── القايمة ─────────────────────────────────────────────────────────

def test_the_list_puts_the_latest_conversation_first():
    html = _as("admin@nutrax.com").get("/messages").get_data(as_text=True)
    names = _names_in_order(html)
    assert names[:2] == ["زينب", "آية"], names
    assert "عمر" in names and names.index("عمر") > 1, names


def test_the_list_is_built_without_a_query_per_client():
    _unread_again()
    rows = A.db_rows("SELECT * FROM messages")
    clients = A.db_rows("SELECT * FROM users WHERE role='client'")
    convs = MV.conversations(ADMIN, rows, clients, "Africa/Cairo", "ar", now_utc=NOW)
    first = convs[0]
    assert first["user"]["id"] == ZEINAB and first["unread"] == 1, first
    assert first["when"] == "من 5 دقايق", first["when"]
    assert first["last"].startswith("دكتور ينفع"), first["last"]
    assert convs[1]["mine_last"] is True        # ‏آخر رسالة لآية كانت من الدكتور


def test_unread_is_said_not_only_coloured_and_there_is_a_search():
    _unread_again()
    html = _as("admin@nutrax.com").get("/messages").get_data(as_text=True)
    row = re.search(r'<a class="ms-row unread"[^>]*>(.*?)</a>', html, re.S)
    assert row and re.search(r'class="sr-only"[^>]*>[^<]*غير مقروء', row.group(1)), row and row.group(1)[:300]
    assert re.search(r'<input[^>]*type="search"[^>]*aria-label="', html)


# ── المحادثة ────────────────────────────────────────────────────────

def test_a_thread_has_days_clock_times_and_read_ticks():
    rows = A.db_rows("SELECT * FROM messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) "
                     "ORDER BY created_at", (ADMIN, AYA, AYA, ADMIN))
    items = MV.thread(rows, ADMIN, "Africa/Cairo", "ar", now_utc=NOW)
    days = [i["day"] for i in items if i.get("day")]
    assert days == ["امبارح"], days
    msgs = [i for i in items if not i.get("day")]
    assert msgs[0]["mine"] is False and msgs[1]["mine"] is True
    assert msgs[1]["read"] is True and msgs[2]["read"] is False
    assert re.match(r"^\d{1,2}:\d{2} (ص|م)$", msgs[0]["clock"]), msgs[0]["clock"]


def test_times_are_the_users_local_time():
    rows = [{"id": 1, "sender_id": AYA, "receiver_id": ADMIN, "message": "x", "is_read": 1,
             "created_at": "2026-11-22 08:00:00"}]
    items = MV.thread(rows, ADMIN, "Africa/Cairo", "ar", now_utc=datetime(2026, 11, 22, 12, 0))
    assert items[-1]["clock"] == "10:00 ص", items[-1]["clock"]


def test_the_doctors_chat_keeps_the_list_beside_it_and_links_the_profile():
    html = _as("admin@nutrax.com").get("/messages/%d" % ZEINAB).get_data(as_text=True)
    assert 'class="ms-list' in html, "القايمة مش جنب المحادثة"
    assert 'href="/admin/users/%d"' % ZEINAB in html
    assert re.search(r'<a class="ms-row[^"]*active[^"]*"[^>]*href="/messages/%d"' % ZEINAB, html)


def test_the_clients_chat_is_just_the_chat():
    html = _as("aya@m.test").get("/messages/%d" % ADMIN).get_data(as_text=True)
    assert 'class="ms-list' not in html and "/admin/users/" not in html
    assert "ابعتيلي وزن النهارده" in html


def test_a_message_keeps_its_lines_and_the_box_takes_lines():
    html = _as("admin@nutrax.com").get("/messages/%d" % ZEINAB).get_data(as_text=True)
    assert re.search(r'\.ms-text\{[^}]*white-space:pre-wrap', html), "السطور بتتلزق"
    box = re.search(r'<textarea[^>]*name="message"[^>]*>', html)
    assert box and 'aria-label="' in box.group(0), box


def test_the_role_reads_in_the_pages_language():
    html = _as("admin@nutrax.com").get("/messages/%d" % ZEINAB).get_data(as_text=True)
    head = html.split('class="ms-chat-head"', 1)[1].split("</header>", 1)[0]
    assert ">client<" not in head and "عميل" in head, head[:400]


def test_no_emoji_in_the_pages():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("messages_list.html", "chat.html"):
        text = open(os.path.join(root, "templates", name), encoding="utf-8").read()
        for e in ("💬", "👋", "⚡", "✅"):
            assert e not in text, (name, e)


def test_sending_still_works_and_still_notifies():
    before = A.db_row("SELECT COUNT(*) AS n FROM notifications WHERE type='new_message'")["n"]
    r = _as("aya@m.test").post("/messages/%d" % ADMIN, data={"message": "تمام\nوزني ٧٠"})
    assert r.status_code == 302
    assert A.db_row("SELECT message FROM messages ORDER BY id DESC LIMIT 1")["message"] == "تمام\nوزني ٧٠"
    assert A.db_row("SELECT COUNT(*) AS n FROM notifications WHERE type='new_message'")["n"] == before + 1
    # ‏يمسح رسالته: باقي الاختبارات بتعتمد على مين آخر واحد بعت
    A.db_run("DELETE FROM messages WHERE id=(SELECT MAX(id) FROM messages)")


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

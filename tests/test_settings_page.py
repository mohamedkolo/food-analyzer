# -*- coding: utf-8 -*-
"""‏صفحة الإعدادات: مرتبة، ومناسبة للي فاتحها.

‏صاحب المشروع: "عايز يتظبط شكل الإعدادات". اللي كان فيها:
  ‏- الأدمن بيتسأل عن طوله ووزنه وهدفه ومستوى نشاطه -- دي بيانات عميل،
    والدكتور مالوش هدف يتحسب.
  ‏- خانة الطول step="0.5" والوزن step="0.1": README قاعدة ٣ -- أي قيد
    خطوة بيخلّي الخانة مرفوضة لرقم زي 70.25، والمتصفح مابيبعتش الفورم
    أصلاً، فالزرار بيموت ساكت.
  ‏- عناوين بإيموجي، وزرار كلمة السر بشكل غير باقي الأزرار، وكارتين
    فوق بعض والنص التاني من الصفحة فاضي.

Run with:  python3 tests/test_settings_page.py
"""

import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_settings_test.db"
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

import app as A  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at,height,weight,age,gender,goal,activity)"
         " VALUES (?,?,?,'client',1,?,?,?,?,?,?,?)",
         ("سلمى", "salma@x.test", generate_password_hash("pw123456"), datetime.now(),
          165, 72.5, 30, "أنثى", "fat_loss", 1.375))
TEMPLATE = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "templates", "settings.html"), encoding="utf-8").read()


def _as(email):
    c = A.app.test_client()
    c.post("/login", data={"action": "login", "email": email, "password": "pw123456"})
    return c


def _page(email):
    return _as(email).get("/settings").get_data(as_text=True)


def test_the_doctor_is_not_asked_for_their_weight():
    html = _page("admin@nutrax.com")
    assert 'name="weight"' not in html and 'name="goal"' not in html, "الأدمن لسه بيتسأل عن وزنه"


def test_a_client_still_keeps_their_body_data():
    html = _page("salma@x.test")
    for field in ("height", "weight", "age", "gender", "goal", "activity"):
        assert 'name="%s"' % field in html, field
    weight = A.db_row("SELECT weight FROM users WHERE email='salma@x.test'")["weight"]
    assert 'value="%s"' % ("%g" % float(weight)) in html, weight


def test_a_client_can_still_save():
    c = _as("salma@x.test")
    r = c.post("/settings", data={"height": "166", "weight": "70.25", "age": "30", "gender": "أنثى",
                                  "goal": "fat_loss", "activity": "1.375"})
    assert r.status_code == 200
    row = A.db_row("SELECT weight, height FROM users WHERE email='salma@x.test'")
    assert float(row["weight"]) == 70.25 and float(row["height"]) == 166, row


def test_number_boxes_take_any_decimal():
    """‏README قاعدة ٣."""
    for box in re.findall(r'<input[^>]*type="number"[^>]*>', TEMPLATE):
        assert 'step="any"' in box, box


def _content(html):
    """‏الصفحة نفسها من غير الهيدر -- الهيدر فيه لغة ووضع غامق أصلاً."""
    return html.split('class="page-title"', 1)[1]


def test_everyone_gets_the_preferences_and_security():
    for email in ("admin@nutrax.com", "salma@x.test"):
        html = _content(_page(email))
        assert re.search(r'href="/lang/(ar|en)"', html), (email, "مفيش تغيير اللغة")
        assert "data-theme-toggle" in html, (email, "مفيش الوضع الغامق")
        assert 'href="/change-password"' in html, email


def test_the_headings_use_line_icons_not_emoji():
    heads = re.findall(r'class="st-sec-title"[^>]*>(.*?)</', TEMPLATE, re.S)
    assert heads, "مفيش عناوين أقسام"
    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
    assert not any(emoji.search(h) for h in heads), heads
    assert not emoji.search(TEMPLATE.split("<h1", 1)[1].split("</h1>", 1)[0])


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

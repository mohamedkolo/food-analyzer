# -*- coding: utf-8 -*-
"""‏القايمة الجانبية بشكل "Liquid Button": حبوب زجاج على كحلي، وكل مجموعة
ليها لون سائل بيملا الزرار من تحت مع موجة لما تقف عليه، وأرضية القايمة
بتميل للون ده.

‏اللي الاختبارات دي بتحرسه:
  ‏- كل عنصر في القايمة (للطاقم وللعميل) حبّة زجاج بلون من الخمسة.
  ‏- الأيقونات خط رفيع أبيض بنفس المقاس، مش أيقونات Font Awesome المصمتة.
  ‏- الكلام على كل لون سائل مقروء (تباين ٤.٥ على الأقل).
  ‏- الصفحة اللي إنت فيها بتفضل مليانة باللون، فتعرف إنت فين.
  ‏- تقليل الحركة بيوقّف الموجة.

Run with:  python3 tests/test_liquid_nav.py
"""

import os
import re
import sys
from datetime import datetime

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_liquid_nav.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app as A  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
ADMIN = A.db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")["id"]
A.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) VALUES (?,?,?,'client',1,?)",
         ("Lina", "lina@x.test", generate_password_hash("pw123456"), datetime.now()))
CLIENT = A.db_row("SELECT id FROM users WHERE email='lina@x.test'")["id"]

COLOURS = {"blue", "amber", "teal", "violet", "red"}
BASE = open(os.path.join(ROOT, "templates", "base.html"), encoding="utf-8").read()


def _page(uid, url):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = uid
    return c.get(url, follow_redirects=True).get_data(as_text=True)


def _sidebar(html):
    i = html.index('<nav class="sidebar"')
    return html[i:html.index("</nav>", i)]


def _items(nav):
    """كل عنصر بيتداس: لينك أو زرار nav-item، أو عنوان مجموعة."""
    return re.findall(r'<(?:a|button|summary)\b[^>]*class="[^"]*\b(?:nav-item|nav-grp-s)\b[^"]*"[^>]*>', nav)


def _lum(hx):
    hx = hx.lstrip("#")
    ch = [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_every_staff_menu_item_is_a_liquid_pill():
    nav = _sidebar(_page(ADMIN, "/dashboard"))
    items = _items(nav)
    assert len(items) >= 15, len(items)
    for tag in items:
        assert re.search(r'\blq\b', tag), tag
        m = re.search(r'data-lq="(\w+)"', tag)
        assert m and m.group(1) in COLOURS, tag


def test_every_client_menu_item_is_a_liquid_pill():
    nav = _sidebar(_page(CLIENT, "/my-plan"))
    items = _items(nav)
    # ‏الدكتور (٢٦ نوفمبر): قايمة العميل أربع وجهات + خروج.
    assert len(items) == 5, len(items)
    for tag in items:
        m = re.search(r'data-lq="(\w+)"', tag)
        assert m and m.group(1) in COLOURS, tag


def test_each_pill_carries_its_liquid():
    nav = _sidebar(_page(ADMIN, "/dashboard"))
    assert nav.count('class="lq-fill"') == len(_items(nav))
    assert re.search(r'<span class="lq-fill" aria-hidden="true">', nav)


def test_icons_are_thin_white_lines_of_one_size():
    for uid, url in ((ADMIN, "/dashboard"), (CLIENT, "/my-plan")):
        nav = _sidebar(_page(uid, url))
        assert "fa-solid" not in nav, re.findall(r'fa-solid [\w-]+', nav)[:5]
        icons = re.findall(r'<svg class="nx-ic"[^>]*>', nav)
        assert len(icons) >= 5
        for svg in icons:
            assert 'stroke-width="1.5"' in svg and 'width="20"' in svg and 'height="20"' in svg, svg
            assert 'aria-hidden="true"' in svg and 'fill="none"' in svg, svg


def test_text_on_each_liquid_is_readable():
    pairs = dict(re.findall(r"--lq-(\w+):(#[0-9A-Fa-f]{6})", BASE))
    inks = dict(re.findall(r"--lq-(\w+)-ink:(#[0-9A-Fa-f]{6})", BASE))
    assert set(inks) == COLOURS, inks
    for name in COLOURS:
        assert _ratio(pairs[name], inks[name]) >= 4.5, (name, pairs[name], inks[name])


def test_the_page_you_are_on_stays_filled():
    nav = _sidebar(_page(ADMIN, "/dashboard"))
    assert re.search(r'<a href="/dashboard" class="[^"]*\bactive\b', nav)
    assert re.search(r"\.lq\.active \.lq-fill\{[^}]*height:100%", BASE)


def test_the_menu_leans_toward_the_hovered_colour():
    for name in COLOURS:
        assert re.search(r'\.sidebar:has\(\[data-lq="%s"\]:hover\)' % name, BASE), name


def test_reduced_motion_stops_the_wave():
    block = BASE[BASE.index("prefers-reduced-motion"):]
    assert ".lq-wave" in block[:600]


# ═══ مراجعة التصميم: التصليحات ═══

def test_waves_hide_until_the_pill_fills():
    # ‏الموجة كانت قاعدة على قاع كل زرار حتى من غير hover: شريط ألوان
    # تحت القايمة كلها.
    assert re.search(r"\.lq-wave\{[^}]*opacity:0", BASE)
    assert re.search(r"\.lq:hover \.lq-wave[^{]*\{[^}]*opacity:1", BASE)


def test_the_phone_drawer_clears_the_bottom_bar():
    i = BASE.index("@media(max-width:768px){")
    block = BASE[i:BASE.index("\n}", i)]
    assert re.search(r"\.sidebar\{[^}]*padding-bottom:calc\(", block), block[:400]


def test_no_group_repeats_its_own_name_as_its_first_item():
    nav = _sidebar(_page(ADMIN, "/dashboard"))
    text = lambda h: re.sub(r"<[^>]+>|\{\{.*?\}\}", "", h).split()
    for summary, body in re.findall(r"<summary[^>]*>(.*?)</summary>\s*<div class=\"nav-grp-body\">(.*?)</a>", nav, re.S):
        assert text(summary)[:1] != text(body)[:1], text(summary)


def test_the_group_holding_this_page_shows_some_liquid():
    assert re.search(r"\.nav-grp\.has-active > summary \.lq-fill\{[^}]*height:", BASE)



# ═══ اللاج على جهاز الشغل ═══
#
# ‏صاحب المشروع: الموقع على التليفون سريع، وعلى جهاز الشغل "الأمواج اللي
# في الجنب فيها لاج". اتقاس على متصفح من غير كارت شاشة ومعالج أبطأ ٦
# مرات: الداشبورد واقفة من غير ما حد يلمسها كانت ٢٦-٢٨ فريم في الثانية
# بدل ٦٠ -- القايمة كانت بترسم طول الوقت:
#   ‏- بقعتين لون متغبّشين (blur 52px) ورا الزجاج بيتحركوا على طول، فكل
#     زرار زجاج (backdrop-filter، حوالي ١٠) بيتعاد تغبيشه كل فريم.
#   ‏- حوالي ٢٠ موجة بتتحرك حتى وهي مخفية (opacity:0).

def test_the_colour_behind_the_glass_stands_still():
    m = re.search(r"\.sidebar::before,\.sidebar::after\{([^}]*)\}", BASE)
    assert m, "البقع ورا الزجاج اختفت"
    assert "animation" not in m.group(1), m.group(1)


def test_a_wave_only_moves_while_it_is_seen():
    assert re.search(r"\.lq-wave\{[^}]*animation-play-state:paused", BASE), "الموجة المخفية لسه بتتحرك"
    m = re.search(r"([^{}]*)\{[^}]*animation-play-state:running", BASE)
    assert m, "الموجة مابتتحركش خالص"
    for shown in (".lq:hover .lq-wave", ".lq:focus-visible .lq-wave", ".nav-grp.has-active > summary .lq-wave"):
        assert shown in m.group(1), (shown, m.group(1))

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

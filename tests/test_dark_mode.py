# -*- coding: utf-8 -*-
"""‏الوضع الغامق للموقع كله.

‏أول زيارة بتمشي على إعداد الجهاز (فاتح أو غامق)، وزرار شمس/قمر في الهيدر
بيغيّره والاختيار بيتحفظ. الألوان بقت أسامي بمعنى (سطح، كلام، حدود، تحذير...)
ولكل اسم قيمة فاتحة وقيمة غامقة -- بدل ~٢٠٠٠ لون مكتوب بالإيد في ٦٦ صفحة.

‏اللي الاختبارات دي بتحرسه:
  ‏- كل صفحة بتشغّل الثيم قبل ما ترسم (من غير وميض أبيض).
  ‏- كل اسم لون له قيمة غامقة، والكلام مقروء في الوضعين.
  ‏- الألوان المحايدة الشائعة مابقتش مكتوبة بالإيد (وإلا هتفضل فاتحة).
  ‏- ملف PDF الخطة والطباعة فاتحين دايمًا.

Run with:  python3 tests/test_dark_mode.py
"""

import glob
import os
import re
import sys
from datetime import datetime

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_dark_mode.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "templates")
sys.path.insert(0, ROOT)

import app as A  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False
ADMIN = A.db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")["id"]

# ‏دول مايتلمسوش: PDF الخطة (WeasyPrint بيطبعه أبيض)، وأفو (ألوانه شخصيته).
KEEP_LIGHT = {"meal_plan.html", "_afo.html"}
# ‏قطع بتتحط جوه صفحات تانية، فالثيم بييجي من الصفحة الأم.
PARTIALS = {"_admin_client_followup.html", "_afo.html", "_client_bar.html", "_client_home_cards.html",
            "_nav_icons.html", "_next_appointment.html", "_public_header.html", "_swap_sheet.html",
            "_theme.html", "_theme_btn.html"}


def _read(name):
    return open(os.path.join(T, name), encoding="utf-8").read()


def _theme():
    return _read("_theme.html")


def _block(css, selector):
    i = css.index(selector)
    return css[i:css.index("}", i)]


def _tokens(block):
    return dict(re.findall(r"(--nx-[a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})", block))


def _lum(hx):
    hx = hx.lstrip("#")
    ch = [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


LIGHT = lambda: _tokens(_block(_theme(), ":root{"))
DARK = lambda: _tokens(_block(_theme(), 'html[data-theme="dark"]{'))

PAIRS = [("--nx-ink", "--nx-surface"), ("--nx-ink", "--nx-bg"), ("--nx-ink-2", "--nx-surface"),
         ("--nx-muted", "--nx-surface"), ("--nx-muted", "--nx-surface-2"), ("--nx-muted", "--nx-bg"),
         ("--nx-warn-ink", "--nx-warn-bg"), ("--nx-bad-ink", "--nx-bad-bg"),
         ("--nx-on-solid", "--nx-solid"), ("--nx-on-solid", "--nx-solid-2"), ("--nx-ok-ink", "--nx-ok-bg")]


# ═══ الثيم بيشتغل قبل الرسم ═══

def test_every_page_starts_the_theme_before_it_paints():
    for path in sorted(glob.glob(os.path.join(T, "*.html"))):
        name = os.path.basename(path)
        if name in PARTIALS or name in KEEP_LIGHT:
            continue
        s = open(path, encoding="utf-8").read()
        if 'extends "base.html"' in s:
            continue
        head = s[:s.index("</head>")] if "</head>" in s else ""
        assert '{% include "_theme.html" %}' in head, name
        first_css = min([i for i in (head.find("<style"), head.find('rel="stylesheet"')) if i >= 0] or [len(head)])
        assert head.index('{% include "_theme.html" %}') < first_css, name


def test_the_theme_script_follows_the_device_until_you_choose():
    s = _theme()
    assert "prefers-color-scheme: dark" in s
    assert "localStorage" in s and "nx-theme" in s
    assert "document.documentElement" in s


def test_every_colour_name_has_a_dark_value():
    light, dark = LIGHT(), DARK()
    assert len(light) >= 18, light
    assert set(light) == set(dark), set(light) ^ set(dark)


def test_text_is_readable_in_both_modes():
    for mode, tok in (("light", LIGHT()), ("dark", DARK())):
        for fg, bg in PAIRS:
            r = _ratio(tok[fg], tok[bg])
            assert r >= 4.5, (mode, fg, bg, round(r, 2))


def test_print_is_always_light():
    s = _theme()
    i = s.index("@media print")
    assert "--nx-surface:#FFFFFF" in s[i:i + 1200].replace(" ", "")


# ═══ الزرار ═══

def test_the_header_has_a_theme_button():
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = ADMIN
    html = c.get("/dashboard").get_data(as_text=True)
    m = re.search(r'<button[^>]*data-theme-toggle[^>]*>', html)
    assert m, "مفيش زرار ثيم في الهيدر"
    assert "aria-label=" in m.group(0)


def test_the_sign_in_page_has_a_theme_button_too():
    html = A.app.test_client().get("/login").get_data(as_text=True)
    assert re.search(r'<button[^>]*data-theme-toggle[^>]*aria-label=', html)


# ═══ الألوان المحايدة مابقتش مكتوبة بالإيد ═══

NEUTRAL = {
    "background": {"#fff", "#ffffff", "white", "#f3f5f7", "#edf0f3", "#f6f7f8", "#fdf6ec", "#fbeded", "#e9f2f6"},
    "color": {"#1e2630", "#5a6472", "#3a4a5c"},
    "border": {"#d5dae0", "#e4e7ea", "#edf0f3"},
}


def test_no_page_hard_codes_the_common_neutrals():
    left = []
    for path in sorted(glob.glob(os.path.join(T, "*.html"))):
        name = os.path.basename(path)
        if name in KEEP_LIGHT or name == "_theme.html":
            continue
        s = open(path, encoding="utf-8").read()
        for m in re.finditer(r'(?<![\w-])(background(?:-color)?|color|border(?:-[a-z-]+)?)\s*:\s*([^;"}]*)', s, re.I):
            prop = m.group(1).lower()
            kind = "background" if prop.startswith("background") else "border" if prop.startswith("border") else "color"
            # ‏(?<!-) علشان var(--white) اسم مش لون
            for c in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|(?<!-)\bwhite\b(?!-)", m.group(2)):
                if c.lower() in NEUTRAL[kind]:
                    left.append("%s: %s %s" % (name, prop, c))
    assert not left, "%d left, e.g. %s" % (len(left), left[:8])


def test_the_plan_pdf_stays_untouched():
    s = _read("meal_plan.html")
    assert "_theme.html" not in s and "var(--nx-" not in s


def test_text_on_dark_buttons_stays_white():
    # ‏الأزرار الكحلي كلامها أبيض. لو خلفيتها اتقلبت فاتحة في الغامق،
    # الكلام الأبيض هيختفي -- فخلفيتها اسم مخصوص (solid) بيفضل غامق.
    dark = DARK()
    assert _lum(dark["--nx-solid"]) < 0.2 and _lum(dark["--nx-solid-2"]) < 0.25


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

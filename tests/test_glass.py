# -*- coding: utf-8 -*-
"""‏الموقع كله زجاج: غامق شفاف زي القايمة الجانبية، وفاتح زي زجاج Apple.

‏صاحب المشروع بص على اللوحة: القايمة زجاج كحلي شفاف والصفحة جنبها أبيض
سادة -- شكلين في صفحة واحدة. طلب إن الموقع كله يمشي على نفس الفكرة: في
الغامق زجاج غامق شفاف، وفي الفاتح زجاج أبيض فاتح.

‏اللي الاختبارات دي بتحرسه:
  ‏- الهيدر والقايمة والكروت المشتركة زجاج في الوضعين.
  ‏- فيه حاجة ورا الزجاج (بقع لون مثبّتة ومطفية) -- زجاج على أرضية سادة
    بيبان رمادي باهت.
  ‏- الكلام مقروء: الزجاج مش شفاف أوي، والقايمة الفاتحة كلامها كحلي.
  ‏- متصفح مابيدعمش الزجاج، أو حد مشغّل "تقليل الشفافية"، بياخد سطح صلب.

Run with:  python3 tests/test_glass.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "templates")


def _read(name):
    return open(os.path.join(T, name), encoding="utf-8").read()


THEME = _read("_theme.html")
BASE = _read("base.html")


def _block(css, selector):
    i = css.index(selector)
    return css[i:css.index("}", i)]


def _alpha(block, name):
    m = re.search(r"%s:rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([\d.]+)\s*\)" % re.escape(name), block)
    assert m, (name, block[:200])
    return float(m.group(1))


def _rule(css, selector):
    m = re.search(re.escape(selector) + r"\{([^}]*)\}", css)
    assert m, selector
    return m.group(1)


def test_glass_tokens_exist_in_both_modes():
    light = _block(THEME, ":root{")
    dark = _block(THEME, 'html[data-theme="dark"]{')
    # ‏شفاف بس مش أوي: تحت النص بيبقى الكلام بيرقص على البقع اللي ورا
    assert 0.55 <= _alpha(light, "--nx-glass") <= 0.9
    assert 0.5 <= _alpha(dark, "--nx-glass") <= 0.9
    for tok in ("--nx-glass-line", "--nx-side-bg", "--nx-side-ink"):
        assert tok + ":" in light and tok + ":" in dark, tok


def test_the_shared_surfaces_are_glass():
    for sel in (".header", ".sidebar", ".card"):
        body = _rule(BASE, sel)
        assert "backdrop-filter" in body, sel
        assert re.search(r"var\(--nx-(glass|glass-strong|side-bg)\)", body), sel


def test_there_is_something_behind_the_glass():
    m = re.search(r"body\.nx-glass-page::before\{([^}]*)\}", THEME)
    assert m and "position:fixed" in m.group(1).replace(" ", ""), "مفيش طبقة ورا الزجاج"
    assert "gradient" not in THEME
    assert re.search(r'<body[^>]*class="[^"]*nx-glass-page', BASE), "base.html مش مفعّل الخلفية"


def test_the_light_sidebar_writes_in_navy():
    light = _block(THEME, ":root{")
    ink = re.search(r"--nx-side-ink:(#[0-9A-Fa-f]{6})", light).group(1)
    assert ink.upper() in ("#1E2630", "#2B3746"), ink
    assert "var(--nx-side-ink)" in _rule(BASE, ".lq")


def test_no_glass_falls_back_to_solid():
    assert "@supports not ((backdrop-filter" in THEME
    assert "prefers-reduced-transparency" in THEME


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

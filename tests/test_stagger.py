# -*- coding: utf-8 -*-
"""‏القوايم بتظهر واحد ورا التاني، مش كلها مرة واحدة.

‏صاحب المشروع طلب نفس الإحساس بتاع flutter_animate: كل كارت fadeIn +
slideY(begin: 0.2) في ٤٠٠ مللي، وبين الكارت والتاني ٨٠ مللي.

‏اللي الاختبارات دي بتحرسه:
  ‏- القايمة الصغيرة (فئات /foods، ١٤ مربع) كل عنصر متأخّر ٨٠ مللي عن اللي
    قبله، من غير سقف.
  ‏- القايمة الطويلة (جدول الفئة) التأخير بيقف عند العنصر السابع. من غير
    السقف الصف رقم ٥٠ كان هيستنى ٤ ثواني وهو أصلاً تحت الشاشة.
  ‏- الأنيميشن مابيمسكش آخر حالته (backwards مش both): لو مسكها، الـtransform
    بتاعه بيغلب hover الكارت فالرفعة الصغيرة بتموت.
  ‏- "تقليل الحركة" بيلغيه.

Run with:  python3 tests/test_stagger.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_stagger_test.db"

import app as A        # noqa: E402
import food_data       # noqa: E402

BASE = open(os.path.join(ROOT, "templates", "base.html"), encoding="utf-8").read()
_CLIENT = A.app.test_client()


def _rule(selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", BASE)
    assert m, selector
    return m.group(1).replace(" ", "")


def _indices(html, cls):
    """‏قيم --i للعناصر اللي عليها الكلاس، بالترتيب."""
    out = []
    for tag in re.findall(r"<[a-z]+[^>]*\bclass=\"[^\"]*\b%s\b[^\"]*\"[^>]*>" % cls, html):
        if "nx-stagger" not in tag:
            out.append(None)
            continue
        m = re.search(r"--i:(\d+)", tag)
        out.append(int(m.group(1)) if m else None)
    return out


def test_the_effect_is_fade_plus_a_fifth_of_its_height():
    m = re.search(r"@keyframes nx-rise\{from\{([^}]*)\}", BASE)
    assert m, "مفيش keyframes nx-rise"
    frm = m.group(1).replace(" ", "")
    assert "opacity:0" in frm, frm
    assert "translateY(20%)" in frm, frm


def test_400ms_with_80ms_between_items():
    body = _rule(".nx-stagger")
    assert "nx-rise.4s" in body or "nx-rise400ms" in body, body
    assert "calc(var(--i,0)*80ms)" in body, body


def test_it_does_not_hold_its_end_state():
    body = _rule(".nx-stagger")
    assert "backwards" in body, body
    assert "both" not in body and "forwards" not in body, body


def test_reduced_motion_turns_it_off():
    m = re.search(r"@media \(prefers-reduced-motion: reduce\)\{(.*?)\n\}", BASE, re.S)
    assert m and ".nx-stagger" in m.group(1), "تقليل الحركة مش بيلغي الـstagger"


def test_small_list_steps_every_item():
    html = _CLIENT.get("/foods").get_data(as_text=True)
    got = _indices(html, "fx-cat")
    assert got == list(range(len(food_data.CATEGORIES))), got


def test_long_list_caps_at_the_seventh_row():
    biggest = max(food_data.CATEGORIES, key=lambda k: len(food_data.foods_in(k)))
    n = len(food_data.foods_in(biggest))
    assert n > 7, n
    html = _CLIENT.get("/foods?cat=" + biggest).get_data(as_text=True)
    got = _indices(html, "fx-row")
    assert got == [min(i, 6) for i in range(n)], got[:12]


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, "--", e)
    print("\n%d passed, %d failed" % (len(tests) - failed, failed))
    sys.exit(1 if failed else 0)

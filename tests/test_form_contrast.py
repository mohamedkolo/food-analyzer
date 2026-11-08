# -*- coding: utf-8 -*-
"""‏الكارت المختار اتلوّن -- والنص اللي فوقه بقى أبيض.

‏الفورم بقى فيه لغة واحدة: اللي مختار **بيتلوّن كله** بتدرّج، مش
بعلامة ✓ صغيرة. ده اتعمل عشان الدكتور بيملا الفورم ده عشرات المرات
في اليوم ولمحة واحدة لازم تقوله اختار إيه.

‏بس أول نسخة منه كان التدرّج بيبدأ من ``#0891B2``، والنص عليه أبيض:
تباين **٣.٦٨:١**. وسطر ``kcal 1200-1500`` حجمه ١١.٥ بكسل -- ومعيار
WCAG AA للنص العادي ``٤.٥:١``. يعني الكارت كان بيبان حلو في الصورة
وسطر السعرات فيه **مش مقروء** على موبايل في نور.

‏فالتدرّج اتغمّق. والاختبار ده بيقيس الرقم من الـCSS نفسه، عشان أي
حد (أو أي ذكاء اصطناعي) يفتّح اللون تاني عشان "يبقى أحلى" يقع هنا
بدل ما يقع على شاشة عميل.

‏اللون الفاتح لسه موجود -- بس في الهالة والإطار، وهناك مفيش نص فوقه.

Run with:  python3 tests/test_form_contrast.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FORM = os.path.join(_HERE, "templates", "generate.html")
# ‏التدرّج نفسه معرّف في :root في base.html، عشان باقي الصفحات تاخده
# من مكان واحد. القواعد اللي بتستعمله في صفحة الفورم.
_BASE = os.path.join(_HERE, "templates", "base.html")

# ‏معيار WCAG AA: ٤.٥:١ للنص العادي، ٣:١ للكبير (١٨.٥ بكسل، أو ١٤
# بكسل تخين). أصغر نص على التدرّج عندنا ١١.٥ -- فالعتبة ٤.٥.
MIN_RATIO = 4.5


def _page(path=None):
    with open(path or _FORM, encoding="utf-8") as fh:
        return fh.read()


def _luminance(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    parts = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    parts = [(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
             for c in parts]
    return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]


def _ratio(a, b):
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _pick_stops():
    """‏ألوان تدرّج الاختيار زي ما هي مكتوبة في الـCSS."""
    m = re.search(r"--pick:\s*linear-gradient\(([^;}]+)\)", _page(_BASE))
    assert m, "‏متغيّر --pick مش معرّف في base.html"
    return re.findall(r"#[0-9a-fA-F]{3,6}", m.group(1))


# ── الرقم ───────────────────────────────────────────────────────────

def test_the_gradient_is_actually_defined():
    stops = _pick_stops()
    assert len(stops) >= 2, stops


def test_white_text_is_readable_on_every_point_of_it():
    """‏مش على المتوسط -- على **أفتح** نقطة. دي اللي بتحدد."""
    for stop in _pick_stops():
        r = _ratio("#ffffff", stop)
        assert r >= MIN_RATIO, (
            "‏لون %s تباينه مع الأبيض %.2f:1 -- أقل من %.1f:1. "
            "سطر السعرات ١١.٥ بكسل، هيبقى مش مقروء." % (stop, r, MIN_RATIO))


def test_the_old_too_light_cyan_did_not_come_back():
    """‏#0891B2 تباينه ٣.٦٨:١. ده اللي اتشال من التدرّج."""
    assert _ratio("#ffffff", "#0891B2") < MIN_RATIO, "‏الحساب نفسه باظ"
    assert "#0891B2" not in " ".join(_pick_stops()), "‏رجع تاني"


# ── اللي النص بيتكتب عليه فعلاً ─────────────────────────────────────

def _last_rule(selector_re):
    """‏القاعدة الأخيرة هي اللي بتكسب -- نفس الـselector مكتوب أكتر من
    مرة في الورقة، والمتصفح بياخد آخر واحدة."""
    hits = re.findall(selector_re + r"\s*\{(.*?)\}", _page(), re.S)
    assert hits, "‏القاعدة مش موجودة خالص"
    return hits[-1]


def test_the_picked_card_uses_that_gradient_and_white_text():
    """‏لو الكارت اتلوّن بحاجة تانية، الرقم اللي فوق مابيحميش حاجة."""
    body = _last_rule(r"\.nx-opt-in:checked \+ \.nx-opt-b")
    assert "var(--pick)" in body, body
    assert "color:#fff" in body.replace(" ", ""), body


def test_the_active_step_speaks_the_same_language():
    body = _last_rule(r"\.wz-tab\.active")
    assert "var(--pick)" in body, (
        "‏الخطوة الحالية بتتلوّن بلون تاني -- لغتين في صفحة واحدة: " + body)


# ── اللون الفاتح لسه موجود، بس في مكانه ─────────────────────────────

def test_the_bright_cyan_survives_where_nothing_is_written_on_it():
    """‏الهالة والإطار -- مش خلفية نص."""
    page = _page() + _page(_BASE)
    assert "rgba(8,145,178" in page or "#0891B2" in page, (
        "‏اللون الحيوي اتشال خالص -- الصفحة هتبقى باهتة")


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

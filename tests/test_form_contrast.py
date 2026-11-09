# -*- coding: utf-8 -*-
"""‏اللي مختار بيتملى باللون -- والنص اللي فوقه أبيض.

‏الفورم فيه لغة واحدة: اللي مختار **بيتلوّن كله**، مش بعلامة ✓ صغيرة.
ده اتعمل عشان الدكتور بيملا الفورم ده عشرات المرات في اليوم ولمحة
واحدة لازم تقوله اختار إيه.

‏وده بيحط نص أبيض على لون -- والرقم بيقرر لو ده شغّال ولا لأ:

  ‏أول نسخة كان اللون تدرّج بيبدأ من ``#0891B2``. تباينه مع الأبيض
  **٣.٦٨:١**، وسطر ``kcal 1200-1500`` حجمه ١١.٥ بكسل ومعيار WCAG AA
  للنص العادي ``٤.٥:١``. يعني الكارت كان شكله حلو في الصورة وسطر
  السعرات فيه **مش مقروء** على موبايل في نور.

‏والتدرّج نفسه اتشال بعد كده لسبب تاني: التدرّج والهالة الملوّنة
والظل الملوّن هما أول تلات حاجات بتخلي الشكل يبان **مولّد**. فبقى
``--pick`` لون صلب.

‏الاختبار ده بيحسب التباين من الـCSS نفسه، عشان أي حد (أو أي ذكاء
اصطناعي) يفتّح اللون عشان "يبقى أحلى" يقع هنا بدل ما يقع على شاشة
عميل -- وعشان حد مايرجّعش التدرّج من غير ما ياخد باله.

Run with:  python3 tests/test_form_contrast.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FORM = os.path.join(_HERE, "templates", "generate.html")
# ‏اللون معرّف في :root في base.html عشان باقي الصفحات تاخده من مكان
# واحد. القواعد اللي بتستعمله في صفحة الفورم.
_BASE = os.path.join(_HERE, "templates", "base.html")

# ‏معيار WCAG AA: ٤.٥:١ للنص العادي. أصغر نص بيتكتب على اللون ده
# ١١.٥ بكسل -- فالعتبة ٤.٥ مش ٣.
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


def _pick_raw():
    m = re.search(r"--pick:\s*([^;}]+)", _page(_BASE))
    assert m, "‏متغيّر --pick مش معرّف في base.html"
    return m.group(1).strip()


def _pick_colors():
    """‏كل لون جوّه --pick. لون صلب = واحد؛ تدرّج = أكتر."""
    return re.findall(r"#[0-9a-fA-F]{3,6}", _pick_raw())


def _last_rule(selector_re):
    """‏القاعدة الأخيرة هي اللي بتكسب: نفس الـselector مكتوب أكتر من مرة
    في الورقة، والمتصفح بياخد آخر واحدة."""
    hits = re.findall(selector_re + r"\s*\{(.*?)\}", _page(), re.S)
    assert hits, "‏القاعدة مش موجودة خالص"
    return hits[-1]


# ── الرقم ───────────────────────────────────────────────────────────

def test_the_colour_is_actually_defined():
    assert _pick_colors(), _pick_raw()


def test_white_text_is_readable_on_it():
    """‏لو بقى تدرّج تاني، ده بيتقاس على **أفتح** نقطة فيه."""
    for colour in _pick_colors():
        r = _ratio("#ffffff", colour)
        assert r >= MIN_RATIO, (
            "‏لون %s تباينه مع الأبيض %.2f:1 -- أقل من %.1f:1. "
            "سطر السعرات ١١.٥ بكسل، هيبقى مش مقروء." % (colour, r, MIN_RATIO))


def test_the_old_too_light_cyan_did_not_come_back():
    """‏#0891B2 تباينه ٣.٦٨:١. ده اللي اتشال."""
    assert _ratio("#ffffff", "#0891B2") < MIN_RATIO, "‏الحساب نفسه باظ"
    assert "#0891B2" not in _pick_raw(), "‏رجع تاني"


def test_it_is_a_flat_colour_not_a_gradient():
    """‏التدرّج أول حاجة بتقول "ده شكل مولّد". ده قرار مقصود، مش صدفة --
    فلو حد رجّعه لازم يكون عارف إنه بيرجّعه."""
    assert "gradient" not in _pick_raw().lower(), _pick_raw()
    assert len(_pick_colors()) == 1, _pick_raw()


# ── اللي النص بيتكتب عليه فعلاً ─────────────────────────────────────

def test_the_picked_card_uses_that_colour_and_white_text():
    """‏لو الكارت اتلوّن بحاجة تانية، الرقم اللي فوق مابيحميش حاجة."""
    body = _last_rule(r"\.nx-opt-in:checked \+ \.nx-opt-b")
    assert "var(--pick)" in body, body
    assert "color:#fff" in body.replace(" ", ""), body


def test_the_active_step_speaks_the_same_language():
    body = _last_rule(r"\.wz-tab\.active")
    assert "var(--green)" in body or "var(--pick)" in body, (
        "‏الخطوة الحالية بتتلوّن بلون تاني -- لغتين في صفحة واحدة: " + body)


# ── صفر تدرّجات ─────────────────────────────────────────────────────

def test_no_gradient_survives_in_the_shared_chrome():
    """‏base.html كان فيه ٦ تدرّجات: زرارين، الفوتر، زرار الواتساب
    العايم، وشريط تثبيت التطبيق. واللي بيشيل تدرّج من غير ما يحط لون
    صلب مكانه بيطلّع زرار **أبيض عليه نص أبيض** -- حصل فعلاً مع
    "ولّد الخطة"."""
    for name in ("base.html", "generate.html", "dashboard.html"):
        text = _page(os.path.join(_HERE, "templates", name))
        assert "linear-gradient" not in text, (
            "‏%s لسه فيه تدرّج" % name)


def test_the_generate_button_still_has_a_background():
    """‏الزرار ده بيستعمل .btn-success، واللي كان تدرّج."""
    base = _page(_BASE)
    m = re.search(r"\.btn-success\{([^}]*)\}", base)
    assert m, "‏.btn-success اختفى"
    body = m.group(1)
    assert "background:" in body, body
    assert "none" not in body, body


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

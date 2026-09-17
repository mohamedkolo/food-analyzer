# -*- coding: utf-8 -*-
"""ما بينكشفش إلا بفحص، فالفحص لازم يتحول لاختبار.

التقرير على الموقع المنشور طلّع 76/100 في الوصولية. اللي طلع من الفحص المحلي
(axe-core على 35 صفحة × مقاسين) كان أربع مشاكل بتتكرر، وكل واحدة فيهم رجعت
لسبب واحد بسيط ينفع يتقاس من الملفات نفسها من غير متصفح:

  * رماديان (#64748b و #94a3b8) مستخدمين نص على خلفيات فاتحة، ونسبتهم تحت
    4.5:1. الاستثناء الوحيد هو الفوتر الغامق وكتلة الكود الغامقة — هناك اللون
    لازم يفتح مايغمقش، فمكتوبين هنا بالاسم.
  * الهيدر العام كان بيورّث لون النص الغامق فوق خلفية كحلي (1.21:1) — النص كان
    شبه مختفي فعلاً، مش مجرد تحذير.
  * حقول وقوائم من غير اسم: label من غير for، أو select مالوش aria-label.
  * الموبايل كان مقفل الزووم بـ user-scalable=no.

فالاختبارات دي بتثبّت الأربعة. لو حد رجع لون منهم أو ضاف select من غير اسم،
بيقع هنا قبل ما يوصل للمريض.

Run with:  python3 tests/test_accessibility.py
"""

import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TPL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")


def _templates():
    return sorted(glob.glob(os.path.join(TPL, "*.html")))


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ‏اللونين دول على خلفية فاتحة بيطلعوا 2.56:1 و4.39:1 — الحد 4.5:1.
LOW_CONTRAST_GREYS = ("#64748b", "#94a3b8")

# ‏الاستثناءات: نص فاتح فوق خلفية غامقة. لو غمّقناه بيبوظ.
ALLOWED_ON_DARK = {
    "base.html": [".nx-footer-col p{font-size:13px;line-height:1.7;color:#94a3b8;margin:0 0 12px}"],
}


def test_no_template_uses_a_grey_that_fails_on_a_light_background():
    offenders = []
    for path in _templates():
        text = _read(path)
        for frag in ALLOWED_ON_DARK.get(os.path.basename(path), []):
            text = text.replace(frag, "")
        for grey in LOW_CONTRAST_GREYS:
            if grey in text.lower():
                offenders.append("%s -> %s" % (os.path.basename(path), grey))
    assert not offenders, (
        "‏لون رمادي تحت 4.5:1 على خلفية فاتحة. استخدم #55647a بدله:\n  "
        + "\n  ".join(offenders)
    )


def test_no_page_disables_pinch_zoom():
    offenders = []
    for path in _templates():
        for line in _read(path).split("\n"):
            if "name=\"viewport\"" not in line:
                continue
            if "user-scalable=no" in line or "maximum-scale" in line:
                offenders.append(os.path.basename(path))
    assert not offenders, (
        "‏قفل الزووم بيمنع حد ضعيف النظر إنه يكبّر: " + ", ".join(offenders)
    )


def test_the_public_header_writes_light_text_on_its_dark_bar():
    text = _read(os.path.join(TPL, "_public_header.html"))
    assert "color:inherit" not in text, (
        "‏الهيدر العام خلفيته var(--blue) الكحلي، وcolor:inherit بيورّث لون "
        "النص الغامق — النسبة بتبقى 1.21:1 والاسم بيختفي."
    )
    assert "#475569" not in text, "‏#475569 على الكحلي = 1.93:1."


# ‏دول مش محتاجين اسم ظاهر: أزرار وحقول مخفية.
SKIP_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image", "checkbox", "radio"}


def test_every_form_control_carries_a_name_a_screen_reader_can_read():
    """‏حقل من غير اسم بيتقرا 'مربع نص' أو 'قائمة' وبس.

    الفحص بالمتصفح وحده مابيكفيش هنا: نص الحقول دي جوه accordion مقفول أو
    خطوة مخفية في الـwizard، وaxe بيتخطى أي حاجة مخفية. فالقياس من الملف
    نفسه بيمسك اللي المتصفح مابيشوفهوش.
    """
    labelled_ids = set()
    for path in _templates():
        labelled_ids |= set(re.findall(r'<label[^>]*\sfor="([^"]+)"', _read(path)))

    offenders = []
    for path in _templates():
        text = _read(path)
        for tag in re.findall(r"<(?:input|select|textarea)\b[^>]*>", text, re.S):
            if "aria-label" in tag or "aria-labelledby" in tag or "placeholder=" in tag:
                continue
            itype = re.search(r'\stype="([^"]+)"', tag)
            if itype and itype.group(1).lower() in SKIP_INPUT_TYPES:
                continue
            sid = re.search(r'\sid="([^"]+)"', tag)
            if sid and sid.group(1) in labelled_ids:
                continue
            offenders.append("%s -> %s" % (os.path.basename(path), " ".join(tag.split())[:70]))
    assert not offenders, (
        "‏كل حقل محتاج label مربوط بـfor أو aria-label:\n  " + "\n  ".join(offenders)
    )


def test_the_login_form_labels_every_field_it_asks_for():
    """‏حقل الباسورد مكانش له placeholder ولا label مربوط، فمكانش له اسم خالص."""
    text = _read(os.path.join(TPL, "login.html"))
    for name in ("email", "password", "name", "age", "country", "phone",
                 "reg_email", "reg_password"):
        tag = re.search(r'<(?:input|select)[^>]*\sname="%s"[^>]*>' % re.escape(name), text)
        assert tag, "‏الحقل %s مش موجود في الفورم" % name
        sid = re.search(r'\sid="([^"]+)"', tag.group(0))
        assert sid, "‏الحقل %s مالوش id يتربط بيه label" % name
        assert 'for="%s"' % sid.group(1) in text, (
            "‏مفيش label بـfor=\"%s\" للحقل %s" % (sid.group(1), name)
        )


def test_the_login_page_puts_its_content_in_a_landmark():
    text = _read(os.path.join(TPL, "login.html"))
    assert "<main" in text and "</main>" in text, (
        "‏من غير main قارئ الشاشة مش لاقي المحتوى الأساسي، وaxe بيقول "
        "landmark-one-main + region."
    )


def test_the_footer_headings_never_skip_a_level():
    """‏الفوتر بيظهر تحت صفحات آخر عنوان فيها h1 أو h2، فh2 هو اللي بيمشي مع
    الاتنين (النزول مسموح، والصعود خطوة واحدة بس). h4 كان بيقفز."""
    text = _read(os.path.join(TPL, "base.html"))
    assert ".nx-footer-col h2{" in text, "‏ستايل عناوين الفوتر مش h2"
    assert re.search(r'<h[34]><i class="fa-solid fa-(leaf|link|scale-balanced|headset)"', text) is None, (
        "‏عنوان فوتر لسه h3/h4 — بيقفز مستوى بعد h1"
    )


def test_every_app_page_has_exactly_one_page_title_as_its_h1():
    """‏page-title كان div، فكانت في صفحات كاملة من غير h1 خالص."""
    offenders = []
    for path in _templates():
        text = _read(path)
        first = re.search(r'<(div|h1)\s+class="page-title"', text)
        if not first:
            continue
        if first.group(1) != "h1":
            offenders.append(os.path.basename(path))
    assert not offenders, (
        "‏أول page-title في الصفحة لازم يكون h1: " + ", ".join(offenders)
    )


def test_every_scrollable_strip_is_reachable_by_keyboard():
    """‏منطقة بتـscroll ومفيهاش حاجة focusable مش بتوصلها غير بالماوس."""
    checks = [
        ("knowledge_hub.html", 'id="foodList"'),
        ("knowledge_hub.html", 'id="planMealsList"'),
        ("analyzer.html", 'id="catStrip"'),
        ("analyzer.html", 'id="medStrip"'),
        ("admin_users.html", 'class="users-table-wrap"'),
    ]
    offenders = []
    for fname, anchor in checks:
        text = _read(os.path.join(TPL, fname))
        i = text.find(anchor)
        assert i != -1, "%s: %s مش موجود" % (fname, anchor)
        tag_start = text.rindex("<", 0, i)
        tag = text[tag_start:text.index(">", i) + 1]
        if 'tabindex="0"' not in tag:
            offenders.append("%s -> %s" % (fname, anchor))
    assert not offenders, "‏منطقة scroll من غير tabindex: " + ", ".join(offenders)


def test_the_youtube_embeds_are_titled():
    text = _read(os.path.join(TPL, "knowledge_hub.html"))
    for tag in re.findall(r"<iframe[^>]*", text):
        assert "title=" in tag, "‏iframe من غير title بيتقرا 'إطار' وبس: " + tag[:80]


def test_no_template_calls_a_jinja_filter_that_does_not_exist():
    """‏ده مش عن الوصولية، ده عن صفحة بتقع.

    صفحة المريض كانت بترمي 500 لأي مريض له حالة مرضية مسجّلة، لأنها بتنادي
    فلتر اسمه split وJinja مافيهاش فلتر بالاسم ده. والغلط مابيظهرش إلا وقت
    التشغيل، ولما الشرط يتحقق بالظبط — يعني ماينفعش نستناه يبان لوحده.

    فبنـparse كل تمبليت ونمشي على شجرة الـAST بتاعها، وناخد اسم كل فلتر
    مستخدم، ونتأكد إنه مسجّل فعلاً. ده بيمسك النوع كله مرة واحدة.
    """
    os.environ.setdefault("SECRET_KEY", "test-only")
    from jinja2 import nodes  # noqa: E402
    import core  # noqa: E402
    import app as _app  # noqa: F401,E402  بيسجّل الفلاتر والراوتس

    env = core.app.jinja_env
    known = set(env.filters)
    offenders = []
    for path in _templates():
        try:
            ast = env.parse(_read(path), filename=os.path.basename(path))
        except Exception as exc:                    # ‏تمبليت مش بيـparse أصلاً
            offenders.append("%s -> لا يـparse: %s" % (os.path.basename(path), exc))
            continue
        for node in ast.find_all(nodes.Filter):
            if node.name not in known:
                offenders.append("%s -> | %s" % (os.path.basename(path), node.name))
    assert not offenders, (
        "‏فلتر Jinja مش موجود — الصفحة هترمي 500 لما توصل للسطر ده:\n  "
        + "\n  ".join(sorted(set(offenders)))
    )


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

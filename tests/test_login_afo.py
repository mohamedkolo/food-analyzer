# -*- coding: utf-8 -*-
"""‏أفو: أفوكادو صغير فوق كارت الدخول.

‏بيبص على الإيميل وإنت بتكتبه، ويغطّي عينه وإنت بتكتب كلمة السر، ويزعل
لو السيرفر رجّع خطأ. الفكرة إن صفحة الدخول هي أول حاجة العميل بيشوفها،
وكانت فورم رمادي زي أي موقع.

‏اللي الاختبارات دي بتحرسه:
  ‏- أفو زينة بس: مخفي عن قارئ الشاشة، والخطأ فاضل في رسالة الصفحة.
  ‏- مزاجه الأول جاي من السيرفر (خطأ = زعلان، تسجيل نجح = فرحان)،
    فبيبان صح حتى قبل ما الـJS يشتغل.
  ‏- ماعندوش دعوة بإرسال الفورم -- الدخول شغال من غير JS.
  ‏- الصفحة الإنجليزي كلامه إنجليزي.
  ‏- الحركة بتقف مع prefers-reduced-motion.

Run with:  python3 tests/test_login_afo.py
"""

import os
import re
import sys

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_login_afo.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARABIC = re.compile(r"[؀-ۿ]")


def _page(lang="ar", method="get", data=None):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["lang"] = lang
    r = c.post("/login", data=data) if method == "post" else c.get("/login")
    assert r.status_code == 200, r.status_code
    return r.get_data(as_text=True)


def _afo_tag(html):
    m = re.search(r'<div[^>]*id="afo"[^>]*>', html)
    assert m, "مفيش أفو في صفحة الدخول"
    return m.group(0)


def test_login_page_has_afo():
    html = _page()
    _afo_tag(html)
    for hook in ('id="afoArmL"', 'id="afoArmR"', 'id="afoPupils"',
                 'id="afoMouth"', 'id="afoSay"'):
        assert hook in html, hook


def test_afo_is_decorative():
    # ‏قارئ الشاشة مش محتاج يسمع "بقرا إيميلك…" مع كل حرف.
    assert 'aria-hidden="true"' in _afo_tag(_page())


def test_mood_idle_on_plain_visit():
    assert 'data-mood="idle"' in _afo_tag(_page())


def test_mood_sad_after_wrong_password():
    html = _page(method="post", data={"action": "login",
                                      "email": "nobody@x.test",
                                      "password": "wrong-one"})
    assert "msg-error" in html          # ‏الرسالة الحقيقية لسه موجودة
    assert 'data-mood="sad"' in _afo_tag(html)


def test_mood_happy_after_register():
    html = _page(method="post", data={
        "action": "register", "name": "Afo Fan", "age": "30",
        "country": "مصر", "phone": "+201000000000",
        "reg_email": "afo.fan@x.test", "reg_password": "pw123456"})
    assert "msg-success" in html
    assert 'data-mood="happy"' in _afo_tag(html)


def test_english_page_speaks_english():
    html = _page(lang="en")
    _afo_tag(html)
    start = html.index('id="afo"')
    end = html.index("</script>", html.index("afoLines", start))
    assert not ARABIC.search(html[start:end]), "أفو بيتكلم عربي في الصفحة الإنجليزي"
    assert "Hi! I’m Afo." in html


def test_afo_never_blocks_the_form():
    src = open(os.path.join(ROOT, "templates", "_afo.html"), encoding="utf-8").read()
    assert "preventDefault" not in src
    html = _page()
    assert '<form method="POST" id="loginForm"' in html


def test_reduced_motion_stops_animation():
    src = open(os.path.join(ROOT, "templates", "_afo.html"), encoding="utf-8").read()
    assert "prefers-reduced-motion" in src


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, "--", repr(e)[:200])
    print("\n%d passed, %d failed" % (len(tests) - failed, failed))
    sys.exit(1 if failed else 0)

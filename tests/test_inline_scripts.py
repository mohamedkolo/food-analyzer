# -*- coding: utf-8 -*-
"""‏كل سكريبت جوه الصفحات لازم يتقري (Syntax) -- وإلا الصفحة كلها بتقف.

‏ليه: في التعديلات بتاعة ٢٦ نوفمبر حصلت غلطتين ومحدش لاحظهم، لأن الصفحة
بتفتح عادي والغلطة في الكونسول بس:
  ‏- whey.html: `<script>` اتفتح جوه `<script>` -- السكريبت الرئيسي كله
    (التصوير، الباركود، الحفظ) بقى syntax error، ومحلل المكملات وقف.
  ‏- login.html: أيقونة العين اتحطت SVG بعلامات ' جوه نص بين ' -- زرار
    إظهار الباسورد وقف، في صفحة الدخول اللي كل الناس بتعدّي عليها.

‏الاختبار بيفتح كل صفحة GET (زائر ومدير)، وبيدّي كل سكريبت inline لـ
`node --check`. لو node مش موجود بيعدّي (Render مابيشغّلش الاختبارات).

Run with:  python3 tests/test_inline_scripts.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_inline_scripts_test.db"

import app as A  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False

_SKIP = ("logout", "export", "backup", "health", "pdf", "download", "sw.js", "manifest")
_SCRIPT = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)


def _pages():
    for r in A.app.url_map.iter_rules():
        if ("GET" in r.methods and not r.arguments and not r.rule.startswith(("/static", "/api", "/ocr"))
                and not r.rule.endswith((".xml", ".txt", ".json")) and not any(s in r.rule for s in _SKIP)):
            yield r.rule
    yield "/whey?kind=whey"
    yield "/whey?kind=creatine"


def _scripts(html):
    for m in _SCRIPT.finditer(html):
        attrs = m.group("attrs").lower()
        if "src=" in attrs or re.search(r'type="(?!text/javascript|module)', attrs):
            continue
        yield m.group("body"), "module" in attrs


def _bad_scripts(client):
    bad = []
    tmp = tempfile.mkdtemp()
    try:
        for url in _pages():
            r = client.get(url)
            if r.status_code != 200 or "html" not in (r.content_type or ""):
                continue
            for i, (body, module) in enumerate(_scripts(r.get_data(as_text=True))):
                if re.search(r"<script[\s>]", body, re.I):
                    bad.append("%s script %d: فيه <script> جوه <script>" % (url, i))
                    continue
                path = os.path.join(tmp, "s%d.%s" % (i, "mjs" if module else "js"))
                open(path, "w", encoding="utf-8").write(body)
                out = subprocess.run(["node", "--check", path], capture_output=True, text=True)
                if out.returncode:
                    err = [l for l in out.stderr.splitlines() if "Error" in l][:1]
                    bad.append("%s script %d: %s" % (url, i, err[0] if err else out.stderr[:200]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return bad


def _admin():
    c = A.app.test_client()
    c.post("/login", data={"action": "login", "email": "admin@nutrax.com", "password": "pw123456"})
    return c


def test_every_inline_script_parses_for_a_visitor():
    if not shutil.which("node"):
        print("  (node not installed -- skipped)")
        return
    bad = _bad_scripts(A.app.test_client())
    assert not bad, "\n".join(bad)


def test_every_inline_script_parses_for_the_admin():
    if not shutil.which("node"):
        print("  (node not installed -- skipped)")
        return
    bad = _bad_scripts(_admin())
    assert not bad, "\n".join(bad)


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, "--", str(e)[:1500])
    print("\n%d passed, %d failed" % (len(tests) - failed, failed))
    sys.exit(1 if failed else 0)

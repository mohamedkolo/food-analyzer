# -*- coding: utf-8 -*-
"""‏الصفحة الرئيسية: خفيفة، وبتقول الخدمة إيه، والـsplash للتطبيق بس.

‏مراجعة تصميم ٢٦ نوفمبر (صاحب المشروع: "صلّح التلاتة على طول"):
  ١. ‏مشهد الـ3D كان بيحمّل three.module.js كامل -- ١.٢٧ ميجا من غير ضغط،
     لأن الملفات الثابتة كانت بتعدّي من غير gzip. صاحب المشروع اشتكى قبل
     كده إن الموقع تقيل من الأنيميشن.
  ٢. ‏الزائر الجديد كان بيشوف "NX في مشهد واحد" وجملة مصمم ("إضاءة، عمق،
     وحركة مربوطة بالتمرير")، ومفيش كلمة عن الخطط الغذائية مع الدكتور --
     المنتج اللي بيتباع.
  ٣. ‏شاشة الـsplash (١.٥ ثانية) كانت بتظهر في أول صفحة في كل تاب، حتى
     للي جاي من جوجل.

Run with:  python3 tests/test_landing_speed.py
"""

import gzip
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_landing_speed_test.db"

import app as A  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False


def _landing(lang="ar"):
    c = A.app.test_client()
    c.get("/lang/" + lang)
    return c.get("/").get_data(as_text=True)


def test_the_3d_library_is_the_minified_build():
    html = _landing()
    m = re.search(r'"three"\s*:\s*"([^"]+)"', html)
    assert m and m.group(1).endswith(".min.js"), m and m.group(1)
    size = os.path.getsize(os.path.join(ROOT, m.group(1).lstrip("/")))
    assert size < 800_000, size


def test_static_scripts_go_out_compressed():
    c = A.app.test_client()
    r = c.get("/static/js/three.module.min.js", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200 and r.headers.get("Content-Encoding") == "gzip", r.headers
    body = gzip.decompress(r.get_data())
    assert body == open(os.path.join(ROOT, "static/js/three.module.min.js"), "rb").read()
    assert len(r.get_data()) < 250_000, len(r.get_data())
    # ‏من غير Accept-Encoding: الملف زي ما هو
    r = c.get("/static/js/three.module.min.js")
    assert "Content-Encoding" not in r.headers and len(r.get_data()) > 600_000


def test_the_landing_says_what_the_service_is():
    html = _landing()
    assert "مربوطة بالتمرير" not in html and "في مشهد واحد" not in html, "لسه كلام المصمم"
    box = html[html.index('id="services"'):]
    for href in ("/book", "/pricing", "/foods", "/whey"):
        assert 'href="%s"' % href in box, href
    assert "د. محمد" in box
    # ‏الزائر مش لازم يعدّي المشهد كله (٥٢٠vh) عشان يوصل للخدمة
    assert re.search(r'href="#services"', html), "مفيش اختصار للخدمة من أول الصفحة"
    en = _landing("en")
    box = en[en.index('id="services"'):en.index("</section>", en.index('id="services"'))]
    assert not re.search(r"[؀-ۿ]", box), "عربي في النسخة الإنجليزي"


def _splash_runs(standalone):
    js = open(os.path.join(ROOT, "static/js/nx-splash.js"), encoding="utf-8").read()
    harness = """
const added = [];
const el = () => ({ style: {}, classList: { add() {} }, setAttribute() {}, addEventListener() {}, remove() {} });
global.sessionStorage = { getItem() { return null; }, setItem() {} };
global.navigator = { standalone: false };
global.window = global;
global.matchMedia = q => ({ matches: q.includes('display-mode') ? %s : false });
global.document = { createElement: el, head: { appendChild: x => added.push(x) },
  body: { appendChild: x => added.push(x) }, documentElement: {} };
global.setTimeout = () => 0;
%s
console.log(added.length);
""" % ("true" if standalone else "false", js)
    out = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return int(out.stdout.strip())


def test_the_splash_is_for_the_installed_app_only():
    if not shutil.which("node"):
        print("  (node not installed -- skipped)")
        return
    assert _splash_runs(standalone=False) == 0, "الـsplash ظهر في المتصفح"
    assert _splash_runs(standalone=True) > 0, "الـsplash اختفى من التطبيق"


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

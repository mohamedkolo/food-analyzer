# -*- coding: utf-8 -*-
"""مسارات العيّنة القديمة في pdf_generator.py.

‏الملف ده كان قالب جاهز اتلزق في المشروع ومعاه تلت مسارات تجربة
من غير تسجيل دخول: /meal-plan/preview و /meal-plan/pdf و
/meal-plan/patient/<id>.pdf. أول اتنين كانوا بيرجّعوا 500 لأي زائر
(القالب مستني `user` ومحدش بيبعته)، والتالت كان بيشغّل WeasyPrint
على بيانات عيّنة لأي حد يطلب -- يعني أي حد يقدر يحمّل السيرفر
المجاني على Render بطلبات PDF تقيلة. الورق الحقيقي بيطلع من
plan_engine.py، ومحدش بيلينك على المسارات دي.

‏المطلوب: زائر من غير دخول ياخد 404 أو تحويل لصفحة الدخول. أبدًا
مش 500، وأبدًا مش PDF.

Run with:  python3 tests/test_pdf_sample_routes.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_pdf_sample_test.db")

import app as A       # noqa: E402

_CLIENT = A.app.test_client()

SAMPLE_URLS = [
    "/meal-plan/preview",
    "/meal-plan/pdf",
    "/meal-plan/patient/1.pdf",
]


def _check(url):
    r = _CLIENT.get(url)
    ctype = r.headers.get("Content-Type", "")
    assert "application/pdf" not in ctype, (
        "%s طلّع PDF لزائر من غير دخول" % url)
    assert not r.data.startswith(b"%PDF"), (
        "%s طلّع ملف PDF لزائر من غير دخول" % url)
    if r.status_code in (301, 302, 303, 307, 308):
        loc = r.headers.get("Location", "")
        assert "/login" in loc, (
            "%s حوّل الزائر على %r مش على الدخول" % (url, loc))
        return
    assert r.status_code == 404, (
        "%s رجّع %s لزائر -- المطلوب 404 أو تحويل للدخول"
        % (url, r.status_code))


def test_preview_is_not_open_to_visitors():
    _check("/meal-plan/preview")


def test_sample_pdf_is_not_open_to_visitors():
    _check("/meal-plan/pdf")


def test_patient_pdf_is_not_open_to_visitors():
    _check("/meal-plan/patient/1.pdf")


def test_real_pages_still_work():
    """‏التأكد إن الشيل ماكسرش الدخول ولا الصفحات العادية."""
    assert _CLIENT.get("/login").status_code == 200, "‏الدخول اتكسر"


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:      # ‏500 من جوه الكلاينت ممكن يطلع استثناء
            print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

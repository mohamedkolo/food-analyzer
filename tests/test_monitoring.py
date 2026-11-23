# -*- coding: utf-8 -*-
"""‏Sentry: إيميل لصاحب المشروع أول ما صفحة تضرب.

‏قبل كده الغلطة كانت بتتكتب في سجل Render بس ([NUTRAX-500 ref])، ومحدش
بيعرف غير لو دكتور اشتكى. والموقع فيه بيانات صحية: اللي يروح Sentry هو
مكان الغلطة في الكود بس -- من غير جسم الطلب (أوزان، أمراض)، ولا كوكيز،
ولا قيم المتغيرات، ولا مين المستخدم.

Run with:  python3 tests/test_monitoring.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_monitoring_test.db"
os.environ.pop("SENTRY_DSN", None)

import app as A            # noqa: E402
import monitoring as M     # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False


@A.app.route("/__boom", methods=["GET", "POST"])
def _boom():
    weight = "98.5 kg diabetic"          # ‏قيمة محلية ماينفعش تطلع
    raise RuntimeError("boom " + str(len(weight)))


def _capture():
    from sentry_sdk.transport import Transport

    class Cap(Transport):
        events = []

        def capture_envelope(self, envelope):
            for item in envelope.items:
                ev = item.get_event()
                if ev:
                    Cap.events.append(ev)
    return Cap


def test_without_a_dsn_nothing_is_sent():
    assert M.init() is False
    M.report(RuntimeError("x"), "abc")     # ‏مابيوقعش


def test_a_crash_is_reported_without_client_data():
    cap = _capture()
    assert M.init(dsn="https://k@o0.ingest.sentry.io/1", transport=cap) is True
    try:
        c = A.app.test_client()
        c.set_cookie("session", "secret-cookie")
        r = c.post("/__boom?email=client@x.test", data={"weight": "98.5", "disease": "diabetes"})
        assert r.status_code == 500
        ref = re.search(r"<b>([0-9a-f]{8})</b>", r.get_data(as_text=True)).group(1)
        M.flush()
    finally:
        M.shutdown()
    assert cap.events, "الغلطة ماوصلتش Sentry"
    ev = cap.events[-1]
    text = json.dumps(ev, ensure_ascii=False)
    assert ev["tags"].get("ref") == ref, (ev.get("tags"), ref)
    assert "RuntimeError" in text and "/__boom" in text
    for leak in ("98.5", "diabetes", "diabetic", "client@x.test", "secret-cookie"):
        assert leak not in text, "طلع لـSentry: " + leak


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

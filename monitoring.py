# -*- coding: utf-8 -*-
"""‏Sentry: تنبيه بالإيميل أول ما صفحة تضرب.

‏قبل كده الغلطة كانت بتتكتب في سجل Render بس ([NUTRAX-500 ref])، ومحدش
بيعرف بيها غير لو دكتور اشتكى. بيشتغل بس لو SENTRY_DSN متحط في Render.

‏الموقع فيه بيانات صحية، فاللي بيروح Sentry هو مكان الغلطة في الكود
وبس: الطريقة والمسار من غير query، ورقم المرجع اللي ظهر للدكتور. مفيش
جسم الطلب (أوزان، أمراض)، ولا كوكيز، ولا هيدرز، ولا قيم المتغيرات في
الكود، ولا مين المستخدم. _strip بيمسحهم حتى لو إصدار المكتبة غيّر
الافتراضي -- الإعداد لوحده مش ضمان.
"""

import os

_ON = False


def _strip(event, hint=None):
    req = event.get("request") or {}
    event["request"] = {k: req[k] for k in ("method",) if k in req}
    if req.get("url"):
        event["request"]["url"] = req["url"].split("?")[0]
    for key in ("user", "breadcrumbs", "extra", "contexts", "server_name"):
        event.pop(key, None)
    for exc in (event.get("exception") or {}).get("values") or []:
        for frame in (exc.get("stacktrace") or {}).get("frames") or []:
            for key in ("vars", "pre_context", "context_line", "post_context"):
                frame.pop(key, None)
    for th in (event.get("threads") or {}).get("values") or []:
        for frame in (th.get("stacktrace") or {}).get("frames") or []:
            frame.pop("vars", None)
    return event


def init(dsn=None, **extra):
    """True لو Sentry اشتغل. extra للاختبارات (transport)."""
    global _ON
    dsn = dsn or (os.environ.get("SENTRY_DSN") or "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        print("[monitoring] SENTRY_DSN is set but sentry-sdk is not installed")
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment="production" if os.environ.get("RENDER") else "dev",
        release=os.environ.get("RENDER_GIT_COMMIT") or None,
        traces_sample_rate=0,            # ‏أخطاء بس: الحد المجاني ٥٠٠٠ في الشهر
        max_request_body_size="never",
        data_collection={"user_info": False, "http_bodies": [], "stack_frame_variables": False,
                         "frame_context_lines": 0},
        before_send=_strip,
        **extra)
    _ON = True
    return True


def report(exc, ref):
    """‏الغلطة لـSentry برقم المرجع اللي ظهر في صفحة ٥٠٠. errorhandler(Exception)
    بيمسك الغلطة قبل ما Sentry يشوفها لوحده، فلازم تتبعت من هناك."""
    if not _ON:
        return
    import sentry_sdk
    with sentry_sdk.new_scope() as scope:
        scope.set_tag("ref", ref)
        sentry_sdk.capture_exception(exc)


def flush():
    if _ON:
        import sentry_sdk
        sentry_sdk.flush(timeout=5)


def shutdown():
    global _ON
    if _ON:
        import sentry_sdk
        sentry_sdk.get_client().close(timeout=2)
        sentry_sdk.init()
    _ON = False

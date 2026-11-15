# -*- coding: utf-8 -*-
"""‏كود التأكيد على الإيميل: "نسيت كلمة السر" و"أكّد إيميلك".

‏قبل كده العميل اللي نسي كلمة السر كان بيكلّم الدكتور واتساب، والدكتور
يغيّرها بإيده من لوحة الأدمن. دلوقتي بيوصله كود من ٦ أرقام ويغيّرها
بنفسه. ونفس الكود بيأكّد إيميل الحساب الجديد قبل أول دخول.

‏الكود متخزّن مشفّر، صلاحيته ١٠ دقايق، بيتستخدم مرة واحدة، وبيتقفل بعد
٥ محاولات غلط. وكود جديد مش قبل دقيقة من اللي قبله. ٦ أرقام فيها مليون
احتمال، و٥ محاولات بس، فالتخمين مش طريق.

‏لو الـSMTP مش متظبّط محدش بيتقفل برّه: الحساب الجديد بيدخل عادي،
و"نسيت كلمة السر" بترجع لزراير الواتساب اللي كانت موجودة.
"""

import secrets
import smtplib
import ssl
from datetime import datetime, timedelta

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Blueprint, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

import notifications as N
from core import (db_row, db_run, get_user_by_id, hp, normalize_email,
                  _clear_login_attempts)

bp = Blueprint("codes", __name__)

TTL = timedelta(minutes=10)
RESEND_AFTER = timedelta(seconds=60)
MAX_TRIES = 5
PURPOSES = ("reset", "verify")


def _utcnow():
    return datetime.utcnow()


def _when(v):
    # ‏SQLite بيرجّع التاريخ نص، وPostgres بيرجّعه datetime.
    if isinstance(v, str):
        return datetime.fromisoformat(v.replace("Z", "").split("+")[0])
    return v


def smtp_ready():
    return bool(N.SMTP_HOST and N.SMTP_USER and N.SMTP_PASS)


def _latest(email, purpose):
    return db_row("SELECT * FROM email_codes WHERE email=? AND purpose=?"
                  " ORDER BY id DESC LIMIT 1", (email, purpose))


def issue(email, purpose):
    """كود جديد للإيميل ده، أو None لو اتبعت كود من أقل من دقيقة."""
    assert purpose in PURPOSES
    email = normalize_email(email)
    now = _utcnow()
    last = _latest(email, purpose)
    if last and now - _when(last["created_at"]) < RESEND_AFTER:
        return None
    # ‏كود واحد شغّال بس لكل إيميل وغرض: الجديد بيلغي اللي قبله.
    db_run("UPDATE email_codes SET used=1 WHERE email=? AND purpose=? AND used=0",
           (email, purpose))
    code = "%06d" % secrets.randbelow(1000000)
    db_run("INSERT INTO email_codes (email,purpose,code_hash,expires_at,attempts,used,created_at)"
           " VALUES (?,?,?,?,0,0,?)",
           (email, purpose, generate_password_hash(code), now + TTL, now))
    return code


def check(email, purpose, code):
    """ok / wrong / expired / locked / none."""
    email = normalize_email(email)
    code = "".join(ch for ch in (code or "") if ch.isdigit())
    row = _latest(email, purpose)
    if not row or row["used"]:
        return "none"
    if (row["attempts"] or 0) >= MAX_TRIES:
        return "locked"
    if _utcnow() > _when(row["expires_at"]):
        return "expired"
    if len(code) != 6 or not check_password_hash(row["code_hash"], code):
        db_run("UPDATE email_codes SET attempts=attempts+1 WHERE id=?", (row["id"],))
        return "wrong"
    db_run("UPDATE email_codes SET used=1 WHERE id=?", (row["id"],))
    return "ok"


def send_code(email, code, purpose, lang):
    """بيبعت الكود للعميل. بيرجّع True لو اتبعت."""
    if not smtp_ready():
        return False
    ar = (lang or "ar") == "ar"
    if purpose == "reset":
        subject = "كود تغيير كلمة السر في NutraX" if ar else "Your NutraX password reset code"
        why = ("حد طلب تغيير كلمة السر لحسابك. لو مش إنت، تجاهل الرسالة دي."
               if ar else "Someone asked to reset your password. If it wasn't you, ignore this email.")
    else:
        subject = "كود تأكيد إيميلك في NutraX" if ar else "Confirm your email for NutraX"
        why = ("اكتب الكود ده في الموقع علشان نتأكد إن الإيميل بتاعك."
               if ar else "Enter this code on the site to confirm this email is yours.")
    valid = "الكود شغّال ١٠ دقايق." if ar else "The code works for 10 minutes."
    d = "rtl" if ar else "ltr"
    html = f"""\
<div dir="{d}" style="font-family:Tahoma,Arial,sans-serif;max-width:480px;margin:auto;
     border:1px solid #D5DAE0;border-radius:14px;padding:24px;color:#1E2630">
  <div style="font-size:20px;font-weight:bold;margin-bottom:12px">NutraX</div>
  <p style="line-height:1.7;margin:0 0 16px">{why}</p>
  <div dir="ltr" style="font-size:32px;font-weight:bold;letter-spacing:10px;text-align:center;
       background:#EDF0F3;border-radius:10px;padding:14px 0">{code}</div>
  <p style="color:#5A6472;font-size:13px;margin:16px 0 0">{valid}</p>
</div>"""
    msg = MIMEMultipart("alternative")
    msg["From"] = N.SMTP_FROM
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(f"{why}\n\n{code}\n\n{valid}", "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtplib.SMTP(N.SMTP_HOST, N.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.login(N.SMTP_USER, N.SMTP_PASS)
            server.sendmail(N.SMTP_FROM, [email], msg.as_string())
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[codes] SMTP error: {e}")
        return False


def _digits(code):
    # ‏صفحة النجاح بتعرض الأرقام اللي اتكتبت تاني علشان الخانات تلف بيها.
    # الكود ده خلاص اتستخدم، فعرضه مابيفتحش حاجة.
    return "".join(ch for ch in (code or "") if ch.isdigit())[:6]


def _lang():
    return session.get("lang", "ar")


def _msg(key):
    ar, en = {
        "wrong":   ("الكود مش مظبوط. راجع الأرقام وجرّب تاني.",
                    "That code isn't right. Check the digits and try again."),
        "expired": ("الكود ده خلص وقته. اطلب كود جديد.",
                    "This code has expired. Ask for a new one."),
        "locked":  ("محاولات غلط كتير على الكود ده. اطلب كود جديد.",
                    "Too many wrong tries on this code. Ask for a new one."),
        "none":    ("مافيش كود شغّال. اطلب كود جديد.",
                    "There's no active code. Ask for a new one."),
        "pw_short": ("كلمة السر لازم ٦ حروف على الأقل.",
                     "The password must be at least 6 characters."),
        "resent":  ("بعتنا كود جديد.", "We sent a new code."),
        "wait":    ("استنى دقيقة قبل ما تطلب كود تاني.",
                    "Wait a minute before asking for another code."),
    }[key]
    return ar if _lang() == "ar" else en


def _page(**kw):
    kw.setdefault("lang", _lang())
    kw.setdefault("error", "")
    kw.setdefault("note", "")
    kw.setdefault("done", False)
    kw.setdefault("digits", "")
    return render_template("email_code.html", **kw)


def _send(email, purpose):
    code = issue(email, purpose)
    if code is None:
        return False
    # ‏send_code بيتنادى من الموديول نفسه علشان الاختبارات تقدر تبدّله.
    import email_codes as _self
    _self.send_code(email, code, purpose, _lang())
    return True


# ═══ نسيت كلمة السر ═══

@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    import email_codes as _self
    if not _self.smtp_ready():
        return _page(step="no_smtp")
    if request.method == "POST":
        email = normalize_email(request.form.get("email", ""))
        if email:
            session["reset_email"] = email
            # ‏نفس الرد للإيميل الموجود واللي مش موجود، علشان الصفحة
            # ماتبقاش طريقة يعرف بيها حد مين عنده حساب.
            u = db_row("SELECT id, active FROM users WHERE email=?", (email,))
            if u and u.get("active", 1):
                _send(email, "reset")
            return redirect("/forgot/code")
    return _page(step="email")


@bp.route("/forgot/code", methods=["GET", "POST"])
def forgot_code():
    email = session.get("reset_email")
    if not email:
        return _page(step="code", purpose="reset", email="")
    if request.method == "POST":
        if request.form.get("resend"):
            u = db_row("SELECT id FROM users WHERE email=?", (email,))
            sent = _send(email, "reset") if u else True
            return _page(step="code", purpose="reset", email=email,
                         note=_msg("resent") if sent else _msg("wait"))
        pw = request.form.get("password", "")
        if len(pw) < 6:
            return _page(step="code", purpose="reset", email=email, error=_msg("pw_short"))
        res = check(email, "reset", request.form.get("code", ""))
        if res != "ok":
            return _page(step="code", purpose="reset", email=email, error=_msg(res))
        # ‏اللي غيّر كلمة السر بكود على إيميله أثبت إن الإيميل بتاعه.
        db_run("UPDATE users SET password=?, email_verified=1 WHERE email=?", (hp(pw), email))
        _clear_login_attempts(email)
        session.pop("reset_email", None)
        return _page(step="code", purpose="reset", email=email, done=True,
                     digits=_digits(request.form.get("code", "")))
    return _page(step="code", purpose="reset", email=email)


# ═══ تأكيد الإيميل للحساب الجديد ═══

def needs_verification(user):
    """الحساب ده لازم يأكّد إيميله قبل ما يدخل؟"""
    import email_codes as _self
    return user.get("email_verified") == 0 and _self.smtp_ready()


def start_verification(user, next_url):
    """بدل ما نفتح الجلسة: نبعت كود ونستنى."""
    session["verify_uid"] = user["id"]
    session["verify_next"] = next_url
    _send(user["email"], "verify")
    return redirect("/verify")


@bp.route("/verify", methods=["GET", "POST"])
def verify():
    uid = session.get("verify_uid")
    u = get_user_by_id(uid) if uid else None
    if not u:
        return redirect("/login")
    if request.method == "POST":
        if request.form.get("resend"):
            sent = _send(u["email"], "verify")
            return _page(step="code", purpose="verify", email=u["email"],
                         note=_msg("resent") if sent else _msg("wait"))
        res = check(u["email"], "verify", request.form.get("code", ""))
        if res != "ok":
            return _page(step="code", purpose="verify", email=u["email"], error=_msg(res))
        db_run("UPDATE users SET email_verified=1 WHERE id=?", (u["id"],))
        nxt = session.pop("verify_next", None) or "/dashboard"
        session.pop("verify_uid", None)
        session.permanent = True
        session["uid"] = u["id"]
        session["lang"] = u.get("lang") or _lang()
        from core import get_user_role
        session["role"] = get_user_role(u)
        return _page(step="code", purpose="verify", email=u["email"], done=True, next_url=nxt,
                     digits=_digits(request.form.get("code", "")))
    return _page(step="code", purpose="verify", email=u["email"])

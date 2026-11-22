# notifications.py
# -*- coding: utf-8 -*-
"""
NutraX - نظام إشعارات الأدمن
============================
بيسجّل إشعار في الداتابيز + (اختياري) يبعت إيميل للأدمن.

الإعداد: ضيف الـ env vars دي على Render (Settings → Environment):
  ADMIN_EMAIL   = admin@nutrax.com        (الإيميل اللي هتوصله الإشعارات)
  SMTP_HOST     = smtp-relay.brevo.com    (أو smtp.gmail.com)
  SMTP_PORT     = 587
  SMTP_USER     = اليوزر بتاع SMTP
  SMTP_PASS     = الباسوورد / App Password
  SMTP_FROM     = (اختياري) الإيميل اللي الرسالة تظهر منه

لو الـ SMTP مش متظبّط، الإشعار هيتسجّل في الموقع عادي بس الإيميل بس اللي مش هيتبعت.
"""

import os
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# ═══════════════════════════════════════════════
# إعدادات الإيميل (من الـ environment variables)
# ═══════════════════════════════════════════════
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@nutrax.com")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or 587)
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "") or SMTP_USER or ADMIN_EMAIL

# ═══════════════════════════════════════════════
# أنواع الإشعارات (أيقونة + اسم للعرض)
# ═══════════════════════════════════════════════
# ‏fa: أيقونة خطوط (Font Awesome) للصفحة -- الإيموجي كانت بتطلع بأشكال
# مختلفة على كل جهاز. cat: المجموعة اللي الفلتر فوق الصفحة بيفرز بيها.
NOTIF_TYPES = {
    "new_client":    {"icon": "🆕", "label": "عميل جديد", "label_en": "New client",
                      "fa": "fa-user-plus", "cat": "clients"},
    "plan_request":  {"icon": "📋", "label": "طلب خطة", "label_en": "Plan request",
                      "fa": "fa-clipboard-list", "cat": "requests"},
    "new_message":   {"icon": "💬", "label": "رسالة جديدة", "label_en": "New message",
                      "fa": "fa-comment", "cat": "messages"},
    "payment_click": {"icon": "💰", "label": "ضغط دفع واتساب", "label_en": "WhatsApp payment click",
                      "fa": "fa-hand-pointer", "cat": "payments"},
    "booking_request": {"icon": "📅", "label": "طلب حجز", "label_en": "Booking request",
                        "fa": "fa-calendar-check", "cat": "bookings"},
    "booking_payment": {"icon": "💵", "label": "تحويل استشارة", "label_en": "Consultation transfer",
                        "fa": "fa-money-bill-transfer", "cat": "payments"},
}
_OTHER = {"icon": "🔔", "label": "إشعار", "label_en": "Notification", "fa": "fa-bell", "cat": "other"}


def get_type_meta(type_):
    return NOTIF_TYPES.get(type_, _OTHER)


# ═══════════════════════════════════════════════
# العرض: مجموعات بالأيام ووقت بيتقري زي الكلام
# ═══════════════════════════════════════════════
_AR_MONTHS = ("يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو",
              "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر")
_GROUPS = (("today", "النهارده", "Today"), ("yesterday", "امبارح", "Yesterday"),
           ("week", "الأسبوع ده", "This week"), ("older", "أقدم", "Older"))


def _as_datetime(value):
    from datetime import datetime
    if isinstance(value, datetime):
        return value
    text = str(value or "").replace("T", " ")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _clock(dt, ar):
    h = dt.hour % 12 or 12
    if ar:
        return "%d:%02d %s" % (h, dt.minute, "ص" if dt.hour < 12 else "م")
    return "%d:%02d %s" % (h, dt.minute, "AM" if dt.hour < 12 else "PM")


def _ago(minutes, ar):
    if minutes < 1:
        return "دلوقتي" if ar else "just now"
    if minutes < 60:
        if not ar:
            return "%d min ago" % minutes
        return {1: "من دقيقة", 2: "من دقيقتين"}.get(
            minutes, "من %d %s" % (minutes, "دقايق" if minutes <= 10 else "دقيقة"))
    hours = minutes // 60
    if not ar:
        return "%d h ago" % hours
    return {1: "من ساعة", 2: "من ساعتين"}.get(
        hours, "من %d %s" % (hours, "ساعات" if hours <= 10 else "ساعة"))


def present(rows, tz_name="Africa/Cairo", lang="ar", now_utc=None):
    """‏الإشعارات زي ما الصفحة بتعرضها: [{key, label, items: [...]}].

    ‏created_at بيتسجّل CURRENT_TIMESTAMP -- توقيت جرينتش. الصفحة كانت
    بتكتبه زي ما هو، فاللي حصل الساعة ١١ في القاهرة كان مكتوب ٩، و"امبارح"
    كان بيبدأ الساعة ٢ الصبح. فالوقت بيتحوّل لتوقيت الأدمن الأول، والأيام
    بتتقسم على توقيته.
    """
    from datetime import datetime, timedelta, timezone
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name or "Africa/Cairo")
    except Exception:
        tz = timezone(timedelta(hours=2))
    ar = lang != "en"
    now = (now_utc or datetime.utcnow()).replace(tzinfo=timezone.utc).astimezone(tz)
    buckets = {key: [] for key, _a, _e in _GROUPS}
    for row in rows or []:
        meta = get_type_meta(row.get("type"))
        raw = _as_datetime(row.get("created_at"))
        local = raw.replace(tzinfo=timezone.utc).astimezone(tz) if raw else now
        days = (now.date() - local.date()).days
        if days <= 0:
            key = "today"
            when = _ago(max(0, int((now - local).total_seconds() // 60)), ar)
        elif days == 1:
            key, when = "yesterday", _clock(local, ar)
        else:
            key = "week" if days < 7 else "older"
            day = ("%d %s" % (local.day, _AR_MONTHS[local.month - 1]) if ar
                   else local.strftime("%-d %b"))
            when = "%s · %s" % (day, _clock(local, ar))
        buckets[key].append({
            "id": row.get("id"), "title": row.get("title") or "",
            "message": row.get("message") or "", "link": row.get("link") or "",
            "unread": not row.get("is_read"), "when": when,
            "iso": local.strftime("%Y-%m-%dT%H:%M"),
            "label": meta["label"] if ar else meta["label_en"],
            "icon": meta["fa"], "cat": meta["cat"],
        })
    return [{"key": key, "label": a if ar else e, "items": buckets[key]}
            for key, a, e in _GROUPS if buckets[key]]


# ═══════════════════════════════════════════════
# إنشاء الجدول (يتنادى مرة واحدة عند التشغيل)
# ═══════════════════════════════════════════════
def ensure_table(db_run, is_postgres=False):
    """بيعمل جدول الإشعارات لو مش موجود."""
    try:
        if is_postgres:
            db_run("""CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                type TEXT,
                title TEXT,
                message TEXT,
                link TEXT,
                related_user_id INTEGER,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        else:
            db_run("""CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                title TEXT,
                message TEXT,
                link TEXT,
                related_user_id INTEGER,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
    except Exception as e:
        print(f"[notif] table create warning: {e}")


# ═══════════════════════════════════════════════
# تسجيل إشعار جديد
# ═══════════════════════════════════════════════
def add_notification(db_run, type_, title, message, link=None,
                     related_user_id=None, send_email_too=True):
    """
    بيسجّل إشعار في الداتابيز + (اختياري) يبعت إيميل للأدمن.
    آمن: أي خطأ في الإيميل مش بيوقّف تسجيل الإشعار.
    """
    try:
        db_run("""INSERT INTO notifications (type, title, message, link, related_user_id)
                  VALUES (?, ?, ?, ?, ?)""",
               (type_, title, message, link, related_user_id))
    except Exception as e:
        print(f"[notif] insert error: {e}")

    if send_email_too:
        # الإيميل بيتبعت في الخلفية عشان ما يعطّلش الطلب لو السيرفر بطيء
        try:
            import threading
            threading.Thread(
                target=_safe_send_email,
                args=(type_, title, message, link),
                daemon=True
            ).start()
        except Exception as e:
            print(f"[notif] email thread error: {e}")


def _safe_send_email(type_, title, message, link):
    try:
        send_admin_email(type_, title, message, link)
    except Exception as e:
        print(f"[notif] email send error: {e}")


# ═══════════════════════════════════════════════
# قراءة الإشعارات
# ═══════════════════════════════════════════════
def get_unread_count(db_row):
    """عدد الإشعارات غير المقروءة (للـ badge الأحمر)."""
    try:
        r = db_row("SELECT COUNT(*) as c FROM notifications WHERE is_read=0")
        return (r.get("c", 0) if r else 0) or 0
    except Exception:
        return 0


def get_all_notifications(db_rows, limit=100):
    """كل الإشعارات (الأحدث أولاً)."""
    try:
        return db_rows(f"SELECT * FROM notifications ORDER BY created_at DESC LIMIT {int(limit)}")
    except Exception:
        return []


def mark_all_read(db_run):
    try:
        db_run("UPDATE notifications SET is_read=1 WHERE is_read=0")
    except Exception as e:
        print(f"[notif] mark all read error: {e}")


def mark_read(db_run, notif_id):
    try:
        db_run("UPDATE notifications SET is_read=1 WHERE id=?", (notif_id,))
    except Exception as e:
        print(f"[notif] mark read error: {e}")


# ═══════════════════════════════════════════════
# إرسال الإيميل
# ═══════════════════════════════════════════════
DOMAIN = os.environ.get("DOMAIN", "https://food-analyzer-duag.onrender.com")


def send_admin_email(type_, title, message, link=None):
    """بيبعت إيميل HTML بسيط للأدمن. بيرجّع True لو اتبعت."""
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        print("[notif] SMTP not configured - email skipped")
        return False

    meta = get_type_meta(type_)
    # ‏الدومين من المتغيّر زي payments.py وapi_platform.py. كان مكتوب هنا
    # بالإيد لوحده -- فلو الدومين اتغيّر، كل اللينكات التانية بتتحوّل
    # وده يفضل على القديم ويبعت الدكتور على عنوان مش شغّال.
    full_link = link or (DOMAIN.rstrip("/") + "/admin/notifications")

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_FROM
    msg["To"] = ADMIN_EMAIL
    msg["Subject"] = f"NutraX {meta['icon']} {title}"

    html = f"""\
<div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;max-width:520px;margin:auto;
     border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;">
  <div style="background:linear-gradient(135deg,#059669,#10b981);color:#fff;padding:18px 22px;">
    <div style="font-size:22px;font-weight:bold;">{meta['icon']} {meta['label']}</div>
  </div>
  <div style="padding:22px;color:#0f172a;">
    <h2 style="margin:0 0 10px;font-size:18px;">{title}</h2>
    <p style="margin:0 0 18px;color:#475569;line-height:1.7;font-size:15px;">{message}</p>
    <a href="{full_link}"
       style="display:inline-block;background:#059669;color:#fff;text-decoration:none;
              padding:12px 26px;border-radius:10px;font-weight:bold;font-size:14px;">
       افتح لوحة التحكم
    </a>
  </div>
  <div style="background:#f8fafc;padding:14px 22px;color:#94a3b8;font-size:12px;text-align:center;">
    NutraX Clinical Nutrition — إشعار تلقائي
  </div>
</div>"""

    plain = f"{meta['label']}: {title}\n\n{message}\n\n{full_link}"

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [ADMIN_EMAIL], msg.as_string())
        print(f"[notif] email sent to {ADMIN_EMAIL}")
        return True
    except Exception as e:
        print(f"[notif] SMTP error: {e}")
        return False


# ═══════════════════════════════════════════════
# إرسال خطة PDF للعميل بالإيميل
# ═══════════════════════════════════════════════
def send_plan_pdf_email(to_email, client_name, pdf_bytes, filename="meal_plan.pdf"):
    """بيبعت خطة الأكل PDF كمرفق لإيميل العميل. بيرجّع True لو اتبعت."""
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        print("[notif] SMTP not configured - plan email skipped")
        return False
    if not to_email:
        return False

    msg = MIMEMultipart("mixed")
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = "🎉 خطتك الغذائية جاهزة - NutraX"

    body = MIMEMultipart("alternative")
    html = f"""\
<div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;max-width:520px;margin:auto;
     border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;">
  <div style="background:linear-gradient(135deg,#059669,#10b981);color:#fff;padding:18px 22px;">
    <div style="font-size:22px;font-weight:bold;">🎉 خطتك الغذائية جاهزة</div>
  </div>
  <div style="padding:22px;color:#0f172a;">
    <p style="margin:0 0 18px;color:#475569;line-height:1.7;font-size:15px;">
      أهلاً {client_name or 'بيك'}، د. محمد جهّزلك خطة غذائية جديدة — هتلاقيها مرفقة في الإيميل ده (PDF)،
      وكمان متاحة على طول من داخل التطبيق.
    </p>
  </div>
  <div style="background:#f8fafc;padding:14px 22px;color:#94a3b8;font-size:12px;text-align:center;">
    NutraX Clinical Nutrition — إشعار تلقائي
  </div>
</div>"""
    plain = f"أهلاً {client_name or ''}، خطتك الغذائية الجديدة مرفقة في هذا الإيميل (PDF)."
    body.attach(MIMEText(plain, "plain", "utf-8"))
    body.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(body)

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        print(f"[notif] plan PDF emailed to {to_email}")
        return True
    except Exception as e:
        print(f"[notif] plan PDF SMTP error: {e}")
        return False


# ═══════════════════════════════════════════════
# إيميل قصير للعميل (حالة الحجز، التذكير بالموعد)
# ═══════════════════════════════════════════════
def send_client_email(to_email, subject, message, link=None, lang="ar"):
    """‏إيميل نصّي بسيط للعميل. بيرجّع True لو اتبعت.

    ‏نصّي بالقصد: ده تنبيه من سطرين ولينك، والنص العادي بيوصل في أي
    برنامج بريد ومابيتحطش في الـspam زي قالب مليان ألوان.
    """
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS) or not to_email:
        return False
    body = message
    if link:
        full = link if link.startswith("http") else DOMAIN.rstrip("/") + link
        body += "\n\n" + full
    body += "\n\n— NutraX"
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = "NutraX — %s" % subject
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[notif] client email error: {e}")
        return False

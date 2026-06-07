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
NOTIF_TYPES = {
    "new_client":    {"icon": "🆕", "label": "عميل جديد"},
    "plan_request":  {"icon": "📋", "label": "طلب خطة"},
    "new_message":   {"icon": "💬", "label": "رسالة جديدة"},
    "payment_click": {"icon": "💰", "label": "ضغط دفع واتساب"},
}


def get_type_meta(type_):
    return NOTIF_TYPES.get(type_, {"icon": "🔔", "label": "إشعار"})


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
def send_admin_email(type_, title, message, link=None):
    """بيبعت إيميل HTML بسيط للأدمن. بيرجّع True لو اتبعت."""
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        print("[notif] SMTP not configured - email skipped")
        return False

    meta = get_type_meta(type_)
    full_link = link or "https://food-analyzer-duag.onrender.com/admin/notifications"

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

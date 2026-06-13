# push.py
# -*- coding: utf-8 -*-
"""
NutraX - إشعارات الموبايل (Web Push)
=====================================
وحدة مستقلة: بتسجّل اشتراكات الموبايل وبتبعت إشعار للأدمن/الأخصائي
حتى والموقع مقفول.

الربط في app.py سطرين بس:
    from push import push_bp, push_to_staff
    app.register_blueprint(push_bp)

ومفاتيح Render المطلوبة (Environment):
    VAPID_PUBLIC_KEY   = ...
    VAPID_PRIVATE_KEY  = ...
    VAPID_CLAIM_EMAIL  = mailto:admin@nutrax.com   (اختياري)

لو المكتبة أو المفاتيح مش موجودة، الوحدة بتشتغل بصمت من غير ما تكسر الموقع.
"""

import os, json, threading
from flask import Blueprint, request, session, jsonify

push_bp = Blueprint("push", __name__)

VAPID_PUBLIC_KEY  = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@nutrax.com")

try:
    from pywebpush import webpush, WebPushException
    _PUSH_AVAILABLE = True
except Exception:
    _PUSH_AVAILABLE = False

DATABASE_URL = os.environ.get("DATABASE_URL")

# ═══════════════════════════════════════════════
# قاعدة البيانات (نفس أسلوب app.py)
# ═══════════════════════════════════════════════
if DATABASE_URL:
    import psycopg2, psycopg2.extras
    def _get_db(): return psycopg2.connect(DATABASE_URL)
    def db_row(sql, params=()):
        sql = sql.replace("?", "%s")
        conn = _get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params); r = cur.fetchone(); conn.close(); return r
    def db_rows(sql, params=()):
        sql = sql.replace("?", "%s")
        conn = _get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params); r = cur.fetchall(); conn.close(); return r
    def db_run(sql, params=(), commit=True):
        sql = sql.replace("?", "%s")
        conn = _get_db(); cur = conn.cursor()
        try: cur.execute(sql, params)
        except: conn.rollback(); conn.close(); raise
        if commit: conn.commit()
        conn.close()
else:
    import sqlite3
    _DB = "/tmp/nutrax.db"
    def _dict_factory(cursor, row):
        return {col[0]: row[i] for i, col in enumerate(cursor.description)}
    def _get_db():
        conn = sqlite3.connect(_DB); conn.row_factory = _dict_factory; return conn
    def db_row(sql, params=()):
        conn = _get_db(); r = conn.execute(sql, params).fetchone(); conn.close(); return r
    def db_rows(sql, params=()):
        conn = _get_db(); r = conn.execute(sql, params).fetchall(); conn.close(); return r
    def db_run(sql, params=(), commit=True):
        conn = _get_db(); conn.execute(sql, params)
        if commit: conn.commit()
        conn.close()


def ensure_table():
    """يعمل جدول الاشتراكات لو مش موجود."""
    try:
        if DATABASE_URL:
            db_run("""CREATE TABLE IF NOT EXISTS push_subscriptions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        endpoint TEXT UNIQUE,
                        sub_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        else:
            db_run("""CREATE TABLE IF NOT EXISTS push_subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        endpoint TEXT UNIQUE,
                        sub_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    except Exception as e:
        print(f"push table init error: {e}")

ensure_table()


# ═══════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════
@push_bp.route("/push/public-key")
def push_public_key():
    """بيرجّع المفتاح العام للمتصفح عشان يعمل اشتراك."""
    return jsonify({"key": VAPID_PUBLIC_KEY})


@push_bp.route("/push/subscribe", methods=["POST"])
def push_subscribe():
    """بيستقبل اشتراك الموبايل ويخزنه."""
    uid = session.get("uid")
    if not uid:
        return jsonify({"ok": False, "error": "no session"}), 401
    try:
        sub = request.get_json(silent=True) or {}
        endpoint = sub.get("endpoint")
        if not endpoint:
            return jsonify({"ok": False, "error": "no endpoint"}), 400
        sub_json = json.dumps(sub, ensure_ascii=False)
        try:
            db_run("DELETE FROM push_subscriptions WHERE endpoint=?", (endpoint,))
        except: pass
        db_run("INSERT INTO push_subscriptions (user_id, endpoint, sub_json) VALUES (?,?,?)",
               (uid, endpoint, sub_json))
        return jsonify({"ok": True})
    except Exception as e:
        print(f"push subscribe error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@push_bp.route("/push/unsubscribe", methods=["POST"])
def push_unsubscribe():
    try:
        sub = request.get_json(silent=True) or {}
        endpoint = sub.get("endpoint")
        if endpoint:
            db_run("DELETE FROM push_subscriptions WHERE endpoint=?", (endpoint,))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ═══════════════════════════════════════════════
# إرسال الإشعار
# ═══════════════════════════════════════════════
def _send_one(sub_json, payload):
    try:
        webpush(
            subscription_info=json.loads(sub_json),
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_CLAIM_EMAIL},
            ttl=86400,
        )
        return True
    except WebPushException as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        if code in (404, 410):
            try:
                data = json.loads(sub_json)
                db_run("DELETE FROM push_subscriptions WHERE endpoint=?", (data.get("endpoint"),))
            except: pass
        else:
            print(f"webpush error: {e}")
        return False
    except Exception as e:
        print(f"webpush error: {e}")
        return False


def _send_to_staff_bg(title, body, url):
    try:
        subs = db_rows("""SELECT ps.sub_json
                          FROM push_subscriptions ps
                          JOIN users u ON ps.user_id = u.id
                          WHERE u.role IN ('admin','nutritionist') OR u.is_admin = 1""")
        payload = {"title": title or "NutraX", "body": body or "", "url": url or "/admin/notifications"}
        for s in subs or []:
            _send_one(s["sub_json"], payload)
    except Exception as e:
        print(f"push to staff error: {e}")


def push_to_staff(title, body, url="/admin/notifications"):
    """بيبعت إشعار موبايل لكل الأدمن/الأخصائيين المشتركين (في الخلفية)."""
    if not _PUSH_AVAILABLE or not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        return
    threading.Thread(target=_send_to_staff_bg, args=(title, body, url), daemon=True).start()

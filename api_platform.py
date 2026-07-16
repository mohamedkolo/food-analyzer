# api_platform.py
# -*- coding: utf-8 -*-
"""
NutraX Developer API — منتج SaaS منفصل عن تطبيق العملاء
=========================================================
بيبيع وصول برمجي (API key) لمولد خطط الوجبات ومكتبة الأكلات لمطورين تانيين
(تطبيقات فيتنس/دايت) — اشتراك شهري متكرر بيتجدد أوتوماتيك عبر Stripe،
منفصل تماماً عن اشتراكات عيادة د. محمد (جدول subscriptions الأصلي).

الربط في app.py (زي payments.py بالظبط — وحدة منطق بدون routes):
    from api_platform import (
        ensure_api_table, API_TIERS, make_require_api_key,
        get_or_create_api_key, regenerate_api_key, get_usage_info,
        create_api_checkout_session, handle_api_checkout_completed,
        handle_api_invoice_paid, handle_api_subscription_updated,
        handle_api_subscription_canceled,
    )
    ensure_api_table(db_run, is_postgres=bool(DATABASE_URL))
    require_api_key = make_require_api_key(db_row, db_run)
    # الـ routes (/developers, /dashboard/api, /api/v1/...) بتتعرّف في app.py
    # عشان محتاجة generate_weekly_plan وباقي الـ helpers اللي هناك.
"""

import os
import secrets
import stripe
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

DOMAIN = os.environ.get("DOMAIN", "https://food-analyzer-duag.onrender.com")

# ═══════════════════════════════════════════════
# TIERS: مجاني تلقائي + خطتين مدفوعتين (اشتراك شهري متكرر)
# ═══════════════════════════════════════════════

API_TIERS = {
    "free": {
        "name": "مجاني", "name_en": "Free",
        "quota": 100, "prices": None,
    },
    "starter": {
        "name": "Starter", "name_en": "Starter",
        "quota": 5000,
        #              EGP   USD  AED  SAR
        "prices": {"EGP": 300, "USD": 6, "AED": 22, "SAR": 23},
    },
    "pro": {
        "name": "Pro", "name_en": "Pro",
        "quota": 50000,
        "prices": {"EGP": 1500, "USD": 30, "AED": 110, "SAR": 113},
    },
}


def _tier_prices_cents(tier_key):
    t = API_TIERS[tier_key]
    if not t["prices"]:
        return {}
    return {cur: int(round(val * 100)) for cur, val in t["prices"].items()}


# ═══════════════════════════════════════════════
# DB
# ═══════════════════════════════════════════════

def ensure_api_table(db_run, is_postgres=False):
    """يجهّز جدول api_keys — آمن يتنفذ كل مرة السيرفر يبدأ."""
    if is_postgres:
        sql = """CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            api_key TEXT UNIQUE NOT NULL,
            tier TEXT DEFAULT 'free',
            monthly_quota INTEGER DEFAULT 100,
            requests_used INTEGER DEFAULT 0,
            requests_reset_at TIMESTAMP,
            stripe_subscription_id TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP
        )"""
    else:
        sql = """CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            api_key TEXT UNIQUE NOT NULL,
            tier TEXT DEFAULT 'free',
            monthly_quota INTEGER DEFAULT 100,
            requests_used INTEGER DEFAULT 0,
            requests_reset_at TIMESTAMP,
            stripe_subscription_id TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP
        )"""
    try:
        db_run(sql)
    except Exception as e:
        print(f"[api_platform] table create warning: {e}")


def generate_api_key():
    return "nutrax_live_" + secrets.token_urlsafe(24)


def _reset_if_due(row, db_run):
    """لو تاريخ إعادة التعيين الشهري فات، يصفّر العداد ويحدد ميعاد جديد. بيرجّع الصف (مُحدّث لو لزم)."""
    reset_at = row.get("requests_reset_at")
    now = datetime.now()
    due = False
    if not reset_at:
        due = True
    else:
        if isinstance(reset_at, str):
            try:
                reset_at = datetime.fromisoformat(reset_at.replace("Z", ""))
            except Exception:
                due = True
        if not due and now >= reset_at:
            due = True
    if due:
        new_reset = now + timedelta(days=30)
        try:
            db_run("UPDATE api_keys SET requests_used=0, requests_reset_at=? WHERE id=?",
                   (new_reset, row["id"]))
        except Exception as e:
            print(f"[api_platform] reset error: {e}")
        row["requests_used"] = 0
        row["requests_reset_at"] = new_reset
    return row


def get_or_create_api_key(user_id, db_row, db_run):
    """يرجّع صف مفتاح الـ API بتاع اليوزر، وينشئه بتير مجاني لو أول مرة."""
    row = db_row("SELECT * FROM api_keys WHERE user_id=?", (user_id,))
    if row:
        return _reset_if_due(dict(row), db_run)
    key = generate_api_key()
    reset_at = datetime.now() + timedelta(days=30)
    db_run("""INSERT INTO api_keys (user_id, api_key, tier, monthly_quota, requests_used, requests_reset_at, active)
              VALUES (?, ?, 'free', ?, 0, ?, 1)""",
           (user_id, key, API_TIERS["free"]["quota"], reset_at))
    return db_row("SELECT * FROM api_keys WHERE user_id=?", (user_id,))


def regenerate_api_key(user_id, db_row, db_run):
    row = get_or_create_api_key(user_id, db_row, db_run)
    new_key = generate_api_key()
    db_run("UPDATE api_keys SET api_key=? WHERE user_id=?", (new_key, user_id))
    return new_key


def get_usage_info(user_id, db_row, db_run):
    row = get_or_create_api_key(user_id, db_row, db_run)
    if not row:
        return None
    row = dict(row)
    tier = API_TIERS.get(row.get("tier") or "free", API_TIERS["free"])
    used = row.get("requests_used") or 0
    quota = row.get("monthly_quota") or tier["quota"]
    reset_at = row.get("requests_reset_at")
    return {
        "api_key": row.get("api_key"),
        "tier": row.get("tier") or "free",
        "tier_name": tier["name"],
        "quota": quota,
        "used": used,
        "remaining": max(0, quota - used),
        "reset_at": reset_at,
        "active": bool(row.get("active", 1)),
    }


# ═══════════════════════════════════════════════
# AUTH DECORATOR (factory — بياخد db_row/db_run من app.py)
# ═══════════════════════════════════════════════

def make_require_api_key(db_row, db_run):
    def require_api_key(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            key = request.headers.get("X-API-Key") or request.args.get("api_key")
            if not key:
                return jsonify({"ok": False, "error": "missing_api_key",
                                 "message": "ابعت مفتاح الـ API في هيدر X-API-Key"}), 401
            row = db_row("SELECT * FROM api_keys WHERE api_key=?", (key,))
            if not row or not row.get("active", 1):
                return jsonify({"ok": False, "error": "invalid_api_key"}), 401
            row = _reset_if_due(dict(row), db_run)
            quota = row.get("monthly_quota") or API_TIERS["free"]["quota"]
            used = row.get("requests_used") or 0
            if used >= quota:
                return jsonify({"ok": False, "error": "quota_exceeded",
                                 "message": "تعديت حد الطلبات الشهري لخطتك — رقّي خطتك من /developers"}), 429
            try:
                db_run("UPDATE api_keys SET requests_used=requests_used+1, last_used_at=? WHERE id=?",
                       (datetime.now(), row["id"]))
            except Exception as e:
                print(f"[api_platform] usage increment error: {e}")
            request.api_user_id = row["user_id"]
            return f(*args, **kwargs)
        return decorated
    return require_api_key


# ═══════════════════════════════════════════════
# STRIPE CHECKOUT (اشتراك شهري متكرر — منفصل عن أسعار العيادة)
# ═══════════════════════════════════════════════

def create_api_checkout_session(user, tier_key, currency="USD"):
    if not stripe.api_key:
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        raise RuntimeError("Stripe not configured - missing STRIPE_SECRET_KEY")
    if tier_key not in API_TIERS or not API_TIERS[tier_key]["prices"]:
        raise ValueError(f"Unknown/unbuyable API tier: {tier_key}")

    prices = _tier_prices_cents(tier_key)
    if currency not in prices:
        currency = "USD"
    tier = API_TIERS[tier_key]

    session_params = {
        "payment_method_types": ["card"],
        "line_items": [{
            "price_data": {
                "currency": currency.lower(),
                "product_data": {
                    "name": f"NutraX API — {tier['name_en']}",
                    "description": f"{tier['quota']} requests/month",
                },
                "unit_amount": prices[currency],
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }],
        "mode": "subscription",
        "success_url": f"{DOMAIN}/dashboard/api?checkout=success",
        "cancel_url": f"{DOMAIN}/dashboard/api?checkout=cancel",
        "customer_email": user.get("email"),
        "metadata": {"product": "api", "user_id": str(user["id"]), "tier": tier_key},
        "subscription_data": {
            "metadata": {"product": "api", "user_id": str(user["id"]), "tier": tier_key},
        },
        "locale": "auto",
    }
    return stripe.checkout.Session.create(**session_params)


def handle_api_checkout_completed(session_obj, db_run, db_row):
    """True لو الحدث ده كان لمنتج الـ API فعلاً (وبيتم التعامل معاه)، False لو مش بتاعنا."""
    metadata = session_obj.get("metadata", {}) or {}
    if metadata.get("product") != "api":
        return False
    user_id = int(metadata.get("user_id", 0))
    tier_key = metadata.get("tier", "")
    subscription_id = session_obj.get("subscription", "")
    if not user_id or tier_key not in API_TIERS:
        return True  # بتاعنا لكن بيانات ناقصة — منسجّلش حاجة تانية

    get_or_create_api_key(user_id, db_row, db_run)
    quota = API_TIERS[tier_key]["quota"]
    reset_at = datetime.now() + timedelta(days=30)
    db_run("""UPDATE api_keys SET tier=?, monthly_quota=?, requests_used=0,
              requests_reset_at=?, stripe_subscription_id=?, active=1 WHERE user_id=?""",
           (tier_key, quota, reset_at, subscription_id, user_id))
    return True


def _find_by_subscription(sub_id, db_row):
    if not sub_id:
        return None
    return db_row("SELECT * FROM api_keys WHERE stripe_subscription_id=?", (sub_id,))


def handle_api_invoice_paid(invoice_obj, db_run, db_row):
    """تجديد شهري ناجح — يصفّر العداد ويمدد الفترة. بيرجّع False لو الاشتراك مش بتاع الـ API."""
    sub_id = invoice_obj.get("subscription")
    row = _find_by_subscription(sub_id, db_row)
    if not row:
        return False
    reset_at = datetime.now() + timedelta(days=30)
    db_run("UPDATE api_keys SET requests_used=0, requests_reset_at=?, active=1 WHERE id=?",
           (reset_at, row["id"]))
    return True


def handle_api_subscription_updated(sub_obj, db_run, db_row):
    sub_id = sub_obj.get("id")
    row = _find_by_subscription(sub_id, db_row)
    if not row:
        return False
    status = sub_obj.get("status")
    db_run("UPDATE api_keys SET active=? WHERE id=?",
           (1 if status in ("active", "trialing") else 0, row["id"]))
    return True


def handle_api_subscription_canceled(sub_obj, db_run, db_row):
    """لما الاشتراك يتلغي، يرجّع المفتاح لتير مجاني بدل ما يقفله خالص."""
    sub_id = sub_obj.get("id")
    row = _find_by_subscription(sub_id, db_row)
    if not row:
        return False
    reset_at = datetime.now() + timedelta(days=30)
    db_run("""UPDATE api_keys SET tier='free', monthly_quota=?, requests_used=0,
              requests_reset_at=?, stripe_subscription_id=NULL, active=1 WHERE id=?""",
           (API_TIERS["free"]["quota"], reset_at, row["id"]))
    return True

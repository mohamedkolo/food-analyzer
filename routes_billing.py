# -*- coding: utf-8 -*-
"""Money: pricing, checkout, Stripe webhooks, subscriptions.

Kept together deliberately. Everything that can take a payment or change what
a client has paid for is in one file, so the whole billing surface can be read
in one sitting.

The webhook is exempt from CSRF because Stripe signs it instead -- see
verify_webhook in payments.py.
"""

import os
from datetime import datetime

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session)

from core import (
    csrf, cur_lang, db_row, db_rows, db_run, get_user_by_id,
    login_required, admin_required, subscription_required, _plan_name,
)
from payments import (
    PRICING, create_checkout_session, verify_webhook, detect_currency,
    get_supported_currencies, get_user_access_info, cancel_user_subscription,
    handle_checkout_completed, handle_invoice_paid,
    handle_subscription_canceled, handle_subscription_updated,
    build_admin_analytics,
)
from api_platform import (
    handle_api_checkout_completed, handle_api_invoice_paid,
    handle_api_subscription_canceled, handle_api_subscription_updated,
)
bp = Blueprint("billing", __name__)

# ═══════════════════════════════════════════════════════════════════
# PAYMENT ROUTES (Stripe Integration)
# ═══════════════════════════════════════════════════════════════════

@bp.route("/pricing")
def pricing():
    """صفحة عرض الأسعار - متاحة للجميع حتى بدون تسجيل دخول"""
    user = None
    user_currency = "EGP"
    active_access = None
    if "uid" in session:
        user = get_user_by_id(session["uid"])
        if user:
            user_currency = detect_currency(user.get("country"))
            try:
                active_access = get_user_access_info(session["uid"], db_row, cur_lang())
            except: pass
    return render_template("pricing.html",
                           user=user,
                           lang=session.get("lang", "ar"),
                           pricing=PRICING,
                           user_currency=user_currency,
                           active_access=active_access)


@bp.route("/subscription-required")
@login_required
def subscription_required_page():
    """صفحة الـ paywall - بتظهر لما العميل يحاول يدخل حاجة محتاجة اشتراك"""
    user = get_user_by_id(session["uid"])
    reason_key = request.args.get("reason", "")
    _lang = session.get("lang", "ar")
    reasons_map = {
        "chat": ("محتاج اشتراك علشان تكلم د. محمد مباشرة في الشات.",
                 "You need a subscription to chat with Dr. Mohamed directly."),
        "plan": ("محتاج اشتراك أو خطة مدفوعة علشان تطلب خطة جديدة.",
                 "You need a subscription or a paid plan to request a new plan."),
    }
    reason = reasons_map.get(reason_key,
                             ("محتاج اشتراك علشان تستخدم الخدمة دي.",
                              "You need a subscription to use this feature."))[0 if _lang == "ar" else 1]
    user_currency = detect_currency(user.get("country")) if user else "EGP"
    return render_template("subscription_required.html",
                           user=user, lang=_lang,
                           reason=reason, pricing=PRICING,
                           user_currency=user_currency)


@bp.route("/checkout/<plan_key>")
@login_required
def checkout(plan_key):
    """بدء جلسة دفع Stripe"""
    user = get_user_by_id(session["uid"])
    if not user:
        return redirect("/")

    if plan_key not in PRICING:
        return redirect("/pricing")

    currency = request.args.get("currency", "").upper()
    if currency not in get_supported_currencies():
        currency = detect_currency(user.get("country"))

    try:
        checkout_session = create_checkout_session(user, plan_key, currency)
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        import traceback; traceback.print_exc()
        return render_template("payment_cancel.html",
                               user=user, lang=session.get("lang", "ar"),
                               error=f"خطأ في إنشاء جلسة الدفع: {str(e)}"), 500


@bp.route("/payment/success")
@login_required
def payment_success():
    """صفحة نجاح الدفع - بتعرض تأكيد للعميل"""
    import stripe
    user = get_user_by_id(session["uid"])
    session_id = request.args.get("session_id", "")

    plan_name = None
    amount = None
    expires_at = None
    is_trial = False

    if session_id and os.environ.get("STRIPE_SECRET_KEY"):
        try:
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
            cs = stripe.checkout.Session.retrieve(session_id)
            metadata = cs.get("metadata", {}) or {}
            plan_key = metadata.get("plan_key", "")
            if plan_key in PRICING:
                plan_name = _plan_name(PRICING[plan_key], plan_key)
            currency = metadata.get("currency", "USD")
            amt = cs.get("amount_total", 0)
            if amt:
                amount = f"{amt / 100:.0f} {currency}"
            if cs.get("subscription"):
                try:
                    sub = stripe.Subscription.retrieve(cs.subscription)
                    if sub.trial_end:
                        is_trial = True
                        from datetime import datetime as dt
                        expires_at = dt.fromtimestamp(sub.trial_end).strftime("%Y-%m-%d")
                except: pass
        except Exception as e:
            print(f"Stripe fetch error: {e}")

    if not plan_name:
        try:
            access = get_user_access_info(session["uid"], db_row, cur_lang())
            if access and access.get("has_access"):
                plan_name = access.get("plan_name")
                is_trial = access.get("is_trial", False)
                exp = access.get("expires_at")
                if exp:
                    expires_at = exp.strftime("%Y-%m-%d") if hasattr(exp, "strftime") else str(exp)[:10]
        except: pass

    return render_template("payment_success.html",
                           user=user, lang=session.get("lang", "ar"),
                           plan_name=plan_name, amount=amount,
                           expires_at=expires_at, is_trial=is_trial)


@bp.route("/payment/cancel")
def payment_cancel():
    """صفحة إلغاء الدفع"""
    user = None
    if "uid" in session:
        user = get_user_by_id(session["uid"])
    return render_template("payment_cancel.html",
                           user=user, lang=session.get("lang", "ar"))


@bp.route("/webhook/stripe", methods=["POST"])
@csrf.exempt
def stripe_webhook():
    """استقبال أحداث Stripe (الدفع نجح، اشتراك اتجدد، إلخ)"""
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")

    event = verify_webhook(payload, sig_header)
    if not event:
        return jsonify({"error": "Invalid signature"}), 400

    event_type = event.get("type") if isinstance(event, dict) else event["type"]
    data_obj = event["data"]["object"] if isinstance(event, dict) else event.data.object

    handled = True
    try:
        if event_type == "checkout.session.completed":
            metadata = (data_obj.get("metadata", {}) or {}) if isinstance(data_obj, dict) else (data_obj.metadata or {})
            if metadata.get("product") == "api":
                handled = handle_api_checkout_completed(data_obj, db_run, db_row)
            else:
                handled = handle_checkout_completed(data_obj, db_run, db_row)
        elif event_type == "invoice.payment_succeeded":
            if not handle_api_invoice_paid(data_obj, db_run, db_row):
                handled = handle_invoice_paid(data_obj, db_run, db_row)
        elif event_type in ("customer.subscription.updated", "customer.subscription.trial_will_end"):
            if not handle_api_subscription_updated(data_obj, db_run, db_row):
                handled = handle_subscription_updated(data_obj, db_run)
        elif event_type == "customer.subscription.deleted":
            if not handle_api_subscription_canceled(data_obj, db_run, db_row):
                handled = handle_subscription_canceled(data_obj, db_run)
    except Exception as e:
        print(f"Webhook handler error: {e}")
        import traceback; traceback.print_exc()
        handled = False

    if not handled:
        # رد غير 2xx يخلي Stripe يعيد محاولة إرسال الحدث تاني بدل ما يضيع بصمت
        return jsonify({"status": "error"}), 500

    return jsonify({"status": "ok"}), 200


@bp.route("/subscription/cancel", methods=["POST"])
@login_required
def cancel_subscription():
    """إلغاء الاشتراك (سيستمر حتى نهاية الفترة المدفوعة)"""
    success, msg = cancel_user_subscription(session["uid"], db_row, db_run)
    if success:
        return redirect("/my-plan?msg=" + msg)
    return redirect("/my-plan?error=" + msg)


# ═══════════════════════════════════════════════
# ADMIN PAYMENTS DASHBOARD
# ═══════════════════════════════════════════════

@bp.route("/admin/payments")
@admin_required
def admin_payments_view():
    """لوحة admin لمتابعة كل المدفوعات والاشتراكات"""
    user = get_user_by_id(session["uid"])
    payments = []
    subscriptions = []
    try:
        payments = db_rows("""
            SELECT p.*, u.name as user_name, u.email as user_email 
            FROM payments p 
            LEFT JOIN users u ON p.user_id = u.id 
            ORDER BY p.created_at DESC LIMIT 200
        """)
    except: pass

    try:
        subscriptions = db_rows("""
            SELECT s.*, u.name as user_name, u.email as user_email 
            FROM subscriptions s 
            LEFT JOIN users u ON s.user_id = u.id 
            ORDER BY s.created_at DESC LIMIT 200
        """)
    except: pass

    stats = {
        "total_revenue": 0,
        "total_revenue_currency": None,
        "active_subscriptions": 0,
        "trialing_count": 0,
        "successful_payments": 0,
        "total_attempts": len(payments) if payments else 0,
        "paying_customers": 0,
        "total_users": 0,
    }

    try:
        currencies_seen = set()
        for p in payments:
            if p.get("status") == "completed":
                stats["total_revenue"] += (p.get("amount") or 0)
                stats["successful_payments"] += 1
                if p.get("currency"):
                    currencies_seen.add(p["currency"])

        if len(currencies_seen) == 1:
            stats["total_revenue_currency"] = list(currencies_seen)[0]
        elif len(currencies_seen) > 1:
            stats["total_revenue_currency"] = "مختلط"

        from datetime import datetime as dt
        now = dt.now()
        unique_paying_users = set()

        for s in subscriptions:
            status = s.get("status", "")
            if status in ("active", "trialing"):
                stats["active_subscriptions"] += 1
                unique_paying_users.add(s.get("user_id"))
                if status == "trialing":
                    stats["trialing_count"] += 1

        for p in payments:
            if p.get("status") == "completed":
                unique_paying_users.add(p.get("user_id"))

        stats["paying_customers"] = len(unique_paying_users)

        r = db_row("SELECT COUNT(*) as cnt FROM users WHERE role='client' OR role IS NULL")
        stats["total_users"] = r.get("cnt", 0) if r else 0
    except Exception as e:
        print(f"Stats compute error: {e}")

    analytics = build_admin_analytics(db_rows)

    return render_template("admin_payments.html",
                           user=user, lang=session.get("lang", "ar"),
                           payments=payments, subscriptions=subscriptions,
                           stats=stats, analytics=analytics)


@bp.route("/check-access")
@login_required
def check_access_endpoint():
    """API endpoint للتحقق من حالة الاشتراك"""
    info = get_user_access_info(session["uid"], db_row, cur_lang())
    if info.get("expires_at") and hasattr(info["expires_at"], "isoformat"):
        info["expires_at"] = info["expires_at"].isoformat()
    return jsonify(info)



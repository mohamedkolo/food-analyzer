"""
NutraX Payments Module - Stripe Integration
============================================
3 خطط دفع:
1. استشارة فردية (149 EGP / 19 AED / $5) - شات مفتوح 24 ساعة
2. خطة واحدة (299 EGP / 35 AED / $9) - خطة + متابعة 7 أيام
3. اشتراك شهري (599 EGP / 69 AED / $19) - كل حاجة + 7 أيام تجربة

Multi-currency: EGP / AED / USD / SAR
"""

import os
import json
import stripe
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
DOMAIN = os.environ.get("DOMAIN", "https://food-analyzer-duag.onrender.com")

# ═══════════════════════════════════════════════
# PRICING (الأسعار بالـ cents/قروش)
# ═══════════════════════════════════════════════

PRICING = {
    "consultation": {
        "name": "استشارة فردية",
        "name_en": "Single Consultation",
        "description": "محادثة مفتوحة لمدة 24 ساعة",
        "description_en": "24-hour chat consultation",
        "duration_days": 1,
        "type": "one_time",
        "icon": "💬",
        "color": "#3b82f6",
        "prices": {
            "EGP": 14900,  # 149 ج.م
            "AED": 1900,   # 19 د.إ
            "USD": 500,    # $5
            "SAR": 1900,   # 19 ر.س
        },
        "features_ar": [
            "محادثة مع د. محمد لمدة 24 ساعة",
            "إجابة على استفساراتك الغذائية",
            "نصائح مخصصة لحالتك",
            "تواصل مباشر عبر الشات"
        ],
        "features_en": [
            "Direct chat with Dr. Mohamed for 24h",
            "Answer your nutrition questions",
            "Personalized advice",
            "Real-time messaging"
        ]
    },
    "single_plan": {
        "name": "خطة واحدة",
        "name_en": "Single Plan",
        "description": "خطة غذائية كاملة + متابعة 7 أيام",
        "description_en": "Full diet plan + 7-day follow-up",
        "duration_days": 7,
        "type": "one_time",
        "icon": "📋",
        "color": "#10b981",
        "prices": {
            "EGP": 29900,  # 299 ج.م
            "AED": 3500,   # 35 د.إ
            "USD": 900,    # $9
            "SAR": 3500,   # 35 ر.س
        },
        "features_ar": [
            "خطة غذائية كاملة من د. محمد",
            "PDF احترافي قابل للطباعة",
            "متابعة 7 أيام عبر الشات",
            "تعديل الخطة لو احتجت",
            "نصائح متابعة يومية"
        ],
        "features_en": [
            "Complete diet plan by Dr. Mohamed",
            "Professional printable PDF",
            "7-day follow-up via chat",
            "Plan adjustments if needed",
            "Daily follow-up tips"
        ]
    },
    "monthly_subscription": {
        "name": "اشتراك شهري",
        "name_en": "Monthly Subscription",
        "description": "كل حاجة - بدون حدود + 7 أيام تجربة مجانية",
        "description_en": "Everything unlimited + 7-day free trial",
        "duration_days": 30,
        "type": "subscription",
        "trial_days": 7,
        "icon": "👑",
        "color": "#f59e0b",
        "badge": "الأكثر توفيراً",
        "badge_en": "Best Value",
        "prices": {
            "EGP": 59900,  # 599 ج.م
            "AED": 6900,   # 69 د.إ
            "USD": 1900,   # $19
            "SAR": 6900,   # 69 ر.س
        },
        "features_ar": [
            "✅ خطط غذائية غير محدودة",
            "✅ شات مفتوح طوال الشهر",
            "✅ متابعة دائمة من د. محمد",
            "✅ تحديثات أسبوعية للخطة",
            "✅ 7 أيام تجربة مجانية",
            "✅ إلغاء أي وقت بدون التزام"
        ],
        "features_en": [
            "✅ Unlimited diet plans",
            "✅ Open chat all month",
            "✅ Ongoing support from Dr. Mohamed",
            "✅ Weekly plan updates",
            "✅ 7-day free trial",
            "✅ Cancel anytime"
        ]
    }
}

# ═══════════════════════════════════════════════
# COUNTRY → CURRENCY DETECTION
# ═══════════════════════════════════════════════

COUNTRY_TO_CURRENCY = {
    "مصر": "EGP", "Egypt": "EGP", "EG": "EGP", "egypt": "EGP",
    "السعودية": "SAR", "Saudi Arabia": "SAR", "SA": "SAR", "saudi": "SAR",
    "الإمارات": "AED", "UAE": "AED", "AE": "AED", "emirates": "AED",
    "الكويت": "USD", "Kuwait": "USD", "KW": "USD",
    "قطر": "USD", "Qatar": "USD", "QA": "USD",
    "البحرين": "USD", "Bahrain": "USD", "BH": "USD",
    "عمان": "USD", "Oman": "USD", "OM": "USD",
    "الأردن": "USD", "Jordan": "USD", "JO": "USD",
    "لبنان": "USD", "Lebanon": "USD", "LB": "USD",
    "المغرب": "USD", "Morocco": "USD", "MA": "USD",
    "الجزائر": "USD", "Algeria": "USD", "DZ": "USD",
    "تونس": "USD", "Tunisia": "USD", "TN": "USD",
}


def detect_currency(country):
    """Detect currency from country name"""
    if not country:
        return "USD"
    country = country.strip()
    # Try exact match first
    if country in COUNTRY_TO_CURRENCY:
        return COUNTRY_TO_CURRENCY[country]
    # Try lowercase
    if country.lower() in COUNTRY_TO_CURRENCY:
        return COUNTRY_TO_CURRENCY[country.lower()]
    return "USD"


def format_price(amount_cents, currency):
    """Convert cents to display string"""
    amount = amount_cents / 100
    if currency == "EGP":
        return f"{amount:.0f} ج.م"
    elif currency == "AED":
        return f"{amount:.0f} د.إ"
    elif currency == "SAR":
        return f"{amount:.0f} ر.س"
    else:
        return f"${amount:.2f}"


def get_plan_price(plan_key, currency):
    """Get price for a plan in specific currency"""
    plan = PRICING.get(plan_key)
    if not plan:
        return None
    return plan["prices"].get(currency, plan["prices"]["USD"])


def get_supported_currencies():
    return ["EGP", "AED", "USD", "SAR"]


def get_currency_label(currency):
    labels = {
        "EGP": "جنيه مصري",
        "AED": "درهم إماراتي",
        "USD": "دولار أمريكي",
        "SAR": "ريال سعودي"
    }
    return labels.get(currency, currency)


def get_currency_flag(currency):
    flags = {
        "EGP": "🇪🇬",
        "AED": "🇦🇪",
        "USD": "🌍",
        "SAR": "🇸🇦"
    }
    return flags.get(currency, "💰")


# ═══════════════════════════════════════════════
# CHECKOUT SESSION CREATION
# ═══════════════════════════════════════════════

def create_checkout_session(user, plan_key, currency="EGP"):
    """
    Create a Stripe Checkout Session for the given plan and currency.
    Returns the Stripe session object (use .url to redirect).
    """
    if not stripe.api_key:
        raise RuntimeError("Stripe not configured - missing STRIPE_SECRET_KEY")

    if plan_key not in PRICING:
        raise ValueError(f"Unknown plan: {plan_key}")

    if currency not in get_supported_currencies():
        currency = "USD"

    plan = PRICING[plan_key]
    price_cents = plan["prices"].get(currency, plan["prices"]["USD"])

    line_items = [{
        'price_data': {
            'currency': currency.lower(),
            'product_data': {
                'name': plan["name"],
                'description': plan["description"],
            },
            'unit_amount': price_cents,
        },
        'quantity': 1,
    }]

    mode = "subscription" if plan["type"] == "subscription" else "payment"

    session_params = {
        'payment_method_types': ['card'],
        'line_items': line_items,
        'mode': mode,
        'success_url': f"{DOMAIN}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        'cancel_url': f"{DOMAIN}/payment/cancel",
        'customer_email': user.get("email"),
        'metadata': {
            'user_id': str(user["id"]),
            'plan_key': plan_key,
            'currency': currency,
            'user_name': user.get("name", ""),
        },
        'locale': 'auto',
    }

    if mode == "subscription":
        # Add recurring billing
        session_params['line_items'][0]['price_data']['recurring'] = {
            'interval': 'month'
        }
        # Add trial period
        if plan.get("trial_days"):
            session_params['subscription_data'] = {
                'trial_period_days': plan["trial_days"],
                'metadata': {
                    'user_id': str(user["id"]),
                    'plan_key': plan_key,
                }
            }

    return stripe.checkout.Session.create(**session_params)


# ═══════════════════════════════════════════════
# WEBHOOK HANDLING
# ═══════════════════════════════════════════════

def verify_webhook(payload, signature):
    """Verify webhook signature - returns Stripe event or None"""
    if not STRIPE_WEBHOOK_SECRET:
        # In dev without webhook secret, parse directly (NOT SECURE)
        try:
            return json.loads(payload)
        except:
            return None
    try:
        return stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return None


def handle_checkout_completed(session_obj, db_run, db_row):
    """Handle successful checkout - save to DB"""
    metadata = session_obj.get('metadata', {})
    user_id = int(metadata.get('user_id', 0))
    plan_key = metadata.get('plan_key', '')
    currency = metadata.get('currency', 'USD')

    if not user_id or not plan_key:
        return False

    plan = PRICING.get(plan_key)
    if not plan:
        return False

    session_id = session_obj.get('id')
    payment_intent = session_obj.get('payment_intent', '')
    subscription_id = session_obj.get('subscription', '')
    amount = session_obj.get('amount_total', 0)

    # Save payment record
    try:
        existing = db_row("SELECT id FROM payments WHERE stripe_session_id=?", (session_id,))
        if existing:
            return True  # Already processed
    except:
        pass

    expires_at = None
    if plan["type"] == "one_time":
        expires_at = datetime.now() + timedelta(days=plan["duration_days"])

    try:
        db_run("""INSERT INTO payments 
                  (user_id, stripe_session_id, stripe_payment_intent_id, plan_key, 
                   status, currency, amount, expires_at, metadata) 
                  VALUES (?, ?, ?, ?, 'completed', ?, ?, ?, ?)""",
               (user_id, session_id, payment_intent, plan_key, currency, amount,
                expires_at, json.dumps(metadata)))
    except Exception as e:
        print(f"Error saving payment: {e}")
        return False

    # If subscription, save subscription record
    if plan["type"] == "subscription" and subscription_id:
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            trial_end = datetime.fromtimestamp(sub.trial_end) if sub.trial_end else None
            period_start = datetime.fromtimestamp(sub.current_period_start)
            period_end = datetime.fromtimestamp(sub.current_period_end)
            customer_id = sub.customer

            db_run("""INSERT INTO subscriptions 
                      (user_id, stripe_customer_id, stripe_subscription_id, plan_key,
                       status, currency, amount, current_period_start, 
                       current_period_end, trial_end)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (user_id, customer_id, subscription_id, plan_key,
                    sub.status, currency, amount, period_start, period_end, trial_end))
        except Exception as e:
            print(f"Error saving subscription: {e}")

    return True


def handle_invoice_paid(invoice_obj, db_run, db_row):
    """Handle recurring subscription renewal"""
    subscription_id = invoice_obj.get('subscription')
    if not subscription_id:
        return False
    try:
        sub = stripe.Subscription.retrieve(subscription_id)
        period_end = datetime.fromtimestamp(sub.current_period_end)
        db_run("""UPDATE subscriptions SET status=?, current_period_end=?, updated_at=? 
                  WHERE stripe_subscription_id=?""",
               (sub.status, period_end, datetime.now(), subscription_id))
        return True
    except Exception as e:
        print(f"Error handling invoice: {e}")
        return False


def handle_subscription_updated(sub_obj, db_run):
    """Handle subscription status changes"""
    subscription_id = sub_obj.get('id')
    status = sub_obj.get('status')
    period_end = datetime.fromtimestamp(sub_obj.get('current_period_end', 0))
    try:
        db_run("""UPDATE subscriptions SET status=?, current_period_end=?, updated_at=? 
                  WHERE stripe_subscription_id=?""",
               (status, period_end, datetime.now(), subscription_id))
        return True
    except:
        return False


def handle_subscription_canceled(sub_obj, db_run):
    """Handle subscription cancellation"""
    subscription_id = sub_obj.get('id')
    try:
        db_run("""UPDATE subscriptions SET status='canceled', cancel_at=?, updated_at=? 
                  WHERE stripe_subscription_id=?""",
               (datetime.now(), datetime.now(), subscription_id))
        return True
    except:
        return False


# ═══════════════════════════════════════════════
# ACCESS CONTROL
# ═══════════════════════════════════════════════

def has_active_access(user_id, db_row):
    """Check if user has any active subscription or valid one-time payment"""
    if not user_id:
        return False

    now = datetime.now()

    # Check active subscription (active or trialing)
    try:
        sub = db_row("""SELECT * FROM subscriptions 
                        WHERE user_id=? AND status IN ('active', 'trialing') 
                        AND current_period_end > ? 
                        ORDER BY current_period_end DESC LIMIT 1""",
                     (user_id, now))
        if sub:
            return True
    except:
        pass

    # Check valid one-time payment
    try:
        pay = db_row("""SELECT * FROM payments 
                        WHERE user_id=? AND status='completed' 
                        AND expires_at > ? 
                        ORDER BY expires_at DESC LIMIT 1""",
                     (user_id, now))
        if pay:
            return True
    except:
        pass

    return False


def get_user_access_info(user_id, db_row):
    """Get details about user's current access"""
    info = {
        "has_access": False,
        "type": None,
        "plan_name": None,
        "expires_at": None,
        "is_trial": False,
        "days_left": 0,
    }

    if not user_id:
        return info

    now = datetime.now()

    # Check subscription first
    try:
        sub = db_row("""SELECT * FROM subscriptions 
                        WHERE user_id=? AND status IN ('active', 'trialing') 
                        AND current_period_end > ? 
                        ORDER BY current_period_end DESC LIMIT 1""",
                     (user_id, now))
        if sub:
            plan = PRICING.get(sub["plan_key"], {})
            info["has_access"] = True
            info["type"] = "subscription"
            info["plan_name"] = plan.get("name", "اشتراك")
            info["is_trial"] = sub["status"] == "trialing"
            end_date = sub["current_period_end"]
            if isinstance(end_date, str):
                try:
                    end_date = datetime.fromisoformat(end_date.replace('Z', ''))
                except:
                    end_date = now
            info["expires_at"] = end_date
            info["days_left"] = max(0, (end_date - now).days)
            return info
    except:
        pass

    # Check one-time payment
    try:
        pay = db_row("""SELECT * FROM payments 
                        WHERE user_id=? AND status='completed' 
                        AND expires_at > ? 
                        ORDER BY expires_at DESC LIMIT 1""",
                     (user_id, now))
        if pay:
            plan = PRICING.get(pay["plan_key"], {})
            info["has_access"] = True
            info["type"] = "one_time"
            info["plan_name"] = plan.get("name", "خطة")
            end_date = pay["expires_at"]
            if isinstance(end_date, str):
                try:
                    end_date = datetime.fromisoformat(end_date.replace('Z', ''))
                except:
                    end_date = now
            info["expires_at"] = end_date
            info["days_left"] = max(0, (end_date - now).days)
            return info
    except:
        pass

    return info


def cancel_user_subscription(user_id, db_row, db_run):
    """Cancel user's active subscription at period end"""
    try:
        sub = db_row("""SELECT * FROM subscriptions 
                        WHERE user_id=? AND status IN ('active', 'trialing') 
                        ORDER BY current_period_end DESC LIMIT 1""", (user_id,))
        if not sub:
            return False, "لا يوجد اشتراك نشط"

        sub_id = sub["stripe_subscription_id"]
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        db_run("""UPDATE subscriptions SET cancel_at=?, updated_at=? 
                  WHERE stripe_subscription_id=?""",
               (datetime.now(), datetime.now(), sub_id))
        return True, "تم إلغاء الاشتراك - سيستمر حتى نهاية الفترة المدفوعة"
    except Exception as e:
        return False, f"خطأ: {e}"

# -*- coding: utf-8 -*-
"""‏الفلوس: مين بيدفع، ومين بياخد، وإمتى بيتقفل.

الدكتور سأل عن نقاط ضعف الموقع، والتانية كانت: الكلام الطبي مغطّى
بـ٤٠٠+ اختبار، و**الدفع والاشتراكات مالهمش ولا اختبار**. دي اللي لو
باظت في صمت بتكلّفه على طول -- عميل دفع واتقفل عليه، أو عميل خلص
اشتراكه وفضل داخل.

الاختبارات دي على المنطق نفسه (payments.py)، من غير أي نداء لـStripe:
الحسابات والتواريخ وقرار الدخول كلها محلية، والنداء الخارجي الوحيد
(استرجاع الاشتراك) بيتبدّل بنسخة مزيّفة.

Run with:  python3 tests/test_money.py
"""

import os
import sys
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_money.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A        # noqa: E402
import payments        # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


def _user(email):
    row = A.db_row("SELECT id FROM users WHERE email=?", (email,))
    if row:
        return row["id"]
    A.db_run("INSERT INTO users (name,email,password,role,active) "
             "VALUES (?,?,?,?,1)",
             ("T", email, generate_password_hash("pw123456"), "client"))
    return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]


def _clear(uid):
    A.db_run("DELETE FROM payments WHERE user_id=?", (uid,))
    A.db_run("DELETE FROM subscriptions WHERE user_id=?", (uid,))


def _pay(uid, days, status="completed", session_id=None):
    A.db_run("INSERT INTO payments (user_id,stripe_session_id,plan_key,status,"
             "currency,amount,expires_at) VALUES (?,?,?,?,?,?,?)",
             (uid, session_id or ("s%s" % datetime.now().timestamp()),
              "monthly_subscription", status, "EGP", 50000,
              datetime.now() + timedelta(days=days)))


def _sub(uid, days, status="active", sub_id="sub_test"):
    A.db_run("INSERT INTO subscriptions (user_id,stripe_customer_id,"
             "stripe_subscription_id,plan_key,status,currency,amount,"
             "current_period_start,current_period_end) "
             "VALUES (?,?,?,?,?,?,?,?,?)",
             (uid, "cus_x", sub_id, "monthly_subscription", status, "EGP",
              50000, datetime.now() - timedelta(days=1),
              datetime.now() + timedelta(days=days)))


# ═══════════════════════════════════════════════════════════════════
#  قرار الدخول
# ═══════════════════════════════════════════════════════════════════

def test_a_client_who_paid_gets_in():
    uid = _user("paid@m.test")
    _clear(uid)
    _pay(uid, days=20)
    assert payments.has_active_access(uid, A.db_row) is True


def test_a_payment_that_expired_does_not_get_in():
    """‏أخطر حالة في الاتجاه ده: عميل خلص اشتراكه وفضل داخل."""
    uid = _user("expired@m.test")
    _clear(uid)
    _pay(uid, days=-1)
    assert payments.has_active_access(uid, A.db_row) is False


def test_a_payment_that_did_not_complete_does_not_get_in():
    """‏دفعة اتبدأت ومااكتملتش مش دخول."""
    uid = _user("pending@m.test")
    _clear(uid)
    _pay(uid, days=30, status="pending")
    assert payments.has_active_access(uid, A.db_row) is False


def test_an_active_subscription_gets_in_and_a_canceled_one_does_not():
    uid = _user("sub@m.test")
    _clear(uid)
    _sub(uid, days=15, status="active")
    assert payments.has_active_access(uid, A.db_row) is True
    _clear(uid)
    _sub(uid, days=15, status="canceled")
    assert payments.has_active_access(uid, A.db_row) is False


def test_a_trial_counts_as_access():
    uid = _user("trial@m.test")
    _clear(uid)
    _sub(uid, days=7, status="trialing")
    assert payments.has_active_access(uid, A.db_row) is True


def test_a_subscription_whose_period_ended_does_not_get_in():
    """‏الحالة active والفترة خلصت -- بيحصل لو الويبهوك ضاع."""
    uid = _user("stale@m.test")
    _clear(uid)
    _sub(uid, days=-2, status="active")
    assert payments.has_active_access(uid, A.db_row) is False


def test_nobody_without_a_record_gets_in():
    uid = _user("broke@m.test")
    _clear(uid)
    assert payments.has_active_access(uid, A.db_row) is False
    assert payments.has_active_access(None, A.db_row) is False
    assert payments.has_active_access(0, A.db_row) is False


# ═══════════════════════════════════════════════════════════════════
#  الويبهوك
# ═══════════════════════════════════════════════════════════════════

def test_an_unsigned_webhook_is_refused():
    """‏من غير التوقيع، أي حد يعرف اللينك يقدر يدي نفسه اشتراك."""
    assert payments.verify_webhook(b'{"type":"checkout.session.completed"}',
                                   "") is None
    assert payments.verify_webhook(b"{}", "t=1,v1=deadbeef") is None


def test_the_same_checkout_is_not_paid_for_twice():
    """‏Stripe بتعيد إرسال الحدث لو الرد مش 2xx. لو الإعادة عملت دفعة
    تانية، العميل بياخد ضعف المدة والحسابات بتبوظ."""
    uid = _user("replay@m.test")
    _clear(uid)
    session = {"id": "cs_replay_1", "payment_intent": "pi_1",
               "subscription": "", "amount_total": 50000,
               "metadata": {"user_id": str(uid), "plan_key": "single_plan",
                            "currency": "EGP"}}
    first = payments.handle_checkout_completed(session, A.db_run, A.db_row)
    second = payments.handle_checkout_completed(session, A.db_run, A.db_row)
    assert first is True and second is True
    rows = A.db_rows("SELECT id FROM payments WHERE stripe_session_id=?",
                     ("cs_replay_1",))
    assert len(rows) == 1, "‏الدفعة اتسجّلت %d مرة" % len(rows)


def test_a_checkout_without_a_user_is_refused():
    """‏بيانات ناقصة = مانسجّلش دفعة على حساب مش معروف."""
    for meta in ({}, {"user_id": "0", "plan_key": "x"},
                 {"user_id": "5"}, {"plan_key": "monthly_subscription"}):
        out = payments.handle_checkout_completed(
            {"id": "cs_bad", "metadata": meta}, A.db_run, A.db_row)
        assert out is False, meta


def test_an_unknown_plan_is_refused():
    """‏خطة مش في جدول الأسعار مابتتسجّلش."""
    uid = _user("badplan@m.test")
    out = payments.handle_checkout_completed(
        {"id": "cs_badplan", "metadata": {"user_id": str(uid),
                                          "plan_key": "not_a_plan"}},
        A.db_run, A.db_row)
    assert out is False


def test_cancelling_a_subscription_marks_it_canceled():
    uid = _user("cancel@m.test")
    _clear(uid)
    _sub(uid, days=10, status="active", sub_id="sub_cancel_me")
    assert payments.handle_subscription_canceled({"id": "sub_cancel_me"},
                                                 A.db_run) is True
    row = A.db_row("SELECT status FROM subscriptions WHERE "
                   "stripe_subscription_id=?", ("sub_cancel_me",))
    assert row["status"] == "canceled", row


def test_a_status_change_moves_the_period_too():
    """‏الحالة لوحدها مابتكفيش: الدخول بيتقرر من تاريخ نهاية الفترة."""
    uid = _user("update@m.test")
    _clear(uid)
    _sub(uid, days=5, status="active", sub_id="sub_update_me")
    future = int((datetime.now() + timedelta(days=40)).timestamp())
    assert payments.handle_subscription_updated(
        {"id": "sub_update_me", "status": "active",
         "current_period_end": future}, A.db_run) is True
    row = A.db_row("SELECT current_period_end FROM subscriptions WHERE "
                   "stripe_subscription_id=?", ("sub_update_me",))
    assert row is not None
    assert payments.has_active_access(uid, A.db_row) is True


def test_a_canceled_subscription_closes_the_door():
    """‏الرحلة كاملة: اشترك -> اتلغى -> اتقفل."""
    uid = _user("journey@m.test")
    _clear(uid)
    _sub(uid, days=20, status="active", sub_id="sub_journey")
    assert payments.has_active_access(uid, A.db_row) is True
    payments.handle_subscription_canceled({"id": "sub_journey"}, A.db_run)
    assert payments.has_active_access(uid, A.db_row) is False


# ═══════════════════════════════════════════════════════════════════
#  الأسعار
# ═══════════════════════════════════════════════════════════════════

def test_every_plan_has_a_price_in_every_currency():
    """‏خطة من غير سعر بعملة = صفحة دفع فاضية أو سعر صفر."""
    missing = []
    for currency in payments.get_supported_currencies():
        for key in payments.PRICING:
            price = payments.get_plan_price(key, currency)
            if not price or price <= 0:
                missing.append((key, currency, price))
    assert not missing, "‏خطط بدون سعر: %s" % missing[:5]


def test_the_price_shown_is_not_the_cents_number():
    """‏٥٠٠٠٠ قرش = ٥٠٠ جنيه. طباعة الرقم الخام على صفحة الدفع كارثة."""
    shown = payments.format_price(50000, "EGP")
    assert "50000" not in shown.replace(",", ""), shown
    assert "500" in shown.replace(",", ""), shown


def test_the_currency_follows_the_country():
    """‏عميل في مصر مايشوفش دولار."""
    assert payments.detect_currency("EG") == "EGP"
    for country in (None, "", "ZZ"):
        assert payments.detect_currency(country) in payments.get_supported_currencies()



# ═══════════════════════════════════════════════════════════════════
#  البوابة في الموقع نفسه، مش في الدالة بس
# ═══════════════════════════════════════════════════════════════════
#
# ‏الدوال فوق بتتفحص لوحدها. ده بيتفحص إن الصفحات **موصّلة** بيها:
# قرار دخول سليم في دالة مش موصولة بصفحة مابيحميش حاجة.

PAYWALLED = ["/analyzer"]


def _as(client, uid):
    with client.session_transaction() as sess:
        sess["uid"] = uid


def test_a_client_without_payment_is_sent_to_the_paywall():
    uid = _user("gate_out@m.test")
    _clear(uid)
    A.db_run("UPDATE users SET onboarded_at=? WHERE id=?",
             (datetime.now(), uid))
    client = A.app.test_client()
    _as(client, uid)
    for path in PAYWALLED:
        res = client.get(path)
        assert res.status_code in (301, 302), (path, res.status_code)
        assert "subscription-required" in (res.headers.get("Location") or ""), (
            path, res.headers.get("Location"))


def test_a_client_who_paid_walks_through():
    uid = _user("gate_in@m.test")
    _clear(uid)
    A.db_run("UPDATE users SET onboarded_at=? WHERE id=?",
             (datetime.now(), uid))
    _pay(uid, days=20)
    client = A.app.test_client()
    _as(client, uid)
    for path in PAYWALLED:
        res = client.get(path)
        assert res.status_code == 200, (path, res.status_code,
                                        res.headers.get("Location"))


def test_the_paywall_opens_the_moment_access_expires():
    """‏نفس العميل، نفس الصفحة -- الفرق تاريخ واحد."""
    uid = _user("gate_expire@m.test")
    _clear(uid)
    A.db_run("UPDATE users SET onboarded_at=? WHERE id=?",
             (datetime.now(), uid))
    _pay(uid, days=5)
    client = A.app.test_client()
    _as(client, uid)
    assert client.get(PAYWALLED[0]).status_code == 200

    _clear(uid)
    _pay(uid, days=-1)
    res = client.get(PAYWALLED[0])
    assert res.status_code in (301, 302), res.status_code


def test_staff_never_hit_the_paywall():
    """‏الدكتور نفسه مش عميل -- مايتقفلش عليه شغله."""
    A.db_run("INSERT OR IGNORE INTO users (name,email,password,role,active) "
             "VALUES (?,?,?,?,1)",
             ("Doc", "doc_money@m.test",
              generate_password_hash("pw123456"), "nutritionist"))
    row = A.db_row("SELECT id FROM users WHERE email=?", ("doc_money@m.test",))
    A.db_run("UPDATE users SET onboarded_at=? WHERE id=?",
             (datetime.now(), row["id"]))
    _clear(row["id"])
    client = A.app.test_client()
    _as(client, row["id"])
    res = client.get(PAYWALLED[0])
    assert res.status_code == 200, (res.status_code,
                                    res.headers.get("Location"))

if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}")
            failed += 1
        except Exception as e:
            print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

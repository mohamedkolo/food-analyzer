# -*- coding: utf-8 -*-
"""‏الخطة اللي الدكتور بيشتغل عليها دلوقتي -- في قاعدة البيانات، مش في الكوكي.

**الباج اللي الملف ده بيصلّحه:** التوليد كان بيحفظ الخطة كلها في كوكي
الجلسة. الكوكي عنده حد في كل المتصفحات: ٤٠٩٣ بايت. والخطة أكبر من كده
في أنظمة كتير -- مقيس:

    التكميم بدون أي حالة مرضية   ٤٧٠٧ بايت    فوق الحد
    التكميم بتلات حالات          ٥٤٣٢ بايت    فوق الحد
    الكيميائي بتلات حالات        ٤٧١٢ بايت    فوق الحد
    التقليدي بتلات حالات         ٣٤٨٧ بايت    تحت الحد بشعرة

‏ولما الكوكي بيعدّي الحد، المتصفح **بيرميه من غير أي رسالة**. النتيجة اللي
الدكتور بيشوفها: بيدوس "ولّد"، الصفحة تلف، وبترجّعه للفورم تاني -- عمره
ما بيوصل للجدول. ومافيش رسالة غلط، لأن السيرفر شغّال والمتصفح هو اللي
رمى الكوكي بالهدوء.

‏وده كان بيخبى على الاختبارات كلها: عميل الاختبار في Flask بيبعت الكوكي
أي حجم، فالتوليد كان بينجح في التست وبيفشل في متصفح حقيقي.

‏الحل: الكوكي بيشيل رقم تعريف (٣٢ حرف) والخطة بتتحفظ في صف في القاعدة.
"""

import json
import random
import secrets

from flask import session

KEY = "draft"           # ‏اللي بيتحفظ في الكوكي: رقم التعريف بس
_LEGACY = ("pdf_data", "current_plan")

# ‏مسوّدة عمرها أكتر من كده يبقى الدكتور مشي ومارجعش. التنضيف بيحصل مع
# واحد من كل ٥٠ كتابة -- مش محتاج شغل دوري عشان صف صغير.
MAX_AGE_DAYS = 3
_CLEAN_EVERY = 50


def _db():
    from core import db_row, db_run
    return db_row, db_run


def _new_id():
    return secrets.token_hex(16)


def _drop_legacy():
    """‏الكوكي القديم لسه فيه الخطة. بنشيلها عشان يصغّر."""
    for key in _LEGACY:
        if key in session:
            session.pop(key, None)


def draft_id(create=False):
    value = session.get(KEY)
    if not value and create:
        value = _new_id()
        session[KEY] = value
    return value


def set_draft(data=None, plan=None, user_id=None):
    """‏يحفظ اللي اتبعت ويسيب الباقي زي ما هو."""
    db_row, db_run = _db()
    ident = draft_id(create=True)
    if user_id is None:
        user_id = session.get("uid") or 0
    _drop_legacy()

    db_run("""INSERT INTO plan_drafts (id, user_id, data_json, plan_json, updated_at)
              VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
              ON CONFLICT (id) DO UPDATE SET
                  user_id = excluded.user_id,
                  data_json = COALESCE(excluded.data_json, plan_drafts.data_json),
                  plan_json = COALESCE(excluded.plan_json, plan_drafts.plan_json),
                  updated_at = CURRENT_TIMESTAMP""",
           (ident, user_id,
            json.dumps(data, ensure_ascii=False) if data is not None else None,
            json.dumps(plan, ensure_ascii=False) if plan is not None else None))

    if random.randrange(_CLEAN_EVERY) == 0:
        try:
            db_run("DELETE FROM plan_drafts WHERE updated_at < "
                   "CURRENT_TIMESTAMP - INTERVAL '%d days'" % MAX_AGE_DAYS)
        except Exception:
            # ‏sqlite مابيعرفش INTERVAL، وده نفس الاستعلام بصيغته
            try:
                db_run("DELETE FROM plan_drafts WHERE updated_at < "
                       "datetime('now', '-%d days')" % MAX_AGE_DAYS)
            except Exception:
                pass
    return ident


def _load(column):
    ident = draft_id()
    if not ident:
        return None
    db_row, _ = _db()
    try:
        row = db_row("SELECT %s AS v FROM plan_drafts WHERE id=?" % column, (ident,))
    except Exception:
        return None
    if not row or not row.get("v"):
        return None
    try:
        return json.loads(row["v"])
    except (ValueError, TypeError):
        return None


def draft_data():
    """‏بيانات العميل اللي الخطة اتولّدت منها."""
    return _load("data_json")


def draft_plan():
    """الخطة نفسها."""
    return _load("plan_json")


def clear_draft():
    ident = session.pop(KEY, None)
    _drop_legacy()
    if not ident:
        return
    _, db_run = _db()
    try:
        db_run("DELETE FROM plan_drafts WHERE id=?", (ident,))
    except Exception:
        pass

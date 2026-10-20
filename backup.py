# -*- coding: utf-8 -*-
"""‏نسخة من كل اللي في قاعدة البيانات، من غير أي أدوات.

ليه الملف ده موجود
──────────────────
‏الموقع وقع يوم ٢٠ أكتوبر ٢٠٢٦: قاعدة Neon اتوقفت لأن حصتها الشهرية
خلصت، والموقع فضل يرد "مش قادر يوصل لقاعدة البيانات". البيانات ماراحتش
(التوقف مش حذف)، بس لحظة اللي أول سؤال اتسأل كان: "فيه نسخة احتياطية؟"
والإجابة كانت لأ.

‏والسبب إن مفيش نسخة مش إهمال: الأداة الموجودة (tools/backup_db.py)
محتاجة Terminal وPython ورابط القاعدة -- والدكتور بيشتغل من المتصفح.
**أداة محدش يقدر يشغّلها مش أداة.** فده نفس الشغل، بزرار.

الجداول بتتقرا من القاعدة نفسها
───────────────────────────────
‏الأداة القديمة فيها قايمة أسماء مكتوبة بالإيد، والقايمة دي **بقت
قديمة**: ناقصها plan_visits (كل الزيارات والأوزان -- أهم جدول في
العيادة) وplan_links. يعني نسخة كانت هتتاخد وهي ناقصة المتابعات كلها،
ومحدش هيعرف غير يوم ما يحتاجها.

‏فالقايمة هنا بتتقرا من القاعدة وقت التنفيذ. أي جدول يتضاف للمشروع
بعد كده بيدخل النسخة لوحده -- من غير ما حد يفتكر.
"""

import datetime as dt
import json
import os

# ‏جداول بتتشال بالقصد: محتوياتها مؤقتة أو بتتولّد لوحدها، ووجودها في
# النسخة بيكبّر الملف من غير فايدة.
#
#   plan_drafts           مسودّة الجدول اللي لسه بيتعمل -- بتتمسح بعد الحفظ
#   meal_reminders_sent   سجل "التذكير ده اتبعت" -- بيتبني من تاني
#   weekly_summary_sent   نفس الحاجة
SKIP = ("plan_drafts", "meal_reminders_sent", "weekly_summary_sent")


def tables(db_rows):
    """‏أسماء جداول القاعدة، مرتّبة.

    بتشتغل على Postgres (الاستضافة) وSQLite (المحلي) -- الاتنين
    بيخزّنوا قايمة الجداول في مكان مختلف.
    """
    for sql in (
        # Postgres
        "SELECT table_name AS n FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE'",
        # SQLite
        "SELECT name AS n FROM sqlite_master WHERE type='table'",
    ):
        try:
            rows = db_rows(sql) or []
        except Exception:
            continue
        names = sorted(str(dict(r).get("n") or "") for r in rows)
        names = [n for n in names
                 if n and not n.startswith("sqlite_") and n not in SKIP]
        if names:
            return names
    return []


def snapshot(db_rows):
    """‏النسخة كلها كـdict جاهز للتحويل لـJSON.

    بترجّع كمان عدد الصفوف لكل جدول وأي جدول فشل -- عشان اللي بياخد
    النسخة يشوف إنها كاملة فعلاً قبل ما يعتمد عليها. نسخة ناقصة وساكتة
    أسوأ من مافيش نسخة، لأنها بتدي إحساس أمان مش موجود.
    """
    data, counts, failed = {}, {}, {}
    found = tables(db_rows)
    for table in found:
        try:
            rows = db_rows('SELECT * FROM "%s"' % table) or []
            data[table] = [dict(r) for r in rows]
            counts[table] = len(data[table])
        except Exception as e:
            failed[table] = str(e)[:200]
    return {
        "taken_at": dt.datetime.now().isoformat(timespec="seconds"),
        "app_commit": _commit(),
        "tables": data,
        "counts": counts,
        "failed": failed,
        "skipped": list(SKIP),
    }


def _commit():
    try:
        from core import running_commit
        return running_commit()
    except Exception:
        return None


def as_json(snap):
    """‏JSON بعربي مقروء. default=str عشان التواريخ والأرقام العشرية."""
    return json.dumps(snap, ensure_ascii=False, indent=2, default=str)


def filename(snap=None, ext="json"):
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    if snap and snap.get("taken_at"):
        try:
            stamp = dt.datetime.fromisoformat(
                snap["taken_at"]).strftime("%Y-%m-%d_%H%M")
        except ValueError:
            pass
    return "nutrax-%s.%s" % (stamp, ext)


def summary(snap, is_ar=True):
    """‏سطر واحد يتعرض بعد التحميل: النسخة فيها إيه."""
    rows = sum(snap.get("counts", {}).values())
    tabs = len(snap.get("counts", {}))
    if is_ar:
        out = "%d صف من %d جدول" % (rows, tabs)
        if snap.get("failed"):
            out += " — وفشل %d جدول" % len(snap["failed"])
        return out
    out = "%d rows across %d tables" % (rows, tabs)
    if snap.get("failed"):
        out += " - %d tables failed" % len(snap["failed"])
    return out

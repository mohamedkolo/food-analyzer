# -*- coding: utf-8 -*-
"""‏تجهيز الرسائل للعرض: قايمة المحادثات، وسلسلة المحادثة الواحدة.

‏مفصول عن app.py عشان يتختبر من غير Flask ولا قاعدة.

‏القايمة كانت بتتبني باستعلامين لكل عميل (آخر رسالة + عدد غير المقروء)،
يعني ٢٠٠ عميل = ٤٠٠ طلب للقاعدة في كل فتحة للصفحة. هنا بتتبني من
رسائل المستخدم كلها في طلب واحد، والترتيب بآخر رسالة -- كانت أبجدية،
فاللي بعت دلوقتي ممكن يبقى في آخر القايمة.

‏والوقت متسجّل CURRENT_TIMESTAMP (جرينتش)؛ بيتحوّل لتوقيت المستخدم
بنفس طريقة صفحة الإشعارات.
"""

from datetime import datetime, timedelta, timezone

from notifications import _AR_MONTHS, _ago, _as_datetime, _clock


def _tz(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name or "Africa/Cairo")
    except Exception:
        return timezone(timedelta(hours=2))


def _local(value, tz):
    raw = _as_datetime(value)
    return raw.replace(tzinfo=timezone.utc).astimezone(tz) if raw else None


def _date_label(local, now, ar):
    days = (now.date() - local.date()).days
    if days <= 0:
        return "النهارده" if ar else "Today"
    if days == 1:
        return "امبارح" if ar else "Yesterday"
    if ar:
        return "%d %s" % (local.day, _AR_MONTHS[local.month - 1])
    return local.strftime("%-d %b")


def _now(now_utc, tz):
    return (now_utc or datetime.utcnow()).replace(tzinfo=timezone.utc).astimezone(tz)


def conversations(me_id, rows, clients, tz_name="Africa/Cairo", lang="ar", now_utc=None):
    """‏كل عميل ومعاه آخر رسالة وعدد اللي مااتقراش، مترتبين بآخر رسالة.

    ‏rows: رسائل المستخدم كلها (هو الراسل أو المستقبل). العملاء اللي مفيش
    بينك وبينهم رسائل بييجوا في الآخر بالاسم -- عشان تبدأ معاهم.
    """
    tz = _tz(tz_name)
    ar = lang != "en"
    now = _now(now_utc, tz)
    last, unread = {}, {}
    for m in rows or []:
        if m.get("sender_id") == me_id:
            other = m.get("receiver_id")
        elif m.get("receiver_id") == me_id:
            other = m.get("sender_id")
        else:
            continue
        at = _as_datetime(m.get("created_at")) or datetime.min
        if other not in last or at >= last[other][0]:
            last[other] = (at, m)
        if m.get("receiver_id") == me_id and not m.get("is_read"):
            unread[other] = unread.get(other, 0) + 1

    out = []
    for c in clients or []:
        entry = {"user": c, "last": None, "when": "", "mine_last": False,
                 "unread": unread.get(c["id"], 0), "_at": None}
        if c["id"] in last:
            at, m = last[c["id"]]
            local = _local(m.get("created_at"), tz)
            text = " ".join(str(m.get("message") or "").split())
            entry.update(last=text[:80], mine_last=m.get("sender_id") == me_id, _at=at)
            if local:
                days = (now.date() - local.date()).days
                entry["when"] = (_ago(max(0, int((now - local).total_seconds() // 60)), ar)
                                 if days <= 0 else _date_label(local, now, ar))
        out.append(entry)
    talked = sorted((e for e in out if e["_at"]), key=lambda e: e["_at"], reverse=True)
    quiet = sorted((e for e in out if not e["_at"]),
                   key=lambda e: (e["user"].get("name") or e["user"].get("email") or ""))
    return talked + quiet


def thread(rows, me_id, tz_name="Africa/Cairo", lang="ar", now_utc=None):
    """‏المحادثة بالترتيب، وقبل أول رسالة في كل يوم سطر باليوم.

    ‏كل رسالة: text، mine (أنا اللي بعتها)، read (الطرف التاني قراها --
    is_read متسجّل من الأول ومكانش بيظهر)، clock بتوقيت المستخدم.
    """
    tz = _tz(tz_name)
    ar = lang != "en"
    now = _now(now_utc, tz)
    out, day = [], None
    for m in rows or []:
        local = _local(m.get("created_at"), tz) or now
        label = _date_label(local, now, ar)
        if label != day:
            out.append({"day": label})
            day = label
        out.append({"id": m.get("id"), "text": m.get("message") or "",
                    "mine": m.get("sender_id") == me_id, "read": bool(m.get("is_read")),
                    "clock": _clock(local, ar), "iso": local.strftime("%Y-%m-%dT%H:%M")})
    return out

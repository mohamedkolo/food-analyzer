# -*- coding: utf-8 -*-
"""‏"أكلت حاجة برّه الخطة؟": أكل زيادة العميل بيسجّله من جدول الأكل.

‏العميل اللي أكل طعمية برّه الخطة ماكانش عنده مكان يقول، والدكتور مايعرفش
ليه الوزن واقف. الجدول (food_data.FOODS) فيه ٩٣٨ صنف بأرقامه لكل ١٠٠ جم،
والأرقام بتتحسب هنا في السيرفر من الجدول × الجرامات. السيرفر مابيصدّقش
أي رقم جاي من المتصفح.

‏مفيش هنا "مسموح" ولا "ممنوع": العميل بيقول أكل إيه، والدكتور هو اللي
بيقرّر. البحث بيعرض أرقام بس.
"""

import food_data
from meal_database import normalize_ar

MIN_GRAMS, MAX_GRAMS = 1, 2000
_BY_SLUG = {f["slug"]: f for f in food_data.FOODS}
_INDEX = [(f, normalize_ar(f["n"]), (f.get("en") or "").lower()) for f in food_data.FOODS]


def search(q, limit=8):
    """أول ٨ أصناف، اللي بيبدأ بالكلمة قبل اللي فيه الكلمة."""
    q = (q or "").strip()
    if len(q) < 2:
        return []
    na, ne = normalize_ar(q), q.lower()
    starts, has = [], []
    for f, ar, en in _INDEX:
        if ar.startswith(na) or en.startswith(ne):
            starts.append(f)
        elif na in ar or ne in en:
            has.append(f)
    return [{"slug": f["slug"], "n": f["n"], "en": f.get("en") or f["n"],
             "cal": f["cal"], "p": f["p"], "c": f["c"], "f": f["f"],
             "units": [[u[0], u[1]] for u in (f.get("units") or [])]}
            for f in (starts + has)[:limit]]


def entry(slug, grams):
    """صف جاهز للحفظ، أو None لو الصنف مش في الجدول أو الكمية مش منطقية."""
    food = _BY_SLUG.get(slug or "")
    try:
        grams = int(round(float(grams)))
    except (TypeError, ValueError):
        return None
    if not food or not (MIN_GRAMS <= grams <= MAX_GRAMS):
        return None
    k = grams / 100.0
    return {"slug": food["slug"], "food_name": food["n"], "grams": grams,
            "cal": int(round(float(food["cal"]) * k)),
            "p": round(float(food["p"]) * k, 1), "c": round(float(food["c"]) * k, 1),
            "f": round(float(food["f"]) * k, 1)}


def by_day(db_rows, user_id, since):
    """{"YYYY-MM-DD": {cal, p, c, f, items}} من since لحد النهارده."""
    out = {}
    try:
        rows = db_rows("SELECT id, log_date, food_name, grams, cal, p, c, f FROM food_log"
                       " WHERE user_id=? AND log_date>=? ORDER BY id", (user_id, since)) or []
    except Exception as e:  # noqa: BLE001
        print("[food_log] read failed: %s" % e)
        rows = []
    for r in rows:
        d = out.setdefault(str(r["log_date"])[:10], {"cal": 0, "p": 0.0, "c": 0.0, "f": 0.0, "items": []})
        d["cal"] += int(r["cal"] or 0)
        for k in ("p", "c", "f"):
            d[k] += float(r[k] or 0)
        d["items"].append({"id": r["id"], "name": r["food_name"], "grams": r["grams"], "cal": r["cal"]})
    for d in out.values():
        for k in ("p", "c", "f"):
            d[k] = int(round(d[k]))
    return out

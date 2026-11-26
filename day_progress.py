# -*- coding: utf-8 -*-
"""‏دواير الماكروز ونصايح النهارده في "خطتي".

‏العميل كان بيعلّم على وجباته ومايعرفش هو فين من يومه: كلت كام سعرة؟ فاضلّي
بروتين قد إيه؟ الملف ده بيرد من خطة الدكتور نفسها، مش من حساب من برّه.

‏المستهدف = مجموع اليوم المكتوب في الخطة (total_* أو target_* في يوم الزجزاج).
الخطة مابتخزّنش أرقام كل وجبة لوحدها، فنصيب كل وجبة بييجي من جدول الأكل
(meal_macros) كنسبة بس، ومجموع الأنصبة بيتظبط على مجموع اليوم بالظبط
(أكبر باقي). يعني الرقم الأخير اللي العميل بيشوفه هو رقم الدكتور.

‏النصايح كلها من الخطة: أرقام فاضلة ووجبات فيها. مفيش "كُل بيضتين" ولا أي
أكل جديد -- العميل ممكن يبقى عنده كلى أو سكر، والأكل الجديد قرار الدكتور.
"""

import meal_macros

NUTRIENTS = ("cal", "p", "c", "f")


def _num(v):
    try:
        v = float(v)
        return int(round(v)) if v > 0 else None
    except (TypeError, ValueError):
        return None


def _split(total, weights):
    """يقسّم رقم صحيح على أوزان، والمجموع بيفضل هو هو (أكبر باقي)."""
    keys = list(weights)
    wsum = sum(weights.values())
    if not keys:
        return {}
    if wsum <= 0:
        weights = {k: 1.0 for k in keys}
        wsum = float(len(keys))
    raw = {k: total * weights[k] / wsum for k in keys}
    out = {k: int(raw[k]) for k in keys}
    left = total - sum(out.values())
    for k in sorted(keys, key=lambda k: raw[k] - int(raw[k]), reverse=True)[:left]:
        out[k] += 1
    return out


def build(day, meal_keys, checked, skipped, labels, is_ar=True, hour=12, extra=None):
    """‏الدواير والنصايح ليوم واحد. None لو اليوم مافيهوش أرقام خالص."""
    if not day or not meal_keys:
        return None
    computed = {k: meal_macros.macros(day.get(k, "")) for k in meal_keys}
    # A meal with any unresolved item gives only a PARTIAL sum. Partial sums
    # must not set the proportions: if any meal is incomplete, split the day's
    # stored target evenly and say so (basis) instead of looking item-based.
    incomplete = [k for k in meal_keys
                  if str(day.get(k) or "").strip() and not computed[k].get("complete")]
    usable = (sum(m["cal"] for m in computed.values()) > 0 and
              sum(m["covered"] for m in computed.values()) / len(computed) >= 0.5
              and not incomplete)

    target = {}
    for n in NUTRIENTS:
        stored = _num(day.get("target_" + n)) or _num(day.get("total_" + n))
        if stored is None and usable:
            stored = _num(sum(m[n] for m in computed.values()))
        target[n] = stored
    if not target["cal"]:
        return None

    meals = {k: {} for k in meal_keys}
    for n in NUTRIENTS:
        if target[n] is None:
            continue
        weights = {k: (computed[k][n] if usable else 0) for k in meal_keys}
        for k, v in _split(target[n], weights).items():
            meals[k][n] = v

    checked = set(checked) & set(meal_keys)
    skipped = (set(skipped) & set(meal_keys)) - checked
    eaten = {n: (sum(meals[k].get(n, 0) for k in checked) if target[n] is not None else None)
             for n in NUTRIENTS}
    left_keys = [k for k in meal_keys if k not in checked and k not in skipped]
    hints = _hints(meals, target, checked, skipped, left_keys, labels, is_ar, hour, usable)
    # ‏أكل برّه الخطة (food_log): بيتجمع على المتاكل، والنصيحة بتقوله بالرقم بس.
    if extra and extra.get("cal"):
        for n in NUTRIENTS:
            if eaten[n] is not None:
                eaten[n] += int(extra.get(n) or 0)
        hints.append(("أكلت برّه الخطة %d سعرة النهارده، والدكتور هيشوفها في ملفك." % extra["cal"]) if is_ar
                     else "You ate %d kcal outside the plan today; your doctor will see it." % extra["cal"])
    return {"basis": "items" if usable else "even_split",
            "meals_done": len(checked), "meals_total": len(meal_keys),
            "incomplete_meals": incomplete,
            "target": target, "eaten": eaten, "meals": meals, "hints": hints,
            "extra": {n: int(extra.get(n) or 0) for n in NUTRIENTS} if extra else None}


def _hints(meals, target, checked, skipped, left_keys, labels, is_ar, hour, by_items=True):
    lab = lambda k: labels.get(k, k)
    hints = []
    if not left_keys:
        if checked and not skipped:
            hints.append("خلّصت كل وجبات النهارده 👏" if is_ar else "All of today's meals done 👏")
        elif checked:
            hints.append(("خلّصت النهارده: %d وجبة اتاكلت و%d اتخطّت." % (len(checked), len(skipped))) if is_ar
                         else "Day done: %d meals eaten, %d skipped." % (len(checked), len(skipped)))
        return hints

    if not by_items:
        # Even split: the per-meal numbers are the target divided by meal
        # count, not what the food contains. Never say "kcal/protein left".
        names = ("، " if is_ar else ", ").join(lab(k) for k in left_keys)
        hints.append(("لسه وجبات: %s. كميات السعرات والبروتين مش محسوبة من الأصناف لأن حساب وجبة ناقص." % names) if is_ar
                     else "Meals left: %s. Calories and protein are not calculated from the foods because a meal's calculation is incomplete." % names)
        if hour >= 21:
            n = len(left_keys)
            hints.append(("الوقت اتأخر وفاضل %d وجبة. لو مش هتاكلها، علّم «ماكلتهاش» علشان الدكتور يعرف." % n) if is_ar
                         else "It's late and %d meal(s) are left. If you won't eat them, mark them skipped so the doctor knows." % n)
        return hints
    left_cal = sum(meals[k].get("cal", 0) for k in left_keys)
    left_p = sum(meals[k].get("p", 0) for k in left_keys)
    names = ("، " if is_ar else ", ").join(lab(k) for k in left_keys)
    if is_ar:
        hints.append("فاضلك %d سعرة و%d جم بروتين في: %s." % (left_cal, left_p, names))
    else:
        hints.append("Left today: %d kcal and %d g protein in %s." % (left_cal, left_p, names))

    if hour >= 21:
        n = len(left_keys)
        hints.append(("الوقت اتأخر وفاضل %d وجبة. لو مش هتاكلها، علّم «ماكلتهاش» علشان الدكتور يعرف." % n) if is_ar
                     else "It's late and %d meal(s) are left. If you won't eat them, mark them skipped so the doctor knows." % n)
        return hints

    if by_items and target.get("p"):
        top = max(left_keys, key=lambda k: meals[k].get("p", 0))
        p = meals[top].get("p", 0)
        if p >= 0.3 * target["p"]:
            hints.append(("%s فيها %d جم بروتين، أكتر وجبة بروتين فاضلة النهارده." % (lab(top), p)) if is_ar
                         else "%s has %d g protein, the most protein left today." % (lab(top), p))
    return hints


# ═══ "أسبوعك": آخر ١٤ يوم ═══

def _window(days):
    """متوسط اللي اتاكل من المستهدف على كام يوم، بالنسبة المئوية."""
    tc = sum(d["cal_target"] for d in days)
    tp = sum(d["p_target"] for d in days)
    # Incomplete days carry no nutrition numbers (targets are 0 for them), so
    # they are left out here. A window with only such days has NO nutrition
    # aggregate (None), never an average of unlike quantities.
    only_incomplete = (not tc) and any(d.get("approx") for d in days)
    return {"cal_pct": None if only_incomplete else (int(round(sum(d["cal"] for d in days) * 100.0 / tc)) if tc else 0),
            "p_pct": None if only_incomplete else (int(round(sum(d["p"] for d in days) * 100.0 / tp)) if tp else 0),
            "days_logged": sum(1 for d in days if d["logged"])}


def days_flag(r):
    return r.get("basis") != "items"


def week(plan, meal_keys, labels, checks, skips, today, start=None, extras=None):
    """‏آخر ١٤ يوم (الأقدم الأول): لكل يوم المتاكل قصاد المستهدف، بنفس حساب
    build()، ومعاهم متوسط الأسبوع ده واللي قبله والفرق بينهم.

    ‏plan = أيام الخطة (الأحد أولها، زي get_meal_tracking). checks وskips =
    {"YYYY-MM-DD": {meal_key}}. الأيام قبل start (بداية الخطة) مابتتحسبش،
    علشان عميل لسه بادئ مايطلعش ملتزم ٣٠٪ بسبب أيام ماكانش عنده فيها خطة."""
    from datetime import timedelta
    days = []
    for back in range(13, -1, -1):
        d = today - timedelta(days=back)
        iso = d.isoformat()
        day = plan[min((d.weekday() + 1) % 7, len(plan) - 1)] if plan else {}
        keys = [k for k in meal_keys if day.get(k)]
        # ‏"ماكلتهاش" بتشيل علامة "اتاكلت" في الأبلكيشن، فهنا كمان التخطّي بيغلب.
        skipped = set(skips.get(iso, ()))
        checked = set(checks.get(iso, ())) - skipped
        r = build(day, keys, checked, skipped, labels, extra=(extras or {}).get(iso)) if keys else None
        active = r is not None and (start is None or d >= start)
        days.append({"date": iso, "dow": d.weekday(), "logged": (bool(checked) or bool((extras or {}).get(iso))) and active,
                     "approx": bool(active and r.get("basis") != "items")})
        # An incomplete day has no calorie/protein figure: it reports meals
        # ticked instead, and is excluded from the nutrition aggregates.
        nut = bool(active) and not days_flag(r)
        days[-1].update({"cal": r["eaten"]["cal"] if nut else 0, "p": (r["eaten"]["p"] or 0) if nut else 0,
                         "cal_target": r["target"]["cal"] if nut else 0,
                         "p_target": (r["target"]["p"] or 0) if nut else 0,
                         "meals_done": r["meals_done"] if active else 0,
                         "meals_total": r["meals_total"] if active else 0})
    this, last = _window(days[7:]), _window(days[:7])
    this["approx_days"] = sum(1 for d in days[7:] if d["approx"])
    last["approx_days"] = sum(1 for d in days[:7] if d["approx"])
    delta = None if (not last["days_logged"] or None in (this["cal_pct"], this["p_pct"], last["cal_pct"], last["p_pct"])) else {
        "cal_pct": this["cal_pct"] - last["cal_pct"], "p_pct": this["p_pct"] - last["p_pct"]}
    return {"days": days, "this": this, "last": last, "delta": delta}

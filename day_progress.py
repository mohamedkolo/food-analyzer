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


def build(day, meal_keys, checked, skipped, labels, is_ar=True, hour=12):
    """‏الدواير والنصايح ليوم واحد. None لو اليوم مافيهوش أرقام خالص."""
    if not day or not meal_keys:
        return None
    computed = {k: meal_macros.macros(day.get(k, "")) for k in meal_keys}
    usable = (sum(m["cal"] for m in computed.values()) > 0 and
              sum(m["covered"] for m in computed.values()) / len(computed) >= 0.5)

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
    return {"target": target, "eaten": eaten, "meals": meals,
            "hints": _hints(meals, target, checked, skipped, left_keys, labels, is_ar, hour)}


def _hints(meals, target, checked, skipped, left_keys, labels, is_ar, hour):
    lab = lambda k: labels.get(k, k)
    hints = []
    if not left_keys:
        if checked and not skipped:
            hints.append("خلّصت كل وجبات النهارده 👏" if is_ar else "All of today's meals done 👏")
        elif checked:
            hints.append(("خلّصت النهارده: %d وجبة اتاكلت و%d اتخطّت." % (len(checked), len(skipped))) if is_ar
                         else "Day done: %d meals eaten, %d skipped." % (len(checked), len(skipped)))
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

    if target.get("p"):
        top = max(left_keys, key=lambda k: meals[k].get("p", 0))
        p = meals[top].get("p", 0)
        if p >= 0.3 * target["p"]:
            hints.append(("%s فيها %d جم بروتين، أكتر وجبة بروتين فاضلة النهارده." % (lab(top), p)) if is_ar
                         else "%s has %d g protein, the most protein left today." % (lab(top), p))
    return hints

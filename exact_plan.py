# -*- coding: utf-8 -*-
"""Arithmetic finalisation of a newly generated plan.

Every displayed number comes from the written items (grams x food_data per
100 g). Meal portions are then scaled so the item-computed day total reaches
the day's kcal target, and, when the day's protein is far above the
clinician-set target, protein-dense items are reduced and carbohydrate-dense
items take back the calories. No clinical target is invented: kcal and
protein targets are the ones the plan already carries.

Saved plans are never touched; this runs only on a freshly generated draft.
"""
import re

import meal_macros as mm
import portion_scale as ps

KCAL_TOL = 0.03          # day total vs target after rounding to 5/10 g
PROTEIN_OVER = 1.10      # reduce protein items above 110% of the target
MAX_PASSES = 14


def _segments(text):
    return text.split(" + ")


def _item(seg):
    f = mm.find_food(seg)
    g, how = mm.item_grams(seg, f)
    if not f or g <= 0:
        return None
    k = g / 100.0
    return {"cal": float(f.get("cal") or 0) * k, "p": float(f.get("p") or 0) * k,
            "c": float(f.get("c") or 0) * k, "f": float(f.get("f") or 0) * k,
            "cat": f.get("cat"), "g": g}


def _totals(plan_meals):
    t = {"cal": 0.0, "p": 0.0, "c": 0.0, "f": 0.0}
    for text in plan_meals.values():
        for seg in _segments(text):
            it = _item(seg)
            if it:
                for k in t:
                    t[k] += it[k]
    return t


def _scale_where(text, pred, factor):
    out = []
    for seg in _segments(text):
        it = _item(seg)
        if it and pred(it) and not ps._is_free(seg):
            seg, _, _ = ps._scale_segment(seg, factor)
        out.append(seg)
    return " + ".join(out)


def _is_protein(it):
    return it["cat"] in ("meat", "poultry", "fish", "dairy", "supplement", "eggs", "egg") and it["p"] * 4 >= 0.35 * max(it["cal"], 1)


MAX_ABSORB_G = 350      # an item already this heavy does not take more calories


def _is_carb(it):
    if it["g"] > MAX_ABSORB_G or it["cal"] < 0.6 * it["g"]:     # light foods (zucchini, apple) do not absorb kcal
        return False
    if it["cat"] in ("grain", "fruit", "legume", "veg") and it["c"] * 4 >= 0.6 * max(it["cal"], 1):
        return True
    return it["cat"] == "nut" and it["f"] * 9 >= 0.6 * max(it["cal"], 1)   # oil/nuts also absorb calories


def finalize_day(day, target_cal, target_p, shares=None):
    slots = [k for k in day.get("meal_labels", []) if isinstance(day.get(k), str)]
    meals = {k: day[k] for k in slots}
    info = {"method": "item arithmetic", "target_cal": int(round(target_cal)),
            "target_p": int(round(target_p)) if target_p else 0,
            "shares": "clinician-configured" if shares else
                      "engine default shape (unchanged, not individualised)"}
    if shares:
        tot = sum(shares.get(k, 0) for k in slots) or 1.0
        for k in slots:
            want = target_cal * shares.get(k, 0) / tot
            for _ in range(3):
                cur = _totals({k: meals[k]})["cal"]
                if cur <= 0 or abs(cur - want) / want < 0.02:
                    break
                meals[k], _ = ps.scale_meal(meals[k], max(0.4, min(2.5, want / cur)))
    for _ in range(MAX_PASSES):
        t = _totals(meals)
        if t["cal"] <= 0:
            break
        over_p = target_p and (t["p"] > PROTEIN_OVER * target_p
                               or t["p"] < 0.92 * target_p)
        if over_p:
            need_cut = t["p"] - 1.0 * target_p if t["p"] > target_p else t["p"] - 0.97 * target_p
            prot_p = sum(_item(s)["p"] for m in meals.values() for s in _segments(m)
                         if _item(s) and _is_protein(_item(s)))
            if prot_p > 0:
                f = max(0.5, min(1.8, (target_p - (t["p"] - prot_p)) / prot_p))
                for k in slots:
                    meals[k] = _scale_where(meals[k], _is_protein, f)
                t = _totals(meals)
        gap = target_cal - t["cal"]
        if abs(gap) / target_cal <= KCAL_TOL and not over_p:
            break
        carb_cal = sum(_item(s)["cal"] for m in meals.values() for s in _segments(m)
                       if _item(s) and _is_carb(_item(s)))
        if over_p and carb_cal > 0:
            f = max(0.5, min(3.0, 1.0 + gap / carb_cal))
            for k in slots:
                meals[k] = _scale_where(meals[k], _is_carb, f)
        else:
            f = max(0.5, min(2.5, target_cal / t["cal"]))
            for k in slots:
                meals[k], _ = ps.scale_meal(meals[k], f)
    t = _totals(meals)
    for k in slots:
        day[k] = meals[k]
    day["total_cal"] = int(round(t["cal"]))
    day["total_p"] = int(round(t["p"]))
    day["total_c"] = int(round(t["c"]))
    day["total_f"] = int(round(t["f"]))
    info["computed_cal"] = day["total_cal"]
    info["computed_p"] = day["total_p"]
    info["cal_dev_pct"] = round((t["cal"] - target_cal) / target_cal * 100, 1)
    info["within_tolerance"] = abs(t["cal"] - target_cal) / target_cal <= 0.05
    info["protein_reached"] = (not target_p) or abs(t["p"] - target_p) / target_p <= 0.15
    info["protein_dev_pct"] = (round((t["p"] - target_p) / target_p * 100, 1)
                               if target_p else None)
    day["exact"] = info
    return day


def finalize_plan(plan, data):
    target_p = ((data or {}).get("protein_basis") or {}).get("grams") or 0
    shares = (data or {}).get("meal_shares") or None
    for day in plan or []:
        if isinstance(day, dict) and day.get("total_cal"):
            finalize_day(day, float(day["total_cal"]), float(target_p), shares)
    return plan

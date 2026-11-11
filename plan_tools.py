# -*- coding: utf-8 -*-
"""Checking a plan while it is being edited, and reusing one as a template.

Two things the preview page could not do:

1. **Say what an edit did.** The day's total and its gap from the target
   were worked out once, when the week was generated. Swap a meal, or type
   over one, and the numbers on the page stayed as they were -- and the text
   typed by hand was never run past the client's conditions at all. The
   generator filters every meal it picks; the keyboard went straight past
   that filter. A meal typed in for a client with kidney disease was saved
   exactly as typed.

   So every change now comes back with the day's new total, the gap, and
   anything in the new text that clashes with this client. The edit is still
   saved: the nutritionist decides. What changes is that they are told.

2. **Carry a week to another client.** A template is the week's meals and
   nothing else -- no name, no phone, no measurements (README rule 6: no
   client data where it does not belong). Applying one to a new client runs
   every meal past *that* client's conditions and exclusions, and swaps the
   ones that fail for meals the generator itself would have allowed. A
   template made for a healthy client must not hand a diabetic the same
   breakfast unexamined.

Nothing here touches Flask or the database; the routes pass the data in.
"""

import meal_macros
from meal_database import CONDITION_MAP, _contains_unsafe
from plan_engine import parse_user_exclusions

MEAL_KEYS = ("breakfast", "snack1", "meal1", "pre_workout", "lunch",
             "post_workout", "iftar", "snack", "snack2", "suhoor", "meal2",
             "dinner")
# ‏فرق أصغر من كده بين مجموع اليوم والهدف مش بيتنبّه عليه -- نفس الرقم
# اللي صفحة المعاينة بتستخدمه من الأول.
GAP_ALERT_KCAL = 150
# ‏تحت النسبة دي من الأصناف المعروفة، سعرات الوجبة تخمين مش حساب.
MIN_COVERAGE = 0.6


def _exclusions(data):
    allergies = data.get("allergies")
    return parse_user_exclusions(
        data.get("notes", ""), data.get("disliked_foods", ""),
        allergies if isinstance(allergies, list) else [])


def meal_problems(data, text):
    """Why this meal should not be on this client's sheet. [] when it is fine.

    Each entry is {"kind": "condition" | "excluded", "what": ...}: the
    condition as the form stores it (Arabic), or the word the client asked
    to avoid.
    """
    text = text or ""
    out = []
    for condition in data.get("symptoms") or []:
        key = CONDITION_MAP.get(condition)
        if key and _contains_unsafe(text, key):
            out.append({"kind": "condition", "what": condition})
    for word in _exclusions(data):
        if word and word in text:
            out.append({"kind": "excluded", "what": word})
    return out


def plan_problems(data, plan):
    """{(day index, meal key): [problems]} for the whole week."""
    found = {}
    for i, day in enumerate(plan or []):
        for key in MEAL_KEYS:
            if day.get(key):
                issues = meal_problems(data, day[key])
                if issues:
                    found[(i, key)] = issues
    return found


def _target(data, day):
    for value in (day.get("target_cal"), data.get("goal_cal")):
        try:
            if value:
                return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def day_status(data, day, estimated=False):
    """The numbers the day's header shows."""
    total = int(day.get("total_cal") or 0)
    target = _target(data, day)
    gap = (target - total) if target else None
    return {"total_cal": total, "target_cal": target, "gap": gap,
            "alert": gap is not None and abs(gap) > GAP_ALERT_KCAL,
            "estimated": bool(estimated)}


def apply_change(data, day, old_text, new_text):
    """Bring the day's total in line with one meal having changed.

    The total is moved by the *difference* between the two meals, both
    measured the same way (from their items), rather than recomputed from
    scratch. The generator's total comes from the calories stored with each
    meal; adding the week up again from the text would jump by the
    disagreement between the two methods on meals nobody touched.

    When too little of either meal is recognised the difference is a guess,
    and the result says so instead of raising a false alarm.
    """
    old = meal_macros.macros(old_text)
    new = meal_macros.macros(new_text)
    estimated = min(old["covered"], new["covered"]) < MIN_COVERAGE
    if old_text != new_text:
        day["total_cal"] = max(0, int(day.get("total_cal") or 0)
                               - old["cal"] + new["cal"])
        if day.get("total_p") is not None:
            day["total_p"] = max(0, int(day.get("total_p") or 0)
                                 - old["p"] + new["p"])
    status = day_status(data, day, estimated)
    status["problems"] = meal_problems(data, new_text)
    status["meal_cal"] = new["cal"]
    return status


# ── القوالب ─────────────────────────────────────────────────────────

def template_from(plan):
    """The week's meals and day names -- nothing about the client."""
    out = []
    for day in plan or []:
        slim = {"day": day.get("day"), "total_cal": day.get("total_cal"),
                "total_p": day.get("total_p")}
        for key in MEAL_KEYS:
            if day.get(key):
                slim[key] = day[key]
        out.append(slim)
    return out


def template_fits(plan, template):
    """A template only drops into a week with the same meal slots.

    A three-meal template laid over a Ramadan week (iftar/suhoor) would
    leave half the day's slots holding the old client's food.
    """
    if not plan or not template or len(plan) != len(template):
        return False
    slots = lambda day: {k for k in MEAL_KEYS if day.get(k)}
    return all(slots(a) == slots(b) for a, b in zip(plan, template))


def apply_template(data, plan, template, safe_options):
    """Lay a template's meals over this client's week. Returns what changed.

    safe_options(meal_key) -> meals the generator would allow this client
    in that slot. Every template meal is checked against the client first;
    one that fails is replaced from that list, and if nothing safe is left
    the client's own generated meal stays where it was.

    Returns {"replaced": [(day index, key)], "kept": [(day index, key)]}.
    """
    replaced, kept = [], []
    for i, (day, tpl) in enumerate(zip(plan, template)):
        for key in MEAL_KEYS:
            if not tpl.get(key) or not day.get(key):
                continue
            wanted = tpl[key]
            if meal_problems(data, wanted):
                options = [m.get("meal") if isinstance(m, dict) else m
                           for m in safe_options(key)]
                options = [m for m in options
                           if m and not meal_problems(data, m)]
                if not options:
                    kept.append((i, key))
                    continue
                wanted = options[(i + len(replaced)) % len(options)]
                replaced.append((i, key))
            apply_change(data, day, day[key], wanted)
            day[key] = wanted
    return {"replaced": replaced, "kept": kept}

# -*- coding: utf-8 -*-
"""Recipe entries with explicit ingredients (review branch, not wired in).

An entry lists ingredient, grams and state per line. Nutrition is computed
from per-100 g source rows with exact fractions. The total belongs to the
whole recipe at the ingredient weights entered. It is not a cooked or plated
yield, and there is deliberately no per-100 g field for the prepared dish.

Nothing here is read by the app yet. Saved plans and the legacy meal lists
are untouched.
"""
from fractions import Fraction

BASIS = "input_ingredient_weights"
NUTRIENTS = ("kcal", "p", "f", "c")
STATES = ("raw", "cooked", "ready", "oil")


class RecipeError(ValueError):
    pass


def source_row(fdc_id, desc, kcal, p, f, c, url=None):
    return {"fdc_id": str(fdc_id), "desc": desc, "kcal": kcal, "p": p, "f": f, "c": c, "url": url}


def validate(entry):
    """Raise RecipeError on anything that would make the numbers unclear."""
    if entry.get("basis") != BASIS:
        raise RecipeError("basis must be %s" % BASIS)
    for banned in ("per100", "per_100g", "cooked_yield_g", "serving_g"):
        if banned in entry:
            raise RecipeError("field %s is not allowed: yield was not measured" % banned)
    items = entry.get("ingredients") or []
    if not items:
        raise RecipeError("no ingredients")
    for it in items:
        if not it.get("name"):
            raise RecipeError("ingredient without a name")
        g = it.get("g")
        if not isinstance(g, (int, float)) or isinstance(g, bool) or g <= 0:
            raise RecipeError("grams missing or not positive for %s" % it.get("name"))
        if it.get("state") not in STATES:
            raise RecipeError("state missing or unknown for %s" % it["name"])
        src = it.get("source")
        if not src or not src.get("fdc_id"):
            raise RecipeError("no source row for %s" % it["name"])
        for k in NUTRIENTS:
            if not isinstance(src.get(k), (int, float)):
                raise RecipeError("source %s lacks %s" % (src["fdc_id"], k))
    return True


def totals(entry):
    """Whole-recipe totals from unrounded data, as floats."""
    validate(entry)
    acc = {k: Fraction(0) for k in NUTRIENTS}
    for it in entry["ingredients"]:
        for k in NUTRIENTS:
            acc[k] += Fraction(str(it["source"][k])) * Fraction(str(it["g"])) / 100
    return {k: float(v) for k, v in acc.items()}


def input_weight_g(entry):
    validate(entry)
    return sum(it["g"] for it in entry["ingredients"])


def meal_text(entry):
    """Text the existing condition filter reads: display name plus every
    ingredient name and its state, so a generic name cannot hide an ingredient."""
    validate(entry)
    parts = [entry["name"]]
    for it in entry["ingredients"]:
        parts.append("%s %sجم" % (it["name"], it["g"]))
    return " + ".join(parts)


def as_meal_item(entry):
    """Shape the legacy pools use ({"meal": ...}), with the computed totals.
    Rounded for display only."""
    t = totals(entry)
    return {"meal": meal_text(entry), "cal": round(t["kcal"]), "p": round(t["p"], 1),
            "basis": BASIS, "recipe_id": entry["id"]}

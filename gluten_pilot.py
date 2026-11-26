# -*- coding: utf-8 -*-
"""Ingredient-level gluten status for the six pilot dishes (review only).

This is a screen on the ingredient identity as written. It is NOT a
certification and NOT a suitability claim for the whole meal: cross-contact in
a kitchen, packaged-product additives and label changes are outside it.

Status per ingredient (keyed by the USDA FDC id the recipe entry cites):
  contains_gluten_grain  a gluten grain or a product of one, by identity
  none_by_identity       a plain food in a category the sources list as
                         naturally free of gluten grains, as described by the row
  unknown                the sources do not settle it, or it depends on the
                         product or recipe. Treated as excluded, never as ok.

Dish outcome:
  excluded_contains_gluten        any ingredient contains_gluten_grain
  excluded_unknown_ingredient     no contains, but at least one unknown
  no_gluten_ingredient_found      every ingredient none_by_identity (as written)
Only the last is offered to a client with a gluten condition. Nothing here is
read by the app, the legacy library, client pages or saved plans.
"""
import recipe_entries as RE

FDA = "https://www.fda.gov/food/nutrition-education-resources-materials/gluten-and-food-labeling"
CDF_SRC = "https://celiac.org/what-is-gluten/sources-of-gluten/"
CDF_FOODS = "https://celiac.org/gluten-free-living/gluten-free-foods/"
MAYO = "https://newsnetwork.mayoclinic.org/discussion/gluten-free-diet-basics/"
OIL = "https://www.beyondceliac.org/gluten-free-diet/is-it-gluten-free/oil/"

C, N, U = "contains_gluten_grain", "none_by_identity", "unknown"

STATUS = {
    "174916": (C, "whole-wheat pita: bread made from wheat", [FDA, CDF_SRC]),
    "169700": (C, "couscous is listed among foods that contain gluten (wheat pasta product)", [CDF_SRC]),
    "173757": (N, "boiled chickpeas: beans and legumes are a naturally gluten-free group", [CDF_FOODS]),
    "171284": (U, "plain yogurt: dairy is listed as naturally gluten-free, but Mayo says 'most dairy products', so a packaged product can carry additives (label-dependent)", [CDF_FOODS, MAYO]),
    "171413": (N, "olive oil: most plain cooking oils are naturally gluten-free (the source adds a label caveat for flavored or additive oils)", [OIL]),
    "169230": (N, "raw garlic: vegetables are a naturally gluten-free group", [CDF_FOODS]),
    "167747": (N, "raw lemon juice: fruit is a naturally gluten-free group", [CDF_FOODS]),
    "171477": (N, "roasted chicken breast, meat only: meat and poultry are naturally gluten-free as long as not breaded, batter-coated or marinated; the recipe lists no coating or marinade", [CDF_FOODS, MAYO]),
    "170000": (N, "raw onion: vegetables are a naturally gluten-free group", [CDF_FOODS]),
    "170457": (N, "raw tomato: vegetables are a naturally gluten-free group", [CDF_FOODS]),
    "170427": (N, "raw green pepper: vegetables are a naturally gluten-free group", [CDF_FOODS]),
    "168878": (N, "cooked white rice: rice is listed as naturally gluten-free", [CDF_FOODS]),
    "171287": (N, "raw whole egg: fresh eggs are naturally gluten-free", [MAYO]),
    "169291": (N, "raw zucchini: vegetables are a naturally gluten-free group", [CDF_FOODS]),
    "170393": (N, "raw carrot: vegetables are a naturally gluten-free group", [CDF_FOODS]),
    "172455": (U, "home-prepared falafel: the USDA row does not state whether flour or breadcrumbs are used, so the sources cannot settle it", []),
}

OUTCOME_CONTAINS = "excluded_contains_gluten"
OUTCOME_UNKNOWN = "excluded_unknown_ingredient"
OUTCOME_NONE_FOUND = "no_gluten_ingredient_found"

# Plain wording. Deliberately no claim of being free of gluten or certified.
LABEL = {
    OUTCOME_CONTAINS: "Excluded: has an ingredient that contains a gluten grain.",
    OUTCOME_UNKNOWN: "Excluded: has an ingredient whose gluten status the sources do not settle.",
    OUTCOME_NONE_FOUND: "No gluten-grain ingredient found among the listed ingredients as written. "
                        "This checks ingredient identity only. It is not a certification and does not cover cross-contact or packaged-product labels.",
}


def ingredient_status(ing):
    fid = (ing.get("source") or {}).get("fdc_id")
    return STATUS.get(str(fid), (U, "ingredient not covered by the pilot table", []))


def outcome(entry):
    RE.validate(entry)
    sts = [ingredient_status(i)[0] for i in entry["ingredients"]]
    if C in sts:
        return OUTCOME_CONTAINS
    if U in sts:
        return OUTCOME_UNKNOWN
    return OUTCOME_NONE_FOUND


def offer_to_gluten_client(entry):
    return outcome(entry) == OUTCOME_NONE_FOUND


def as_item(entry):
    item = RE.as_meal_item(entry)
    item["gluten_pilot"] = outcome(entry)
    item["gluten_pilot_label"] = LABEL[outcome(entry)]
    return item


def gate(items, condition_names):
    """For a gluten condition keep only items whose pilot outcome is
    no_gluten_ingredient_found. Items without a pilot outcome are dropped for
    gluten clients (unknown is excluded). Other conditions: unchanged."""
    import meal_database as MD
    if "جلوتين" not in MD.unsafe_keys_for(condition_names):
        return list(items)
    return [i for i in items if isinstance(i, dict) and i.get("gluten_pilot") == OUTCOME_NONE_FOUND]

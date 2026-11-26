# -*- coding: utf-8 -*-
"""Recipe entries: explicit ingredients, source math, ingredient propagation.

Checks the schema and that the existing condition filter sees each ingredient.
It does not say the library's exclusion lists are clinically right, only that
what the lists contain reaches the entry through its ingredients.

Run with:  python3 tests/test_recipe_entries.py
"""
import copy
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import meal_database as MD  # noqa: E402
import recipe_entries as RE  # noqa: E402

S = RE.source_row
FATTEH = {
    "id": "fatteh-hummus-base-v1", "name": "طبق الفتة", "basis": RE.BASIS,
    "ingredients": [
        {"name": "عيش بيتا قمح كامل", "g": 25, "state": "ready", "source": S(174916, "Pita bread, whole-wheat", 262, 9.8, 1.71, 55.9)},
        {"name": "حمص مسلوق", "g": 70, "state": "cooked", "source": S(173757, "Chickpeas, boiled", 164, 8.86, 2.59, 27.4)},
        {"name": "زبادي كامل الدسم", "g": 40, "state": "ready", "source": S(171284, "Yogurt, plain, whole milk", 61, 3.47, 3.25, 4.66)},
        {"name": "زيت زيتون", "g": 5, "state": "oil", "source": S(171413, "Olive oil", 884, 0, 100, 0)},
        {"name": "توم", "g": 2, "state": "raw", "source": S(169230, "Garlic", 149, 6.36, 0.5, 33.1)},
        {"name": "عصير ليمون", "g": 8, "state": "raw", "source": S(167747, "Lemon juice", 22, 0.35, 0.24, 6.9)},
    ],
}
FAILS = []


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + (" " + detail if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


def raises(fn):
    try:
        fn()
    except RE.RecipeError:
        return True
    return False


# 1. Source math: independent recompute, accepted base totals.
t = RE.totals(FATTEH)
exp = {k: sum(Fraction(str(i["source"][k])) * i["g"] / 100 for i in FATTEH["ingredients"]) for k in RE.NUTRIENTS}
check("totals equal an independent exact recompute", all(abs(t[k] - float(exp[k])) < 1e-9 for k in RE.NUTRIENTS))
check("accepted base kcal 253.6, P 10.2, F 8.6, C 36.2",
      [round(t[k], 1) for k in ("kcal", "p", "f", "c")] == [253.6, 10.2, 8.6, 36.2], str(t))
check("input weight is 150 g and is labelled as input weight", RE.input_weight_g(FATTEH) == 150 and FATTEH["basis"] == RE.BASIS)

# 2. Schema refuses unclear numbers.
bad = copy.deepcopy(FATTEH); bad["per100"] = {"kcal": 169}
check("per-100 g prepared-dish field refused", raises(lambda: RE.validate(bad)))
bad = copy.deepcopy(FATTEH); bad["cooked_yield_g"] = 150
check("cooked-yield field refused", raises(lambda: RE.validate(bad)))
bad = copy.deepcopy(FATTEH); bad["basis"] = "serving"
check("wrong basis refused", raises(lambda: RE.validate(bad)))
bad = copy.deepcopy(FATTEH); bad["ingredients"][1]["state"] = "boiled-ish"
check("unknown state refused", raises(lambda: RE.validate(bad)))
bad = copy.deepcopy(FATTEH); del bad["ingredients"][0]["g"]
check("missing grams refused", raises(lambda: RE.validate(bad)))
bad = copy.deepcopy(FATTEH); bad["ingredients"][2]["g"] = 0
check("zero grams refused", raises(lambda: RE.validate(bad)))
bad = copy.deepcopy(FATTEH); bad["ingredients"][3]["source"] = None
check("ingredient without a source row refused", raises(lambda: RE.validate(bad)))
bad = copy.deepcopy(FATTEH); bad["ingredients"] = []
check("no ingredients refused", raises(lambda: RE.validate(bad)))

# 3. Ingredient propagation through the existing filter. Display name is
# generic on purpose, so only the ingredient lines can trigger a match.
item = RE.as_meal_item(FATTEH)
check("meal text lists every ingredient", all(i["name"] in item["meal"] for i in FATTEH["ingredients"]))
check("generic name alone passes every list", all(not MD._contains_unsafe(FATTEH["name"], k) for k in MD.UNSAFE_FOODS))
pool = [item]
# (condition, ingredient the list is expected to catch, expected to be dropped)
for cond, ing in (("حساسية اللاكتوز", "yogurt"), ("نقص G6PD", "chickpeas"), ("قولون عصبي", "chickpeas")):
    kept = MD.filter_by_conditions(pool, [cond])
    check("%s: entry dropped through its %s line" % (cond, ing), item not in kept)

# Gluten: the list now holds the bread and wheat words. The entry's pita line
# is written "عيش بيتا قمح كامل" (bread, wheat), so it must be dropped.
kept = MD.filter_by_conditions(pool, ["حساسية الجلوتين"])
check("حساسية الجلوتين: entry dropped through its bread/wheat line", item not in kept)

# 4. Removing the triggering ingredient changes the outcome (propagation, not name).
nolac = copy.deepcopy(FATTEH); del nolac["ingredients"][2]
lac = "حساسية اللاكتوز"
check("without the yogurt line the lactose list no longer matches",
      not MD._contains_unsafe(RE.meal_text(nolac), "لاكتوز") and MD._contains_unsafe(RE.meal_text(FATTEH), "لاكتوز"))


# 5. Word identity (sources are in meal_database next to the list).
G = "جلوتين"
for text, expect in (("عيش بلدي 60جم", True), ("عيش بيتا 25جم", True), ("خبز 60جم", True), ("بليلة قمح 150جم", True),
                     ("تورتيلا قمح كامل 1", True), ("كسكس 100جم", True), ("جاودار 50جم", True), ("سميد 40جم", True),
                     ("عيش الغراب 100جم", False), ("بدون عيش", False), ("أرز أبيض 100جم", False)):
    check("gluten word match %r -> %s" % (text, expect), MD._contains_unsafe(text, G) == expect)

# 6. End-to-end through the generation path routes_plans uses for a gluten client.
os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_recipe_entries.db"
import routes_plans as RP  # noqa: E402
leaks = []
checked = 0
for goal in ("weight_loss", "muscle_gain", "maintenance"):
    for culture in ("مصري", "خليجي", "شامي", "مغربي", "عالمي"):
        for slot in ("breakfast", "lunch", "dinner", "snack"):
            data = {"goal_type": goal, "culture": culture, "symptoms": ["حساسية الجلوتين"]}
            meals = RP._filtered_meals(data, slot, culture)
            for m in meals:
                checked += 1
                if MD._contains_unsafe(MD._meal_text(m), G):
                    leaks.append((goal, culture, slot, MD._meal_text(m)[:60]))
check("generation path returns no gluten-listed meal (%d meals checked, %d leaks)" % (checked, len(leaks)), not leaks, str(leaks[:3]))
check("generation path pools are not empty for a gluten client",
      all(RP._filtered_meals({"goal_type": "weight_loss", "culture": c, "symptoms": ["حساسية الجلوتين"]}, "breakfast", c) for c in ("مصري", "خليجي", "شامي", "مغربي", "عالمي")))
# no other condition list was touched by this change
check("only the gluten list gained the bread/wheat words", all("عيش" not in v and "قمح" not in v for k, v in MD.UNSAFE_FOODS.items() if k != G))

print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)

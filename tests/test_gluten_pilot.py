# -*- coding: utf-8 -*-
"""Pilot: ingredient-level gluten status for six proposed dishes.

Checks statuses, dish outcomes, wording, and the real filter path for a gluten
client. It does not certify any dish and says nothing about other conditions'
lists. Run with:  python3 tests/test_gluten_pilot.py
"""
import os
import sys

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_gluten_pilot.db"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import meal_database as MD  # noqa: E402
import gluten_pilot as GP  # noqa: E402
import pilot_recipes as PR  # noqa: E402
import recipe_entries as RE  # noqa: E402

FAILS = []
GC = ["حساسية الجلوتين"]


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + (" " + str(detail) if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


by_id = {e["id"]: e for e in PR.RECIPES}
EXPECT = {
    "fatteh-hummus-base-v1": GP.OUTCOME_CONTAINS,        # whole-wheat pita
    "shawarma-chicken-no-bread-v1": GP.OUTCOME_NONE_FOUND,
    "mandi-chicken-v1": GP.OUTCOME_NONE_FOUND,
    "omelette-vegetables-v1": GP.OUTCOME_NONE_FOUND,
    "couscous-vegetables-v1": GP.OUTCOME_CONTAINS,       # couscous
    "shakshuka-falafel-v1": GP.OUTCOME_UNKNOWN,          # falafel flour not stated
}
for k, v in EXPECT.items():
    check("%s -> %s" % (k, v), GP.outcome(by_id[k]) == v, GP.outcome(by_id[k]))

# every ingredient used by the six dishes has an explicit status with a reason
used = {i["source"]["fdc_id"] for e in PR.RECIPES for i in e["ingredients"]}
check("all 16 ingredients covered by an explicit status", len(used) == 16 and used <= set(GP.STATUS), (len(used), used - set(GP.STATUS)))
check("every non-unknown status cites a source", all(GP.STATUS[k][2] for k in GP.STATUS if GP.STATUS[k][0] != GP.U))
check("unknown ingredients are exactly yogurt and falafel", {k for k, v in GP.STATUS.items() if v[0] == GP.U} == {"171284", "172455"})
check("an ingredient outside the table is unknown, never ok",
      GP.ingredient_status({"source": {"fdc_id": "999999"}})[0] == GP.U)

# wording never claims free-of-gluten or certified
bad_words = ("gluten-free", "gluten free", "certified", "safe for", "suitable", "خالي من الجلوتين", "خالية من الجلوتين", "مضمون", "مناسب")
check("labels carry no free-of-gluten, certified or suitable claim",
      all(not any(w in v.lower() for w in bad_words) for v in GP.LABEL.values()))
check("the 'none found' label says it is not a certification", "not a certification" in GP.LABEL[GP.OUTCOME_NONE_FOUND])

# Real filter path for a gluten client: the existing word filter, then the pilot gate.
items = [GP.as_item(e) for e in PR.RECIPES]
word_kept = MD.filter_by_conditions(items, GC)
word_kept_ids = {i["recipe_id"] for i in word_kept}
check("word filter alone drops the pita and couscous dishes (sourced words)",
      "fatteh-hummus-base-v1" not in word_kept_ids and "couscous-vegetables-v1" not in word_kept_ids)
check("word filter alone would let the falafel dish through", "shakshuka-falafel-v1" in word_kept_ids)
gated = GP.gate(word_kept, GC)
ids = sorted(i["recipe_id"] for i in gated)
check("after the pilot gate only the three 'none found' dishes remain",
      ids == sorted(["shawarma-chicken-no-bread-v1", "mandi-chicken-v1", "omelette-vegetables-v1"]), ids)
check("unknown-ingredient dish is excluded, not offered with a warning",
      all(i["recipe_id"] != "shakshuka-falafel-v1" for i in gated))
check("an item with no pilot outcome is dropped for a gluten client", GP.gate([{"meal": "x"}], GC) == [])
check("without a gluten condition the gate changes nothing", len(GP.gate(items, ["حساسية اللاكتوز"])) == len(items))

# the dish names and the pilot text do not hide the pita or couscous words
for i in items:
    check("%s: item text carries every ingredient name" % i["recipe_id"],
          all(x["name"] in i["meal"] for x in by_id[i["recipe_id"]]["ingredients"]))

# Through the plan-generation filter function with an isolated pool.
import routes_plans as RP  # noqa: E402
orig = RP.get_meal_pool
RP.get_meal_pool = lambda goal, culture: {"lunch": items}
try:
    meals = RP._filtered_meals({"goal_type": "weight_loss", "culture": "مصري", "symptoms": GC}, "lunch", "مصري")
finally:
    RP.get_meal_pool = orig
gen_ids = {m["recipe_id"] for m in meals}
check("generation filter (isolated pool): pita and couscous dishes dropped by the word layer",
      "fatteh-hummus-base-v1" not in gen_ids and "couscous-vegetables-v1" not in gen_ids, gen_ids)
check("generation filter then pilot gate: exactly the three 'none found' dishes",
      sorted(m["recipe_id"] for m in GP.gate(meals, GC)) == sorted(["shawarma-chicken-no-bread-v1", "mandi-chicken-v1", "omelette-vegetables-v1"]))

print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)

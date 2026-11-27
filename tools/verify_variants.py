# -*- coding: utf-8 -*-
"""Re-verify meal_variant_foods against a local copy of USDA SR Legacy (April 2018 CSV).
usage: python3 tools/verify_variants.py /path/to/FoodData_Central_sr_legacy_food_csv_2018-04
Checks per row: the USDA id exists, its description equals "usda", and kcal/protein/carbs/fat equal USDA per 100 g exactly."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import meal_variant_foods as V
D = sys.argv[1]
food = {r["fdc_id"]: r["description"] for r in csv.DictReader(open(os.path.join(D, "food.csv"), encoding="utf-8"))}
want = {"1008": "cal", "1003": "p", "1004": "f", "1005": "c"}
nut = {}
for r in csv.DictReader(open(os.path.join(D, "food_nutrient.csv"))):
    k = want.get(r["nutrient_id"])
    if k:
        nut.setdefault(r["fdc_id"], {})[k] = float(r["amount"])
bad = 0
for f in V.VARIANT_FOODS:
    i = str(f["fdc"])
    ok = food.get(i) == f["usda"] and all(nut.get(i, {}).get(k) == f[k] for k in want.values())
    if not ok:
        bad += 1; print("MISMATCH", f["n"])
print(len(V.VARIANT_FOODS), "rows checked,", bad, "mismatches")
raise SystemExit(1 if bad else 0)

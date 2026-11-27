# /foods table audit (food_data.FOODS, 938 rows, per 100 g)

Method (value-level only, no name or identity verification): a row is "usda_exact_values" when its kcal, protein, fat and carbs all equal one USDA SR Legacy record (2018-04 CSV, https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip). Equal values can collide across different foods, so the usda_ref column must be read before calling a row verified. "macro_kcal_mismatch" means 4p+4c+9f differs from kcal by more than 25% (fiber, polyols and alcohols can explain some). Everything else is "unverified": no source was checked.

| status | rows |
|---|---|
| usda_exact_values (values equal a USDA record, identity not checked) | 181 |
| macro_kcal_mismatch (needs a source or the doctor) | 31 |
| unverified (no source checked, mostly brand/Arabic product rows) | 726 |

Full row list with the USDA record id and name where matched: docs/foods-audit.csv.
Not changed in the candidate: no row value was edited, since no source gives the true value. The public /foods/<slug> pages use these numbers as they are.
Separate earlier finding: generic rows picked a different USDA record than a quick name match for lean beef (217 vs 174), cottage cheese (98 vs 81), whole-wheat bread (293 vs 252); not edited.

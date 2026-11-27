# Review proposal: seed p339, Thursday (90 kg male, weight loss, refeed). Not applied, not default.

Day as generated (candidate 036882d): target 1560 kcal, target protein 162 g. Stored total 1544 kcal (food sum, computed from grams), protein 79 g (flagged protein_short). Calories are within 1%; protein is 49% of the configured target.

| Item (as written) | Resolved food row | Notes |
|---|---|---|
| oats 60 g, strawberries 150 g, almonds 15 g | شوفان خام, فراولة, لوز | existing /foods rows, value-level USDA match not individually re-checked here |
| "كفتة دجاج مشوية" 230 g | "كفتة مشوية" 250 kcal, 18 g protein per 100 g (575 kcal) | Identity gap: the name says chicken, the row is a generic grilled kofta (not a chicken row, no source). The 575 kcal and ~41 g protein may be wrong in either direction. Unverified. |
| brown rice 150 g, green salad 150 g | cooked brown rice 112 kcal/100 g, salad | |
| chicken soup 380 ml, grilled vegetables 230 g | شوربة دجاج 36 kcal/100 g (2.5 g protein) | |
| kiwi 230 g | كيوي 61 kcal/100 g | |

What the existing top-up can do: protein_fix has three sources (tuna in water 100 kcal/23 g per 100 g, egg whites 52/11, grilled chicken breast 165/31 per 100 g) and adds one of them, at most 250 g, to one slot. Both lunch and dinner already contain chicken, so the chicken source is skipped as a duplicate, and one tuna or egg-white portion cannot close an 83 g gap.

Feasibility search (docs/feas339.py, grid in 10 g steps, rows from food_data.FOODS, kcal within 5% of 1560, items: oats 30-80 g, rice 60-200 g, chicken breast 0-250 g, tuna 0-200 g, egg whites 0-250 g, kiwi 0-230 g, the rest of the day fixed; the kofta is replaced by chicken breast):
- Exists, protein 162 g exactly, 1483-1488 kcal: e.g. oats 70, rice 60, chicken breast 210, tuna 200, egg whites 90, kiwi 200 (tuna 200 g and chicken 210 g in one day).
- Moderate portions (tuna <= 100 g, egg whites <= 100 g, chicken <= 250 g): best 155 g protein at 1634 kcal (+4.8% kcal).
- Chicken breast alone (no tuna or egg whites): no combination reaches the 5% kcal band in this grid.
So a balanced solution within the configured calorie band needs a heavy protein day: roughly 200-250 g chicken breast plus tuna and egg whites, and starch cut to about 60-100 g rice and 40-70 g oats.

Algorithm gap (mine to fix, once a policy is chosen): top-up adds one source to one slot and skips repeats; it cannot combine two sources or raise the meal's own protein item.
Clinician decisions needed: (1) is 162 g (1.8 g/kg) a hard target at 1560 kcal on a refeed day, or may the sheet show the shortfall; (2) may a day carry 200-250 g chicken plus tuna plus egg whites; (3) which row is "كفتة دجاج" (a sourced chicken kofta row, or reword the meal).
Source-backed alternative for the protein portion scale: USDA SR Legacy 171477 "Chicken, broilers or fryers, breast, meat only, cooked, roasted" (https://fdc.nal.usda.gov/food-details/171477/nutrients): 165 kcal and 31.02 g protein per 100 g (SR Legacy CSV). It equals the library row "صدر دجاج" 165/31, so the chicken source values are source-backed; the tuna and egg-white rows were not re-checked here. I did not change any row.

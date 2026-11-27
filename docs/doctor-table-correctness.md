# Doctor-table correctness, local candidate (not deployed)

Denominator: the 597 library meals (2067 items; 329 items state an explicit quantity). Counts are entries, not unique texts.
Three things are kept apart: source identity (the USDA description names the same food and preparation), numeric tolerance
(library value within the stated rule of the USDA value) and ingredient availability (not assessed).

## A. Default settings (proposed layer off)
- explicit quantity 329; exact identity 178; exact AND verified against USDA 7 (chia 5, almonds 2); all four macros match the independent USDA calculation for those 7.
- 2 more carry an FDC id (Baked Cod) and are not independently verified. 169 are exact but unverified (identity or preparation unstated in the library).
- Meat, chicken and rice entries whose row names no preparation are withheld (unresolved with a reason) rather than priced.

## B. Proposed layer on (NX_PROPOSED_VARIANTS=1, level B): separate from the originals, never "exact"
- 158 explicit-quantity entries priced end to end from a named USDA cooked/as-sold row: 151 proposed options plus the 7 verified originals.
- Result vs the unrounded USDA calculation (grams/100 times the USDA row): maximum absolute deviation kcal 0.5, protein 0.5, carbs 0.48, fat 0.56. This is display rounding to whole numbers, not a data difference.
- In the proposed entries the identity is the PROPOSAL's choice (for example "دجاج 120جم" becomes USDA 171477 roasted breast meat only). It is not the doctor's stated preparation and needs adoption.

## C. Reviewed originals: actual deviations (library minus USDA, per 100 g)
Rule used to accept: kcal 1.5, protein 0.5 g, carbs 0.6 g, fat 0.3 g. Tolerances are not equality; actual deviations:

| row | USDA id | USDA description | preparation | library kcal/p/c/f | USDA kcal/p/c/f | deviation kcal/p/c/f (library minus USDA) |
|---|---|---|---|---|---|---|
| أرز أبيض مطبوخ | 168878 | Rice, white, long-grain, regular, enriched, cooked | cooked | 130.0/2.7/28.0/0.3 | 130.0/2.69/28.17/0.28 | +0.00/+0.01/-0.17/+0.02 |
| صدر دجاج بالجلد مطبوخ أو مشوى | 171075 | Chicken, broilers or fryers, breast, meat and skin, cooked, roasted | cooked (roasted, meat and skin) | 197.0/29.8/0.0/7.78 | 197.0/29.8/0.0/7.78 | +0.00/+0.00/+0.00/+0.00 |
| Chicken, leg with skin Cooked | 173618 | Chicken, broilers or fryers, leg, meat and skin, cooked, stewed | cooked (stewed, meat and skin) | 220.0/24.1/0.0/12.92 | 220.0/24.17/0.0/12.92 | +0.00/-0.07/+0.00/+0.00 |
| Chicken, leg, no skin Cooked | 172381 | Chicken, broilers or fryers, leg, meat only, cooked, stewed | cooked (stewed, meat only) | 185.0/26.26/0.0/8.06 | 185.0/26.26/0.0/8.06 | +0.00/+0.00/+0.00/+0.00 |
| سمك المياس مطبوخ بالتوابل | 174229 | Fish, bluefish, cooked, dry heat | cooked, dry heat | 159.0/25.69/0.0/5.44 | 159.0/25.69/0.0/5.44 | +0.00/+0.00/+0.00/+0.00 |
| سمك عروسة البحر ( الزبيدى) | 174231 | Fish, butterfish, cooked, dry heat | cooked, dry heat | 187.0/22.1/0.0/10.28 | 187.0/22.15/0.0/10.28 | +0.00/-0.05/+0.00/+0.00 |
| سمك موسى مطهى بالحرارة | 174197 | Fish, flatfish (flounder and sole species), cooked, dry heat | cooked, dry heat | 86.0/15.2/0.0/2.3 | 86.0/15.24/0.0/2.37 | +0.00/-0.04/+0.00/-0.07 |
| سمك ماكاريل أسبانى | 173674 | Fish, mackerel, spanish, cooked, dry heat | cooked, dry heat | 158.0/23.5/0.0/6.3 | 158.0/23.59/0.0/6.32 | +0.00/-0.09/+0.00/-0.02 |
| سمك أبيض مطبوخ | 174246 | Fish, whitefish, mixed species, cooked, dry heat | cooked, dry heat | 172.0/24.47/0.0/7.5 | 172.0/24.47/0.0/7.51 | +0.00/+0.00/+0.00/-0.01 |
| روبيان مقلى | 171970 | Crustaceans, shrimp, mixed species, cooked, breaded and fried | breaded and fried | 242.0/21.3/11.47/12.28 | 242.0/21.39/11.47/12.28 | +0.00/-0.09/+0.00/+0.00 |
| سالمون مدخن | 171985 | Fish, salmon, chinook, smoked, (lox), regular | smoked as sold (lox) | 117.0/18.28/0.0/4.32 | 117.0/18.28/0.0/4.32 | +0.00/+0.00/+0.00/+0.00 |
| شيا | 170554 | Seeds, chia seeds, dried | dried seeds | 486.0/17.0/42.0/31.0 | 486.0/16.54/42.12/30.74 | +0.00/+0.46/-0.12/+0.26 |
| لوز | 170567 | Nuts, almonds | nuts, as sold | 579.0/21.0/22.0/50.0 | 579.0/21.15/21.55/49.93 | +0.00/-0.15/+0.45/+0.07 |

Quarantined, not verified: "المحار" (values equal USDA 172843 "Ostrich, oyster, cooked"); withheld with an identity reason, record untouched, regression in tests/test_basis_gate.py.

## D. Examples (entry, USDA id, grams, app result kcal/p/c/f, independent USDA result)
- proposed cooked option | 🌮 Chicken Burrito Bowl (ارز بني 100جم | 169704 100.0 g got [123, 3, 26, 1] USDA [123.0, 2.7, 25.6, 1.0]
- proposed cooked option | 🍗 دجاج 120جم | 171477 120.0 g got [198, 37, 0, 4] USDA [198.0, 37.2, 0.0, 4.3]
- proposed cooked option | 🌮 Fish Tacos (سمك 150جم | 175177 150.0 g got [192, 39, 0, 4] USDA [192.0, 39.2, 0.0, 4.0]
- proposed cooked option | 🍚 ارز 200جم | 168878 200.0 g got [260, 5, 56, 1] USDA [260.0, 5.4, 56.3, 0.6]
- proposed cooked option | 🧆 حمص 80جم | 173757 80.0 g got [131, 7, 22, 2] USDA [131.2, 7.1, 21.9, 2.1]
- proposed cooked option | 🍠 بطاطا 150جم | 168483 150.0 g got [135, 3, 31, 0] USDA [135.0, 3.0, 31.1, 0.2]
- proposed cooked option | 🍗 كبدة دجاج 120جم | 174491 120.0 g got [206, 31, 1, 8] USDA [206.4, 30.9, 1.3, 7.7]
- proposed cooked option | 🦐 جمبري 120جم | 175180 120.0 g got [119, 29, 0, 0] USDA [118.8, 28.8, 0.2, 0.3]
- proposed cooked option | 🌴 تمر 1 | 168191 8.0 g got [22, 0, 6, 0] USDA [22.2, 0.1, 6.0, 0.0]
- proposed cooked option | 🧀 جبن 60جم | 172179 60.0 g got [59, 7, 2, 3] USDA [58.8, 6.7, 2.0, 2.6]
- proposed cooked option | 🐟 Big Poke Bowl (تونة 220جم | 171986 220.0 g got [255, 56, 0, 2] USDA [255.2, 56.1, 0.0, 1.8]
- proposed cooked option | 💪 Mass Gainer Bowl (شوفان 100جم | 173904 100.0 g got [379, 13, 68, 7] USDA [379.0, 13.2, 67.7, 6.5]
- proposed cooked option | 🌰 مكسرات 20جم | 170585 20.0 g got [121, 4, 4, 11] USDA [121.4, 3.9, 4.5, 10.7]
- original, verified | 🥣 Chia Breakfast (🌱 شيا 30جم | 170554 30.0 g got [146, 5, 13, 9] USDA [145.8, 5.0, 12.6, 9.2]
- original, verified | 🌰 لوز 10جم | 170567 10.0 g got [58, 2, 2, 5] USDA [57.9, 2.1, 2.2, 5.0]
- proposed cooked option | 🫓 طعمية مشوية 3 قطع | 172455 60.0 g got [200, 8, 19, 11] USDA [199.8, 8.0, 19.1, 10.7]

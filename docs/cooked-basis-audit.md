# Cooked-basis audit of meat, fish and rice rows (read-only, no values changed)

Basis the user stated (WhatsApp 15:22 Nov 27, "لا انا عايز بعد الطبخ"): weights of meat, chicken and rice mean AFTER cooking, going forward.
This does not establish how the doctor's historic entries were written.

Method: for each of 67 food-table rows (meat, poultry, fish, rice; composite dishes excluded), list USDA SR Legacy rows within 1.5 kcal and 0.6 g protein.
Evidence: docs/cooked-basis-audit.csv. A numeric match is NOT identity: the same numbers match unrelated foods
(for example the 129 kcal rice row also matches frozen potato products). Identity below is only from the row's own English name where it names a preparation.

## Source-verified by name (the row's English name states the preparation, and a USDA row of that name exists)
- Rice, white (cooked) 130: USDA 168878 long-grain enriched cooked is the intended row. Basmati and jasmine rows name "cooked".
- Brown rice cooked 111-112: name says cooked (USDA 169704).
- Tilapia cooked dry heat (steamed or baked) 121: USDA 175177 is the nearby row. Grilled/baked tilapia rows name preparation.
- Chicken breast no skin cooked/grilled 165-166: name says cooked. USDA 171477 roasted.

## Numeric resemblance only (name has no preparation; do NOT call raw or cooked)
- Ground chicken 143 / 17: resembles USDA raw 171116 (143 / 17.4). Cooked crumbles 171117 is 189 / 23.3.
- Ground beef 90/10 176 / 20 resembles raw 174030. Ground beef 80/20 254 / 17 resembles raw 174036.
- Lean beef 217 / 26 resembles cooked 90/10 broiled patty 174031 (217 / 26.1). Name "lean beef" gives no preparation or cut.
- Lamb 294 / 25 resembles a USDA lamb composite row (172480). Preparation not read from the name.
- Ground veal 144 / 20, camel 160 / 21, beef tenderloin 188 / 26, beef shank 201 / 29, thigh 209 / 26, wings 203 / 30, turkey breast 135 / 30,
  sea bass 124 / 23: no clean USDA identity found by this method. Unresolved.
- Rows whose names say fried or smoked (mullet fried, sea bass fried, smoked turkey) still collide numerically with unrelated raw rows. That shows the method cannot assign raw vs cooked from numbers.

## Recommendation (preparation choices for the user to review, no USDA row picking)
For each food, one sentence in the user's terms. Anything not answered stays unresolved and is not priced:
1. Ground chicken / ground beef / veal: "weights are after cooking, pan-cooked (crumbled) or grilled patty". Recommended default: grilled or pan-cooked patty.
   Until then these rows stay as written and are labeled as possibly raw-basis estimates.
2. Chicken breast, turkey breast, tilapia, other fish: "after cooking, dry heat (grilled or baked), no breading". Recommended default: grilled/baked.
3. Rice: "after cooking, boiled plain, no oil or ghee". Egyptian rice with ghee and other prepared rice dishes need their own recipes.
4. Lamb, camel, beef cuts: unresolved, need the cut and preparation. No default recommended.
5. Kofta: separate, no cooked yield sourced (see chicken-kofta-proposal.md).

# NutraX accuracy: defect ledger (candidate, not a completion claim)

Candidate: branch work/accuracy, on top of main 37a2cfd. Nothing pushed or deployed. Counts, not accuracy percentages.

## 1. What is verified, proposed, unverified (kept separate)

| Class | What | Source / status |
|---|---|---|
| Verified generic foods | USDA-sourced rows used by the computed path (raw rice 168877, dry pasta 169736, plus existing generic /foods rows) | 181 of 938 /foods rows equal a USDA SR Legacy record by value; identity not checked by hand except ~40 generic rows (34 exact, 3 differ by record choice) |
| Proposed (not applied) | Standard portions: rice, bread, milk, salad plate (docs/proposed-standard-portions.md); composites (docs/proposed-composites.md) | USDA household measures; need the user's approval; never counted as repaired |
| Unverified | 726 /foods rows; 31 value mismatches (docs/foods-audit.csv); brand rows (Chocorite x2, Diet Jelly, Burger King strips, Advantage Chocolate, coconut water, vanilla 288 vs 53, ACV) | no source |
| Doctor-written meals | 597 unique base meals (1125 entries is a separate denominator) | 308 incomplete, 280 default-portion only, 9 all-explicit (5 of those differ >25% from the written kcal). Per-meal rows: library_audit.csv |

## 2. Experimental heuristics (no clinical or user source, not validated)
- portion_scale ceilings: 300 g solids, 350 g vegetables/salad, 500 ml liquids. Placeholders, OFF by default (NX_PLAUSIBILITY_CAPS=1 enables the experimental variant; its tests set the flag). Without them the portion_scaling run shows 67 computed days, 5 more than 5% off, worst 16%; with them 22 unmet, worst 30%. The portion policy is the user's choice.
- Day target "unmet" label at 5% is an engineering line, not a clinical tolerance.
- 0.95 g/kg protein floor: internal tripwire only; user-facing protein uses the day's own target_p.
- Alternate-selection retry cap of 3 (unmet days stay reported).

## 3. Remaining failures in the candidate
- Unmet computed days remain, by design reported not hidden: portion_scaling run shows 52-61 computed days with 16-22 more than 5% off, worst 30-33%. High targets (bulking, 2-meal) cannot be reached under the ceilings. Example: bulking / intermittent_16_8 target 3300 gets 3032 (8%). Pinned: PINNED_UNMET seeds 0,1,9,18,20,25,26,29 (test_computed_scaling), PINNED_UNRESOLVED seed 96 (95 kg strong-deficit, Tuesday, 90 g, flagged protein_short).
- Failing tests I did not edit away: test_portion_scaling::test_every_system_lands_on_its_calorie_target (Postgres run, bulking 16:8, 8%; passed in the sqlite run, time-seeded); test_child_program_guard::test_an_ordinary_sheet_carries_no_extra_line_at_all (see 4).
- Meal composition still odd in places: tuna plus chicken breast in one meal, 4-egg and large fish meals. Caps do not fix this.
- 308 incomplete library meals (bare emoji items, bread/milk with no unit): top items salad emoji 51, bread emoji 38, "خبز 2" 19, plain milk 17, plain laban 12. Real fix needs approved explicit recipes. Composites with no USDA record (shawarma, mandi and others) stay unsourced.
- Plain "حليب" fat level, and whether recomputed numbers display over doctor-written ones: user decisions.
- /foods: 726 unverified rows, 31 mismatches, brand rows above. No row edited.

## 4. PDF and the sheet rule
- Rule as recorded in the repo: printed client sheet = name, table, allowed/forbidden only; clinical numbers and warnings go to the specialist preview (data["sheet_notes"]) before delivery. Source: git commits d7a472c (2026-10-12, quotes the doctor: "عايز شكل الورقة النهائي يكون كده، مفهوش أي إضافات غير إيه الممنوع والمسموح بالنسبة للحالة فقط") and 7f91284 (2026-10-13, "شيل كل حاجة ما عدا اللي قلته"). Scope: all plans' client sheet, not child-only. The child-program line is a separate existing exception (alert only when there is a reason). This is repo-recorded wording by an earlier author, not an original message found on the user's channel with Instinct; I found no later resolution.
- Candidate behaviour: the calorie-basis notes (estimate days, days over 5% off the target, protein below the day's target) go to the preview notes (rendered, doctor view screenshot attached). The printed sheet stays rule-compliant. Printing them is opt-in (NX_PDF_BASIS_FOOTNOTE=1), not default.
- Open user decision: should the printed sheet carry a basis note even though the doctor asked for no additions? Nearly every plan has estimate days, so it would appear on almost every sheet.

## 4b. Meal composition (measured, 30 seeded weeks, 630 breakfast/lunch/dinner meals, standard test profile)
- Two protein families in one meal (e.g. fish + chicken, tuna + chicken): 141 meals on the candidate, 156 on main 37a2cfd. Cause is main's protein_fix design: only three top-up sources (tuna, egg whites, grilled chicken) rotated onto the meal. My guard removes a top-up that repeats the meal's own protein; it does not stop a different second protein.
- Protein item above 250 g: 121 (candidate) vs 132 (main). Meals with 4 or more eggs: 110 vs 100.
- Not repaired: changing top-up sources or composition is a nutrition-design choice for the user.

## 5. Test matrix at the final commit (see git head)
| Suite | Result |
|---|---|
| sqlite, 82 files | fail only test_accessibility, test_db_connection, test_report_reading (same as main). test_medical_filtering times out at the 60 s batch cap but passes 70/70 alone (about 80 s). |
| Fresh Postgres, 82 files | 22 fail: the 21 SQLite-only-SQL files shared with main, plus test_followup_history_flow in the shared batch DB only (its own seed asserts exactly 3 visits, so earlier tests' rows break it). Alone on a clean Postgres DB it passes, and on SQLite. Its raw `datetime('now', ?)` UPDATE was a test-portability defect and is fixed (timestamp computed in Python). Not a production history failure. |
| Pinned fixtures | PINNED_FIXED (protein floor holds), PINNED_UNRESOLVED (95 kg seed 96 Tuesday, plus 90 kg male refeed seeds 339 Thu, 351 Mon, 393 Sun, 401 Mon, 573 Thu), PINNED_UNMET seeds 0,1,9,18,20,25,26,29 |

## 6. Protein 84 g vs 162 g target (found, partly fixed)
- Profile: ذكر 90 كجم، تخسيس، refeed, target_p 162, target_cal 1560 on the day. Scan of 640 seeds (p60-p699) x 7 days = 4480 days: 6 days under 0.95 g/kg (77-85 g), calories met within 2.5%, basis items (computed from grams). Seeds: 216, 339, 351, 393, 401, 573.
- Cause found: my duplicate-protein guard dropped the top-up when the rotating source repeated the meal's own protein, and gave up instead of trying the other sources; lunch is chicken kofta and dinner chicken soup. Fixed: it now tries every source and skips only a repeat. Seed 216 now reaches 168 g via the alternate week. Rescan: 5 days remain (339, 351, 393, 401, 573), 77-85 g against 162 g (about -50%).
- Why the rest stay: every feasible top-up for those days repeats the chicken already in the meal, and the alternate weeks that fix the day turn other computed days into label estimates (the guard against trading computed for estimate days rejects them, and the shifted day itself becomes an estimate). They are flagged protein_short with the target and computed protein displayed. Not repaired. Feasible next work: raise the meal's own protein portion with its sourced macros instead of adding a second protein, or add more top-up sources. Both are nutrition design choices.
- The earlier one-off failure (84 g seed unknown, same profile) was one of these.

## 7. Identity gap and the three flags (supersedes the computed-coverage numbers above)

What "computed" means now: calculated from the matched table row. It is not source-verified.
Each priced item carries three independent flags:
- explicit_quantity: the text states grams, a count or ml.
- exact_identity: the table row's own name is in the text. A generic bridge is not exact
  ("جبنة" -> cottage cheese, "لحم" -> lean beef, "لبن" -> laban rayeb, bare "زبادي" -> fat-free,
  "خبز" -> brown bread, "بطاطس" -> boiled). Only "بيضة/بيض" -> whole egg is allowed as an alias.
- sourced: the row has a USDA FDC id (meal_food_sources). Unsourced library rows are table values only.
A meal is `exact` only when every item is priced, explicit and exact. `all_sourced` is separate.
Raw/dry/whole-grain words are state words, not formatting: they must be in the matched row's name.

Where the flags are used: day_calc basis, computed_meal (scaling), client progress rings, snack
option numbers, swap/edit refresh ("estimated"), stored totals, doctor chip, PDF basis note.

Counts, 597 unique base meals (the 1125 entries were not re-run):
- not priced at all (identity gap, dish, composite, unit, variant, no row): 437+ of 597 (308 before the identity rule)
- priced from a table row: 160; exact (explicit + exact identity): 1; all items USDA-sourced: 0.
- Item level (2067 items): 579 exact-name rows, 269 identity-unresolved, 244 no row, about 1037 priced items
  without a stated quantity. Largest bridges: bread 150, salad 85, rice 78, cottage cheese 75,
  frozen vegetables 58, chicken 41, sweet potato 40, chickpeas 36, honey 30, dates 29.
- Generated weeks (40 seeds x 7 days, CASES data): days with basis "items": 129 before the identity
  work, 0 now (280 label days). 211 of 560 slots are blocked by a generic identity, 45 by a default portion.
  Result: computed scaling never applies to library meals. Generated days are label estimates.
- Protein misses on the 5 pinned refeed seeds are NOT resolved. The scan shows 0 bad computed days only
  because no day is computed now.

Tests: test_identity_pairs, test_three_flags (new), test_food_identity (12; one test used to sit after the
runner and never ran). Two food_identity tests accept either unresolved reason. Fixtures that used bare
"زبادي" now name the fat level.

p339 proposal (docs/p339-review-proposal.md) used unsourced kofta values: unverified. Do not use it as a
nutrition proposal.

Next library work (not authorized as done): state quantities and exact variants for the top bridged
foods; sourced standard recipes proposed for review (grams + URL, kept apart from the doctor-written meals);
unverified branded rows.

## 8. Denominators and final test matrix (head recorded in the report)

Denominators re-run on the current code. The earlier "1125 entries" could not be reproduced from the code,
so it is not used. Two reproducible universes:
- Doctor-written library (meal_database lists): 600 entries, 597 unique. Priced from a table row 162 / 160;
  exact (stated quantity + exact name) 1 / 1; all items USDA-sourced 0 / 0; not priced 438 / 437.
  Items without an exact basis: 1656 with no stated quantity, 882 bridged to a generic row (entries).
- Library plus meal_extra additions (what generation can draw from): 1591 entries, 941 unique. Priced 663 / 306;
  exact 177 / 47; all USDA-sourced 0 / 0; not priced 928 / 635.
  Not-priced item reasons (entries): identity 735, no row 156, variant 42, composite 35, unit 34, dish 22.
Counts only. "Exact" means calculated from a matched table row with a stated quantity, not source-verified.

Postgres, fresh DB, 84 files: 11 fail. Each file was re-run on its own fresh DB, on main (/tmp/fa_main) and on
the candidate:
- Fail the same way on both (pre-existing, not from this work): test_accessibility (hard-coded RTL in a template),
  test_db_connection (8 asserts, connection-pool tests), test_messages_page (SQLite AUTOINCREMENT SQL),
  test_money (SQLite "INSERT OR" SQL), test_plan_link (NUL character in a string literal), test_report_reading
  (missing module for the corrupt-upload test), test_speed (core.get_db missing).
- Pass on both when each has its own fresh DB, so they failed in the batch only through shared DB state:
  test_admin_dashboard, test_plan_editing, test_translation.
- test_medical_filtering: not an assertion failure. 70/70 pass alone on SQLite and Postgres (74-80 s); the batch
  runner kills it at 60 s (rc 124). test_child_protein: same, 19/19 alone (62 s).
22 -> 11: the earlier run (nx_fin4) reused a database that earlier test files had already written to (admin password,
row counts, saved plans), so 11 more files failed on state. The later run used a fresh database. Same test files,
different harness state. Test selection did not change.
SQLite (84 files): 4 fail in the batch: test_accessibility, test_db_connection, test_report_reading (same on main)
and test_medical_filtering (timeout only).

Proof pixels for the final candidate (after the three-flag change): f3_client_desk.png, f3_client_mob.png,
f3_doctor_preview_desk.png, f3_doctor_preview_mob.png, f3_pdf-1.png (real CSS, RTL, headless Chrome; PDF page
rendered with pdftoppm). Sample plan: all 7 days are label estimates; the client sees the 1400 target and the
"estimates" note; the doctor preview shows "تقدير من الوصف" chips and a basis note.

## 9. Proposed-variant review layer (separate, off by default)

meal_proposed.py + NX_PROPOSED_VARIANTS=1. A bridged generic phrase is priced from ONE chosen USDA SR Legacy variant
(generated from the CSV, FDC ids in the file), and a missing quantity from the USDA household portion. Items are flagged
proposed (+ original_food, proposed_qty). They are never `exact`, never original, never verified. Originals and records are
untouched; with the flag off nothing changes (test_proposed_layer, 5 tests).
Rows: whole-wheat bread slice 172688, cottage 2% 172182, baked sweet potato 168483, chickpeas 173757, honey 169640,
medjool date 168191, roasted chicken breast 171477.
Coverage, reported separately (library + meal_extra: 1591 entries / 941 unique):
- Original exact: 177 / 47. Priced from a table row: 663 / 306.
- Exact if the proposals are accepted: 233 / 84 (uses a proposed row or quantity: 478 / 422 meals).
- Biggest remaining blockers among priced unique meals: salad 88, cooked white rice 54, frozen mixed vegetables 36,
  tilapia 27, brown rice 15, oil 11, fat-free yoghurt 10, lean beef 10, oats 9. Unpriced meals (identity, dish, composite)
  need standard recipes.
The generation path (day_calc, scaling, protein) still reads `exact` only, so it is unaffected by the layer.

## 10. Proposed layer extended and measured (flag NX_PROPOSED_VARIANTS=1, off by default; supersedes the section 9 coverage numbers)

Rows added (USDA SR Legacy FDC ids in meal_proposed.py, generated from the CSV): white rice 168878, brown rice 169704, mixed frozen
vegetables 170472, tilapia 175177, olive oil 171413, oats 173904, mixed nuts 170585 (only for the phrase "مكسرات"), tuna 171986,
falafel 172455, cottage creamed 172179 (matches the library's own value), bread slice 172688.
Two are not plain USDA rows: the salad is a PROPOSED mix (50% romaine 169247 + 25% tomato 170457 + 25% cucumber 168409, by weight, no
dressing, PROPOSED 100 g portion); "كفتة دجاج" is priced with plain cooked ground chicken 171117 as a PROXY (no spices, onion or binder).
Household portions come from the exact USDA preparation. Caveats stored per row: sliced commercial bread is not local baladi bread;
USDA cottage cheese is not necessarily local qareesh; falafel piece weight is the library's, not USDA's.

Library values that differ from the USDA row they most resemble (not changed): bread 293 vs 252 kcal, brown rice 112 vs 123, frozen
vegetables 55 vs 65, oats 389/17 g vs 379/13.15 g, lean-beef-kofta row 250/18 g vs plain cooked ground chicken 189/23.3 g.

Coverage, original vs proposed (1591 entries / 941 unique): original exact 177 / 47. Exact if the proposals are accepted 475 / 205
(uses a proposed row or quantity in 928 / 668). Separate counts, never mixed.
Generated weeks (40 seeds x 7 days = 280 days, 560 slots): original basis "items" 0 days. Proposed-exact: 37 days (13%), 223 slots.
Among those 37, computed calories vs the day target range from -32.6% to +10.4%: scaling does not run on proposed values, so these days
still miss the target.
Pinned refeed days (target 1560 kcal / 162 g protein), computed with proposed values:
339 Thu 1270 kcal / 79 g; 393 Sun 1212 / 85 g; 573 Thu 1648 / 149 g; 351 Mon and 401 Mon are blocked by "لوز نيئ" (raw word not in the
almond row name, so the identity check leaves it unresolved). Protein is still short by 13 to 83 g on the days that compute.
Not a repair: the proposed values are not the doctor's meals and none is accepted for use.

## 11. Proposed levels, proxies excluded (supersedes the coverage numbers in sections 9 and 10)

Levels, all behind NX_PROPOSED_VARIANTS=1; the generator also needs NX_PROPOSED_LEVEL=A|B. With the flags off nothing changes
(baseline and flag-off tests pass).
- Original exact: stated quantity + exact table name.
- A (source-matched): original-exact or a per-100g replacement with one chosen USDA variant (kind "variant") and a stated quantity.
  A proposed household portion also counts but is reported separately (proposed_qty).
- B: A plus the deliberately specified new salad recipe (kind "new_recipe"), tested as a new recipe, not as the original salad.
- Proxy (kind "proxy": plain cooked ground chicken standing in for chicken kofta): in neither level. It is an identity mismatch.
Nutrient replacements (per 100 g) and portion proposals are separate flags. A replacement variant is a choice, not recovered truth:
matching an old library number does not establish the variant (cottage creamed and tuna were chosen that way and still need the
user's pick).

Coverage (1591 entries / 941 unique): original exact 177 / 47. A: 387 / 140 (of 140 unique: 93 rely only on a stated quantity with a
replaced row, 0 rely on a proposed portion). B: 453 / 199. Meals using the kofta proxy (excluded): 22 / 6.
Generated weeks, 280 days, scaling running on the allowed levels:
- Flags off: 0 days computed.
- Level A: 19 days computed (6.8%); calorie gap vs target -10.2% to +1.6%; 4 of 19 outside 5%.
- Level B: 35 days computed (12.5%); same range; 9 of 35 outside 5%.
Pinned refeed days (target 1560 kcal / 162 g protein): all five have lunch blocked by the kofta proxy, so none computes at any level.
Stored (label) protein on those days: 339 Thu 114 g, 351 Mon 108 g, 393 Sun 136 g, 401 Mon 162 g, 573 Thu 156 g. Computed with the proxy
(not claimed): 79, 99, 85, 148, 149 g. Clinical appropriateness of any protein number is not settled by meeting it.
No portion caps are on. Blockers named: chicken kofta needs a specified recipe; "لوز نيئ" stays unresolved (state word not in the row name).

## 12. Cooked-weight basis gate and unresolved-entry list (local, 27 Nov 15:44)
- User rule (WhatsApp 15:22): meat, chicken and rice weights mean AFTER cooking. This is the basis going forward, not proof of how historic entries were written.
- meal_macros.BASIS_UNVERIFIED: three rows whose values equal a USDA raw row (ground chicken 171116, ground beef 90/10 174030, 80/20 174036) and whose names state no preparation are unresolved ("basis:"), not exact. Resemblance, not proof. NX_BASIS_STRICT=0 restores the old behaviour. Original-exact coverage is unchanged (177 entries / 47 unique).
- plan_engine.day_calc slots carry "entries" (text, reason code); templates/_day_calc.html lists them under the estimate note (up to 8, Arabic and English). Codes: basis, identity, qualifier, variant, composite, unit, noquantity, generic, nofood.
- Provenance: 0 of 938 food-table rows carry an FDC id, so "sourced" is False everywhere in the original table. Names alone do not validate nutrients.
- Tests: tests/test_basis_gate.py (5). Pixels: /downloads/f4_entries_desk.png, f4_entries_mob.png (client page, RTL).

## 13. Basis rule for all meat, poultry, fish and rice rows (local, 27 Nov 15:49)
- meal_macros.basis_of(row) classifies single-food rows in scope (cat meat, poultry, fish, and rice) from the row's own names: cooked, prepared (canned, smoked, cured, dried), raw, unknown. Dishes, soups, sausages, salads, flours are out of scope. Only cooked and prepared qualify under the cooked-weight rule; raw and unknown rows make the item unresolved ("basis:"), the total partial. An explicit raw word in the text ("نيء", "خام") accepts a raw row.
- food_provenance.MATCHES: 21 rows whose names state no preparation have exactly one USDA SR Legacy row with the species name and kcal/protein/fat equal (kcal within 2, protein within 0.8 g, fat within 0.6 g). USDA states the preparation, so it sets the row's basis (8 cooked, 13 raw). This is a candidate match, not reviewed verification: it never sets "sourced".
- A label qualifies basis only. It does not validate nutrients and does not set sourced.
- Client page: one concise warning naming all causes (amount, name, cooking method). Doctor preview and saved-plan view: the per-entry reasons.
- Measured: original exact unchanged at 177 entries / 47 unique. Level A 381 / 134 (was 387 / 140), Level B 444 / 191 (was 453 / 199). 280 generated days: Level A 19, Level B 35 computed, same as before.
- Fixture changes with comments: three_flags dinner uses a cooked fish row (salmon row = USDA raw row); the lean-beef bridge is now unresolved by basis (either way not exact); meal_macros covered floor 150 -> 140 (measured 146).

## 14. Basis gate: runtime rule corrected, and an UNRESOLVED REGRESSION record (15:54)
- Correction to section 13: food_provenance matches no longer promote anything. An unreviewed COOKED candidate leaves the row unresolved ("basis:candidate cooked match USDA <id>, not yet reviewed"). An unreviewed RAW match only withholds (demotes). REVIEWED_MATCHES in meal_macros is empty: nobody has reviewed any candidate. NX_BASIS_ACCEPT_MATCHES=1 simulates a review; it is an experiment switch and is off by default.
- Precise preparation labels: canned, smoked, cured and dried are kept as their own labels, not called cooked. They qualify only as as-sold weights (no cooking step applies); that is a rule choice for review, not a source fact.
- With NX_PROPOSED_VARIANTS=1 a row that has a proposed USDA variant named cooked is not decided by the library row's basis (the variant row names its own preparation and FDC id).
- REGRESSION, unresolved: coverage of the 597 doctor-library meals (tests/test_meal_macros.py measure). Fully covered meals: 160 with the basis gate off; 146 with the 8 cooked candidate matches treated as reviewed; 107 by default (unreviewed). Average covered share 0.678 / 0.664 / 0.628. The default values are below the old floors (average 0.65, full 150). The test passes only because it runs with the review switch on; I lowered its full-meals floor 150 -> 140 under that switch. Real default coverage will stay lower until someone reviews the candidate matches (8 cooked rows: chicken breast, chicken liver, tilapia, sea bass, mullet, shrimp, crab, lobster) and the 21 unknown rows. This regression is an intended consequence of the cooked-weight rule, not fixed.
- Fixtures: nine suites set NX_BASIS_ACCEPT_MATCHES=1 with a comment because they test other behaviour with rows like "صدر دجاج مشوي".

## 14b. Update 27 Nov 16:02 (default settings, no simulated-review switch)
- Removed NX_BASIS_ACCEPT_MATCHES and REVIEWED_MATCHES. An unreviewed cooked candidate leaves a no-preparation row unresolved. Default tests no longer need a switch.
- INTENTIONAL coverage reduction (unresolved regression): library meals fully covered 150 -> floor 100 (measured 107); average coverage 0.65 -> floor 0.62 (measured 0.628). Cause: meat, poultry, fish and rice rows with no stated preparation are now unresolved. Not repaired. Fix path: source-backed cooked options (proposed layer) or the doctor's own preparation.
- Fixtures that used "صدر دجاج مشوي" / "سمك بلطي مشوي" now use cooked-named rows ("دجاج مشوى", "سمك بلطى مشوى او بالفرن"); expected numbers unchanged.
- Correction: 7 of 945 library rows carry an FDC id (earlier "0 of 938" was wrong for the full table). 5 of the 7 are not independently verified.
- food_provenance.REVIEWED: 13 rows reviewed against the USDA description and all four macros (rule: kcal<=1.5, protein<=0.5, carbs<=0.6, fat<=0.3 per 100 g). Only these set "sourced". Fava beans failed (carbs 0.65 off).
- Defect, not fixed: library row "المحار" (159/28.8/0/3.97) equals USDA "Ostrich, oyster, cooked" 172843, likely a mislabelled ostrich cut.
- Measured over the 597 library meals (2067 items): explicit quantity 329; exact identity + explicit quantity 178; of those exact and verified-source 7 (chia 5, almonds 2); macros correct vs independent USDA expectation (kcal, protein, carbs, fat) 7 of 7; FDC id only, not verified: 2 (Baked Cod); exact but source unverified 169.
- Doctor preview mobile (420 px): the meal row was wider than the card, so the swap/move buttons clipped at the left edge; the move arrow also had no button style. Fixed (wrapping buttons row under the text, .move-btn styled).

## 14c. 16:05 additions
- Quarantine: "المحار" withheld with an identity reason (food_provenance.QUARANTINE); record unchanged; regression test in test_basis_gate. Not mapped to seafood or ostrich.
- Proposed layer: added cooked options for chicken liver 174491, sea bass 173694, mullet 175124, shrimp 175180, crab (alaska king, moist heat) 174202, lobster 174209. Fixed a hole: with the layer on, an explicit amount of a no-preparation row was kept as an exact original; it is now swapped to the named cooked option (proposed, never exact).
- docs/doctor-table-correctness.md: counts, actual deviations, examples.

## 14d. 16:16 review options and full suite (sqlite, 87 test files)
- New: meal_option_foods.py, 8 named source-backed cooked options (name carries the USDA id). They match only when the written text contains the full name. The doctor preview and saved-plan view offer one beside a "basis" entry; the preview has a "use this option" button that edits only that entry in the draft (/edit_meal). Original text and stored records are untouched until pressed. No automatic replacement. Test: tests/test_option_adoption.py.
- Full suite: 1263 passed, 14 failed in 6 files. Baseline (37a2cfd) also fails: test_accessibility (1), test_db_connection (needs Postgres), test_report_reading (1). Mine, fixed: shopping_list (basis-unresolved items keep their written amount, as before), week_progress (cooked-named fixture), three_meals.
- REGRESSION (unresolved): test_three_meals dinner-share check now measures only fully calculated days, 1 of 7. Weaker than before; not repaired. Liver ("كبدة" -> beef liver, no preparation) is withheld by the cooked-weight rule; the test now asserts the withholding.

## 14e. 16:26 representative day, surfaces, dinner-share
- test_three_meals dinner-share restored: invariant unchanged (dinner <= 30% of a fully calculated day) on every fully calculable generated day (15 goal/weight variants, seeded), plus an explicit fixture for the DINNER_HALF mechanism, plus a SEPARATE test that counts incomplete days (98 of 105 generated days are incomplete under the default rule, 7 calculable; only those 7 are claimed to pass).
- REVIEWED widened from 13 to 29 rows (second pass: lentils, chickpeas, whole and skim milk, whole-milk yogurt, olive oil 171413, cucumber, tomato, carrot, broccoli, apple, banana, strawberries, avocado, two lettuces). Rejected on identity or tolerance: boiled potato (with-salt variant), white cheese (queso blanco is not Egyptian white cheese), cottage cheese (creamed not stated), peanut, fava (carbs 0.65), tuna, bread, Greek yogurt (fat level not in name), eggs (raw vs boiled not stated; a named hard-boiled option row 173424 was added). Rounding rule: a library value stored as a whole number gets half a unit.
- Calc line now shows protein, carbs and fat next to kcal (preview, saved plan, client page). PDF intentionally carries no analysis: it is the written table only.
- Tests: test_representative_day (independent USDA calculation, 11 items, whole day), test_surfaces (preview, save, reopen saved, client link, PDF 200, adopted option persists).

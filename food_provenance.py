# -*- coding: utf-8 -*-
"""Source MATCHES for table rows whose own name states no preparation.

A match = the English species name is in the USDA SR Legacy description AND the row's kcal, protein and fat equal that one USDA row
(kcal within 2, protein within 0.8 g, fat within 0.6 g) AND exactly one USDA row qualified. USDA states the preparation.
It qualifies the BASIS of the row (raw or cooked) only. It is a candidate match from numbers plus species name, NOT a reviewed
verification of the library value, so it never sets "sourced". Generated 27 Nov 2026 from the USDA SR Legacy 2018-04 CSV;
see docs/cooked-basis-audit.md. Format: row name -> (FDC id, USDA description, state).
"""

MATCHES = {
    'صدر دجاج': ('171477', 'Chicken, broilers or fryers, breast, meat only, cooked, roasted', 'cooked'),
    'دجاج مفروم': ('171116', 'Chicken, ground, raw', 'raw'),
    'كبدة دجاج': ('174491', 'Chicken, liver, all classes, cooked, pan-fried', 'cooked'),
    'قوانص دجاج': ('171456', 'Chicken, gizzard, all classes, raw', 'raw'),
    'سمان': ('172419', 'Quail, meat only, raw', 'raw'),
    'حمام': ('171079', 'Squab, (pigeon), meat only, raw', 'raw'),
    'لحم بقري مفروم 90/10': ('174030', 'Beef, ground, 90% lean meat / 10% fat, raw', 'raw'),
    'لحم بقري مفروم 80/20': ('174036', 'Beef, ground, 80% lean meat / 20% fat, raw', 'raw'),
    'سمك بلطي': ('175177', 'Fish, tilapia, cooked, dry heat', 'cooked'),
    'سلمون': ('175167', 'Fish, salmon, Atlantic, farmed, raw', 'raw'),
    'ماكريل': ('175119', 'Fish, mackerel, Atlantic, raw', 'raw'),
    'سمك قاروص': ('173694', 'Fish, sea bass, mixed species, cooked, dry heat', 'cooked'),
    'بوري': ('175124', 'Fish, mullet, striped, cooked, dry heat', 'cooked'),
    'جمبري': ('175180', 'Crustaceans, shrimp, cooked', 'cooked'),
    'كابوريا': ('174202', 'Crustaceans, crab, alaska king, cooked, moist heat', 'cooked'),
    'جراد البحر': ('174209', 'Crustaceans, lobster, northern, cooked, moist heat', 'cooked'),
    'قلوب فراخ': ('171458', 'Chicken, heart, all classes, raw', 'raw'),
    'بلطي فيليه': ('175176', 'Fish, tilapia, raw', 'raw'),
    'بلح البحر': ('174216', 'Mollusks, mussel, blue, raw', 'raw'),
    'Chicken thigh, no skin': ('173627', 'Chicken, broilers or fryers, dark meat, thigh, meat only, raw', 'raw'),
    'سمك أنشوجة': ('174182', 'Fish, anchovy, european, raw', 'raw'),
}


# REVIEWED: rows checked by the agent against the primary USDA SR Legacy row (identity, preparation and edible part from the
# USDA DESCRIPTION, then all four macros). Rule: |kcal|<=1.5, |protein|<=0.5 g, |carbs|<=0.6 g, |fat|<=0.3 g per 100 g (half a unit when the library value is stored as a whole number).
# This is an agent review, not a doctor or user certification. Only these rows set "sourced". Candidate MATCHES above never do.
# Format: row name -> (FDC id, USDA description, preparation, kcal, protein, carbs, fat) per 100 g.
REVIEWED = {
    'أرز أبيض مطبوخ': ('168878', 'Rice, white, long-grain, regular, enriched, cooked', 'cooked', 130.0, 2.69, 28.17, 0.28),
    'صدر دجاج بالجلد مطبوخ أو مشوى': ('171075', 'Chicken, broilers or fryers, breast, meat and skin, cooked, roasted', 'cooked (roasted, meat and skin)', 197.0, 29.8, 0.0, 7.78),
    'Chicken, leg with skin Cooked': ('173618', 'Chicken, broilers or fryers, leg, meat and skin, cooked, stewed', 'cooked (stewed, meat and skin)', 220.0, 24.17, 0.0, 12.92),
    'Chicken, leg, no skin Cooked': ('172381', 'Chicken, broilers or fryers, leg, meat only, cooked, stewed', 'cooked (stewed, meat only)', 185.0, 26.26, 0.0, 8.06),
    'سمك المياس مطبوخ بالتوابل': ('174229', 'Fish, bluefish, cooked, dry heat', 'cooked, dry heat', 159.0, 25.69, 0.0, 5.44),
    'سمك عروسة البحر ( الزبيدى)': ('174231', 'Fish, butterfish, cooked, dry heat', 'cooked, dry heat', 187.0, 22.15, 0.0, 10.28),
    'سمك موسى مطهى بالحرارة': ('174197', 'Fish, flatfish (flounder and sole species), cooked, dry heat', 'cooked, dry heat', 86.0, 15.24, 0.0, 2.37),
    'سمك ماكاريل أسبانى': ('173674', 'Fish, mackerel, spanish, cooked, dry heat', 'cooked, dry heat', 158.0, 23.59, 0.0, 6.32),
    'سمك أبيض مطبوخ': ('174246', 'Fish, whitefish, mixed species, cooked, dry heat', 'cooked, dry heat', 172.0, 24.47, 0.0, 7.51),
    'روبيان مقلى': ('171970', 'Crustaceans, shrimp, mixed species, cooked, breaded and fried', 'breaded and fried', 242.0, 21.39, 11.47, 12.28),
    'سالمون مدخن': ('171985', 'Fish, salmon, chinook, smoked, (lox), regular', 'smoked as sold (lox)', 117.0, 18.28, 0.0, 4.32),
    'شيا': ('170554', 'Seeds, chia seeds, dried', 'dried seeds', 486.0, 16.54, 42.12, 30.74),
    'لوز': ('170567', 'Nuts, almonds', 'nuts, as sold', 579.0, 21.15, 21.55, 49.93),
}
# second review pass (16:23): common supported items, same rule
REVIEWED['عدس'] = ('172421', 'Lentils, mature seeds, cooked, boiled, without salt', 'cooked, boiled, without salt', 116.0, 9.02, 20.13, 0.38)
REVIEWED['حمص مسلوق'] = ('173757', 'Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, without salt', 'cooked, boiled, without salt', 164.0, 8.86, 27.42, 2.59)
REVIEWED['حليب كامل الدسم'] = ('172217', 'Milk, whole, 3.25% milkfat, without added vitamin A and vitamin D', 'whole milk, as sold', 61.0, 3.15, 4.78, 3.27)
REVIEWED['حليب خالي الدسم'] = ('171269', 'Milk, nonfat, fluid, with added vitamin A and vitamin D (fat free or skim)', 'nonfat milk, as sold', 34.0, 3.37, 4.96, 0.08)
REVIEWED['زبادي كامل الدسم'] = ('171284', 'Yogurt, plain, whole milk', 'plain whole-milk yogurt, as sold', 61.0, 3.47, 4.66, 3.25)
REVIEWED['زيت زيتون'] = ('171413', 'Oil, olive, salad or cooking', 'olive oil, as sold', 884.0, 0.0, 0.0, 100.0)
REVIEWED['طماطم'] = ('170457', 'Tomatoes, red, ripe, raw, year round average', 'raw', 18.0, 0.88, 3.89, 0.2)
REVIEWED['خيار'] = ('168409', 'Cucumber, with peel, raw', 'raw, with peel', 15.0, 0.65, 3.63, 0.11)
REVIEWED['جزر'] = ('170393', 'Carrots, raw', 'raw', 41.0, 0.93, 9.58, 0.24)
REVIEWED['بروكلي'] = ('170379', 'Broccoli, raw', 'raw', 34.0, 2.82, 6.64, 0.37)
REVIEWED['تفاح'] = ('171688', "Apples, raw, with skin (Includes foods for USDA's Food Distribution Program)", 'raw, with skin', 52.0, 0.26, 13.81, 0.17)
REVIEWED['موز'] = ('173944', 'Bananas, raw', 'raw', 89.0, 1.09, 22.84, 0.33)
REVIEWED['فراولة'] = ('167762', 'Strawberries, raw', 'raw', 32.0, 0.67, 7.68, 0.3)
REVIEWED['أفوكادو'] = ('171705', 'Avocados, raw, all commercial varieties', 'raw', 160.0, 2.0, 8.53, 14.66)
REVIEWED['خس آيسبرج'] = ('169248', 'Lettuce, iceberg (includes crisphead types), raw', 'raw', 14.0, 0.9, 2.97, 0.14)
REVIEWED['خس روماني'] = ('169247', 'Lettuce, cos or romaine, raw', 'raw', 17.0, 1.23, 3.29, 0.3)

# cooked-weight review (28 Nov 2026): library rows whose own numbers equal the cooked USDA row; values read from the USDA FoodData Central API (api.nal.usda.gov/fdc/v1/food/<id>).
REVIEWED['صدر دجاج'] = ('171477', 'Chicken, broilers or fryers, breast, meat only, cooked, roasted', 'cooked (roasted, meat only)', 165.0, 31.02, 0.0, 3.57)
REVIEWED['سمك بلطي'] = ('175177', 'Fish, tilapia, cooked, dry heat', 'cooked, dry heat', 128.0, 26.15, 0.0, 2.65)
REVIEWED['جمبري'] = ('175180', 'Crustaceans, shrimp, cooked', 'cooked', 99.0, 23.98, 0.2, 0.28)
REVIEWED['بوري'] = ('175124', 'Fish, mullet, striped, cooked, dry heat', 'cooked, dry heat', 150.0, 24.81, 0.0, 4.86)

# PREP_REQUIRED: a reviewed row whose USDA row names ONE cooking method counts only when the item text names a compatible method.
# "Cooked weight" settles the weight basis; it does not say roasted, boiled or fried, and the generic row does not either.
# regex over the normalised item text. Rows not listed here need no method word.
PREP_REQUIRED = {
    'صدر دجاج': r"مشوي|مشوى|مشويه|مشوية|بالفرن|محمص|roast|grill|bak",           # USDA 171477: roasted, meat only
    'سمك بلطي': r"مشوي|مشوى|مشويه|مشوية|بالفرن|بالحراره الجافه|dry heat|grill|bak|roast",      # USDA 175177: cooked, dry heat
    'بوري': r"مشوي|مشوى|مشويه|مشوية|بالفرن|بالحراره الجافه|dry heat|grill|bak|roast",         # USDA 175124: cooked, dry heat
    'جمبري': r"مطبوخ|مسلوق|بالبخار|boil|cook|steam",     # USDA 175180: shrimp, cooked, moist heat (grilled, breaded or fried is another row)
}
# the text must also NAME the species/cut the USDA row is about ("سمك مشوي" is not tilapia, "دجاج بالفرن" is not breast)
NAME_REQUIRED = {'صدر دجاج': r"صدر", 'سمك بلطي': r"بلطي|بلطى", 'بوري': r"بوري", 'جمبري': r"جمبري|روبيان|ربيان"}
# generic rows that must not be offered as a picker choice (the named USDA options with their method are)
NOT_OFFERED = ('صدر دجاج', 'سمك بلطي', 'بوري', 'جمبري')

TOL = (1.5, 0.5, 0.6, 0.3)


def verified(food):
    """True when the row is in REVIEWED and its own values are within TOL of the USDA row."""
    v = REVIEWED.get(food.get('n'))
    if not v:
        return False
    mine = (food.get('cal'), food.get('p'), food.get('c'), food.get('f'))
    # a library value stored as a whole number (13.0, 15.0) is a rounded value: allow half a unit for it
    tol = [max(t, 0.5) if (a is not None and float(a) == int(a)) else t for a, t in zip(mine, TOL)]
    return all(abs((a or 0) - b) <= t for a, b, t in zip(mine, v[3:], tol))


# QUARANTINE: library rows whose Arabic name and values disagree about what the food is. The stored record is left as it is.
# These rows are never priced as exact, never sourced, and never mapped to a seafood or ostrich meaning without validated meaning.
QUARANTINE = {
    'المحار': 'name says oyster (shellfish) but 159 / 28.8 / 0 / 3.97 equals USDA "Ostrich, oyster, cooked" 172843 (an ostrich cut); meaning unvalidated',
}

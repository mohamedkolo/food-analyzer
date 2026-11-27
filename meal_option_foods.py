# -*- coding: utf-8 -*-
"""Named source-backed COOKED options, offered for review next to a table row whose name states no preparation.

Each row is a NEW food with its own name (the USDA id is in the name) copied value-for-value from USDA SR Legacy per 100 g by script.
It matches only when the written text contains its full name, so it never replaces a generic or original entry by itself.
The doctor picks it in the preview; until then the original text and record stay as written.
"""

OPTION_FOODS = [
    {"n": 'صدر دجاج مشوي بدون جلد (USDA 171477)', "en": 'Chicken, broilers or fryers, breast, meat only, cooked, roasted', "cat": 'poultry', "cal": 165.0, "p": 31.02, "f": 3.57, "c": 0.0,
     "fdc": 171477, "usda": 'Chicken, broilers or fryers, breast, meat only, cooked, roasted', "basis": 'cooked weight, roasted, meat only (no skin, no bone)', "option_for": 'صدر دجاج'},
    {"n": 'كبدة دجاج مطبوخة مقلية (USDA 174491)', "en": 'Chicken, liver, all classes, cooked, pan-fried', "cat": 'poultry', "cal": 172.0, "p": 25.78, "f": 6.43, "c": 1.11,
     "fdc": 174491, "usda": 'Chicken, liver, all classes, cooked, pan-fried', "basis": 'cooked weight, pan-fried', "option_for": 'كبدة دجاج'},
    {"n": 'سمك بلطي مطبوخ بالحرارة الجافة (USDA 175177)', "en": 'Fish, tilapia, cooked, dry heat', "cat": 'fish', "cal": 128.0, "p": 26.15, "f": 2.65, "c": 0.0,
     "fdc": 175177, "usda": 'Fish, tilapia, cooked, dry heat', "basis": 'cooked weight, dry heat', "option_for": 'سمك بلطي'},
    {"n": 'سمك قاروص مطبوخ بالحرارة الجافة (USDA 173694)', "en": 'Fish, sea bass, mixed species, cooked, dry heat', "cat": 'fish', "cal": 124.0, "p": 23.63, "f": 2.56, "c": 0.0,
     "fdc": 173694, "usda": 'Fish, sea bass, mixed species, cooked, dry heat', "basis": 'cooked weight, dry heat', "option_for": 'سمك قاروص'},
    {"n": 'سمك بوري مطبوخ بالحرارة الجافة (USDA 175124)', "en": 'Fish, mullet, striped, cooked, dry heat', "cat": 'fish', "cal": 150.0, "p": 24.81, "f": 4.86, "c": 0.0,
     "fdc": 175124, "usda": 'Fish, mullet, striped, cooked, dry heat', "basis": 'cooked weight, dry heat', "option_for": 'بوري'},
    {"n": 'جمبري مطبوخ (USDA 175180)', "en": 'Crustaceans, shrimp, cooked', "cat": 'fish', "cal": 99.0, "p": 23.98, "f": 0.28, "c": 0.2,
     "fdc": 175180, "usda": 'Crustaceans, shrimp, cooked', "basis": 'cooked weight', "option_for": 'جمبري'},
    {"n": 'كابوريا ألاسكا كينج مطبوخة بالبخار (USDA 174202)', "en": 'Crustaceans, crab, alaska king, cooked, moist heat', "cat": 'fish', "cal": 97.0, "p": 19.35, "f": 1.54, "c": 0.0,
     "fdc": 174202, "usda": 'Crustaceans, crab, alaska king, cooked, moist heat', "basis": 'cooked weight, moist heat; Alaska king crab, species may differ from the one meant', "option_for": 'كابوريا'},
    {"n": 'كركند شمالي مطبوخ بالبخار (USDA 174209)', "en": 'Crustaceans, lobster, northern, cooked, moist heat', "cat": 'fish', "cal": 89.0, "p": 19.0, "f": 0.86, "c": 0.0,
     "fdc": 174209, "usda": 'Crustaceans, lobster, northern, cooked, moist heat', "basis": 'cooked weight, moist heat', "option_for": 'جراد البحر'},    {"n": "بيض مسلوق صلب (USDA 173424)", "en": 'Egg, whole, cooked, hard-boiled', "cat": "egg", "cal": 155.0, "p": 12.58, "f": 10.61, "c": 1.12,
     "fdc": 173424, "usda": 'Egg, whole, cooked, hard-boiled', "basis": "cooked weight, hard-boiled, whole egg without shell (100 g = about 2 large eggs)", "option_for": "بيضة كاملة"},
]

for _f in OPTION_FOODS:
    _f.setdefault("safe", [])
    _f.setdefault("units", [])

# original row name -> option row name
OPTION_FOR = {f["option_for"]: f["n"] for f in OPTION_FOODS}

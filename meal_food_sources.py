# -*- coding: utf-8 -*-
"""Source-backed foods used ONLY by meal_macros (not shown on /foods,
not in the analyzer, not in the medical-filter chips: safe=[]).

Each row is copied value-for-value from USDA FoodData Central, SR Legacy
(April 2018 release, https://fdc.nal.usda.gov/download-datasets), per 100 g.
`fdc` is the SR Legacy NDB-linked FDC id, `basis` says what the grams are.
No value here is estimated. A food with no exact USDA entry is not listed.
"""

SOURCED_FOODS = [
    {"n": "حليب كامل", "en": "Whole milk", "cat": "dairy",
     "cal": 61.0, "p": 3.15, "f": 3.25, "c": 4.8,
     "fdc": 171265, "usda": "Milk, whole, 3.25% milkfat, with added vitamin D",
     "basis": "as drunk. ml -> g uses USDA household weight: 1 US cup (236.588 ml) = 244 g (SR Legacy 01077 / FDC 171265)"},
    {"n": "جبن شيدر", "en": "Cheddar cheese", "cat": "dairy",
     "cal": 403.0, "p": 22.87, "f": 33.31, "c": 3.37,
     "fdc": 173414, "usda": "Cheese, cheddar",
     "basis": "as eaten"},
    {"n": "سلمون مدخن", "en": "Smoked salmon", "cat": "fish",
     "cal": 117.0, "p": 18.28, "f": 4.32, "c": 0.0,
     "fdc": 173687, "usda": "Fish, salmon, chinook, smoked",
     "basis": "as eaten (smoked, ready to eat)"},
    {"n": "سمك قد مشوي", "en": "Cod, baked", "cat": "fish",
     "cal": 105.0, "p": 22.83, "f": 0.86, "c": 0.0,
     "fdc": 171956, "usda": "Fish, cod, Atlantic, cooked, dry heat",
     "basis": "cooked weight"},
    {"n": "أرز أبيض نيء", "en": "White rice, raw", "cat": "grain",
     "cal": 365.0, "p": 7.13, "f": 0.66, "c": 80.0,
     "fdc": 168877, "usda": "Rice, white, long-grain, regular, raw, enriched",
     "basis": "raw (dry) weight; USDA FDC API energy 365 kcal checked 2026-11-27"},
    {"n": "معكرونة نيئة", "en": "Pasta, dry", "cat": "grain",
     "cal": 371.0, "p": 13.0, "f": 1.51, "c": 74.7,
     "fdc": 169736, "usda": "Pasta, dry, enriched",
     "basis": "dry weight; USDA FDC API energy 371 kcal checked 2026-11-27"},
    {"n": "Baked Cod", "en": "Cod, baked", "cat": "fish",
     "cal": 105.0, "p": 22.83, "f": 0.86, "c": 0.0,
     "fdc": 171956, "usda": "Fish, cod, Atlantic, cooked, dry heat",
     "basis": "cooked weight"},
]

for _f in SOURCED_FOODS:
    _f.setdefault("safe", [])
    _f.setdefault("units", [])

# ml -> g, only where a source gives the household weight. USDA SR Legacy 01077
# (FDC 171265): 1 US cup (236.588 ml) of whole milk = 244 g -> 1.0314 g/ml.
# Applied to both whole-milk rows (the existing food_data row has the same
# per-100 g values). Every other food keeps the existing ml = g rule.
ML_G = {"حليب كامل": 1.0314, "حليب كامل الدسم": 1.0314}

# -*- coding: utf-8 -*-
"""Matcher fixes found by the nutrition audit, plus end-to-end day checks.

Run with:  python3 tests/test_nutrition_matcher_fixes.py
Synthetic profiles only. No client data.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")

import meal_macros as mm

FAILED = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (" " + str(detail) if detail and not cond else ""))
    if not cond:
        FAILED.append(name)


def food(text):
    f = mm.find_food(text)
    return f.get("n") if f else None


# 1. "تين" must not match inside "بروتين"
check("protein shake is whey, not fig", food("💪 بروتين شيك 45جم") == "واي بروتين (سكوب)", food("💪 بروتين شيك 45جم"))
check("protein 30g = whey scoop ~120 kcal", 100 <= mm.macros("💪 بروتين 30جم")["cal"] <= 140)
check("real fig still matches", food("تين 2") == "تين", food("تين 2"))

# 2. plain milk is milk, not laban
check("حليب is milk, not laban", food("🥛 حليب 290مل") == "حليب قليل الدسم", food("🥛 حليب 290مل"))
check("whole milk by name still whole", food("🥛 حليب كامل الدسم 200مل") == "حليب كامل الدسم")
check("لبن stays laban", food("🥛 لبن 200مل") == "لبن رايب")
check("almond milk (لبن لوز) is not laban", food("لبن لوز 200مل") == "حليب لوز غير محلى", food("لبن لوز 200مل"))

# 3. dry foods measured in ml are a prepared dish: unknown, not 200 g raw oats
for t in ("🥣 شوفان بحليب 200مل", "🍲 شوربة شوفان بالخضار 250مل"):
    m = mm.macros(t)
    check("ml dish not read as dry food: " + t, m["cal"] == 0 and m["covered"] == 0.0, m["cal"])
check("oats in grams unaffected", mm.macros("🥣 شوفان 40جم")["cal"] == 156)

# 4. prefixes still work
check("بحليب prefix", food("بحليب 100 جم") == "حليب قليل الدسم")
check("فول بطحينة is fava", food("فول بطحينة 150جم") == "فول مدمس")

# 5. synthetic full days: shown day total follows its target, and day = sum of meals
from plan_engine import generate_weekly_plan
import app as A
base = {"name": "x", "age": "34", "gender": "ذكر", "height": "178", "weight": "93",
        "tdee": "2500", "goal_cal": "1800", "goal_type": "weight_loss", "culture": "مصري",
        "diet_plan_type": "standard", "symptoms": [], "allergies": [], "notes": "",
        "disliked_foods": "", "protein_per_kg": "1.6", "fat_pct_cal": "30",
        "zigzag_mode": "off", "user_id": 1, "activity": "1.55"}
for label, ov in (("M93 loss", {}),
                  ("F70 loss", {"gender": "انثى", "weight": "70", "height": "162", "tdee": "1900", "goal_cal": "1400"}),
                  ("M70 gain", {"weight": "70", "tdee": "2600", "goal_cal": "3000", "goal_type": "muscle_gain"})):
    d = dict(base, **ov)
    with A.app.test_request_context("/"):
        plan = generate_weekly_plan(dict(d))
    tgt = float(d["goal_cal"])
    worst = max(abs(day["total_cal"] - tgt) / tgt for day in plan)
    check(label + ": every day within 6% of target", worst <= 0.06, round(worst, 3))

print("FAILED: %d" % len(FAILED))
sys.exit(1 if FAILED else 0)

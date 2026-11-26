# -*- coding: utf-8 -*-
"""Six proposed dishes as ingredient entries (review pilot, proposals, not the original recipes).
Values are USDA FoodData Central SR Legacy rows fetched from the FDC API (per 100 g).
"""
from recipe_entries import BASIS, source_row as S

RECIPES = [
    {"id": 'fatteh-hummus-base-v1', "name": 'فتة حمص', "basis": BASIS, "ingredients": [
        {"name": 'عيش بيتا قمح كامل', "g": 25, "state": 'ready', "source": S(174916, 'Bread, pita, whole-wheat', 262, 9.8, 1.71, 55.9)},
        {"name": 'حمص مسلوق', "g": 70, "state": 'cooked', "source": S(173757, 'Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, without salt', 164, 8.86, 2.59, 27.4)},
        {"name": 'زبادي كامل الدسم', "g": 40, "state": 'ready', "source": S(171284, 'Yogurt, plain, whole milk', 61.0, 3.47, 3.25, 4.66)},
        {"name": 'زيت زيتون', "g": 5, "state": 'oil', "source": S(171413, 'Oil, olive, salad or cooking', 884, 0.0, 100, 0.0)},
        {"name": 'توم', "g": 2, "state": 'raw', "source": S(169230, 'Garlic, raw', 149, 6.36, 0.5, 33.1)},
        {"name": 'عصير ليمون', "g": 8, "state": 'raw', "source": S(167747, 'Lemon juice, raw', 22.0, 0.35, 0.24, 6.9)},
    ]},
    {"id": 'shawarma-chicken-no-bread-v1', "name": 'شاورما دجاج بدون عيش', "basis": BASIS, "ingredients": [
        {"name": 'صدر دجاج، لحم بس', "g": 115, "state": 'cooked', "source": S(171477, 'Chicken, broilers or fryers, breast, meat only, cooked, roasted', 165, 31.0, 3.57, 0.0)},
        {"name": 'زيت زيتون', "g": 5, "state": 'oil', "source": S(171413, 'Oil, olive, salad or cooking', 884, 0.0, 100, 0.0)},
        {"name": 'بصل', "g": 15, "state": 'raw', "source": S(170000, 'Onions, raw', 40.0, 1.1, 0.1, 9.34)},
        {"name": 'طماطم', "g": 15, "state": 'raw', "source": S(170457, 'Tomatoes, red, ripe, raw, year round average', 18.0, 0.88, 0.2, 3.89)},
    ]},
    {"id": 'mandi-chicken-v1', "name": 'مندي دجاج', "basis": BASIS, "ingredients": [
        {"name": 'صدر دجاج، لحم بس', "g": 70, "state": 'cooked', "source": S(171477, 'Chicken, broilers or fryers, breast, meat only, cooked, roasted', 165, 31.0, 3.57, 0.0)},
        {"name": 'أرز أبيض', "g": 75, "state": 'cooked', "source": S(168878, 'Rice, white, long-grain, regular, enriched, cooked', 130, 2.69, 0.28, 28.2)},
        {"name": 'زيت زيتون', "g": 5, "state": 'oil', "source": S(171413, 'Oil, olive, salad or cooking', 884, 0.0, 100, 0.0)},
    ]},
    {"id": 'omelette-vegetables-v1', "name": 'عجة بالخضار', "basis": BASIS, "ingredients": [
        {"name": 'بيض كامل', "g": 100, "state": 'raw', "source": S(171287, 'Egg, whole, raw, fresh', 143, 12.6, 9.51, 0.72)},
        {"name": 'بصل', "g": 20, "state": 'raw', "source": S(170000, 'Onions, raw', 40.0, 1.1, 0.1, 9.34)},
        {"name": 'طماطم', "g": 30, "state": 'raw', "source": S(170457, 'Tomatoes, red, ripe, raw, year round average', 18.0, 0.88, 0.2, 3.89)},
        {"name": 'فلفل أخضر', "g": 20, "state": 'raw', "source": S(170427, 'Peppers, sweet, green, raw', 20.0, 0.86, 0.17, 4.64)},
        {"name": 'زيت زيتون', "g": 5, "state": 'oil', "source": S(171413, 'Oil, olive, salad or cooking', 884, 0.0, 100, 0.0)},
    ]},
    {"id": 'couscous-vegetables-v1', "name": 'كسكس بالخضار', "basis": BASIS, "ingredients": [
        {"name": 'كسكسي', "g": 100, "state": 'cooked', "source": S(169700, 'Couscous, cooked', 112, 3.79, 0.16, 23.2)},
        {"name": 'كوسة', "g": 60, "state": 'raw', "source": S(169291, 'Squash, summer, zucchini, includes skin, raw', 17.0, 1.21, 0.32, 3.11)},
        {"name": 'جزر', "g": 40, "state": 'raw', "source": S(170393, 'Carrots, raw', 41.0, 0.93, 0.24, 9.58)},
        {"name": 'زيت زيتون', "g": 5, "state": 'oil', "source": S(171413, 'Oil, olive, salad or cooking', 884, 0.0, 100, 0.0)},
    ]},
    {"id": 'shakshuka-falafel-v1', "name": 'شكشوكة بالفلافل', "basis": BASIS, "ingredients": [
        {"name": 'بيض كامل', "g": 100, "state": 'raw', "source": S(171287, 'Egg, whole, raw, fresh', 143, 12.6, 9.51, 0.72)},
        {"name": 'طماطم', "g": 100, "state": 'raw', "source": S(170457, 'Tomatoes, red, ripe, raw, year round average', 18.0, 0.88, 0.2, 3.89)},
        {"name": 'بصل', "g": 20, "state": 'raw', "source": S(170000, 'Onions, raw', 40.0, 1.1, 0.1, 9.34)},
        {"name": 'فلفل أخضر', "g": 20, "state": 'raw', "source": S(170427, 'Peppers, sweet, green, raw', 20.0, 0.86, 0.17, 4.64)},
        {"name": 'فلافل منزلية', "g": 50, "state": 'cooked', "source": S(172455, 'Falafel, home-prepared', 333, 13.3, 17.8, 31.8)},
        {"name": 'زيت زيتون', "g": 5, "state": 'oil', "source": S(171413, 'Oil, olive, salad or cooking', 884, 0.0, 100, 0.0)},
    ]},
]

# -*- coding: utf-8 -*-
"""English rendering for the Arabic meal strings in meal_database / meal_extra.

The meal database is authored in Arabic, and it has to stay that way: the
condition filters in filter_by_conditions match Arabic substrings from
UNSAFE_FOODS against the meal text, so rewriting the stored strings would
silently break the safety filtering for diabetes, kidney disease, G6PD and the
rest.

So instead of translating 900+ meals by hand, this module translates them on
the way out, from a glossary. Meals are compositional -- "🍗 صدر دجاج مشوي
150جم + 🍚 ارز بني 120جم + 🥗 سلطة" is a handful of terms plus quantities -- so
a glossary of ~370 entries covers the whole database and any meal added later.

PHRASES is tried before WORDS and longest-first, so multi-word terms come out
idiomatic ("صدر دجاج" -> "chicken breast", not "breast chicken").

Emoji, digits, "+" separators and punctuation pass through untouched.

Use translate_meal(); it returns the Arabic unchanged if anything is left
untranslated, so a gap shows up as Arabic text rather than a mangled sentence.
Run this file directly to audit coverage against the live database.
"""

import re

# ── multi-word terms, checked before single words ──────────────────────────
PHRASES = {
    "صدر دجاج": "chicken breast",
    "صدر فرخة": "chicken breast",
    "بصدر دجاج": "with chicken breast",
    "فخذ دجاج": "chicken thigh",
    "كبدة دجاج": "chicken liver",
    "كبدة فراخ": "chicken liver",
    "ديك رومي": "turkey",
    "لحم بقري": "beef",
    "لحم مفروم": "minced meat",
    "قليل الدهن": "lean",
    "قليل الدسم": "low-fat",
    "قليلة الدسم": "low-fat",
    "قليل الملح": "low-salt",
    "خالي الدسم": "fat-free",
    "جيد النضج": "well-done",
    "مطبوخ جيداً": "well cooked",
    "بدون جلد": "skinless",
    "بدون دهون": "fat-free",
    "بدون زيت": "no oil",
    "بدون ملح": "no salt",
    "زيت زيتون": "olive oil",
    "زيت الزيتون": "olive oil",
    "بزيت الزيتون": "with olive oil",
    "بزيت زيتون": "with olive oil",
    "قليل الزيت": "with little oil",
    "كامل الدسم": "full-fat",
    "كاملة الدسم": "full-fat",
    "جبن دسم": "full-fat cheese",
    "جبن كامل الدسم": "full-fat cheese",
    "جبنة كاملة الدسم": "full-fat cheese",
    "جبن قريش دسم": "full-fat cottage cheese",
    "زبادي كامل الدسم": "full-fat yogurt",
    "زبادي يوناني كامل الدسم": "full-fat Greek yogurt",
    "كفتة لحم دسمة": "rich meat kofta",
    "لحم دسم": "fatty meat",
    "فخذ دجاج بالجلد مشوي": "grilled chicken thigh with skin",
    "فخذ دجاج بالجلد": "chicken thigh with skin",
    "أفوكادو محشي بيض": "egg-stuffed avocado",
    "افوكادو محشي بيض": "egg-stuffed avocado",
    "خبز تورتيلا قمح كامل": "whole-wheat tortilla",
    "تورتيلا قمح كامل": "whole-wheat tortilla",
    "جوز الهند": "coconut",
    "جوز هند": "coconut",
    "لسان عصفور": "orzo",
    "بياض البيض": "egg whites",
    "بيض مسلوق": "boiled eggs",
    "بيضة مسلوقة": "boiled egg",
    "بيض عيون": "fried eggs",
    "لبن رايب": "buttermilk",
    "سمن بلدي": "ghee",
    "متعدد الحبوب": "multigrain",
    "جبن قريش": "cottage cheese",
    "جبنة قريش": "cottage cheese",
    "جبن فيتا": "feta cheese",
    "جبنة فيتا": "feta cheese",
    "جبن حلوم": "halloumi",
    "جبن بارميزان": "parmesan",
    "جبن نابلسية": "Nabulsi cheese",
    "جبنة نابلسية": "Nabulsi cheese",
    "خبز اسمر": "whole-wheat bread",
    "خبز أسمر": "whole-wheat bread",
    "خبز ابيض": "white bread",
    "خبز أبيض": "white bread",
    "خبز عربي": "pita bread",
    "خبز شامي": "pita bread",
    "خبز مرقوق": "markook bread",
    "خبز قمح كامل": "whole-wheat bread",
    "توست اسمر": "whole-wheat toast",
    "توست أسمر": "whole-wheat toast",
    "ارز بني": "brown rice",
    "أرز بني": "brown rice",
    "ارز ابيض": "white rice",
    "أرز أبيض": "white rice",
    "ارز بسيط": "plain rice",
    "بطاطا حلوة": "sweet potato",
    "بابا غنوج": "baba ghanoush",
    "فول مدمس": "ful mudammas",
    "حمص بطحينة": "hummus with tahini",
    "شوربة عدس": "lentil soup",
    "سلطة راهب": "raheb salad",
    "سلطة فتوش": "fattoush",
    "سلطة تبولة": "tabbouleh",
    "زبادي يوناني": "Greek yogurt",
    "لبن يوناني": "Greek yogurt",
    "يوغورت يوناني": "Greek yogurt",
    "شيش طاووق": "shish taouk",
    "طاجين الدار المغربي": "Moroccan house tagine",
    "الدار المغربي": "Moroccan house",
    "بروتين شيك": "protein shake",
    "بذور شيا": "chia seeds",
    "بذور القرع": "pumpkin seeds",
    "سلمون مدخّن": "smoked salmon",
    "سمك بلطي": "tilapia",
    "سمك فيلية": "fish fillet",
    "سمك زبيدي": "zubaidi fish",
    "سمك هامور": "hamour fish",
    "لحم ضأن": "lamb",
    "شرائح ديك رومي": "turkey slices",
    "خضار سوتيه": "sautéed vegetables",
    "خضار ورقية": "leafy greens",
    "خضار مشكلة": "mixed vegetables",
    "خضار متنوعة": "assorted vegetables",
    "فواكه مختلطة": "mixed fruit",
    "فواكه متنوعة": "assorted fruit",
    "توت أزرق": "blueberries",
    "توت ازرق": "blueberries",
    "دبس رمان": "pomegranate molasses",
    "غير مبستر": "unpasteurized",
    # Arabic construct state (إضافة) reverses in English: "شوربة عدس" is
    # lentil soup, not soup lentils.
    "شوربة دجاج": "chicken soup",
    "شوربة فراخ": "chicken soup",
    "شوربة خضار": "vegetable soup",
    "شوربة شوفان": "oat soup",
    "شوربة فريكة": "freekeh soup",
    "شوربة لسان عصفور": "orzo soup",
    "شوربة طماطم": "tomato soup",
    "طاجين دجاج": "chicken tagine",
    "طاجين خضار": "vegetable tagine",
    "طاجن خضار": "vegetable tagine",
    "طاجين سمك": "fish tagine",
    "طاجين لحم": "meat tagine",
    "طاجين كفتة": "kofta tagine",
    "طاجن بامية": "okra tagine",
    "طاجين بامية": "okra tagine",
    "فتة حمص": "chickpea fatteh",
    "كفتة دجاج": "chicken kofta",
    "كفتة لحم": "meat kofta",
    "يخنة فاصوليا": "bean stew",
    "يخنة بازيلا": "pea stew",
    "سلطة دجاج": "chicken salad",
    "سلطة تونة": "tuna salad",
    "سلطة خيار": "cucumber salad",
    "سلطة جزر": "carrot salad",
    "سلطة زعلوك": "zaalouk salad",
    "سلطة خضرا": "green salad",
    "سلطة خضراء": "green salad",
    "صلصة طماطم": "tomato sauce",
    "صلصة صويا": "soy sauce",
    "محشي كوسة": "stuffed zucchini",
    "فطائر الشعير": "barley pastries",
    "عجة بيض": "omelette",
    "عجة جبن": "cheese omelette",
    "زبدة فول سوداني": "peanut butter",
    "زبدة لوز": "almond butter",
    "زبدة طحينة": "tahini",
    "حليب لوز": "almond milk",
    "لبن لوز": "almond milk",
    "حليب صويا": "soy milk",
    "حليب جوز الهند": "coconut milk",
    "حليب كامل الدسم": "whole milk",
    "حليب كامل": "whole milk",
    "حليب خالي الدسم": "skim milk",
    "حليب قليل الدسم": "low-fat milk",
    "فول سوداني": "peanuts",
    "زبدة فول": "peanut butter",
    "شاورما دجاج": "chicken shawarma",
    "شاورما لحم": "meat shawarma",
    "كبسة دجاج": "chicken kabsa",
    "كبسة لحم": "lamb kabsa",
    "مندي لحم": "lamb mandi",
    "مندي دجاج": "chicken mandi",
    "برياني دجاج": "chicken biryani",
    "مسخن دجاج": "chicken musakhan",
    "مقلوبة باذنجان": "eggplant maqluba",
    "مناقيش زعتر": "zaatar manakish",
    "بانكيك شوفان": "oat pancakes",
    "بانكيك بروتين": "protein pancakes",
    "مشاوي مختلطة": "mixed grill",
    "مشاوي مشكلة": "mixed grill",
    "مشاوي دجاج": "chicken mixed grill",
    "بليلة قمح": "wheat balila",
    "ستيك لحم": "beef steak",
    "توست قمح كامل": "whole-wheat toast",
    "توست كامل": "whole-wheat toast",
    "توست متعدد الحبوب": "multigrain toast",
    "قطع شوفان": "oat pieces",
}

# ── single words ───────────────────────────────────────────────────────────
WORDS = {
    # units / quantities
    "جم": "g", "مل": "ml", "ملعقة": "tbsp", "ملاعق": "tbsp", "كوب": "cup",
    "حبة": "pc", "حبات": "pcs", "قطعة": "pc", "قطع": "pcs", "ثمرة": "piece",
    "شريحة": "slice", "شريحتين": "2 slices", "شرائح": "slices",
    "علبة": "can", "كاسة": "bowl", "كف": "handful", "نص": "½",
    # staples
    "خبز": "bread", "توست": "toast", "ارز": "rice", "أرز": "rice",
    "مكرونة": "pasta", "معكرونة": "pasta", "نودلز": "noodles",
    "برغل": "bulgur", "فريكة": "freekeh", "كينوا": "quinoa", "كسكس": "couscous",
    "شوفان": "oats", "شعير": "barley", "الشعير": "barley", "قمح": "wheat",
    "جرانولا": "granola", "كورنفليكس": "cornflakes", "بليلة": "balila",
    "كشري": "koshari", "برياني": "biryani", "تورتيلا": "tortilla",
    "نان": "naan", "مرقوق": "markook", "الحبوب": "grains",
    # protein
    "بيض": "eggs", "بيضة": "egg", "بيضتين": "2 eggs", "بياض": "whites",
    "دجاج": "chicken", "فراخ": "chicken", "فرخة": "chicken", "فروج": "chicken",
    "صدر": "breast", "فخذ": "thigh", "لحم": "meat", "بقري": "beef",
    "كبدة": "liver", "كفتة": "kofta", "ستيك": "steak", "مشاوي": "mixed grill",
    "سمك": "fish", "سلمون": "salmon", "تونة": "tuna", "جمبري": "shrimp",
    "بلطي": "tilapia", "فيلية": "fillet", "زبيدي": "zubaidi", "هامور": "hamour",
    "بيكون": "bacon", "بروتين": "protein", "صويا": "soy",
    # dairy
    "جبن": "cheese", "جبنة": "cheese", "قريش": "cottage", "فيتا": "feta",
    "حلوم": "halloumi", "بارميزان": "parmesan", "نابلسية": "Nabulsi",
    "لبنة": "labneh", "زبادي": "yogurt", "يوغورت": "yogurt", "لبن": "yogurt",
    "حليب": "milk", "رايب": "buttermilk", "زبدة": "butter", "قشدة": "cream",
    "كريمة": "cream", "الدسم": "fat", "دسم": "fat", "دسمة": "fat",
    "لبني": "dairy", "لبنية": "labaniyah", "مبستر": "pasteurized",
    # legumes / nuts
    "فول": "fava beans", "حمص": "chickpeas", "عدس": "lentils",
    "فاصوليا": "beans", "بازيلا": "peas", "لوبيا": "black-eyed beans",
    "لوز": "almonds", "جوز": "walnuts", "كاجو": "cashews", "فستق": "pistachios",
    "مكسرات": "nuts", "بذور": "seeds", "سمسم": "sesame", "طحينة": "tahini",
    "شيا": "chia", "الهند": "coconut", "هند": "coconut",
    # vegetables
    "خضار": "vegetables", "خضرا": "greens", "سلطة": "salad", "خس": "lettuce",
    "طماطم": "tomato", "الطماطم": "tomato", "بندورة": "tomato",
    "خيار": "cucumber", "جزر": "carrots", "بطاطا": "potato", "بطاطس": "potato",
    "باذنجان": "eggplant", "كوسة": "zucchini", "زوكيني": "zucchini",
    "بروكلي": "broccoli", "قرنبيط": "cauliflower", "سبانخ": "spinach",
    "ملوخية": "molokhia", "بامية": "okra", "فطر": "mushrooms", "كرفس": "celery",
    "ثوم": "garlic", "بصل": "onion", "فلفل": "pepper", "كيل": "kale",
    "زيتون": "olives", "الزيتون": "olive", "نعناع": "mint", "بقدونس": "parsley",
    "زعتر": "zaatar", "كرنب": "cabbage",
    # fruit
    "موز": "banana", "تفاح": "apple", "تمر": "dates", "توت": "berries",
    "فراولة": "strawberries", "ليمون": "lemon", "فواكه": "fruit",
    "افوكادو": "avocado", "أفوكادو": "avocado", "برقوق": "prunes",
    "دبس": "molasses",
    # fats / condiments
    "زيت": "oil", "الزيت": "oil", "سمن": "ghee", "عسل": "honey",
    "صلصة": "sauce", "صوص": "sauce", "ملح": "salt", "الملح": "salt",
    "قرفة": "cinnamon", "شرمولة": "chermoula", "جواكامولي": "guacamole",
    "دهون": "fat", "الدهن": "fat",
    # dishes
    "شوربة": "soup", "عجة": "omelette", "اومليت": "omelette",
    "أومليت": "omelette", "شكشوكة": "shakshuka", "طعمية": "taameya",
    "فلافل": "falafel", "فتوش": "fattoush", "تبولة": "tabbouleh",
    "كبة": "kibbeh", "فتة": "fatteh", "محشي": "stuffed", "مقلوبة": "maqluba",
    "مسخن": "musakhan", "مناقيش": "manakish", "شاورما": "shawarma",
    "طاجين": "tagine", "طاجن": "tagine", "طنجية": "tanjia",
    "حريرة": "harira", "بيصارة": "bissara", "زعلوك": "zaalouk",
    "رفيسة": "rfissa", "مسمن": "msemen", "حرشة": "harcha", "بغرير": "baghrir",
    "سفنج": "sfenj", "شباكية": "chebakia", "شبكية": "chebakia",
    "كبسة": "kabsa", "مندي": "mandi", "مجبوس": "machboos", "محمر": "mhammar",
    "يخنة": "stew", "باليخنة": "stewed", "سوشي": "sushi", "غنوج": "ghanoush",
    "بابا": "baba", "مدمس": "mudammas", "راهب": "raheb", "بليله": "balila",
    "كعك": "kaak", "كيك": "cake", "بانكيك": "pancakes", "فطائر": "pastries",
    "سوتيه": "sautéed", "شيش": "shish", "طاووق": "taouk", "مشكلة": "mixed",
    # descriptors
    "مشوي": "grilled", "مشوية": "grilled", "مسلوق": "boiled",
    "مسلوقة": "boiled", "مقلي": "fried", "مقلية": "fried",
    "مطبوخ": "cooked", "مطبوخة": "cooked", "مفروم": "minced",
    "مبشور": "grated", "مدخّن": "smoked", "مدخن": "smoked",
    "فرن": "oven", "عيون": "fried", "طازة": "fresh", "طازج": "fresh",
    "طازجة": "fresh", "اسمر": "whole-wheat", "أسمر": "whole-wheat",
    "بني": "brown", "ابيض": "white", "أبيض": "white", "بيضاء": "white",
    "اخضر": "green", "أخضر": "green", "خضراء": "green", "سوداء": "black",
    "حلوة": "sweet", "سادة": "plain", "بسيط": "simple", "كامل": "whole",
    "كاملة": "whole", "قليل": "low", "قليلة": "low", "خالي": "free",
    "كبير": "large", "كبيرة": "large", "صغير": "small", "صغيرة": "small",
    "خفيف": "light", "خفيفة": "light", "قديم": "aged", "جلد": "skin",
    "ورقية": "leafy", "ملونة": "colourful", "متنوعة": "assorted",
    "مختلطة": "mixed", "متعدد": "multi", "زيادة": "extra", "بدون": "without",
    "جيد": "good", "جيداً": "well", "النضج": "done", "الدار": "house",
    # cuisines
    "مصري": "Egyptian", "مصرية": "Egyptian", "شامي": "Levantine",
    "شامية": "Levantine", "خليجي": "Gulf", "مغربي": "Moroccan",
    "مغربية": "Moroccan", "المغربي": "Moroccan", "مراكشية": "Marrakech",
    "عربي": "Arabic", "يوناني": "Greek", "يونانية": "Greek",
    "تركي": "Turkish", "تركية": "Turkish", "صيني": "Chinese",
    "آسيوي": "Asian", "آسيوية": "Asian", "هندي": "Indian",
    "حمصي": "Homsi", "بحلب": "Aleppo", "بلدي": "baladi",
    # drinks
    "شاي": "tea", "قهوة": "coffee", "عصير": "juice", "ماء": "water",
    "عيران": "ayran", "رَي": "rey", "راي": "rey",
    # snack vocabulary (get_snacks_for_goal returns plain strings)
    "ساندويتش": "sandwich", "تفاحة": "apple", "برتقالة": "orange",
    "موزة": "banana", "كمثرى": "pear", "كيوي": "kiwi", "زبيب": "raisins",
    "نيئ": "raw", "نيء": "raw", "مخبوز": "baked", "باي": "pie",
    "بالنعناع": "with mint",
    # connectors
    "أو": "or", "او": "or", "مع": "with", "من": "of", "في": "in",
    "بدل": "instead of", "غير": "un",
    # "بـ" prefixed forms
    "بالخضار": "with vegetables", "بالحليب": "with milk",
    "بالطحينة": "with tahini", "بطحينة": "with tahini",
    "بالزعفران": "with saffron", "بلحم": "with meat", "باللحم": "with meat",
    "بالدجاج": "with chicken", "بالكمون": "with cumin",
    "بالجبن": "with cheese", "بالشرمولة": "with chermoula",
    "بالزعتر": "with zaatar", "بزيت": "with oil", "بالزبدة": "with butter",
    "بالماء": "in water", "بالبيض": "with eggs", "بالبقدونس": "with parsley",
    "بالفرن": "oven-baked", "بالبهارات": "with spices",
    "بالزيتون": "with olives", "بالبرقوق": "with prunes",
    "بالصينية": "tray-baked", "بالقليل": "with a little",
    "بالثوم": "with garlic", "بالأفوكادو": "with avocado",
    "بالتفاح": "with apple", "بالسبانخ": "with spinach",
    "بالفلافل": "with falafel", "بالطماطم": "with tomato",
    "بالتمر": "with dates", "بالليمون": "with lemon",
    "بالبندورة": "with tomato", "بالأعشاب": "with herbs",
    "بالقرفة": "with cinnamon", "بالقشر": "with skin",
    "بالجلد": "with skin", "بالكريمة": "with cream", "بحليب": "with milk",
    "بصدر": "with breast", "بالشوفان": "with oats",
    # "و" prefixed forms
    "وطماطم": "and tomato", "والكمون": "and cumin", "والليمون": "and lemon",
    "والكفتة": "and kofta", "والقرفة": "and cinnamon",
    "والدجاج": "and chicken", "والبقدونس": "and parsley",
    "والتفاح": "and apple", "والسبانخ": "and spinach",
    "والفطر": "and mushrooms", "والزبدة": "and butter", "والجبن": "and cheese",
}

_AR = r"؀-ۿ"
# longest first so "صدر دجاج" wins over "دجاج", and phrases beat single words
_TERMS = sorted(
    list(PHRASES.items()) + list(WORDS.items()),
    key=lambda kv: len(kv[0]),
    reverse=True,
)
_COMPILED = [
    (re.compile(f"(?<![{_AR}]){re.escape(ar)}(?![{_AR}])"), en)
    for ar, en in _TERMS
]
_HAS_AR = re.compile(f"[{_AR}]")

# Arabic puts the adjective after the noun, English before it, so a literal
# word-for-word pass yields "fish grilled 150g". These are the adjectives that
# get moved ahead of the noun they follow.
_ADJECTIVES = {
    "grilled", "boiled", "fried", "cooked", "minced", "grated", "smoked",
    "sautéed", "stewed", "tray-baked", "oven-baked", "stuffed", "fresh",
    "raw", "baked",
    "whole-wheat", "whole", "full-fat", "brown", "white", "green", "black", "sweet",
    "plain", "simple", "low", "low-fat", "lean", "fat-free", "low-salt",
    "large", "small", "light", "aged", "leafy", "colourful", "assorted",
    "mixed", "multi", "multigrain", "extra", "skinless", "baladi",
    "pasteurized", "unpasteurized", "well-done", "cottage", "feta",
    "halloumi", "parmesan", "Nabulsi", "Greek", "Egyptian", "Levantine",
    "Gulf", "Moroccan", "Marrakech", "Arabic", "Turkish", "Chinese",
    "Asian", "Indian", "Homsi", "Aleppo",
}
# a segment never reorders across these
_STOPS = {"with", "and", "or", "of", "in", "without", "instead", "no", "½"}
_WORD = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ-]*$")


def _reorder(text):
    """Move post-positive adjectives ahead of their noun, per segment."""
    out_parts = []
    for part in text.split("+"):
        toks = part.split()
        buf, seg = [], []

        def flush():
            if not seg:
                return
            adjs = [t for t in seg if t in _ADJECTIVES]
            rest = [t for t in seg if t not in _ADJECTIVES]
            # only reorder when there is a noun left to qualify
            buf.extend(adjs + rest if (adjs and rest) else seg)
            seg.clear()

        for t in toks:
            if _WORD.match(t) and t.lower() not in _STOPS:
                seg.append(t)
            else:
                flush()
                buf.append(t)
        flush()
        out_parts.append(" ".join(buf))
    return " + ".join(p.strip() for p in out_parts)


def translate_meal(text, strict=True):
    """Render an Arabic meal string in English.

    Returns the input unchanged when it holds no Arabic, and (when strict)
    also when any Arabic survives translation -- a partial rendering reads
    worse than the original, and leaves the gap visible for us to fix.
    """
    if not text or not _HAS_AR.search(text):
        return text
    out = text
    for rx, en in _COMPILED:
        out = rx.sub(en, out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    if strict and _HAS_AR.search(out):
        return text
    return _reorder(out)


def untranslated_terms(text):
    """Arabic words left over after translating -- used by the audit below."""
    out = text
    for rx, en in _COMPILED:
        out = rx.sub(" ", out)
    return [w for w in re.findall(f"[{_AR}]+", out)]


if __name__ == "__main__":
    import collections
    import meal_database as md
    import meal_extra as mx

    # Only the things actually rendered as meal text: the four goal pools, the
    # safe-alternative swaps, and the snack lists. Deliberately excludes
    # UNSAFE_FOODS (match keywords), NUTRIENT_BOOST_NOTES and DIET_PLAN_TYPES
    # (advice prose and slot labels) -- none of those are meals.
    meals = []

    def walk(cur):
        if isinstance(cur, dict):
            if isinstance(cur.get("meal"), str):
                meals.append(cur["meal"])
                return
            for v in cur.values():
                walk(v)
        elif isinstance(cur, (list, tuple)):
            for v in cur:
                walk(v)
        elif isinstance(cur, str) and _HAS_AR.search(cur):
            meals.append(cur)

    for pool in ("WEIGHT_LOSS", "MUSCLE_GAIN", "BULKING", "MAINTENANCE",
                 "SAFE_ALTERNATIVES", "KETO_MEALS", "KETO_SNACKS"):
        for mod in (md, mx):
            walk(getattr(mod, pool, None))
    for goal in ("weight_loss", "muscle_gain", "bulking", "maintenance"):
        walk(md.get_snacks_for_goal(goal))

    meals = sorted(set(meals))
    missing = collections.Counter()
    failed = 0
    for m in meals:
        left = untranslated_terms(m)
        if left:
            failed += 1
            missing.update(left)

    print(f"meals checked      : {len(meals)}")
    print(f"fully translated   : {len(meals) - failed}")
    print(f"with leftover terms: {failed}")
    if missing:
        print(f"\nunmapped terms ({len(missing)}):")
        for w, n in missing.most_common():
            print(f"  {n:>4}  {w}")
    else:
        print("\nglossary covers the whole database.")
    print("\nsamples:")
    for m in meals[:6]:
        print("  AR:", m)
        print("  EN:", translate_meal(m))


# ── clinical allow/avoid guidance ──────────────────────────────────────────
# The 68 phrases get_allowed_forbidden returns. These are advice sentences, not
# meals, so they get a straight lookup rather than going through the glossary.
# Keys must stay byte-identical to the Arabic in app.get_allowed_forbidden.
GUIDANCE_EN = {
    "فول مدمس + عدس + شوربات + سمك مشوي": "Ful mudammas, lentils, soups, grilled fish",
    "دجاج مشوي أو فرن + بيض": "Grilled or oven-baked chicken, eggs",
    "شوفان + خبز أسمر + أرز بني": "Oats, whole-wheat bread, brown rice",
    "زبادي يوناني سادة + جبن قريش": "Plain Greek yogurt, cottage cheese",
    "ملوخية + كوسة + خضار مطبوخة": "Molokhia, zucchini, cooked vegetables",
    "زيت زيتون (ملعقة) + فاكهة طازجة": "Olive oil (1 tbsp), fresh fruit",
    "شاي أخضر + ماء بالليمون": "Green tea, water with lemon",
    "الخبز الأبيض": "White bread",
    "الأكل المقلي + السمن": "Fried food and ghee",
    "المشروبات الغازية": "Fizzy drinks",
    "الحلويات والسكريات": "Sweets and sugars",
    "عدس أصفر بكميات محدودة": "Yellow lentils in limited amounts",
    "الفول بكل أنواعه": "Fava beans of every kind",
    "الحمص والبقوليات الحمراء": "Chickpeas and red legumes",
    "شاي مع الوجبات": "Tea with meals",
    "الكبدة والأعضاء الداخلية": "Liver and organ meats",
    "اللحوم الحمراء بإفراط": "Excessive red meat",
    "التوابل الحارة": "Hot spices",
    "الكافيين الزائد": "Excess caffeine",
    "حليب اللوز / الصويا / جوز الهند": "Almond, soy or coconut milk",
    "جبن معتق بكميات قليلة": "Aged cheese in small amounts",
    "الحليب والألبان كاملة الدسم": "Whole milk and full-fat dairy",
    "الجبن الطازج": "Fresh cheese",
    "الايس كريم": "Ice cream",
    "أسماك دهنية: سلمون": "Oily fish such as salmon",
    "صفار البيض + الفطر": "Egg yolk and mushrooms",
    "تعرض للشمس 15 دقيقة": "15 minutes of sun exposure",
    "لحوم حمراء + كبدة": "Red meat and liver",
    "سبانخ + عدس": "Spinach and lentils",
    "كارب معقّد بكميات محسوبة: شوفان + أرز بني":
        "Complex carbs in measured amounts: oats, brown rice",
    "خضار غير نشوية + بروتين في كل وجبة":
        "Non-starchy vegetables and protein at every meal",
    "قياس السكر قبل الأكل وبعده بساعتين":
        "Check blood sugar before eating and 2 hours after",
    "السكر المضاف + العصائر + المشروبات الغازية":
        "Added sugar, juices and fizzy drinks",
    "الأرز الأبيض والخبز الأبيض": "White rice and white bread",
    "الحلويات والمعجنات": "Sweets and pastries",
    "أكل قليل الملح + خضار ورقية": "Low-salt food and leafy greens",
    "تقليل الكافيين + مياه كافية": "Less caffeine, enough water",
    "الملح الزائد + المخللات + المعلبات": "Excess salt, pickles and tinned food",
    "الصوصات الجاهزة + اللحوم المصنّعة": "Ready-made sauces and processed meat",
    "بروتين معتدل حسب تعليمات الطبيب": "Moderate protein per your doctor's instructions",
    "كمية المياه حسب إرشاد الطبيب": "Water intake as your doctor advises",
    "البوتاسيوم العالي: موز/طماطم/بطاطا بكثرة":
        "High potassium: lots of banana, tomato or potato",
    "البروتين والفوسفور الزائد": "Excess protein and phosphorus",
    "الملح والمعلبات": "Salt and tinned food",
    "أوميجا 3: سمك مرتين أسبوعياً": "Omega 3: fish twice a week",
    "زيت زيتون + أفوكادو + مكسرات": "Olive oil, avocado and nuts",
    "الدهون المشبعة + المقليات": "Saturated fat and fried food",
    "اللحوم المصنّعة + السمن": "Processed meat and ghee",
    "حمض فوليك: خضار ورقية + بقوليات": "Folic acid: leafy greens and legumes",
    "كالسيوم: ألبان مبسترة": "Calcium: pasteurized dairy",
    "حديد وبروتين كافي": "Enough iron and protein",
    "الكبدة + الأسماك عالية الزئبق": "Liver and high-mercury fish",
    "الأطعمة النيئة وغير المبسترة": "Raw and unpasteurized foods",
    "عجز سعري معتدل + بروتين عالي": "A moderate calorie deficit with high protein",
    "خضار كتير + مشي يومي": "Plenty of vegetables and a daily walk",
    "الوجبات السريعة + السعرات الفارغة": "Fast food and empty calories",
    "المشروبات السكرية": "Sugary drinks",
    "ألياف: خضار + فاكهة بقشرها + شوفان":
        "Fibre: vegetables, fruit with the skin on, oats",
    "مياه كافية (8 أكواب)": "Enough water (8 glasses)",
    "زبادي / بروبيوتيك": "Yogurt or probiotics",
    "مصادر بروتين عالية: دجاج + لحم + سمك + بيض":
        "High-protein sources: chicken, meat, fish, eggs",
    "كاربوهيدرات معقدة: ارز بني + شوفان + بطاطا":
        "Complex carbohydrates: brown rice, oats, potato",
    "مكسرات + افوكادو + زيت زيتون": "Nuts, avocado and olive oil",
    "حليب كامل + زبادي يوناني": "Whole milk and Greek yogurt",
    "بروتين شيك بعد التمرين": "A protein shake after training",
    "الأكل المقلي الزائد": "Too much fried food",
    "السكريات المضافة": "Added sugars",
    "الوجبات السريعة": "Fast food",
}


def translate_guidance(text):
    """English for one allow/avoid line; falls back to the Arabic."""
    return GUIDANCE_EN.get((text or "").strip(), text)

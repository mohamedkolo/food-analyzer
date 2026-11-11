# -*- coding: utf-8 -*-
"""What a client may eat instead of one item on their plan.

The plan says "ارز بني 140جم". The client has no rice at home. Until now
they either guessed or wrote to the nutritionist. This offers a short list
of swaps, each with the amount that keeps the meal what it was.

A swap is offered only when **all four** of these hold. Each one alone was
not enough, and the reason is beside it:

1. **Same kind of food.** Grain for grain, fruit for fruit, lean protein
   for lean protein. Dates can match rice on calories and carbohydrate to
   the gram and still not be what a lunch is built around.

2. **Same calories, and the same protein, carbohydrate and fat.** The
   amount is chosen so the calories match; then each of the three macros
   must land close to the original. Matching calories alone lets 150g of
   chicken breast become 60g of sausage.

3. **Allowed for this client's conditions -- checked twice, from two
   lists that were written separately.** The first is UNSAFE_FOODS, the
   same list the plan generator filters on. The second is the food table's
   own `safe` field (dm, htn, ckd, ibs, heart). For those five conditions
   the food must *say* it is safe: a food nobody has annotated is left out,
   not waved through. An unreviewed food is not a safe food.

4. **The original was read with certainty.** If the amount on the plan had
   to be guessed ("سلطة" with no grams), nothing is offered. A swap sized
   against a guess is a wrong amount with a confident number on it.

When in doubt this returns fewer swaps, or none. An empty list sends the
client back to the plan as written, which the nutritionist approved.
The cost of a missing suggestion is a message; the cost of a wrong one is
on the client's plate.

Where the rules come from
-------------------------
The groups, and what each condition closes, are not this file's opinion.
They are taken from the two textbooks the clinic works from, and every rule
below carries its page:

  [خ]  د. منى خليل عبد القادر، «التغذية العلاجية»، مجموعة النيل العربية،
       الطبعة الثانية ٢٠٠٤.
  [CN] Elia, Ljungqvist, Stratton & Lanham-New (eds), «Clinical Nutrition»,
       The Nutrition Society Textbook Series, 2nd edition.
  [UN] Rolfes, Pinna & Whitney, «Understanding Normal and Clinical
       Nutrition», 8th edition.

The exchange system itself ([خ] ص ٢٩-٣٦) is why a second check is needed at
all. The book says it in so many words (ص ٣٥-٣٦): the exchange units reflect
energy, protein, fat and carbohydrate **only**, and say nothing about
vitamins and minerals, "because there are large differences between the
foods of one group". Two fruits that are one exchange each can be far apart
in potassium. So macros decide *how much*, and the condition rules decide
*whether at all*.

Nothing here knows about Flask or the database.
"""

import re

import food_data
import meal_macros
from meal_database import CONDITION_MAP, _contains_unsafe

# ‏المجموعات الست التبادلية -- [خ] ص ٢٩-٣٥. الصنف مايتبدّلش غير بصنف من
# مجموعته. وهي **مش** فئات جدول الأكل، والفرق في تلات حتت:
#
#   - البيض والجبن في مجموعة **اللحوم** (ص ٣٤-٣٥)، مش الألبان. مجموعة
#     الألبان لبن وزبادي بس (ص ٣٠).
#   - البقول الناشفة والبطاطس والذرة والبسلة في مجموعة **الخبز** (ص ٣٣).
#   - المكسرات والزيتون والزبدة والقشدة في مجموعة **الدهن** (ص ٣٥).
MILK, VEG, FRUIT, BREAD, MEAT, FAT = (
    "milk", "veg", "fruit", "bread", "meat", "fat")
_CAT_GROUP = {"poultry": MEAT, "meat": MEAT, "fish": MEAT, "grain": BREAD,
              "legume": BREAD, "veg": VEG, "fruit": FRUIT, "nut": FAT}
_MILK_WORDS = ("حليب", "لبن", "زبادي", "رايب")
_DAIRY_FAT_WORDS = ("زبده", "زبد", "قشده", "قشطه", "كريمه", "سمن")
_STARCHY_VEG = ("بطاطس", "بطاطا", "ذره", "بسله", "بازلاء")


def group_of(food):
    """The exchange group a food belongs to, or None when it has none."""
    cat = food.get("cat")
    name = meal_macros._norm(food.get("n"))
    if cat == "dairy":
        if any(meal_macros._norm(w) in name for w in _DAIRY_FAT_WORDS):
            return FAT
        if "جبن" in name or "بيض" in name or "صفار" in name:
            return MEAT
        if any(meal_macros._norm(w) in name for w in _MILK_WORDS):
            return MILK
        return None
    if cat == "veg" and any(meal_macros._norm(w) in name for w in _STARCHY_VEG):
        return BREAD
    return _CAT_GROUP.get(cat)


# ‏الحالات اللي جدول الأكل بيقول عليها "آمن" صراحة. للحالات دي الصنف
# لازم يكون متعلّم عليه؛ السكوت مش موافقة.
SAFE_KEY = {"سكري": "dm", "ضغط": "htn", "كلوي": "ckd", "قولون": "ibs",
            "قلب": "heart"}

# ‏كلمة من اللي العميل طلب يبعد عنه (أو من حساسيته) بتقفل **الفئة كلها**،
# مش الأصناف اللي الكلمة في اسمها بس. "مابياكلش سمك" لازم تمنع البلطي
# والباسا والكابوريا -- ومافيش واحد فيهم اسمه فيه "سمك". مع الحساسية
# الغلطة دي مش ذوق، دي خطر.
CATEGORY_TRIGGERS = {
    "fish": ("سمك", "اسماك", "سلمون", "تونه", "بلطي", "جمبري", "محار",
             "ماكولات بحريه"),
    "nut": ("مكسرات", "لوز", "كاجو", "بندق", "فستق", "جوز", "فول سوداني",
            "سوداني", "سمسم", "طحينه"),
    "meat": ("لحم", "لحوم", "لحمه"),
    "poultry": ("دجاج", "فراخ", "دواجن"),
    "legume": ("بقول", "بقوليات"),
    "dairy": ("حليب", "لبن", "البان", "جبن", "جبنه", "زبادي", "لاكتوز"),
    "grain": ("قمح", "جلوتين", "جلوتن"),
}
# ‏البيض مكتوب في الجدول تحت "ألبان"، وهو مش لبن: حساسية اللاكتوز
# ماتمنعوش، وحساسية البيض بتمنعه باسمه.
_EGG = "بيض"
# ‏من النشويات، دول اللي مافيهمش جلوتين. أي حاجة تانية بتتمنع مع القمح.
_GLUTEN_FREE = ("ارز", "ذره", "بطاط", "كينوا")

# ══ قواعد الحالات من الكتاب ══════════════════════════════════════════
#
# ‏الكلى -- [خ] ص ١٩٢-١٩٨، [CN] p.243-245
#   - البروتين محدد (٠٫٦ جم/كجم): البديل مايزودش بروتين عن الأصل.
#   - البوتاسيوم محدد (٢-٣ جم/يوم، [خ] ص ١٩٤). جدول [خ] ص ١٩٦: وحدة الألبان
#     ٣٤٠ ملجم، الخضروات ٢٤٠، الفواكه ١٢٠، اللحوم ١٢٠، الخبز ٢٥، الدهن صفر.
#     الألبان مقفولة كمجموعة (بوتاسيوم وفوسفور مع بعض).
#     الفواكه والخضروات: [UN] p.885 بيسمّي اللي بوتاسيومه عالي لدرجة إن
#     "regular use is discouraged": avocados, bananas, beets, brussels
#     sprouts, chard, dates, dried beans and peas, dried fruit, honeydew
#     melon, nectarines, oranges, potatoes, spinach, sweet potatoes,
#     tomatoes, winter squash, zucchini -- ومعاهم milk products, molasses,
#     nuts. وبيقول إن مريض الكلى "can consume most fruits and vegetables in
#     limited amounts". فالمسمّين دول مقفولين، والباقي بيتعرض بشرطين مع بعض:
#     مش في القايمة، **و**متعلّم عليه "آمن للكلى" في جدول الأكل. البديل
#     بنفس الكمية بتاعة الأصل، فمابيزودش اللي الخطة سمحت بيه.
#   - الفوسفور (ص ١٩٨): "اللبن، الجبن، البقول الجافة، الكولا، المكسرات
#     وزبدة الفول السوداني" -- يجب الإقلال. فمايتعرضوش كبديل.
#   - الصوديوم (ص ١٩٧): "معظم الأطعمة المعلبة والمجمدة والمصنعة".
KIDNEY_CLOSED_GROUPS = (MILK,)
KIDNEY_PROTEIN_SLACK_G = 1.0
_KIDNEY_BANNED = ("جبن", "معلب", "مجمد", "مكسرات", "سوداني", "لوز", "كاجو",
                  "بندق", "فستق", "عين جمل", "جوز", "لب ", "سمسم", "طحينه",
                  # ‏[UN] p.885 -- بوتاسيوم عالي
                  "افوكادو", "موز", "بنجر", "شمندر", "بروكسل", "سلق", "تمر",
                  "بلح", "زبيب", "مشمشيه", "قراصيا", "تين", "شمام",
                  "كانتالوب", "نكتارين", "برتقال", "بطاطس", "بطاطا", "سبانخ",
                  "طماطم", "قرع", "كوسه", "عسل اسود", "فول", "عدس",
                  "فاصوليا", "لوبيا", "حمص", "بسله")

# ‏القلب والكوليسترول -- [خ] ص ١٧٨، جدول "الأطعمة الممنوعة / المسموح بها".
#   ممنوع: الضأن، المخ، الكلاوي، الكبد، الريش؛ البط والحمام والأوز وجلد
#   الدجاج؛ الأسماك العالية الدهن والجمبري والسردين والتونة والكابوريا؛
#   صفار البيض (٣ مرات في الأسبوع بس)؛ الألبان والجبن كاملة الدسم والآيس
#   كريم؛ السمن والزبد والمهدرج؛ البسكويت والكيك.
#   مسموح: البتلو والعجالي خالي الدهن؛ الدجاج والرومي بدون جلد؛ السمك
#   الخالي من الدهن (البلطي، قشر البياض)؛ بياض البيض؛ اللبن والزبادي منزوع
#   الدسم والجبن القريش؛ الزيوت النباتية؛ الخضروات والفواكه الطازجة.
_HEART_BANNED = (
    "ضان", " مخ ", "كلاوي", "كبد", " ريش ", " بط ", "حمام", " اوز ", " وز ",
    "جلد",
    "جمبري", "سردين", "تونه", "كابوريا", "سلمون", "ماكريل", "صفار",
    "بيضه كامله", "كامل الدسم", "كامله الدسم", "ايس كريم", "سمن", "زبد",
    "مارجرين", "مهدرج", "قشده", "قشطه", "كريمه", "بسكويت", "كيك", "بيتي فور",
    "مسبك")
# ‏الجبن للقلب: القريش بس (ص ١٧٨). أي جبن تاني كامل الدسم لحد ما يثبت غير كده.
_HEART_CHEESE_OK = ("قريش", "خالي الدسم", "منزوع الدسم", "قليل الدسم", "لايت")

# ‏الضغط -- [خ] ص ١٦٩-١٧٢. جدول ص ١٧١: الأكل الطازج صوديومه قليل (خضار ٩
#   ملجم، فاكهة ٢، خبز ٥)، و"جزء كبير من الصوديوم يأتي من مركبات الصوديوم
#   المضافة للطعام أثناء عمليات الإنتاج والحفظ". أمثلة ص ١٧٢: ٣٠ جم جبنة
#   شيدر = ٤٠٠ ملجم، زيتونة كبيرة = ١٣٠، فنجان شوربة معلبة = ١١٠٠.
_SODIUM_BANNED = ("معلب", "مخلل", "زيتون", "صوص", "صلصه", "شوربه", "مرق",
                  "شيبسي", "مملح")

# ‏السكري -- [خ] ص ١٥٤-١٦٠. "تمنع الأطعمة العالية في محتواها من السكر".
#   الفواكه طازجة، مش "العصائر ... أو المعلبة في عصيرها أو المجففة"
#   (ص ١٥٩)؛ والقليل من "النشويات العالية الدهن والمحمرة" (ص ١٥٨).
#   والنشويات: [خ] ص ١٥٧ "مفيدة وضرورية لجميع الأفراد بما فيهم مريض البول
#   السكري"، والحبوب الكاملة أحسن (ص ١٥٨)؛ و[UN] p.821-822: الأكل العالي
#   الألياف وقليل التصنيع أثره أهدى من النشا المكرر. فالأبيض المكرر مقفول.
_DIABETES_BANNED = ("عصير", "تمر", "زبيب", "قراصيا", "مشمشيه", "عسل", "مربي",
                    "سكر", "شراب", "محمر", "مقلي", "فطير", "كيك", "بسكويت",
                    " ابيض ", "فينو", "بقسماط", "شابوره")

# ‏الحمل -- [UN] p.499.
#   الزئبق: "Avoid shark, swordfish, king mackerel, and tilefish"، وحدّ
#   أسبوعي للمأكولات البحرية (١٢ أونصة) وللتونة البيضاء (٦ أونصات). البديل
#   بيتعرض كل مرة ومانعرفش العميلة كلت كام الأسبوع ده، فالتونة والماكريل
#   مايتعرضوش خالص.
#   الليستيريا: "avoid ... feta cheese, brie, Camembert, and blue-veined
#   cheeses such as Roquefort"، واللانشون واللحوم المقددة (دول مقفولين
#   للكل أصلاً في _NOT_A_SWAP).
_PREGNANCY_BANNED = ("فيتا", " بري ", "كاممبير", "كامامبير", "روكفور",
                     "ريكفور", "ازرق", "ابو سيف", "قرش", "ماكريل", "تونه")

# ‏النقرس -- [UN] p.890، Table 28-8 "Foods High in Purines":
#   brains, kidney, liver, sweetbreads; game meat, gravies, meat extracts;
#   anchovies, herring, mackerel, sardines, scallops.
_GOUT_BANNED = (" مخ ", "كلاوي", "كبد", "مرق", "شوربه", "انشوجه", "رنجه",
                "ماكريل", "سردين", "اسكالوب")

# ‏الارتجاع -- [UN] p.736، Table 23-3 "Substances That Weaken Lower
#   Esophageal Sphincter Pressure": caffeine, chocolate, garlic, high-fat
#   foods, onions, peppermint and spearmint. والدهن: البديل مايزودش دهن.
_REFLUX_BANNED = ("شوكولات", "كاكاو", "ثوم", "بصل", "نعناع", "قهوه",
                  "كافيين")
REFLUX_FAT_SLACK_G = 2.0

# ‏القولون العصبي -- [UN] p.775: "avoid dietary substances that produce
#   excessive gas unless they can tolerate these foods"، وTable 24-2 p.758:
#   apples, broccoli, brussels sprouts, cabbage, cauliflower, corn, dried
#   beans and peas, fruit juices, leeks, onions, peanuts, pears, potatoes,
#   turnips. مانعرفش العميل بيستحمل إيه، فمايتعرضوش كبديل.
_GAS_BANNED = ("تفاح", "بروكلي", "بروكسل", "كرنب", "قرنبيط", "ذره", "فول",
               "عدس", "فاصوليا", "لوبيا", "حمص", "بسله", "عصير", "كرات",
               "بصل", "سوداني", "كمثري", "بطاطس", "لفت")

# ‏المرارة -- [UN] p.801: "a low-fat diet (with less than 30 percent of
#   total kcalories from fat) may be prescribed". البديل مايزودش دهن.
GALLBLADDER_FAT_SLACK_G = 1.0

# ‏تليف الكبد -- [UN] p.795-796: "restrict sodium as necessary to control
#   ascites; 2000 mg sodium per day". فبيتقفل عليه نفس قايمة الصوديوم.

# ‏السكري، تكملة -- [UN] p.821: "The amount of carbohydrate ingested has the
#   greatest influence on blood glucose levels after meals ... the
#   carbohydrate intake must be fairly consistent at meals and snacks".
#   فهامش الكارب للسكري أضيق من هامش الماكروز العام.
DIABETES_CARB_ABS_G = 3.0
DIABETES_CARB_REL = 0.10

_BOOK_RULES = {"حامل": _PREGNANCY_BANNED, "نقرس": _GOUT_BANNED,
               "ارتجاع": _REFLUX_BANNED, "قولون": _GAS_BANNED,
               "تليف": _SODIUM_BANNED, "كلوي": _KIDNEY_BANNED, "قلب": _HEART_BANNED,
               "كوليسترول": _HEART_BANNED, "ضغط": _SODIUM_BANNED,
               "سكري": _DIABETES_BANNED}


def _has(plain, word):
    """Is `word` in the name? A word written with spaces around it must
    stand alone: " ريش " (لحم الريش) is not the end of "قريش", and the
    cottage cheese the book allows a heart patient must not be caught by
    the cut of lamb it forbids."""
    core = meal_macros._norm(word.strip())
    if word != word.strip():
        return (" " + core + " ") in (" " + plain + " ")
    return core in plain


def _banned_by_book(food, key):
    """Does the textbook close this food to a client with this condition?"""
    plain = meal_macros._norm(food.get("n")) + " "
    if any(_has(plain, w) for w in _BOOK_RULES.get(key, ())):
        return True
    if key == "سكري" and "مكرون" in plain and not any(
            meal_macros._norm(w) in plain for w in ("قمح كامل", "اسمر")):
        # ‏قايمة الممنوعات بتاعة المولّد بتمنع "مكرونة بيضاء" لمريض السكر.
        # "مكرونة مسلوقة" في جدول الأكل هي نفسها باسم تاني، فكانت بتعدّي.
        return True
    if "جبن" in plain:
        if key in ("ضغط", "تليف"):
            # ‏الصوديوم مش الدسم: الفيتا اللايت والشيدر قليل الدسم لسه مالحين
            # ([خ] ص ١٧٢: ٣٠ جم شيدر = ٤٠٠ ملجم). القريش بس.
            return "قريش" not in plain
        if key in ("قلب", "كوليسترول"):
            return not any(meal_macros._norm(w) in plain
                           for w in _HEART_CHEESE_OK)
    return False


# ‏مش بدائل تتقال لعميل على نظام، لأي حد (ده ذوق الخطة مش حكم طبي):
#   - نيّ ودقيق، ومدخّن ومقلي ومصنّع ومجفف؛
#   - أحشاء (قوانص، لسان، كوارع...) -- أرقامها بتطابق ومحدش بيكتبها؛
#   - أطباق مركّبة ("مكرونة بالصلصة"، "بيتزا"): الطبق مش صنف، ومكوّناته
#     مابتتفحصش واحد واحد.
_NOT_A_SWAP = ("نئ", "نيء", "ني ", "طحين", "دقيق", "مدخن", "مملح", "مقلي",
               "محمر", "محلى", "بالسكر", "مجفف", "لانشون", "سجق", "بسطرمه",
               "مقدد", "قوانص", "لسان", "قلوب", "كوارع", "ممبار", "مخ ",
               "كرشه", "فشه", "بيتزا", "برياني", "بشاميل", "محشي", "كشري",
               "ساندوتش", "برجر", "نودلز", "سيريلاك", "كورن فليكس", "سلامي",
               "مرتديلا", "هوت دوج", "نقانق", "بيبروني")
_DISH = re.compile(r"(?:^|\s)بال\S+|(?:^|\s)مع\s")

CAL_TOLERANCE = 0.10          # ‏السعرات بعد تقريب الكمية
MACRO_ABS_G = 4.0             # ‏كل ماكرو: في حدود ٤ جرام...
MACRO_REL = 0.25              # ‏...أو ٢٥٪ من الأصل، الأكبر فيهم
MIN_GRAMS, MAX_GRAMS = 10, 600
MAX_RESULTS = 4
_ARABIC = re.compile("[؀-ۿ]")
_CERTAIN = ("grams", "count")


def _num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _portion(food, grams):
    share = grams / 100.0
    return {k: _num(food.get(k)) * share for k in ("cal", "p", "c", "f")}


def _round_grams(grams):
    step = 5 if grams >= 30 else 1
    return max(step, int(round(grams / step)) * step)


def read_item(text):
    """The food and amount an item names, or None when either is a guess."""
    # ‏طبق مركّب: "سلطة تونة كبيرة (تونة 150جم + خضار 230جم)". تقسيم الوجبة
    # على " + " بيقطعه من نص القوس، فالقطعة الأولى بتبقى "سلطة ... 150جم"
    # -- والـ١٥٠ دي بتاعة التونة مش السلطة. أي قطعة فيها قوس مش صنف واحد
    # بكمية واحدة، فمابتتقراش.
    if not text or any(ch in text for ch in "()（）"):
        return None
    food = meal_macros.find_food(text)
    if not food:
        return None
    grams, how = meal_macros.item_grams(text, food)
    if how not in _CERTAIN or grams <= 0:
        return None
    if group_of(food) is None:
        return None
    return {"food": food, "grams": grams, "macros": _portion(food, grams)}


def profile_from(data):
    """What the checks need to know about the client, from the plan's data."""
    from plan_engine import parse_user_exclusions
    data = data or {}
    allergies = data.get("allergies")
    keys = []
    for condition in data.get("symptoms") or []:
        key = CONDITION_MAP.get(condition)
        if key and key not in keys:
            keys.append(key)
    return {
        "conditions": keys,
        "exclusions": [w for w in parse_user_exclusions(
            data.get("notes", ""), data.get("disliked_foods", ""),
            allergies if isinstance(allergies, list) else []) if w],
        "keto": data.get("diet_plan_type") == "keto",
    }


def allowed_for(food, profile):
    """May this client eat this food at all? Conservative on purpose."""
    name = food.get("n") or ""
    safe = food.get("safe") or []
    for key in profile["conditions"]:
        if _contains_unsafe(name, key) or _banned_by_book(food, key):
            return False
        wanted = SAFE_KEY.get(key)
        if wanted and wanted not in safe:
            # ‏استثناء واحد: نشويات مريض السكري. جدول الأكل مافيهوش علامة
            # "آمن للسكري" على **ولا صنف** نشوي، فكان مريض السكر مابيتعرضلوش
            # بديل للخبز والأرز خالص -- والكتابين بيقولوا العكس ([خ] ص ١٥٧،
            # [UN] p.821). اللي بيحمي هنا مش العلامة: الكارب مطابق في حدود
            # ٣ جم، والأبيض المكرر مقفول، وقايمة الممنوعات لسه شغالة.
            if not (key == "سكري" and group_of(food) == BREAD):
                return False
    if profile.get("keto") and "keto" not in safe:
        return False
    plain = meal_macros._norm(name)
    words = [meal_macros._norm(w) for w in profile["exclusions"]]
    # ‏الجلوتين واللاكتوز بييجوا حساسية أو حالة؛ في الاتنين نفس القفل.
    # [UN] p.768، Table 24-6 "Gluten-Free Diet": القمح والشعير والبرغل
    # والسميد ممنوعين، والشوفان "questionable"؛ والمسموح الذرة والأرز
    # والبطاطس والكينوا.
    words += [meal_macros._norm(k) for k in ("جلوتين", "لاكتوز")
              if k in profile["conditions"]]
    for word in words:
        if word and word in plain:
            return False
    cat = food.get("cat")
    triggers = [meal_macros._norm(t) for t in CATEGORY_TRIGGERS.get(cat, ())]
    if any(t and (t == w or t in w or w in t) for t in triggers for w in words if w):
        if cat == "dairy" and _EGG in plain:
            return True
        if cat == "grain" and any(meal_macros._norm(g) in plain
                                  for g in _GLUTEN_FREE):
            return True
        return False
    return True


def _close(original, candidate):
    for key in ("p", "c", "f"):
        gap = abs(candidate[key] - original[key])
        if gap > max(MACRO_ABS_G, MACRO_REL * original[key]):
            return False
    if original["cal"] <= 0:
        return False
    return abs(candidate["cal"] - original["cal"]) <= CAL_TOLERANCE * original["cal"]


def _distance(original, candidate):
    return sum(abs(candidate[k] - original[k]) for k in ("p", "c", "f"))


def _head(name):
    """The word a food's name is built on: 'ارز' in 'أرز بسمتي مطبوخ'."""
    words = meal_macros._norm(name).split()
    return words[0] if words else ""


def _same_food(source, food):
    """Rice for rice is not a swap. Neither is chicken breast for chicken
    breast without the skin. The client asked what *else* they could eat."""
    head = _head(source.get("n"))
    if len(head) < 3:
        return False
    return head in meal_macros._norm(food.get("n")) or \
        _head(food.get("n")) in meal_macros._norm(source.get("n"))


def _amount_label(food, grams, ar=True):
    """'2 بيضة (100جم)' when the food comes in pieces, else '140جم'."""
    # ‏أسماء الوحدات في الجدول عربي بس ("شريحة"، "حفنة")، فالإنجليزي
    # بياخد الجرامات.
    for row in (food.get("units") or []) if ar else []:
        try:
            unit, each = row[0], float(row[1])
        except (TypeError, ValueError, IndexError):
            continue
        if each < 25:                    # ‏معلقة تونة مش وحدة تتاكل بيها وجبة
            continue
        unit = re.sub(r"\s*\(.*?\)", "", str(unit)).strip() or str(unit)
        count = grams / each
        nearest = round(count * 2) / 2.0
        if nearest >= 0.5 and abs(count - nearest) * each <= 0.08 * grams:
            shown = int(nearest) if nearest == int(nearest) else nearest
            return ("%s %s (%dجم)" if ar else "%s %s (%dg)") % (
                shown, unit, int(round(nearest * each))), nearest * each
    return ("%dجم" if ar else "%dg") % grams, float(grams)


def alternatives(text, profile, ar=True):
    """Swaps for one item of a meal. [] when nothing qualifies.

    Returns {"original": {...}, "options": [{name, amount, cal, p, c, f}]},
    or None when the item itself could not be read with certainty.
    """
    item = read_item(text)
    if item is None:
        return None
    source, want = item["food"], item["macros"]
    group = group_of(source)
    kidney = "كلوي" in profile["conditions"]
    original = {
        "name": source["n"] if ar else (source.get("en") or source["n"]),
        "cal": int(round(want["cal"])), "p": round(want["p"], 1),
        "c": round(want["c"], 1), "f": round(want["f"], 1)}
    if kidney and group in KIDNEY_CLOSED_GROUPS:
        # ‏[خ] ص ١٩٦ وص ٣٥-٣٦: بوتاسيوم المجموعات دي عالي ومتفاوت، وماعندناش
        # رقمه لكل صنف.
        return {"original": original, "options": []}

    found = []
    for food in food_data.FOODS:
        if food is source or group_of(food) != group:
            continue
        if not _ARABIC.search(food.get("n") or ""):
            continue                      # ‏أصناف مستوردة من غير اسم عربي
        padded = meal_macros._norm(food["n"]) + " "
        if _same_food(source, food) or _DISH.search(padded) or any(
                meal_macros._norm(w) in padded for w in _NOT_A_SWAP):
            continue
        per_100 = _num(food.get("cal"))
        if per_100 <= 0:
            continue
        grams = _round_grams(want["cal"] / per_100 * 100.0)
        if not MIN_GRAMS <= grams <= MAX_GRAMS:
            continue
        label, real_grams = _amount_label(food, grams, ar)
        got = _portion(food, real_grams)
        if not _close(want, got):
            continue
        if kidney and got["p"] > want["p"] + KIDNEY_PROTEIN_SLACK_G:
            continue                      # ‏[خ] ص ١٩٢: البروتين محدد
        conds = profile["conditions"]
        if "سكري" in conds and abs(got["c"] - want["c"]) > max(
                DIABETES_CARB_ABS_G, DIABETES_CARB_REL * want["c"]):
            continue                      # ‏[UN] p.821: الكارب ثابت
        if "ارتجاع" in conds and got["f"] > want["f"] + REFLUX_FAT_SLACK_G:
            continue                      # ‏[UN] p.736: high-fat foods
        if "مراره" in conds or "مرارة" in conds:
            if got["f"] > want["f"] + GALLBLADDER_FAT_SLACK_G:
                continue                  # ‏[UN] p.801: low-fat diet
        if not allowed_for(food, profile):
            continue
        name = food["n"] if ar else (food.get("en") or food["n"])
        # ‏نفس الفئة الأول (دجاج بدل دجاج)، وبعدين الأقرب في الماكروز.
        # ‏واللي الجدول مراجعه طبيًا (عليه علامات "آمن لـ") قبل اللي
        # اتضاف من غير مراجعة: دول الأصناف المعروفة اللي بتتكتب في الخطط.
        found.append(((food.get("cat") != source.get("cat"),
                       not food.get("safe"), _distance(want, got)), {
            "name": name, "amount": label,
            "cal": int(round(got["cal"])), "p": round(got["p"], 1),
            "c": round(got["c"], 1), "f": round(got["f"], 1),
            "_same": tuple(round(_num(food.get(k)), 1)
                           for k in ("cal", "p", "c", "f"))}))

    found.sort(key=lambda pair: pair[0])
    options, seen = [], set()
    for _, option in found:
        # ‏الجدول فيه نفس الصنف مكتوب مرتين ("جبن قريش" و"جبنة قريش")
        # بنفس الأرقام؛ العميل يشوفه مرة واحدة.
        same = option.pop("_same")
        if option["name"] in seen or same in seen:
            continue
        seen.update((option["name"], same))
        options.append(option)
        if len(options) == MAX_RESULTS:
            break
    return {"original": original, "options": options}

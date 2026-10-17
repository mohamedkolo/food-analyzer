# -*- coding: utf-8 -*-
"""‏قايمة مشتريات الأسبوع، من جرامات الجدول نفسه.

المشكلة
───────
‏الجدول بيقول للعميل "صدر دجاج مشوي ١٦٠جم" أربع مرات في الأسبوع، و"فول
مدمس ١٠٠جم" تلاتة. العميل بيمسك الورقة ويروح السوق -- ويقف. هو محتاج
يشتري كام؟ الجمع ده شغل بيتعمل بالإيد على ٢٨ خانة، أو مابيتعملش،
والنتيجة إنه يشتري بالتخمين: يجيب أكتر فيبوظ، أو أقل فالجدول يقف
نص الأسبوع.

‏والمعلومة موجودة بالكامل في الورقة أصلاً. دي عملية جمع.

من فين الأرقام
──────────────
‏meal_macros بيقسّم الوجبة أصناف وبيطلّع لكل صنف: كميته بالجرام، وإزاي
عرفها، والصنف اللي طابقه من جدول الأكل (٩٣٨ صنف). فالملف ده مابيكتبش
جدول أكل تاني -- بيستعمل اللي موجود، والتصنيف (دواجن، خضار، ألبان...)
جاي من نفس الجدول عشان القايمة تتقرا على ترتيب السوق.

الحاجة الوحيدة اللي محتاجة حرص
──────────────────────────────
‏item_grams بترجّع الكمية **ومصدرها**: "grams" يعني الرقم مكتوب في
الجدول، و"count" يعني عدد × وزن الوحدة، و"default" يعني **حصة
افتراضية** -- الصنف مالوش رقم في الجدول خالص.

‏والتالت ده مينفعش يتجمع. "قرفة" و"ليمون" و"ملح" مالهمش كمية مكتوبة،
فلو حطينا لهم الحصة الافتراضية وجمعناها على سبع أيام، القايمة هتقول
"قرفة ٣٥ جم" -- رقم إحنا اللي اخترعناه. والعميل هيشتري على أساسه.

‏فالأصناف دي بتتكتب بأسمها من غير كمية، تحت عنوان "حسب الحاجة". نفس
قاعدة الباركود: خانة فاضية أحسن من رقم مخترع.
"""

import re

# ‏ترتيب السوق مش ترتيب أبجدي: اللي بيتشترى من نفس الركن بيبقى مع بعضه.
_CATS = (
    ("poultry", "دواجن", "Poultry"),
    ("meat", "لحوم", "Meat"),
    ("fish", "أسماك", "Fish"),
    ("dairy", "ألبان وأجبان", "Dairy"),
    ("legume", "بقوليات", "Pulses"),
    ("grain", "نشويات وخبز", "Grains and bread"),
    ("veg", "خضار", "Vegetables"),
    ("fruit", "فاكهة", "Fruit"),
    ("nut", "مكسرات", "Nuts"),
    ("drink", "مشروبات", "Drinks"),
    ("spice", "بهارات وتوابل", "Spices"),
)
_OTHER = ("other", "متنوع", "Other")

# ‏مفاتيح الوجبات في اليوم. نفس اللي في followup.meals_in_plan -- أي
# نظام ممكن يكون له أسماء خانات مختلفة (سحور، قبل التمرين...).
_MEAL_KEYS = ("breakfast", "lunch", "dinner", "snack", "snack1", "snack2",
              "meal1", "meal2", "iftar", "suhoor", "pre_workout",
              "post_workout")

# ‏أصناف بتتباع بالعدد مش بالوزن. "٤ بيضات" أوضح من "٢٢٠ جم بيض" في
# السوق، فالعدد بيتحفظ لما يكون هو اللي مكتوب في الجدول.
_BY_COUNT = ("بيض", "بيضة", "موز", "تفاح", "برتقال", "ليمون", "خيار",
             "طماطم", "جزر", "تمر", "بلح", "كيوي", "رغيف", "خبز")

_COUNT_RX = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:حبة|حبات|ثمرة|ثمرات|"
                       r"قطعة|قطع|شريحة|شرائح|رغيف|أرغفة)?\s*$")


def _round_grams(grams):
    """‏رقم ينفع يتقال في السوق.

    ‏١٠٤٧ جم مش كمية حد بيشتريها -- بيشتري كيلو. والتقريب لفوق مش
    لأقرب: ناقص ٥٠ جم في آخر الأسبوع معناه وجبة ناقصة، وزيادة ٥٠ جم
    معناها ولا حاجة.
    """
    if grams <= 0:
        return 0
    if grams < 1000:
        step = 50 if grams >= 200 else 25
    else:
        step = 100
    return int(step * ((grams + step - 1) // step))


def _fmt_grams(grams, is_ar=True):
    g = _round_grams(grams)
    if g >= 1000:
        kg = g / 1000.0
        txt = ("%.1f" % kg).rstrip("0").rstrip(".")
        return "%s %s" % (txt, "كجم" if is_ar else "kg")
    return "%d %s" % (g, "جم" if is_ar else "g")


def _is_count_food(name):
    return any(k in (name or "") for k in _BY_COUNT)


def build(plan, lang="ar"):
    """‏قايمة مشتريات أسبوع من خطة.

    بترجّع:
      groups   [{key, title, items:[{name, qty, days}]}]
      loose    أصناف من غير كمية مكتوبة -- بتتعرض "حسب الحاجة"
      unknown  أصناف مش في جدول الأكل خالص
    """
    import meal_macros

    is_ar = (lang or "ar") == "ar"
    # ‏المفتاح هو اسم الصنف من الجدول (مش نص الوجبة): "صدر دجاج مشوي
    # ١٦٠جم" و"شرائح دجاج ١٣٠جم" الاتنين "صدر دجاج"، فبيتجمعوا.
    totals = {}
    loose = {}
    unknown = {}

    for day in (plan or []):
        if not isinstance(day, dict):
            continue
        for key in _MEAL_KEYS:
            text = day.get(key)
            if not isinstance(text, str) or not text.strip():
                continue
            for row in meal_macros.macros(text).get("items") or []:
                name = row.get("food")
                raw = str(row.get("text") or "").strip()
                # ‏٣٥ وجبة في القاعدة آخرها إيموجي لوحده ("... + 🍋").
                # المقطع ده مش صنف، فمالوش مكان لا في القايمة ولا في
                # اللي "مش متعرّف".
                if not re.search(r"[\w\u0600-\u06FF]", raw):
                    continue
                if not name:
                    # ‏مش في الجدول خالص. مابنخمّنش له كمية، بس
                    # مابنرميهوش كمان -- الدكتور لازم يشوف اللي القايمة
                    # معرفتوش عشان يزوّده بإيده.
                    if raw:
                        unknown[raw] = unknown.get(raw, 0) + 1
                    continue
                how = row.get("how")
                if how in ("grams", "count"):
                    cur = totals.setdefault(
                        name, {"grams": 0.0, "days": 0, "counts": 0.0,
                               "cat": None, "en": None})
                    cur["grams"] += float(row.get("grams") or 0)
                    cur["days"] += 1
                    # ‏العدد المكتوب بيتحفظ للأصناف اللي بتتباع بالعدد
                    m = _COUNT_RX.search(raw)
                    if how == "count" and m and _is_count_food(name):
                        try:
                            cur["counts"] += float(m.group(1))
                        except ValueError:
                            pass
                else:
                    # ‏"default" = حصة افتراضية، مش رقم من الجدول.
                    # جمعها بيخترع كمية. التفاصيل في أول الملف.
                    loose[name] = loose.get(name, 0) + 1

    # ‏التصنيف والاسم الإنجليزي من نفس جدول الأكل
    for name, cur in totals.items():
        food = meal_macros.find_food(name)
        cur["cat"] = (food or {}).get("cat") or "other"
        cur["en"] = (food or {}).get("en") or name

    groups = []
    for key, ar, en in _CATS + (_OTHER,):
        rows = []
        for name, cur in totals.items():
            if (cur["cat"] if key != "other" else
                    (cur["cat"] if cur["cat"] in
                     [c[0] for c in _CATS] else "other")) != key:
                continue
            if cur["counts"] >= 1 and _is_count_food(name):
                qty = "%d %s" % (int(round(cur["counts"])),
                                 "حبة" if is_ar else "pcs")
            else:
                qty = _fmt_grams(cur["grams"], is_ar)
            rows.append({"name": name if is_ar else cur["en"],
                         "qty": qty, "days": cur["days"]})
        if rows:
            rows.sort(key=lambda r: (-r["days"], r["name"]))
            groups.append({"key": key, "title": ar if is_ar else en,
                           "items": rows})

    # ‏صنف اتكتب بكميته في يوم وبالحصة الافتراضية في يوم تاني (زيت
    # الزيتون والبيض بيحصلهم كده) كان بيتعرض مرتين: مرة برقمه ومرة
    # تحت "حسب الحاجة". الرقم أولى -- والسطر التاني بيلخبط بس.
    for name in list(loose):
        if name in totals:
            loose.pop(name, None)

    def _names(src):
        out = []
        for name, times in sorted(src.items(), key=lambda kv: (-kv[1], kv[0])):
            food = meal_macros.find_food(name) if src is loose else None
            out.append({"name": (name if is_ar else
                                 ((food or {}).get("en") or name)),
                        "days": times})
        return out

    return {"groups": groups, "loose": _names(loose),
            "unknown": _names(unknown)}

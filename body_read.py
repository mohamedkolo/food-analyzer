# -*- coding: utf-8 -*-
"""‏قراءة ورقة تحليل الجسم للعميل: يعني إيه، وتشرحها إزاي.

الدكتور بيقرا الورقة قدام العميل. الملف ده بياخد نفس الأرقام اللي في
الفورم (أو اللي اتقرت من صورة الورقة) وبيرجّع تلات حاجات:

    rows    كل رقم، في أنهي نطاق، ويعني إيه بجملة
    focus   النقاط اللي تركّز عليها، مرتّبة بالأهم طبياً
    script  السيناريو: تشرح الورقة بأي ترتيب، وتقول إيه في كل خطوة

**اللي الملف ده مابيعملهوش:** مابيشخّصش، ومابيوصفش دوا، ومابيقولش رقم
مش متحسوب من الأرقام اللي دخلت. النطاقات دي مراجع عامة منشورة (تحت)،
والقرار في الآخر قرار الدكتور -- فكل نتيجة بتيجي ومعاها الرقم والنطاق
اللي اتقارن بيه، عشان يكون شايف على أساس إيه.

المراجع:
  نسبة الدهون   نطاقات ACE (American Council on Exercise) حسب النوع
  BMI           تصنيف منظمة الصحة العالمية
  الدهون الحشوية مقياس InBody (١-٢٠): ١-٩ طبيعي، ١٠-١٤ مرتفع، ١٥+ عالي
  العضل         SMI = كتلة العضل ÷ (الطول بالمتر)²، حدود Janssen 2002
  الماء         نسبة الماء من الكتلة الخالية من الدهون، الطبيعي ٧٠-٧٥٪
"""

# ‏"انثى"/"ذكر" زي ما الفورم بيبعتها، و"female"/"male" زي ما القراءة بترجّعها.
# ‏"woman" لازم تبقى قبل "man": "man" جوّه "woman".
_FEMALE = ("انثى", "أنثى", "female", "woman", "women", "f", "w")


_MALE = ("ذكر", "male", "man", "m")


# ‏الحروف المفردة بتتطابق بالكامل بس. "f" لو اتقارنت كجزء من الكلمة،
# أي قيمة فيها حرف f بتبقى أنثى -- "unspecified" مثلاً.
_SHORT = {"f": "female", "w": "female", "m": "male"}


def _sex(gender):
    """‏"female" / "male" / None. الـNone مهم: نطاقات الدهون بتفرق كتير
    بين الاتنين (٣٢٪ للأنثى مقابل ٢٥٪ للذكر)، فمن غير النوع مانحكمش."""
    low = str(gender or "").strip().lower()
    if not low:
        return None
    if low in _SHORT:
        return _SHORT[low]
    if "نث" in low or any(word in low for word in _FEMALE if len(word) > 1):
        return "female"
    if any(word in low for word in _MALE if len(word) > 1):
        return "male"
    return None


def _is_female(gender):
    return _sex(gender) == "female"


def _num(value):
    try:
        if value is None or value == "":
            return None
        out = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None


def _pick(ar, en, is_ar):
    return ar if is_ar else en


_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"


def _step(number, is_ar):
    """‏ترقيم الخطوات. لازم يبقى بأرقام عربية في النص العربي -- الترقيم
    كان بيطلع «١. ٢. ٣. 5. 6.» لما الرقم كان بيتحسب في بايثون."""
    if not is_ar:
        return "%d." % number
    return "".join(_ARABIC_DIGITS[int(d)] for d in str(number)) + "."


# ═══ النطاقات ═══════════════════════════════════════════════════════
# ‏كل نطاق: (الحد الأعلى, المفتاح, عربي, إنجليزي, النوع)
# ‏النوع: good = في مكانه، watch = محتاج شغل، high/low = بعيد عن الطبيعي

_FAT_FEMALE = [
    (14.0, "low", "أقل من اللازم", "below healthy", "low"),
    (21.0, "athletic", "مستوى رياضي", "athletic", "good"),
    (25.0, "fit", "لياقة عالية", "fit", "good"),
    (32.0, "acceptable", "مقبولة", "acceptable", "watch"),
    (None, "obese", "في نطاق السمنة", "in the obese range", "high"),
]
_FAT_MALE = [
    (6.0, "low", "أقل من اللازم", "below healthy", "low"),
    (14.0, "athletic", "مستوى رياضي", "athletic", "good"),
    (18.0, "fit", "لياقة عالية", "fit", "good"),
    (25.0, "acceptable", "مقبولة", "acceptable", "watch"),
    (None, "obese", "في نطاق السمنة", "in the obese range", "high"),
]

_BMI = [
    (18.5, "under", "نقص وزن", "underweight", "low"),
    (25.0, "normal", "طبيعي", "normal", "good"),
    (30.0, "over", "زيادة وزن", "overweight", "watch"),
    (35.0, "obese1", "سمنة درجة أولى", "obesity class I", "high"),
    (40.0, "obese2", "سمنة درجة تانية", "obesity class II", "high"),
    (None, "obese3", "سمنة مفرطة", "obesity class III", "high"),
]

_VISCERAL = [
    (10.0, "normal", "طبيعي", "normal", "good"),
    (15.0, "high", "مرتفع", "high", "watch"),
    (None, "very_high", "مرتفع جداً", "very high", "high"),
]

# ‏أول هدف واقعي لنسبة الدهون: آخر النطاق المقبول -- يعني يخرج من نطاق
# السمنة. والتاني: وسط النطاق الصحي.
_GOAL_FAT = {"female": (31.0, 27.0), "male": (24.0, 20.0)}

# ‏حدود SMI (كتلة العضل ÷ الطول²) -- (طبيعي من, نقص خفيف من)
_SMI = {"female": (6.76, 5.76), "male": (10.76, 8.51)}


def _band(value, table):
    for top, key, ar, en, kind in table:
        if top is None or value < top:
            return {"key": key, "ar": ar, "en": en, "kind": kind}
    return None


def _row(label_ar, label_en, value, unit, band, means_ar, means_en, is_ar):
    return {
        "label": _pick(label_ar, label_en, is_ar),
        "value": value,
        "unit": unit,
        "band": _pick(band["ar"], band["en"], is_ar) if band else None,
        "kind": band["kind"] if band else "plain",
        "means": _pick(means_ar, means_en, is_ar),
    }


def _fmt(value, places=1):
    if value is None:
        return ""
    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))
    return ("%%.%df" % places) % value


def explain(data, is_ar=True):
    """‏أرقام الفورم -> شرح للعميل. مافيش نداء لأي خدمة، كله حساب."""
    sex = _sex(data.get("gender"))
    # ‏من غير نوع: بنعرض الأرقام ومانحكمش على النطاق. نطاق دهون الأنثى
    # بيبدأ سمنة عند ٣٢٪ والذكر عند ٢٥٪ -- حكم بالغلط هنا أسوأ من مفيش حكم.
    sex_known = sex is not None
    female = sex == "female"
    if not sex_known:
        sex = "female"
    weight = _num(data.get("weight"))
    height = _num(data.get("height"))
    fat_pct = _num(data.get("fat_pct"))
    bmi = _num(data.get("bmi"))
    bmr = _num(data.get("bmr"))
    tdee = _num(data.get("tdee"))
    muscle = _num(data.get("muscle_mass"))
    visceral = _num(data.get("visceral_fat"))
    water = _num(data.get("body_water"))

    # ‏الـBMI بيتحسب لو مش مكتوب -- الوزن والطول كفاية.
    if bmi is None and weight and height:
        bmi = weight / ((height / 100.0) ** 2)

    rows, focus, script, targets, caveats = [], [], [], [], []
    missing = []

    # ═══ تركيب الوزن: ده أهم سطر في الشرح كله ═══
    fat_mass = lean_mass = None
    if weight and fat_pct:
        fat_mass = weight * fat_pct / 100.0
        lean_mass = weight - fat_mass

    if weight:
        rows.append(_row(
            "الوزن", "Weight", _fmt(weight), _pick("كجم", "kg", is_ar), None,
            "رقم واحد، وجواه حاجتين مختلفتين تماماً: دهون وكتلة خالية من الدهون.",
            "One number holding two different things: fat, and fat-free mass.",
            is_ar))

    if fat_mass is not None:
        band = _band(fat_pct, _FAT_FEMALE if female else _FAT_MALE) if sex_known else None
        rows.append(_row(
            "نسبة الدهون", "Body fat", _fmt(fat_pct), "%", band,
            "يعني %s كجم دهون، و%s كجم كتلة خالية من الدهون (عضل وعظم وماء)."
            % (_fmt(fat_mass), _fmt(lean_mass)),
            "That is %s kg of fat and %s kg of fat-free mass (muscle, bone, water)."
            % (_fmt(fat_mass), _fmt(lean_mass)),
            is_ar))
    else:
        missing.append(_pick("نسبة الدهون", "body fat", is_ar))

    if bmi:
        band = _band(bmi, _BMI)
        rows.append(_row(
            "BMI", "BMI", _fmt(bmi), _pick("كجم/م²", "kg/m2", is_ar), band,
            "مقياس وزن على طول، مابيفرّقش بين عضل ودهن -- فبنقراه جنب نسبة الدهون مش لوحده.",
            "A weight-for-height number. It cannot tell muscle from fat, so it is read next to body fat, never alone.",
            is_ar))

    if visceral:
        band = _band(visceral, _VISCERAL)
        rows.append(_row(
            "الدهون الحشوية (مستوى)", "Visceral fat (level)", _fmt(visceral),
            "", band,
            "دهون حوالين الأعضاء جوّه البطن. دي اللي مرتبطة بالسكر والضغط ودهون الكبد أكتر من الوزن نفسه.",
            "Fat around the organs inside the abdomen. This is what tracks with blood sugar, blood pressure and fatty liver -- more than weight does.",
            is_ar))

    if muscle and height and sex_known:
        smi = muscle / ((height / 100.0) ** 2)
        normal_from, mild_from = _SMI[sex]
        if smi >= normal_from:
            band = {"ar": "في النطاق الطبيعي", "en": "within normal", "kind": "good"}
        elif smi >= mild_from:
            band = {"ar": "أقل من الطبيعي شوية", "en": "slightly below normal", "kind": "watch"}
        else:
            band = {"ar": "أقل من الطبيعي", "en": "below normal", "kind": "low"}
        rows.append(_row(
            "كتلة العضل", "Skeletal muscle", _fmt(muscle),
            _pick("كجم", "kg", is_ar), band,
            "نسبةً للطول = %s (الطبيعي %s وأكتر). دي اللي بتحرق، وحمايتها وإنت بتنزل هي الشغل كله."
            % (_fmt(smi, 2), _fmt(normal_from, 2)),
            "Relative to height = %s (normal is %s and up). This is the tissue that burns, and protecting it while losing is the whole job."
            % (_fmt(smi, 2), _fmt(normal_from, 2)),
            is_ar))

    if water and lean_mass:
        share = water / lean_mass * 100.0
        if share < 70:
            band = {"ar": "أقل من المتوقع", "en": "lower than expected", "kind": "watch"}
        elif share > 75:
            band = {"ar": "أعلى من المتوقع", "en": "higher than expected", "kind": "watch"}
        else:
            band = {"ar": "طبيعي", "en": "normal", "kind": "good"}
        rows.append(_row(
            "ماء الجسم", "Body water", _fmt(water), _pick("لتر", "L", is_ar), band,
            "%s%% من كتلتك الخالية من الدهون (الطبيعي ٧٠-٧٥%%). بنقيسه على الكتلة الخالية مش على الوزن، "
            "لأن الدهون فيها ماء قليل -- فنسبة الماء من الوزن بتبان أقل كل ما الدهون تزيد."
            % _fmt(share),
            "%s%% of your fat-free mass (normal is 70-75%%). It is measured against fat-free mass, "
            "not total weight: fat holds little water, so water-as-a-share-of-weight looks low whenever fat is high."
            % _fmt(share),
            is_ar))

    if bmr:
        extra = ""
        if tdee and tdee > bmr:
            extra = _pick(
                " ومع حركتك اليومية الحرق بيبقى حوالي %s كالوري." % _fmt(tdee),
                " With your daily activity that becomes about %s kcal." % _fmt(tdee), is_ar)
        rows.append(_row(
            "معدل الحرق وقت الراحة", "Resting metabolic rate", _fmt(bmr),
            _pick("كالوري", "kcal", is_ar), None,
            "ده اللي جسمك بيحرقه وهو ساكن تماماً." + extra,
            "This is what the body burns at complete rest." + extra,
            is_ar))

    # ═══ الهدف بالأرقام: أقوى حاجة تقولها للعميل ═══
    #
    # ‏لو العضل ثابت والنازل دهون بس، الوزن عند نسبة دهون معيّنة بيبقى:
    #     الوزن = الكتلة الخالية ÷ (١ - نسبة الدهون المستهدفة)
    # ‏الرقم ده بيحوّل "عايز أنزل" لهدف محدد، وبيشرح ليه الميزان لوحده
    # مش مقياس: ممكن الوزن ينزل ٣ كيلو منهم كيلو عضل -- ودي خسارة.
    if lean_mass and fat_pct and sex_known:
        for goal in _GOAL_FAT[sex]:
            if fat_pct - goal < 1.0:
                continue
            target_weight = lean_mass / (1.0 - goal / 100.0)
            targets.append({
                "fat_pct": _fmt(goal),
                "weight": _fmt(target_weight),
                "drop": _fmt(weight - target_weight),
            })

    # ═══ النقاط اللي يركّز عليها، مرتّبة بالأهم طبياً ═══
    if visceral and visceral >= 10:
        focus.append({
            "title": _pick("الدهون الحشوية قبل الوزن", "Visceral fat before weight", is_ar),
            "why": _pick(
                "مستوى %s. دي الدهون اللي بتفرق في تحليل السكر والدهون والضغط، "
                "وبتستجيب بسرعة لنقص السعرات وتقليل السكريات السريعة." % _fmt(visceral),
                "Level %s. This is the fat that moves blood sugar, lipids and blood pressure, "
                "and it responds fast to a calorie deficit and cutting fast sugars." % _fmt(visceral),
                is_ar),
            "do": _pick("قوله: أول حاجة هتتحسّن دي، وهتحسّها في التحاليل قبل الميزان.",
                        "Tell them: this is the first thing that improves, and it shows in labs before the scale.",
                        is_ar)})

    if fat_pct and sex_known:
        band = _band(fat_pct, _FAT_FEMALE if female else _FAT_MALE)
        if band["kind"] == "high":
            focus.append({
                "title": _pick("الشغل على الدهون مش على الوزن", "Work on fat, not weight", is_ar),
                "why": _pick(
                    "نسبة الدهون %s%% و%s. عند العميل ده الوزن مؤشر ضعيف، "
                    "ونسبة الدهون هي اللي بتتحرك بمعنى." % (_fmt(fat_pct), band["ar"]),
                    "Body fat is %s%% and %s. For this client weight is a weak signal; "
                    "body fat is what moves meaningfully." % (_fmt(fat_pct), band["en"]),
                    is_ar),
                "do": _pick("قوله: هنقيس نسبة الدهون والمقاسات كل ٢-٤ أسابيع، مش الميزان كل يوم.",
                            "Tell them: we measure body fat and tape measurements every 2-4 weeks, not the scale daily.",
                            is_ar)})
        elif band["kind"] == "low":
            focus.append({
                "title": _pick("الدهون أقل من اللازم", "Body fat is below healthy", is_ar),
                "why": _pick(
                    "نسبة الدهون %s%%. النزول أكتر مش هدف صحي هنا، والشغل يبقى على العضل والأداء."
                    % _fmt(fat_pct),
                    "Body fat is %s%%. Losing more is not a healthy goal here; the work is muscle and performance."
                    % _fmt(fat_pct), is_ar),
                "do": _pick("قوله: مش هنخفّض تاني، هنبني.", "Tell them: we are not cutting further, we are building.", is_ar)})

    if muscle and height and sex_known:
        smi = muscle / ((height / 100.0) ** 2)
        if smi < _SMI[sex][0]:
            focus.append({
                "title": _pick("حماية العضل وإحنا بننزّل", "Protect muscle while losing", is_ar),
                "why": _pick(
                    "كتلة العضل نسبةً للطول %s، والطبيعي %s وأكتر. النزول السريع بياخد من العضل، "
                    "والعضل اللي بيروح بيقلّل الحرق فيحصل ثبات." % (_fmt(smi, 2), _fmt(_SMI[sex][0], 2)),
                    "Muscle relative to height is %s against a normal of %s and up. Fast loss takes muscle, "
                    "and lost muscle lowers the burn and stalls progress." % (_fmt(smi, 2), _fmt(_SMI[sex][0], 2)),
                    is_ar),
                "do": _pick("قوله: البروتين في كل وجبة + تمرين مقاومة ٢-٣ مرات أسبوعياً، مش كارديو بس.",
                            "Tell them: protein at every meal plus resistance training 2-3 times a week, not cardio alone.",
                            is_ar)})

    # ‏وزن طبيعي ودهون عالية: الحالة اللي الميزان بيخفيها تماماً.
    if bmi and fat_pct and sex_known:
        fat_band = _band(fat_pct, _FAT_FEMALE if female else _FAT_MALE)
        if bmi < 25 and fat_band["kind"] == "high":
            focus.append({
                "title": _pick("وزنه طبيعي ودهونه عالية", "Normal weight, high fat", is_ar),
                "why": _pick(
                    "الـBMI %s (طبيعي) ونسبة الدهون %s%%. الميزان مبيّنش الحالة دي خالص، "
                    "والعميل بيستغرب لما تقوله فيه شغل." % (_fmt(bmi), _fmt(fat_pct)),
                    "BMI is %s (normal) while body fat is %s%%. The scale hides this completely, "
                    "and the client is surprised to hear there is work to do." % (_fmt(bmi), _fmt(fat_pct)),
                    is_ar),
                "do": _pick("قوله: وزنك مش المشكلة، تركيبه هو الشغل. الهدف نبدّل دهون بعضل بنفس الوزن تقريباً.",
                            "Tell them: your weight is not the problem, its composition is. The goal is to trade fat for muscle at roughly the same weight.",
                            is_ar)})
        elif bmi >= 25 and fat_band["kind"] == "good":
            focus.append({
                "title": _pick("الـBMI بيقول زيادة والدهون تقول لأ", "BMI says overweight, fat says otherwise", is_ar),
                "why": _pick(
                    "الـBMI %s ونسبة الدهون %s%% وهي في نطاق كويس. الزيادة جاية من كتلة خالية من الدهون."
                    % (_fmt(bmi), _fmt(fat_pct)),
                    "BMI is %s while body fat is %s%%, which sits in a good range. The excess is fat-free mass."
                    % (_fmt(bmi), _fmt(fat_pct)), is_ar),
                "do": _pick("قوله: مانشتغلش على رقم الـBMI هنا.", "Tell them: we do not chase the BMI number here.", is_ar)})

    if bmi and bmi >= 35:
        focus.append({
            "title": _pick("الوزن في مرحلة محتاجة متابعة طبية", "Weight is at a level needing medical follow-up", is_ar),
            "why": _pick("الـBMI %s. المرحلة دي بيتراجع فيها السكر والضغط ودهون الكبد والنوم مع الطبيب."
                         % _fmt(bmi),
                         "BMI is %s. At this level blood sugar, blood pressure, liver fat and sleep are reviewed with a physician."
                         % _fmt(bmi), is_ar),
            "do": _pick("قوله: الخطة ماشية، وبالتوازي التحاليل والمتابعة مع الدكتور.",
                        "Tell them: the plan runs, and labs and medical follow-up run alongside it.", is_ar)})

    if water and lean_mass:
        share = water / lean_mass * 100.0
        if share > 75:
            focus.append({
                "title": _pick("احتمال احتباس سوائل", "Possible fluid retention", is_ar),
                "why": _pick("الماء %s%% من الكتلة الخالية من الدهون، أعلى من المتوقع. "
                             "ساعات بيكون ملح أو دورة شهرية أو دوا، وساعات محتاج مراجعة."
                             % _fmt(share),
                             "Water is %s%% of fat-free mass, above what is expected. Sometimes salt, "
                             "the menstrual cycle or a medication; sometimes it needs review." % _fmt(share),
                             is_ar),
                "do": _pick("قوله: لو الوزن بيتقلّب كيلو ونص في اليوم، ده ماء مش دهون.",
                            "Tell them: if weight swings a kilo and a half in a day, that is water, not fat.",
                            is_ar)})

    # ═══ السيناريو: ترتيب الكلام قدام العميل ═══
    def _add(ar, en):
        head = _step(len(script) + 1, is_ar)
        script.append(head + " " + _pick(ar, en, is_ar))

    _add("ابدأ بالوزن وقوله إنه رقم واحد مش قصة كاملة: «الميزان بيقولنا كام، ومابيقولناش إيه.»",
         "Start with the weight and say it is one number, not the story: the scale says how much, not what.")
    if fat_mass is not None:
        _add("قسّم الوزن قدامه: «من الـ%s كجم دي، %s كجم دهون و%s كجم كتلة خالية من الدهون.» "
             "قول الرقمين بصوت عالي -- دي اللحظة اللي العميل بيفهم فيها الورقة."
             % (_fmt(weight), _fmt(fat_mass), _fmt(lean_mass)),
             "Split the weight in front of them: of these %s kg, %s kg is fat and %s kg is fat-free mass. "
             "Say both numbers out loud -- this is the moment the sheet makes sense to them."
             % (_fmt(weight), _fmt(fat_mass), _fmt(lean_mass)))
    if targets:
        first = targets[0]
        _add("حوّل الهدف لرقم: «لو نزّلنا دهون بس والعضل ثابت، عند نسبة دهون %s%% وزنك يبقى %s كجم — "
             "يعني %s كجم، كلهم دهون.» ده بيخلّي الهدف واضح ومقيس."
             % (first["fat_pct"], first["weight"], first["drop"]),
             "Turn the goal into a number: if we lose fat only and hold muscle, at %s%% body fat your weight is "
             "%s kg -- a drop of %s kg, all of it fat. This makes the goal concrete and measurable."
             % (first["fat_pct"], first["weight"], first["drop"]))
    if visceral:
        _add("الدهون الحشوية: قوله دي الرقم اللي بيفرق في صحته مش في شكله، ودي أول حاجة بتتحسّن.",
             "Visceral fat: tell them this is the number that matters for health rather than looks, "
             "and it is the first to improve.")
    _add("اتفق على مقياس المتابعة قبل ما يمشي: نسبة الدهون والمقاسات كل ٢-٤ أسابيع. "
         "الميزان اليومي بيتقلّب بالماء والملح والأكل في المعدة، والعميل بيزهق منه.",
         "Agree on the measure before they leave: body fat and tape measurements every 2-4 weeks. "
         "A daily scale swings with water, salt and food in the gut, and it wears the client out.")
    _add("الرقم الواقعي: نزول ٠.٥ إلى ١٪ من الوزن في الأسبوع. أسرع من كده بياخد من العضل.",
         "The realistic rate: 0.5 to 1% of body weight a week. Faster than that comes out of muscle.")

    # ═══ الجملة الأولى ═══
    if fat_pct and weight:
        band = _band(fat_pct, _FAT_FEMALE if female else _FAT_MALE) if sex_known else None
        tail = (_pick(" (%s)" % band["ar"], " (%s)" % band["en"], is_ar)) if band else ""
        headline = _pick(
            "وزن %s كجم، منهم %s كجم دهون و%s كجم كتلة خالية من الدهون — نسبة الدهون %s%%%s."
            % (_fmt(weight), _fmt(fat_mass), _fmt(lean_mass), _fmt(fat_pct), tail),
            "Weight %s kg: %s kg of it fat and %s kg fat-free -- body fat %s%%%s."
            % (_fmt(weight), _fmt(fat_mass), _fmt(lean_mass), _fmt(fat_pct), tail),
            is_ar)
    elif weight and bmi:
        headline = _pick(
            "وزن %s كجم و BMI %s. نسبة الدهون مش مكتوبة، فالتقسيم بين دهون وعضل مش محسوب."
            % (_fmt(weight), _fmt(bmi)),
            "Weight %s kg, BMI %s. Body fat is missing, so the fat/muscle split is not computed."
            % (_fmt(weight), _fmt(bmi)), is_ar)
    else:
        headline = _pick("الأرقام مش كفاية للشرح -- اكتب الوزن والطول على الأقل.",
                         "Not enough numbers to explain -- enter at least weight and height.", is_ar)

    # ═══ اللي ناقص واللي الملف ده مش بيعمله ═══
    if not sex_known:
        caveats.append(_pick(
            "النوع مش مختار، ونطاقات الدهون والعضل بتفرق كتير بين الذكر والأنثى -- "
            "فعرضت الأرقام من غير حكم على النطاق. اختار النوع وهيتحدّد.",
            "Sex is not selected, and the fat and muscle ranges differ a lot between male and female -- "
            "so the numbers are shown without a range verdict. Pick the sex and it resolves.",
            is_ar))
    if not fat_pct:
        caveats.append(_pick(
            "نسبة الدهون مش مدخّلة، فالوزن هنا مش متقسّم لدهون وعضل — وده أهم سطر في الشرح.",
            "Body fat was not entered, so the weight is not split into fat and muscle -- the most useful line in the explanation.",
            is_ar))
    if not visceral:
        missing.append(_pick("الدهون الحشوية", "visceral fat", is_ar))
    if not muscle:
        missing.append(_pick("كتلة العضل", "skeletal muscle", is_ar))
    caveats.append(_pick(
        "النطاقات دي مراجع عامة (ACE للدهون، منظمة الصحة للـBMI، مقياس InBody للحشوية). "
        "مابتشخّصش، والقرار قرارك.",
        "These are general reference ranges (ACE for fat, WHO for BMI, the InBody scale for visceral fat). "
        "They do not diagnose; the call is yours.",
        is_ar))

    return {"headline": headline, "rows": rows, "focus": focus, "script": script,
            "targets": targets, "caveats": caveats,
            "missing": [m for m in missing if m]}


def as_text(result, is_ar=True):
    """‏نفس الشرح كنص سادة -- الدكتور بينسخه ويبعته واتساب للعميل."""
    out = [result["headline"], ""]
    for row in result["rows"]:
        value = ("%s %s" % (row["value"], row["unit"])).strip()
        band = (" — %s" % row["band"]) if row["band"] else ""
        out.append("• %s: %s%s" % (row["label"], value, band))
        out.append("  %s" % row["means"])
    if result["targets"]:
        out.append("")
        out.append(_pick("الهدف بالأرقام:", "The goal in numbers:", is_ar))
        for target in result["targets"]:
            out.append(_pick(
                "• عند نسبة دهون %s%%: الوزن %s كجم (نزول %s كجم دهون)"
                % (target["fat_pct"], target["weight"], target["drop"]),
                "• At %s%% body fat: weight %s kg (a %s kg drop, all fat)"
                % (target["fat_pct"], target["weight"], target["drop"]), is_ar))
    if result["focus"]:
        out.append("")
        out.append(_pick("النقاط اللي تركّز عليها:", "What to focus on:", is_ar))
        for item in result["focus"]:
            out.append("• %s — %s" % (item["title"], item["why"]))
            out.append("  %s" % item["do"])
    out.append("")
    out.append(_pick("السيناريو:", "How to walk through it:", is_ar))
    out.extend(result["script"])
    return "\n".join(out)

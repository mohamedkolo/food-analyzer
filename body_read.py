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


def _step(number, is_ar):
    """‏ترقيم خطوات النص المنسوخ.

    ‏كان بأرقام عربية في النص العربي، وبقيت لاتينية: كل رقم جوّه
    النص (الوزن، النسبة، السعرات) بيتكتب لاتيني من بايثون، فالترقيم
    العربي كان بيخلي الورقة نوعين أرقام في نفس السطر."""
    return "%d." % number


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


def _script_free(_say, weight, fat_mass, lean_mass, fat_pct, targets, weeks,
                 sex_known, female, is_ar, _fmt):
    """‏فحص سريع بدون اسم ولا رقم.

    ‏الهدف إن العميل يشوف الفرق بين "أعرف وزني" و"أعرف تركيبي وأقيسه"،
    ويقرر هو. الإقناع من الأرقام اللي قدامه، مش من تهويل: مافيش كلام عن
    مرض ولا خطر، ومافيش وعد بمدة أقصر من الواقع.
    """
    steps = []
    steps.append(_say(
        "الافتتاح", "Opening",
        "«الميزان بيقولك رقم واحد. الورقة دي بتقولك الرقم ده جوّاه إيه.»",
        "\"The scale gives you one number. This sheet tells you what is inside it.\"",
        "ابدأ بده. بيفتح الباب للرقم اللي بعده.",
        "Start here. It opens the door for the number that follows."))

    if fat_mass is not None:
        steps.append(_say(
            "التقسيم", "The split",
            "«وزنك %s كجم: منهم %s دهون، و%s عضل وعضم وماء.»"
            % (_fmt(weight), _fmt(fat_mass), _fmt(lean_mass)),
            "\"You weigh %s kg: %s of that is fat, and %s is muscle, bone and water.\""
            % (_fmt(weight), _fmt(fat_mass), _fmt(lean_mass)),
            "قول الرقمين بصوت عالي.",
            "Say both numbers out loud."))

    if fat_pct and sex_known and fat_mass is not None:
        band_top = 31.0 if female else 24.0
        if fat_pct > band_top:
            steps.append(_say(
                "المعنى", "What it means",
                "«الشغل على الـ%s دهون دي. مش على الـ%s كلهم.»"
                % (_fmt(fat_mass), _fmt(weight)),
                "\"The work is on those %s of fat. Not on the whole %s.\""
                % (_fmt(fat_mass), _fmt(weight)),
                "بيحوّل «إنت تقيل» لرقم واحد محدد.",
                "It turns \"you are heavy\" into one specific number."))

    if targets:
        first = targets[0]
        steps.append(_say(
            "الهدف بالأرقام", "The goal in numbers",
            "«لو نزّلنا دهون بس، توصل %s كجم. يعني %s كجم كلهم دهون، "
            "والرقم ده محسوب من أرقامك.»" % (first["weight"], first["drop"]),
            "\"If we lose fat only, you land at %s kg. That is %s kg, all of it fat, "
            "and it is computed from your own numbers.\""
            % (first["weight"], first["drop"]),
            "الرقم محسوب من أرقامه. قوله بثقة.",
            "The number is computed from their own numbers. Say it with confidence."))

    if weeks:
        steps.append(_say(
            "المدة الحقيقية", "The honest timeline",
            "«بياخد حوالي %d أسبوع. أسرع من كده بياخد من العضل.»" % weeks,
            "\"That takes about %d weeks. Faster than that comes out of muscle.\"" % weeks,
            "قول المدة الحقيقية. اللي بيوعد بشهر بيرجع بعد شهرين.",
            "Give the honest timeline. Whoever promises a month is seen again in two."))

    steps.append(_say(
        "الخطوة الجاية", "The next step",
        "«ده كله تقدر تعمله لوحدك. اللي بيفرق إننا نقيس ونعدّل كل أسبوعين. "
        "لو تحب نبدأ، أعملك خطة على أرقام النهاردة.»",
        "\"You could do all of this on your own. What changes it is that we measure and "
        "adjust every two weeks. If you would like to start, I will build a plan on "
        "today's numbers.\"",
        "ده اللي بتبيعه: القياس والتعديل، مش الورقة.",
        "This is what you are selling: measuring and adjusting, not a sheet."))
    return steps


def _script_first(_say, weight, fat_mass, lean_mass, targets, weeks, visit_no,
                  is_ar, _fmt):
    """‏أول زيارة بخطة: الأرقام دي بقت نقطة البداية اللي نقيس عليها."""
    steps = []
    steps.append(_say(
        "الافتتاح", "Opening",
        "«الأرقام دي بقت نقطة البداية. كل مرة جاية نقيس ونقارن بيها.»",
        "\"These numbers are the starting point. Every visit from now on we measure and "
        "compare against them.\"",
        "بيخلي القياس الجاي متوقّع، فمايبقاش مفاجأة.",
        "It makes the next measurement expected rather than a surprise."))
    if fat_mass is not None:
        steps.append(_say(
            "التقسيم", "The split",
            "«وزنك %s كجم: %s دهون و%s عضل وعضم وماء. هننزّل الـ%s ونحافظ على الـ%s.»"
            % (_fmt(weight), _fmt(fat_mass), _fmt(lean_mass),
               _fmt(fat_mass), _fmt(lean_mass)),
            "\"You weigh %s kg: %s fat and %s muscle, bone and water. We bring the %s "
            "down and protect the %s.\""
            % (_fmt(weight), _fmt(fat_mass), _fmt(lean_mass),
               _fmt(fat_mass), _fmt(lean_mass)),
            "بيشرح البروتين والمقاومة من غير ما تسمّيهم.",
            "It explains protein and resistance work without naming either."))
    if targets:
        first = targets[0]
        steps.append(_say(
            "الهدف", "The goal",
            "«الهدف الأول %s كجم. يعني %s كجم نازلين، كلهم دهون.»"
            % (first["weight"], first["drop"]),
            "\"First target %s kg. That is a %s kg drop, all of it fat.\""
            % (first["weight"], first["drop"]),
            "هدف واحد بس. التاني بعد ما يوصل للأول.",
            "One target only. The second comes after the first is met."))
    if weeks:
        steps.append(_say(
            "المدة", "The timeline",
            "«حوالي %d أسبوع. ولو نزل أسرع، هنبطّأ — الأسرع بياخد من العضل.»" % weeks,
            "\"About %d weeks. If it goes faster we slow it down -- faster comes out "
            "of muscle.\"" % weeks,
            "", ""))
    steps.append(_say(
        "المتابعة", "Follow-up",
        "«المقياس بينا نسبة الدهون والمقاسات كل 2-4 أسابيع، مش الميزان كل يوم.»",
        "\"Our measure is body fat and tape measurements every 2-4 weeks, not the scale "
        "daily.\"",
        "اتفق على ده قبل ما يمشي، وإلا هيوزن كل يوم ويزهق.",
        "Agree on this before they leave, or they will weigh daily and give up."))
    return steps


def _script_followup(progress, _say, fat_pct, is_ar, _fmt):
    """‏عنده تاريخ: الكلام كله على اللي اتغيّر.

    ‏الأرقام هنا مش محسوبة هنا -- جاية من followup.assess، اللي بيقارن
    الزيارة بالزيارة اللي قبلها. فمافيش حساب مكرر ومافيش رقمين مختلفين
    بيقولوا نفس الحاجة.
    """
    delta = progress.get("delta") or 0
    days = progress.get("days")
    rate = progress.get("rate")
    fat_delta = progress.get("fat_delta")
    steps = []

    steps.append(_say(
        "الافتتاح", "Opening",
        "«خليني أقولك النتيجة من آخر مرة.»",
        "\"Let me tell you the result since last time.\"",
        "ابدأ بالرقم. هو مستنيه ومش سامعك قبله.",
        "Start with the number. They are waiting for it and not listening before it."))

    if delta < 0:
        moved = "«الوزن نزل %s كجم" % _fmt(abs(delta))
        moved_en = "\"Weight is down %s kg" % _fmt(abs(delta))
    elif delta > 0:
        moved = "«الوزن زاد %s كجم" % _fmt(delta)
        moved_en = "\"Weight is up %s kg" % _fmt(delta)
    else:
        moved = "«الوزن ثابت"
        moved_en = "\"Weight is unchanged"
    if days:
        moved += " في %s يوم" % days
        moved_en += " over %s days" % days
    if rate:
        moved += "، بمعدل %s كجم في الأسبوع" % _fmt(abs(rate))
        moved_en += ", about %s kg a week" % _fmt(abs(rate))
    steps.append(_say(
        "اللي حصل", "What happened", moved + ".»", moved_en + ".\"",
        "الرقم زي ما هو، من غير تحسين ولا تهويل.",
        "The number as it is, neither dressed up nor dressed down."))

    if fat_delta:
        if fat_delta < 0:
            steps.append(_say(
                "الأهم", "The part that matters",
                "«والأهم: نسبة الدهون نزلت %s نقاط. يعني النازل دهون فعلاً، مش ماء.»"
                % _fmt(abs(fat_delta)),
                "\"And the part that matters: body fat is down %s points. So what came "
                "off really was fat, not water.\"" % _fmt(abs(fat_delta)),
                "دي الجملة اللي بتخليه يكمّل.",
                "This is the line that keeps them going."))
        else:
            steps.append(_say(
                "اللي محتاج شغل", "What needs work",
                "«بس نسبة الدهون زادت %s نقاط. يعني النازل ماء أو عضل، ودي اللي هنظبّطها.»"
                % _fmt(fat_delta),
                "\"But body fat is up %s points. So what came off was water or muscle, "
                "and that is what we fix.\"" % _fmt(fat_delta),
                "قولها بصراحة. السكوت عليها بيخلي القياس الجاي مفاجأة.",
                "Say it plainly. Skipping it makes the next measurement a shock."))

    # ‏الشرط **أكبر من صفر** مش مجرد إنه موجود: tdee_drop = القديم ناقص
    # الجديد، فبيطلع سالب لما الحرق الجديد يبقى أعلى (بيحصل لما معامل
    # النشاط المشتق من الزيارة اللي فاتت يترفض ويرجع لمعامل الفورم).
    # وساعتها الجملة كانت بتطلع «بيحرق أقل ‎-201 كالوري» -- كلام مقلوب
    # ومكتوب بعلامة سالب، والدكتور بيقراه بصوته للعميل.
    if (progress.get("tdee_drop") or 0) > 0:
        steps.append(_say(
            "السبب", "The reason",
            "«وجسمك بقى بيحرق أقل %s كالوري، عشان الوزن نزل. ده متوقع، وبنعدّله.»"
            % progress["tdee_drop"],
            "\"And your body now burns %s kcal less, because the weight came down. That "
            "is expected, and we adjust for it.\"" % progress["tdee_drop"],
            "بيمنع إحساس الفشل عند الثبات.",
            "It heads off the sense of failure at a plateau."))

    steps.append(_say(
        "اللي ماشي صح", "What is working",
        "«اللي عملناه شغّال، مش هنقلبه. هنعدّل فيه على أرقام النهاردة.»",
        "\"What we did is working, we are not overturning it. We adjust it against "
        "today's numbers.\"",
        "التغيير الكامل بيلغي اللي اتعلّمه. عدّل، مابدّلش.",
        "A full rewrite throws away what they learned. Adjust, do not replace."))

    steps.append(_say(
        "الخطوة الجاية", "The next step",
        "«نقيس تاني بعد 2-4 أسابيع. ولو ثبت أسبوعين، تعالى قبل الميعاد.»",
        "\"We measure again in 2-4 weeks. And if it stalls two weeks, come in before "
        "the appointment.\"",
        "الميعاد المفتوح بيخلّي الثبات يتحول لانسحاب.",
        "An open-ended appointment lets a plateau turn into dropping out."))
    return steps


def explain(data, is_ar=True, mode="first", progress=None, visit_no=None):
    """‏أرقام الفورم -> شرح للعميل. مافيش نداء لأي خدمة، كله حساب.

    mode: "free" (فحص سريع بدون اسم) أو "first" (أول زيارة بخطة) أو
          "followup" (عنده تاريخ، ومعاه progress من followup.assess).
    """
    visit_hint = visit_no
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

    # ‏النطاق بيتحسب مرة واحدة هنا، والصفوف وقايمة «صح وغلط» بيقروا من
    # نفس المتغيّر -- عشان يبقى مستحيل الصف يقول حاجة والحكم يقول غيرها.
    fat_band = (_band(fat_pct, _FAT_FEMALE if female else _FAT_MALE)
                if (fat_pct and sex_known) else None)
    bmi_band = _band(bmi, _BMI) if bmi else None
    vis_band = _band(visceral, _VISCERAL) if visceral else None
    muscle_band = water_band = None
    smi = water_share = None

    if weight:
        rows.append(_row(
            "الوزن", "Weight", _fmt(weight), _pick("كجم", "kg", is_ar), None,
            "رقم واحد، وجواه حاجتين مختلفتين تماماً: دهون وكتلة خالية من الدهون.",
            "One number holding two different things: fat, and fat-free mass.",
            is_ar))

    if fat_mass is not None:
        band = fat_band
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
        band = bmi_band
        rows.append(_row(
            "BMI", "BMI", _fmt(bmi), _pick("كجم/م²", "kg/m2", is_ar), band,
            "مقياس وزن على طول، مابيفرّقش بين عضل ودهن — فبنقراه جنب نسبة الدهون مش لوحده.",
            "A weight-for-height number. It cannot tell muscle from fat, so it is read next to body fat, never alone.",
            is_ar))

    if visceral:
        band = vis_band
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
        muscle_band = band
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
        water_band, water_share = band, share
        rows.append(_row(
            "ماء الجسم", "Body water", _fmt(water), _pick("لتر", "L", is_ar), band,
            "%s%% من كتلتك الخالية من الدهون (الطبيعي 70-75%%). بنقيسه على الكتلة الخالية مش على الوزن، "
            "لأن الدهون فيها ماء قليل — فنسبة الماء من الوزن بتبان أقل كل ما الدهون تزيد."
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

    # ═══ صح وغلط: البصة الواحدة ═══
    #
    # ‏الدكتور بيبص على الورقة مرة واحدة، وعايز تلات حاجات: إيه اللي
    # تمام عشان يحافظ عليه، وإيه اللي فيه شغل، وإيه اللي مانقدرش نحكم
    # عليه أصلاً. والتالتة مهمة زي التانية -- الرقم اللي مش متحكوم عليه
    # بيبان كأنه تمام لو سكتنا عنه.
    #
    # ‏وفي حالتين الرقم لوحده بيكدب، فبيروح «مش متحكوم عليه» بدل ما
    # نقول عليه صح أو غلط:
    #     BMI عالي ونسبة الدهون كويسة  ->  الزيادة كتلة خالية من الدهون
    #     BMI طبيعي ونسبة الدهون عالية ->  الميزان مخبّي الحالة
    #
    # ‏وكله بيتبني من نفس النطاقات اللي فوق، فمستحيل الصف يقول حاجة
    # والحكم يقول غيرها.
    good, work, unsure = [], [], []

    def _judge(kind, label_ar, label_en, line_ar, line_en):
        item = {"label": _pick(label_ar, label_en, is_ar),
                "line": _pick(line_ar, line_en, is_ar)}
        if kind == "good":
            good.append(item)
        elif kind == "unsure":
            unsure.append(item)
        else:
            work.append(item)

    # ‏في المتابعة، أول حاجة تتقال هي اللي حصل — مش أي رقم في الورقة.
    #
    # ‏والحكم مابيتحسبش هنا تاني: followup.assess هو اللي بيقرر،
    # واللي هنا مجرّد ترجمة لكل حكم لسطر يتقال للعميل. ولو جه
    # حكم مش في الجدول (اتضاف حكم جديد في followup بعدين)، بنقول
    # ملاحظة assess نفسها وبنحطها في «مالوش حكم» — أحسن من
    # إن حكم ماتعرفناهوش يقع في else ويتقرا غلط: رياضي بيزيد عضل
    # بالمعدل الصح (gain_on_track) كان بيطلع «الوزن رجع».
    if mode == "followup" and progress:
        rate = abs(float(progress.get("rate") or 0))
        moved = abs(float(progress.get("delta") or 0))
        days = int(progress.get("days") or 0)
        went_up = str(progress.get("direction") or "") == "up"
        verb_ar = "زاد" if went_up else "نزل"
        verb_en = "Up" if went_up else "Down"

        # (القايمة, العنوان عربي/إنجليزي, السطر عربي/إنجليزي)
        moves = {
            "on_track": (
                "good", "اللي حصل من آخر زيارة", "Since the last visit",
                "%s %s كجم في %d يوم، بمعدل %s كجم في الأسبوع — جوّه النطاق الآمن."
                % (verb_ar, _fmt(moved), days, _fmt(rate)),
                "%s %s kg over %d days, %s kg a week -- inside the safe band."
                % (verb_en, _fmt(moved), days, _fmt(rate))),
            "gain_on_track": (
                "good", "اللي حصل من آخر زيارة", "Since the last visit",
                "زاد %s كجم في %d يوم، بمعدل %s كجم في الأسبوع — ده المعدل الصحي "
                "لبناء العضل." % (_fmt(moved), days, _fmt(rate)),
                "Up %s kg over %d days, %s kg a week -- the healthy rate for building muscle."
                % (_fmt(moved), days, _fmt(rate))),
            "too_soon": (
                "unsure", "اللي حصل من آخر زيارة", "Since the last visit",
                "%d يوم بس بين الزيارتين. الفرق ده مياه، مش دليل على حاجة." % days,
                "Only %d days between visits. This is water, not evidence." % days),
            "too_fast": (
                "work", "سرعة النزول", "Rate of loss",
                "%s كجم في الأسبوع — أسرع من الآمن، والسريع بياخد عضل معاه." % _fmt(rate),
                "%s kg a week -- faster than is safe, and fast loss takes muscle with it."
                % _fmt(rate)),
            "too_slow": (
                "work", "سرعة النزول", "Rate of loss",
                "%s كجم في الأسبوع — أبطأ من المتوقع للعجز اللي ماشي." % _fmt(rate),
                "%s kg a week -- slower than the running deficit predicts." % _fmt(rate)),
            "plateau": (
                "work", "الوزن ثابت", "Weight has stalled",
                "مافيش فرق يعتد بيه في %d يوم. أول حاجة: الـTDEE يتحسب على الوزن الجديد."
                % days,
                "No meaningful change in %d days. First move: recalculate TDEE on the new weight."
                % days),
            "regained": (
                "work", "الوزن زاد", "Weight regained",
                "زاد %s كجم من آخر زيارة، والهدف نزول." % _fmt(moved),
                "Up %s kg since the last visit, on a weight-loss plan." % _fmt(moved)),
            "gain_too_fast": (
                "work", "سرعة الزيادة", "Rate of gain",
                "%s كجم في الأسبوع — أسرع من اللازم، والزيادة السريعة بتبقى دهون "
                "أكتر من عضل." % _fmt(rate),
                "%s kg a week -- faster than needed, and fast gain is more fat than muscle."
                % _fmt(rate)),
            "gain_stalled": (
                "work", "الوزن مش بيزيد", "The gain has stalled",
                "مافيش زيادة تعتد بيها في %d يوم. الفائض محتاج يكبر." % days,
                "No meaningful gain in %d days. The surplus needs to grow." % days),
            "lost_on_gain": (
                "work", "الوزن نزل والهدف زيادة", "Lost weight on a gain plan",
                "نزل %s كجم، والهدف زيادة — السعرات أقل من اللازم." % _fmt(moved),
                "Down %s kg on a gain plan -- calories are below what is needed." % _fmt(moved)),
        }
        move = moves.get(progress.get("verdict"))
        if move:
            _judge(move[0], move[1], move[2], move[3], move[4])
        elif progress.get("note_ar") or progress.get("note"):
            _judge("unsure", "اللي حصل من آخر زيارة", "Since the last visit",
                   progress.get("note_ar") or progress.get("note"),
                   progress.get("note_en") or progress.get("note"))

        # ‏تقسيم التغيّر: دهون ولّا كتلة خالية من الدهون؟
        #
        # ‏حتة مهمة: fat_delta اللي جاي من followup هو فرق **النسبة**
        # بالنقطة، مش كيلوهات. ولو اتقرا كتر بيطلع غلط كتير:
        # 40% من 88 كيلو = 35.2 كجم دهون، و36% من 82 = 29.5 — يعني 5.7 كجم
        # دهون نزلت، مش 4. فالكيلوهات بتتحسب من الوزنين والنسبتين.
        #
        # ‏والحكم على **نسبة** الدهون من التغيّر، وبيقلب مع الهدف:
        #     نزول  ->  نعوز النازل دهون. نزول 6 كيلو منهم 1.6 دهون
        #                معناه إن 4.4 راحوا من الكتلة الخالية — خسارة.
        #     زيادة  ->  العكس: نعوز الزايد كتلة خالية، والدهون أقل ما يمكن.
        # ‏الاستيراد جوّه الدالة مقصود: الملف ده مابيستوردش حاجة على
        # مستوى الملف، وقايمة أهداف الزيادة لازم تيجي من مكان واحد
        # (followup) مش تتكرر هنا.
        import followup as _fu
        gaining = str(progress.get("goal_type") or "") in _fu.GAIN_GOALS
        fat_points = progress.get("fat_delta")
        old_weight = _num(progress.get("old_weight"))
        if (fat_points is not None and fat_pct and weight and old_weight
                and moved > 0.2):
            old_pct = fat_pct - float(fat_points)
            old_fat_kg = old_weight * old_pct / 100.0
            new_fat_kg = weight * fat_pct / 100.0
            fat_kg = new_fat_kg - old_fat_kg
            lean_kg = (weight - new_fat_kg) - (old_weight - old_fat_kg)
            if gaining and went_up:
                # ‏الزيادة المطلوبة: نصّها عضل ولازم يبقى أقل حاجة.
                if lean_kg / moved >= 0.5:
                    _judge("good", "الزيادة دي إيه", "What the gain was",
                           "من %s كجم زادوا، %s كجم كتلة خالية من الدهون و%s كجم دهون "
                           "— دي زيادة نضيفة."
                           % (_fmt(moved), _fmt(max(0.0, lean_kg)), _fmt(max(0.0, fat_kg))),
                           "Of the %s kg gained, %s kg was fat-free mass and %s kg was fat "
                           "-- that is a clean gain."
                           % (_fmt(moved), _fmt(max(0.0, lean_kg)), _fmt(max(0.0, fat_kg))))
                else:
                    _judge("work", "الزيادة دي إيه", "What the gain was",
                           "من %s كجم زادوا، %s كجم دهون — يعني أغلب الزيادة دهن مش عضل. "
                           "الفائض محتاج يقل والمقاومة تزيد."
                           % (_fmt(moved), _fmt(max(0.0, fat_kg))),
                           "Of the %s kg gained, %s kg was fat -- most of the gain is fat, "
                           "not muscle. The surplus needs to come down and resistance work up."
                           % (_fmt(moved), _fmt(max(0.0, fat_kg))))
            elif not went_up and lean_kg > 0.2:
                # ‏الدهون نزلت أكتر من الوزن كله، يعني الكتلة الخالية زادت.
                # ده أحسن اللي ممكن يحصل، بس النسبة بتطلع فوق ١٠٠٪ --
                # و«١.٨ كجم دهون (120%)» رقم مايتقالش لعميل. فالسطر ده
                # بيقول اللي حصل فعلاً: نزلت دهون وزاد عضل.
                _judge("good", "النازل ده إيه", "What actually came off",
                       "نزل %s كجم دهون، والعضل زاد %s كجم. ده أحسن اللي ممكن يحصل."
                       % (_fmt(-fat_kg), _fmt(lean_kg)),
                       "%s kg of fat came off and lean mass went up %s kg. That is the "
                       "best outcome there is." % (_fmt(-fat_kg), _fmt(lean_kg)))
            elif not went_up and (-fat_kg) / moved >= 0.65:
                _judge("good", "النازل ده إيه", "What actually came off",
                       "من %s كجم نزلوا، %s كجم دهون (%s%%) — ده بالظبط اللي إحنا وراه."
                       % (_fmt(moved), _fmt(-fat_kg), _fmt((-fat_kg) / moved * 100, 0)),
                       "Of the %s kg lost, %s kg was fat (%s%%) -- exactly what we are after."
                       % (_fmt(moved), _fmt(-fat_kg), _fmt((-fat_kg) / moved * 100, 0)))
            elif not went_up and (-fat_kg) / moved >= 0.4:
                _judge("work", "النازل ده إيه", "What actually came off",
                       "من %s كجم نزلوا، %s كجم دهون و%s كجم كتلة خالية من الدهون. "
                       "البروتين وتمرين المقاومة محتاجين يعلوا."
                       % (_fmt(moved), _fmt(-fat_kg), _fmt(max(0.0, -lean_kg))),
                       "Of the %s kg lost, %s kg was fat and %s kg was fat-free mass. "
                       "Protein and resistance training need to go up."
                       % (_fmt(moved), _fmt(-fat_kg), _fmt(max(0.0, -lean_kg))))
            elif not went_up:
                _judge("work", "النازل ده إيه", "What actually came off",
                       "من %s كجم نزلوا، %s كجم بس دهون — الباقي ماء وعضل. "
                       "ده اللي يعمل الثبات بعدين، ولازم يتصلّح دلوقتي."
                       % (_fmt(moved), _fmt(max(0.0, -fat_kg))),
                       "Of the %s kg lost, only %s kg was fat -- the rest was water and muscle. "
                       "This is what stalls progress later, and it is fixed now."
                       % (_fmt(moved), _fmt(max(0.0, -fat_kg))))
            elif fat_kg > 0.2:
                _judge("work", "الزيادة دي إيه", "What the gain was",
                       "الوزن زاد %s كجم، منهم %s كجم دهون."
                       % (_fmt(moved), _fmt(fat_kg)),
                       "Weight went up %s kg, of which %s kg was fat."
                       % (_fmt(moved), _fmt(fat_kg)))
            else:
                _judge("good", "الزيادة دي إيه", "What the gain was",
                       "الوزن زاد %s كجم والدهون مازادتش — الزيادة كتلة خالية من الدهون."
                       % _fmt(moved),
                       "Weight went up %s kg with no fat gain -- the gain was fat-free mass."
                       % _fmt(moved))

    if fat_band:
        pct = _fmt(fat_pct)
        if fat_band["kind"] == "good":
            _judge("good", "نسبة الدهون", "Body fat",
                   "%s%% — في النطاق الصحي (%s). دي أهم حاجة تمام في الورقة، "
                   "والشغل إننا نحافظ عليها." % (pct, fat_band["ar"]),
                   "%s%% -- in the healthy range (%s). This is the best thing on the sheet, "
                   "and the job is to hold it." % (pct, fat_band["en"]))
        elif fat_band["kind"] == "watch":
            _judge("work", "نسبة الدهون", "Body fat",
                   "%s%% — %s، يعني فوق النطاق الصحي. مش خطر، بس هي الشغل الأساسي."
                   % (pct, fat_band["ar"]),
                   "%s%% -- %s, above the healthy range. Not dangerous, but this is the main work."
                   % (pct, fat_band["en"]))
        elif fat_band["kind"] == "high":
            _judge("work", "نسبة الدهون", "Body fat",
                   "%s%% — %s. ده أعلى رقم في ترتيب الأولويات." % (pct, fat_band["ar"]),
                   "%s%% -- %s. This is the top priority on the sheet."
                   % (pct, fat_band["en"]))
        else:
            _judge("work", "نسبة الدهون", "Body fat",
                   "%s%% — أقل من الحد الصحي. النزول أكتر مش هدف هنا، الشغل بناء." % pct,
                   "%s%% -- below the healthy floor. Losing more is not the goal here; building is."
                   % pct)
    elif fat_pct:
        _judge("unsure", "نسبة الدهون", "Body fat",
               "%s%% مكتوبة، بس النوع مش مختار — والنطاق الصحي بيفرق كتير "
               "(السمنة بتبدأ 32%% للأنثى و25%% للذكر)." % _fmt(fat_pct),
               "%s%% is entered, but the sex is not selected -- and the range differs a lot "
               "(obesity starts at 32%% for women, 25%% for men)." % _fmt(fat_pct))
    elif weight:
        _judge("unsure", "نسبة الدهون", "Body fat",
               "مش مكتوبة، فالوزن مش متقسّم دهون وكتلة خالية من الدهون. "
               "ده أهم سطر ناقص في الورقة.",
               "Not entered, so the weight is not split into fat and fat-free mass. "
               "This is the most useful missing line.")

    if bmi_band:
        value = _fmt(bmi)
        if fat_band and fat_band["kind"] == "good" and bmi_band["kind"] != "good":
            _judge("unsure", "BMI", "BMI",
                   "%s — بيقول «%s»، ونسبة الدهون %s%% وهي في نطاق كويس. "
                   "يعني الرقم ده جاي من كتلة خالية من الدهون، فمانشتغلش عليه هنا."
                   % (value, bmi_band["ar"], _fmt(fat_pct)),
                   "%s -- reads %s while body fat is %s%%, which sits in a good range. "
                   "The number comes from fat-free mass, so it is not what we chase."
                   % (value, bmi_band["en"], _fmt(fat_pct)))
        elif fat_band and fat_band["kind"] == "high" and bmi_band["kind"] == "good":
            _judge("unsure", "BMI", "BMI",
                   "%s — بيقول «طبيعي»، ودي الحالة اللي الميزان بيخبّيها: "
                   "نسبة الدهون %s%%. الحكم بيتاخد من نسبة الدهون مش منه."
                   % (value, _fmt(fat_pct)),
                   "%s -- reads normal, and this is exactly the case the scale hides: "
                   "body fat is %s%%. The verdict comes from body fat, not from here."
                   % (value, _fmt(fat_pct)))
        elif bmi_band["kind"] == "good":
            _judge("good", "BMI", "BMI",
                   "%s — الوزن على الطول في النطاق الطبيعي." % value,
                   "%s -- weight-for-height sits in the normal range." % value)
        else:
            _judge("work", "BMI", "BMI",
                   "%s — %s بمقياس الوزن على الطول." % (value, bmi_band["ar"]),
                   "%s -- %s on weight-for-height." % (value, bmi_band["en"]))

    if vis_band:
        if vis_band["kind"] == "good":
            _judge("good", "الدهون الحشوية", "Visceral fat",
                   "مستوى %s — طبيعي. دي اللي بتفرق في السكر والضغط ودهون الكبد، "
                   "وكونها في مكانها خبر كبير." % _fmt(visceral),
                   "Level %s -- normal. This is the fat that moves blood sugar, blood pressure "
                   "and liver fat, so having it in range is a big deal." % _fmt(visceral))
        else:
            _judge("work", "الدهون الحشوية", "Visceral fat",
                   "مستوى %s — %s. بتستجيب بسرعة للعجز، وبتبان في التحاليل قبل الميزان."
                   % (_fmt(visceral), vis_band["ar"]),
                   "Level %s -- %s. It responds fast to a deficit and shows in labs before the scale."
                   % (_fmt(visceral), vis_band["en"]))

    if muscle_band and smi is not None:
        if muscle_band["kind"] == "good":
            _judge("good", "كتلة العضل", "Skeletal muscle",
                   "%s كجم، ونسبةً للطول %s — في النطاق الطبيعي. دي اللي بتحرق، "
                   "وحمايتها وإحنا بننزّل هي الشغل." % (_fmt(muscle), _fmt(smi, 2)),
                   "%s kg, and %s relative to height -- within normal. This is the tissue that "
                   "burns, and protecting it while losing is the job."
                   % (_fmt(muscle), _fmt(smi, 2)))
        else:
            _judge("work", "كتلة العضل", "Skeletal muscle",
                   "%s كجم، ونسبةً للطول %s والطبيعي %s وأكتر — %s. "
                   "ده بيقلّل الحرق ويعمل ثبات بعد شهرين."
                   % (_fmt(muscle), _fmt(smi, 2), _fmt(_SMI[sex][0], 2), muscle_band["ar"]),
                   "%s kg, %s relative to height against a normal of %s and up -- %s. "
                   "It lowers the burn and stalls progress a couple of months in."
                   % (_fmt(muscle), _fmt(smi, 2), _fmt(_SMI[sex][0], 2), muscle_band["en"]))
    elif muscle:
        _judge("unsure", "كتلة العضل", "Skeletal muscle",
               "%s كجم مكتوبة، بس الحكم عليها محتاج الطول والنوع." % _fmt(muscle),
               "%s kg is entered, but judging it needs the height and the sex." % _fmt(muscle))

    if water_band and water_share is not None:
        if water_band["kind"] == "good":
            _judge("good", "ماء الجسم", "Body water",
                   "%s%% من الكتلة الخالية من الدهون — في الطبيعي (70-75%%)."
                   % _fmt(water_share),
                   "%s%% of fat-free mass -- normal (70-75%%)." % _fmt(water_share))
        else:
            _judge("work", "ماء الجسم", "Body water",
                   "%s%% من الكتلة الخالية من الدهون — %s (الطبيعي 70-75%%). "
                   "راجع الملح والدوا وتقلّب الوزن اليومي."
                   % (_fmt(water_share), water_band["ar"]),
                   "%s%% of fat-free mass -- %s (normal is 70-75%%). "
                   "Review salt, medication and day-to-day weight swings."
                   % (_fmt(water_share), water_band["en"]))

    # ‏اللي مش موجود خالص: بيتقال مرة واحدة في سطر، مش يتسكت عنه.
    absent_ar, absent_en = [], []
    for present, name_ar, name_en in (
            (visceral, "الدهون الحشوية", "visceral fat"),
            (muscle, "كتلة العضل", "skeletal muscle"),
            (water, "ماء الجسم", "body water"),
            (bmr, "معدل الحرق وقت الراحة", "resting metabolic rate")):
        if not present:
            absent_ar.append(name_ar)
            absent_en.append(name_en)
    if absent_ar:
        _judge("unsure", "أرقام مش موجودة", "Numbers not present",
               "%s — لا في الورقة ولا مكتوبة، فمالهاش حكم."
               % "، ".join(absent_ar),
               "%s -- neither on the sheet nor entered, so there is no verdict on them."
               % ", ".join(absent_en))

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
                "do": _pick("قوله: هنقيس نسبة الدهون والمقاسات كل 2-4 أسابيع، مش الميزان كل يوم.",
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
                "do": _pick("قوله: البروتين في كل وجبة + تمرين مقاومة 2-3 مرات أسبوعياً، مش كارديو بس.",
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

    # ═══ السيناريو: الكلام اللي بيتقال، بالترتيب ═══
    #
    # ‏ده مش تعليمات -- دي جمل تتقال. الدكتور بيقرا من على الشاشة والعميل
    # قاعد قدامه، فأي سطر بيقول "اشرح له كذا" بيضطره يترجمه بنفسه وسط
    # الكلام. فكل خطوة: العنوان (وإحنا فين)، والجملة، وسبب قصير له هو.
    #
    # ‏وبيختلف على حسب الحالة، لأن الهدف مختلف:
    #
    #   free      فحص سريع بدون اسم ولا رقم. العميل ماعندوش خطة، والهدف
    #             إنه يشوف الفرق بين "أعرف وزني" و"أعرف تركيبي وأقيسه"،
    #             ويقرر هو.
    #   first     أول زيارة بخطة. الأرقام دي بقت نقطة البداية.
    #   followup  عنده تاريخ. الكلام كله بيبقى على اللي اتغيّر: إيه اللي
    #             نزل، وليه، وإيه اللي نكمّل عليه.
    def _say(label_ar, label_en, say_ar, say_en, note_ar="", note_en=""):
        return {"label": _pick(label_ar, label_en, is_ar),
                "say": _pick(say_ar, say_en, is_ar),
                "note": _pick(note_ar, note_en, is_ar)}

    weeks = None
    if targets and weight:
        # ‏٠.٧٥٪ من الوزن في الأسبوع -- وسط النطاق الواقعي (٠.٥ إلى ١٪).
        drop = float(targets[0]["drop"])
        weeks = max(2, int(round(drop / (weight * 0.0075))))

    if mode == "followup" and progress:
        script = _script_followup(progress, _say, fat_pct, is_ar, _fmt)
    elif mode == "free":
        script = _script_free(_say, weight, fat_mass, lean_mass, fat_pct,
                              targets, weeks, sex_known, female, is_ar, _fmt)
    else:
        script = _script_first(_say, weight, fat_mass, lean_mass, targets,
                               weeks, visit_hint, is_ar, _fmt)

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
        headline = _pick("الأرقام مش كفاية للشرح — اكتب الوزن والطول على الأقل.",
                         "Not enough numbers to explain -- enter at least weight and height.", is_ar)

    # ═══ اللي ناقص واللي الملف ده مش بيعمله ═══
    if not sex_known:
        caveats.append(_pick(
            "النوع مش مختار، ونطاقات الدهون والعضل بتفرق كتير بين الذكر والأنثى — "
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
            "verdict": {"good": good, "work": work, "unsure": unsure},
            "targets": targets, "caveats": caveats, "mode": mode,
            "visit_no": visit_hint,
            "missing": [m for m in missing if m]}


def as_text(result, is_ar=True):
    """‏نفس الشرح كنص سادة -- الدكتور بينسخه ويبعته واتساب للعميل."""
    out = [result["headline"], ""]

    # ‏الحكم قبل الأرقام: ده اللي الدكتور بيقراه الأول، وده اللي
    # العميل بياخد باله منه لو الدكتور بعت له النص ده واتساب.
    verdict = result.get("verdict") or {}
    for key, head_ar, head_en, mark in (
            ("good", "اللي تمام:", "What is fine:", "✓"),
            ("work", "اللي فيه شغل:", "What needs work:", "!"),
            ("unsure", "اللي مالوش حكم:", "What has no verdict:", "?")):
        items = verdict.get(key) or []
        if not items:
            continue
        out.append(_pick(head_ar, head_en, is_ar))
        for item in items:
            out.append("%s %s: %s" % (mark, item["label"], item["line"]))
        out.append("")

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
    out.append(_pick("السيناريو — الكلام بالترتيب:", "The script, in order:", is_ar))
    for index, step in enumerate(result["script"], start=1):
        out.append("")
        out.append("%s %s" % (_step(index, is_ar), step["label"]))
        out.append(step["say"])
        if step.get("note"):
            out.append("   (%s)" % step["note"])
    return "\n".join(out)

# -*- coding: utf-8 -*-
"""تدوير السعرات — calorie cycling across the seven days of a plan.

The idea: instead of eating the same number of calories every day, the week
swings above and below the target while the weekly total stays the same. Two
things make that worth doing -- it keeps the metabolic drop of a long deficit
from settling in, and it gives the client a couple of days they can actually
live with socially, which is the reason most plans get abandoned.

What this module adds over a plain percentage table:

* protein is held constant every day (it is the one macro you do not want
  swinging in a deficit -- it is what protects lean mass), so the calorie
  swing is carried by carbs, with fat kept near its target and only pulled
  down when a low day cannot fit the carbs otherwise;
* every day is clamped to a clinical floor and a sane ceiling, and whatever
  gets clamped is redistributed across the other days so the weekly total is
  still the number the plan was built on.

Public API:
    ZIGZAG_MODES              the presets, each with an Arabic and English label
    build_zigzag(...)         -> the seven days, with kcal and macros
    zigzag_from_data(data)    -> build_zigzag from a plan-form dict
"""

DAYS_AR = ["الاحد", "الاثنين", "الثلاثاء", "الاربعاء", "الخميس", "الجمعة", "السبت"]
DAYS_EN = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# أقل سعرات آمنة يومياً — تحت كده الخطة محتاجة إشراف طبي مباشر
MIN_KCAL_FEMALE = 1200
MIN_KCAL_MALE = 1500

# أقل دهون لازمة لصحة الهرمونات (جم/كجم من وزن الجسم)
MIN_FAT_PER_KG = 0.6

# نسب التدوير لكل يوم. مجموع كل نمط = صفر، عشان المجموع الأسبوعي ما يتغيرش.
ZIGZAG_MODES = {
    "off": {
        "ar": "بدون تدوير",
        "en": "No cycling",
        "desc_ar": "نفس السعرات كل يوم — الأبسط في التطبيق.",
        "desc_en": "The same calories every day — simplest to follow.",
        "pattern": [0, 0, 0, 0, 0, 0, 0],
    },
    "gentle": {
        "ar": "تدوير خفيف (±١٠٪)",
        "en": "Gentle (±10%)",
        "desc_ar": "فرق بسيط بين الأيام، مناسب لأول مرة أو للحالات المرضية.",
        "desc_en": "A small day-to-day swing — good for a first plan or a medical case.",
        "pattern": [8, -8, 8, -12, 8, -12, 8],
    },
    "classic": {
        "ar": "تدوير كلاسيكي (±٢٠٪)",
        "en": "Classic (±20%)",
        "desc_ar": "النمط المعتاد: يومين أقل + أيام أعلى، والمجموع الأسبوعي زي ما هو.",
        "desc_en": "The usual pattern: two lower days plus higher ones, same weekly total.",
        "pattern": [15, -15, 10, -20, 15, -20, 15],
    },
    "strong": {
        "ar": "تدوير قوي (±٣٠٪)",
        "en": "Strong (±30%)",
        "desc_ar": "فرق كبير بين الأيام — للرياضيين وحالات ثبات الوزن الطويل.",
        "desc_en": "A wide swing — for athletes and long weight-loss plateaus.",
        "pattern": [25, -25, 15, -30, 20, -30, 25],
    },
    "refeed": {
        "ar": "خمس أيام عجز + يومين ريفيد",
        "en": "Five deficit days + two refeeds",
        "desc_ar": "عجز طول الأسبوع وأيام أعلى في الويك إند — أسهل نمط اجتماعياً.",
        "desc_en": "A deficit through the week with higher weekend days — the easiest socially.",
        "pattern": [-15, -15, -15, -15, -15, 35, 40],
    },
    "training": {
        "ar": "حسب أيام التمرين",
        "en": "Training-day based",
        "desc_ar": "سعرات أعلى أيام التمرين (الأحد/الثلاثاء/الخميس) وأقل أيام الراحة.",
        "desc_en": "Higher on training days (Sun/Tue/Thu), lower on rest days.",
        "pattern": [20, -15, 20, -15, 20, -15, -15],
    },
}

DEFAULT_MODE = "classic"


def _floor_for(gender):
    g = (gender or "").strip().lower()
    if g in ("انثى", "أنثى", "female", "f", "woman", "بنت", "ست"):
        return MIN_KCAL_FEMALE
    return MIN_KCAL_MALE


def _clamped_days(target, pattern, floor, ceiling):
    """يوزّع السعرات على السبع أيام مع احترام الحد الأدنى والأقصى.

    اللي بيتقص من يوم وصل للحد بيترد على باقي الأيام، عشان المجموع الأسبوعي
    يفضل = 7 × الهدف.
    """
    weekly_total = target * 7
    day = [target * (1 + p / 100.0) for p in pattern]

    for _ in range(12):
        free = []
        fixed_sum = 0.0
        for i, v in enumerate(day):
            if v < floor:
                day[i] = floor
                fixed_sum += floor
            elif v > ceiling:
                day[i] = ceiling
                fixed_sum += ceiling
            else:
                free.append(i)
                fixed_sum += v
        residual = weekly_total - fixed_sum
        if abs(residual) < 1 or not free:
            break
        share = residual / len(free)
        for i in free:
            day[i] += share

    return day, (weekly_total - sum(day))


def build_zigzag(target_cal, mode=DEFAULT_MODE, gender="male", weight=None,
                 protein_per_kg=1.6, fat_pct=30, tdee=None, custom=None):
    """يبني جدول السبع أيام.

    target_cal      متوسط السعرات اليومي المستهدف
    mode            مفتاح من ZIGZAG_MODES
    custom          لستة ٧ نسب مئوية تتغلب على النمط الجاهز
    """
    try:
        target = float(target_cal or 0)
    except (TypeError, ValueError):
        target = 0.0
    if target <= 0:
        return None

    if custom and len(custom) == 7:
        try:
            pattern = [float(x) for x in custom]
        except (TypeError, ValueError):
            pattern = ZIGZAG_MODES[DEFAULT_MODE]["pattern"]
        mode_key = "custom"
        # نظبّط النسب المخصّصة عشان مجموعها يبقى صفر — المجموع الأسبوعي ما يتغيرش
        drift = sum(pattern) / 7.0
        pattern = [p - drift for p in pattern]
    else:
        mode_key = mode if mode in ZIGZAG_MODES else DEFAULT_MODE
        pattern = list(ZIGZAG_MODES[mode_key]["pattern"])

    floor = _floor_for(gender)
    floor_disabled = floor >= target
    if floor_disabled:
        # الهدف نفسه عند الحد الآمن أو تحته: مفيش مجال ننزّل يوم عنه، سيب الأيام ثابتة
        floor = target
    # ── سقف اليوم الأعلى ──
    #
    # ‏كان max(TDEE × ١.٢٥, الهدف × ١.١٥)، يعني اليوم الأعلى في خطة تخسيس
    # كان يعدّي اللي العميل بيحرقه بـ٢٥٪. واحدة TDEE بتاعها ١٩٠٠ وهدفها
    # ١٤٠٠ كانت تاخد يوم ١٩٣٠ -- يوم **زيادة** مطبوع على ورقة تخسيس.
    #
    # ‏الريفيد في الأبحاث بيروح لحد **التثبيت**، مش فوقه: الفكرة إن اللبتين
    # والغدة الدرقية يرجعوا يوم، مش إن العميل يدخل فائض. وفوق كده الورقة
    # نفسها بتبوّظ الثقة -- العميل بيقرا ٢٠٠٠ سعرة في خطة تخسيس وبيسأل.
    #
    # ‏فالقاعدة بقت: **لو الهدف تحت الـTDEE (يعني خطة تخسيس)، مافيش يوم
    # يعدّي الـTDEE.** الهدف فوق أو يساوي الـTDEE (تثبيت/تضخيم) الفائض هو
    # المقصود أصلاً، فالسقف القديم بيفضل.
    tdee_val = 0.0
    if tdee:
        try:
            tdee_val = float(tdee)
        except (TypeError, ValueError):
            tdee_val = 0.0
    capped_at_tdee = False
    if tdee_val > 0:
        if target < tdee_val:
            ceiling = tdee_val
            capped_at_tdee = True
        else:
            ceiling = max(tdee_val * 1.25, target * 1.15)
    else:
        ceiling = target * 1.6
    # ‏السقف ما ينفعش ينزل تحت الهدف: ساعتها كل الأيام تتقفل على رقم واحد
    # والمجموع الأسبوعي يبوظ. بيحصل لو الهدف قريب جداً من الـTDEE.
    if ceiling < target:
        ceiling = target

    kcal, leftover = _clamped_days(target, pattern, floor, ceiling)

    # ── تقريب لأقرب ١٠ ──
    #
    # ‏فرق التقريب بيترد على الأيام في حدود الأرضية والسقف: من غير ده
    # التقريب نفسه كان بيكسر الحدين -- ينزّل يوم تحت الحد الآمن، أو
    # يرفع يوم فوق الحرق.
    #
    # ‏والسقف لازم يبقى من مضاعفات العشرة هو كمان، وإلا التقريب نفسه
    # بيكسره: سقف ١٣٦٨ بيتقرّب لـ١٣٧٠، فاليوم بيعدّي الحرق بـسعرتين --
    # من غير ما حد يبص. فبناخد أكبر مضاعف للعشرة **مش فوق** السقف.
    floor_i = int(floor)
    ceil_i = int(ceiling // 10 * 10)
    if ceil_i < floor_i:
        ceil_i = int(ceiling)

    rounded = [min(int(round(v / 10.0) * 10), ceil_i) for v in kcal]
    drift = int(round(target * 7)) - sum(rounded)

    # ‏الفرق بيترد على الأيام في حدود السقف والأرضية. أكتر من لفة لأن
    # اللفة الواحدة بتدي كل يوم مساحته مرة واحدة بس.
    for _ in range(4):
        if drift == 0:
            break
        if drift > 0:
            # ‏من أعلى يوم لأقل: اليوم العالي هو اللي المفروض يشيل الزيادة
            for i in sorted(range(7), key=lambda j: rounded[j], reverse=True):
                if drift == 0:
                    break
                give = min(ceil_i - rounded[i], drift)
                if give > 0:
                    rounded[i] += give
                    drift -= give
        else:
            for i in sorted(range(7), key=lambda j: rounded[j], reverse=True):
                if drift == 0:
                    break
                take = min(rounded[i] - floor_i, -drift)
                if take > 0:
                    rounded[i] -= take
                    drift += take
        if drift and all((rounded[i] >= ceil_i) if drift > 0 else
                         (rounded[i] <= floor_i) for i in range(7)):
            break
    if drift:
        # ‏كل الأيام عند الحد ومفيش مكان للفرق -- بيحصل بس لما الهدف
        # نفسه عند السقف أو عند الأرضية. المجموع الأسبوعي هو الرقم اللي
        # الخطة اتحسبت عليه، فبيتحط على اليوم اللي أبعد عن الحد المكسور.
        i = (min(range(7), key=lambda j: rounded[j]) if drift > 0
             else max(range(7), key=lambda j: rounded[j]))
        rounded[i] += drift
        drift = 0

    # ── الماكروز: البروتين ثابت، الكارب هو اللي بيتأرجح ──
    try:
        w = float(weight or 0)
    except (TypeError, ValueError):
        w = 0.0
    try:
        ppk = float(protein_per_kg or 0)
    except (TypeError, ValueError):
        ppk = 0.0
    try:
        fpct = float(fat_pct or 0)
    except (TypeError, ValueError):
        fpct = 0.0

    protein_g = round(w * ppk) if (w > 0 and ppk > 0) else 0
    min_fat_g = round(w * MIN_FAT_PER_KG) if w > 0 else 0
    base_fat_g = round(target * (fpct / 100.0) / 9.0) if fpct > 0 else 0
    # نسبة الدهون اللي الدكتور كتبها هدف، لكن ٠.٦ جم/كجم حد صحي مش بنعدّيه لتحت
    fat_floor_applied = bool(base_fat_g and min_fat_g and base_fat_g < min_fat_g)
    if fat_floor_applied:
        base_fat_g = min_fat_g

    macro_conflict = False
    days = []
    for i, day_kcal in enumerate(rounded):
        fat_g = base_fat_g
        carb_g = 0
        if protein_g or fat_g:
            remaining = day_kcal - protein_g * 4 - fat_g * 9
            if remaining < 0 and fat_g > min_fat_g:
                # اليوم المنخفض مش شايل الدهون كلها: نزّل الدهون لحد الأمان
                deficit_kcal = -remaining
                fat_g = max(min_fat_g, fat_g - int(deficit_kcal // 9) - 1)
                remaining = day_kcal - protein_g * 4 - fat_g * 9
            if remaining < 0:
                # البروتين + أقل دهون آمنة أكبر من سعرات اليوم: الوصفة نفسها
                # مش قابلة للتنفيذ، والدكتور لازم يشوفها بدل ما نطلّع أرقام غلط
                macro_conflict = True
            carb_g = max(0, int(round(remaining / 4.0)))

        pct = round((day_kcal - target) / target * 100.0)
        days.append({
            "idx": i,
            "day_ar": DAYS_AR[i],
            "day_en": DAYS_EN[i],
            "pct": pct,
            "kcal": day_kcal,
            "protein_g": protein_g,
            "fat_g": fat_g,
            "carb_g": carb_g,
            "level": "high" if pct >= 5 else ("low" if pct <= -5 else "even"),
        })

    meta = ZIGZAG_MODES.get(mode_key, {"ar": "مخصّص", "en": "Custom",
                                       "desc_ar": "نسب من عندك.", "desc_en": "Your own percentages."})
    total = sum(d["kcal"] for d in days)
    return {
        "mode": mode_key,
        "mode_ar": meta["ar"],
        "mode_en": meta["en"],
        "desc_ar": meta["desc_ar"],
        "desc_en": meta["desc_en"],
        "target": int(round(target)),
        "weekly_total": total,
        "avg": int(round(total / 7.0)),
        "low": min(d["kcal"] for d in days),
        "high": max(d["kcal"] for d in days),
        "floor": int(floor),
        "ceiling": int(ceiling),
        # ‏اليوم الأعلى متسقّف عند الـTDEE لأن دي خطة عجز. الواجهة بتقول
        # للدكتور إن ده حصل، عشان ميدوّرش على اليوم العالي اللي طلبه.
        "capped_at_tdee": capped_at_tdee,
        "clamped": abs(leftover) > 1,
        "floor_disabled": floor_disabled,
        "fat_floor_applied": fat_floor_applied,
        "min_fat_g": min_fat_g,
        "macro_conflict": macro_conflict,
        "days": days,
    }


def zigzag_from_data(data):
    """يبني التدوير من ديكشنري الفورم اللي الخطة بتتولد منه."""
    mode = (data.get("zigzag_mode") or "off").strip()
    if mode == "off":
        return None

    custom = None
    raw = data.get("zigzag_custom")
    if raw:
        if isinstance(raw, str):
            parts = [p.strip() for p in raw.replace("،", ",").split(",") if p.strip()]
        else:
            parts = list(raw)
        if len(parts) == 7:
            custom = parts

    return build_zigzag(
        target_cal=data.get("goal_cal"),
        mode=mode,
        gender=data.get("gender", "ذكر"),
        weight=data.get("weight"),
        protein_per_kg=data.get("protein_per_kg", 1.6),
        fat_pct=data.get("fat_pct_cal", 30),
        tdee=data.get("tdee"),
        custom=custom,
    )

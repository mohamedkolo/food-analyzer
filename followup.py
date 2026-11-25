# -*- coding: utf-8 -*-
"""المتابعة — treating a returning client as a second visit, not a first one.

Until now the plan builder had no memory of anyone. A client who came back a
month later got a plan built from scratch, on a TDEE calculated from the
weight they no longer had, out of the same meal pool they had just spent four
weeks eating. Three separate problems, and the middle one is the reason most
plans stall:

**TDEE follows weight down.** A 95 kg man burns more than the same man at
88 kg. The 1800 kcal that was a 700 kcal deficit in January is a 400 kcal
deficit in March, and by June it is maintenance. The client did nothing
wrong and the plan quietly stopped working. Recalculating on the weight in
front of you is the single most useful thing a follow-up visit does.

So this module:

  * links visits by a folded name (plus a phone tail when there is one), so
    "أحمد على" and "احمد علي" are the same person;
  * measures what actually happened between the two visits -- kilos, days,
    and the rate per week that the kilos imply;
  * judges that rate against what is safe and expected for the client's
    goal, and moves the calorie target accordingly;
  * hands back the meals from the last plan so the new week can avoid them.

Nothing here decides anything on its own. Every number it produces is a
suggestion shown to the doctor with the reasoning attached, and the doctor
can overwrite it in the form before generating.
"""

import datetime as dt
import re

# ── معدلات التغيّر الأسبوعية ── كجم/أسبوع
SAFE_LOSS_MIN = 0.4       # أقل من كده الخطة مش شغالة
SAFE_LOSS_MAX = 1.2       # أكتر من كده خسارة عضل وخطر حصوات مرارة
PLATEAU_BAND = 0.15       # جوه النطاق ده الوزن عملياً ثابت
SAFE_GAIN_MIN = 0.1       # لزيادة العضل
SAFE_GAIN_MAX = 0.5       # أكتر من كده الزيادة دهون مش عضل

MIN_DAYS_TO_JUDGE = 7     # أقل من أسبوع بين الزيارتين = مياه مش دهون

# أقصى تعديل على السعرات في زيارة واحدة، عشان الخطة ما تتقلبش رأساً على عقب
MAX_STEP_KCAL = 250

GAIN_GOALS = ("muscle_gain", "bulking", "weight_gain")

_AR_FOLD = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي",
    "ؤ": "و", "ئ": "ي", "ً": "", "ٌ": "", "ٍ": "", "َ": "", "ُ": "",
    "ِ": "", "ّ": "", "ْ": "", "ـ": "",
})


def fold_name(name):
    """يوحّد صيغة الاسم عشان نفس الشخص ما يتعملهوش ملفين."""
    s = (name or "").strip().translate(_AR_FOLD).lower()
    s = re.sub(r"[^\w؀-ۿ ]+", " ", s)
    return " ".join(s.split())


def client_key(name, phone=None):
    """مفتاح العميل: الاسم الموحّد، ومعاه آخر ٦ أرقام من الموبايل لو موجود.

    الموبايل بيفرّق بين شخصين بنفس الاسم. لو مفيش موبايل، الاسم لوحده --
    وده مقصود: الدكتور بيشوف المتابعة قدامه ويقدر يرفضها."""
    base = fold_name(name)
    if not base:
        return ""
    digits = re.sub(r"\D", "", str(phone or ""))
    return f"{base}|{digits[-6:]}" if len(digits) >= 6 else base


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def bmr_mifflin(weight, height, age, gender):
    """Mifflin-St Jeor -- نفس المعادلة المستخدمة في باقي البرنامج."""
    w, h, a = _f(weight), _f(height), _f(age)
    if w <= 0 or h <= 0 or a <= 0:
        return 0.0
    base = 10 * w + 6.25 * h - 5 * a
    male = str(gender or "").strip().lower() in ("ذكر", "male", "m", "man")
    return base + (5 if male else -161)


def _days_between(then, now=None):
    now = now or dt.datetime.now()
    if isinstance(then, str):
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                then = dt.datetime.strptime(then[:26], fmt)
                break
            except ValueError:
                continue
        else:
            return 0
    if hasattr(then, "date") and not isinstance(then, dt.datetime):
        then = dt.datetime.combine(then, dt.time())
    try:
        return max(0, (now - then).days)
    except TypeError:
        return 0


# ── الأحكام ── كل واحد بنصّه بالعربي والإنجليزي وتعديله على السعرات
#    الرقم = كام سعرة نزوّد (+) أو نقلّل (-) على الهدف المحسوب من الـTDEE الجديد
VERDICTS = {
    "too_soon": (
        "أقل من أسبوع بين الزيارتين — فرق الوزن في المدة دي ممكن يكون مياه، مش حكم على الخطة.",
        "Less than a week apart — a weight difference over this span can be water, so it is not a judgement of the plan.", 0),
    "on_track": (
        "المعدل المسجّل داخل النطاق المعتاد لهدف العميل. الجديد بس إن الـTDEE اتحسب على الوزن الجديد.",
        "The recorded rate is inside the usual band for the client's goal. The only change is that TDEE was recalculated on the new weight.", 0),
    "too_fast": (
        "النزول المسجّل أسرع من النطاق المعتاد. راجع القياسات والحالة الطبية؛ النزول السريع ممكن يزوّد فقد العضل وخطر الحصوات. القاعدة اقترحت رفع السعرات شوية، والقرار ليك.",
        "The recorded loss is faster than the usual band. Review the measurements and clinical context; rapid loss can raise lean-mass loss and gallstone risk. The rule suggests a small calorie increase; the decision is yours.", 150),
    "too_slow": (
        "النزول المسجّل أبطأ من النطاق المعتاد. السبب مش معروف من الأرقام: راجع القياسات وتوقيتها والالتزام (لو متاح) والحالة الطبية قبل أي تعديل. القاعدة اقترحت تقليل السعرات شوية، والقرار ليك.",
        "The recorded loss is slower than the usual band. The numbers do not show why: review the measurements and their timing, adherence (if available) and the clinical context before any change. The rule suggests a small calorie reduction; the decision is yours.", -120),
    "plateau": (
        "الوزن المسجّل تقريباً ثابت. الأرقام لوحدها ماتقولش السبب: راجع القياسات وتوقيتها والالتزام (لو متاح) والحالة الطبية. الـTDEE اتحسب على الوزن الجديد، وده ممكن يصغّر العجز عن الزيارة اللي فاتت. القاعدة اقترحت تقليل السعرات شوية، والقرار ليك.",
        "The recorded weight is roughly flat. The numbers alone do not show why: review the measurements and their timing, adherence (if available) and the clinical context. TDEE was recalculated on the new weight, which can narrow the gap versus the last visit. The rule suggests a small calorie reduction; the decision is yours.", -150),
    "regained": (
        "الوزن المسجّل زاد. السبب مش معروف من الأرقام: راجع القياسات والالتزام (لو متاح) والحالة الطبية قبل أي تعديل. القاعدة اقترحت تقليل السعرات شوية، والقرار ليك.",
        "The recorded weight went up. The numbers do not show why: review the measurements, adherence (if available) and the clinical context before any change. The rule suggests a small calorie reduction; the decision is yours.", -100),
    "gain_on_track": (
        "الزيادة المسجّلة داخل النطاق المعتاد لزيادة العضل.",
        "The recorded gain is inside the usual band for muscle gain.", 0),
    "gain_too_fast": (
        "الزيادة المسجّلة أسرع من النطاق المعتاد، والزيادة السريعة غالباً بتبقى دهون أكتر. القاعدة اقترحت تقليل السعرات شوية، والقرار ليك.",
        "The recorded gain is faster than the usual band; fast gain tends to be more fat. The rule suggests a small calorie reduction; the decision is yours.", -150),
    "gain_stalled": (
        "الوزن المسجّل مش بيزيد. راجع القياسات والالتزام (لو متاح) قبل أي تعديل. القاعدة اقترحت زيادة السعرات شوية، والقرار ليك.",
        "The recorded weight is not rising. Review the measurements and adherence (if available) before any change. The rule suggests a small calorie increase; the decision is yours.", 150),
    "lost_on_gain": (
        "الوزن المسجّل نزل والهدف زيادة. راجع القياسات والالتزام (لو متاح). القاعدة اقترحت رفع السعرات، والقرار ليك.",
        "The recorded weight fell on a gaining goal. Review the measurements and adherence (if available). The rule suggests a calorie increase; the decision is yours.", 250),
}


def _classify(rate, goal_type):
    """يحوّل معدل التغيّر الأسبوعي لحكم."""
    if goal_type in GAIN_GOALS:
        if rate < -PLATEAU_BAND:
            return "lost_on_gain"
        if abs(rate) <= PLATEAU_BAND:
            return "gain_stalled"
        if rate > SAFE_GAIN_MAX:
            return "gain_too_fast"
        return "gain_on_track"

    # تخسيس / محافظة: التغيّر السالب هو النزول
    loss = -rate
    if loss > SAFE_LOSS_MAX:
        return "too_fast"
    if loss >= SAFE_LOSS_MIN:
        return "on_track"
    if abs(rate) <= PLATEAU_BAND:
        return "plateau"
    if loss > 0:
        return "too_slow"
    return "regained"


def assess(previous, current, lang="ar"):
    """يقارن زيارة بالزيارة اللي قبلها ويرجّع القراءة كاملة.

    previous / current: ديكشنري فيه على الأقل weight و height و age و gender
    و activity و goal_type و goal_cal، و created_at في previous.

    بيرجّع None لو مفيش زيارة سابقة أو مفيش وزن في أي منهم.
    """
    if not previous:
        return None

    old_w, new_w = _f(previous.get("weight")), _f(current.get("weight"))
    if old_w <= 0 or new_w <= 0:
        return None

    # لو الزيارة الحالية متسجّلة (بنعرض تاريخ قديم) نقيس للتاريخ بتاعها،
    # مش لدلوقتي -- من غير كده كل صفوف التاريخ بتقيس من نفس اللحظة
    days = _days_between(previous.get("created_at"),
                         _parse_dt(current.get("created_at")))
    delta = round(new_w - old_w, 1)
    weeks = days / 7.0
    rate = round(delta / weeks, 2) if weeks >= 0.5 else 0.0

    goal_type = current.get("goal_type") or previous.get("goal_type") or "weight_loss"
    verdict = "too_soon" if days < MIN_DAYS_TO_JUDGE else _classify(rate, goal_type)
    ar, en, step = VERDICTS[verdict]

    # ── الهدف الجديد ── الـTDEE بيتحسب على الوزن اللي قدامك دلوقتي
    height = current.get("height") or previous.get("height")
    age = current.get("age") or previous.get("age")
    gender = current.get("gender") or previous.get("gender")

    # معامل النشاط بيتاخد من الزيارة اللي فاتت نفسها: الـTDEE اللي الدكتور
    # اشتغل عليه وقتها مقسوم على BMR الوزن اللي كان عليه.
    #
    # ده مقصود إنه يسبق المعامل المكتوب في الفورم. الدكتور بيقدر يعدّل خانة
    # الـTDEE بإيده بعد الحساب التلقائي، وساعتها الرقم اللي اشتغل عليه فعلاً
    # مش بيساوي BMR × المعامل المختار. لو حسبنا الجديد بالمعامل بدل الرقم
    # الحقيقي، الـTDEE ممكن يطلع أعلى من الزيارة اللي فاتت والعميل نازل --
    # يعني نقول له إنه بيحرق أكتر وهو خسّان، وده عكس الحقيقة تماماً.
    activity = 0.0
    old_bmr = bmr_mifflin(old_w, previous.get("height") or height,
                          previous.get("age") or age,
                          previous.get("gender") or gender)
    prev_tdee = _f(previous.get("tdee"))
    if old_bmr > 0 and prev_tdee > 0:
        derived = prev_tdee / old_bmr
        if 1.1 <= derived <= 2.1:      # برّه النطاق ده الرقم غالباً غلط إدخال
            activity = round(derived, 3)
    if activity <= 0:
        activity = _f(current.get("activity") or previous.get("activity"), 1.55)
        activity = min(2.0, max(1.2, activity))

    bmr = bmr_mifflin(new_w, height, age, gender)
    new_tdee = int(round(bmr * activity)) if bmr else 0

    old_target = _f(previous.get("goal_cal"))
    old_tdee = _f(previous.get("tdee"))
    # نحافظ على نفس العجز/الفائض اللي كان شغال، وبعدين نعدّله حسب الحكم
    old_gap = (old_target - old_tdee) if (old_target and old_tdee) else 0
    suggested = int(round(new_tdee + old_gap + step)) if new_tdee else int(old_target)

    if verdict == "too_soon" and old_target:
        # قلنا إن الفرق ده مياه ومش دليل على حاجة -- يبقى ميبقاش دليل نبني
        # عليه هدف جديد كمان. الاقتراح يفضل هو الهدف الحالي.
        suggested = int(old_target)
    elif suggested and new_tdee:
        # حد أقصى للتغيير في الزيارة الواحدة
        if old_target:
            suggested = max(int(old_target - MAX_STEP_KCAL),
                            min(int(old_target + MAX_STEP_KCAL), suggested))
        # ومفيش خطة تنزل تحت الحد الآمن
        floor = 1200 if str(current.get("gender") or "").strip().lower() not in (
            "ذكر", "male", "m", "man") else 1500
        suggested = max(floor, suggested)

    fat_delta = None
    old_fat, new_fat = _f(previous.get("fat_pct")), _f(current.get("fat_pct"))
    if old_fat > 0 and new_fat > 0:
        fat_delta = round(new_fat - old_fat, 1)

    return {
        "days": days,
        "weeks": round(weeks, 1),
        "old_weight": round(old_w, 1),
        "new_weight": round(new_w, 1),
        "delta": delta,
        "rate": rate,
        "fat_delta": fat_delta,
        "verdict": verdict,
        "note": ar if lang == "ar" else en,
        "note_ar": ar,
        "note_en": en,
        "step": step,
        "old_tdee": int(old_tdee) if old_tdee else None,
        "new_tdee": new_tdee or None,
        "old_goal_cal": int(old_target) if old_target else None,
        "suggested_goal_cal": suggested or None,
        "activity": round(activity, 3),
        "tdee_drop": (int(old_tdee) - new_tdee) if (old_tdee and new_tdee) else None,
        "goal_type": goal_type,
        "direction": "down" if delta < 0 else ("up" if delta > 0 else "flat"),
    }


def meals_in_plan(plan):
    """كل نصوص الوجبات في خطة، عشان الخطة الجديدة تتفاداها."""
    keys = ("breakfast", "lunch", "dinner", "snack", "snack1", "snack2",
            "meal1", "meal2", "iftar", "suhoor", "pre_workout", "post_workout")
    out = []
    for day in (plan or []):
        if not isinstance(day, dict):
            continue
        for k in keys:
            v = day.get(k)
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
    return out


def summarise_history(visits):
    """خط سير العميل من أول زيارة لآخر واحدة."""
    weights = [(v, _f(v.get("weight"))) for v in visits]
    weights = [(v, w) for v, w in weights if w > 0]
    if not weights:
        return None
    first_v, first_w = weights[-1]      # الزيارات مرتّبة من الأحدث
    last_v, last_w = weights[0]
    days = _days_between(first_v.get("created_at"),
                         _parse_dt(last_v.get("created_at")) or dt.datetime.now())
    total = round(last_w - first_w, 1)
    return {
        "visits": len(visits),
        "first_weight": round(first_w, 1),
        "current_weight": round(last_w, 1),
        "total_change": total,
        "days": days,
        "rate": round(total / (days / 7.0), 2) if days >= 7 else None,
    }


# ── تحليل التاريخ كله ── مش آخر زيارتين بس
#
# ‏assess() بتقارن زيارتين. ده كافي لحكم على أسبوع، لكن مش كافي لسؤال "الخطة
# شغّالة ولا لأ": وزن واقف شهر واحد ممكن يكون مياه، ووزن واقف شهرين ورا بعض
# معناه إن الهدف نفسه محتاج مراجعة. فبنقرا كل فترة بين زيارتين بنفس الحكم
# (assess) ونقول للدكتور لو نفس الحكم اتكرر. مفيش رقم جديد بيتحسب هنا ولا
# السعرات بتتغيّر -- ده شرح للدكتور يقرر عليه، من الأوزان اللي اتسجّلت بس.
_STALLED = ("plateau", "too_slow", "regained", "gain_stalled", "lost_on_gain")

_STREAK_TEXT = {
    "plateau": ("الوزن واقف", "Weight has stalled"),
    "too_slow": ("النزول أبطأ من المتوقع", "Loss has been slower than expected"),
    "regained": ("الوزن بيزيد", "Weight has been going up"),
    "gain_stalled": ("الوزن مش بيزيد", "Weight has not been rising"),
    "lost_on_gain": ("الوزن بينزل والهدف زيادة", "Weight has been falling on a gaining goal"),
}


def analyse_history(visits, current, lang="ar", limit=6, total_visits=None):
    """يقرا كل الفترات بين زيارات العميل لحد الزيارة الحالية.

    visits: زيارات العميل، الأحدث الأول (زي visits_for). current: بيانات الزيارة
    الجديدة. بيرجّع None لو مفيش وزن مسجّل نبني عليه -- مش بنخترع تاريخ."""
    chron = [dict(v) for v in reversed(list(visits or [])[:limit])
             if _f(dict(v).get("weight")) > 0]
    if not chron or _f((current or {}).get("weight")) <= 0:
        return None

    points = chron + [dict(current)]
    intervals = []
    for old, new in zip(points, points[1:]):
        a = assess(old, new, lang)
        if not a:
            continue
        intervals.append({
            "from_visit": old.get("visit_no"),
            "to_visit": new.get("visit_no") if new is not points[-1] else None,
            "date": str(old.get("created_at") or "")[:10],
            "old_weight": a["old_weight"], "new_weight": a["new_weight"],
            "delta": a["delta"], "days": a["days"], "rate": a["rate"],
            "verdict": a["verdict"],
        })
    if not intervals:
        return None

    # ‏الفترة الأقصر من أسبوع مش حكم: مابتكسرش السلسلة ومابتزوّدها
    judged = [i for i in intervals if i["verdict"] != "too_soon"]
    streak = {"verdict": judged[-1]["verdict"] if judged else None, "count": 0}
    for i in reversed(judged):
        if i["verdict"] != streak["verdict"]:
            break
        streak["count"] += 1

    # ‏وصف لترند وزن متسجّل، مش حكم على السبب. الثبات ممكن يكون قياس أو
    # توقيت أو التزام أو حالة طبية، فالنص بيطلب من الدكتور يراجع دي كلها
    # ومابيفرضش تعديل سعرات.
    note_ar = note_en = ""
    if streak["count"] >= 2 and streak["verdict"] in _STALLED:
        ar, en = _STREAK_TEXT[streak["verdict"]]
        note_ar = ("ترند متسجّل: %s في %d فترات ورا بعض. ده وصف للأوزان بس، "
                   "مش دليل على السبب. راجع القياسات وتوقيتها والالتزام (لو "
                   "متاح) والحالة الطبية قبل ما تقرر أي تعديل." % (ar, streak["count"]))
        note_en = ("Recorded trend: %s over %d intervals in a row. This describes the "
                   "weights only, not the cause. Review the measurements and their "
                   "timing, adherence (if available) and the clinical context before "
                   "deciding on any change." % (en, streak["count"]))

    first_w = _f(chron[0].get("weight"))
    return {
        "intervals": intervals,
        "streak": streak,
        "streak_note_ar": note_ar,
        "streak_note_en": note_en,
        "net_change": round(_f(current.get("weight")) - first_w, 1),
        "visits_used": len(chron),
        # ‏العدد الكلي لزيارات العميل، عشان الشاشة تقول لو القراءة آخر `limit` بس
        "total_visits": max(total_visits or 0, len(chron)),
    }


def meals_across_plans(visits, limit=3):
    """وجبات آخر `limit` خطط، الأحدث الأول، من غير تكرار.

    ‏الخطة بتتفادى أكل أكتر من أسبوع واحد: عميل جه تلات مرات أكل التلات
    أسابيع، وكان بياخد نفس الأطباق تاني من الأسبوع اللي قبل اللي فات."""
    import json
    out, seen = [], set()
    for v in list(visits or [])[:limit]:
        try:
            plan = json.loads(dict(v).get("plan_json") or "[]")
        except (ValueError, TypeError):
            continue
        for m in meals_in_plan(plan):
            if m not in seen:
                seen.add(m)
                out.append(m)
    return out


def _parse_dt(value):
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(value[:26], fmt)
            except ValueError:
                continue
    return None


# ── لوحة المتابعة ── كل العملاء في صفحة واحدة
#
# ‏صفحة /followups كانت بتقول: الاسم، عدد الزيارات، وتاريخ آخر زيارة. تلات
# حاجات مش فيهم ولا واحدة بتقول **إيه اللي حصل**. الدكتور عنده ستين ملف،
# وعشان يعرف مين واقف كان لازم يفتح الستين واحد واحد.
#
# ‏اللي اللوحة بتجاوب عليه: مين نازل، مين واقف، ومين غاب. والتلاتة دول
# أحكام مختلفة ومحتاجين تصرّف مختلف:
#
#   * نازل/واقف/زايد = حكم على **آخر فترة** (آخر زيارتين)، مش على التاريخ
#     كله. عميل نزل ١٠ كيلو في ٦ شهور وواقف من شهرين، المهم إنه واقف
#     دلوقتي -- التاريخ الحلو مش بيلغي إن الخطة وقفت.
#   * غاب = حكم على **الوقت من آخر زيارة**، والدكتور مشفوش أصلاً. ده
#     بيسبق أي حكم على المعدل: لو العميل مجاش من شهرين، مافيش معنى نقول
#     "نازل كويس" على قياس عمره شهرين. الأول يرجع، وبعدين نحكم.
#
# ‏الدورة ٤ أسابيع (زي "المراجعة بعد ٤ أسابيع" اللي على الورقة)، فـ:
#   ٢٨-٥٥ يوم = ميعاده عدّى، ٥٦+ = غاب (دورتين كاملتين).
REVIEW_DAYS = 28
LAPSED_DAYS = REVIEW_DAYS * 2

# ‏ترتيب اللوحة = ترتيب الإلحاح، مش الأبجدية ولا التاريخ. اللي محتاج
# تدخّل فوق. الرقم الأصغر = أعلى.
_URGENCY = {
    "lapsed": 0,        # ‏غاب -- اتصل بيه
    "regained": 1,      # ‏رجع زاد
    "lost_on_gain": 1,
    "plateau": 2,       # ‏واقف
    "gain_stalled": 2,
    "too_fast": 3,      # ‏أسرع من الآمن
    "gain_too_fast": 3,
    "due": 4,           # ‏ميعاده عدّى بس لسه في الدورة
    "too_slow": 5,
    "on_track": 6,      # ‏ماشي -- مش محتاج حاجة
    "gain_on_track": 6,
    "too_soon": 7,
    "single": 8,        # ‏زيارة واحدة -- مافيش مقارنة أصلاً
}

# ‏حالات اللوحة اللي مش جاية من VERDICTS (دي أحكام على الوقت مش على المعدل)
_BOARD_ONLY = {
    # ‏"بقاله/بقالها" مذكّر ومؤنث، ونص العملاء ستات -- فالعدّ من غير ضمير
    "lapsed": ("آخر زيارة من {days} يوم — محتاج مكالمة",
               "Lapsed — last seen {days} days ago"),
    "due": ("ميعاد المراجعة عدّى بـ{over} يوم",
            "Review is {over} days overdue"),
    "single": ("زيارة واحدة — مافيش مقارنة لسه",
               "One visit — nothing to compare yet"),
}

# ‏اللون بيتقرا قبل النص. تلات مجموعات بس: محتاج تدخّل، تحت الملاحظة،
# ماشي. أكتر من كده بيبقى ألوان كتير والعين بتبطّل تفرّق.
_TONE = {
    "lapsed": "bad", "regained": "bad", "lost_on_gain": "bad",
    "plateau": "warn", "gain_stalled": "warn", "too_fast": "warn",
    "gain_too_fast": "warn", "due": "warn", "too_slow": "warn",
    "on_track": "good", "gain_on_track": "good",
    "too_soon": "idle", "single": "idle",
}

_SHORT = {
    "lapsed": ("غاب", "Lapsed"),
    "regained": ("رجع زاد", "Regained"),
    "lost_on_gain": ("نزل والهدف زيادة", "Lost on a gain plan"),
    "plateau": ("واقف", "Stalled"),
    "gain_stalled": ("مش بيزيد", "Not gaining"),
    "too_fast": ("أسرع من الآمن", "Too fast"),
    "gain_too_fast": ("زيادة سريعة", "Gaining too fast"),
    "due": ("ميعاده عدّى", "Review due"),
    "too_slow": ("بطيء", "Slow"),
    "on_track": ("ماشي", "On track"),
    "gain_on_track": ("ماشي", "On track"),
    "too_soon": ("بدري على الحكم", "Too soon to judge"),
    "single": ("زيارة واحدة", "One visit"),
}


def board(visits, lang="ar", today=None):
    """‏كل عملاء الدكتور في صف واحد لكل عميل، مرتّبين بالإلحاح.

    visits: كل صفوف plan_visits بتاعت الدكتور، أي ترتيب. بنجمّعها في
    بايثون مش في SQL عشان أول وآخر وزن في نفس الاستعلام محتاج window
    functions، وSQLite المحلي وPostgres اللي على الاستضافة بيختلفوا فيها.

    بيرجّع {"rows": [...], "counts": {...}}.
    """
    today = today or dt.datetime.now()
    by_key = {}
    for v in (visits or []):
        v = dict(v)
        if not v.get("client_key"):
            continue
        by_key.setdefault(v["client_key"], []).append(v)

    rows = []
    for key, group in by_key.items():
        # ‏الأحدث الأول -- زي ما visits_for بترجّعها، وassess متوقعة كده
        group.sort(key=lambda r: _parse_dt(r.get("created_at")) or dt.datetime.min,
                   reverse=True)
        last = group[0]
        prev = group[1] if len(group) > 1 else None
        since = _days_between(last.get("created_at"), today)
        progress = assess(prev, last, lang) if prev else None

        # ‏الغياب بيسبق المعدل: لو مجاش من دورتين، الحكم على قياس قديم
        # مش حكم على حالته دلوقتي.
        if since >= LAPSED_DAYS:
            state = "lapsed"
        elif not progress:
            state = "due" if since >= REVIEW_DAYS else "single"
        elif since >= REVIEW_DAYS and progress["verdict"] in (
                "on_track", "gain_on_track", "too_soon"):
            # ‏ماشي كويس بس ميعاده عدّى -- التذكرة هي الخبر، مش المعدل
            state = "due"
        else:
            state = progress["verdict"]

        if state in _BOARD_ONLY:
            ar, en = _BOARD_ONLY[state]
            note = (ar if lang == "ar" else en).format(
                days=since, over=max(0, since - REVIEW_DAYS))
        else:
            note = progress["note"]

        hist = summarise_history(group)
        rows.append({
            "client_key": key,
            "client_name": last.get("client_name") or "",
            "phone": last.get("phone") or "",
            "visits": len(group),
            "days_since": since,
            "state": state,
            "tone": _TONE.get(state, "idle"),
            "label": _SHORT.get(state, ("", ""))[0 if lang == "ar" else 1],
            "note": note,
            "weight": round(_f(last.get("weight")), 1) or None,
            "last_delta": progress["delta"] if progress else None,
            "last_rate": progress["rate"] if progress else None,
            "total_change": hist["total_change"] if hist else None,
            "first_weight": hist["first_weight"] if hist else None,
            "goal_type": last.get("goal_type") or "",
        })

    rows.sort(key=lambda r: (_URGENCY.get(r["state"], 9), r["days_since"] * -1,
                             r["client_name"]))
    counts = {"total": len(rows), "needs": 0, "watch": 0, "ok": 0}
    for r in rows:
        if r["tone"] == "bad":
            counts["needs"] += 1
        elif r["tone"] == "warn":
            counts["watch"] += 1
        elif r["tone"] == "good":
            counts["ok"] += 1
    return {"rows": rows, "counts": counts}

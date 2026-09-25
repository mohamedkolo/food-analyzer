# -*- coding: utf-8 -*-
"""قراءة ورقة تحليل الجسم على السيرفر نفسه، بدون أي خدمة برّه.

ليه موجود: الميزة كانت محتاجة مفتاح API، والمفتاح مربوط بحساب الدكتور
وفيزته -- فالميزة كانت مقفولة لحد ما يعمل حساب. الملف ده بيشيل الشرط ده:
القراءة بتحصل على السيرفر، مجاناً، وبدون ما تخرج صورة العميل من السيرفر.

بيستخدم rapidocr (نماذج ONNX جوّه الحزمة، تتركّب بـpip من غير أي حزمة
نظام) -- ده مهم لأن الاستضافة مابتسمحش بتركيب برامج نظام.

**حدوده، مقيسة مش مفترضة:**

  ورقة إنجليزية (InBody / Tanita وأي جهاز):  الأرقام والعناوين بتتقرا صح
  ورقة عناوينها عربية:                      الأرقام بتتقرا، العناوين لأ

في الحالة التانية مانعرفش الرقم ده الوزن ولا الطول، فمابنخمّنش: بنقول
مقدرناش نقرا. اللي عنده مفتاح API بيشتغل بالطريق التاني اللي بيقرا العربي.

نفس قاعدة الملف التاني: **مايخمّنش ولا رقم.**
"""

import re

# ‏العناوين وأشكالها اللي بتطلع من الـOCR. الترتيب مهم: أطول تعبير الأول،
# عشان "target weight" ما تتقراش كـ"weight".
_LABELS = [
    ("fat_pct", ("percent body fat", "percentbodyfat", "body fat", "bodyfat",
                 "pbf", "fat%", "fat %")),
    ("bmr", ("basal metabolic rate", "basalmetabolicrate", "basal metabolic",
             "bmr")),
    ("bmi", ("bmi",)),
    ("muscle_mass", ("skeletal muscle mass", "skeletalmusclemass",
                     "skeletal muscle", "smm", "muscle mass")),
    ("visceral_fat", ("visceral fat level", "visceralfatlevel",
                      "visceral fat", "vfa", "visceral")),
    ("body_water", ("total body water", "totalbodywater", "tbw", "body water")),
    ("weight", ("weight", "wt")),
    ("height", ("height", "ht")),
    ("age", ("age",)),
    ("gender", ("gender", "sex")),
]

# ‏السطور دي أرقامها مش قراءة العميل: هدف، أو نطاق طبيعي، أو تحكّم في الوزن.
# "Target Weight 60.0 kg" لو اتقرت كوزن، الخطة تتحسب على وزن العميل المستهدف
# مش وزنه الحالي -- والفرق ١٨ كيلو في المثال اللي جرّبته.
_NOT_A_READING = ("target", "ideal", "control", "range", "normal", "recommend",
                  "desirable", "standard", "goal", "loss", "gain", "obesity",
                  "degree", "score", "history", "graph", "date", "trend")

_NUMBER = re.compile(r"(\d{1,4}(?:[.,]\d{1,2})?)")


def available():
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


def _boxes(image_bytes):
    """‏يرجّع [(نص, وسط س, وسط ص, أعلى, أسفل)] لكل صندوق قرأه الـOCR."""
    import io
    import tempfile
    import os as _os
    from rapidocr_onnxruntime import RapidOCR

    try:
        engine = RapidOCR()
    except Exception as e:
        raise RuntimeError("محرّك القراءة مش قادر يشتغل على السيرفر (%s)"
                           % type(e).__name__)
    # ‏rapidocr بتاخد مسار أو numpy. بنكتب ملف مؤقت وبنمسحه، عشان مانعتمدش
    # على numpy/cv2 في المسار ده.
    fd, path = tempfile.mkstemp(suffix=".img")
    try:
        with _os.fdopen(fd, "wb") as fh:
            fh.write(image_bytes)
        try:
            result, _ = engine(path)
        except Exception as e:
            # ‏ملف صورة ناقص أو تالف: PIL بترفع OSError من جوّه المحرّك،
            # وكانت بتطلع خطأ 500 فاضي. الرفع من الموبايل بيتقطع عادي.
            raise RuntimeError("الصورة مش سليمة أو الرفع اتقطع -- صوّرها "
                               "تاني وارفعها (%s)" % type(e).__name__)
    finally:
        try:
            _os.remove(path)
        except OSError:
            pass
        # ‏النموذج بياخد ~٢٨٠ ميجا رام. الاستضافة عندها ٥١٢، والتطبيق ماشي
        # فيهم، فبنسيبه يتفضى بعد كل قراءة بدل ما يفضل مقيم.
        del engine
        import gc
        gc.collect()

    out = []
    slopes = []
    for item in (result or []):
        try:
            points, text = item[0], item[1]
        except (TypeError, IndexError):
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        out.append((str(text), sum(xs) / 4.0, sum(ys) / 4.0, min(ys), max(ys)))
        # ‏ميل الحرف نفسه: الحد الأعلى للصندوق. الورقة المصوّرة بموبايل
        # دايماً مايلة شوية، والميل ده هو اللي بيخلّي السطر مش أفقي.
        try:
            dx = points[1][0] - points[0][0]
            dy = points[1][1] - points[0][1]
            if dx > 20:
                slopes.append(dy / float(dx))
        except (TypeError, IndexError):
            pass
    slopes.sort()
    slope = slopes[len(slopes) // 2] if slopes else 0.0
    return out, slope


def _label_of(text):
    low = re.sub(r"[^a-z% ]", "", text.lower())
    if any(bad in low for bad in _NOT_A_READING):
        return None
    for field, forms in _LABELS:
        for form in forms:
            if form in low:
                return field
    return None


def _number_in(text):
    match = _NUMBER.search(text.replace(",", "."))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def parse_boxes(boxes, slope=0.0):
    """‏يطلّع الأرقام من صناديق الـOCR.

    العنوان والرقم بيبقوا في صندوقين مختلفين: العنوان شمال والرقم يمين على
    نفس السطر. فبندوّر على أقرب صندوق فيه رقم **على يمين** العنوان وبينهم
    تقاطع رأسي -- مش أقرب صندوق عمومًا، عشان مانخدش رقم من السطر اللي تحت.
    """
    found = {}
    for text, cx, cy, top, bottom in boxes:
        field = _label_of(text)
        if not field or field in found:
            continue

        if field == "gender":
            low = text.lower()
            for box in boxes:
                low += " " + box[0].lower() if abs(box[2] - cy) < 18 else ""
            if "female" in low or "anthy" in low:
                found["gender"] = "female"
            elif "male" in low:
                found["gender"] = "male"
            continue

        # ‏رقم في نفس الصندوق؟ ("BMI 28.8")
        same = _number_in(re.sub(r"[a-zA-Z%/]", " ", text))
        if same is not None:
            found[field] = same
            continue

        # ‏الورقة المصوّرة بموبايل مايلة شوية، فالسطر مش أفقي تماماً. شرط
        # التقاطع الرأسي الصارم كان بيفشل مع ميل ٢.٥ درجة بس -- كان بيسيب
        # الـBMI والعمر فاضيين في صورة القراية فيها واضحة. فالمقارنة بقت على
        # مسافة مركز السطر نسبةً لارتفاع الصندوق: بتتحمّل الميل وبرضه
        # مابتاخدش رقم من السطر اللي تحت.
        # ‏السطر مايل، فبنحسب مكانه المتوقّع عند س الرقم بدل ما نقارن
        # بالارتفاع نفسه. جرّبت طريقتين غلط قبل كده: تقاطع رأسي صارم فشل مع
        # ميل ٢.٥ درجة وساب الـBMI فاضي، وترخية الشرط خدت أرقام من السطر
        # اللي تحت وطلّعت "الطول ٢٩ سم". تصحيح الميل بيحل الاتنين: الشرط
        # يفضل ضيّق والسطر المايل يفضل سطر واحد.
        height = max(1.0, bottom - top)
        best = None
        for other_text, ocx, ocy, otop, obottom in boxes:
            if ocx <= cx:
                continue
            expected = cy + slope * (ocx - cx)
            if abs(ocy - expected) > height * 0.6:
                continue
            value = _number_in(other_text)
            if value is None:
                continue
            if best is None or ocx < best[0]:
                best = (ocx, value)
        if best is not None:
            found[field] = best[1]
    return found


def read(image_bytes):
    """‏يرجّع نفس شكل ديكشنري lab_report، أو يرفع RuntimeError برسالة عربية."""
    boxes, slope = _boxes(image_bytes)
    if not boxes:
        raise RuntimeError("مقدرتش أقرا أي كلام في الصورة. صوّرها في نور أحسن "
                           "وخلي الورقة كلها في الكادر.")

    found = parse_boxes(boxes, slope)
    text_all = " ".join(b[0] for b in boxes)

    # ‏ورقة عناوينها عربية: الأرقام بتتقرا والعناوين لأ. مانعرفش الرقم ده
    # الوزن ولا الطول، فمابنخمّنش.
    if not any(k in found for k in ("weight", "height", "fat_pct", "bmi", "bmr")):
        if re.search(r"\d", text_all):
            raise RuntimeError("قريت أرقام في الصورة بس مش عارف كل رقم بيخص "
                               "إيه -- الورقة عناوينها مش إنجليزي. اكتب "
                               "البيانات بإيدك، أو فعّل القراءة المتقدمة.")
        raise RuntimeError("الصورة دي مش ورقة تحليل جسم. صوّر ورقة الـInBody "
                           "أو جهاز قياس نسبة الدهون.")

    # ‏فحص تناسق: الـBMI = الوزن ÷ (الطول بالمتر)². التلاتة مطبوعين على
    # الورقة، فلو الحساب مااتطابقش يبقى واحد منهم اتقرا غلط -- ومانعرفش
    # مين. فبنشيل التلاتة ونقول للدكتور يكتبهم. الفحص ده بيمسك بالظبط نوع
    # الغلط اللي حدود المعقول مابتمسكهوش: رقم معقول في الخانة الغلط.
    w, hgt, bmi = found.get("weight"), found.get("height"), found.get("bmi")
    mismatch = False
    if w and hgt and bmi and hgt > 0:
        try:
            computed = w / ((hgt / 100.0) ** 2)
            mismatch = abs(computed - bmi) > 1.5
        except ZeroDivisionError:
            mismatch = True
    if mismatch:
        for field in ("weight", "height", "bmi"):
            found.pop(field, None)

    out = dict(found)
    out["is_body_report"] = True
    out["name"] = None          # ‏الاسم على الورقة مش دايماً، وتخمينه غلط
    out["extras"] = []
    out["unreadable"] = [label for label, _ in _LABELS
                         if label not in found
                         and label in ("weight", "height", "fat_pct", "bmi")]
    return out

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


# ‏القراءة بتتعمل في **عملية منفصلة**، مش جوّه السيرفر.
#
# النموذج بياخد ~٢٨٠ ميجا رام، والاستضافة المجانية عندها ٥١٢ والتطبيق ماشي
# فيهم. لو القراءة اتعملت جوّه السيرفر، أول صورة ممكن توصل للحد وتخلّي
# النظام يقتل العملية -- يعني الموقع كله يقع، مش القراءة بس. العملية
# المنفصلة بتموت لوحدها وبترجّع رامها للنظام، ولو النظام قتلها الموقع
# مايحسّش، وبنقول للدكتور رسالة مفهومة.
_CHILD = r"""
import sys, json, tempfile, os
def main():
    data = sys.stdin.buffer.read()
    from rapidocr_onnxruntime import RapidOCR
    fd, path = tempfile.mkstemp(suffix=".img")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        result, _ = RapidOCR()(path)
    finally:
        try: os.remove(path)
        except OSError: pass
    out = []
    for item in (result or []):
        try:
            points, text = item[0], item[1]
        except (TypeError, IndexError):
            continue
        out.append({"t": str(text),
                    "p": [[float(p[0]), float(p[1])] for p in points]})
    sys.stdout.write(json.dumps(out))
try:
    main()
except Exception as e:
    sys.stderr.write(type(e).__name__)
    sys.exit(3)
"""

READ_TIMEOUT = 90


def _boxes(image_bytes):
    """‏يرجّع ([(نص, وسط س, وسط ص, أعلى, أسفل)], ميل الورقة)."""
    import json
    import subprocess
    import sys

    try:
        proc = subprocess.run([sys.executable, "-c", _CHILD],
                              input=image_bytes, capture_output=True,
                              timeout=READ_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RuntimeError("القراءة خدت وقت أطول من اللازم -- صوّر الورقة "
                           "بدقة أقل وجرّب تاني")
    except FileNotFoundError:
        raise RuntimeError("محرّك القراءة مش متركّب على السيرفر")

    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode("utf-8", "replace").strip()[:40]
        if proc.returncode < 0:
            # ‏النظام قتلها (غالباً الرام). الموقع لسه واقف، وده المقصود.
            raise RuntimeError("السيرفر مش قادر يقرا الصورة دي (رام) -- "
                               "صوّرها بدقة أقل وجرّب تاني")
        raise RuntimeError("الصورة مش سليمة أو الرفع اتقطع -- صوّرها تاني "
                           "وارفعها (%s)" % (detail or "?"))
    try:
        items = json.loads((proc.stdout or b"").decode("utf-8", "replace"))
    except ValueError:
        raise RuntimeError("القراءة رجعت رد مش مفهوم -- جرّب تاني")

    out = []
    slopes = []
    for item in items:
        points = item.get("p") or []
        if len(points) < 2:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        out.append((item.get("t", ""), sum(xs) / len(xs), sum(ys) / len(ys),
                    min(ys), max(ys)))
        dx = points[1][0] - points[0][0]
        dy = points[1][1] - points[0][1]
        if dx > 20:
            slopes.append(dy / float(dx))
    slopes.sort()
    slope = slopes[len(slopes) // 2] if slopes else 0.0
    return out, slope


def _label_form(text):
    """‏يرجّع (الخانة، شكل العنوان اللي طابق) أو (None, None)."""
    low = re.sub(r"[^a-z% ]", "", text.lower())
    if any(bad in low for bad in _NOT_A_READING):
        return None, None
    for field, forms in _LABELS:
        for form in forms:
            if form in low:
                return field, form
    return None, None


def _label_of(text):
    return _label_form(text)[0]


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


# ‏رقم في أول الكلمة، والحرف اللي قبله مايكونش حرف أبجدي. الشرط التاني
# مهم: "kg/m2" فيها رقم ٢، ولولا الشرط ده كانت تتقرا كقيمة.
_VALUE_WORD = re.compile(r"^[^\dA-Za-z]{0,2}(\d{1,4}(?:[.,]\d{1,2})?)")


def _value_word(word):
    match = _VALUE_WORD.match(word.replace(",", "."))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _after_label(words, form):
    """‏رقم الكلمة اللي بعد آخر كلمة في العنوان.

    ليه: سطر زي "Height 165.0 cm Weight 78.4 kg" فيه عنوانين. لو خدنا أول
    رقم في السطر كان الوزن هيبقى ١٦٥. فبندوّر على الرقم اللي **بعد** العنوان.
    """
    norm = [re.sub(r"[^a-z% ]", "", w.lower()) for w in words]
    for i in range(len(words)):
        acc = ""
        for j in range(i, len(words)):
            acc = (acc + " " + norm[j]).strip()
            if form in acc or form in acc.replace(" ", ""):
                return j + 1
    return 0


def parse_lines(lines):
    """‏يطلّع الأرقام من سطور محرّك المتصفح.

    محرّك المتصفح بيرجّع الكلام مجمّع في سطور فعلية، فمافيش تخمين هندسي:
    العنوان والرقم في نفس السطر بالظبط. ده أضبط من حساب الميل اللي
    محرّك السيرفر محتاجه، عشان التجميع بيحصل جوّه المحرّك نفسه.

    الشكل: [[{"t": كلمة, "x": مكانها}, ...], ...] -- أو سطور كنص عادي.
    """
    found = {}
    for line in lines or []:
        if isinstance(line, str):
            words = line.split()
        else:
            words = [w if isinstance(w, str) else str((w or {}).get("t", ""))
                     for w in (line or [])]
        words = [w for w in words if w.strip()]
        if not words:
            continue
        text = " ".join(words)
        field, form = _label_form(text)
        if not field:
            continue

        if field == "gender":
            low = text.lower()
            if "female" in low:
                found.setdefault("gender", "female")
            elif "male" in low:
                found.setdefault("gender", "male")
            continue

        if field in found:
            continue
        for word in words[_after_label(words, form):]:
            value = _value_word(word)
            if value is not None:
                found[field] = value
                break
    return found


def merge_found(founds):
    """‏يجمع قراءتين للصورة الواحدة: اللي اتفقوا عليه يتاخد، واللي اختلفوا فيه يتشال.

    المتصفح بيقرا الصورة مرتين -- مرة كما هي ومرة بعد تحديد الحدود --
    عشان كل معالجة بتنجح في حاجة التانية بتفشل فيها (التحديد رفع القراءة
    في الصورة المهزوزة من ٥ خانات لـ٩). بس لو الاتنين طلّعوا رقمين
    مختلفين لنفس الخانة، يبقى واحد منهم غلط ومانعرفش مين -- فبنشيلها.
    الدكتور يكتبها بإيده، وده أحسن ألف مرة من رقم غلط في خطة.
    """
    merged = {}
    conflict = set()
    for found in founds:
        for key, value in (found or {}).items():
            if key not in merged:
                merged[key] = value
                continue
            old = merged[key]
            if isinstance(old, (int, float)) and isinstance(value, (int, float)):
                if abs(float(old) - float(value)) > 0.05:
                    conflict.add(key)
            elif old != value:
                conflict.add(key)
    for key in conflict:
        merged.pop(key, None)
    return merged


def read_passes(passes):
    """‏سطور أكتر من قراءة لنفس الصورة -> نفس شكل ديكشنري read()."""
    passes = [p for p in (passes or []) if p]
    flat = []
    for one in passes:
        for line in one:
            if isinstance(line, str):
                flat.append(line)
            else:
                flat.append(" ".join(
                    w if isinstance(w, str) else str((w or {}).get("t", ""))
                    for w in (line or [])))
    text_all = " ".join(flat).strip()
    if not text_all:
        raise RuntimeError("مقدرتش أقرا أي كلام في الصورة. صوّرها في نور أحسن "
                           "وخلي الورقة كلها في الكادر.")
    return interpret(merge_found([parse_lines(one) for one in passes]), text_all)


def read_lines(lines):
    """‏نفس شكل ديكشنري read()، بس من سطور جاهزة مش من صورة."""
    flat = []
    for line in lines or []:
        if isinstance(line, str):
            flat.append(line)
        else:
            flat.append(" ".join(
                w if isinstance(w, str) else str((w or {}).get("t", ""))
                for w in (line or [])))
    text_all = " ".join(flat).strip()
    if not text_all:
        raise RuntimeError("مقدرتش أقرا أي كلام في الصورة. صوّرها في نور أحسن "
                           "وخلي الورقة كلها في الكادر.")
    return interpret(parse_lines(lines), text_all)


def read(image_bytes):
    """‏يرجّع نفس شكل ديكشنري lab_report، أو يرفع RuntimeError برسالة عربية."""
    boxes, slope = _boxes(image_bytes)
    if not boxes:
        raise RuntimeError("مقدرتش أقرا أي كلام في الصورة. صوّرها في نور أحسن "
                           "وخلي الورقة كلها في الكادر.")
    return interpret(parse_boxes(boxes, slope),
                     " ".join(b[0] for b in boxes))


def interpret(found, text_all):
    """‏الفحوص اللي بتخلّي القراءة آمنة، مشتركة بين كل المحرّكات.

    أي محرّك (السيرفر أو المتصفح) بيوصل لنفس الديكشنري ده، فالحواجز اللي
    بتمنع الرقم الغلط بتشتغل مرة واحدة في مكان واحد وعليها اختبارات.
    """
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

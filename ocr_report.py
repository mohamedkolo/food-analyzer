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
# ‏**نسبة الدهون وكتلة الدهون مش نفس الحاجة**، وورقة GAIA بتطبع الاتنين:
#
#     P.B.F.     36.1     نسبة الدهون (٪)
#     Body Fat   24.3     كتلة الدهون (كجم)
#
# ‏"body fat" كانت في قايمة النسبة، فالقراية كانت تاخد ٢٤.٣ وتحطها كنسبة
# دهون. و٢٤.٣٪ نسبة **معقولة تماماً**، فحدود المعقول مش هتمسكها، والخطة
# تتحسب على نسبة غلط بفرق ١٢ نقطة. فالنسبة بقى ليها عناوينها الصريحة بس،
# والكتلة بقت خانة لوحدها -- ومنها بنحسب النسبة بالقسمة على الوزن (٢٤.٣ ÷
# ٦٧.٣ = ٣٦.١٪، وده بالظبط الرقم المطبوع).
_LABELS = [
    ("fat_pct", ("percent body fat", "percentbodyfat", "pbf", "fat%", "fat %",
                 "body fat %", "bodyfat%", "pbf%")),
    ("fat_mass", ("body fat", "bodyfat", "fat mass", "fatmass")),
    ("bmr", ("basal metabolic rate", "basalmetabolicrate", "basal metabolic",
             "bmr")),
    ("bmi", ("bmi",)),
    ("muscle_mass", ("skeletal muscle mass", "skeletalmusclemass",
                     "skeletal muscle", "smm", "muscle mass")),
    # ‏الدهون الحشوية بالعنوان الكامل بس، بدون اختصار.
    #
    # ‏VFA مساحة (سم²) وVFL مستوى (١-٢٠)، وكانوا الاتنين على نفس الخانة.
    # وأهم من كده: في تلات ورقات من الأربعة اللي جرّبتها المستوى مطبوع
    # فوق عمود رسم، والصف بيبقى كله أرقام مسطرة -- فسطر "VFL i = 2 ."
    # كان بيطلّع مستوى ٢ والصح ٦. والمستوى الغلط أخطر من مفيش: الشرح
    # بيقول للعميل "طبيعي" وهو مرتفع. العنوان الكامل ("Visceral Fat
    # Level 9" في ورق InBody) بيتقرا من صف نص عادي، وهو الآمن.
    ("visceral_fat", ("visceral fat level", "visceralfatlevel",
                      "visceral fat area", "visceral fat")),
    ("body_water", ("total body water", "totalbodywater", "tbw", "body water")),
    ("weight", ("weight", "wt")),
    ("height", ("height", "ht")),
    ("age", ("age",)),
    ("gender", ("gender", "sex")),
]

# ‏السطور دي أرقامها مش قراءة العميل: هدف، أو نطاق طبيعي، أو تحكّم في الوزن.
# "Target Weight 60.0 kg" لو اتقرت كوزن، الخطة تتحسب على وزن العميل المستهدف
# مش وزنه الحالي -- والفرق ١٨ كيلو في المثال اللي جرّبته.
# ‏السطور اللي أرقامها مش قراءة العميل. الدفعة التانية جاية من ورقة
# DR.NUTRITION الحقيقية بتاعة الدكتور، واللي كانت بتطلّع أرقام غلط:
#
#   "Biological Age 1324"   ->  العمر = ١٣٢٤   (والرقم ده أصله الـBMR)
#   "( Target Weight : 55.6 )" ->  الوزن = ٥٥.٦
#   "Body Cell Mass 78"     ->  رقم مالوش خانة
#
# ‏"Biological Age" فيها كلمة age كاملة، فحدود الكلمة مابتمنعهاش -- لازم
# تتشال بالاسم.
_NOT_A_READING = ("target", "ideal", "control", "range", "normal", "recommend",
                  "desirable", "standard", "goal", "loss", "gain", "obesity",
                  "degree", "score", "history", "graph", "date", "trend",
                  "biological", "cell mass", "expenditure", "impedance",
                  "matched", "reference", "estimated", "assessment",
                  "segmental", "circumference", "ratio", "body type",
                  "evaluation", "balance")

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


# ‏العنوان لازم يطابق ككلمة كاملة، مش كجزء من كلمة. ده مش تجميل:
#
#   "Right Leg 6.01"   كان بيتقرا **طول 6.01**   -- "ht" جوّه "right"
#   "Average 1324"     كان بيتقرا **عمر 1324**   -- "age" جوّه "average"
#
# ‏وورقة الـInBody الكاملة مليانة الصفوف دي (الأطراف، والمتوسطات)، فالقراية
# كانت بتطلّع أرقام من صفوف مالهاش علاقة، وحدود المعقول هي اللي بتشيلها --
# يعني الدكتور مابيتملّاش ولا خانة ومش عارف ليه. الأرقام دي مقيسة من
# ورقته هو، مش مفترضة.
_FORM_RX = {}


def _form_regex(form):
    rx = _FORM_RX.get(form)
    if rx is None:
        # ‏(?<![a-z]) و(?![a-z]) = حدود كلمة على الحروف بس، عشان "fat%"
        # و"fat %" يفضلوا يطابقوا.
        body = r"\s+".join(re.escape(word) for word in form.split())
        rx = re.compile(r"(?<![a-z])" + body + r"(?![a-z])")
        _FORM_RX[form] = rx
    return rx


def _label_form(text):
    """‏يرجّع (الخانة، شكل العنوان اللي طابق) أو (None, None)."""
    low = re.sub(r"[^a-z% ]", "", text.lower())
    if any(bad in low for bad in _NOT_A_READING):
        return None, None
    for field, forms in _LABELS:
        for form in forms:
            if _form_regex(form).search(low):
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
        # ‏الاستبعاد لازم يتقاس على **السطر** مش على الصندوق لوحده. في
        # المطابقة بالمكان كل صندوق كلمة واحدة، فصندوق "Age" وحده مافيهوش
        # كلمة "Biological" -- وورقة الدكتور طلّعت منها العمر = ١٣٢٤.
        height = max(1.0, bottom - top)
        row = " ".join(b[0] for b in boxes if abs(b[2] - cy) < height * 0.6)
        if _label_form(row)[0] is None and _label_of(text):
            continue
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

# ‏رقم بإشارة = فرق، مش قياس. ورق التحليل مليان خانات "اللي تحتاج تتغير":
#
#     Body Fat  ——  +7.0        (كتلة دهون تنزل ٧ كيلو)
#     Weight Control  -18.4
#     Obesity Degree  -3.4
#
# ‏و"+7.0" كانت بتتقرا كأنها كتلة الدهون نفسها. مافيش قياس جسم بيتكتب
# بإشارة، فأي رقم قبله + أو − بيتشال.
_SIGNED = re.compile(r"^[+\u2212\u2013-]\s*\d")

# ‏"Body Fat:24.3" -- الرقم بعد نقطتين في نفس الكلمة
_GLUED = re.compile(r"[:=]\s*(\d{1,4}(?:[.,]\d{1,2})?)\s*$")


def _value_word(word):
    clean = word.replace(",", ".")
    if _SIGNED.match(clean):
        return None
    match = _VALUE_WORD.match(clean)
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
    rx = _form_regex(form)
    for i in range(len(words)):
        acc = ""
        for j in range(i, len(words)):
            acc = (acc + " " + norm[j]).strip()
            # ‏نفس حدود الكلمة بتاعة _label_form، وإلا الرقم يتاخد من بعد
            # كلمة غلط: "Right Leg" كان بيعتبر "right" هو عنوان الطول.
            if rx.search(acc) or rx.search(acc.replace(" ", "")):
                return j + 1
    return 0


def _labels_in(words):
    """‏كل العناوين في السطر ومكانها: [(الخانة, أول كلمة, آخر كلمة+١)].

    ‏ليه أكتر من عنوان في السطر: ورق GAIA بيحط اتنين جنب بعض --
    "Height 162.0 cm Age 53 yrs" و"Weight 67.3 kg Gender Female". لما كنا
    بناخد أول عنوان بس، العمر والنوع كانوا بيضيعوا من كل ورقة من النوع ده.

    ‏المكان بيتحسب بخريطة حرف→كلمة، مش بتجميع من كل بداية: النسخة الأولى
    كانت بتقول إن "Age" بتبدأ من كلمة "162.0" لأنها جمّعت من عندها لحد ما
    لقتها -- فالطول كان بيضيع.
    """
    norm = [re.sub(r"[^a-z% ]", "", w.lower()) for w in words]
    text = ""
    owner = []
    for index, word in enumerate(norm):
        if index:
            text += " "
            owner.append(index)
        text += word
        owner.extend([index] * len(word))

    hits = []
    taken = set()
    seen = set()
    # ‏كلمات الاستبعاد ومكانها، عشان نشوف قربها من كل عنوان
    bad_at = [index for index, word in enumerate(norm)
              if any(bad in word for bad in _NOT_A_READING)]
    bad_at += [index for index, word in enumerate(norm[:-1])
               if any(bad in (word + " " + norm[index + 1]) for bad in _NOT_A_READING)]
    # ‏الأطول الأول: "percent body fat" تاخد كلماتها قبل ما "body fat"
    # تاخد نصها -- وإلا النسبة والكتلة يتلخبطوا في نفس السطر.
    order = sorted(((field, form) for field, forms in _LABELS for form in forms),
                   key=lambda pair: -len(pair[1]))
    for field, form in order:
        if field in seen:
            continue
        for match in _form_regex(form).finditer(text):
            first_char, last_char = match.start(), match.end() - 1
            if last_char >= len(owner):
                continue
            first, last = owner[first_char], owner[last_char]
            span = set(range(first, last + 1))
            if span & taken:
                continue
            # ‏كلمة الاستبعاد بتلغي العنوان لو **جنبه**، مش لو موجودة في
            # أي مكان في السطر. القراية بتلزق أعمدة في سطر واحد، فسطر
            # "B.M.R. 1316 kcal T.E.E. 2027 kcal Date Weight ..." كان
            # بيترفض كله بسبب كلمة "Date" على بعد ست كلمات -- والـBMR
            # الصح كان بيضيع. واللي المفروض يترفض قريب دايماً:
            # "Target Weight"، "Biological Age"، "Weight Control".
            if any(first - 2 <= at <= last + 2 for at in bad_at):
                continue
            taken |= span
            seen.add(field)
            hits.append((field, first, last + 1))
            break
    hits.sort(key=lambda hit: hit[1])
    return hits


def parse_lines(lines):
    """‏يطلّع الأرقام من سطور محرّك المتصفح.

    محرّك المتصفح بيرجّع الكلام مجمّع في سطور فعلية، فمافيش تخمين هندسي:
    العنوان والرقم في نفس السطر بالظبط. ده أضبط من حساب الميل اللي
    محرّك السيرفر محتاجه، عشان التجميع بيحصل جوّه المحرّك نفسه.

    الشكل: [[{"t": كلمة, "x": مكانها}, ...], ...] -- أو سطور كنص عادي.
    """
    return {field: values[0] for field, values in _scan(lines).items()}


def _scan(lines):
    """‏كل الاحتمالات لكل خانة، بترتيب ظهورها في الورقة.

    ‏ليه احتمالات مش رقم واحد: القراءة الواحدة بتشوف العنوان في أكتر من
    سطر (الصف الحقيقي، وسطر الشرح، وصف "المطلوب يتغيّر"). ولما كنا
    بناخد أول واحد ونسيب الباقي، قراءة شافت ضوضاء قبل الصف الحقيقي كانت
    بتلغي قراءة تانية شافته صح -- وورقة GAIA ضيّعت كتلة الدهون ٢٤.٣
    بسبب "Body Fat 1]" في سطر نص.
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
        # ‏الاستبعاد بقى جوّه _labels_in وعلى جوار كل عنوان لوحده، فمافيش
        # رفض للسطر كله هنا. الشرط القديم كان بيرفض السطر لو فيه كلمة
        # استبعاد في أي مكان -- وسطر "B.M.R. 1316 kcal ... Date Weight"
        # كان بيترفض كله بسبب "Date" على بعد ست كلمات.
        hits = _labels_in(words)
        if not hits:
            continue
        for index, (field, start, after) in enumerate(hits):
            # ‏الرقم لازم يبقى **قبل العنوان اللي بعده**. من غير الشرط ده،
            # "Height 162.0 cm Age 53" كان ينفع ياخد ٥٣ كطول.
            stop = hits[index + 1][1] if index + 1 < len(hits) else len(words)

            if field == "gender":
                low = " ".join(words[after:stop]).lower() or text.lower()
                if "female" in low:
                    found.setdefault("gender", []).append("female")
                elif "male" in low:
                    found.setdefault("gender", []).append("male")
                continue

            value = None
            # ‏الرقم لازم يبقى **قريب** من عنوانه. سطر الشرح في آخر ورقة
            # X-CONTACT ("M.B.F. : Mass of Body Fat ... A.M.B. 1 ...")
            # كان بيطلّع كتلة دهون = ١، والرقم بعيد عشر كلمات عن العنوان.
            # في الصفوف الحقيقية الرقم بيبقى كلمة أو اتنين بعد العنوان.
            stop = min(stop, after + 5)
            for word in words[after:stop]:
                value = _value_word(word)
                if value is not None:
                    break
            if value is None:
                # ‏الرقم ملزوق في نفس كلمة العنوان: "Body Fat:24.3" أو
                # "T.B.W.:31.0". الملخّص في آخر ورقة GAIA كله بالشكل ده،
                # وهو المكان الوحيد فيها اللي العنوان والرقم في سطر واحد.
                for word in words[start:after]:
                    match = _GLUED.search(word.replace(",", "."))
                    if match:
                        try:
                            value = float(match.group(1))
                        except ValueError:
                            value = None
                        if value is not None:
                            break
            if value is not None:
                found.setdefault(field, []).append(value)
    return found


def merge_found(founds):
    """‏يجمع قراءتين للصورة الواحدة: اللي اتفقوا عليه يتاخد، واللي اختلفوا فيه يتشال.

    ‏المتصفح بيقرا الصورة مرتين -- مرة كما هي ومرة بعد تحديد الحدود --
    عشان كل معالجة بتنجح في حاجة التانية بتفشل فيها (التحديد رفع القراءة
    في الصورة المهزوزة من ٥ خانات لـ٩).

    ‏الاتفاق بيتحسب على **كل** احتمالات كل قراءة، مش على أول واحد فيها.
    القراءة بتشوف العنوان في أكتر من سطر (الصف الحقيقي، سطر الشرح، صف
    "المطلوب يتغيّر")، فلو واحدة شافت ضوضاء قبل الصف الحقيقي كانت بتلغي
    الرقم الصح اللي التانية شافته.
    """
    lists = []
    for found in founds:
        if not found:
            continue
        lists.append({key: (values if isinstance(values, list) else [values])
                      for key, values in found.items()})
    if not lists:
        return {}

    def _same(one, two):
        if isinstance(one, (int, float)) and isinstance(two, (int, float)):
            return abs(float(one) - float(two)) <= 0.05
        return one == two

    def _decimal_slip(one, two):
        """‏نفس الرقم وفرقه عشرة أو مية ضعف = نقطة عشرية ضايعة."""
        if not (isinstance(one, (int, float)) and isinstance(two, (int, float))):
            return False
        small, big = sorted((abs(float(one)), abs(float(two))))
        if small <= 0:
            return False
        return any(abs(big - small * factor) < 0.01 for factor in (10.0, 100.0))

    # ‏الحدود جوّه الدالة عشان مافيش استيراد متبادل بين الملفين.
    from lab_report import SANE_RANGES

    def _sane(key, value):
        low, high = SANE_RANGES.get(key, (None, None))
        if low is None or not isinstance(value, (int, float)):
            return True
        return low <= float(value) <= high

    merged = {}
    for key in set().union(*[set(one) for one in lists]):
        seen = [one.get(key) or [] for one in lists]
        if any(not values for values in seen):
            # ‏قراءة واحدة بس شافته. مافيش اتفاق يتقاس، فبناخده -- وحدود
            # المعقول والفحوص اللي بعدها هي اللي بتحكم.
            merged[key] = next(values[0] for values in seen if values)
            continue
        agreed = [value for value in seen[0]
                  if all(any(_same(value, other) for other in values)
                         for values in seen[1:])]
        if agreed:
            merged[key] = agreed[0]
            continue
        # ‏مافيش اتفاق. استثناء واحد ضيّق: نقطة عشرية ضايعة (١٦٤.٠ و١٦٤٠)،
        # وواحد منهم بس في حدود المعقول.
        first, second = seen[0][0], seen[1][0]
        if _decimal_slip(first, second):
            if _sane(key, first) and not _sane(key, second):
                merged[key] = first
            elif _sane(key, second) and not _sane(key, first):
                merged[key] = second
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
    # ‏السطور بتتوصّل بفاصل عشان interpret يرجّعها للدكتور سطور تاني.
    text_all = " | ".join(line for line in flat if line.strip())
    if not text_all.strip():
        raise RuntimeError("مقدرتش أقرا أي كلام في الصورة. صوّرها في نور أحسن "
                           "وخلي الورقة كلها في الكادر.")
    return interpret(merge_found([_scan(one) for one in passes]), text_all)


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


# ‏موبايل مصري على الورقة: ١١ رقم بيبدأوا ٠١ وبعدها ٠ أو ١ أو ٢ أو ٥
# (فودافون، اتصالات، أورنج، وي).
#
# ‏والورقة بتطبعه بأي تجميع: 01004294521 أو 0100 429 4521 أو
# 010 0429 4521 أو بشرطات. فالنمط بيسمح بفاصل أو اتنين **قبل أي رقم**،
# مش بين مجموعات بأطوال ثابتة -- أول نسخة كانت بتتوقّع ٤ و٤ وضيّعت
# «0100 429 4521» وهو أشهر شكل بيتكتب بيه.
#
# ‏بس التلات أرقام الأولى لازم يبقوا ملزوقين: ده اللي بيمنع سطر فيه
# أرقام متفرّقة («0 1 2 3 4 5...») إنه يتلزق ويبقى موبايل.
#
# ‏و(?<!\d) و(?!\d) بيخلّوه ١١ رقم بالظبط، فكود جهاز فيه ١٤ رقم
# مابيتقطّعش منه موبايل.
_PHONE = re.compile(r"(?<!\d)01[0125](?:[\s\-\.]{0,2}\d){8}(?!\d)")


def _phone_in(text):
    """‏أول موبايل مصري في كلام الورقة، أو None.

    ‏ده اللي بيوصل الورقة بملف المتابعة: الدكتور بيصوّر الورقة، والصفحة
    بتدوّر بالرقم ده في العملاء -- فلو العميل جه قبل كده، الشرح يبقى
    مقارنة بآخر زيارة من غير ما الدكتور يكتب حرف.

    ‏وبيرجّع **واحد بس ولما يبقى واضح**: رقم غلط معناه إننا نفتح ملف عميل
    تاني ونقول للي قاعد قدامه أرقام حد غيره. فلو الورقة فيها أكتر من
    موبايل، مابنختارش -- بنرجّع None والدكتور يكتب.
    """
    hits = {re.sub(r"\D", "", m.group(0)) for m in _PHONE.finditer(text or "")}
    hits = {h for h in hits if len(h) == 11}
    if len(hits) != 1:
        return None
    return hits.pop()


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

    # ‏نسبة الدهون من كتلتها: ورقة GAIA بتطبع النسبة فوق عمود رسم (والقراية
    # بتقراها "PBE." مش "PBF."، والرقم مش في سطرها)، بس بتطبع كتلة الدهون
    # بالكيلو في الملخّص. والقسمة على الوزن بتطلّع نفس الرقم المطبوع بالظبط:
    # ٢٤.٣ ÷ ٦٧.٣ = ٣٦.١٪. ده حساب مش تخمين، وبيتعمل بس لما النسبة نفسها
    # مش مقروءة.
    if ("fat_pct" not in found and found.get("fat_mass")
            and found.get("weight")):
        fat_mass, weight = found["fat_mass"], found["weight"]
        if 0 < fat_mass < weight:
            percent = fat_mass / weight * 100.0
            # ‏نفس حدود lab_report.SANE_RANGES["fat_pct"]. لو اتفرقوا،
            # النسبة المحسوبة بتعدّي حاجز واحد وتتشال عند التاني.
            if 3.0 <= percent <= 75.0:
                found["fat_pct"] = round(percent, 1)

    # ‏فحص تناسق الـBMI مع الوزن والطول اتنقل لـlab_report._clean، بعد ما
    # حدود المعقول تشيل الأرقام المستحيلة. الترتيب كان مقلوب: ورقة GAIA
    # طلّعت BMI = ١٤٥٠ (رقم من مسطرة الرسم)، فالفحص قارنه بالمحسوب
    # (٢٥.٦)، مالقاهمش متطابقين، وشال **الطول والوزن الصح** معاه.

    out = dict(found)
    # ‏السطور اللي المحرّك شافها. لما مافيش خانة اتملت، دي الحاجة الوحيدة
    # اللي بتقول ليه: الورقة مش واضحة، ولا عناوينها بشكل تاني؟
    out["seen"] = [line for line in (text_all or "").split(" | ") if line.strip()]
    out["is_body_report"] = True
    out["name"] = None          # ‏الاسم على الورقة مش دايماً، وتخمينه غلط
    out["phone"] = _phone_in(text_all)
    out["extras"] = []
    out["unreadable"] = [label for label, _ in _LABELS
                         if label not in found
                         and label in ("weight", "height", "fat_pct", "bmi")]
    return out

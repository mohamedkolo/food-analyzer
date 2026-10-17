# -*- coding: utf-8 -*-
"""قراءة ورقة تحليل الجسم من صورة.

الدكتور بيدخّل نفس الأرقام اللي مطبوعة قدامه على ورقة الـInBody: الوزن،
الطول، نسبة الدهون، الـBMI، الـBMR. الملف ده بياخد صورة الورقة ويرجّع
الأرقام دي جاهزة للفورم، والدكتور يشوفها ويعدّل اللي عايزه.

**القاعدة اللي الملف كله مبني عليها: مايخمّنش ولا رقم.** أي خانة مش مقروءة
بترجع null والفورم بيسيبها فاضية للدكتور يكتبها. رقم مخمّن في ورقة تغذية
أسوأ من خانة فاضية: الخانة الفاضية بتبان، والرقم الغلط بيمشي في الخطة
لحد ما يطلع في إيد العميل.

**طريقين للقراءة، والفرق بينهم مقيس:**

  من غير مفتاح API (الافتراضي):  ocr_report -- القراءة على السيرفر نفسه،
                                  مجاناً، والصورة مابتخرجش منه. بتقرا ورقة
                                  الـInBody الإنجليزية صح (اختبرت ميل وتشويش
                                  وضغط ونصف دقة: صفر رقم غلط)، ومابتعرفش
                                  العناوين العربية.
  بمفتاح API:                     Claude -- بيقرا العربي والورق المايل
                                  والمكتوب بخط اليد، وبيفهم أي شكل ورقة.

الاتنين بيرجّعوا نفس الشكل وبيمرّوا على نفس التنضيف وحدود المعقول.
"""

import base64
import json
import os
import re

MODEL = "claude-opus-5"

# ‏حد حجم الصورة. الـAPI حدّه ٥ ميجا للصورة بعد الترميز، والكاميرا بتطلّع
# صور أكبر من كده، فبنرفض بدري برسالة مفهومة بدل ما الـAPI يرفض برسالة
# إنجليزية عن base64.
MAX_IMAGE_BYTES = 4 * 1024 * 1024

# ‏الـPDF مسموحله أكبر: ورقة تحليل متصوّرة سكانر بتطلع ٢-٣ ميجا لوحدها،
# وحد الطلب عند الـAPI ٣٢ ميجا. بس مش سايبينه مفتوح -- ملف ٣٠ ميجا على
# نت موبايل بيقعد دقايق وبعدين يفشل، والدكتور مايعرفش ليه.
MAX_PDF_BYTES = 8 * 1024 * 1024

PDF_TYPE = "application/pdf"

ALLOWED_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
    "image/gif": "image/gif",
    # ‏الدكتور بيوصله تحاليل PDF من المعمل على الواتس، فكان بيطبعها
    # ويصوّرها عشان البرنامج يقراها. الـAPI بيقرا الـPDF نفسه، وأحسن
    # من صورة لصفحة مطبوعة -- لأن الـPDF اللي جاي من المعمل نصّه
    # مكتوب جوّاه أصلاً، مش محتاج يتخمّن من بكسلات.
    PDF_TYPE: PDF_TYPE,
    "application/x-pdf": PDF_TYPE,
}

# ‏الحدود دي مش تجميل: موديل بيقرا صورة مشوشة ممكن يطلّع "الوزن ٧٥٠ كجم".
# الرقم اللي برّه الحدود بيتشال ويتحوّل لتحذير، فالدكتور يكتبه بإيده.
SANE_RANGES = {
    "weight": (20.0, 400.0),
    "height": (80.0, 250.0),
    "age": (1, 120),
    # ‏الحد الأدنى ٣٪ مش ٢٪: الدهون الأساسية (حوالين الأعضاء والأعصاب)
    # لوحدها ٣٪ للذكر و٨٪ للأنثى، وأقل بطل كمال أجسام في ذروته بيوصل ٤٪.
    # ورقة عيادة فيها ٢٪ قراءة غلط، مش حالة نادرة.
    "fat_pct": (3.0, 75.0),
    "bmi": (8.0, 90.0),
    "bmr": (600, 4500),
    "muscle_mass": (10.0, 120.0),
    "visceral_fat": (1.0, 60.0),
    "body_water": (10.0, 90.0),
    "fat_mass": (1.0, 200.0),
}

_SCHEMA = {
    "type": "object",
    "properties": {
        "is_body_report": {
            "type": "boolean",
            "description": "true only if this image is a body composition / body "
                           "analysis report (InBody, Tanita, bioimpedance, or a "
                           "clinic's body measurement sheet).",
        },
        "name": {"type": ["string", "null"], "description": "Client name if printed."},
        "gender": {"type": ["string", "null"], "enum": ["male", "female", None]},
        "age": {"type": ["integer", "null"]},
        "height": {"type": ["number", "null"], "description": "Height in cm."},
        "weight": {"type": ["number", "null"], "description": "Weight in kg."},
        "fat_pct": {"type": ["number", "null"],
                    "description": "Body fat percentage (PBF)."},
        "bmi": {"type": ["number", "null"]},
        "bmr": {"type": ["number", "null"],
                "description": "Basal metabolic rate in kcal, as printed. Do not "
                               "compute it, do not convert a TDEE into a BMR."},
        "muscle_mass": {"type": ["number", "null"],
                        "description": "Skeletal muscle mass in kg."},
        "visceral_fat": {"type": ["number", "null"],
                         "description": "Visceral fat level or area, as printed."},
        "body_water": {"type": ["number", "null"],
                       "description": "Total body water in litres or kg."},
        "extras": {
            "type": "array",
            "description": "Any other printed reading worth keeping, at most 8.",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["label", "value"],
                "additionalProperties": False,
            },
        },
        "unreadable": {
            "type": "array",
            "description": "Fields that appear on the sheet but could not be read "
                           "with confidence (blurred, cut off, glare).",
            "items": {"type": "string"},
        },
    },
    "required": ["is_body_report", "name", "gender", "age", "height", "weight",
                 "fat_pct", "bmi", "bmr", "muscle_mass", "visceral_fat",
                 "body_water", "extras", "unreadable"],
    "additionalProperties": False,
}

_PROMPT = """You are reading a photo of a body composition report for a
clinical dietitian, so the numbers go straight into a patient's plan.

Read only what is actually printed on the sheet. The single most important
rule: **never guess a value.** If a number is blurred, cut off, hidden by
glare, or you are not certain you read it correctly, return null for that
field and name it in "unreadable". A missing field is safe -- the dietitian
sees the blank and types it. A wrong number is not: it flows into the
calorie target and reaches the patient.

Specifically:
- Do not compute or derive anything. If BMI is not printed, return null even
  though you could calculate it from height and weight.
- Do not convert units. Return kg for weight, cm for height, kcal for BMR.
  If the sheet uses pounds or inches, convert to kg/cm -- that is a unit
  change, not a guess.
- A range or a target band (for example "normal range 18.5-24.9") is not a
  reading. Return the patient's own measured value only.
- Arabic and English sheets are both common. Names may be Arabic; return the
  name exactly as printed.
- If the image is not a body composition report at all, set is_body_report
  to false and leave every field null."""


class ReportError(Exception):
    """‏غلطة المفروض الدكتور يقراها ويعرف يعمل إيه."""


def api_key():
    return (os.environ.get("ANTHROPIC_API_KEY") or "").strip()


def _clean_number(value, key):
    if value is None:
        return None, None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, key
    low, high = SANE_RANGES.get(key, (None, None))
    if low is not None and not (low <= number <= high):
        return None, key
    if key in ("age", "bmr"):
        return int(round(number)), None
    return round(number, 1), None


_PHONE_OK = re.compile(r"^01[0125]\d{8}$")


def _clean_phone(value):
    """‏موبايل مصري ١١ رقم، وإلا None."""
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if _PHONE_OK.match(digits) else None


def _clean(raw):
    """‏يشيل أي رقم برّه المعقول ويحوّله لتحذير."""
    out = {"is_body_report": bool(raw.get("is_body_report")),
           "name": (raw.get("name") or "").strip() or None,
           # ‏موبايل مطبوع على الورقة. الصفحة بتدوّر بيه في المتابعين،
           # فلازم يبقى ١١ رقم نضيفين -- أي حاجة غير كده بترجع None،
           # لأن رقم نصه غلط بيفتح ملف عميل تاني.
           "phone": _clean_phone(raw.get("phone")),
           "gender": raw.get("gender") if raw.get("gender") in ("male", "female") else None,
           "extras": [], "dropped": [],
           "unreadable": [str(x) for x in (raw.get("unreadable") or [])][:12],
           # ‏السطور اللي المحرّك قراها، زي ما هي. الدكتور يشوفها لما
           # القراية ماتملّيش حاجة -- وإلا مافيش حاجة تدل على السبب.
           "seen": [str(x)[:120] for x in (raw.get("seen") or [])][:25],
           # ‏الخانات اللي المعادلة أكّدتها بدل سطرها (الـBMI من الوزن
           # والطول مثلاً). بتبان للدكتور عشان يعرف الرقم جاي منين.
           "confirmed": {str(k): str(v) for k, v
                         in (raw.get("confirmed") or {}).items()}}
    for key in ("age", "height", "weight", "fat_pct", "bmi", "bmr",
                "muscle_mass", "visceral_fat", "body_water", "fat_mass"):
        value, dropped = _clean_number(raw.get(key), key)
        out[key] = value
        if dropped:
            # ‏الرقم اللي اتقرا بيرجع مع الخانة. قبل كده كان بيرجع اسم
            # الخانة بس، فالدكتور كان يشوف "height, muscle_mass" ومايعرفش
            # القراية شافت إيه -- ولا هو ولا أنا نعرف نصلّح إيه.
            out["dropped"].append({"field": dropped,
                                   "value": raw.get(key),
                                   "low": SANE_RANGES.get(dropped, (None, None))[0],
                                   "high": SANE_RANGES.get(dropped, (None, None))[1]})
    # ‏الرقم اللي معادلة ناقضته: بيتسجّل في dropped **بقيمته** والخانة
    # تتفضّى. لازم يجي **بعد** حلقة الأرقام فوق، وإلا الحلقة بترجّع
    # تحط الرقم اللي لسه شِلناه (جرّبتها بالترتيب الغلط: BMR ٢٠٣٨ رجع).
    #
    # ‏والدكتور لازم يشوف الرقم نفسه: "BMR اتشال" مايقولش حاجة، و
    # "BMR = ٢٠٣٨ اتشال لأن الجسم ده بيحرق ١٣٢٥" بتقول كل حاجة.
    _was = raw.get("contradicted_values") or {}
    for _field, _reason in {str(k): str(v) for k, v
                            in (raw.get("contradicted") or {}).items()}.items():
        # ‏القيمة المرفوضة جاية من contradicted_values: المحرّك بيشيلها
        # من found قبل أي حساب، فهي مش في out خلاص. ولو الحساب بعد
        # الرفض ملا الخانة تاني (النسبة من الكتلة والوزن)، الخانة
        # بتفضل مليانة بالرقم الصح والمرفوض بيتعرض جنبه.
        _value = _was.get(_field, out.get(_field))
        out["dropped"].append({"field": _field, "value": _value,
                               "low": None, "high": None, "why": _reason})
        if _field not in _was and out.get(_field) is not None:
            out[_field] = None

    # ‏فحص تناسق: الـBMI = الوزن ÷ (الطول بالمتر)². التلاتة مطبوعين على
    # الورقة، فلو الحساب مااتطابقش يبقى واحد منهم اتقرا غلط ومانعرفش مين --
    # فبنشيل التلاتة والدكتور يكتبهم. الفحص ده بيمسك النوع اللي حدود
    # المعقول مابتمسكهوش: رقم معقول في الخانة الغلط.
    #
    # ‏وبيجي **بعد** حدود المعقول بالقصد. لما كان قبلها، BMI = ١٤٥٠ (رقم
    # من مسطرة رسم) كان بيشيل الطول والوزن الصح معاه.
    weight, height, bmi = out.get("weight"), out.get("height"), out.get("bmi")
    if weight and height and bmi and height > 0:
        computed = weight / ((height / 100.0) ** 2)
        if abs(computed - bmi) > 1.5:
            for key in ("weight", "height", "bmi"):
                if out.get(key) is not None:
                    out["dropped"].append({"field": key, "value": out[key],
                                           "low": None, "high": None})
                out[key] = None

    # ‏فحص تناسق تاني: الوزن ونسبة الدهون والطول لازم يوصفوا جسم ممكن
    # يكون موجود. المقياس هو FFMI -- الكتلة الخالية من الدهون على مربع
    # الطول، زي الـBMI بالظبط بس على الكتلة الخالية بدل الوزن:
    #
    #     الكتلة الخالية = الوزن × (١ - نسبة الدهون ÷ ١٠٠)
    #     FFMI = الكتلة الخالية ÷ (الطول بالمتر)²
    #
    # ‏الرقم ده عند البشر بين ١٦ و٢٢ للعادي، و٢٥ لأعلى رياضي طبيعي،
    # و~٣٠ بالمنشّطات. والحدود هنا (٨ إلى ٣٢) واسعة بالقصد: بتسيب أضخم
    # رياضي وأنحف حالة يعدّوا، وبتمسك المستحيل بس.
    #
    # ‏ده اللي مسك ورقة طلعت «وزن ١١٠.٩ كجم ونسبة دهون ٢٪»: يعني ١٠٨.٧
    # كجم كتلة خالية من الدهون على طول ١٦٢ = FFMI ٤١، وده مش موجود في
    # البشر. وكل رقم لوحده كان جوّه حدود المعقول، فمافيش حاجة تمسكه غير
    # إن التلاتة يتحسبوا مع بعض.
    #
    # ‏وبنشيل نسبة الدهون هي بالتحديد (مش الوزن ولا الطول): الوزن والطول
    # ليهم شاهد تاني -- فحص الـBMI فوق -- ونسبة الدهون مالهاش.
    weight, height, fat_pct = out.get("weight"), out.get("height"), out.get("fat_pct")
    if weight and height and fat_pct and height > 0:
        lean = weight * (1.0 - fat_pct / 100.0)
        ffmi = lean / ((height / 100.0) ** 2)
        if not (8.0 <= ffmi <= 32.0):
            for key in ("fat_pct", "fat_mass"):
                if out.get(key) is not None:
                    out["dropped"].append({"field": key, "value": out[key],
                                           "low": None, "high": None})
                out[key] = None

    for item in (raw.get("extras") or [])[:8]:
        label = str(item.get("label", "")).strip()[:40]
        value = str(item.get("value", "")).strip()[:40]
        if label and value:
            out["extras"].append({"label": label, "value": value})
    return out


# ‏حدود على اللي جاي من المتصفح. مش عشان الدكتور -- عشان الطلب نفسه
# مفتوح، وأي حد داخل بحساب موظف يقدر يبعت أي حجم. الأرقام دي أوسع بكتير
# من أي ورقة تحليل حقيقية (ورقة InBody فيها ~٦٠ سطر).
MAX_PASSES = 3
MAX_LINES = 400
MAX_WORDS = 40
MAX_WORD = 40


def _tidy_passes(passes):
    """‏يقصّ اللي جاي من المتصفح على حدود معروفة قبل أي تفسير."""
    if not isinstance(passes, list):
        raise ReportError("القراءة رجعت شكل مش متوقع -- جرّب تاني")
    out = []
    for one in passes[:MAX_PASSES]:
        if not isinstance(one, list):
            continue
        lines = []
        for line in one[:MAX_LINES]:
            words = []
            if isinstance(line, str):
                words = [w[:MAX_WORD] for w in line.split()[:MAX_WORDS]]
            elif isinstance(line, list):
                for word in line[:MAX_WORDS]:
                    if isinstance(word, str):
                        text = word
                    elif isinstance(word, dict):
                        text = str(word.get("t", ""))
                    else:
                        continue
                    text = text.strip()[:MAX_WORD]
                    if text:
                        words.append(text)
            if words:
                lines.append(words)
        if lines:
            out.append(lines)
    if not out:
        raise ReportError("مقدرتش أقرا أي كلام في الصورة. صوّرها في نور أحسن "
                          "وخلي الورقة كلها في الكادر.")
    return out


def read_browser(passes):
    """‏سطور جاية من محرّك المتصفح -> نفس شكل ديكشنري read_report.

    الصورة عمرها ما وصلت للسيرفر. اللي وصل هو الكلام، والتفسير والحواجز
    اللي بتمنع الرقم الغلط بتشتغل هنا -- نفس الكود ونفس الاختبارات بتاعة
    القراءة على السيرفر.
    """
    import ocr_report
    try:
        local = ocr_report.read_passes(_tidy_passes(passes))
    except RuntimeError as e:
        raise ReportError(str(e))
    data = _clean(local)
    data["engine"] = "browser"
    return data


def read_report(image_bytes, content_type):
    """‏يرجّع ديكشنري بالأرقام المقروءة. بيرفع ReportError برسالة عربية.

    بياخد صورة أو PDF. الـPDF بيتبعت للـAPI زي ما هو (بلوك document)،
    مش بيتحوّل لصورة -- تحليل المعمل اللي جاي PDF نصّه مكتوب جوّاه،
    فتحويله لصورة بيرمي النص ويخلّي القراءة تخمين من بكسلات.
    """
    if not image_bytes:
        raise ReportError("مافيش ملف")
    media_type = ALLOWED_TYPES.get((content_type or "").split(";")[0].strip().lower())
    if not media_type:
        raise ReportError("نوع الملف مش مدعوم (صورة JPG أو PNG أو WEBP، أو ملف PDF)")
    is_pdf = media_type == PDF_TYPE
    cap = MAX_PDF_BYTES if is_pdf else MAX_IMAGE_BYTES
    if len(image_bytes) > cap:
        raise ReportError(
            ("الملف كبير (%.1f ميجا). الحد %d ميجا." if is_pdf else
             "الصورة كبيرة (%.1f ميجا). الحد %d ميجا -- صوّرها بدقة أقل.")
            % (len(image_bytes) / 1048576.0, cap // 1048576))
    key = api_key()
    if is_pdf and not key:
        # ‏محرّك القراءة المحلي (rapidocr) بياخد بكسلات، مش PDF. تحويل
        # الـPDF لصورة محتاج مكتبة تانية -- فبدل ما نضيفها عشان حالة
        # نادرة، بنقول الحقيقة: صوّر الورقة، الصورة بتتقرا في المتصفح.
        raise ReportError("قراءة الـPDF محتاجة مفتاح API على السيرفر. "
                          "من غيره صوّر الورقة بالكاميرا -- الصورة بتتقرا "
                          "في المتصفح نفسه.")
    if not key:
        # ‏من غير مفتاح: القراءة بتحصل على السيرفر نفسه، مجاناً، والصورة
        # مابتخرجش منه. الميزة كانت مقفولة تماماً لحد ما الدكتور يعمل حساب
        # ويحط مفتاح -- وده شرط مالوش لازمة لورقة InBody إنجليزية.
        import ocr_report
        if not ocr_report.available():
            raise ReportError("مكتبة القراءة مش متركّبة على السيرفر -- "
                              "شغّل النشر تاني (rapidocr في requirements.txt)")
        try:
            local = ocr_report.read(image_bytes)
        except RuntimeError as e:
            raise ReportError(str(e))
        data = _clean(local)
        data["engine"] = "local"
        return data

    try:
        import anthropic
    except ImportError:
        # ‏المكتبة في requirements.txt، فلو ناقصة يبقى النشر مخلّصش تركيبها.
        # الرسالة دي بتقول كده بدل ما تطلع 500 فاضية.
        raise ReportError("مكتبة القراءة مش متركّبة على السيرفر -- "
                          "شغّل النشر تاني (anthropic في requirements.txt)")

    client = anthropic.Anthropic(api_key=key)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    # ‏PDF بيتبعت بلوك document، الصورة بلوك image. والاتنين
                    # قبل النص: الموديل بيقرا أحسن لما المستند يسبق السؤال.
                    {"type": ("document" if is_pdf else "image"),
                     "source": {"type": "base64", "media_type": media_type,
                                "data": base64.standard_b64encode(image_bytes).decode()}},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        )
    except anthropic.AuthenticationError:
        raise ReportError("مفتاح الـAPI مرفوض -- اتأكد من ANTHROPIC_API_KEY")
    except anthropic.RateLimitError:
        raise ReportError("الخدمة مشغولة دلوقتي، جرّب تاني بعد شوية")
    except anthropic.APIConnectionError:
        raise ReportError("السيرفر مش قادر يوصل للخدمة -- جرّب تاني")
    except anthropic.APIStatusError as e:
        raise ReportError("الخدمة ردّت بغلطة (%s)" % getattr(e, "status_code", "?"))

    if getattr(response, "stop_reason", None) == "refusal":
        raise ReportError("الخدمة رفضت تقرا الملف ده")

    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        raw = json.loads(text)
    except ValueError:
        raise ReportError("الرد مش مفهوم -- جرّب نسخة أوضح")
    if not isinstance(raw, dict):
        raise ReportError("الرد مش مفهوم -- جرّب نسخة أوضح")

    data = _clean(raw)
    data["engine"] = "api"
    # ‏الرسايل دي بقت توصل على PDF كمان، مش صورة بس -- فـ"صوّرها تاني"
    # نصيحة مالهاش معنى لملف جاي من المعمل.
    _it = "الملف ده" if is_pdf else "الصورة دي"
    _retry = ("جرّب نسخة أوضح من المعمل." if is_pdf else
              "صوّرها في نور أحسن وخلي الورقة كلها في الكادر.")
    if not data["is_body_report"]:
        raise ReportError("%s مش ورقة تحليل جسم. ابعت ورقة الـInBody "
                          "أو جهاز قياس نسبة الدهون." % _it)
    if not any(data.get(k) is not None for k in
               ("weight", "height", "fat_pct", "bmi", "bmr", "age")):
        raise ReportError("مقدرتش أقرا أي رقم. %s" % _retry)
    return data

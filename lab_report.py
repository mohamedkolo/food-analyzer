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

ALLOWED_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
    "image/gif": "image/gif",
}

# ‏الحدود دي مش تجميل: موديل بيقرا صورة مشوشة ممكن يطلّع "الوزن ٧٥٠ كجم".
# الرقم اللي برّه الحدود بيتشال ويتحوّل لتحذير، فالدكتور يكتبه بإيده.
SANE_RANGES = {
    "weight": (20.0, 400.0),
    "height": (80.0, 250.0),
    "age": (1, 120),
    "fat_pct": (2.0, 75.0),
    "bmi": (8.0, 90.0),
    "bmr": (600, 4500),
    "muscle_mass": (10.0, 120.0),
    "visceral_fat": (1.0, 60.0),
    "body_water": (10.0, 90.0),
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


def _clean(raw):
    """‏يشيل أي رقم برّه المعقول ويحوّله لتحذير."""
    out = {"is_body_report": bool(raw.get("is_body_report")),
           "name": (raw.get("name") or "").strip() or None,
           "gender": raw.get("gender") if raw.get("gender") in ("male", "female") else None,
           "extras": [], "dropped": [],
           "unreadable": [str(x) for x in (raw.get("unreadable") or [])][:12]}
    for key in ("age", "height", "weight", "fat_pct", "bmi", "bmr",
                "muscle_mass", "visceral_fat", "body_water"):
        value, dropped = _clean_number(raw.get(key), key)
        out[key] = value
        if dropped:
            out["dropped"].append(dropped)
    for item in (raw.get("extras") or [])[:8]:
        label = str(item.get("label", "")).strip()[:40]
        value = str(item.get("value", "")).strip()[:40]
        if label and value:
            out["extras"].append({"label": label, "value": value})
    return out


def read_report(image_bytes, content_type):
    """‏يرجّع ديكشنري بالأرقام المقروءة. بيرفع ReportError برسالة عربية."""
    if not image_bytes:
        raise ReportError("مافيش صورة")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ReportError("الصورة كبيرة (%.1f ميجا). الحد %d ميجا -- صوّرها بدقة أقل."
                          % (len(image_bytes) / 1048576.0,
                             MAX_IMAGE_BYTES // 1048576))
    media_type = ALLOWED_TYPES.get((content_type or "").split(";")[0].strip().lower())
    if not media_type:
        raise ReportError("نوع الملف مش صورة مدعومة (JPG أو PNG أو WEBP)")
    key = api_key()
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
                    {"type": "image",
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
        raise ReportError("الخدمة رفضت تقرا الصورة دي")

    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        raw = json.loads(text)
    except ValueError:
        raise ReportError("الرد مش مفهوم -- جرّب صورة أوضح")
    if not isinstance(raw, dict):
        raise ReportError("الرد مش مفهوم -- جرّب صورة أوضح")

    data = _clean(raw)
    data["engine"] = "api"
    if not data["is_body_report"]:
        raise ReportError("الصورة دي مش ورقة تحليل جسم. صوّر ورقة الـInBody "
                          "أو جهاز قياس نسبة الدهون.")
    if not any(data.get(k) is not None for k in
               ("weight", "height", "fat_pct", "bmi", "bmr", "age")):
        raise ReportError("مقدرتش أقرا أي رقم من الصورة. صوّرها في نور أحسن "
                          "وخلي الورقة كلها في الكادر.")
    return data

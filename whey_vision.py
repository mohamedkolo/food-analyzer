# -*- coding: utf-8 -*-
"""‏قراية ضهر علبة الواي بالذكاء الاصطناعي -- لو فيه مفتاح على السيرفر.

‏ليه: صاحب المشروع صوّر ٣ علب في المحل. Tesseract في المتصفح قرا العلبة
الأولى (جدول أبيض على أسود، علبة مقوّسة ولامعة) ٩ أرقام من ٢٠ وأغلبهم
غلط، وعلبة Dymatize ولا حمض. الصور الحقيقية دي محتاجة موديل بيشوف.
‏نفس المفتاح اللي بيقرا ورق التحليل (lab_report)؛ من غيره الصفحة بترجع
للقراية في الموبايل زي ما هي.

‏والمطلوب منه أرقام بس، وكل رقم بيعدّي على نفس حواجز whey_analyzer
(normalize): نطاق منطقي، ووحدة. موديل بيغلط صفر زيادة زي أي OCR.
"""

import base64
import json
import os
import urllib.request

import whey_analyzer as W

_FIELDS = {"type": ["number", "null"]}
_SCHEMA = {
    "type": "object",
    "properties": {
        "serving_g": _FIELDS, "protein_g": _FIELDS,
        "unit": {"type": "string", "enum": ["per100", "serving", "unknown"]},
        "amino": {"type": "object",
                  "properties": {k: _FIELDS for k in W.AMINO},
                  "required": list(W.AMINO), "additionalProperties": False},
        "summary": {"type": "object",
                    "properties": {k: _FIELDS for k in ("total_aa_g", "eaa_g", "bcaa_g", "leucine_g")},
                    "required": ["total_aa_g", "eaa_g", "bcaa_g", "leucine_g"],
                    "additionalProperties": False},
        "added": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["serving_g", "protein_g", "unit", "amino", "summary", "added"],
    "additionalProperties": False,
}

_PROMPT = """This is a photo of the back of a whey protein tub. Read ONLY what is printed; never estimate.

- serving_g: serving size in grams (e.g. "1 Scoop (31g)" -> 31).
- protein_g: protein per serving in grams.
- amino: the amino acid profile, in MILLIGRAMS, exactly as printed. Convert grams to mg (2.6 g -> 2600).
  Glutamic acid goes under Glutamine, Aspartic acid under Aspartic, Cysteine under Cystine.
  null for any amino acid that is not printed or that you cannot read with certainty.
- unit: "per100" if the profile says per 100 g of protein, "serving" if per serving, else "unknown".
- summary: only if the label prints totals instead of (or besides) a full table, in grams per serving:
  total amino acids, EAAs, BCAAs, leucine. null otherwise.
- added: free amino acids listed in the INGREDIENTS (e.g. "Amino Acid Blend (L-Glycine, L-Glutamine,
  L-Taurine)" -> ["Amino acid blend", "Glycine", "Glutamine", "Taurine"]). Empty if none.
Read each row's number from the same row as its name; tables are often curved or glossy."""


def _gemini_key():
    return (os.environ.get("GEMINI_API_KEY") or "").strip()


def available():
    from lab_report import api_key
    return bool(_gemini_key() or api_key())


def normalize(raw):
    """‏رد الموديل -> نفس شكل whey_analyzer.parse_label، بعد نفس الحواجز."""
    raw = raw or {}
    amino_in = {k: v for k, v in (raw.get("amino") or {}).items() if k in W.AMINO and v}
    amino_in = {k: round(float(v)) for k, v in amino_in.items()}
    serving = raw.get("serving_g") or None
    unit = raw.get("unit")
    if unit not in ("per100", "serving"):
        unit = W._unit("", serving, amino_in)
    amino = W._in_range(amino_in, unit, raw.get("protein_g") or None)
    summary = raw.get("summary") or {}
    summary = summary if summary.get("total_aa_g") else None
    added = []
    for item in raw.get("added") or []:
        low = str(item).lower()
        for label, rx in W._ADDED:
            import re
            if re.search(rx, low) and label not in added:
                added.append(label)
    return W._finish({"serving_g": serving, "protein_g": raw.get("protein_g") or None,
                      "amino": amino, "unit": unit, "summary": summary,
                      "added": added, "hints": {}, "engine": "vision"})


class VisionError(Exception):
    pass


# ── Gemini: المفتاح المجاني من Google AI Studio ────────────────────
#
# ‏صاحب المشروع طلب حل من غير فلوس، ومفتاح Claude مدفوع. Gemini عنده
# استخدام مجاني بحد يومي. الطلب بيتبعت REST مباشرة (urllib) -- من غير ما
# نضيف مكتبة. واسم الموديل مش مكتوب: Google بتغيّر الأسامي كل كام شهر،
# فبيتختار من قايمة الموديلات المتاحة للمفتاح (flash الأول: أسرع، وهو
# اللي عليه الحد المجاني الأوسع). GEMINI_MODEL بيغيّره لو حد عايز.
_GEMINI = "https://generativelanguage.googleapis.com/v1beta"
_MODEL_CACHE = {}
_SHAPE = (' Reply with JSON only, exactly this shape: {"serving_g": number|null, "protein_g": number|null, '
          '"unit": "per100"|"serving"|"unknown", "amino": {' +
          ", ".join('"%s": number|null' % k for k in W.AMINO) +
          '}, "summary": {"total_aa_g": number|null, "eaa_g": number|null, "bcaa_g": number|null, '
          '"leucine_g": number|null}, "added": [string]}')


def _get(url, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                         "x-goog-api-key": _gemini_key()})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _gemini_models():
    """‏الموديلات اللي هتتجرّب بالترتيب. GEMINI_MODEL الأول لو متحدد، وبعدين
    من قايمة المفتاح: الـ"-latest" (اسم ثابت Google بتحدّثه)، وبعدين flash،
    وبعدين flash-lite. موديل عليه حد مجاني صفر بيرد 429 -- فبنجرّب اللي بعده."""
    chosen = (os.environ.get("GEMINI_MODEL") or "").strip()
    if "names" not in _MODEL_CACHE:
        names = [m.get("name", "").split("/")[-1] for m in _get(_GEMINI + "/models", timeout=20).get("models", [])
                 if "generateContent" in (m.get("supportedGenerationMethods") or [])]
        names = [n for n in names if n.startswith("gemini") and "image" not in n and "tts" not in n]

        def rank(n):
            return (0 if n.endswith("-latest") and "flash" in n else
                    1 if "flash" in n and "lite" not in n else
                    2 if "flash" in n else 3)
        _MODEL_CACHE["names"] = sorted(names, key=rank)[:3] or ["gemini-flash-latest"]
    return ([chosen] if chosen else []) + [n for n in _MODEL_CACHE["names"] if n != chosen]


def _why(e):
    """‏سبب الفشل من غير المفتاح: كود الـHTTP وأول سطر من رسالة Google."""
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        msg = ""
        try:
            msg = json.loads(e.read().decode()).get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            pass
        return ("HTTP %s %s" % (e.code, msg[:120])).strip()
    return type(e).__name__


def _read_gemini(image_bytes, media_type):
    body = json.dumps({"contents": [{"parts": [
        {"inline_data": {"mime_type": media_type, "data": base64.standard_b64encode(image_bytes).decode()}},
        {"text": _PROMPT + _SHAPE}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}).encode()
    errors = []
    for model in _gemini_models():
        try:
            out = _get("%s/models/%s:generateContent" % (_GEMINI, model), body)
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %s" % (model, _why(e)))
            continue
        parts = ((out.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return json.loads("".join(p.get("text", "") for p in parts))
    raise RuntimeError(" | ".join(errors) or "no model")


def read_label(image_bytes, content_type):
    from lab_report import ALLOWED_TYPES, MAX_IMAGE_BYTES, MODEL, api_key
    media_type = ALLOWED_TYPES.get((content_type or "").split(";")[0].strip().lower())
    if not image_bytes or not media_type or media_type == "application/pdf":
        raise VisionError("ابعت صورة JPG أو PNG")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise VisionError("الصورة كبيرة -- صوّرها بدقة أقل")
    if _gemini_key():
        try:
            return normalize(_read_gemini(image_bytes, media_type))
        except Exception as e:  # noqa: BLE001 -- حد يومي خلص، شبكة، رد غريب: الموبايل يكمّل
            _MODEL_CACHE.clear()
            why = str(e) if isinstance(e, RuntimeError) else _why(e)
            print("[whey] gemini failed: %s" % why)    # ‏يبان في سجل Render
            if not api_key():
                raise VisionError("Gemini: %s" % why)
    try:
        import anthropic
    except ImportError:
        raise VisionError("مكتبة القراءة مش متركّبة على السيرفر")
    client = anthropic.Anthropic(api_key=api_key())
    try:
        response = client.messages.create(
            model=MODEL, max_tokens=2048,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                             "data": base64.standard_b64encode(image_bytes).decode()}},
                {"type": "text", "text": _PROMPT}]}],
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        )
    except Exception as e:  # noqa: BLE001 -- أي غلطة: الصفحة بترجع للقراية في الموبايل
        raise VisionError("الخدمة مش متاحة دلوقتي (%s)" % type(e).__name__)
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return normalize(json.loads(text))
    except (ValueError, TypeError):
        raise VisionError("الرد مش مفهوم")

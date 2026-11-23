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


def available():
    from lab_report import api_key
    return bool(api_key())


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


def read_label(image_bytes, content_type):
    from lab_report import ALLOWED_TYPES, MAX_IMAGE_BYTES, MODEL, api_key
    media_type = ALLOWED_TYPES.get((content_type or "").split(";")[0].strip().lower())
    if not image_bytes or not media_type or media_type == "application/pdf":
        raise VisionError("ابعت صورة JPG أو PNG")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise VisionError("الصورة كبيرة -- صوّرها بدقة أقل")
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

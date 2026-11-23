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
Read each row's number from the same row as its name; tables are often curved or glossy, and the
number column can sit half a row below its names -- check that BCAA = Leucine + Isoleucine + Valine.

Labels with several columns: use the FIRST per-serving column, the one "in water" (never "in milk",
never the bigger 2-serving column), and give serving_g for that same column. A "per 100 g" column is
per 100 g of product, NOT per 100 g of protein: take protein per serving from the serving column
(e.g. "Per 100 g: 71 g / Per 35 g: 25 g" -> serving_g 35, protein_g 25). Labels may be in several
languages; read the English or the numbers.
Free amino acids in the ingredients count for "added" too, with or without a blend:
"L-Glycine, L-Alanine, L-Lysine" -> ["Glycine", "Alanine", "Lysine"]."""


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
    # ‏الملخص بيتاخد لو فيه أي رقم منه: علب كتير كاتبة EAA وBCAA من غير
    # المجموع. ورقم أكبر من الحصة نفسها غلطة قراية (عمود الـ٢٠٠ جم).
    summary = {k: (float(v) if v and (not serving or float(v) <= serving) else None)
               for k, v in (raw.get("summary") or {}).items()
               if k in ("total_aa_g", "eaa_g", "bcaa_g", "leucine_g")}
    protein = raw.get("protein_g") or None
    if summary and not summary.get("leucine_g") and amino.get("Leucine"):
        # ‏الليوسين في الجدول بالمللي (جينر Body Builder: "Leucine 2155 mg")
        leu = amino["Leucine"] / 1000.0
        summary["leucine_g"] = round(leu if unit == "serving" else leu * (protein or 0) / 100, 3) or None
    summary = summary if any(summary.values()) else None
    import re
    added = []
    for item in raw.get("added") or []:
        low = str(item).lower().strip()
        for label, rx in W._ADDED:
            # ‏الموديل ساعات بيكتب "Alanine" من غير الـL-: الاسم لوحده كفاية هنا،
            # لأنه جاي من خانة المكونات مش من الجدول
            if (re.search(rx, low) or low == label.lower()) and label not in added:
                added.append(label)
    return W._finish({"serving_g": serving, "protein_g": protein,
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


def _read_gemini(image_bytes, media_type, text=None):
    body = json.dumps({"contents": [{"parts": [
        {"inline_data": {"mime_type": media_type, "data": base64.standard_b64encode(image_bytes).decode()}},
        {"text": text or (_PROMPT + _SHAPE)}]}],
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


# ── باقي المكملات ──────────────────────────────────────────────────
#
# ‏نفس القراية، بس المطلوب حقول المكمل (supplements.TYPES) بدل جدول
# الأحماض. الوحدات اللي العلب بتكتبها بالـIU بتتحوّل في البرومبت، لأن حدود
# الأمان (UL) بالميكروجرام والمللي.
_SUPP_NOTES = {
    "creatine": "form: one of monohydrate, hcl, ethyl_ester, other, unknown. blend: true only if creatine "
                "sits inside a proprietary blend with no amount of its own.",
    "omega3": "Per serving (e.g. per 2 softgels if the serving is 2). oil_mg is the total fish oil.",
    "multi": "Convert units: vitamin D 1 IU = 0.025 ug; vitamin A as retinol/retinyl 1 IU = 0.3 ug "
             "(give null for vitamin A that comes only from beta-carotene); vitamin E 1 IU = 0.67 mg "
             "(d-alpha) or 0.45 mg (dl-alpha); 1 mg = 1000 ug. Give elemental amounts for minerals "
             "when printed. magnesium_mg is from the supplement.",
    "preworkout": "blend: true if any active ingredient is inside a proprietary blend without its own dose.",
    "eaa": "bcaa_only: true if the product has only leucine, isoleucine and valine and none of the other "
           "six essential amino acids.",
}


def prompt_for(kind):
    import supplements as SP
    spec = SP.TYPES[kind]
    shape = ", ".join('"%s": %s' % (k, "number|null" if typ == "num" else "true|false" if typ == "bool" else "string|null")
                      for k, _ar, _en, typ, _lo, _hi in spec["fields"])
    names = "; ".join("%s = %s" % (k, en) for k, _ar, en, _t, _lo, _hi in spec["fields"])
    return ("This is a photo of the label of a %s supplement. Read ONLY what is printed; never estimate. "
            "Use the amounts per ONE serving. Fields: %s. %s null for anything not printed. "
            "Reply with JSON only, exactly this shape: {%s}"
            % (spec["en"], names, _SUPP_NOTES.get(kind, ""), shape))


def normalize_supplement(kind, raw):
    """‏رد الموديل -> حقول المكمل بعد حدود القراية (supplements.clean)."""
    import supplements as SP
    return {"kind": kind, "fields": SP.clean(kind, raw or {}), "engine": "vision"}


def _anthropic(image_bytes, media_type, text, schema=None):
    from lab_report import MODEL, api_key
    try:
        import anthropic
    except ImportError:
        raise VisionError("مكتبة القراءة مش متركّبة على السيرفر")
    client = anthropic.Anthropic(api_key=api_key())
    extra = {"output_config": {"format": {"type": "json_schema", "schema": schema}}} if schema else {}
    try:
        response = client.messages.create(
            model=MODEL, max_tokens=2048,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                             "data": base64.standard_b64encode(image_bytes).decode()}},
                {"type": "text", "text": text}]}], **extra)
    except Exception as e:  # noqa: BLE001 -- أي غلطة: الصفحة بترجع للقراية في الموبايل
        raise VisionError("الخدمة مش متاحة دلوقتي (%s)" % type(e).__name__)
    out = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return json.loads(out[out.find("{"):out.rfind("}") + 1] if not schema else out)
    except (ValueError, TypeError):
        raise VisionError("الرد مش مفهوم")


def read_label(image_bytes, content_type, kind="whey"):
    from lab_report import ALLOWED_TYPES, MAX_IMAGE_BYTES, api_key
    media_type = ALLOWED_TYPES.get((content_type or "").split(";")[0].strip().lower())
    if not image_bytes or not media_type or media_type == "application/pdf":
        raise VisionError("ابعت صورة JPG أو PNG")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise VisionError("الصورة كبيرة -- صوّرها بدقة أقل")
    supp = kind not in W.KINDS
    text = prompt_for(kind) if supp else None
    finish = (lambda raw: normalize_supplement(kind, raw)) if supp else normalize
    if _gemini_key():
        try:
            return finish(_read_gemini(image_bytes, media_type, text))
        except Exception as e:  # noqa: BLE001 -- حد يومي خلص، شبكة، رد غريب: الموبايل يكمّل
            _MODEL_CACHE.clear()
            why = str(e) if isinstance(e, RuntimeError) else _why(e)
            print("[whey] gemini failed: %s" % why)    # ‏يبان في سجل Render
            if not api_key():
                raise VisionError("Gemini: %s" % why)
    if supp:
        return finish(_anthropic(image_bytes, media_type, text))
    return finish(_anthropic(image_bytes, media_type, _PROMPT, _SCHEMA))

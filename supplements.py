# -*- coding: utf-8 -*-
"""‏باقي المكملات (غير الواي): كرياتين، أوميجا ٣، مالتي فيتامين، بري وورك
أوت، EAA/BCAA.

‏ليه مفيش درجة من ١٠٠ هنا: معادلات الواي ونقطها جاية من صاحب المشروع
بالحرف. باقي المكملات مالهاش جدول نقط منه، واختراع أوزان (الجرعة ٤٠ نقطة
والنوع ٣٠؟) يبقى رقم شكله علمي ومالوش أصل. فكل بند هنا قاعدة واحدة من
مصدر منشور (SOURCES، ومكتوبة بالتفصيل في docs/supplements-sources.md)،
ونتيجته: كويس (pass) / ملاحظة (warn) / مش كويس (fail). والحكم على
المنتج كله هو أسوأ بند فيه.

‏البنود دي بتقفل بس (بتحذّر)، مابتفتحش حاجة لحالة مرضية. وأي قاعدة جديدة
تتكتب معاها مصدرها، زي equivalents.py.
"""

SOURCES = {
    "issn_creatine": "Kreider RB et al. ISSN position stand: safety and efficacy of creatine supplementation. JISSN 2017;14:18",
    "efsa_epa_dha": "EFSA NDA Panel. Dietary Reference Values for fats. EFSA Journal 2010;8(3):1461",
    "efsa_epa_dha_ul": "EFSA NDA Panel. Tolerable upper intake level of EPA, DHA and DPA. EFSA Journal 2012;10(7):2815",
    "nih_omega3": "NIH Office of Dietary Supplements. Omega-3 Fatty Acids fact sheet",
    "nih_ul": "NIH ODS / National Academies. Tolerable Upper Intake Levels, adults 19+",
    "efsa_caffeine": "EFSA NDA Panel. Scientific Opinion on the safety of caffeine. EFSA Journal 2015;13(5):4102",
    "issn_beta_alanine": "Trexler ET et al. ISSN position stand: Beta-Alanine. JISSN 2015;12:30",
    "issn_protein": "Jäger R et al. ISSN position stand: protein and exercise. JISSN 2017;14:20",
    "wolfe_bcaa": "Wolfe RR. Branched-chain amino acids and muscle protein synthesis in humans: myth or reality? JISSN 2017;14:30",
    "fda_blend": "21 CFR 101.36(c): a proprietary blend lists only its total weight, not each ingredient",
    "who_sugars": "WHO. Guideline: Sugars intake for adults and children, 2015",
    "usdec_wpi": "U.S. Dairy Export Council. Reference Manual for U.S. Whey and Lactose Products (WPI: 90% protein or more)",
}

# ‏الحد الأعلى الآمن في اليوم للكبار (NIH ODS / National Academies). علبة
# بتدّي أكتر من كده في حصة واحدة بتعدّيه لوحدها، من غير الأكل.
# (المفتاح، عربي، إنجليزي، الوحدة، الحد)
UL = (
    ("vit_a_ug", "فيتامين A (ريتينول)", "Vitamin A (retinol)", "µg", 3000),
    ("vit_d_ug", "فيتامين D", "Vitamin D", "µg", 100),
    ("vit_e_mg", "فيتامين E", "Vitamin E", "mg", 1000),
    ("vit_c_mg", "فيتامين C", "Vitamin C", "mg", 2000),
    ("vit_b6_mg", "فيتامين B6", "Vitamin B6", "mg", 100),
    ("niacin_mg", "نياسين (B3)", "Niacin (B3)", "mg", 35),
    ("folic_ug", "حمض الفوليك", "Folic acid", "µg", 1000),
    ("iron_mg", "حديد", "Iron", "mg", 45),
    ("zinc_mg", "زنك", "Zinc", "mg", 40),
    ("selenium_ug", "سيلينيوم", "Selenium", "µg", 400),
    ("iodine_ug", "يود", "Iodine", "µg", 1100),
    ("copper_mg", "نحاس", "Copper", "mg", 10),
    ("manganese_mg", "منجنيز", "Manganese", "mg", 11),
    ("magnesium_mg", "ماغنيسيوم (من المكمل)", "Magnesium (supplemental)", "mg", 350),
    ("calcium_mg", "كالسيوم", "Calcium", "mg", 2500),
)

# ‏الحقول: (المفتاح، عربي، إنجليزي، النوع، أقل، أكتر). "num" رقم للحصة،
# "bool" علامة صح، "choice" اختيار. أقل/أكتر حدود قراية بس: رقم برّاهم
# غلطة صورة (صفر زيادة) مش منتج، فبيتشال -- زي RANGE في whey_analyzer.
TYPES = {
    "creatine": {
        "ar": "كرياتين", "en": "Creatine", "icon": "fa-bolt",
        "rules": ["issn_creatine", "fda_blend"],
        "fields": [
            ("creatine_g", "كرياتين في الحصة (جم)", "Creatine per serving (g)", "num", 0.1, 30),
            ("form", "نوع الكرياتين", "Creatine form", "choice", None, None),
            ("blend", "مكتوب Proprietary Blend من غير كمية الكرياتين", "A proprietary blend without the creatine amount", "bool", None, None),
        ],
        "choices": {"form": (("monohydrate", "Monohydrate", "Monohydrate"), ("hcl", "HCl", "HCl"),
                             ("ethyl_ester", "Ethyl Ester", "Ethyl Ester"),
                             ("other", "نوع تاني (Buffered/Nitrate/…)", "Other (Buffered/Nitrate/…)"),
                             ("unknown", "مش مكتوب", "Not stated"))},
    },
    "omega3": {
        "ar": "أوميجا ٣", "en": "Omega-3", "icon": "fa-fish",
        "rules": ["efsa_epa_dha", "efsa_epa_dha_ul", "nih_omega3"],
        "fields": [
            ("oil_mg", "زيت السمك في الحصة (مجم)", "Fish oil per serving (mg)", "num", 100, 10000),
            ("epa_mg", "EPA في الحصة (مجم)", "EPA per serving (mg)", "num", 1, 6000),
            ("dha_mg", "DHA في الحصة (مجم)", "DHA per serving (mg)", "num", 1, 6000),
        ],
    },
    "multi": {
        "ar": "مالتي فيتامين", "en": "Multivitamin", "icon": "fa-capsules",
        "rules": ["nih_ul"],
        "fields": [(k, ar + " (%s)" % u, en + " (%s)" % u, "num", 0, lim * 50) for k, ar, en, u, lim in UL],
    },
    "preworkout": {
        "ar": "بري وورك أوت", "en": "Pre-workout", "icon": "fa-fire",
        "rules": ["efsa_caffeine", "issn_beta_alanine", "fda_blend"],
        "fields": [
            ("caffeine_mg", "كافيين في الحصة (مجم)", "Caffeine per serving (mg)", "num", 1, 1500),
            ("beta_alanine_g", "بيتا ألانين في الحصة (جم)", "Beta-alanine per serving (g)", "num", 0.1, 20),
            ("blend", "مكتوب Proprietary Blend من غير الجرعات", "A proprietary blend without the doses", "bool", None, None),
        ],
    },
    "eaa": {
        "ar": "EAA / BCAA", "en": "EAA / BCAA", "icon": "fa-dna",
        "rules": ["issn_protein", "wolfe_bcaa"],
        "fields": [
            ("leucine_g", "ليوسين في الحصة (جم)", "Leucine per serving (g)", "num", 0.05, 20),
            ("bcaa_only", "BCAA بس (مفيهوش باقي الأحماض الأساسية)", "BCAA only (no other essential amino acids)", "bool", None, None),
        ],
    },
}

VERDICTS = {
    "pass": ("كويس", "Good", "البنود كلها مطابقة للمصادر.", "Every item matches the sources."),
    "warn": ("فيه ملاحظات", "Has notes", "ينفع، بس اقرا الملاحظات قبل ما تشتري.", "Usable, but read the notes before you buy."),
    "fail": ("مش ننصح بيه", "Not recommended", "فيه بند مش آمن أو مش معروف جرعته.", "An item is unsafe or its dose is unknown."),
}
_ORDER = {"pass": 0, "warn": 1, "fail": 2}


def _c(key, status, ar, en, source):
    return {"key": key, "status": status, "ar": ar, "en": en, "source": source}


def _creatine(v):
    out = []
    if v.get("blend"):
        out.append(_c("blend", "fail", "كمية الكرياتين مستخبية جوه Proprietary Blend: مش هتعرف بتاخد كام.",
                      "The creatine amount is hidden in a proprietary blend: you cannot know your dose.", "fda_blend"))
    g = v.get("creatine_g")
    if g:
        if g < 3:
            out.append(_c("dose", "warn", "%g جم أقل من جرعة الصيانة (٣-٥ جم في اليوم): هتحتاج أكتر من حصة." % g,
                          "%g g is below the 3-5 g/day maintenance dose: you will need more than one serving." % g,
                          "issn_creatine"))
        elif g > 5:
            out.append(_c("dose", "warn", "%g جم أكتر من جرعة الصيانة (٣-٥ جم) -- الزيادة مش بتفرق غير في أيام التحميل." % g,
                          "%g g is above the 3-5 g maintenance dose -- more only matters during loading." % g,
                          "issn_creatine"))
        else:
            out.append(_c("dose", "pass", "%g جم: جرعة الصيانة المدروسة (٣-٥ جم)." % g,
                          "%g g: the studied maintenance dose (3-5 g)." % g, "issn_creatine"))
    form = v.get("form")
    if form == "monohydrate":
        out.append(_c("form", "pass", "Monohydrate: أكتر نوع مدروس وأمانه وفايدته ثابتين.",
                      "Monohydrate: the most studied form, proven safe and effective.", "issn_creatine"))
    elif form == "ethyl_ester":
        out.append(_c("form", "fail", "Ethyl Ester طلع أضعف من الـMonohydrate في المقارنة المباشرة.",
                      "Ethyl ester did worse than monohydrate when compared head to head.", "issn_creatine"))
    elif form in ("hcl", "other"):
        out.append(_c("form", "warn", "النوع ده مااتثبتش إنه أحسن من الـMonohydrate، وغالباً أغلى.",
                      "This form has not been shown to beat monohydrate, and usually costs more.", "issn_creatine"))
    return out


def _omega3(v):
    out = []
    epa, dha, oil = v.get("epa_mg"), v.get("dha_mg"), v.get("oil_mg")
    both = (epa or 0) + (dha or 0)
    if epa or dha:
        if both < 250:
            out.append(_c("dose", "warn", "EPA+DHA %d مجم في الحصة، أقل من ٢٥٠ مجم في اليوم (الاحتياج)." % both,
                          "EPA+DHA %d mg per serving, below the 250 mg a day adults need." % both, "efsa_epa_dha"))
        else:
            out.append(_c("dose", "pass", "EPA+DHA %d مجم في الحصة: بيغطي الـ٢٥٠ مجم في اليوم." % both,
                          "EPA+DHA %d mg per serving: covers the 250 mg a day." % both, "efsa_epa_dha"))
        if both > 5000:
            out.append(_c("upper", "warn", "أكتر من ٥ جم EPA+DHA في الحصة -- ده أعلى من اللي اتثبت أمانه.",
                          "More than 5 g EPA+DHA per serving -- above what has been shown safe.", "efsa_epa_dha_ul"))
    if oil and (epa or dha):
        pct = both / oil * 100
        if pct < 30:
            out.append(_c("purity", "warn", "EPA+DHA %.0f%% بس من الزيت -- أقل من زيت السمك العادي (٣٠٪)." % pct,
                          "EPA+DHA is only %.0f%% of the oil -- below plain fish oil (30%%)." % pct, "nih_omega3"))
        else:
            out.append(_c("purity", "pass", "EPA+DHA %.0f%% من الزيت%s." % (pct, " (مركّز)" if pct >= 50 else ""),
                          "EPA+DHA is %.0f%% of the oil%s." % (pct, " (concentrated)" if pct >= 50 else ""), "nih_omega3"))
    return out


def _multi(v):
    out = []
    for key, ar, en, unit, lim in UL:
        amount = v.get(key)
        if amount is None:
            continue
        if amount > lim:
            out.append(_c(key, "fail", "%s %g %s في الحصة -- أكتر من الحد الأعلى الآمن في اليوم (%g %s)." % (ar, amount, unit, lim, unit),
                          "%s %g %s per serving -- above the daily safe upper limit (%g %s)." % (en, amount, unit, lim, unit), "nih_ul"))
        else:
            out.append(_c(key, "pass", "%s %g %s: تحت الحد الأعلى (%g)." % (ar, amount, unit, lim),
                          "%s %g %s: under the upper limit (%g)." % (en, amount, unit, lim), "nih_ul"))
    return out


def _preworkout(v):
    out = []
    caf = v.get("caffeine_mg")
    if caf:
        if caf > 400:
            out.append(_c("caffeine", "fail", "كافيين %d مجم في الحصة -- أكتر من ٤٠٠ مجم، الحد الآمن لليوم كله." % caf,
                          "%d mg caffeine per serving -- over 400 mg, the safe limit for a whole day." % caf, "efsa_caffeine"))
        elif caf > 200:
            out.append(_c("caffeine", "warn", "كافيين %d مجم -- أكتر من ٢٠٠ مجم في المرة. ومش للحوامل." % caf,
                          "%d mg caffeine -- over 200 mg in one go. Not for pregnancy." % caf, "efsa_caffeine"))
        else:
            out.append(_c("caffeine", "pass", "كافيين %d مجم: في حدود الجرعة الآمنة في المرة (٢٠٠ مجم)." % caf,
                          "%d mg caffeine: within the safe single dose (200 mg)." % caf, "efsa_caffeine"))
    ba = v.get("beta_alanine_g")
    if ba:
        ok = ba >= 4
        out.append(_c("beta_alanine", "pass" if ok else "warn",
                      "بيتا ألانين %g جم%s (الفعّال ٤-٦ جم في اليوم لمدة أسبوعين على الأقل)." % (ba, "" if ok else "، أقل من الفعّال"),
                      "Beta-alanine %g g%s (effective: 4-6 g a day for at least 2 weeks)." % (ba, "" if ok else ", below the effective dose"),
                      "issn_beta_alanine"))
    if v.get("blend"):
        out.append(_c("blend", "warn", "Proprietary Blend: الجرعات مستخبية، فمش هتعرف كل مادة بكام.",
                      "Proprietary blend: the doses are hidden, so you cannot check each one.", "fda_blend"))
    return out


def _eaa(v):
    out = []
    leu = v.get("leucine_g")
    if leu:
        ok = leu >= 0.7
        out.append(_c("leucine", "pass" if ok else "warn",
                      "ليوسين %g جم%s (المطلوب في الجرعة ٠.٧-٣ جم)." % (leu, "" if ok else "، قليل"),
                      "Leucine %g g%s (a dose should carry 0.7-3 g)." % (leu, "" if ok else ", too little"),
                      "issn_protein"))
    if v.get("bcaa_only"):
        out.append(_c("bcaa_only", "warn", "BCAA لوحدها مابتبنيش عضل: الجسم محتاج الـ٩ أحماض الأساسية كلهم. الواي أو EAA كاملة أحسن.",
                      "BCAAs alone do not build muscle: the body needs all 9 essential amino acids. Whey or full EAAs do better.",
                      "wolfe_bcaa"))
    return out


_RULES = {"creatine": _creatine, "omega3": _omega3, "multi": _multi, "preworkout": _preworkout, "eaa": _eaa}


def clean(kind, values):
    """‏قيم الحقول بعد حدود القراية: رقم برّا الحدود بيتشال."""
    out = {}
    for key, _ar, _en, typ, lo, hi in TYPES[kind]["fields"]:
        v = (values or {}).get(key)
        if typ == "num":
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if lo <= v <= hi and v > 0:
                out[key] = v
        elif typ == "bool":
            if v in (True, "1", "on", "true", 1):
                out[key] = True
        elif v in {c[0] for c in TYPES[kind]["choices"][key]}:
            out[key] = v
    return out


def evaluate(kind, values):
    """‏البنود والحكم. ValueError لو مفيش ولا بند اتحسب (مفيش أرقام)."""
    checks = _RULES[kind](clean(kind, values))
    if not checks:
        raise ValueError("اكتب الأرقام اللي على العلبة الأول")
    verdict = max((c["status"] for c in checks), key=_ORDER.get)
    ar, en, note_ar, note_en = VERDICTS[verdict]
    return {"kind": kind, "checks": checks, "verdict": verdict,
            "verdict_ar": ar, "verdict_en": en, "note_ar": note_ar, "note_en": note_en,
            "sources": [s for s in dict.fromkeys(c["source"] for c in checks)]}

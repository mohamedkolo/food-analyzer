# -*- coding: utf-8 -*-
"""‏يخلّي بروتين اليوم يوصل للمستهدف، بدل ما الورقة تقول رقم والأكل يدي غيره.

المشكلة اللي الملف ده موجود عشانها
──────────────────────────────────
‏الورقة بتطبع "بروتين: ١٦٢ جم (١.٨ جم/كجم)" -- ده **وصفة**، محسوبة من
وزن العميل. والأكل اللي في الجدول بيدي حاجة تانية خالص. قِسْتها على
أربع حالات حقيقية:

    ذكر ٩٠ كجم، هدف ١٦٢ جم   ->  الأسبوع ١٠٨ إلى ١٧٣   (ناقص ٣٣٪)
    أنثى ٨٢ كجم، هدف ١٣١ جم   ->  الأسبوع  ٨٦ إلى ١٤٨   (ناقص ٣٤٪)
    أنثى ٩٥ كجم، هدف ١٥٢ جم   ->  الأسبوع  ٧٨ إلى ١٤٤   (ناقص ٤٩٪)
    ذكر ٧٠ كجم عضل، هدف ١٤٠   ->  الأسبوع ٢١١ إلى ٢٥٧   (زايد ٨٤٪)

‏ليه بيحصل: وجبات القاعدة حصصها ثابتة، وبتتكبّر أو تتصغّر بمعامل واحد
عشان توصل لسعرات اليوم. والمعامل بيشد **السعرات والبروتين مع بعض**.
فيوم التدوير المنخفض بروتينه بينزل معاه، ويوم التضخيم بروتينه بيطلع
معاه. والتدوير نفسه مبني على مبدأ "البروتين ثابت والكارب هو اللي
يتأرجح" -- وهو ثابت في الوصفة بس، الأكل مابيلتزمش.

‏ويوم الـ٧٨ جم في عجز هو بالظبط اليوم اللي العميل بيفقد فيه عضل.

ليه الترتيب لوحده مش حل
───────────────────────
‏أول حاجة جرّبتها: نوزّع التركيبات على الأيام بحيث التركيبة الأعلى
بروتيناً تقع على اليوم الأقل سعرات. قِسْت كثافة البروتين (جرام لكل
سعرة) في قاعدة الأكل كلها:

    المتاح في القاعدة   ٠.٠٦٨ إلى ٠.٠٧٩ جم/سعرة
    المطلوب ليوم ١٥٣٠ سعرة و١٦٢ جم   ٠.١٠٦ جم/سعرة

‏يعني **مافيش ترتيب** بيوصل: أعلى تركيبة في القاعدة على أعلى يوم
بتطلّع ١٢١ جم والمطلوب ١٦٢. الأكل نفسه مش كفاية بروتين للوصفة دي.

الحل: زيادة بروتين، ومقابلها نقص من الأقل بروتيناً
──────────────────────────────────────────────────
‏ده اللي أخصائي التغذية بيعمله بإيده: اليوم ناقص بروتين، يزوّد بياض
بيض أو تونة بالماء، ويقلّل النشوية. والحسبة لازم تبص للاتنين مع بعض،
لأن الزيادة سعراتها بتخرج من مكان تاني:

    خانة بروتين ناقصة          G
    كثافة البروتين في الزيادة  dP  (بياض البيض ٠.٢١ جم/سعرة)
    كثافة البروتين في المقتطع  dS  (طبق مختلط ~٠.٠٧٥)

    لو زوّدنا G بروتين، سعراتها G/dP، وشِلنا نفس السعرات من طبق
    كثافته dS، نكون خسّرنا (G/dP)×dS بروتين. فالصافي:

        الصافي = G × (1 - dS/dP)

    ومع dS=٠.٠٧٥ وdP=٠.٢١ الصافي = ٠.٦٤ × G. يعني عشان نسد خانة G
    لازم نزوّد G/٠.٦٤ -- والمعادلة دي هي اللي الملف بيحلها.

‏والزيادة بتتقطع من **أقل خانة كثافة بروتين** في اليوم، وهي بالتعريف
الخانة النشوية (مافيش أرقام كارب في القاعدة، فالكثافة هي أحسن دليل
متاح).

حدود مقصودة
───────────
  • ‏الزيادة أكلة حقيقية بحصة معقولة، وفوق ٢٥٠ جم مابنزوّدش أكتر --
    بنسد اللي نقدر عليه ونقول للدكتور الباقي.
  • ‏الزيادة لازم تعدّي حالات العميل زي أي أكل تاني. مافيش استثناء.
  • ‏اليوم اللي بروتينه **زايد** (التضخيم) مابنشيلش منه بروتين:
    مينفعش نلغي أكل من طبق، والزيادة مش خطر. بنقوله الرقم الحقيقي.
"""

import re


# ‏مصادر البروتين للزيادة. الأرقام لكل ١٠٠ جرام، والترتيب بالكثافة:
# الأعلى كثافة الأول عشان السعرات المقتطعة تبقى أقل.
#
# ‏والتلاتة من الـ٤١ صنف اللي بيعدّوا الـ٦٥ حالة كلها -- فمهما كانت
# حالات العميل، فيه مصدر بيملا الخانة.
SOURCES = [
    # ‏العدّ بيتعمل في plan_engine بنفس دالة توزيع الوجبات
    # (_main_base)، مش بتوكن من عندي: جرّبت توكن ("تونة") والدالة
    # بتحوّلها "سمك"، فالعدّ ماشافش أطباق السمك في الطابور والتكرار
    # طلع ٥. المقياس لازم يبقى هو نفسه في المكانين.
    {"ar": "تونة بالماء", "en": "tuna in water", "cal": 100, "p": 23,
     "emoji": "🐟", "token": "تونة"},
    {"ar": "بياض بيض", "en": "egg whites", "cal": 52, "p": 11,
     "emoji": "🥚", "token": "بيض"},
    {"ar": "صدر دجاج مشوي", "en": "grilled chicken breast", "cal": 165,
     "p": 31, "emoji": "🍗", "token": "دجاج"},
]

# ‏أقصى حصة للزيادة الواحدة. فوق كده بقى رقم على ورق مش أكل.
MAX_GRAMS = 250

# ‏أقصى عدد أيام في الأسبوع للمصدر الواحد. نفس الحد اللي توزيع
# الوجبات ماشي عليه (_spread_by_base) -- ٣ من ٧.
MAX_WEEK_USES = 3

# ‏الخانة دي مقفولة لو الفرق أقل من كده. البروتين مش رقم دقيق لدرجة
# إن ٥ جرام فرق يستاهل نغيّر الطبق.
TOL_G = 8
TOL_PCT = 0.07


def _density(cal, protein):
    return (float(protein) / float(cal)) if cal else 0.0


def pick_source(is_safe, turn=0):
    """‏مصدر بروتين بيعدّي حالات العميل، **بالتدوير على الأيام**.

    ‏turn = رقم اليوم. من غيره كانت بتختار أول مصدر آمن كل يوم،
    والنتيجة تونة ١٧٥-٢٥٠ جم **ستة أيام من سبعة** -- أخصائي تغذية
    مايعملش كده، والعميل مش هيكمّل أسبوع على نفس الصنف.
    """
    safe = [s for s in SOURCES if is_safe(s["ar"])]
    if not safe:
        return None
    return safe[int(turn) % len(safe)]


def grams_needed(gap_g, source, trim_density):
    """‏كام جرام من المصدر عشان نسد خانة gap_g **بعد** حساب المقتطع.

    ‏بترجّع (جرامات, سعرات الزيادة, الصافي اللي هيتحقق) -- والتلاتة
    مقرّبين لأرقام تنفع تتكتب على ورقة.
    """
    dp = _density(source["cal"], source["p"])
    if dp <= 0:
        return 0, 0, 0.0
    # ‏الصافي لكل جرام من المصدر: بروتينه ناقص اللي بيضيع من المقتطع
    net_per_gram = (source["p"] / 100.0) - (source["cal"] / 100.0) * trim_density
    if net_per_gram <= 0:
        # ‏المقتطع كثافته أعلى من المصدر -- الزيادة بتضر مش بتنفع
        return 0, 0, 0.0
    grams = gap_g / net_per_gram
    grams = max(0, min(MAX_GRAMS, int(round(grams / 5.0) * 5)))
    if grams <= 0:
        return 0, 0, 0.0
    return (grams,
            grams * source["cal"] / 100.0,
            grams * net_per_gram)


def shortfall(actual_p, target_p):
    """‏الخانة الناقصة بالجرام، أو صفر لو اليوم مظبوط أو زايد."""
    if not target_p or target_p <= 0:
        return 0.0
    gap = float(target_p) - float(actual_p)
    if gap <= max(TOL_G, target_p * TOL_PCT):
        return 0.0
    return gap


def plan_topup(actual_p, target_p, slots, is_safe, turn=0, used=None):
    """‏يرجّع خطة الزيادة لليوم، أو None لو مش محتاج/مش ممكن.

    slots: {اسم الخانة: (سعراتها, بروتينها)} -- اللي ينفع يتقطع منها.

    ‏بترجّع ديكشنري: المصدر، الجرامات، سعرات الزيادة، الخانة اللي
    هيتقطع منها، السعرات المقتطعة، والصافي المتوقّع.
    """
    gap = shortfall(actual_p, target_p)
    if gap <= 0:
        return None
    safe = [s for s in SOURCES if is_safe(s["ar"])]
    if not safe:
        return None
    # ‏الترتيب: اللي بالدور الأول (عشان الأسبوع ما يبقاش صنف واحد)،
    # وبعده الباقي -- فلو اللي بالدور مش هيسد الخانة، بنكمّل عليه.
    #
    # ‏الحد بالجرامات (٢٥٠) بيظلم المصدر الأقل كثافة: ٢٥٠ جم بياض بيض
    # بتدي ٢٧.٥ جم بروتين بس، و٢٥٠ جم صدر دجاج بتدي ٧٧.٥. فاليوم اللي
    # خانته كبيرة كان بينزل ١.٢٢ جم/كجم لأن الدور وقع على بياض البيض.
    start = int(turn) % len(safe)
    order = safe[start:] + safe[:start]
    # ‏والأقل استخداماً الأول. من غير ده الرجوع للمصدر الأكثف كان
    # بيحط نفس الصنف في نفس الخانة **خمس مرات في الأسبوع** -- والطقم
    # مسكها (اختبار تكرار المكوّن في الخانة). التنويع بيتقدّم على
    # الدور، والسد بيتقدّم على الاتنين.
    # ‏حد صارم على التكرار: مصدر واحد مايزيدش عن MAX_WEEK_USES في
    # الأسبوع.
    #
    # ‏ليه صارم ومش ترتيب بس: الرجوع للمصدر الأكثف (اللي بيسد الخانة)
    # كان بيحط صدر الدجاج في نفس الخانة **خمس مرات في الأسبوع**،
    # والطقم مسكها. والاختبار على حق: لو الزيادة دجاج خمس أيام، العميل
    # بياكل دجاج خمس أيام -- والتنويع شرط التزام مش تجميل.
    #
    # ‏وتلات مصادر × تلات مرات = تسع خانات لسبع أيام، فالحد دايماً
    # قابل للتحقيق لو التلاتة آمنين. ولو الحد خلّى المصدر المتاح
    # مايسدّش الخانة كلها، بناخد اللي نقدر عليه والورقة بتقول الباقي.
    used = used or {}
    under = [src for src in order
             if used.get(src["ar"], 0) < MAX_WEEK_USES]
    if under:
        order = under
    order.sort(key=lambda src: used.get(src["ar"], 0))

    # ‏المقتطع من الخانات الأقل كثافة بروتين (النشوية بالتعريف)،
    # **وأكتر من خانة لو لزم**.
    #
    # ‏أول نسخة كانت بتقطع من خانة واحدة بحد نص سعراتها، والحد ده كان
    # هو اللي بيوقف الإصلاح: أنثى ٩٥ كجم هدفها ١٥٢ جم فضل عندها يوم
    # ٩٧ جم (ناقص ٣٦٪) -- مش لأن الحساب غلط، لأن مافيش سعرات كفاية
    # في طبق واحد. الأسبوع كله بقى محتاج طبقين.
    usable = sorted(
        ((name, cal, p) for name, (cal, p) in slots.items() if cal > 0),
        key=lambda row: _density(row[1], row[2]))
    if not usable:
        return None

    def _trims(want_cal):
        """‏يوزّع want_cal سعرة على الخانات، نص كل خانة بالكتير."""
        out, left = [], float(want_cal)
        for name, cal, protein in usable:
            if left <= 0:
                break
            take = min(cal * 0.5, left)
            if take <= 0:
                continue
            out.append((name, take, _density(cal, protein)))
            left -= take
        return out, left

    def _solve(src):
        """‏يحل التشابك لمصدر واحد: الجرامات بتحدّد السعرات المقتطعة،
        والمقتطع بيحدّد الصافي، والصافي بيحدّد الجرامات. تلات لفّات."""
        blended = _density(usable[0][1], usable[0][2])
        g = c = 0
        n = 0.0
        tr = []
        for _ in range(3):
            g, c, _ = grams_needed(gap, src, blended)
            if g <= 0:
                return None
            tr, _left = _trims(c)
            if not tr:
                return None
            paid = sum(cal for _nm, cal, _d in tr)
            if paid <= 0:
                return None
            blended = sum(cal * d for _nm, cal, d in tr) / paid
            # ── الجرامات تتسقّف على اللي الأطباق تقدر تدفعه ──
            #
            # ‏الغلطة اللي كانت هنا: كنت بسقّف السعرات المدفوعة
            # (c = min(c, paid)) وبسيب الجرامات زي ما هي. فاليوم كان
            # بيزوّد بروتين سعراته أكتر من اللي اتقطع، ويكسب الفرق من
            # فراغ -- والطقم مسكها: يومين من ١٦٨ بعدوا ١٢٪ عن هدفهم،
            # والمقيس قبل كده صفر.
            if paid < c:
                g = int(round((paid / (src["cal"] / 100.0)) / 5.0) * 5)
                if g <= 0:
                    return None
                tr, _left = _trims(g * src["cal"] / 100.0)
                if not tr:
                    return None
            c = g * src["cal"] / 100.0
            n = g * src["p"] / 100.0 - sum(cal * d for _nm, cal, d in tr)
        return (g, c, n, tr) if (g > 0 and n > 0) else None

    # ‏أول مصدر بيسد الخانة فعلاً؛ وإلا أحسن واحد متاح
    best = None
    for src in order:
        got = _solve(src)
        if not got:
            continue
        if got[2] >= gap * 0.9:
            source, (grams, add_cal, net, trims) = src, got
            break
        if best is None or got[2] > best[1][2]:
            best = (src, got)
    else:
        if best is None:
            return None
        source, (grams, add_cal, net, trims) = best
    return {
        "source": source,
        "grams": grams,
        "add_cal": add_cal,
        "add_p": grams * source["p"] / 100.0,
        "trims": [(name, cal) for name, cal, _d in trims],
        "trim_slot": trims[0][0],
        "trim_cal": add_cal,
        "net_p": net,
        "gap": gap,
        "closed": net >= gap * 0.9,
    }


def line(topup, is_ar=True):
    """‏سطر الزيادة زي ما بيتكتب في الوجبة."""
    source = topup["source"]
    name = source["ar"] if is_ar else source["en"]
    unit = "جم" if is_ar else "g"
    # ‏إيموجي المصدر نفسه. كان 🥚 لكل المصادر، فصدر الدجاج كان بيطلع
    # على الورقة برسمة بيضة.
    return "%s %s %d%s" % (source.get("emoji", "🥚"), name,
                           topup["grams"], unit)


def _density(cal, protein):
    return (float(protein) / float(cal)) if cal else 0.0


def pick_source(is_safe, turn=0):
    """‏مصدر بروتين بيعدّي حالات العميل، **بالتدوير على الأيام**.

    ‏turn = رقم اليوم. من غيره كانت بتختار أول مصدر آمن كل يوم،
    والنتيجة تونة ١٧٥-٢٥٠ جم **ستة أيام من سبعة** -- أخصائي تغذية
    مايعملش كده، والعميل مش هيكمّل أسبوع على نفس الصنف.
    """
    safe = [s for s in SOURCES if is_safe(s["ar"])]
    if not safe:
        return None
    return safe[int(turn) % len(safe)]


def grams_needed(gap_g, source, trim_density):
    """‏كام جرام من المصدر عشان نسد خانة gap_g **بعد** حساب المقتطع.

    ‏بترجّع (جرامات, سعرات الزيادة, الصافي اللي هيتحقق) -- والتلاتة
    مقرّبين لأرقام تنفع تتكتب على ورقة.
    """
    dp = _density(source["cal"], source["p"])
    if dp <= 0:
        return 0, 0, 0.0
    # ‏الصافي لكل جرام من المصدر: بروتينه ناقص اللي بيضيع من المقتطع
    net_per_gram = (source["p"] / 100.0) - (source["cal"] / 100.0) * trim_density
    if net_per_gram <= 0:
        # ‏المقتطع كثافته أعلى من المصدر -- الزيادة بتضر مش بتنفع
        return 0, 0, 0.0
    grams = gap_g / net_per_gram
    grams = max(0, min(MAX_GRAMS, int(round(grams / 5.0) * 5)))
    if grams <= 0:
        return 0, 0, 0.0
    return (grams,
            grams * source["cal"] / 100.0,
            grams * net_per_gram)


def shortfall(actual_p, target_p):
    """‏الخانة الناقصة بالجرام، أو صفر لو اليوم مظبوط أو زايد."""
    if not target_p or target_p <= 0:
        return 0.0
    gap = float(target_p) - float(actual_p)
    if gap <= max(TOL_G, target_p * TOL_PCT):
        return 0.0
    return gap


def plan_topup(actual_p, target_p, slots, is_safe, turn=0, used=None):
    """‏يرجّع خطة الزيادة لليوم، أو None لو مش محتاج/مش ممكن.

    slots: {اسم الخانة: (سعراتها, بروتينها)} -- اللي ينفع يتقطع منها.

    ‏بترجّع ديكشنري: المصدر، الجرامات، سعرات الزيادة، الخانة اللي
    هيتقطع منها، السعرات المقتطعة، والصافي المتوقّع.
    """
    gap = shortfall(actual_p, target_p)
    if gap <= 0:
        return None
    safe = [s for s in SOURCES if is_safe(s["ar"])]
    if not safe:
        return None
    # ‏الترتيب: اللي بالدور الأول (عشان الأسبوع ما يبقاش صنف واحد)،
    # وبعده الباقي -- فلو اللي بالدور مش هيسد الخانة، بنكمّل عليه.
    #
    # ‏الحد بالجرامات (٢٥٠) بيظلم المصدر الأقل كثافة: ٢٥٠ جم بياض بيض
    # بتدي ٢٧.٥ جم بروتين بس، و٢٥٠ جم صدر دجاج بتدي ٧٧.٥. فاليوم اللي
    # خانته كبيرة كان بينزل ١.٢٢ جم/كجم لأن الدور وقع على بياض البيض.
    start = int(turn) % len(safe)
    order = safe[start:] + safe[:start]
    # ‏والأقل استخداماً الأول. من غير ده الرجوع للمصدر الأكثف كان
    # بيحط نفس الصنف في نفس الخانة **خمس مرات في الأسبوع** -- والطقم
    # مسكها (اختبار تكرار المكوّن في الخانة). التنويع بيتقدّم على
    # الدور، والسد بيتقدّم على الاتنين.
    used = used or {}
    order.sort(key=lambda src: used.get(src["ar"], 0))

    # ‏المقتطع من الخانات الأقل كثافة بروتين (النشوية بالتعريف)،
    # **وأكتر من خانة لو لزم**.
    #
    # ‏أول نسخة كانت بتقطع من خانة واحدة بحد نص سعراتها، والحد ده كان
    # هو اللي بيوقف الإصلاح: أنثى ٩٥ كجم هدفها ١٥٢ جم فضل عندها يوم
    # ٩٧ جم (ناقص ٣٦٪) -- مش لأن الحساب غلط، لأن مافيش سعرات كفاية
    # في طبق واحد. الأسبوع كله بقى محتاج طبقين.
    usable = sorted(
        ((name, cal, p) for name, (cal, p) in slots.items() if cal > 0),
        key=lambda row: _density(row[1], row[2]))
    if not usable:
        return None

    def _trims(want_cal):
        """‏يوزّع want_cal سعرة على الخانات، نص كل خانة بالكتير."""
        out, left = [], float(want_cal)
        for name, cal, protein in usable:
            if left <= 0:
                break
            take = min(cal * 0.5, left)
            if take <= 0:
                continue
            out.append((name, take, _density(cal, protein)))
            left -= take
        return out, left

    def _solve(src):
        """‏يحل التشابك لمصدر واحد: الجرامات بتحدّد السعرات المقتطعة،
        والمقتطع بيحدّد الصافي، والصافي بيحدّد الجرامات. تلات لفّات."""
        blended = _density(usable[0][1], usable[0][2])
        g = c = 0
        n = 0.0
        tr = []
        for _ in range(3):
            g, c, _ = grams_needed(gap, src, blended)
            if g <= 0:
                return None
            tr, _left = _trims(c)
            if not tr:
                return None
            paid = sum(cal for _nm, cal, _d in tr)
            if paid <= 0:
                return None
            blended = sum(cal * d for _nm, cal, d in tr) / paid
            # ── الجرامات تتسقّف على اللي الأطباق تقدر تدفعه ──
            #
            # ‏الغلطة اللي كانت هنا: كنت بسقّف السعرات المدفوعة
            # (c = min(c, paid)) وبسيب الجرامات زي ما هي. فاليوم كان
            # بيزوّد بروتين سعراته أكتر من اللي اتقطع، ويكسب الفرق من
            # فراغ -- والطقم مسكها: يومين من ١٦٨ بعدوا ١٢٪ عن هدفهم،
            # والمقيس قبل كده صفر.
            if paid < c:
                g = int(round((paid / (src["cal"] / 100.0)) / 5.0) * 5)
                if g <= 0:
                    return None
                tr, _left = _trims(g * src["cal"] / 100.0)
                if not tr:
                    return None
            c = g * src["cal"] / 100.0
            n = g * src["p"] / 100.0 - sum(cal * d for _nm, cal, d in tr)
        return (g, c, n, tr) if (g > 0 and n > 0) else None

    # ‏أول مصدر بيسد الخانة فعلاً؛ وإلا أحسن واحد متاح
    best = None
    for src in order:
        got = _solve(src)
        if not got:
            continue
        if got[2] >= gap * 0.9:
            source, (grams, add_cal, net, trims) = src, got
            break
        if best is None or got[2] > best[1][2]:
            best = (src, got)
    else:
        if best is None:
            return None
        source, (grams, add_cal, net, trims) = best
    return {
        "source": source,
        "grams": grams,
        "add_cal": add_cal,
        "add_p": grams * source["p"] / 100.0,
        "trims": [(name, cal) for name, cal, _d in trims],
        "trim_slot": trims[0][0],
        "trim_cal": add_cal,
        "net_p": net,
        "gap": gap,
        "closed": net >= gap * 0.9,
    }


def line(topup, is_ar=True):
    """‏سطر الزيادة زي ما بيتكتب في الوجبة."""
    source = topup["source"]
    name = source["ar"] if is_ar else source["en"]
    unit = "جم" if is_ar else "g"
    # ‏إيموجي المصدر نفسه. كان 🥚 لكل المصادر، فصدر الدجاج كان بيطلع
    # على الورقة برسمة بيضة.
    return "%s %s %d%s" % (source.get("emoji", "🥚"), name,
                           topup["grams"], unit)


# ‏الزيادة **إضافة** مش هوية الطبق. الفرق ده مهم لأن توزيع الأسبوع
# بيتقاس بمكوّن الطبق الأساسي (_main_base في plan_engine)، واللي
# بيرجع للنص الكامل لو أول صنف مش معروف. فطبق زي "طاجن خضار" مع
# زيادة دجاج كان بيتحسب "دجاج" -- والأسبوع بقى ٥ أيام دجاج في عين
# الاختبار، والطقم مسكها.
#
# ‏الحذف دقيق بالقصد: الشكل اللي line() بتطلّعه بالظبط، وفي آخر النص
# بس. طبق حقيقي آخره "صدر دجاج مشوي 150جم" مابيتلمسش -- الإيموجي
# والترتيب هما الفرق.
_TAIL = re.compile(
    r"\s*\+\s*(?:%s)\s+\d+\s*(?:جم|g)\s*$"
    % "|".join(re.escape("%s %s" % (s.get("emoji", ""), s["ar"]))
               for s in SOURCES))


def strip_topup(text):
    """‏نص الوجبة من غير سطر الزيادة، للمقارنات اللي بتخص الطبق نفسه."""
    return _TAIL.sub("", str(text or ""))

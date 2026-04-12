#!/usr/bin/env python3
"""
NutraX — مولّد PDF الجداول الغذائية
يولّد جدول أسبوعي كامل بناءً على بيانات المريض والأعراض
"""

import sys, json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
import arabic_reshaper
from bidi.algorithm import get_display

# ── Register Arabic fonts ──
FONT_REG  = "/usr/share/fonts/opentype/fonts-hosny-amiri/Amiri-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/opentype/fonts-hosny-amiri/Amiri-Bold.ttf"
pdfmetrics.registerFont(TTFont("Amiri", FONT_REG))
pdfmetrics.registerFont(TTFont("AmiriBold", FONT_BOLD))

# ── Colors ──
C_BLUE   = colors.HexColor("#1a3a6b")
C_LBLUE  = colors.HexColor("#dce8f5")
C_GREEN  = colors.HexColor("#1a5c3a")
C_LGREEN = colors.HexColor("#e8f5ec")
C_RED    = colors.HexColor("#8b0000")
C_LRED   = colors.HexColor("#ffeef0")
C_ORANGE = colors.HexColor("#b34700")
C_LORANG = colors.HexColor("#fef3e2")
C_GRAY   = colors.HexColor("#f5f5f5")
C_DGRAY  = colors.HexColor("#333333")
C_WHITE  = colors.white
C_BLACK  = colors.black

def ar(text):
    """Reshape and apply BiDi to Arabic text"""
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except:
        return str(text)

def style(name="Normal", font="Amiri", size=11, color=C_BLACK, align=TA_RIGHT,
          bold=False, space_after=4, space_before=2):
    return ParagraphStyle(
        name,
        fontName="AmiriBold" if bold else font,
        fontSize=size,
        textColor=color,
        alignment=align,
        spaceAfter=space_after,
        spaceBefore=space_before,
        rightIndent=4,
        leftIndent=4,
        leading=size * 1.5,
    )

def p(text, st):
    return Paragraph(ar(text), st)

def hr(color=C_BLUE, thickness=1.5):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=8, spaceBefore=8)

def sp(h=8):
    return Spacer(1, h)


# ══════════════════════════════════════════════════════════════
# MEAL DATABASE — مكتبة الوجبات المصرية
# ══════════════════════════════════════════════════════════════

FOODS = {
    # اسم: (الكمية, السعرات, البروتين, وصف)
    "فول مدمس بزيت الزيتون": ("200 جم", 220, 8, "ألياف + أوميغا 3 — يحفز الأمعاء"),
    "فول مع طحينة وليمون": ("200 جم + ملعقة طحينة", 290, 11, "كالسيوم + دهون صحية + ألياف"),
    "بيضتان مسلوقتان": ("2 حبة", 156, 12, "بروتين كامل عالي الجودة"),
    "بيض أومليت بالخضار": ("3 بيضات + خضار", 250, 18, "بروتين صباحي يرفع الحرق 25%"),
    "شوفان بالحليب": ("6 ملاعق + كوب حليب", 280, 10, "بيتا جلوكان يهدئ القولون"),
    "شوفان بالموز والقرفة": ("6 ملاعق + موزة", 310, 9, "القرفة تنظم السكر + ترفع الحرق"),
    "خبز أسمر": ("شريحة (30جم)", 70, 3, "ألياف تساعد القولون"),
    "طماطم وخيار": ("طبق صغير", 30, 1, "ألياف + ترطيب"),
    "صدر دجاج مشوي": ("150 جم", 248, 46, "بروتين يرفع معدل الحرق"),
    "صدر دجاج فرن بالخضار": ("180 جم + خضار", 310, 50, "وجبة مثالية لحرق الدهون"),
    "فخذ دجاج فرن بدون جلد": ("200 جم", 250, 35, "بروتين عالي بدون دهون الجلد"),
    "كبدة دجاج مشوية": ("150 جم", 179, 26, "أغنى مصدر للحديد — يرفع الطاقة"),
    "سمك بلطي مشوي": ("200 جم", 192, 40, "أوميغا 3 يقلل التهاب القولون"),
    "سمكة بلطي كاملة مشوية": ("250 جم", 240, 50, "بروتين عالي جداً + أوميغا 3"),
    "أرز بني": ("4 ملاعق مطبوخ", 130, 3, "كارب بطيء يشبع طويل"),
    "برغل مطبوخ": ("4 ملاعق", 120, 4, "ألياف أعلى من الأرز الأبيض"),
    "بطاطا حلوة مشوية": ("1 حبة وسط", 129, 2, "ألياف + بيتا كاروتين"),
    "بطاطا مسلوقة": ("150 جم", 116, 2, "بوتاسيوم — ينظم الأمعاء"),
    "شوربة عدس أحمر": ("طبق عميق", 180, 9, "ألياف قابلة للذوبان — ممتازة للقولون"),
    "شوربة عدس أصفر": ("طبق عميق", 180, 9, "بروتين نباتي + ألياف"),
    "عدس مطهو بجزر وكرفس": ("طبق", 200, 10, "ألياف + بروتين نباتي"),
    "شوربة خضار": ("طبق عميق", 150, 4, "مرق دافئ يريح القولون"),
    "حمص بطحينة": ("150 جم", 250, 10, "بروتين نباتي + ألياف"),
    "كشري مصري": ("طبق صغير 250جم", 280, 12, "عدس + أرز + مكرونة = بروتين كامل نباتي"),
    "ملوخية بزيت الزيتون": ("طبق", 80, 4, "سوبر فود مصري — حديد + كالسيوم"),
    "سلطة خضار نيئة": ("طبق كبير", 40, 2, "ألياف + إنزيمات هضمية"),
    "سلطة فتوش": ("طبق كبير", 80, 3, "خضار نيئة — إنزيمات طبيعية"),
    "كوسة مشوية": ("150 جم", 35, 2, "خضار طرية سهلة على القولون"),
    "زبادي يوناني سادة": ("150 جم", 89, 15, "بروبيوتيك يصلح بكتيريا الأمعاء"),
    "جبن قريش": ("50 جم", 49, 6, "بروتين خفيف للعشاء"),
    "تفاحة بالقشر": ("1 حبة وسط", 80, 0.5, "بيكتين يغذي بكتيريا القولون"),
    "كمثرى": ("1 حبة", 101, 1, "سوربيتول طبيعي يلين الأمعاء"),
    "موزة": ("1 حبة صغيرة", 89, 1, "ماغنيسيوم ينظم الأمعاء"),
    "برتقالة": ("1 حبة", 62, 1, "فيتامين C + يساعد امتصاص الحديد"),
    "كيوي": ("1 حبة", 61, 1, "فيتامين C + يحسن النوم + يساعد القولون"),
    "رمانة نصف": ("نصف حبة", 53, 1, "مضاد التهاب يهدئ القولون"),
    "تمرتان": ("2 حبة", 66, 0.4, "طاقة طبيعية سريعة"),
    "لوز نيئ": ("20 جم", 120, 4, "دهون صحية ترفع معدل الحرق"),
    "حليب دافئ خالي الدسم": ("200 مل", 70, 7, "تريبتوفان — ينوم ويهدئ"),
    "لبن رايب": ("كوب 200مل", 120, 7, "بروبيوتيك طبيعي مصري"),
}

# ══════════════════════════════════════════════════════════════
# WEEKLY PLAN GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_plan(data: dict) -> list:
    """يولّد خطة أسبوعية بناءً على بيانات المريض والأعراض"""
    symptoms = data.get("symptoms", [])
    has_colon   = "قولون" in symptoms or "ibs" in symptoms
    has_constip = "إمساك" in symptoms or "constipation" in symptoms
    has_diabetes = "سكري" in symptoms or "diabetes" in symptoms
    has_cardiac  = "قلب" in symptoms or "cardiac" in symptoms
    has_kidney   = "كلى" in symptoms or "kidney" in symptoms
    low_metabolism = "حرق بطيء" in symptoms or "metabolism" in symptoms

    # الوجبات الأساسية حسب الأعراض
    breakfasts = [
        ("فول مدمس بزيت الزيتون", "بيضتان مسلوقتان", "خبز أسمر"),
        ("شوفان بالحليب", "تفاحة بالقشر"),
        ("بيض أومليت بالخضار", "خبز أسمر"),
        ("فول مع طحينة وليمون", "خبز أسمر"),
        ("شوفان بالموز والقرفة", "لوز نيئ"),
        ("فول مدمس بزيت الزيتون", "بيضتان مسلوقتان", "طماطم وخيار"),
        ("شوفان بالحليب", "كيوي"),
    ]
    lunches = [
        ("صدر دجاج مشوي", "أرز بني", "سلطة خضار نيئة"),
        ("سمك بلطي مشوي", "بطاطا حلوة مشوية", "كوسة مشوية"),
        ("فخذ دجاج فرن بدون جلد", "برغل مطبوخ", "سلطة فتوش"),
        ("كبدة دجاج مشوية", "أرز بني", "ملوخية بزيت الزيتون"),
        ("سمكة بلطي كاملة مشوية", "بطاطا مسلوقة", "سلطة خضار نيئة"),
        ("صدر دجاج فرن بالخضار", "أرز بني", "سلطة خضار نيئة"),
        ("سمك بلطي مشوي", "برغل مطبوخ", "سلطة فتوش"),
    ]
    dinners = [
        ("شوربة عدس أحمر", "خبز أسمر"),
        ("عدس مطهو بجزر وكرفس", "خبز أسمر"),
        ("شوربة خضار", "جبن قريش"),
        ("حمص بطحينة", "خبز أسمر", "طماطم وخيار"),
        ("شوربة عدس أصفر", "خبز أسمر"),
        ("عدس مطهو بجزر وكرفس", "جبن قريش"),
        ("كشري مصري", "سلطة خضار نيئة") if not has_colon else ("شوربة عدس أحمر", "خبز أسمر"),
    ]
    snacks = [
        "تفاحة بالقشر",
        "لوز نيئ",
        "برتقالة",
        "تمرتان",
        "كيوي",
        "رمانة نصف",
        "موزة",
    ]
    before_sleep = [
        "زبادي يوناني سادة",
        "كمثرى",
        "حليب دافئ خالي الدسم",
        "زبادي يوناني سادة",
        "تفاحة بالقشر",
        "زبادي يوناني سادة",
        "موزة",
    ]

    days_ar = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
    plan = []

    for i in range(7):
        day_meals = []
        total_cal = 0
        total_prot = 0

        def add_meal(meal_name, items):
            nonlocal total_cal, total_prot
            for item in items:
                if item in FOODS:
                    qty, cal, prot, note = FOODS[item]
                    day_meals.append((meal_name, item, qty, cal, prot, note))
                    total_cal += cal
                    total_prot += prot
                    meal_name = ""  # show meal name only for first item

        add_meal("🌅 فطار", breakfasts[i])
        add_meal("🍎 سناك", [snacks[i]])
        add_meal("☀️ غداء", lunches[i])
        add_meal("🌙 عشاء", dinners[i])
        add_meal("🌛 قبل النوم", [before_sleep[i]])

        plan.append({
            "day": f"اليوم {i+1} — {days_ar[i]}",
            "meals": day_meals,
            "total_cal": total_cal,
            "total_prot": total_prot,
        })

    return plan


# ══════════════════════════════════════════════════════════════
# PDF BUILDER
# ══════════════════════════════════════════════════════════════

def build_pdf(data: dict, out_path: str):
    name    = data.get("name", "المريض")
    age     = data.get("age", "—")
    height  = data.get("height", "—")
    weight  = data.get("weight", "—")
    fat_pct = data.get("fat_pct", "—")
    bmi     = data.get("bmi", "—")
    tdee    = data.get("tdee", "—")
    goal_cal = data.get("goal_cal", 1350)
    symptoms = data.get("symptoms", [])
    notes   = data.get("notes", "")

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        rightMargin=1.8*cm, leftMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        title=f"NutraX — {name}",
        author="NutraX",
    )

    # ── Styles ──
    S_TITLE  = style("title",  size=22, color=C_BLUE,  bold=True, align=TA_CENTER, space_after=8)
    S_SUB    = style("sub",    size=14, color=C_GREEN, bold=False, align=TA_CENTER, space_after=4)
    S_H1     = style("h1",     size=15, color=C_BLUE,  bold=True,  space_after=6)
    S_H2     = style("h2",     size=13, color=C_GREEN, bold=True,  space_after=4)
    S_BODY   = style("body",   size=11, color=C_DGRAY, space_after=4)
    S_SMALL  = style("small",  size=10, color=C_DGRAY, space_after=3)
    S_CENTER = style("center", size=11, color=C_DGRAY, align=TA_CENTER, space_after=4)
    S_RED    = style("red",    size=11, color=C_RED,   bold=True,  space_after=4)

    def tbl_style_base(extra=None):
        base = [
            ("FONTNAME",    (0,0), (-1,-1), "Amiri"),
            ("FONTNAME",    (0,0), (-1, 0), "AmiriBold"),
            ("FONTSIZE",    (0,0), (-1,-1), 10),
            ("FONTSIZE",    (0,0), (-1, 0), 11),
            ("ALIGN",       (0,0), (-1,-1), "RIGHT"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("TEXTCOLOR",   (0,0), (-1, 0), colors.white),
            ("BACKGROUND",  (0,0), (-1, 0), C_BLUE),
            ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_WHITE, C_GRAY]),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("RIGHTPADDING",(0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
        ]
        if extra:
            base.extend(extra)
        return TableStyle(base)

    story = []

    # ══ COVER ══
    story.append(sp(12))
    story.append(p("🥗  NutraX", S_TITLE))
    story.append(p("النظام الغذائي الأسبوعي المتخصص", S_SUB))
    story.append(sp(4))
    story.append(hr(C_BLUE, 2))
    story.append(sp(6))

    # Patient card
    pat_data = [
        [ar("الاسم"), ar(name), ar("العمر"), ar(f"{age} سنة"), ar("الجنس"), ar(data.get("gender","—"))],
        [ar("الطول"), ar(f"{height} سم"), ar("الوزن"), ar(f"{weight} كجم"), ar("BMI"), ar(str(bmi))],
        [ar("دهون الجسم"), ar(f"{fat_pct}%"), ar("TDEE"), ar(f"{tdee} kcal"), ar("الهدف اليومي"), ar(f"{goal_cal} kcal")],
    ]
    pat_tbl = Table(pat_data, colWidths=[2.4*cm, 2.8*cm, 2.4*cm, 2.8*cm, 2.4*cm, 2.8*cm])
    pat_tbl.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Amiri"),
        ("FONTNAME",    (0,0), (0,-1),  "AmiriBold"),
        ("FONTNAME",    (2,0), (2,-1),  "AmiriBold"),
        ("FONTNAME",    (4,0), (4,-1),  "AmiriBold"),
        ("FONTSIZE",    (0,0), (-1,-1), 10),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND",  (0,0), (0,-1),  C_LBLUE),
        ("BACKGROUND",  (2,0), (2,-1),  C_LBLUE),
        ("BACKGROUND",  (4,0), (4,-1),  C_LBLUE),
        ("TEXTCOLOR",   (0,0), (0,-1),  C_BLUE),
        ("TEXTCOLOR",   (2,0), (2,-1),  C_BLUE),
        ("TEXTCOLOR",   (4,0), (4,-1),  C_BLUE),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#aaaaaa")),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [C_WHITE, C_GRAY]),
    ]))
    story.append(pat_tbl)
    story.append(sp(8))

    # Symptoms
    if symptoms:
        story.append(p("الأعراض والحالات المرضية:", S_H1))
        symp_str = "  |  ".join(symptoms)
        story.append(p(symp_str, S_BODY))
        story.append(sp(4))

    if notes:
        story.append(p(f"ملاحظات: {notes}", S_SMALL))

    story.append(hr(C_GREEN))
    story.append(PageBreak())

    # ══ CLINICAL NOTES ══
    story.append(p("📋 التشخيص التغذوي والتدخل الغذائي", S_H1))
    story.append(sp(4))

    clinical_rows = [[ar("الحالة"), ar("التدخل الغذائي المخصص")]]
    clin_map = {
        "قولون":        "Low-FODMAP جزئي — تجنب الخبز الأبيض والألبان كاملة الدسم — شوفان + عدس + خضار مطبوخة",
        "إمساك":        "ألياف 28-35 جم/يوم + 8 أكواب ماء + زبادي يوناني ليلياً + تفاح/كمثرى بالقشر يومياً",
        "حرق بطيء":    "فطار إلزامي + بروتين في كل وجبة + قرفة وكركم + مشي 30 دقيقة بعد الغداء",
        "سكري":         "كارب معقد فقط + توزيع السعرات على 5 وجبات + تجنب السكريات البسيطة",
        "قلب":          "صوديوم أقل من 2000 مجم + دهون مشبعة أقل من 7% + سمك مرتين أسبوعياً",
        "كلى":          "بروتين 0.6-0.8 جم/كجم + تقليل البوتاسيوم والفوسفور + سوائل حسب إخراج البول",
        "سمنة":         "عجز 500-750 kcal + بروتين 25-30% + ألياف 30-38 جم/يوم",
    }
    for symp in symptoms:
        for key, val in clin_map.items():
            if key in symp:
                clinical_rows.append([ar(f"⚕ {symp}"), ar(val)])

    if len(clinical_rows) > 1:
        clin_tbl = Table(clinical_rows, colWidths=[4*cm, 13.4*cm])
        clin_tbl.setStyle(tbl_style_base([
            ("BACKGROUND", (0,1), (0,-1), C_LBLUE),
            ("TEXTCOLOR",  (0,1), (0,-1), C_BLUE),
            ("FONTNAME",   (0,1), (0,-1), "AmiriBold"),
        ]))
        story.append(clin_tbl)
        story.append(sp(8))

    story.append(hr(C_BLUE))

    # ══ RULES ══
    story.append(p("✅ المسموح  |  🚫 الممنوع", S_H1))
    story.append(sp(4))

    allowed = [
        "فول مدمس • عدس • شوربات • سمك مشوي",
        "دجاج مشوي أو فرن (بدون جلد) • بيض",
        "شوفان • خبز أسمر • أرز بني • برغل",
        "زيت زيتون (ملعقة كبيرة) • طحينة بكميات صغيرة",
        "زبادي يوناني سادة • جبن قريش • لبن رايب",
        "ملوخية • كوسة • جزر • خضار مطبوخة",
        "شاي أخضر • ماء دافئ بالليمون صباحاً",
    ]
    forbidden = [
        "الخبز الأبيض والعيش الفينو",
        "البهارات الحارة — تستفز القولون",
        "الدهانة والسمن والأكل المقلي",
        "المشروبات الغازية والعصائر المعلبة",
        "الكافيين الزائد (أكثر من كوب يومياً)",
        "البقوليات بكميات كبيرة دفعة واحدة",
        "الحلويات والسكريات المضافة",
    ]
    rules_rows = [[ar("✅ مسموح — بحرية"), ar("🚫 ممنوع أو مقلل")]]
    for a, f in zip(allowed, forbidden):
        rules_rows.append([ar(a), ar(f)])

    rules_tbl = Table(rules_rows, colWidths=[8.7*cm, 8.7*cm])
    rules_tbl.setStyle(tbl_style_base([
        ("BACKGROUND",  (0,0), (0, 0), C_GREEN),
        ("BACKGROUND",  (1,0), (1, 0), C_RED),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_LGREEN, C_WHITE]),
        ("TEXTCOLOR",   (0,1), (0,-1), C_GREEN),
        ("TEXTCOLOR",   (1,1), (1,-1), C_RED),
    ]))
    story.append(rules_tbl)
    story.append(sp(8))
    story.append(hr(C_GREEN))
    story.append(PageBreak())

    # ══ WEEKLY PLAN ══
    story.append(p("📅 الجدول الغذائي الأسبوعي التفصيلي", S_H1))
    story.append(sp(6))

    plan = generate_plan(data)
    days_colors = [C_LBLUE, C_LGREEN, C_WHITE, C_LBLUE, C_LGREEN, C_WHITE, C_LBLUE]

    for i, day in enumerate(plan):
        story.append(p(day["day"], S_H2))

        meal_rows = [[ar("الوجبة"), ar("الأكل"), ar("الكمية"), ar("kcal"), ar("بروتين"), ar("ملاحظة")]]
        for meal, food, qty, cal, prot, note in day["meals"]:
            meal_rows.append([ar(meal), ar(food), ar(qty), ar(str(cal)), ar(f"{prot}ج"), ar(note)])
        # Total row
        meal_rows.append([
            ar("الإجمالي"), ar(""),
            ar(""),
            ar(f"{day['total_cal']} kcal"),
            ar(f"{day['total_prot']}ج"),
            ar(""),
        ])

        col_w = [1.8*cm, 3.8*cm, 2.6*cm, 1.6*cm, 1.4*cm, 6.2*cm]
        meal_tbl = Table(meal_rows, colWidths=col_w)
        meal_tbl.setStyle(TableStyle([
            ("FONTNAME",    (0,0), (-1,-1), "Amiri"),
            ("FONTNAME",    (0,0), (-1, 0), "AmiriBold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9.5),
            ("FONTSIZE",    (0,0), (-1, 0), 10),
            ("ALIGN",       (0,0), (-1,-1), "RIGHT"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("TEXTCOLOR",   (0,0), (-1, 0), colors.white),
            ("BACKGROUND",  (0,0), (-1, 0), C_BLUE),
            ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, C_GRAY]),
            ("BACKGROUND",  (0,-1), (-1,-1), C_LBLUE),
            ("FONTNAME",    (0,-1), (-1,-1), "AmiriBold"),
            ("TEXTCOLOR",   (3,-1), (3,-1),  C_RED),
            ("TEXTCOLOR",   (4,-1), (4,-1),  C_GREEN),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
            ("RIGHTPADDING",(0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(meal_tbl)
        story.append(sp(8))

        if i < 6:
            story.append(hr(colors.HexColor("#dddddd"), 0.5))
            story.append(sp(4))

    story.append(PageBreak())

    # ══ PROTOCOLS ══
    story.append(p("💧 بروتوكول الماء والنشاط", S_H1))
    story.append(sp(4))

    water_rows = [
        [ar("💧 بروتوكول الماء"), ar("🏃 النشاط المقترح")],
        [ar("كوب ماء دافئ + نصف ليمون فور الاستيقاظ"), ar("مشي 30 دقيقة يومياً بعد الغداء — الأفضل للقولون")],
        [ar("كوب ماء قبل كل وجبة بـ 30 دقيقة"), ar("لا تجلس مباشرة بعد الأكل — تحرك 10 دقائق")],
        [ar("8 أكواب على مدار اليوم (2 لتر على الأقل)"), ar("تمارين البطن الخفيفة تساعد على الأمعاء")],
        [ar("تجنب الماء البارد جداً مع الأكل"), ar("قم وتحرك 5 دقائق كل ساعة إن كنت جالساً")],
    ]
    water_tbl = Table(water_rows, colWidths=[8.7*cm, 8.7*cm])
    water_tbl.setStyle(tbl_style_base([
        ("BACKGROUND", (0,0), (0,0), C_BLUE),
        ("BACKGROUND", (1,0), (1,0), C_GREEN),
    ]))
    story.append(water_tbl)
    story.append(sp(10))

    # Gut protocol
    story.append(p("🦠 بروتوكول القولون والإمساك", S_H1))
    gut_items = [
        "زبادي يوناني سادة كل ليلة قبل النوم — بروبيوتيك يصلح البكتيريا",
        "تفاحة أو كمثرى بالقشر يومياً — بيكتين يلين الأمعاء طبيعياً",
        "كمون + شبت في الطهي — يقلل الغازات ويهدئ القولون",
        "شاي النعنع بعد الغداء مباشرة — مضاد تشنج طبيعي",
        "المضغ الجيد يقلل 50% من مشاكل القولون — تناول ببطء",
        "لا تشرب ماء بارد جداً مع الأكل — يسبب تقلص الأمعاء",
        "ملعقة بذور الكتان المطحونة في الزبادي صباحاً إذا استمر الإمساك",
    ]
    gut_rows = [[ar("🦠 البروتوكول")]] + [[ar(f"• {item}")] for item in gut_items]
    gut_tbl = Table(gut_rows, colWidths=[17.4*cm])
    gut_tbl.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Amiri"),
        ("FONTNAME",    (0,0), (-1, 0), "AmiriBold"),
        ("FONTSIZE",    (0,0), (-1,-1), 10),
        ("ALIGN",       (0,0), (-1,-1), "RIGHT"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("TEXTCOLOR",   (0,0), (0, 0), colors.white),
        ("BACKGROUND",  (0,0), (0, 0), C_RED),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_LRED, colors.white]),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
    ]))
    story.append(gut_tbl)
    story.append(sp(10))

    # Metabolism
    story.append(p("🔥 رفع معدل الحرق", S_H1))
    met_items = [
        "وجبة الصباح إلزامية خلال ساعة من الاستيقاظ — إغلاقها يخفض الحرق 20%",
        "البروتين في كل وجبة (بيض / دجاج / سمك / عدس) — هضمه يحرق 25% من سعراته",
        "البهارات الآمنة للقولون: كركم + قرفة + زنجبيل — ترفع الحرق 10-12%",
        "الشاي الأخضر كوب يومياً — كاتيكين يرفع الحرق 4-6%",
        "لا تنام جائعاً ولا ممتلئاً — الإفراط في التقليل يوقف الحرق",
        "الجلوس المستمر يقلل الحرق — قم وتحرك 5 دقائق كل ساعة",
    ]
    met_rows = [[ar("🔥 رفع معدل الحرق")]] + [[ar(f"• {item}")] for item in met_items]
    met_tbl = Table(met_rows, colWidths=[17.4*cm])
    met_tbl.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Amiri"),
        ("FONTNAME",    (0,0), (0, 0),  "AmiriBold"),
        ("FONTSIZE",    (0,0), (-1,-1), 10),
        ("ALIGN",       (0,0), (-1,-1), "RIGHT"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("TEXTCOLOR",   (0,0), (0, 0), colors.white),
        ("BACKGROUND",  (0,0), (0, 0), C_ORANGE),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_LORANG, colors.white]),
        ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
    ]))
    story.append(met_tbl)
    story.append(sp(14))

    # Footer
    story.append(hr(C_BLUE))
    story.append(p(f"NutraX | النظام الغذائي مُعَد خصيصاً لـ {name} بتاريخ {__import__('datetime').date.today().strftime('%d/%m/%Y')} | يُراجَع بعد 4 أسابيع", S_CENTER))

    doc.build(story)
    print(f"PDF generated: {out_path}")


# ══════════════════════════════════════════════════════════════
# MAIN — للاختبار
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    test_data = {
        "name": "محمد أحمد",
        "age": 28,
        "gender": "ذكر",
        "height": 166,
        "weight": 92.2,
        "fat_pct": 46.9,
        "bmi": 33.4,
        "tdee": 2593,
        "goal_cal": 1350,
        "symptoms": ["قولون عصبي", "إمساك مزمن", "حرق بطيء", "سمنة"],
        "notes": "دهون البطن: 15.2 (Very High)",
    }
    build_pdf(test_data, "/home/claude/test_meal_plan.pdf")

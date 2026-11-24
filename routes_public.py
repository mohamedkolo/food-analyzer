# -*- coding: utf-8 -*-
"""The pages a visitor can reach without an account.

The landing page, the public food tables, robots.txt and sitemap.xml. This is
the whole crawlable surface of the site -- everything else sits behind the
login wall and is listed in _CRAWL_BLOCKED so search engines do not waste
their time on redirects.
"""

from flask import Blueprint, Response, render_template, request, session, redirect
import json
from datetime import datetime

import food_data
from core import site_origin
from payments import PRICING

bp = Blueprint("public", __name__)

# ═══════════════════════════════════════════════
# SEO: robots.txt + sitemap.xml
# ═══════════════════════════════════════════════
# Everything indexable is listed here in one place; PUBLIC_PAGES feeds both
# the sitemap and the canonical tags. site_origin() lives in core, because
# every template uses it.

# path -> how often it changes, priority
PUBLIC_PAGES = [
    ("/", "weekly", "1.0"),
    ("/pricing", "monthly", "0.8"),
    ("/foods", "weekly", "0.7"),
    ("/whey", "monthly", "0.6"),
    ("/terms", "yearly", "0.3"),
    ("/privacy", "yearly", "0.3"),
]

# everything behind the login wall -- crawling these only ever yields a redirect
# /p/ = جداول العملاء بالاسم والوزن والحالات المرضية. مش للفهرسة أبداً.
_CRAWL_BLOCKED = ["/p/", "/followups", "/dashboard", "/my-plan", "/my-plans-history", "/generate",
                  "/preview", "/planner", "/patients", "/saved", "/analyzer",
                  "/knowledge", "/clinical", "/daily-tips", "/messages",
                  "/settings", "/change-password", "/history", "/onboarding",
                  "/subscription-required", "/admin", "/api", "/webhook",
                  "/push", "/track", "/login", "/logout", "/lang"]


@bp.route("/robots.txt")
def robots_txt():
    lines = ["User-agent: *"]
    lines += [f"Disallow: {p}" for p in _CRAWL_BLOCKED]
    lines += ["Allow: /", f"Sitemap: {site_origin()}/sitemap.xml", ""]
    return Response("\n".join(lines), mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap_xml():
    origin = site_origin()
    today = datetime.now().strftime("%Y-%m-%d")
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, freq, prio in PUBLIC_PAGES:
        out += [f"  <url><loc>{origin}{path}</loc>",
                f"    <lastmod>{today}</lastmod>",
                f"    <changefreq>{freq}</changefreq>",
                f"    <priority>{prio}</priority></url>"]
    # one entry per food, plus the category listings
    for key in food_data.CATEGORIES:
        out += [f"  <url><loc>{origin}/foods?cat={key}</loc>",
                f"    <changefreq>monthly</changefreq>",
                f"    <priority>0.5</priority></url>"]
    for f in food_data.FOODS:
        out += [f"  <url><loc>{origin}/foods/{f['slug']}</loc>",
                f"    <changefreq>yearly</changefreq>",
                f"    <priority>0.6</priority></url>"]
    out.append("</urlset>")
    return Response("\n".join(out), mimetype="application/xml")


# ── public, crawlable food pages (no login: this is the SEO surface) ──
_SAFE_LABELS = {
    "dm":    ("مناسب للسكري", "Diabetes-friendly"),
    "htn":   ("مناسب لضغط الدم", "Blood-pressure friendly"),
    "ckd":   ("مناسب لمرضى الكلى", "Kidney-friendly"),
    "ibs":   ("لطيف على القولون", "Gut-gentle"),
    "heart": ("مناسب للقلب", "Heart-friendly"),
    "keto":  ("مناسب للكيتو", "Keto-friendly"),
}


@bp.route("/foods")
def public_foods():
    """The food index.

    Landing on the whole table at once was a wall of numbers nobody reads. Without a
    category the page is now a search box over the whole set plus the fourteen
    categories to browse; pick one and you get that category's table on its
    own. Every food still has its own page and they are all in the sitemap, so
    narrowing the index costs nothing in search.
    """
    lang = session.get("lang", "ar")
    cat = (request.args.get("cat") or "").strip() or None
    if cat and cat not in food_data.CATEGORIES:
        cat = None

    counts = {k: len(food_data.foods_in(k)) for k in food_data.CATEGORIES}
    rows = food_data.foods_in(cat) if cat else []

    # a few worth surfacing, so the index says something instead of nothing
    every = food_data.FOODS
    highlights = [
        ("protein", sorted(every, key=lambda f: -f["p"])[:8]),
        ("light", sorted([f for f in every if f["cal"] > 0],
                         key=lambda f: f["cal"])[:8]),
        ("lowcarb", sorted([f for f in every if f["p"] >= 8],
                           key=lambda f: (f["c"], -f["p"]))[:8]),
    ]

    # the whole set, small, for the client-side search box
    index = [{"s": f["slug"], "n": f["n"], "e": f["en"],
              "c": f["cal"], "p": f["p"], "k": f["cat"]} for f in every]

    return render_template("public_foods.html", lang=lang,
                           categories=food_data.CATEGORIES, counts=counts,
                           rows=rows, active_cat=cat,
                           cat_label=food_data.category_name(cat, lang) if cat else None,
                           highlights=highlights, total=len(every),
                           search_index=json.dumps(index, ensure_ascii=False),
                           canonical_url=site_origin() + "/foods"
                           + (f"?cat={cat}" if cat else ""))


@bp.route("/foods/<slug>")
def public_food(slug):
    lang = session.get("lang", "ar")
    food = food_data.get_food(slug)
    if not food:
        return render_template("404.html", lang=lang), 404
    related = [f for f in food_data.foods_in(food["cat"]) if f["slug"] != slug][:12]
    labels = [_SAFE_LABELS[k][0 if lang == "ar" else 1]
              for k in food.get("safe", []) if k in _SAFE_LABELS]
    return render_template("public_food.html", lang=lang, food=food,
                           cat_label=food_data.category_name(food["cat"], lang),
                           related=related, safe_labels=labels,
                           canonical_url=f"{site_origin()}/foods/{slug}")


@bp.route("/")
def landing():
    """The public front door, for signed-in visitors too.

    ‏بموافقة الدكتور (٢٥ نوفمبر): المشهد يظهر حتى لمسجّلي الدخول،
    وزر «خطتي» في الشريط بيرجّعهم لحسابهم بدل التحويل التلقائي.
    """
    return render_template("landing.html", lang=session.get("lang", "ar"),
                           pricing=PRICING, signed_in=("uid" in session))


# "/" still answers POST: the login form used to live at the root, so old
# bookmarks and any cached PWA shell keep working.


# ── محلل الواي بروتين ───────────────────────────────────────────────

def _whey_form(form):
    """الأرقام من الفورم. الخانة الفاضية = None، مش صفر -- عشان تبان ناقصة."""
    import whey_analyzer as W

    def num(name):
        raw = (form.get(name) or "").strip().replace(",", ".")
        raw = raw.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789."))
        try:
            return float(raw) if raw else None
        except ValueError:
            return None
    return {"serving_g": num("serving_g"), "protein_g": num("protein_g"),
            "unit": "serving" if form.get("unit") == "serving" else "per100",
            "mode": "summary" if form.get("mode") == "summary" else "profile",
            "summary": {k: num(k) for k in ("total_aa_g", "eaa_g", "bcaa_g", "leucine_g")},
            "added": [a for a in (form.get("added") or "").split(",") if a.strip()][:6],
            "kind": form.get("kind") if form.get("kind") in W.KINDS else "whey",
            "sugar_g": num("sugar_g"),
            "amino": {k: num(k) for k in W.AMINO}}


# ‏النوع بيتختار قبل الصورة (طلب صاحب المشروع): الواي بأنواعه بيتقيّم
# بمعادلاته، وباقي المكملات ببنود supplements.py.
WHEY_KINDS = (("isolate", "واي أيزوليت", "Whey Isolate", "fa-droplet"),
              ("whey", "واي (Concentrate / Blend)", "Whey (Concentrate / Blend)", "fa-bottle-water"),
              ("mass", "ماس جينر", "Mass Gainer", "fa-weight-hanging"))


def _kind(value):
    import supplements as SP
    return value if value in dict((k[0], 1) for k in WHEY_KINDS) or value in SP.TYPES else None


def _whey_page(values=None, result=None, error=None, demo=False, kind=None,
               supp_values=None, supp_result=None):
    import whey_analyzer as W
    import supplements as SP
    # ‏المسجّل بيشوف الصفحة بقايمته الجانبية -- بيوصلها منها، ومن غيرها
    # كان بيتنقل لهيدر الزوار ويتوه. الزائر بالهيدر العام.
    from core import get_user_by_id
    user = get_user_by_id(session["uid"]) if session.get("uid") else None
    import whey_vision
    return render_template("whey.html", lang=session.get("lang", "ar"), user=user,
                           vision=whey_vision.available(),
                           amino=W.AMINO, amino_ar=W.AMINO_AR, eaa=W.EAA, bcaa=W.BCAA, fortify=list(W.FORTIFY),
                           values=values or {"unit": "per100", "amino": {}},
                           result=result, error=error, demo=demo,
                           kind=kind, whey_kinds=WHEY_KINDS, supp_types=SP.TYPES,
                           supp=SP.TYPES.get(kind), supp_values=supp_values or {},
                           supp_result=supp_result, sources=SP.SOURCES,
                           canonical_url=site_origin() + "/whey")


@bp.route("/whey", methods=["GET", "POST"])
def whey():
    """صورة ضهر علبة الواي -> تقييم من ١٠٠ (whey_analyzer)."""
    import whey_analyzer as W
    import supplements as SP
    if request.method != "POST":
        return _whey_page(kind=_kind(request.args.get("kind")))
    kind = _kind(request.form.get("kind")) or "whey"
    if kind in SP.TYPES:
        sv = {k: request.form.get(k) for k, *_ in SP.TYPES[kind]["fields"]}
        try:
            return _whey_page(kind=kind, supp_values=sv, supp_result=SP.evaluate(kind, sv))
        except ValueError as e:
            return _whey_page(kind=kind, supp_values=sv, error=str(e))
    values = _whey_form(request.form)
    extra = {"kind": kind, "sugar_g": values["sugar_g"]}
    try:
        # ‏جدول أحماض فاضي = مفيش أحماض مكتوبة: نفس الملخص الفاضي -- نسبة
        # البروتين والسكر والمكونات بدل "مفيش أرقام" ومفيش نتيجة خالص.
        # صاحب المشروع دوس احسب على ماس جينر بالحصة والبروتين بس ووقف هنا.
        if values["mode"] == "summary" or not any(values["amino"].values()):
            sm = values["summary"]
            result = W.analyze_summary(values["serving_g"], values["protein_g"], sm["total_aa_g"],
                                       sm["eaa_g"], sm["bcaa_g"], sm["leucine_g"], values["added"], **extra)
        else:
            result = W.analyze(values["serving_g"], values["protein_g"],
                               values["amino"], values["unit"], values["added"], **extra)
    except ValueError as e:
        return _whey_page(values=values, error=str(e), kind=kind)
    return _whey_page(values=values, result=result, kind=kind)


@bp.route("/whey/demo")
def whey_demo():
    """العلبة التجريبية من صاحب المشروع -- نتيجتها المتوقعة ١٠٠ ممتاز."""
    import whey_analyzer as W
    values = {"serving_g": W.DEMO["serving_g"], "protein_g": W.DEMO["protein_g"],
              "unit": "per100", "mode": "profile", "summary": {}, "added": [],
              "amino": dict(W.DEMO["amino"])}
    result = W.analyze(values["serving_g"], values["protein_g"], values["amino"], "per100")
    return _whey_page(values=values, result=result, demo=True, kind="whey")


@bp.route("/whey/parse", methods=["POST"])
def whey_parse():
    """نص الصورة (اتقرا في موبايل المستخدم) -> أرقام. الصورة نفسها مابتوصلش هنا."""
    import whey_analyzer as W
    from flask import jsonify
    body = request.get_json(silent=True) or {}
    passes = body.get("passes")
    if isinstance(passes, list):
        return jsonify(W.parse_passes([str(p)[:20000] for p in passes[:4]]))
    return jsonify(W.parse_label((body.get("text") or "")[:20000]))


@bp.route("/whey/read", methods=["POST"])
def whey_read():
    """الصورة نفسها -> أرقام بالذكاء الاصطناعي، لو فيه مفتاح على السيرفر
    (whey_vision). من غيره 503 والصفحة بتقرا في الموبايل."""
    import whey_vision
    from flask import jsonify
    if not whey_vision.available():
        return jsonify({"ok": False, "fallback": True}), 503
    f = request.files.get("image")
    if not f:
        return jsonify({"ok": False, "fallback": True, "error": "no image"}), 400
    try:
        data = whey_vision.read_label(f.read(), f.mimetype, _kind(request.form.get("kind")) or "whey")
    except whey_vision.VisionError as e:
        return jsonify({"ok": False, "fallback": True, "error": str(e)}), 502
    data["ok"] = True
    return jsonify(data)


# ── الباركود: صورة -> رقم، ورقم -> منتج ─────────────────────────────

@bp.route("/barcode/read", methods=["POST"])
def barcode_read():
    """صورة باركود -> رقمه (barcode_scan). محلل المكملات ومحلل الطعام بيستخدموها."""
    import barcode_scan
    from flask import jsonify
    f = request.files.get("image")
    code = barcode_scan.decode(f.read(barcode_scan.MAX_BYTES + 1) if f else b"")
    if not code:
        return jsonify({"ok": False, "error": "مقدرناش نقرا الباركود. صوّره قريب ومستقيم، أو اكتب الرقم اللي تحته."}), 422
    return jsonify({"ok": True, "code": code})


@bp.route("/whey/barcode/<code>")
def whey_barcode(code):
    """رقم الباركود -> اللي Open Food Facts عارفه عن المكمل."""
    import barcode_scan
    from flask import jsonify
    code = barcode_scan.clean_code(code)
    if len(code) < 8:
        return jsonify({"ok": False, "error": "باركود غير صالح"}), 400
    try:
        product = barcode_scan.fetch_product(code)
    except Exception as e:  # noqa: BLE001
        print("[barcode] fetch error: %s" % type(e).__name__)
        return jsonify({"ok": False, "error": "تعذر الاتصال بقاعدة بيانات الباركود"}), 502
    if not product:
        return jsonify({"ok": False, "error": "الباركود اتقرا، لكن المنتج مش موجود في قاعدة البيانات. مفيش أرقام اتخمنت. اكتب بيانات العبوة أو استخدم قراءة الملصق الاختيارية."}), 404
    return jsonify({"ok": True, "code": code, "product": barcode_scan.supplement_fields(product)})

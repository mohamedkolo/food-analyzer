# -*- coding: utf-8 -*-
"""The pages a visitor can reach without an account.

The landing page, the public food tables, robots.txt and sitemap.xml. This is
the whole crawlable surface of the site -- everything else sits behind the
login wall and is listed in _CRAWL_BLOCKED so search engines do not waste
their time on redirects.
"""

from flask import Blueprint, Response, render_template, request, session, redirect
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
    ("/terms", "yearly", "0.3"),
    ("/privacy", "yearly", "0.3"),
]

# everything behind the login wall -- crawling these only ever yields a redirect
_CRAWL_BLOCKED = ["/dashboard", "/my-plan", "/my-plans-history", "/generate",
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
    lang = session.get("lang", "ar")
    cat = (request.args.get("cat") or "").strip() or None
    if cat and cat not in food_data.CATEGORIES:
        cat = None
    rows = food_data.foods_in(cat)
    keys = [cat] if cat else list(food_data.CATEGORIES)
    grouped = [(k, [f for f in rows if f["cat"] == k]) for k in keys]
    grouped = [(k, v) for k, v in grouped if v]
    return render_template("public_foods.html", lang=lang,
                           categories=food_data.CATEGORIES, grouped=grouped,
                           active_cat=cat, total=len(food_data.FOODS),
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
    """The public front door. Signed-in visitors go straight to their own page."""
    if "uid" in session:
        return redirect("/dashboard")
    return render_template("landing.html", lang=session.get("lang", "ar"),
                           pricing=PRICING)


# "/" still answers POST: the login form used to live at the root, so old
# bookmarks and any cached PWA shell keep working.

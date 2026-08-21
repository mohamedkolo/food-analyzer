# -*- coding: utf-8 -*-
"""Building and editing a plan: the staff side.

Generating a week, previewing it, swapping a meal, picking one from a list,
editing the text by hand, and saving or downloading the result.

Everything here is staff-only. The logic these routes call lives in
plan_engine; this module is the request handling around it.

The meals sent back to the browser carry both forms: `meal` is the stored
Arabic, which is what gets saved and what the safety filtering matches
against, and `display` is what the reader sees. Never save `display`.
"""

import io
import json
import random
from datetime import datetime

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   send_file, session)

import meal_extra
from core import (
    DIET_PLAN_TYPES, cur_lang, db_row, db_rows, db_run, filter_by_conditions,
    get_meal_pool, get_user_by_id, log_error, staff_required, translate_meal,
)
from plan_engine import (
    build_pdf, filter_carbs, filter_meals_by_exclusions,
    generate_weekly_plan, parse_user_exclusions,
)
from zigzag import ZIGZAG_MODES

bp = Blueprint("plans", __name__)

@bp.route("/saved")
@staff_required
def saved():
    u = get_user_by_id(session["uid"])
    plans = db_rows("SELECT * FROM saved_plans WHERE user_id=? ORDER BY created_at DESC", (session["uid"],))
    return render_template("saved.html", user=u, lang=session.get("lang","ar"), plans=plans)

@bp.route("/save_plan", methods=["POST"])
@staff_required
def save_plan():
    n = request.form.get("plan_name", "خطتي")
    pt = request.form.get("plan_type", "personal")
    db_run("INSERT INTO saved_plans (user_id,name,plan_data,plan_type) VALUES (?,?,?,?)",
           (session["uid"], n, json.dumps(dict(request.form)), pt))
    return redirect("/saved")

@bp.route("/delete_plan/<int:pid>", methods=["POST"])
@staff_required
def delete_plan(pid):
    db_run("DELETE FROM saved_plans WHERE id=? AND user_id=?", (pid, session["uid"]))
    return redirect("/saved")

@bp.route("/saved/<int:pid>/open")
@staff_required
def open_saved_plan(pid):
    """فتح خطة محفوظة في صفحة المعاينة"""
    row = db_row("SELECT * FROM saved_plans WHERE id=? AND user_id=?", (pid, session["uid"]))
    if not row:
        return redirect("/saved")
    try:
        pd = json.loads(row.get("plan_data") or "{}")
        data = pd.get("data")
        plan = pd.get("plan")
        if data and plan:
            session["pdf_data"] = data
            session["current_plan"] = plan
            session.pop("current_request_id", None)
            return redirect("/preview")
    except Exception as _e:
        print(f"open saved plan error: {_e}")
    return redirect("/saved")

@bp.route("/saved/<int:pid>/pdf")
@staff_required
def saved_plan_pdf(pid):
    """تحميل PDF لخطة محفوظة"""
    row = db_row("SELECT * FROM saved_plans WHERE id=? AND user_id=?", (pid, session["uid"]))
    if not row:
        return redirect("/saved")
    try:
        pd = json.loads(row.get("plan_data") or "{}")
        data = pd.get("data")
        plan = pd.get("plan")
        if not data:
            return redirect("/saved")
        pdf_bytes = build_pdf(data, plan)
        buf = io.BytesIO(pdf_bytes); buf.seek(0)
        name = (data.get("name", "plan") or "plan").replace(" ", "_")
        return send_file(buf, as_attachment=True, download_name=f"NutraX_{name}.pdf", mimetype="application/pdf")
    except Exception as e:
        return f"خطأ في توليد PDF: {e}", 500

@bp.route("/generate", methods=["GET","POST"])
@staff_required
def generate():
    u = get_user_by_id(session["uid"])
    if request.method == "POST":
        data = {
            "name": request.form.get("name",""), "age": request.form.get("age",""),
            "gender": request.form.get("gender",""), "height": request.form.get("height",""),
            "weight": request.form.get("weight",""), "fat_pct": request.form.get("fat_pct",""),
            "bmi": request.form.get("bmi",""), "tdee": request.form.get("tdee",""),
            "goal_cal": request.form.get("goal_cal","1400"),
            "activity_level": request.form.get("activity_level","regular"),
            "protein_per_kg": request.form.get("protein_per_kg","1.6"),
            "fat_pct_cal": request.form.get("fat_pct_cal","30"),
            "goal_type": request.form.get("goal_type","weight_loss"),
            "culture": request.form.get("culture","مصري"),
            "diet_plan_type": request.form.get("diet_plan_type","standard"),
            "symptoms": request.form.getlist("symptoms"),
            "allergies": request.form.getlist("allergies"),
            "liked_foods": request.form.get("liked_foods",""),
            "disliked_foods": request.form.get("disliked_foods",""),
            "notes": request.form.get("notes",""),
            "insulin_tdd": request.form.get("insulin_tdd",""),
            "zigzag_mode": request.form.get("zigzag_mode","off"),
        }
        session["pdf_data"] = data
        plan = generate_weekly_plan(data)
        session["current_plan"] = plan
        # ── حفظ تلقائي للخطة عشان الدكتور يلاقيها في "جداولي المحفوظة" ──
        try:
            nm = (data.get("name") or "خطة") + " - " + datetime.now().strftime("%Y-%m-%d %H:%M")
            db_run("INSERT INTO saved_plans (user_id,name,plan_data,plan_type) VALUES (?,?,?,?)",
                   (session["uid"], nm, json.dumps({"plan": plan, "data": data}, ensure_ascii=False),
                    data.get("diet_plan_type", "standard")))
        except Exception as _e:
            print(f"auto save plan error: {_e}")
        return redirect("/preview")
    return render_template("generate.html", user=u, lang=session.get("lang","ar"),
                           diet_plans=DIET_PLAN_TYPES, zigzag_modes=ZIGZAG_MODES,
                           zigzag_json=json.dumps(ZIGZAG_MODES, ensure_ascii=False))

@bp.route("/preview")
@staff_required
def preview():
    u = get_user_by_id(session["uid"])
    data = session.get("pdf_data")
    plan = session.get("current_plan")
    if not data or not plan: return redirect("/generate")
    current_request_id = session.get("current_request_id")
    return render_template("preview.html", user=u, lang=session.get("lang","ar"),
                           data=data, plan=plan, current_request_id=current_request_id)

def _filtered_meals(data, pool_key, culture=None):
    """بيرجّع وجبات pool_key بعد تطبيق: الحالة المرضية + الحساسية + المرفوض + الكيتو/لو-كارب."""
    goal = data.get("goal_type", "weight_loss")
    if goal == "cutting": goal = "weight_loss"  # التنشيف = وجبات عجز سعرات + بروتين عالي
    culture = culture or data.get("culture", "مصري")
    diet_type = data.get("diet_plan_type", "standard")
    symptoms = data.get("symptoms", []) or []
    notes = data.get("notes", "")
    disliked = data.get("disliked_foods", "")
    allergies = data.get("allergies", []) if isinstance(data.get("allergies"), list) else []
    exclusions = parse_user_exclusions(notes, disliked, allergies)
    pool = get_meal_pool(goal, culture)
    meals = list(pool.get(pool_key, []))
    if diet_type == "keto":
        try:
            from meal_extra import KETO_MEALS
            if pool_key in KETO_MEALS and KETO_MEALS[pool_key]:
                meals = list(KETO_MEALS[pool_key])
        except Exception:
            pass
    try:
        meals = filter_by_conditions(meals, symptoms) or meals
    except Exception as e:
        # Falling through here hands a patient with medical conditions the
        # unfiltered list -- exactly the food the ban exists to prevent. It
        # must never pass unnoticed.
        log_error(f"safety filtering failed for symptoms={symptoms!r}", e, critical=True)
    meals = filter_meals_by_exclusions(meals, exclusions) or meals
    if diet_type == "keto":
        meals = filter_carbs(meals, True) or meals
    elif diet_type == "low_carb":
        meals = filter_carbs(meals, False) or meals
    return meals

def _meal_display(text):
    """The meal as the current user should read it -- stored Arabic, or English."""
    if cur_lang() == "ar":
        return text
    return translate_meal(text)


@bp.route("/swap_meal", methods=["POST"])
@staff_required
def swap_meal():
    data = session.get("pdf_data")
    plan = session.get("current_plan")
    if not data or not plan: return jsonify({"ok": False}), 400
    day_idx = int(request.form.get("day_idx", 0))
    meal_type = request.form.get("meal_type", "breakfast")
    pool_key = meal_type
    if meal_type in ["meal1", "meal2", "iftar", "suhoor", "snack1", "snack2", "pre_workout", "post_workout"]:
        if meal_type in ["meal1", "iftar"]: pool_key = "lunch"
        elif meal_type in ["meal2", "suhoor"]: pool_key = "dinner"
        elif meal_type in ["snack1", "snack2"]: pool_key = "breakfast"
        elif meal_type == "pre_workout": pool_key = "breakfast"
        elif meal_type == "post_workout": pool_key = "lunch"
    meals = _filtered_meals(data, pool_key)
    if meals:
        current = plan[day_idx].get(meal_type, "")
        options = [m for m in meals if m["meal"] != current]
        if options:
            new_meal = random.choice(options)
            plan[day_idx][meal_type] = new_meal["meal"]
            session["current_plan"] = plan
            return jsonify({"ok": True, "new_meal": new_meal["meal"],
                            "display": _meal_display(new_meal["meal"])})
    return jsonify({"ok": False}), 400

@bp.route("/get_meal_options", methods=["POST"])
@staff_required
def get_meal_options():
    data = session.get("pdf_data")
    if not data: return jsonify({"ok": False, "options": []}), 400
    meal_type = request.form.get("meal_type", "breakfast")
    culture = data.get("culture", "مصري")
    diet_type = data.get("diet_plan_type", "standard")
    pool_key = meal_type
    if meal_type in ["meal1", "meal2", "iftar", "suhoor", "snack1", "snack2", "pre_workout", "post_workout"]:
        if meal_type in ["meal1", "iftar"]: pool_key = "lunch"
        elif meal_type in ["meal2", "suhoor"]: pool_key = "dinner"
        elif meal_type in ["snack1", "snack2"]: pool_key = "breakfast"
        elif meal_type == "pre_workout": pool_key = "breakfast"
        elif meal_type == "post_workout": pool_key = "lunch"
    all_options = []
    for m in _filtered_meals(data, pool_key):
        all_options.append({"meal": m["meal"], "display": _meal_display(m["meal"]),
                            "cal": m.get("cal", 0), "p": m.get("p", 0), "source": culture})
    # مطابخ تانية (مفلترة برضو) - مش للكيتو/لو-كارب عشان النشويات
    if diet_type not in ("keto", "low_carb"):
        for oc in ["مصري", "خليجي", "شامي", "مغربي", "عالمي"]:
            if oc == culture:
                continue
            for m in _filtered_meals(data, pool_key, culture=oc)[:5]:
                all_options.append({"meal": m["meal"], "display": _meal_display(m["meal"]),
                                    "cal": m.get("cal", 0), "p": m.get("p", 0), "source": oc})
    return jsonify({"ok": True, "options": all_options})

@bp.route("/replace_meal", methods=["POST"])
@staff_required
def replace_meal():
    plan = session.get("current_plan")
    if not plan: return jsonify({"ok": False, "error": "no plan"}), 400
    try:
        day_idx = int(request.form.get("day_idx", 0))
        meal_type = request.form.get("meal_type", "")
        new_meal = request.form.get("new_meal", "").strip()
        if not new_meal or not meal_type: return jsonify({"ok": False, "error": "missing data"}), 400
        if day_idx < 0 or day_idx >= len(plan): return jsonify({"ok": False, "error": "invalid day"}), 400
        plan[day_idx][meal_type] = new_meal
        session["current_plan"] = plan
        return jsonify({"ok": True, "new_meal": new_meal,
                        "display": _meal_display(new_meal)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@bp.route("/edit_meal", methods=["POST"])
@staff_required
def edit_meal():
    plan = session.get("current_plan")
    if not plan: return jsonify({"ok": False, "error": "no plan"}), 400
    try:
        day_idx = int(request.form.get("day_idx", 0))
        meal_type = request.form.get("meal_type", "")
        new_text = request.form.get("new_text", "").strip()
        if not new_text or not meal_type: return jsonify({"ok": False, "error": "missing data"}), 400
        if day_idx < 0 or day_idx >= len(plan): return jsonify({"ok": False, "error": "invalid day"}), 400
        plan[day_idx][meal_type] = new_text
        session["current_plan"] = plan
        return jsonify({"ok": True, "saved_text": new_text})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



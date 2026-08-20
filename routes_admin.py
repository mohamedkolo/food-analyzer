# -*- coding: utf-8 -*-
"""The clinic's own screens: clients, plan requests, notifications, blocking.

27 routes that were scattered through app.py rather than sitting together.
They are gathered here by what they are, not by where they happened to be
written.

Most of this is admin-only; the plan-request handling is staff, so a
nutritionist can work a request without reaching user management or the
payments page. The decorators say which is which, and the access-control
tests check it holds.
"""

import io
import json
import os
import threading
from datetime import datetime, timedelta

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   send_file, session)

from core import (
    DATABASE_URL, PRICING, _plan_name, admin_required, build_whatsapp_link,
    db_row, db_rows, db_run, get_all_notifications, get_diet_plan_info,
    get_meal_tracking, get_type_meta, get_unread_count, get_user_by_id,
    has_active_access, hp, log_error, mark_all_read, push_to_user,
    send_plan_pdf_email, staff_required,
)

bp = Blueprint("admin", __name__)

@bp.route("/admin/users")
@admin_required
def admin_users():
    u = get_user_by_id(session["uid"])
    try: all_users = db_rows("SELECT * FROM users ORDER BY id DESC")
    except: all_users = []
    return render_template("admin_users.html", user=u, lang=session.get("lang","ar"), users=all_users)


@bp.route("/admin/users/export")
@admin_required
def admin_users_export():
    """تصدير كل العملاء لملف CSV يفتح في Excel بالعربي سليم"""
    import csv
    try:
        rows = db_rows("SELECT * FROM users ORDER BY id")
    except Exception:
        rows = []
    goal_labels = {"weight_loss": "تخسيس", "muscle_gain": "زيادة عضل",
                   "bulking": "تضخيم", "cutting": "تنشيف", "maintain": "محافظة", "maintenance": "محافظة"}
    role_labels = {"client": "عميل", "nutritionist": "أخصائي", "admin": "أدمن"}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["#", "الاسم", "الإيميل", "التليفون", "البلد", "العمر", "الجنس",
                "الطول", "الوزن", "الهدف", "الدور", "الحالة", "تاريخ التسجيل"])
    for u in rows:
        created = u.get("created_at")
        created_str = created.strftime("%Y-%m-%d") if hasattr(created, "strftime") else (str(created)[:10] if created else "")
        w.writerow([
            u.get("id"), u.get("name") or "", u.get("email") or "", u.get("phone") or "",
            u.get("country") or "", u.get("age") or "", u.get("gender") or "",
            u.get("height") or "", u.get("weight") or "",
            goal_labels.get(u.get("goal"), u.get("goal") or ""),
            role_labels.get(u.get("role"), u.get("role") or ""),
            "نشط" if u.get("active", 1) else "موقوف",
            created_str,
        ])
    # BOM عشان Excel يقرأ العربي صح
    data = "\ufeff" + buf.getvalue()
    out = io.BytesIO(data.encode("utf-8"))
    out.seek(0)
    fname = f"NutraX_clients_{datetime.now().strftime('%Y-%m-%d')}.csv"
    return send_file(out, as_attachment=True, download_name=fname, mimetype="text/csv; charset=utf-8")


@bp.route("/admin/users/new", methods=["GET","POST"])
@admin_required
def admin_new_user():
    u = get_user_by_id(session["uid"])
    if request.method == "POST":
        name = request.form.get("name","")
        email = request.form.get("email","").lower()
        pw = request.form.get("password","")
        role = request.form.get("role","client")
        phone = request.form.get("phone","")
        if not email or not pw:
            return render_template("admin_new_user.html", user=u, lang=session.get("lang","ar"), error="الإيميل وكلمة السر مطلوبة")
        try:
            db_run("INSERT INTO users (name,email,password,role,phone,active) VALUES (?,?,?,?,?,1)",
                   (name, email, hp(pw), role, phone))
            return redirect("/admin/users")
        except:
            return render_template("admin_new_user.html", user=u, lang=session.get("lang","ar"), error="الإيميل موجود بالفعل")
    return render_template("admin_new_user.html", user=u, lang=session.get("lang","ar"))


@bp.route("/admin/users/<int:uid>/toggle")
@admin_required
def admin_toggle_user(uid):
    target = db_row("SELECT * FROM users WHERE id=?", (uid,))
    if target and not target.get("is_admin"):
        new_active = 0 if target.get("active", 1) else 1
        db_run("UPDATE users SET active=? WHERE id=?", (new_active, uid))
    return redirect("/admin/users")


@bp.route("/admin/users/<int:uid>/role/<role>")
@admin_required
def admin_change_role(uid, role):
    if role in ["client", "nutritionist", "admin"]:
        target = db_row("SELECT * FROM users WHERE id=?", (uid,))
        if target and not target.get("is_admin"):
            db_run("UPDATE users SET role=? WHERE id=?", (role, uid))
    return redirect("/admin/users")


@bp.route("/admin/users/<int:uid>/delete", methods=["POST"])
@admin_required
def admin_delete_user(uid):
    target = db_row("SELECT * FROM users WHERE id=?", (uid,))
    if target and not target.get("is_admin"):
        db_run("DELETE FROM users WHERE id=?", (uid,))
    return redirect("/admin/users")


@bp.route("/admin/requests")
@staff_required
def admin_requests():
    u = get_user_by_id(session["uid"])
    try: requests_list = db_rows("SELECT * FROM plan_requests ORDER BY created_at DESC LIMIT 50")
    except: requests_list = []
    return render_template("admin_requests.html", user=u, lang=session.get("lang","ar"), requests=requests_list)


@bp.route("/admin/requests/<int:rid>/generate")
@staff_required
def admin_request_generate(rid):
    req = db_row("SELECT * FROM plan_requests WHERE id=?", (rid,))
    if not req: return redirect("/admin/requests")
    try: rdata = json.loads(req["request_data"])
    except: return redirect("/admin/requests")
    client = get_user_by_id(req["client_id"])
    data = {
        "name": client.get("name","") if client else req.get("client_name",""),
        **rdata,
    }
    session["pdf_data"] = data
    session["current_plan"] = generate_weekly_plan(data)
    session["current_request_id"] = rid
    return redirect("/preview")


@bp.route("/admin/requests/<int:rid>/manual")
@staff_required
def admin_request_manual(rid):
    """Generate empty plan for manual filling"""
    req = db_row("SELECT * FROM plan_requests WHERE id=?", (rid,))
    if not req: return redirect("/admin/requests")
    try: rdata = json.loads(req["request_data"])
    except: return redirect("/admin/requests")
    client = get_user_by_id(req["client_id"])
    data = {
        "name": client.get("name","") if client else req.get("client_name",""),
        **rdata,
    }
    diet_type = data.get("diet_plan_type", "standard")
    plan_info = get_diet_plan_info(diet_type)
    days = ["الاحد","الاثنين","الثلاثاء","الاربعاء","الخميس","الجمعة","السبت"]

    goal = (data.get("goal") or "").lower()
    conditions_raw = data.get("symptoms") or data.get("conditions") or ""
    conditions = conditions_raw.lower() if isinstance(conditions_raw, str) else ""
    is_diabetes = any(k in conditions for k in ["سكري", "سكر", "diabet"])
    is_kidney = any(k in conditions for k in ["كلى", "كلي", "kidney"])

    def get_starter(meal_key, day_idx):
        breakfasts_general = [
            "🥣 شوفان بالحليب 40جم + 🍌 موز + 🌰 لوز 10جم",
            "🥚 بيضتين مسلوق + 🧀 جبن قريش 50جم + 🍞 خبز اسمر",
            "🥘 فول مدمس 150جم + 🥚 بيضة + 🍞 خبز اسمر",
            "🥞 توست بالأفوكادو + 🥚 بيضة + 🍅 طماطم",
            "🥛 زبادي يوناني 200جم + 🍓 فراولة + 🥜 جوز",
            "🥚 اومليت بالسبانخ + 🍞 خبز اسمر + 🧀 جبن قريش",
            "🥣 موسلي بالحليب + 🍎 تفاح + 🌰 لوز",
        ]
        breakfasts_diabetes = [
            "🥣 شوفان مطبوخ 40جم + 🥜 لوز 10جم + 🥚 بيضة مسلوقة",
            "🥚 بيضتين + 🥒 خيار + 🍞 خبز اسمر شريحة + 🥑 أفوكادو",
            "🥘 فول 100جم + 🥚 بيضة + 🥬 سلطة خضراء",
            "🥛 زبادي يوناني سادة + 🌰 جوز 10جم + 🍓 فراولة قليلة",
            "🥚 اومليت 2 بيضة + 🥬 سبانخ + 🍞 خبز اسمر شريحة",
            "🥚 بيض مسلوق + 🧀 جبن قريش + 🥒 خيار",
            "🥣 شوفان + 🥜 لوز + 🥛 حليب قليل دسم",
        ]
        breakfasts_kidney = [
            "🥚 بياض بيض 3 + 🍞 خبز ابيض + 🥒 خيار",
            "🥣 شوفان بماء + 🍎 تفاح + 🌰 لوز قليل",
            "🥚 بيضتين + 🍞 خبز ابيض + 🥒 خيار",
            "🥚 اومليت ببياض البيض + 🥬 خس",
            "🥖 توست + 🧈 زبدة قليلة + 🍯 عسل",
            "🥚 بياض بيض + 🍞 خبز ابيض + 🍎 تفاح",
            "🥣 شوفان + 🍓 فراولة قليلة",
        ]
        lunches_general = [
            "🍗 صدر دجاج مشوي 150جم + 🍚 أرز 100جم + 🥗 سلطة",
            "🐟 سمك مشوي 150جم + 🍠 بطاطا حلوة 100جم + 🥦 بروكلي",
            "🥩 لحم مشوي 120جم + 🍚 أرز بني 80جم + 🥗 سلطة",
            "🍗 دجاج بالخضار + 🍚 أرز 80جم + 🥒 خيار",
            "🐟 سلمون 150جم + 🍠 بطاطا حلوة + 🥬 سبانخ",
            "🍗 شيش طاووق 150جم + 🍚 أرز 100جم + 🥗 طبق سلطة",
            "🥚 طاجن فول + 🍞 خبز اسمر + 🥗 سلطة بلدي",
        ]
        lunches_diabetes = [
            "🍗 صدر دجاج 150جم + 🍚 أرز بني 70جم + 🥗 سلطة كبيرة",
            "🐟 سمك مشوي 150جم + 🥦 بروكلي + 🍠 بطاطا حلوة 80جم",
            "🥩 لحم 100جم + 🍚 أرز بني 60جم + 🥬 سبانخ",
            "🍗 دجاج مشوي + 🥗 سلطة كبيرة + 🍞 خبز اسمر شريحة",
            "🐟 تونة + 🥗 سلطة بأفوكادو + 🥖 خبز اسمر",
            "🥚 طاجن خضار بالبيض + 🍞 خبز اسمر شريحة",
            "🍗 صدر دجاج + 🥦 بروكلي + 🥕 جزر",
        ]
        lunches_kidney = [
            "🍗 صدر دجاج 100جم + 🍚 أرز ابيض + 🥒 خيار",
            "🐟 سمك ابيض 120جم + 🍚 أرز + 🥗 خس",
            "🍗 دجاج 100جم + 🍚 أرز + 🥒 خيار",
            "🥚 بيضتين + 🍚 أرز + 🥬 خس",
            "🍗 صدر دجاج + 🍚 أرز + 🍆 كوسى",
            "🐟 سمك مسلوق + 🍚 أرز + 🍎 تفاح",
            "🍗 دجاج + 🍚 أرز + 🥒 خيار + 🥬 خس",
        ]
        dinners_general = [
            "🥗 سلطة دجاج + 🍞 خبز اسمر + 🧀 جبن قريش",
            "🥚 بيضتين + 🧀 جبن + 🥒 خضار + 🍞 خبز اسمر",
            "🐟 تونة + 🥗 سلطة كبيرة + 🍞 توست",
            "🥛 زبادي يوناني + 🍓 فاكهة + 🥜 مكسرات",
            "🍗 صدر دجاج صغير + 🥗 سلطة + 🥖 خبز",
            "🥚 اومليت بالخضار + 🍞 خبز",
            "🥗 سلطة قيصر بالدجاج",
        ]
        snacks_general = [
            "🍎 تفاحة + 🌰 لوز 10 حبات",
            "🥛 زبادي + 🍓 فراولة",
            "🥜 مكسرات 30جم",
            "🍌 موزة + 🥜 زبدة فول سوداني ملعقة",
            "🥕 جزر + حمص",
            "🍐 كمثرى + 🧀 جبن قريش",
            "🥚 بيضة مسلوقة + 🥒 خيار",
        ]

        if "breakfast" in meal_key or "فطار" in meal_key.lower() or "فطور" in meal_key.lower():
            pool = breakfasts_kidney if is_kidney else (breakfasts_diabetes if is_diabetes else breakfasts_general)
        elif "lunch" in meal_key or "غدا" in meal_key.lower():
            pool = lunches_kidney if is_kidney else (lunches_diabetes if is_diabetes else lunches_general)
        elif "dinner" in meal_key or "عشا" in meal_key.lower():
            pool = dinners_general
        elif "snack" in meal_key or "سناك" in meal_key.lower() or "وجبة خفيفة" in meal_key.lower():
            pool = snacks_general
        else:
            pool = breakfasts_general

        return pool[day_idx % len(pool)]

    empty_plan = []
    for i in range(7):
        day_plan = {"day": days[i], "diet_type": diet_type,
                    "meal_labels": plan_info["meal_labels"],
                    "meal_emojis": plan_info["meal_emojis"], "total_cal": 0}
        for meal_key in plan_info["meals"]:
            day_plan[meal_key] = get_starter(meal_key, i)
        empty_plan.append(day_plan)
    session["pdf_data"] = data
    session["current_plan"] = empty_plan
    session["current_request_id"] = rid
    session["manual_mode"] = True
    return redirect("/preview")


@bp.route("/admin/requests/<int:rid>/approve", methods=["POST"])
@staff_required
def admin_request_approve(rid):
    plan = session.get("current_plan")
    data = session.get("pdf_data")
    if not plan or not data: return redirect("/admin/requests")
    db_run("UPDATE plan_requests SET status='approved', plan_data=?, updated_at=? WHERE id=?",
           (json.dumps({"plan": plan, "data": data}), datetime.now().isoformat(), rid))
    # ── إشعار موبايل للعميل إن خطته جاهزة ──
    client = None
    try:
        req = db_row("SELECT client_id FROM plan_requests WHERE id=?", (rid,))
        if req and req.get("client_id"):
            client = get_user_by_id(req["client_id"])
            push_to_user(req["client_id"], "خطتك الغذائية جاهزة! 🎉",
                         "د. محمد جهّزلك خطة جديدة. افتح التطبيق لمشاهدتها.",
                         url="/my-plan")
    except Exception as _e:
        print(f"push to client (plan) error: {_e}")

    # ── إرسال الخطة PDF بالإيميل للعميل ──
    try:
        if client and client.get("email"):
            pdf_bytes = build_pdf(data, plan)
            threading.Thread(
                target=send_plan_pdf_email,
                args=(client["email"], client.get("name"), pdf_bytes),
                daemon=True
            ).start()
    except Exception as _e:
        print(f"email plan pdf error: {_e}")

    session.pop("current_request_id", None)
    return redirect("/admin/requests")


@bp.route("/admin/notifications")
@staff_required
def admin_notifications():
    """صفحة كل الإشعارات (وبتعلّمها مقروءة بعد العرض)"""
    user = get_user_by_id(session["uid"])
    items = get_all_notifications(db_rows, limit=100)
    notifs = []
    for n in items:
        nd = dict(n)
        v = nd.get("created_at")
        if v:
            nd["created_str"] = v.strftime("%Y-%m-%d %H:%M") if hasattr(v, "strftime") else str(v)[:16]
        else:
            nd["created_str"] = ""
        meta = get_type_meta(nd.get("type"))
        nd["icon"] = meta["icon"]
        nd["type_label"] = meta["label"]
        notifs.append(nd)
    unread_before = sum(1 for n in notifs if not n.get("is_read"))
    # نعلّمها كلها مقروءة بعد ما اتعرضت
    try:
        mark_all_read(db_run)
    except: pass
    return render_template("admin_notifications.html", user=user,
                           lang=session.get("lang", "ar"),
                           notifications=notifs, unread_before=unread_before)


@bp.route("/admin/notifications/read", methods=["POST"])
@staff_required
def admin_notifications_read():
    """تعليم كل الإشعارات كمقروءة"""
    mark_all_read(db_run)
    return redirect("/admin/notifications")


@bp.route("/admin/notifications/count")
@staff_required
def admin_notifications_count():
    """API للجرس: بيرجّع عدد الإشعارات غير المقروءة (للـ polling والصوت)"""
    return jsonify({"count": get_unread_count(db_row)})


@bp.route("/admin/requests/<int:rid>/reject", methods=["POST"])
@staff_required
def admin_request_reject(rid):
    reason = request.form.get("reason", "").strip()
    db_run("UPDATE plan_requests SET status='rejected', notes=?, updated_at=? WHERE id=?",
           (reason, datetime.now().isoformat(), rid))

    req = db_row("SELECT client_id FROM plan_requests WHERE id=?", (rid,))
    if req:
        admin = db_row("SELECT id FROM users WHERE role='admin' OR is_admin=1 LIMIT 1")
        if admin:
            msg = f"⚠️ طلبك للخطة تم رفضه. السبب: {reason}" if reason else "⚠️ طلبك للخطة تم رفضه. تواصل معنا للمزيد."
            db_run("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?,?,?)",
                   (admin["id"], req["client_id"], msg))
    return redirect("/admin/requests")


@bp.route("/admin/users/<int:uid>/block", methods=["POST"])
@admin_required
def admin_block_user(uid):
    user = get_user_by_id(uid)
    if not user: return redirect("/admin/users")
    reason = request.form.get("reason", "").strip()

    try:
        db_run("INSERT INTO blocked_users (email, reason) VALUES (?,?)", (user["email"].lower(), reason))
    except Exception as e:
        # Blocking the same email twice lands here and is harmless. Anything
        # else means the account gets deactivated below without making it onto
        # the block list, so the person could sign up again with that email --
        # worth seeing in the logs rather than losing.
        log_error(f"blocked_users insert for {user['email'].lower()!r}", e)

    db_run("UPDATE users SET active=0 WHERE id=?", (uid,))
    return redirect("/admin/users")


@bp.route("/admin/users/<int:uid>/unblock", methods=["POST"])
@admin_required
def admin_unblock_user(uid):
    user = get_user_by_id(uid)
    if not user: return redirect("/admin/users")

    db_run("DELETE FROM blocked_users WHERE email=?", (user["email"].lower(),))
    db_run("UPDATE users SET active=1 WHERE id=?", (uid,))
    return redirect("/admin/users")


@bp.route("/admin/blocked")
@admin_required
def admin_blocked_list():
    try:
        blocked = db_rows("SELECT * FROM blocked_users ORDER BY blocked_at DESC")
    except Exception:
        try:
            if DATABASE_URL:
                db_run("""CREATE TABLE IF NOT EXISTS blocked_users (id SERIAL PRIMARY KEY, email TEXT UNIQUE, blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason TEXT)""")
            else:
                db_run("""CREATE TABLE IF NOT EXISTS blocked_users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason TEXT)""")
        except: pass
        blocked = []
    user = get_user_by_id(session["uid"])
    return render_template("admin_blocked.html", blocked=blocked, user=user, lang=session.get("lang","ar"))


@bp.route("/admin/blocked/<int:bid>/remove", methods=["POST"])
@admin_required
def admin_blocked_remove(bid):
    row = db_row("SELECT email FROM blocked_users WHERE id=?", (bid,))
    if row:
        db_run("UPDATE users SET active=1 WHERE email=?", (row["email"],))
    db_run("DELETE FROM blocked_users WHERE id=?", (bid,))
    return redirect("/admin/blocked")


@bp.route("/admin/users/<int:uid>")
@admin_required
def admin_user_profile(uid):
    """عرض صفحة الملف الشامل للعميل"""
    target_user = get_user_by_id(uid)
    if not target_user:
        return redirect("/admin/users")

    conditions = []
    allergies = []
    liked_foods = []
    disliked_foods = []
    try:
        if target_user.get("conditions"):
            conditions = json.loads(target_user["conditions"])
    except: pass
    try:
        if target_user.get("allergies"):
            allergies = json.loads(target_user["allergies"])
    except: pass
    try:
        if target_user.get("liked_foods"):
            liked_foods = json.loads(target_user["liked_foods"])
    except: pass
    try:
        if target_user.get("disliked_foods"):
            disliked_foods = json.loads(target_user["disliked_foods"])
    except: pass

    bmi = None
    try:
        h = float(target_user.get("height") or 0)
        w = float(target_user.get("weight") or 0)
        if h > 0 and w > 0:
            bmi = w / ((h / 100) ** 2)
    except: pass

    tdee = None
    try:
        h = float(target_user.get("height") or 0)
        w = float(target_user.get("weight") or 0)
        a = float(target_user.get("age") or 0)
        gender = (target_user.get("gender") or "ذكر").lower()
        activity = float(target_user.get("activity") or 1.55)
        if h > 0 and w > 0 and a > 0:
            if gender in ("ذكر", "male", "m"):
                bmr = 10 * w + 6.25 * h - 5 * a + 5
            else:
                bmr = 10 * w + 6.25 * h - 5 * a - 161
            tdee = int(bmr * activity)
    except: pass

    active_sub = None
    try:
        sub = db_row("""SELECT * FROM subscriptions 
                        WHERE user_id=? AND status IN ('active', 'trialing') 
                        ORDER BY current_period_end DESC LIMIT 1""", (uid,))
        if sub:
            active_sub = dict(sub)
            plan_info = PRICING.get(sub.get("plan_key"), {})
            active_sub["plan_name"] = _plan_name(plan_info, sub.get("plan_key"))
            for k in ("current_period_start", "current_period_end", "trial_end"):
                v = active_sub.get(k)
                if v:
                    if hasattr(v, "strftime"):
                        active_sub[k.replace("current_period_", "") + "_date" if k.startswith("current_period_") else k] = v.strftime("%Y-%m-%d")
                    else:
                        active_sub[k.replace("current_period_", "") + "_date" if k.startswith("current_period_") else k] = str(v)[:10]
            active_sub["start_date"] = active_sub.get("start_date") or "-"
            active_sub["end_date"] = active_sub.get("end_date") or "-"
    except: pass

    active_payment = None
    try:
        pay = db_row("""SELECT * FROM payments 
                        WHERE user_id=? AND status='completed' 
                        AND expires_at > ? 
                        ORDER BY expires_at DESC LIMIT 1""", (uid, datetime.now()))
        if pay:
            active_payment = dict(pay)
            plan_info = PRICING.get(pay.get("plan_key"), {})
            active_payment["plan_name"] = _plan_name(plan_info, pay.get("plan_key"))
            v = active_payment.get("expires_at")
            if v:
                active_payment["expires"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
    except: pass

    plan_requests = []
    try:
        plans = db_rows("SELECT * FROM plan_requests WHERE client_id=? ORDER BY created_at DESC LIMIT 50", (uid,))
        for p in plans:
            pd = dict(p)
            v = pd.get("created_at")
            if v:
                pd["created_date"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
            plan_requests.append(pd)
    except: pass

    payments = []
    try:
        pays = db_rows("SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (uid,))
        for p in pays:
            pd = dict(p)
            plan_info = PRICING.get(pd.get("plan_key"), {})
            pd["plan_label"] = plan_info.get("name", pd.get("plan_key"))
            v = pd.get("created_at")
            if v:
                pd["created_date"] = v.strftime("%Y-%m-%d %H:%M") if hasattr(v, "strftime") else str(v)[:16]
            v2 = pd.get("expires_at")
            if v2:
                pd["expires_date"] = v2.strftime("%Y-%m-%d") if hasattr(v2, "strftime") else str(v2)[:10]
            payments.append(pd)
    except: pass

    weight_logs = []
    try:
        logs = db_rows("SELECT * FROM weight_log WHERE user_id=? ORDER BY logged_at DESC LIMIT 30", (uid,))
        prev = None
        logs_list = list(logs)
        for i, w in enumerate(logs_list):
            wd = dict(w)
            v = wd.get("logged_at")
            if v:
                wd["logged_date"] = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
            if i + 1 < len(logs_list):
                try:
                    diff = float(wd["weight"]) - float(logs_list[i + 1]["weight"])
                    wd["diff"] = diff
                except: wd["diff"] = None
            else:
                wd["diff"] = None
            weight_logs.append(wd)
    except: pass

    return render_template("admin_user_profile.html",
                           user=target_user, lang=session.get("lang", "ar"),
                           client_whatsapp=build_whatsapp_link(target_user.get("phone"), target_user.get("country")),
                           tracking=get_meal_tracking(uid),
                           conditions=conditions, allergies=allergies,
                           liked_foods=liked_foods, disliked_foods=disliked_foods,
                           bmi=bmi, tdee=tdee,
                           active_sub=active_sub, active_payment=active_payment,
                           plan_requests=plan_requests, payments=payments,
                           weight_logs=weight_logs,
                           doctor_notes=target_user.get("doctor_notes") or "",
                           today_date=datetime.now().strftime("%Y-%m-%d"))


@bp.route("/admin/users/<int:uid>/update", methods=["POST"])
@admin_required
def admin_user_update(uid):
    """تعديل بيانات العميل الشاملة"""
    target = get_user_by_id(uid)
    if not target:
        return redirect("/admin/users")
    try:
        name = request.form.get("name", "").strip() or target.get("name")
        email = request.form.get("email", "").strip().lower() or target.get("email")
        phone = request.form.get("phone", "").strip() or target.get("phone")
        country = request.form.get("country", "").strip() or target.get("country")
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip() or target.get("gender")

        weight = request.form.get("weight", "").strip()
        height = request.form.get("height", "").strip()
        goal = request.form.get("goal", "").strip() or target.get("goal")
        activity = request.form.get("activity", "").strip()

        conditions = request.form.get("conditions", "[]")
        allergies = request.form.get("allergies", "[]")

        liked_text = request.form.get("liked_foods_text", "").strip()
        disliked_text = request.form.get("disliked_foods_text", "").strip()

        def text_to_json(txt):
            if not txt:
                return "[]"
            items = [s.strip() for s in txt.replace("،", ",").replace(";", ",").split(",") if s.strip()]
            return json.dumps(items, ensure_ascii=False)

        liked_foods = text_to_json(liked_text)
        disliked_foods = text_to_json(disliked_text)

        try: age_v = int(age) if age else target.get("age")
        except: age_v = target.get("age")
        try: weight_v = float(weight) if weight else target.get("weight")
        except: weight_v = target.get("weight")
        try: height_v = float(height) if height else target.get("height")
        except: height_v = target.get("height")
        try: activity_v = float(activity) if activity else target.get("activity")
        except: activity_v = target.get("activity")

        db_run("""UPDATE users SET 
                  name=?, email=?, phone=?, country=?, age=?, gender=?,
                  weight=?, height=?, goal=?, activity=?,
                  conditions=?, allergies=?,
                  liked_foods=?, disliked_foods=?
                  WHERE id=?""",
               (name, email, phone, country, age_v, gender,
                weight_v, height_v, goal, activity_v,
                conditions, allergies,
                liked_foods, disliked_foods,
                uid))

        if weight and weight_v and float(weight_v) != (target.get("weight") or 0):
            try:
                db_run("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)", (uid, weight_v))
            except: pass
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"Update error: {e}")
    return redirect(f"/admin/users/{uid}?updated=1")


@bp.route("/admin/users/<int:uid>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(uid):
    """الأدمن يعيّن كلمة سر جديدة لعميل نسي كلمة سره"""
    target = db_row("SELECT * FROM users WHERE id=?", (uid,))
    if not target or target.get("is_admin"):
        return redirect("/admin/users")
    new_pw = request.form.get("new_password", "").strip()
    if len(new_pw) < 6:
        return redirect(f"/admin/users/{uid}?pwreset=short")
    try:
        db_run("UPDATE users SET password=? WHERE id=?", (hp(new_pw), uid))
        return redirect(f"/admin/users/{uid}?pwreset=ok")
    except Exception as e:
        print(f"admin reset password error: {e}")
        return redirect(f"/admin/users/{uid}?pwreset=err")


@bp.route("/admin/users/<int:uid>/notes", methods=["POST"])
@admin_required
def admin_user_notes(uid):
    """حفظ ملاحظات الدكتور الخاصة عن العميل"""
    notes = request.form.get("notes", "").strip()
    try:
        db_run("UPDATE users SET doctor_notes=? WHERE id=?", (notes, uid))
    except Exception as e:
        print(f"Notes save error: {e}")
    return redirect(f"/admin/users/{uid}")


@bp.route("/admin/users/<int:uid>/add-weight", methods=["POST"])
@admin_required
def admin_user_add_weight(uid):
    """إضافة قياس وزن يدوياً للعميل"""
    try:
        w = float(request.form.get("weight", 0))
        if 20 < w < 300:
            logged_date = request.form.get("logged_date", "")
            if logged_date:
                db_run("INSERT INTO weight_log (user_id, weight, logged_at) VALUES (?, ?, ?)",
                       (uid, w, logged_date))
            else:
                db_run("INSERT INTO weight_log (user_id, weight) VALUES (?, ?)", (uid, w))
            db_run("UPDATE users SET weight=? WHERE id=?", (w, uid))
    except Exception as e:
        print(f"Add weight error: {e}")
    return redirect(f"/admin/users/{uid}")


@bp.route("/admin/users/<int:uid>/manual-activate", methods=["POST"])
@admin_required
def admin_manual_activate(uid):
    """تفعيل اشتراك مدفوع للعميل يدوياً (بعد ما يدفع عبر واتساب)"""
    target = get_user_by_id(uid)
    if not target:
        return redirect("/admin/users")

    try:
        plan_key = request.form.get("plan_key", "").strip()
        amount_raw = request.form.get("amount", "0").strip()
        currency = request.form.get("currency", "EGP").strip()
        payment_method = request.form.get("payment_method", "other").strip()
        notes = request.form.get("notes", "").strip()

        if plan_key not in ("consultation", "single_plan", "monthly_subscription"):
            return redirect(f"/admin/users/{uid}?error=invalid_plan")

        try:
            amount_value = float(amount_raw or 0)
            amount_cents = int(amount_value * 100)
        except:
            amount_cents = 0

        duration_days_map = {
            "consultation": 1,
            "single_plan": 7,
            "monthly_subscription": 30,
        }
        plan_names_map = {
            "consultation": "استشارة فردية",
            "single_plan": "خطة واحدة",
            "monthly_subscription": "اشتراك شهري",
        }
        method_names = {
            "vodafone_cash": "فودافون كاش",
            "instapay": "InstaPay",
            "bank_transfer_eg": "تحويل بنكي مصري",
            "bank_transfer_ae": "تحويل بنكي إماراتي",
            "cash": "كاش",
            "other": "طريقة أخرى",
        }

        duration_days = duration_days_map.get(plan_key, 30)
        plan_name = plan_names_map.get(plan_key, plan_key)
        method_name = method_names.get(payment_method, payment_method)

        now = datetime.now()
        end_date = now + timedelta(days=duration_days)

        metadata = {
            "manual_activation": True,
            "payment_method": payment_method,
            "method_name": method_name,
            "notes": notes,
            "activated_by_admin": session.get("uid"),
        }

        try:
            db_run("""INSERT INTO payments 
                      (user_id, stripe_session_id, plan_key, status, currency, amount, expires_at, metadata)
                      VALUES (?, ?, ?, 'completed', ?, ?, ?, ?)""",
                   (uid, f"manual_{uid}_{int(now.timestamp())}", plan_key,
                    currency, amount_cents, end_date, json.dumps(metadata, ensure_ascii=False)))
        except Exception as e:
            print(f"Insert payment error: {e}")

        if plan_key == "monthly_subscription":
            try:
                db_run("""INSERT INTO subscriptions
                          (user_id, plan_key, status, currency, amount,
                           current_period_start, current_period_end,
                           stripe_subscription_id)
                          VALUES (?, ?, 'active', ?, ?, ?, ?, ?)""",
                       (uid, plan_key, currency, amount_cents,
                        now, end_date, f"manual_sub_{uid}_{int(now.timestamp())}"))
            except Exception as e:
                print(f"Insert subscription error: {e}")

        try:
            admin = db_row("SELECT id FROM users WHERE role='admin' OR is_admin=1 LIMIT 1")
            if admin:
                msg = f"""✅ تم تفعيل اشتراكك بنجاح!

📋 الخطة: {plan_name}
💰 المبلغ: {amount_value:.0f} {currency}
💳 طريقة الدفع: {method_name}
📅 ساري حتى: {end_date.strftime('%Y-%m-%d')}

شكراً لثقتك فينا. تقدر تستخدم كل خدمات الموقع دلوقتي."""
                db_run("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                       (admin["id"], uid, msg))
        except Exception as e:
            print(f"Send message error: {e}")

    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"Manual activate error: {e}")
        return redirect(f"/admin/users/{uid}?error=activation_failed")

    return redirect(f"/admin/users/{uid}?activated=1")


@bp.route("/admin/users/<int:uid>/grant-trial", methods=["POST"])
@admin_required
def admin_grant_trial(uid):
    """إعطاء العميل 7 أيام تجربة مجاناً (يدوي - بدون Stripe)"""
    target = get_user_by_id(uid)
    if not target:
        return redirect("/admin/users")
    try:
        if has_active_access(uid, db_row):
            return redirect(f"/admin/users/{uid}")
        now = datetime.now()
        trial_end = now + timedelta(days=7)
        db_run("""INSERT INTO subscriptions 
                  (user_id, plan_key, status, currency, amount,
                   current_period_start, current_period_end, trial_end,
                   stripe_subscription_id)
                  VALUES (?, 'monthly_subscription', 'trialing', 'EGP', 0, ?, ?, ?, ?)""",
               (uid, now, trial_end, trial_end, f"manual_trial_{uid}_{int(now.timestamp())}"))
        admin = db_row("SELECT id FROM users WHERE role='admin' OR is_admin=1 LIMIT 1")
        if admin:
            msg = "🎁 تم منحك فترة تجريبية مجانية 7 أيام! تقدر تستخدم كل خدمات الموقع مجاناً."
            db_run("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                   (admin["id"], uid, msg))
    except Exception as e:
        print(f"Grant trial error: {e}")
    return redirect(f"/admin/users/{uid}")


@bp.route("/admin/users/<int:uid>/cancel-subscription", methods=["POST"])
@admin_required
def admin_cancel_subscription(uid):
    """إلغاء اشتراك العميل من جهة admin"""
    try:
        sub = db_row("""SELECT * FROM subscriptions 
                        WHERE user_id=? AND status IN ('active', 'trialing') 
                        ORDER BY current_period_end DESC LIMIT 1""", (uid,))
        if sub:
            sub_id = sub.get("stripe_subscription_id", "")
            if sub_id and not sub_id.startswith("manual_"):
                try:
                    import stripe as _stripe
                    _stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
                    _stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
                except Exception as e:
                    print(f"Stripe cancel error: {e}")
            db_run("""UPDATE subscriptions SET status='canceled', cancel_at=?, updated_at=? 
                      WHERE id=?""", (datetime.now(), datetime.now(), sub["id"]))
    except Exception as e:
        print(f"Cancel subscription error: {e}")
    return redirect(f"/admin/users/{uid}")


@bp.route("/admin/users/<int:uid>/payments")
@admin_required
def admin_user_payments(uid):
    """صفحة كل دفعات العميل (redirect لصفحة الـ admin payments مع filter)"""
    return redirect(f"/admin/payments?user={uid}")

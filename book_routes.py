"""
book_routes.py
==============
أضف السطر ده في app.py بتاعك:
    from book_routes import book_bp
    app.register_blueprint(book_bp)
"""

import os
import json
import sqlite3
import urllib.request
from flask import Blueprint, render_template, request, jsonify, session
from functools import wraps

book_bp = Blueprint("book", __name__)

DB_PATH = "book_index.db"
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ── حماية — لازم يكون مسجل دخول ────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "غير مصرح"}), 401
        return f(*args, **kwargs)
    return decorated


# ── اتصال بقاعدة البيانات ────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── صفحة مساعد الكتاب ────────────────────────────────────────────────────────
@book_bp.route("/book-assistant")
def book_assistant():
    if "user_id" not in session:
        return render_template("login.html")
    return render_template("book_assistant.html")


# ── بحث نصي ─────────────────────────────────────────────────────────────────
@book_bp.route("/api/book/search")
@login_required
def search_book():
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"results": []})

    conn    = get_db()
    # بحث بسيط بكل كلمة في الاستعلام
    words   = query.split()
    like    = "%" + "%".join(words) + "%"
    results = conn.execute(
        "SELECT page_num, substr(text, 1, 300) as snippet FROM pages WHERE text LIKE ? LIMIT 10",
        (like,)
    ).fetchall()
    conn.close()

    return jsonify({
        "results": [{"page": r["page_num"], "snippet": r["snippet"]} for r in results]
    })


# ── سؤال الـ AI ───────────────────────────────────────────────────────────────
@book_bp.route("/api/book/ask", methods=["POST"])
@login_required
def ask_book():
    data     = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "السؤال فارغ"}), 400

    # ابحث عن الصفحات الأكثر صلة بالسؤال
    conn    = get_db()
    words   = question.split()
    context_pages = []

    for word in words[:5]:  # أول 5 كلمات بس
        if len(word) < 3:
            continue
        rows = conn.execute(
            "SELECT page_num, text FROM pages WHERE text LIKE ? LIMIT 3",
            (f"%{word}%",)
        ).fetchall()
        for r in rows:
            if r["page_num"] not in [p["page"] for p in context_pages]:
                context_pages.append({"page": r["page_num"], "text": r["text"]})

    conn.close()

    # لو ملقيناش صفحات ذات صلة
    if not context_pages:
        return jsonify({
            "answer": "لم أجد معلومات كافية في الكتاب عن هذا الموضوع.",
            "pages": []
        })

    # جهّز الـ context للـ AI
    context_text = "\n\n".join([
        f"[صفحة {p['page']}]\n{p['text'][:600]}"
        for p in context_pages[:5]
    ])

    prompt = f"""أنت مساعد تغذية متخصص. أجب على السؤال التالي بناءً فقط على المحتوى المقتطف من كتاب "الغذاء والتغذية" الطبي.

محتوى الكتاب:
{context_text}

السؤال: {question}

تعليمات:
- أجب بالعربية بشكل واضح ومختصر
- استند فقط على المعلومات الموجودة في المحتوى أعلاه
- في نهاية إجابتك اذكر أرقام الصفحات التي استندت إليها هكذا: (المصدر: ص X، ص Y)
- إذا لم تجد إجابة كافية قل ذلك صراحة"""

    try:
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type":      "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key":         API_KEY
            }
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            answer = json.loads(r.read())["content"][0]["text"]

        return jsonify({
            "answer": answer,
            "pages":  [p["page"] for p in context_pages[:5]]
        })

    except Exception as e:
        return jsonify({"error": f"خطأ في الاتصال: {str(e)}"}), 500

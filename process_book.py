"""
process_book.py
===============
سكريبت بيشتغل مرة واحدة بس — بيحول الكتاب كله لنصوص ويحفظها في قاعدة البيانات
شغّله من جهازك بـ: python process_book.py
"""

import os
import base64
import json
import sqlite3
import time
import urllib.request
from pathlib import Path

import fitz  # pip install pymupdf

PDF_PATH = "الغذاء_والتغذية.pdf"   # حط الـ PDF جنب السكريبت
DB_PATH  = "book_index.db"          # هيتعمل تلقائياً
API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")  # حط الـ key في environment variables
BATCH_SIZE = 5  # عدد الصفحات اللي بنبعتها لـ Claude في كل مرة


# ── إنشاء قاعدة البيانات ────────────────────────────────────────────────────
def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            page_num  INTEGER PRIMARY KEY,
            text      TEXT,
            processed INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_text ON pages(text)")
    conn.commit()
    return conn


# ── استخراج نص صفحة بـ Claude Vision ────────────────────────────────────────
def ocr_page(img_bytes: bytes) -> str:
    img_b64 = base64.b64encode(img_bytes).decode()
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
                },
                {
                    "type": "text",
                    "text": (
                        "استخرج كل النص الموجود في هذه الصفحة بدقة تامة. "
                        "لا تضف أي تعليق أو شرح، فقط النص الموجود في الصفحة."
                    )
                }
            ]
        }]
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type":    "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key":       API_KEY
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["content"][0]["text"]


# ── المعالجة الرئيسية ─────────────────────────────────────────────────────────
def process_book():
    if not API_KEY:
        print("❌ مفيش API key! حط ANTHROPIC_API_KEY في الـ environment")
        return

    conn   = init_db(DB_PATH)
    doc    = fitz.open(PDF_PATH)
    total  = len(doc)
    done   = conn.execute("SELECT COUNT(*) FROM pages WHERE processed=1").fetchone()[0]

    print(f"📖 الكتاب: {total} صفحة | تم معالجة: {done} صفحة")

    for page_num in range(done, total):
        page = doc[page_num]
        # تحويل الصفحة لصورة
        pix  = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("jpeg")

        try:
            text = ocr_page(img_bytes)
            conn.execute(
                "INSERT OR REPLACE INTO pages (page_num, text, processed) VALUES (?,?,1)",
                (page_num + 1, text)
            )
            conn.commit()
            print(f"✅ صفحة {page_num+1}/{total}")
        except Exception as e:
            print(f"⚠️  صفحة {page_num+1} فشلت: {e}")

        # استنى شوية عشان ما تتضربش بـ rate limit
        time.sleep(0.5)

    conn.close()
    print(f"\n🎉 خلصنا! الملف: {DB_PATH}")


if __name__ == "__main__":
    process_book()

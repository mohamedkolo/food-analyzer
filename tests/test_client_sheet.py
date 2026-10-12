# -*- coding: utf-8 -*-
"""‏الورقة اللي بتتسلّم: جدول وممنوع/مسموح وبس.

‏الدكتور بعت صورة الشكل اللي عايزه وقال بالنص: "عايز شكل الورقة
النهائي يكون كده، مفهوش أي إضافات غير إيه الممنوع والمسموح بالنسبة
للحالة فقط".

‏يعني اللي اتشال من ورقة العميل: سطر البيانات (الوزن، الطول، BMI،
السعرات، الماكروز)، أعمدة الأرقام (هدف اليوم، السعرات، البروتين)،
الملخص، الماء، والتحذيرات الإكلينيكية.

‏واللي اتشال **مااتلغاش** -- اتنقل للمعاينة. ده مهم: التحذيرات دي
شغل الأخصائي أصلاً ("لازم يشوف الفرق ده قبل ما يسلّم الورقة")، ولو
ضاعت يبقى الشيل ده خسارة مش تنضيف.

Run with:  python3 tests/test_client_sheet.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_sheet_test.db"

import app as A            # noqa: E402
import plan_engine         # noqa: E402
import zigzag              # noqa: E402

CLIENT = {"name": "ريم محمد", "age": "38", "gender": "انثى", "culture": "مصري",
          "diet_plan_type": "standard", "fat_pct_cal": "30",
          "symptoms": ["سكري النوع الثاني"], "allergies": [],
          "zigzag_mode": "classic", "activity_level": "light",
          "goal_type": "weight_loss", "weight": "95", "height": "162",
          "tdee": "2350", "goal_cal": "1750", "protein_per_kg": "1.6",
          "bmi": "36.2"}


def _sheet(**over):
    data = dict(CLIENT, **over)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
        html = plan_engine.plan_html(data, plan)
    return data, plan, html


def _text(html):
    return re.sub(r"<[^>]+>", " ", html)


def test_the_table_carries_the_food_and_nothing_else():
    """‏الصورة اللي بعتها: اليوم والفطار والغداء والعشاء وسناك. خلاص."""
    _data, _plan, html = _sheet()
    head = html[html.index("<thead>"):html.index("</thead>")]
    cells = re.findall(r"<th[^>]*>(.*?)</th>", head, re.S)
    labels = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
    assert labels[0] in ("اليوم", "Day"), labels
    for banned in ("سعرات", "بروتين", "هدف اليوم", "kcal", "Protein",
                   "Day target"):
        assert banned not in labels, "‏عمود %s لسه في الجدول: %s" % (
            banned, labels)


def test_the_meta_line_is_only_the_name():
    """‏الوزن والطول وBMI والسعرات والماكروز -- كلهم بيانات شغل."""
    _data, _plan, html = _sheet()
    meta = re.search(r'<div class="meta">(.*?)</div>', html, re.S)
    assert meta, "‏سطر البيانات اختفى خالص -- الاسم المفروض يفضل"
    body = re.sub(r"<[^>]+>", " ", meta.group(1))
    assert "ريم محمد" in body, body
    for banned in ("BMI", "الطول", "الوزن", "بروتين مستهدف", "المطبخ",
                   "السعرات المستهدفة"):
        assert banned not in body, "‏%s لسه في سطر البيانات: %s" % (banned, body)


def test_the_sheet_keeps_only_allowed_and_forbidden():
    """‏الفحص على **الصناديق** مش على الكلمات: أول نسخة من الاختبار
    كانت بتدوّر على كلمة "الماء" في الورقة كلها، وهي جوه أسماء وجبات
    ("تونة بالماء"، "شوفان بالماء") -- فكان بيفشل على ورقة سليمة."""
    _data, _plan, html = _sheet()
    boxes = re.findall(r'<div class="fbox[^"]*"><h4>(.*?)</h4>', html, re.S)
    heads = [re.sub(r"<[^>]+>", "", b).strip() for b in boxes]
    assert heads == ["مسموح", "ممنوع"], heads
    for banned in ('class="summary"', 'class="notes"', 'class="pnote"',
                   'class="fu-note"'):
        assert banned not in html, "‏%s لسه على ورقة العميل" % banned


def test_no_calorie_number_reaches_the_client_sheet():
    """‏سعرات السناك كانت مكتوبة جنبه في آخر النص."""
    _data, plan, html = _sheet()
    assert any("kcal" in (d.get("snack") or "") for d in plan), (
        "‏الاختبار ده مالوش معنى من غير سناك بسعراته")
    text = _text(html)
    assert "kcal" not in text and "سعرة" not in text, (
        "‏لسه فيه سعرات: %s" % text[:400])


def test_a_dangling_separator_is_not_printed():
    """‏٣٥ وجبة في القاعدة آخرها إيموجي لوحده، والإيموجي بيتشال من
    المطبوع -- فكان بيفضل "سلطة كبيرة 200جم +"."""
    data = dict(CLIENT, zigzag_mode="off")
    plan = [{"day": "الاحد", "diet_type": "standard",
             "meal_labels": ["breakfast"], "meal_emojis": {},
             "breakfast": "🐟 جمبري مشوي 150جم + 🥗 سلطة كبيرة 200جم + 🍋",
             "total_cal": 400, "total_p": 40}]
    with A.app.test_request_context("/"):
        html = plan_engine.plan_html(data, plan)
    items = re.findall(r'<span class="it">(.*?)</span>', html, re.S)
    items = [re.sub(r"<[^>]+>", "", i).strip() for i in items]
    assert items == ["جمبري مشوي 150جم", "سلطة كبيرة 200جم"], items


def test_what_left_the_sheet_reaches_the_specialist_instead():
    """‏ده الشرط اللي بيخلي الشيل تنضيف مش خسارة."""
    data, _plan, _html = _sheet()
    notes = data.get("sheet_notes")
    assert notes, "‏التحذيرات ضاعت خالص"
    joined = " ".join(n["short"] for n in notes)
    assert "الفعلي" in joined and "الهدف" in joined, joined
    assert any("بروتين مستهدف" in n["short"] for n in notes), joined


def test_the_specialist_notes_are_short():
    """‏"الملحوظة اللي بتكتبها تبقى مختصرة شوية" -- ملاحظة سن النمو
    كانت فقرة كاملة."""
    data, _plan, _html = _sheet(age="10", weight="108.8", height="152",
                                tdee="1912", goal_cal="1912",
                                protein_per_kg="1.3", symptoms=[])
    for note in data["sheet_notes"]:
        assert len(note["short"]) <= 160, (len(note["short"]), note["short"])
        assert "<" not in note["short"], note["short"]


def test_a_warning_still_reads_as_a_warning():
    """‏الاختصار مايخليش التحذير يبان زي أي سطر."""
    data, _plan, _html = _sheet(activity_level="athlete",
                                protein_per_kg="2.5")
    kinds = {n["kind"] for n in data["sheet_notes"]}
    assert "warn" in kinds or "info" in kinds, data["sheet_notes"]


def test_the_sheet_is_still_one_page():
    from weasyprint import HTML
    for over in ({}, {"diet_plan_type": "five_meals"},
                 {"age": "10", "weight": "108.8", "height": "152",
                  "tdee": "1912", "goal_cal": "1912", "symptoms": []}):
        _d, _p, html = _sheet(**over)
        pages = len(HTML(string=html).render().pages)
        assert pages == 1, (over, pages)


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {str(e)[:300]}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

# -*- coding: utf-8 -*-
"""‏التعليمات تحت الجدول: اختيارية، ومطفية.

‏ورقة العميل اتقلّمت لحد ما بقت **جدول + مسموح + ممنوع** وبس، بطلب
الدكتور: "مفهوش أي إضافات". والملاحظات الإكلينيكية راحت للمعاينة.

‏وبعدين طلب تعليمات مع الورقة لعميلة معيّنة -- النوم والمياه والرياضة
والأكل من برّه -- وطلبها تاني وتالت، وقال "مختصر أكتر" مرتين. فاتعملت
بالإيد تلات مرات والتطبيق مابيعرفش يعملها.

‏فبقت فيه، **بزرار مطفي**: اللي عايزها يشوّلها، والورقة الافتراضية
زي ما هي بالظبط.

‏وستة سطور، كل واحد **نتيجة** مش شرح -- ده اللي اتطلب حرفياً.

Run with:  python3 tests/test_sheet_rules.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_rules_test.db")

import app as A            # noqa: E402
import plan_engine         # noqa: E402
import zigzag              # noqa: E402

_BASE = {"name": "ع", "gender": "انثى", "age": "30", "height": "163",
         "weight": "82", "culture": "مصري", "diet_plan_type": "standard",
         "goal_type": "weight_loss", "activity_level": "light",
         "tdee": "1900", "goal_cal": "1550", "protein_per_kg": "1.6",
         "fat_pct_cal": "30", "allergies": [], "symptoms": [],
         "zigzag_mode": "off"}


def _sheet(**over):
    data = dict(_BASE)
    data.update(over)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data, seed="r")
        return plan_engine.plan_html(data, plan)


def _rules_text(html):
    assert 'class="rules"' in html, "‏مافيش تعليمات في الورقة"
    body = html[html.index('class="rules"'):]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()


# ── مطفية بالافتراضي ─────────────────────────────────────────────────

def test_the_default_sheet_is_untouched():
    """‏الورقة اتقلّمت بطلب الدكتور. أي إضافة افتراضية بتلغي الطلب ده."""
    html = _sheet()
    # ‏الفحص على البلوك نفسه، مش على الكلمة: كلمة "التعليمات" موجودة في
    # تعليق الـCSS وهو بيتطبع في كل ورقة.
    assert 'class="rules"' not in html, "‏التعليمات طلعت من غير ما تتطلب"
    assert "<table>" in html, "‏الجدول نفسه اختفى"


def test_it_shows_only_when_asked():
    assert 'class="rules"' in _sheet(print_rules="1")


def test_a_falsy_value_does_not_turn_it_on():
    for value in ("", "0", "off", "لأ"):
        assert 'class="rules"' not in _sheet(print_rules=value), value


# ── المحتوى ─────────────────────────────────────────────────────────

def test_the_six_lines_are_all_there():
    text = _rules_text(_sheet(print_rules="1"))
    for head in ("النوم", "المياه", "الرياضة", "من برّه", "الطبق", "الوزن"):
        assert head in text, "‏ناقص سطر %s" % head


def test_it_stays_six_lines_not_six_paragraphs():
    """‏"مختصر أكتر" اتطلبت مرتين."""
    html = _sheet(print_rules="1")
    body = html[html.index('class="rules"'):]
    assert body.count("<tr>") == 6, body.count("<tr>")
    text = _rules_text(html)
    words = [w for w in text.split() if len(w) > 1]
    assert len(words) < 90, "‏%d كلمة -- بقت فقرات" % len(words)


# ── الأرقام من بياناته هو ───────────────────────────────────────────

def test_the_water_follows_his_own_report_when_it_is_recorded():
    text = _rules_text(_sheet(print_rules="1", water_l="1.8"))
    assert "1.8 لتر" in text, text[:200]


def test_without_a_recorded_number_it_follows_his_weight():
    """‏٣٣ مل لكل كيلو -- نفس الرقم المكتوب في ملاحظة سن النمو."""
    text = _rules_text(_sheet(print_rules="1", weight="82"))
    assert "2.7 لتر" in text, text[:200]
    text2 = _rules_text(_sheet(print_rules="1", weight="60"))
    assert "2 لتر" in text2, text2[:200]


def test_an_athlete_is_not_told_to_start_walking():
    """‏سطر المشي للمبتدئ. الرياضي محتاج يسمع عن زيادة الحمل."""
    plain = _rules_text(_sheet(print_rules="1"))
    assert "مشي" in plain, plain[:200]
    athlete = _rules_text(_sheet(print_rules="1", sport="strength",
                                 training_days="4"))
    assert "زوّد الحمل" in athlete, athlete[:200]
    assert "مشي ٢٠" not in athlete, athlete[:200]


# ── الفورم ──────────────────────────────────────────────────────────

def test_the_form_offers_it_and_the_server_reads_it():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "templates", "generate.html"),
              encoding="utf-8") as fh:
        page = fh.read()
    assert 'name="print_rules"' in page, "‏مافيش زرار في الفورم"
    assert 'type="checkbox"' in page
    with open(os.path.join(here, "routes_plans.py"), encoding="utf-8") as fh:
        src = fh.read()
    assert 'request.form.get("print_rules"' in src, (
        "‏السيرفر مش بيقرا الزرار -- هيتبعت ويضيع")


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

# -*- coding: utf-8 -*-
"""‏زرار "ولّد الخطة" كان بيموت ساكت مع العميل الراجع.

‏الدكتور بيكتب اسم عميل راجع، القايمة بتنزل، بيدوس عليه، والخانات
بتتملى من آخر زيارة. وبعدين بيدوس "ولّد الخطة" و**مايحصلش حاجة
خالص** -- لا صفحة ولا رسالة ولا أي حركة.

‏السبب: الملء التلقائي بيجيب الأرقام من القاعدة **زي ما هي**، والقاعدة
بتخزّنها REAL. فـBMI بيطلع ٢٧.٦٨ وTDEE ١٩٠٣.٥ والهدف ١٤٠٣.٥. والخانات
كان عليها قيود خطوة (step="0.1" للـBMI، والـTDEE والهدف من غير step
يعني خطوة ١ افتراضي) -- فتلات خانات بقت **مرفوضة** من المتصفح في نفس
اللحظة.

‏واللي خلاه ساكت: لما يبقى في حقل مرفوض، المتصفح **مابيبعتش حدث submit
أصلاً**. فمعالج الإرسال اللي في الصفحة -- اللي شغلته يوديه للخطوة
الصح ويوريه الرسالة -- كان كود ميت في الحالة دي.

‏حاجتين اتصلحوا:
  ١) الأرقام كلها step="any". البرنامج نفسه هو اللي بيكتب الكسور دي،
     والنطاق بيتأكد منه السيرفر مش المتصفح.
  ٢) الصفحة بقت تسمع حدث invalid (في مرحلة الالتقاط) وتفتح الخطوة
     وأي صندوق <details> مطوي الحقل جواه -- عشان الرسالة يكون ليها
     مكان تبان فيه.

Run with:  python3 tests/test_generate_button.py
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = io.open(os.path.join(HERE, "templates", "generate.html"),
               encoding="utf-8").read()

# ‏الخانات اللي **البرنامج** بيكتب فيها: الملء من آخر زيارة أو قارئ
# ورقة التحليل أو الحساب في الصفحة. أي قيد خطوة عليها بيرفض قيمة
# البرنامج نفسه.
WRITTEN_BY_THE_APP = ("age", "height", "weight", "fat_pct", "bmi", "tdee",
                      "goal_cal", "protein_per_kg", "fat_pct_cal",
                      "carb_pct_cal")


def _input(name):
    m = re.search(r'<input[^>]*name="%s"[^>]*>' % re.escape(name), PAGE)
    if not m:
        m = re.search(r'<input[^>]*name="%s"[^>]*>' % re.escape(name),
                      PAGE.replace("\n", " "))
    assert m, "‏خانة %s مش موجودة" % name
    return m.group(0)


# ── القيد اللي كان بيرفض أرقام البرنامج ─────────────────────────────

def test_no_number_the_app_writes_can_be_rejected_by_the_browser():
    """‏٢٧.٦٨ مش من اختراع الدكتور -- ده BMI اتحسب واتخزن. وstep="0.1"
    بيخليه قيمة مرفوضة."""
    bad = []
    for name in WRITTEN_BY_THE_APP:
        tag = _input(name)
        if 'type="number"' not in tag:
            continue
        step = re.search(r'step="([^"]+)"', tag)
        if not step or step.group(1) != "any":
            bad.append("%s: step=%s" % (name, step.group(1) if step else "(1 افتراضي)"))
    assert not bad, "\n   ".join(bad)


def test_the_range_is_still_guarded_where_it_matters():
    """step="any" مش معناه أي رقم: النسب والبروتين لسه ليهم حدود."""
    for name, lo, hi in (("protein_per_kg", "0", "5"),
                         ("fat_pct_cal", "0", "90")):
        tag = _input(name)
        assert 'min="%s"' % lo in tag, tag
        assert 'max="%s"' % hi in tag, tag


# ── الرفض الصامت ────────────────────────────────────────────────────

def test_the_page_listens_for_invalid_not_only_for_submit():
    """‏لما يبقى في حقل مرفوض، المتصفح مابيبعتش submit أصلاً. فمعالج
    الإرسال لوحده بيبقى كود ميت، والدكتور يدوس ومايحصلش حاجة."""
    assert "addEventListener('invalid'" in PAGE, (
        "‏الصفحة بتستنى submit بس -- وهو مش بييجي أصلاً")
    at = PAGE.index("addEventListener('invalid'")
    tail = PAGE[at:at + 220]
    assert "true" in tail, (
        "‏invalid مابيصعدّش، فلازم يتسمع في مرحلة الالتقاط: %s" % tail[:120])


def test_a_rejected_field_inside_a_shut_box_gets_opened():
    """‏الماكروز والتدوير بقوا صناديق مطوية. حقل مرفوض جوه صندوق مقفول
    مش مرسوم أصلاً -- فمافيش فقاعة تطلع عليه ومافيش رسالة."""
    assert "function reveal(" in PAGE, "‏مافيش دالة بتظهّر الحقل"
    at = PAGE.index("function reveal(")
    body = PAGE[at:at + 420]
    assert "details:not([open])" in body, body[:200]
    assert ".open = true" in body, body[:200]
    assert "closest('.wz-step')" in body, "‏الخطوة اللي فيها الحقل مش بتتفتح"


def test_the_reveal_runs_before_the_browser_gives_up():
    """‏الترتيب مهم: الإظهار لازم يحصل في معالج invalid نفسه."""
    at = PAGE.index("addEventListener('invalid'")
    assert "reveal(" in PAGE[at:at + 160], PAGE[at:at + 160]


# ── السيرفر ─────────────────────────────────────────────────────────

def test_the_server_takes_the_decimals_the_database_hands_back():
    """‏لو السيرفر بيرفضهم، فـstep="any" بينقل المشكلة مش بيحلها."""
    os.environ.setdefault("SECRET_KEY", "test-only")
    os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
    os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_button_test.db")
    import app as A
    A.app.config["WTF_CSRF_ENABLED"] = False
    c = A.app.test_client()
    with c.session_transaction() as sess:
        sess["uid"] = 1
        sess["role"] = "admin"
        sess["lang"] = "ar"
    r = c.post("/generate", data={
        "name": "عميل راجع", "gender": "ذكر", "age": "30",
        "height": "170.5", "weight": "80.4", "fat_pct": "24.25",
        "bmi": "27.68", "tdee": "1903.5", "goal_cal": "1403.5",
        "activity_mult": "1.55", "protein_per_kg": "1.55",
        "fat_pct_cal": "30", "carb_pct_cal": "45",
        "goal_type": "weight_loss", "culture": "مصري",
        "diet_plan_type": "standard", "zigzag_mode": "off",
    }, follow_redirects=False)
    assert r.status_code in (200, 302), r.status_code
    if r.status_code == 302:
        assert "/preview" in (r.headers.get("Location") or ""), r.headers


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
            print(f"  FAIL  {name}\n        {str(e)[:400]}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

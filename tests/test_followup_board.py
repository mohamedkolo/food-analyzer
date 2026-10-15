# -*- coding: utf-8 -*-
"""‏لوحة المتابعة: مين نازل، مين واقف، ومين غاب.

‏صفحة /followups كانت بتعرض الاسم وعدد الزيارات وتاريخ آخر زيارة. تلات
أعمدة، ولا واحد فيهم بيقول **إيه اللي حصل**. الدكتور عنده عشرات الملفات،
وعشان يعرف مين واقف كان لازم يفتحهم واحد واحد.

‏الحاجتين اللي الملف ده بيحميهم:

  * **الغياب بيسبق المعدل.** عميل آخر قياس له نزول ممتاز بس مجاش من
    شهرين -- "نازل كويس" هنا كذب: القياس عمره شهرين والدكتور مشفوش.
    اللي محتاج يحصل إنه يرجع، مش إن الخطة تتعدّل على رقم قديم.
  * **الحكم على آخر فترة، مش على التاريخ كله.** عميل نزل ١٢ كيلو في
    ٦ شهور وواقف من شهرين = واقف. التاريخ الحلو مابيلغيش إن الخطة
    وقفت دلوقتي.

Run with:  python3 tests/test_followup_board.py
"""

import datetime as dt
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_board_test.db"

import app as A          # noqa: E402
import followup          # noqa: E402

NOW = dt.datetime(2026, 6, 1, 12, 0, 0)


def _visit(key, name, weight, days_ago, **kw):
    """‏زيارة واحدة. الباقي قيم معقولة عشان assess تقدر تحسب."""
    v = {"client_key": key, "client_name": name, "weight": weight,
         "height": 170, "age": 35, "gender": "ذكر", "activity": 1.55,
         "tdee": 2400, "goal_cal": 1900, "goal_type": "weight_loss",
         "created_at": (NOW - dt.timedelta(days=days_ago)
                        ).strftime("%Y-%m-%d %H:%M:%S")}
    v.update(kw)
    return v


def _row(board, key):
    for r in board["rows"]:
        if r["client_key"] == key:
            return r
    raise AssertionError("‏%s مش في اللوحة: %s" % (
        key, [r["client_key"] for r in board["rows"]]))


# ── الأحكام ──────────────────────────────────────────────────────────

def test_a_client_losing_at_a_safe_rate_reads_as_on_track():
    b = followup.board([_visit("a", "ماشي", 94.0, 2),
                        _visit("a", "ماشي", 97.0, 23)], today=NOW)
    r = _row(b, "a")
    assert r["state"] == "on_track", r
    assert r["tone"] == "good", r
    assert r["last_delta"] == -3.0, r


def test_a_client_whose_weight_stopped_reads_as_stalled():
    b = followup.board([_visit("b", "واقف", 90.1, 3),
                        _visit("b", "واقف", 90.0, 31)], today=NOW)
    r = _row(b, "b")
    assert r["state"] == "plateau", r
    assert r["tone"] == "warn", r


def test_a_client_who_went_back_up_reads_as_regained():
    b = followup.board([_visit("c", "رجع", 93.0, 4),
                        _visit("c", "رجع", 90.0, 32)], today=NOW)
    r = _row(b, "c")
    assert r["state"] == "regained", r
    assert r["tone"] == "bad", r


def test_a_single_visit_is_not_judged():
    """‏زيارة واحدة مافيهاش مقارنة. لو قلنا عليها "ماشي" يبقى اخترعنا حكم."""
    b = followup.board([_visit("d", "جديد", 100.0, 3)], today=NOW)
    r = _row(b, "d")
    assert r["state"] == "single", r
    assert r["last_delta"] is None, r
    assert r["tone"] == "idle", r


# ── الغياب ───────────────────────────────────────────────────────────

def test_a_client_who_stopped_coming_outranks_their_own_good_rate():
    """‏دي الحاجة الأساسية: نزول ممتاز بس مجاش من ٧٠ يوم.

    لو اللوحة قالت "نازل كويس"، الدكتور هيعدّي عليه وهو أكتر واحد
    محتاج يتكلم معاه -- والرقم اللي الحكم مبني عليه عمره ٧٠ يوم.
    """
    b = followup.board([_visit("e", "غايب", 88.0, 70),
                        _visit("e", "غايب", 92.0, 98)], today=NOW)
    r = _row(b, "e")
    assert r["state"] == "lapsed", r
    assert r["tone"] == "bad", r
    assert "70" in r["note"], r["note"]


def test_a_client_past_the_review_date_is_flagged_even_while_on_track():
    """‏بين ٢٨ و٥٥ يوم: لسه مش غايب، بس ميعاد المراجعة عدّى."""
    b = followup.board([_visit("f", "ميعاده", 94.0, 35),
                        _visit("f", "ميعاده", 97.0, 56)], today=NOW)
    r = _row(b, "f")
    assert r["state"] == "due", r
    assert r["tone"] == "warn", r


def test_a_bad_rate_is_not_hidden_behind_an_overdue_review():
    """‏العكس: اللي ميعاده عدّى **و**واقف، الحكم الأهم إنه واقف.

    "ميعاده عدّى" بيحل محل "ماشي" بس -- لأن ساعتها التذكرة هي الخبر
    الوحيد. لكن لو واقف أو رجع زاد، ده خبر أكبر من التذكرة.
    """
    b = followup.board([_visit("g", "واقف ومتأخر", 90.0, 40),
                        _visit("g", "واقف ومتأخر", 90.1, 75)], today=NOW)
    r = _row(b, "g")
    assert r["state"] == "plateau", r


def test_a_client_who_never_came_back_after_one_visit_is_chased():
    """‏زيارة واحدة من ٩٠ يوم مش "زيارة واحدة" -- ده واحد ضاع."""
    b = followup.board([_visit("h", "ضاع", 100.0, 90)], today=NOW)
    r = _row(b, "h")
    assert r["state"] == "lapsed", r


# ── الترتيب والعدّ ───────────────────────────────────────────────────

def test_the_board_is_ordered_by_who_needs_the_doctor():
    """‏الترتيب هو الفايدة كلها: ستين صف، واللي محتاج تدخّل فوق."""
    rows = (
        [_visit("ok", "ماشي", 94.0, 2), _visit("ok", "ماشي", 97.0, 23)] +
        [_visit("st", "واقف", 90.1, 3), _visit("st", "واقف", 90.0, 31)] +
        [_visit("gone", "غايب", 88.0, 70), _visit("gone", "غايب", 92.0, 98)]
    )
    order = [r["client_key"] for r in followup.board(rows, today=NOW)["rows"]]
    assert order == ["gone", "st", "ok"], order


def test_the_counts_match_the_rows():
    """‏المربعات فوق فلاتر؛ لو عددها مش مطابق للصفوف، الفلتر بيكدب."""
    rows = (
        [_visit("ok", "ماشي", 94.0, 2), _visit("ok", "ماشي", 97.0, 23)] +
        [_visit("st", "واقف", 90.1, 3), _visit("st", "واقف", 90.0, 31)] +
        [_visit("up", "رجع", 93.0, 4), _visit("up", "رجع", 90.0, 32)] +
        [_visit("new", "جديد", 100.0, 3)]
    )
    b = followup.board(rows, today=NOW)
    tones = [r["tone"] for r in b["rows"]]
    assert b["counts"]["total"] == 4, b["counts"]
    assert b["counts"]["needs"] == tones.count("bad"), b["counts"]
    assert b["counts"]["watch"] == tones.count("warn"), b["counts"]
    assert b["counts"]["ok"] == tones.count("good"), b["counts"]


def test_the_whole_history_is_shown_next_to_the_last_period():
    """‏الحكم على آخر فترة، بس الدكتور لازم يشوف المشوار كله جنبه --
    عشان "واقف" على واحد نزل ١٢ كيلو حاجة غير "واقف" على واحد لسه مكانه."""
    rows = [_visit("i", "مشوار", 88.0, 3),
            _visit("i", "مشوار", 88.2, 33),
            _visit("i", "مشوار", 100.0, 180)]
    r = _row(followup.board(rows, today=NOW), "i")
    assert r["state"] == "plateau", r          # ‏الحكم على آخر فترة
    assert r["total_change"] == -12.0, r       # ‏والمشوار ظاهر
    assert r["first_weight"] == 100.0, r
    assert r["visits"] == 3, r


# ── البيانات الناقصة ────────────────────────────────────────────────

def test_a_visit_with_no_weight_does_not_crash_the_board():
    """‏الوزن مش مطلوب في فورم التوليد، فممكن يكون فاضي."""
    rows = [_visit("j", "بدون وزن", None, 3),
            _visit("j", "بدون وزن", None, 33)]
    r = _row(followup.board(rows, today=NOW), "j")
    assert r["state"] in ("due", "single"), r
    assert r["last_delta"] is None, r


def test_rows_with_no_client_key_are_dropped_not_grouped_together():
    """‏مفتاح فاضي معناه الزيارة اتسجّلت من غير اسم -- لو جمّعناهم
    مع بعض هيبقى "عميل" واحد فيه ناس مختلفة، وده أسوأ من إننا نشيلهم."""
    rows = [_visit(None, "مجهول", 90.0, 3), _visit("", "مجهول", 80.0, 4),
            _visit("k", "معروف", 90.0, 3)]
    b = followup.board(rows, today=NOW)
    assert [r["client_key"] for r in b["rows"]] == ["k"], b["rows"]


def test_the_name_shown_is_the_one_from_the_latest_visit():
    """‏لو الدكتور صلّح كتابة الاسم في زيارة جديدة، اللوحة تعرض الجديد."""
    rows = [_visit("l", "محمد علي", 90.0, 3),
            _visit("l", "محمد على", 93.0, 33)]
    assert _row(followup.board(rows, today=NOW), "l")["client_name"] == "محمد علي"


# ── الصفحة نفسها ────────────────────────────────────────────────────

def _page(state=""):
    """‏الصفحة الحقيقية بزيارات حقيقية في القاعدة.

    التواريخ هنا محسوبة من **النهارده الحقيقي**، مش من NOW الثابتة:
    الصفحة بتنادي board() من غير today، فبتقيس من لحظتها. أول نسخة
    من الاختبار سجّلت التواريخ بالنسبة لـNOW، فالزيارات طلعت عمرها
    شهور والكل بقى "غاب" -- والفلتر رجع فاضي.
    """
    import core
    real = dt.datetime.now()

    def _rel(key, name, weight, days_ago):
        v = _visit(key, name, weight, days_ago)
        v["created_at"] = (real - dt.timedelta(days=days_ago)
                           ).strftime("%Y-%m-%d %H:%M:%S")
        return v

    with A.app.app_context():
        core.db_run("DELETE FROM plan_visits")
        for v in ([_rel("zz", "واقف", 90.1, 3), _rel("zz", "واقف", 90.0, 31)] +
                  [_rel("yy", "ماشي", 94.0, 2), _rel("yy", "ماشي", 97.0, 23)]):
            core.db_run(
                """INSERT INTO plan_visits
                   (user_id, client_key, client_name, weight, height, age,
                    gender, activity, tdee, goal_cal, goal_type, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (1, v["client_key"], v["client_name"], v["weight"],
                 v["height"], v["age"], v["gender"], v["activity"],
                 v["tdee"], v["goal_cal"], v["goal_type"], v["created_at"]))
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = 1
        s["role"] = "admin"
        s["lang"] = "ar"
    return c.get("/followups" + ("?state=" + state if state else ""))


def test_the_page_renders_the_board_not_the_old_date_list():
    r = _page()
    assert r.status_code == 200, r.status_code
    html = r.get_data(as_text=True)
    assert "واقف" in html, "‏الحالة مش ظاهرة على الصفحة"
    assert "محتاج تدخّل" in html, "‏مربعات الفلترة مش موجودة"


def test_the_filter_actually_filters():
    """‏المربعات فوق لازم تفلتر فعلاً، مش تبقى أرقام مرسومة."""
    html = _page("good").get_data(as_text=True)
    body = html[html.index("<tbody>"):html.index("</tbody>")]
    assert "ماشي" in body, body[:400]
    assert "واقف" not in body, "‏الفلتر مابيفلترش -- الواقف لسه ظاهر"


def test_the_page_does_not_load_the_plans_to_draw_a_list():
    """‏كان SELECT * -- يعني خطة أسبوع كاملة (plan_json) لكل زيارة
    بتتقرا عشان نرسم جدول مافيهوش ولا وجبة."""
    import inspect
    import core
    # ‏الفحص على الكود من غير الشرح: الـdocstring نفسه بيحكي إن
    # SELECT * كان المشكلة، فلو فحصنا المصدر كله الشرح بيوقّع الاختبار.
    src = inspect.getsource(core.all_visits)
    src = re.sub(r'""".*?"""', "", src, flags=re.S)
    assert "SELECT *" not in src, "‏رجعت SELECT *"
    assert "plan_json" not in src, "‏الخطة بتتحمّل على صفحة مش محتاجاها"


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

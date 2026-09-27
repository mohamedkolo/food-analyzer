# -*- coding: utf-8 -*-
"""‏فحص سريع بدون اسم، وتصليح اسم أو رقم اتكتب غلط.

حاجتين طلبهم الدكتور:

  «ما ممكن يكون فحص مجانى عادى مش لازم يبقى متسجل الرقم والاسم»
  «عايز اعرف اعدل فى المتابعين الى بضفهم -- اقدر اعدل الاسم لو متسجل
   غلط او الرقم»

الأولى: الاسم كان required في الفورم، فمكانش ينفع يولّد خطة من غيره.
والتانية أصعب من UPDATE عادي: مفتاح العميل **مبني** على الاسم والموبايل،
فتغيير الاسم لازم يغيّر المفتاح في كل الزيارات -- وإلا الملف يتقسم نصين
والتقدّم يتحسب غلط.

Run with:  python3 tests/test_quick_check_and_renaming.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_quickcheck_test.db"

import app as A          # noqa: E402
import core              # noqa: E402
from followup import client_key   # noqa: E402

BASE = {"age": "29", "gender": "انثى", "height": "165", "weight": "78.4",
        "goal_cal": "1400", "tdee": "2000", "activity_mult": "1.55",
        "protein_per_kg": "1.6", "fat_pct_cal": "30", "goal_type": "weight_loss",
        "culture": "مصري", "zigzag_mode": "classic", "diet_plan_type": "standard"}


def _staff():
    A.app.config["WTF_CSRF_ENABLED"] = False
    client = A.app.test_client()
    page = client.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', page).group(1)
    client.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                                "password": "pw123456", "csrf_token": token})
    return client


def _uid():
    row = core.db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")
    return row["id"]


def _wipe():
    core.db_run("DELETE FROM plan_visits WHERE user_id=?", (_uid(),))


def test_a_plan_generates_with_no_name_and_no_phone():
    """‏الفحص السريع: الخطة تتولّد وتتطبع من غير تسجيل حد."""
    client = _staff()
    response = client.post("/generate", data=dict(BASE), follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert response.headers["Location"].endswith("/preview"), response.headers

    page = client.get("/preview").get_data(as_text=True)
    assert "معاينة الخطة" in page, "‏مافيش جدول"
    # ‏ومابيسيبش سطر الاسم فاضي -- بيقول إنه فحص سريع
    assert "فحص سريع" in page, "‏سطر الاسم طلع فاضي"

    pdf = client.get("/download_pdf")
    assert pdf.status_code == 200 and pdf.get_data()[:4] == b"%PDF", pdf.status_code


def test_the_form_does_not_demand_a_name_any_more():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "templates", "generate.html"),
              encoding="utf-8") as fh:
        page = fh.read()
    tag = re.search(r'<input[^>]*id="nameField"[^>]*>', page)
    assert tag, "‏خانة الاسم مش موجودة"
    assert "required" not in tag.group(0), tag.group(0)
    # ‏والدكتور لازم يعرف إن سيبها فاضية معناه مافيش ملف متابعة
    assert "مش هيتعمل ملف متابعة" in page, "‏مافيش أي كلام عن نتيجة سيبها فاضية"


def test_a_quick_check_does_not_open_a_follow_up_file():
    """‏ملف متابعة من غير اسم = ملف مالوش صاحب. تسجيل كل الفحوص السريعة
    في ملف واحد بيبوّظ حساب التقدّم لكل العملاء."""
    _wipe()
    client = _staff()
    client.post("/generate", data=dict(BASE))
    client.post("/api/save-plan")
    assert core.recent_clients(_uid()) == [], core.recent_clients(_uid())
    # ‏وباسم: الملف بيتعمل عادي
    client.post("/generate", data=dict(BASE, name="نورة سيد"))
    client.post("/api/save-plan")
    files = core.recent_clients(_uid())
    assert len(files) == 1 and files[0]["client_name"] == "نورة سيد", files


def _make_file(client, name, phone=""):
    _wipe()
    client.post("/generate", data=dict(BASE, name=name, phone=phone))
    client.post("/api/save-plan")
    return core.recent_clients(_uid())[0]["client_key"]


def test_a_misspelled_name_can_be_fixed_across_every_visit():
    client = _staff()
    key = _make_file(client, "نوره سييد", "01011112222")
    # ‏زيارة تانية في نفس الملف. **جلسة جديدة** بالقصد: التطبيق بيمنع إن
    # نفس الجدول يتسجّل زيارتين في نفس الجلسة (الدكتور بيظبّط ويولّد تاني)،
    # فالزيارة التانية الحقيقية بتبقى في يوم تاني وجلسة تانية.
    later = _staff()
    later.post("/generate", data=dict(BASE, name="نوره سييد",
                                      phone="01011112222", weight="77.0"))
    later.post("/api/save-plan")
    assert core.recent_clients(_uid())[0]["visits"] == 2, core.recent_clients(_uid())

    response = client.post("/followups/%s/rename" % key,
                           data={"name": "نورة سيد", "phone": "01011112222"},
                           follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert "ok=1" in response.headers["Location"], response.headers["Location"]

    files = core.recent_clients(_uid())
    assert len(files) == 1, "‏الملف اتقسم: %s" % files
    assert files[0]["client_name"] == "نورة سيد", files[0]
    assert files[0]["visits"] == 2, "‏زيارة ضاعت: %s" % files[0]
    # ‏والمفتاح اتحدّث، وإلا الزيارة الجاية بتفتح ملف تالت
    assert files[0]["client_key"] == client_key("نورة سيد", "01011112222"), files[0]


def test_the_phone_can_be_fixed_and_the_key_follows_it():
    """‏المفتاح فيه آخر ٦ أرقام من الموبايل، فتغييره بيغيّر المفتاح."""
    client = _staff()
    key = _make_file(client, "منى حسن", "01055556666")
    client.post("/followups/%s/rename" % key,
                data={"name": "منى حسن", "phone": "01077778888"})
    files = core.recent_clients(_uid())
    assert len(files) == 1, files
    assert files[0]["client_key"] == client_key("منى حسن", "01077778888"), files[0]
    row = core.db_row("SELECT phone FROM plan_visits WHERE user_id=? LIMIT 1", (_uid(),))
    assert row["phone"] == "01077778888", row


def test_a_later_visit_lands_in_the_same_file_after_the_fix():
    """‏ده اللي بيتأكد إن التصليح مانفعش نصه: الزيارة الجاية بالاسم الصح
    لازم تكمّل نفس الملف، مش تفتح واحد جديد."""
    client = _staff()
    key = _make_file(client, "سارة على", "01099998888")
    client.post("/followups/%s/rename" % key,
                data={"name": "سارة علي", "phone": "01099998888"})
    later = _staff()          # ‏زيارة جديدة في جلسة جديدة، زي الواقع
    later.post("/generate", data=dict(BASE, name="سارة علي",
                                      phone="01099998888", weight="76.0"))
    later.post("/api/save-plan")
    files = core.recent_clients(_uid())
    assert len(files) == 1, "‏الزيارة فتحت ملف جديد: %s" % files
    assert files[0]["visits"] == 2, files[0]
    assert files[0]["last_no"] == 2, "‏ترقيم الزيارات اتلخبط: %s" % files[0]


def test_renaming_onto_an_existing_file_is_refused_not_merged():
    """‏دمج ملفين بيغيّر ترقيم الزيارات ومفيش رجوع. فبنوقف ونقول للدكتور."""
    client = _staff()
    _wipe()
    client.post("/generate", data=dict(BASE, name="هدى كامل", phone="01000000001"))
    client.post("/api/save-plan")
    client.post("/generate", data=dict(BASE, name="هدي كامل", phone="01000000002"))
    client.post("/api/save-plan")
    files = {f["client_name"]: f["client_key"] for f in core.recent_clients(_uid())}
    assert len(files) == 2, files

    wrong = files["هدي كامل"]
    response = client.post("/followups/%s/rename" % wrong,
                           data={"name": "هدى كامل", "phone": "01000000001"},
                           follow_redirects=False)
    assert "err=exists" in response.headers["Location"], response.headers["Location"]
    # ‏ومافيش حاجة اتغيرت
    after = {f["client_name"] for f in core.recent_clients(_uid())}
    assert after == {"هدى كامل", "هدي كامل"}, after
    # ‏والصفحة بتشرح الحالة وبتقول إن الدمج ممكن لو طلبه
    page = client.get("/followups/%s?err=exists" % wrong).get_data(as_text=True)
    assert "ملف متابعة تاني" in page, "‏الرسالة مش بتشرح"


def test_an_empty_name_is_refused_and_nothing_is_lost():
    client = _staff()
    key = _make_file(client, "ليلى فؤاد", "01033334444")
    response = client.post("/followups/%s/rename" % key,
                           data={"name": "   ", "phone": "01033334444"},
                           follow_redirects=False)
    assert "err=name" in response.headers["Location"], response.headers["Location"]
    files = core.recent_clients(_uid())
    assert len(files) == 1 and files[0]["client_name"] == "ليلى فؤاد", files


def test_only_staff_can_rename_and_only_their_own_files():
    client = _staff()
    key = _make_file(client, "أمل سمير", "01022223333")

    anon = A.app.test_client()
    response = anon.post("/followups/%s/rename" % key, data={"name": "حد تاني"})
    assert response.status_code in (301, 302, 401, 403), response.status_code
    files = core.recent_clients(_uid())
    assert files[0]["client_name"] == "أمل سمير", files[0]

    # ‏ملف مش موجود: بيرجّع للقايمة، مش ٥٠٠
    gone = client.post("/followups/nobody|000000/rename",
                       data={"name": "حد", "phone": ""}, follow_redirects=False)
    assert gone.status_code == 302, gone.status_code
    assert gone.headers["Location"].endswith("/followups"), gone.headers["Location"]


def test_the_page_offers_the_edit_without_leaving_the_file():
    client = _staff()
    key = _make_file(client, "ريم عادل", "01044445555")
    page = client.get("/followups/%s" % key).get_data(as_text=True)
    assert 'id="fuEditForm"' in page, "‏مافيش فورم تعديل"
    assert 'name="csrf_token"' in page, "‏الفورم بدون توكن"
    assert "01044445555" in page, "‏الرقم الحالي مش معروض للتعديل"
    assert "ريم عادل" in page
    # ‏وبيقول إن التعديل بيسري على كل الزيارات، مش الزيارة اللي شايفها
    assert "كل زيارات الملف" in page, "‏مش بيقول إن التعديل على الملف كله"


# ═══════════════════════════════════════════════════════════════════════
# ‏تصليح الزيارات: تعديل أرقامها، مسح زيارة غلط، ودمج ملفين
#
# ‏الرقم اللي اتدخّل غلط مش مشكلة في سطر واحد: حساب التقدّم كله مبني عليه،
# فوزن ٩٥ بالغلط بيخلي الزيارة تبان "زيادة ١٨ كيلو" واللي بعديها "نزول ١٩".
# ═══════════════════════════════════════════════════════════════════════

def _three_visits(name="نورة سيد", phone="01011112222", weights=("78.4", "77.0", "95.0")):
    """‏تلات زيارات، كل واحدة في جلسة لوحدها -- زي الواقع (التطبيق بيمنع
    إن نفس الجدول يتسجّل زيارتين في نفس الجلسة)."""
    _wipe()
    for weight in weights:
        client = _staff()
        client.post("/generate", data=dict(BASE, name=name, phone=phone,
                                           weight=weight, fat_pct="38.2"))
        client.post("/api/save-plan")
    key = core.recent_clients(_uid())[0]["client_key"]
    return key, core.visits_for(_uid(), key, limit=9)


def _visit_with(rows, weight):
    return [row for row in rows if row["weight"] == weight][0]


def test_a_wrong_number_in_a_visit_can_be_corrected():
    key, rows = _three_visits()
    wrong = _visit_with(rows, 95.0)
    client = _staff()
    response = client.post("/followups/%s/visit/%s/edit" % (key, wrong["id"]),
                           data={"weight": "76.0", "height": "165",
                                 "fat_pct": "36.0", "age": "29",
                                 "visit_notes": "اتصلّح"},
                           follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert "ok=visit" in response.headers["Location"], response.headers["Location"]

    fixed = core.db_row("SELECT * FROM plan_visits WHERE id=?", (wrong["id"],))
    assert fixed["weight"] == 76.0, fixed["weight"]
    assert fixed["fat_pct"] == 36.0, fixed["fat_pct"]
    assert fixed["visit_notes"] == "اتصلّح", fixed["visit_notes"]
    # ‏الـBMI بيتحسب من الوزن والطول، مابيتكتبش بالإيد
    assert abs(fixed["bmi"] - 76.0 / (1.65 ** 2)) < 0.1, fixed["bmi"]


def test_correcting_a_visit_fixes_the_progress_that_hangs_off_it():
    """‏ده اللي بيفرق فعلاً: التقدّم بيتحسب وقت العرض من الزيارات، فتصليح
    رقم واحد بيصلّح السلسلة كلها -- من غير ما نلمس أي حساب."""
    import followup
    key, rows = _three_visits()
    wrong = _visit_with(rows, 95.0)
    ordered = sorted(rows, key=lambda row: row["visit_no"])
    before = followup.assess(ordered[-2], ordered[-1], "ar")
    assert before["delta"] > 0, "‏المفروض الزيارة الغلط تبان زيادة: %s" % before

    client = _staff()
    client.post("/followups/%s/visit/%s/edit" % (key, wrong["id"]),
                data={"weight": "76.0", "height": "165", "fat_pct": "36.0",
                      "age": "29"})
    again = sorted(core.visits_for(_uid(), key, limit=9),
                   key=lambda row: row["visit_no"])
    after = followup.assess(again[-2], again[-1], "ar")
    assert after["delta"] < 0, "‏بعد التصليح المفروض تبان نزول: %s" % after


def test_a_visit_edit_refuses_nonsense_and_changes_nothing():
    key, rows = _three_visits()
    target = _visit_with(rows, 77.0)
    client = _staff()
    for payload, why in (({"weight": "abc"}, "number"),
                         ({"weight": "-5"}, "number"),
                         ({"weight": ""}, "weight")):
        response = client.post("/followups/%s/visit/%s/edit" % (key, target["id"]),
                               data=payload, follow_redirects=False)
        assert "err=%s" % why in response.headers["Location"], (payload, response.headers)
        still = core.db_row("SELECT weight FROM plan_visits WHERE id=?", (target["id"],))
        assert still["weight"] == 77.0, (payload, still)


def test_a_visit_recorded_by_mistake_can_be_deleted_and_the_rest_renumbered():
    key, rows = _three_visits()
    victim = _visit_with(rows, 95.0)
    client = _staff()
    response = client.post("/followups/%s/visit/%s/delete" % (key, victim["id"]),
                           follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert "ok=deleted" in response.headers["Location"], response.headers["Location"]

    left = core.visits_for(_uid(), key, limit=9)
    assert len(left) == 2, left
    assert 95.0 not in [row["weight"] for row in left], left
    # ‏الترقيم لازم يترتّب: فجوة في الأرقام معناها الدكتور يقرا "زيارة ٣"
    # وهي التانية
    assert sorted(row["visit_no"] for row in left) == [1, 2], [
        row["visit_no"] for row in left]


def test_deleting_the_only_visit_closes_the_file():
    _wipe()
    client = _staff()
    client.post("/generate", data=dict(BASE, name="ملف واحد", phone="01000001111"))
    client.post("/api/save-plan")
    key = core.recent_clients(_uid())[0]["client_key"]
    only = core.visits_for(_uid(), key, limit=1)[0]
    response = client.post("/followups/%s/visit/%s/delete" % (key, only["id"]),
                           follow_redirects=False)
    assert response.headers["Location"].endswith("/followups"), response.headers
    assert core.recent_clients(_uid()) == [], core.recent_clients(_uid())


def test_two_files_for_one_client_can_be_merged_into_one_history():
    """‏نفس العميل باسمين = ملفين، وكل واحد بيحسب تقدّمه لوحده. يعني نزول
    ٦ كيلو على ٣ زيارات بيتقسم نصين ومحدش شايف الصورة كاملة."""
    key, _rows = _three_visits()
    client = _staff()
    client.post("/generate", data=dict(BASE, name="نوره سييد", phone="01099998888"))
    client.post("/api/save-plan")
    files = core.recent_clients(_uid())
    assert len(files) == 2, files
    duplicate = [f for f in files if f["client_name"] == "نوره سييد"][0]["client_key"]

    client = _staff()
    response = client.post("/followups/%s/merge" % duplicate, data={"into": key},
                           follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert "ok=merged" in response.headers["Location"], response.headers["Location"]

    after = core.recent_clients(_uid())
    assert len(after) == 1, "‏الدمج ساب ملفين: %s" % after
    assert after[0]["visits"] == 4, after[0]
    merged = core.visits_for(_uid(), key, limit=9)
    # ‏الترقيم بترتيب التاريخ، بدون تكرار -- وإلا "زيارة ١" تبان مرتين
    assert sorted(row["visit_no"] for row in merged) == [1, 2, 3, 4], [
        row["visit_no"] for row in merged]
    assert len({row["client_name"] for row in merged}) == 1, merged


def test_a_merge_needs_a_real_other_file():
    key, _rows = _three_visits()
    client = _staff()
    for payload in ({"into": ""}, {"into": key}, {"into": "nobody|000000"}):
        response = client.post("/followups/%s/merge" % key, data=payload,
                               follow_redirects=False)
        assert "err=merge" in response.headers["Location"], (payload, response.headers)
    assert core.recent_clients(_uid())[0]["visits"] == 3, core.recent_clients(_uid())


def test_nobody_can_touch_a_visit_that_is_not_theirs():
    key, rows = _three_visits()
    target = rows[0]

    anon = A.app.test_client()
    for path in ("edit", "delete"):
        response = anon.post("/followups/%s/visit/%s/%s" % (key, target["id"], path),
                             data={"weight": "1"})
        assert response.status_code in (301, 302, 401, 403), (path, response.status_code)
    assert core.db_row("SELECT weight FROM plan_visits WHERE id=?",
                       (target["id"],))["weight"] == target["weight"]

    # ‏وزيارة من ملف تاني: المسار بيحدّد الملف، فلازم يتطابق
    client = _staff()
    response = client.post("/followups/%s/visit/%s/edit" % ("ملف|تاني", target["id"]),
                           data={"weight": "1"}, follow_redirects=False)
    assert response.headers["Location"].endswith("/followups"), response.headers
    assert core.db_row("SELECT weight FROM plan_visits WHERE id=?",
                       (target["id"],))["weight"] == target["weight"]


def test_the_page_offers_all_three_and_warns_before_the_ones_that_cannot_be_undone():
    key, rows = _three_visits()
    client = _staff()
    # ‏ملف تاني عشان زرار الدمج يظهر
    client.post("/generate", data=dict(BASE, name="حد تاني", phone="01055554444"))
    client.post("/api/save-plan")
    page = client.get("/followups/%s" % key).get_data(as_text=True)

    assert 'data-visit-edit="%s"' % rows[0]["id"] in page, "‏مافيش زرار تعديل للزيارة"
    assert 'id="visitForm%s"' % rows[0]["id"] in page, "‏مافيش فورم تعديل"
    assert "/visit/%s/delete" % rows[0]["id"] in page, "‏مافيش زرار مسح"
    assert 'id="fuMergeForm"' in page, "‏مافيش فورم دمج"
    # ‏المسح والدمج مالهمش رجوع، فلازم تأكيد قبلهم
    assert page.count("confirm(") >= 2, "‏مافيش تأكيد قبل اللي مالوش رجوع"
    # ‏وكل فورم عليه توكن
    assert page.count('name="csrf_token"') >= 3, page.count('name="csrf_token"')


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
            print(f"  FAIL  {name}\n        {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

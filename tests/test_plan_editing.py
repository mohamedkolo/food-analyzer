# -*- coding: utf-8 -*-
"""Building a plan is iterative, and the app used to punish that.

Every POST to /generate wrote a saved plan AND a follow-up visit. Adjusting a
client's weight and regenerating three times left three plans and three
visits dated the same day -- which does not just clutter the list, it
corrupts the follow-up maths, because the next visit compares against a
"previous visit" that is really the same appointment. And going back to edit
came back to an empty form, so the details had to be typed again.

Run with:  python3 tests/test_plan_editing.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import app as A  # noqa: E402
import core  # noqa: E402

FORM = {
    "action": "generate", "name": "أحمد على", "phone": "01012345678",
    "age": "32", "gender": "ذكر", "height": "176", "weight": "95",
    "tdee": "2350", "goal_cal": "1750", "goal_type": "weight_loss",
    "culture": "مصري", "diet_plan_type": "standard", "activity_mult": "1.55",
    "protein_per_kg": "1.8", "fat_pct_cal": "30", "zigzag_mode": "off",
}


def _staff_client():
    c = A.app.test_client()
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]*)"',
                    c.get("/login").get_data(as_text=True)).group(1)
    c.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                           "password": "pw123456", "csrf_token": tok})
    return c


def _counts():
    return (core.db_row("SELECT COUNT(*) AS c FROM saved_plans")["c"],
            core.db_row("SELECT COUNT(*) AS c FROM plan_visits")["c"])


def _generate(c, **over):
    A.app.config["WTF_CSRF_ENABLED"] = False
    return c.post("/generate", data=dict(FORM, **over))


def test_generating_repeatedly_does_not_record_anything():
    c = _staff_client()
    before = _counts()
    for weight in ("95", "95", "94"):
        assert _generate(c, weight=weight).status_code == 302
    assert _counts() == before, (
        "adjusting the plan wrote saved plans or follow-up visits before "
        "the doctor asked for it")


def test_saving_records_once_no_matter_how_often_it_is_pressed():
    c = _staff_client()
    _generate(c)
    plans, visits = _counts()

    r = c.post("/api/save-plan")
    assert r.status_code == 200 and r.get_json()["ok"]
    assert _counts() == (plans + 1, visits + 1), "saving did not record the visit"

    after_first = _counts()
    c.post("/api/save-plan")
    c.post("/api/save-plan")
    assert _counts() == after_first, "pressing Save again created duplicates"

    # a link is also an "I am done" signal, and must not duplicate either
    assert c.post("/api/plan-link").get_json()["ok"]
    assert _counts() == after_first, "creating a link created a second record"

    # nor does downloading the PDF
    assert c.get("/download_pdf").status_code == 200
    assert _counts() == after_first, "downloading the PDF created a second record"


def test_adjusting_after_saving_updates_the_same_visit():
    """The doctor saves, spots a wrong weight, fixes it and saves again. That
    is one appointment corrected -- not two."""
    # the suites share one database, so this needs a client of its own or an
    # earlier test's rows get counted as history
    who = {"name": "مريض التصحيح", "phone": "01055554444"}
    # ‏وكمان بينضّف سطوره الأول: الاختبار بيعدّ زيارات المفتاح ده، فلو
    # القاعدة فيها سطر من تشغيلة قديمة كان بيفشل ويورّي باگ مش موجود.
    key = __import__("followup").client_key(who["name"], who["phone"])
    core.db_run("DELETE FROM plan_visits WHERE client_key=?", (key,))
    c = _staff_client()
    _generate(c, weight="95", **who)
    c.post("/api/save-plan")
    plans, visits = _counts()

    _generate(c, weight="93", **who)
    c.post("/api/save-plan")
    assert _counts() == (plans, visits), "the correction was filed as a new visit"

    rows = core.visits_for(1, key)
    assert len(rows) == 1, f"{len(rows)} visits recorded for one appointment"
    assert float(rows[0]["weight"]) == 93.0, "the visit kept the old weight"


def test_a_different_client_starts_a_new_record():
    c = _staff_client()
    _generate(c)
    c.post("/api/save-plan")
    plans, visits = _counts()

    _generate(c, name="سارة محمد", phone="01199998888", weight="70")
    c.post("/api/save-plan")
    assert _counts() == (plans + 1, visits + 1), (
        "a different client was written over the previous one")


def test_going_back_to_edit_finds_the_form_filled_in():
    """Only the edit link refills the form -- /generate?edit=1.

    A plain /generate is a new client: it used to come back carrying the last
    plan's data, so the next person's plan was silently built on the previous
    one's conditions. The edit button on the preview page now asks for the
    refill explicitly, and that is what this checks.
    """
    c = _staff_client()
    _generate(c, name="أحمد على", weight="95", height="176", age="32")
    body = c.get("/generate?edit=1").get_data(as_text=True)
    for value in ("أحمد على", "95", "176", "32", "01012345678"):
        assert f'value="{value}"' in body, f"{value} was lost from the form"
    # and the choices too, not just the text boxes
    assert re.search(r'name="goal_type" value="weight_loss"[^>]*checked', body)
    assert re.search(r'name="culture" value="مصري"[^>]*checked', body)


def test_every_field_the_plan_was_built_from_comes_back_on_edit():
    """‏رجوع للتعديل لازم يلاقي كل حاجة، مش معظمها.

    خانة مابترجعش = الدكتور بيرجع يعدّل الوزن، يدوس توليد، والخانة دي بترجع
    للافتراضي في صمت. حصل فعلاً مع تدوير السعرات: النمط كان بيرجع off من غير
    أي رسالة، فالخطة التانية تطلع مسطحة -- والدكتور فاكر التدوير شغال.
    """
    c = _staff_client()
    extra = {
        "zigzag_mode": "classic",
        "insulin_tdd": "42",
        "liked_foods": "شوفان، سلمون",
        "disliked_foods": "كبدة، باذنجان",
        "notes": "بدون فلفل حار",
        "visit_notes": "بيشتكي من انتفاخ",
    }
    _generate(c, name="مريض التدوير", phone="01066667777", **extra)
    body = c.get("/generate?edit=1").get_data(as_text=True)

    # ‏نمط التدوير مختار فعلاً في الـselect بتاعه
    sel = re.search(r'name="zigzag_mode".*?</select>', body, re.S)
    assert sel, "‏خانة تدوير السعرات مش في الفورم"
    chosen = re.search(r'value="([^"]+)" selected', sel.group(0))
    assert chosen and chosen.group(1) == "classic", (
        "‏نمط التدوير رجع %s مش classic -- التدوير بيضيع في صمت"
        % (chosen.group(1) if chosen else "مفيش"))

    for field, value in extra.items():
        if field == "zigzag_mode":
            continue
        assert value in body, "‏%s ضاع لما رجعنا نعدّل" % field


def test_the_form_has_no_field_that_silently_forgets_itself():
    """‏كل خانة بيتبنى عليها الجدول لازم تقرا prev.

    الاختبار اللي فوق بيجرّب الخانات اللي عرفناها. ده بيمسك الجديدة: أي
    حد يضيف خانة للفورم وينسى prev بتاعتها، يفشل هنا مش عند الدكتور.
    """
    html = open(os.path.join(HERE, "templates", "generate.html"),
                encoding="utf-8").read()
    # ‏خانات محسوبة بالجافاسكريبت، مش محفوظة ومالهاش لازمة ترجع
    DERIVED = {"carb_pct_cal"}
    stored = set(re.findall(r'"([a-z_]+)": request\.form\.get',
                            open(os.path.join(HERE, "routes_plans.py"),
                                 encoding="utf-8").read()))
    stored |= set(re.findall(r'"([a-z_]+)": request\.form\.getlist',
                             open(os.path.join(HERE, "routes_plans.py"),
                                  encoding="utf-8").read()))
    missing = []
    for name in sorted(set(re.findall(r'name="([a-z_]+)"', html))):
        if name in DERIVED or name not in stored:
            continue
        i = html.index('name="%s"' % name)
        # ‏الـselect بنبص جوه بلوكه، والباقي في نفس الوسم أو اللي بعده
        end = html.index("</select>", i) if '<select' in html[max(0, i-200):i]               else i + 400
        if "prev." not in html[max(0, i - 200):end]:
            missing.append(name)
    assert not missing, (
        "‏الخانات دي بتضيع لما ترجع تعدّل: %s" % "، ".join(missing))


def test_a_plain_generate_is_empty_even_right_after_a_plan():
    """The other half: the form must not open on the last client's data."""
    c = _staff_client()
    # ‏هدف مش الافتراضي، عشان لو رجع يبقى رجع من الخطة اللي فاتت
    _generate(c, name="أحمد على", weight="95", height="176", age="32",
              goal_type="muscle_gain")
    body = c.get("/generate").get_data(as_text=True)
    for value in ("أحمد على", "95", "176", "32"):
        assert f'value="{value}"' not in body, (
            f"{value} came back in a fresh form -- the next client inherits it")
    # ‏الراديو بيرجع لافتراضيه (تخسيس)، مش لهدف العميل اللي فات
    assert not re.search(r'name="goal_type" value="muscle_gain"[^>]*checked', body), (
        "the goal was pre-picked from the last plan")
    assert re.search(r'name="goal_type" value="weight_loss"[^>]*checked', body), (
        "the goal group opens with nothing picked")
    prev = c.get("/preview").get_data(as_text=True)
    assert "/generate?edit=1" in prev, (
        "the edit button no longer asks for the refill")


def test_a_meal_can_be_swapped_with_the_one_above_it():
    c = _staff_client()
    _generate(c)
    with c.session_transaction() as s:
        before = dict(s["current_plan"][0])

    r = c.post("/move_meal", data={"day_idx": "0", "meal_type": "lunch",
                                   "other_type": "breakfast"})
    assert r.status_code == 200 and r.get_json()["ok"]

    with c.session_transaction() as s:
        after = s["current_plan"][0]
    assert after["breakfast"] == before["lunch"], "the meals did not swap"
    assert after["lunch"] == before["breakfast"]
    assert after["dinner"] == before["dinner"], "an untouched meal moved"


def test_moving_a_meal_refuses_nonsense():
    c = _staff_client()
    _generate(c)
    for payload in ({"day_idx": "99", "meal_type": "lunch", "other_type": "breakfast"},
                    {"day_idx": "0", "meal_type": "nope", "other_type": "breakfast"},
                    {"day_idx": "0", "meal_type": "lunch", "other_type": ""},
                    {"day_idx": "abc", "meal_type": "lunch", "other_type": "breakfast"}):
        r = c.post("/move_meal", data=payload)
        assert r.status_code >= 400 or not r.get_json().get("ok"), (
            f"{payload} was accepted")


def test_the_two_meal_system_ends_at_lunch():
    """Some people eat breakfast and finish at lunch. That is a real pattern,
    not a three-meal plan with dinner deleted."""
    from meal_database import DIET_PLAN_TYPES
    assert "two_meals" in DIET_PLAN_TYPES
    info = DIET_PLAN_TYPES["two_meals"]
    assert info["meals"] == ["breakfast", "lunch"]
    for field in ("name", "name_en", "description", "description_en",
                  "meal_labels", "meal_labels_en", "meal_emojis"):
        assert info.get(field), f"two_meals is missing {field}"

    from plan_engine import build_pdf, generate_weekly_plan
    data = dict(FORM, diet_plan_type="two_meals", symptoms=[], allergies=[],
                notes="", disliked_foods="", user_id=1)
    with A.app.test_request_context("/"):
        plan = generate_weekly_plan(data)
    assert len(plan) == 7
    for day in plan:
        assert day.get("breakfast") and day.get("lunch"), f"{day['day']} is short a meal"
        assert "dinner" not in day, f"{day['day']} still has dinner"
        assert day["total_cal"] > 0

    with A.app.test_request_context("/"):
        assert build_pdf(data, plan)[:5] == b"%PDF-"


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

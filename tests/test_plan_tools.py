# -*- coding: utf-8 -*-
"""‏الخطة وهي بتتعدّل، والقالب وهو بيتحط لعميل تاني.

‏المولّد بيفلتر كل وجبة بيختارها على حالة العميل. بس فيه بابين كانوا
بيعدّوا من جنب الفلتر:

  ‏١) **التعديل بالإيد.** الدكتور بيكتب فوق الوجبة، والنص بيتحفظ زي ما
     هو -- من غير ما يتعدّي على الممنوعات، ومن غير ما مجموع اليوم يتحدّث.
  ‏٢) **القالب.** أسبوع اتعمل لعميل سليم واتحط لمريض سكر أو كلى.

‏الاختبارات دي بتتأكد إن الاتنين بقوا بيتفحصوا، وإن القالب مابيشيلش معاه
بيانات عميل.

Run with:  python3 tests/test_plan_tools.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")

import app as A            # noqa: E402
import core                # noqa: E402
import draft_store         # noqa: E402
import meal_database as md  # noqa: E402
import plan_tools as T     # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False

DIABETES = next(c for c, k in md.CONDITION_MAP.items() if k == "سكري")
KIDNEY = next(c for c, k in md.CONDITION_MAP.items() if k == "كلوي")

FORM = {
    "action": "generate", "name": "أحمد على", "phone": "01012345678",
    "age": "32", "gender": "ذكر", "height": "176", "weight": "95",
    "tdee": "2350", "goal_cal": "1750", "goal_type": "weight_loss",
    "culture": "مصري", "diet_plan_type": "standard", "activity_mult": "1.55",
    "protein_per_kg": "1.8", "fat_pct_cal": "30", "zigzag_mode": "off",
}
BANNED_FOR_DIABETES = "ارز ابيض 200جم + عسل 2 ملعقة"
BANNED_FOR_KIDNEY = "موز 2 + سبانخ 150جم"
FINE = "بيض مسلوق 2 + خيار 100جم"


def _staff():
    c = A.app.test_client()
    c.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                           "password": "pw123456"})
    return c


def _generate(c, **over):
    form = dict(FORM, **over)
    r = c.post("/generate", data=form)
    assert r.status_code in (200, 302), r.status_code
    return c


def _draft(c):
    with c.session_transaction() as s:
        ident = s.get(draft_store.KEY)
    row = core.db_row("SELECT * FROM plan_drafts WHERE id=?", (ident,))
    return json.loads(row["data_json"]), json.loads(row["plan_json"])


def _post(c, path, **data):
    return c.post(path, data=data).get_json()


# ── التعديل اللحظي ──────────────────────────────────────────────────

def test_a_meal_typed_by_hand_is_checked_against_the_clients_conditions():
    """‏ده الباب اللي كان مفتوح: نص مكتوب بالإيد لمريض سكر فيه أرز أبيض
    وعسل، واتحفظ من غير ولا كلمة."""
    c = _generate(_staff(), symptoms=DIABETES)
    got = _post(c, "/edit_meal", day_idx=0, meal_type="breakfast",
                new_text=BANNED_FOR_DIABETES)
    assert got["ok"] and DIABETES in got["check"]["warning"], got
    fine = _post(c, "/edit_meal", day_idx=0, meal_type="breakfast", new_text=FINE)
    assert fine["check"]["warning"] == "", fine


def test_the_warning_is_about_this_client_not_about_the_food():
    c = _generate(_staff())                       # no conditions at all
    got = _post(c, "/edit_meal", day_idx=0, meal_type="breakfast",
                new_text=BANNED_FOR_DIABETES)
    assert got["check"]["warning"] == "", got


def test_the_edit_is_saved_even_when_it_is_flagged():
    """‏التحذير مابيمنعش: القرار للأخصائي. اللي اتغيّر إنه بيتقال له."""
    c = _generate(_staff(), symptoms=DIABETES)
    _post(c, "/edit_meal", day_idx=2, meal_type="lunch",
          new_text=BANNED_FOR_DIABETES)
    _, plan = _draft(c)
    assert plan[2]["lunch"] == BANNED_FOR_DIABETES
    page = c.get("/preview").get_data(as_text=True)
    assert "do not suit this client" in page or "ماتنفعش العميل" in page
    assert DIABETES in page


def test_what_the_client_asked_to_avoid_is_flagged_too():
    c = _generate(_staff(), disliked_foods="تونة")
    got = _post(c, "/edit_meal", day_idx=0, meal_type="dinner",
                new_text="تونة 150جم + خبز اسمر 60جم")
    assert "تونة" in got["check"]["warning"], got


def test_the_days_total_follows_the_edit():
    """‏المجموع والفرق عن الهدف كانوا بيتحسبوا مرة وقت التوليد ويفضلوا."""
    c = _generate(_staff())
    _, before = _draft(c)
    heavy = before[0]["lunch"] + " + ارز ابيض 400جم"
    got = _post(c, "/edit_meal", day_idx=0, meal_type="lunch", new_text=heavy)
    check = got["check"]
    assert check["total_cal"] > before[0]["total_cal"] + 300, check
    assert check["target_cal"] == 1750
    assert check["gap"] == 1750 - check["total_cal"]
    _, after = _draft(c)
    assert after[0]["total_cal"] == check["total_cal"], "the draft kept the old total"
    assert after[1]["total_cal"] == before[1]["total_cal"], "another day moved"
    back = _post(c, "/edit_meal", day_idx=0, meal_type="lunch",
                 new_text=before[0]["lunch"])
    assert back["check"]["total_cal"] == before[0]["total_cal"], \
        "putting the meal back did not put the total back"


def test_a_big_gap_raises_the_alert_and_a_small_one_does_not():
    data = {"goal_cal": "1600"}
    assert not T.day_status(data, {"total_cal": 1600 + T.GAP_ALERT_KCAL})["alert"]
    over = T.day_status(data, {"total_cal": 1600 + T.GAP_ALERT_KCAL + 1})
    assert over["alert"] and over["gap"] == -(T.GAP_ALERT_KCAL + 1)
    assert T.day_status(data, {"total_cal": 1300})["alert"]
    assert T.day_status({"goal_cal": "1600"},
                        {"total_cal": 2000, "target_cal": 2000})["gap"] == 0, \
        "a zigzag day's own target must win over the plan's"
    assert T.day_status({}, {"total_cal": 900})["alert"] is False


def test_a_meal_nobody_can_measure_is_marked_as_a_guess():
    """‏"وجبة حرة" مالهاش جرامات. الفرق اللي يطلع منها تخمين، والصفحة
    بتقول كده (~) بدل ما ترفع تنبيه على رقم مش حقيقي."""
    day = {"total_cal": 1500, "lunch": FINE}
    got = T.apply_change({"goal_cal": "1500"}, day, FINE, "وجبة حرة")
    assert got["estimated"] is True, got
    assert T.apply_change({"goal_cal": "1500"}, dict(day), FINE, FINE)["estimated"] is False


def test_swapping_and_picking_report_the_same_way():
    c = _generate(_staff(), symptoms=KIDNEY)
    swapped = _post(c, "/swap_meal", day_idx=1, meal_type="lunch")
    assert swapped["ok"] and "total_cal" in swapped["check"], swapped
    assert swapped["check"]["warning"] == "", \
        "the generator's own pool handed a kidney patient a banned meal"
    picked = _post(c, "/replace_meal", day_idx=1, meal_type="lunch",
                   new_meal=BANNED_FOR_KIDNEY)
    assert KIDNEY in picked["check"]["warning"], picked


def test_the_preview_page_carries_the_live_hooks():
    c = _generate(_staff())
    page = c.get("/preview").get_data(as_text=True)
    assert page.count('class="day-total"') == 7
    assert page.count('class="day-gap"') == 7
    assert "function applyCheck" in page
    assert page.count("applyCheck(") >= 4, "an edit path does not call applyCheck"


# ── القوالب ─────────────────────────────────────────────────────────

def _save_template(c, name="Weight loss 1750"):
    c.post("/templates/save", data={"name": name})
    return core.db_row("SELECT * FROM plan_templates ORDER BY id DESC LIMIT 1")


def test_a_template_carries_the_meals_and_nothing_about_the_client():
    c = _generate(_staff(), notes="العميل عنده ظروف خاصة")
    _, plan = _draft(c)
    row = _save_template(c)
    assert row["name"] == "Weight loss 1750" and row["goal_cal"] == 1750
    stored = row["plan_json"]
    # ‏الطول والوزن مش هنا بالقصد: "176" ممكن تطلع جرامات صنف في وجبة.
    # اللي بيثبت إن مفيش بيانات عميل هو فحص المفاتيح تحت.
    for private in ("أحمد", "01012345678", "ظروف خاصة"):
        assert private not in stored, "the template kept %r" % private
    tpl = json.loads(stored)
    assert [d["breakfast"] for d in tpl] == [d["breakfast"] for d in plan]
    assert set(tpl[0]) <= {"day", "total_cal", "total_p"} | set(T.MEAL_KEYS)


def test_applying_a_template_puts_its_week_on_the_new_client():
    c = _staff()
    _generate(c)
    _, source = _draft(c)
    tid = _save_template(c)["id"]
    _generate(c, name="منى سعيد", phone="01099999999", weight="70")
    r = c.post("/templates/%d/apply" % tid)
    assert "tpl=applied" in r.headers["Location"], r.headers["Location"]
    data, plan = _draft(c)
    assert data["name"] == "منى سعيد", "the template overwrote the client"
    assert [d["lunch"] for d in plan] == [d["lunch"] for d in source]


def test_a_template_never_hands_a_patient_a_banned_meal():
    """‏أسبوع اتعمل لعميل سليم وفيه أكل ممنوع على مريض السكر. لما يتحط
    لمريض سكر، كل وجبة ممنوعة لازم تتبدّل -- مافيش ولا واحدة تعدّي."""
    c = _staff()
    _generate(c)
    for day in range(7):
        _post(c, "/edit_meal", day_idx=day, meal_type="breakfast",
              new_text=BANNED_FOR_DIABETES)
    tid = _save_template(c, "Has sugar")["id"]

    _generate(c, name="مريض سكر", phone="01088888888", symptoms=DIABETES)
    r = c.post("/templates/%d/apply" % tid)
    loc = r.headers["Location"]
    # ‏السبعة اللي اتحطوا بالإيد على الأقل -- والمولّد نفسه بيدّي العميل
    # السليم وجبات تانية ممنوعة على السكر، ودي كمان لازم تتبدّل.
    assert int(re.search(r"replaced=(\d+)", loc).group(1)) >= 7, loc
    assert "kept=0" in loc, loc
    data, plan = _draft(c)
    assert T.plan_problems(data, plan) == {}, T.plan_problems(data, plan)
    assert all(d["breakfast"] != BANNED_FOR_DIABETES for d in plan)
    page = c.get(loc).get_data(as_text=True)
    assert "swapped for ones that do" in page or "اتبدّلت بوجبات مسموحة" in page


def test_a_template_with_other_meal_slots_is_refused():
    c = _staff()
    _generate(c)
    tid = _save_template(c)["id"]
    week = json.loads(core.db_row("SELECT plan_json FROM plan_templates WHERE id=?",
                                  (tid,))["plan_json"])
    for day in week:
        day["iftar"] = day.pop("lunch")
    core.db_run("UPDATE plan_templates SET plan_json=? WHERE id=?",
                (json.dumps(week, ensure_ascii=False), tid))
    _, before = _draft(c)
    r = c.post("/templates/%d/apply" % tid)
    assert "tpl=misfit" in r.headers["Location"]
    assert _draft(c)[1] == before, "a misfitting template changed the week"
    assert not T.template_fits(before, week[:3])


def test_templates_belong_to_the_nutritionist_who_made_them():
    c = _staff()
    _generate(c)
    tid = _save_template(c)["id"]
    core.db_run("INSERT INTO users (name,email,password,role,active) "
                "VALUES ('Other','other@p.test','x','nutritionist',1)")
    other = core.db_row("SELECT id FROM users WHERE email='other@p.test'")["id"]
    o = A.app.test_client()
    with o.session_transaction() as s:
        s["uid"] = other
    _generate(o)
    assert "tpl=missing" in o.post("/templates/%d/apply" % tid).headers["Location"]
    o.post("/templates/%d/delete" % tid)
    assert core.db_row("SELECT id FROM plan_templates WHERE id=?", (tid,))
    assert "Weight loss 1750" not in o.get("/saved").get_data(as_text=True)
    assert "Weight loss 1750" in c.get("/saved").get_data(as_text=True)
    c.post("/templates/%d/delete" % tid)
    assert not core.db_row("SELECT id FROM plan_templates WHERE id=?", (tid,))


def test_clients_and_visitors_cannot_touch_templates():
    core.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) "
                "VALUES ('Cli','cli@p.test','x','client',1,CURRENT_TIMESTAMP)")
    cli = core.db_row("SELECT id FROM users WHERE email='cli@p.test'")["id"]
    before = core.db_row("SELECT COUNT(*) AS c FROM plan_templates")["c"]
    for uid in (cli, None):
        c = A.app.test_client()
        if uid:
            with c.session_transaction() as s:
                s["uid"] = uid
        assert c.post("/templates/save", data={"name": "x"}).status_code == 302
        assert c.post("/templates/1/apply").status_code == 302
    assert core.db_row("SELECT COUNT(*) AS c FROM plan_templates")["c"] == before


def test_a_template_needs_a_name():
    c = _generate(_staff())
    before = core.db_row("SELECT COUNT(*) AS c FROM plan_templates")["c"]
    r = c.post("/templates/save", data={"name": "   "})
    assert "tpl=bad_name" in r.headers["Location"]
    assert core.db_row("SELECT COUNT(*) AS c FROM plan_templates")["c"] == before


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
        except Exception as e:
            print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

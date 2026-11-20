# -*- coding: utf-8 -*-
"""‏الدكتور بيزوّد أو ينقّص كمية صنف واحد في الوجبة بزرار.

‏صاحب المشروع: "أشوف الوجبات محطوطة وكله تمام، لو لقيت كمية مش عاجباني
أنقّص فيها براحتي أو أزوّد". قبل كده الطريقة الوحيدة كانت إنه يفتح نص
الوجبة كله ويكتب الرقم بإيده -- وده بيبوّظ بسهولة حاجة تانية في نفس
السطر.

‏اللي الاختبارات دي بتحرسه:
  ‏- الزرار بيلمس رقم الصنف ده بس؛ باقي النص بالحرف زي ما هو.
  ‏- الخطوة رقم يقدر يوزنه (٥ جم تحت الـ٥٠، و١٠ فوقها)، والعدد واحدة واحدة.
  ‏- مفيش نزول لصفر: الصنف اللي عايز يتشال بيتشال بالتعديل العادي.
  ‏- "زيت زيتون 1 ملعقة" بتتحسب ملعقة مش عدد زيتون (نفس فخ portion_scale).
  ‏- التغيير بيعدّي على نفس فحص التعديل بالإيد: مجموع اليوم بيتحدّث،
    والتحذير الطبي بيظهر لو الوجبة فيها حاجة ممنوعة على العميل.

Run with:  python3 tests/test_portion_control.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_portion_control_test.db"

import app as A               # noqa: E402
import core                   # noqa: E402
import draft_store            # noqa: E402
import meal_database as md    # noqa: E402
import portion_scale as P     # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False

DIABETES = next(c for c, k in md.CONDITION_MAP.items() if k == "سكري")
FORM = {
    "action": "generate", "name": "عميل الكميات", "phone": "01077778888",
    "age": "32", "gender": "ذكر", "height": "176", "weight": "95",
    "tdee": "2350", "goal_cal": "1750", "goal_type": "weight_loss",
    "culture": "مصري", "diet_plan_type": "standard", "activity_mult": "1.55",
    "protein_per_kg": "1.8", "fat_pct_cal": "30", "zigzag_mode": "off",
}
MEAL = "🥚 بيض مسلوق 2 + 🧀 جبن قريش 60جم + 🥒 خضار طازة"


# ── الحساب ──────────────────────────────────────────────────────────

def test_every_item_gets_a_control_and_only_numbers_get_a_quantity():
    """‏كل صنف ليه شريحة عشان ينفع يتشال -- حتى "خضار طازة" اللي مالهاش رقم."""
    items = P.meal_items(MEAL)
    assert [(i["index"], i["qty"], i["unit"]) for i in items] == [
        (0, 2, ""), (1, 60, "جم"), (2, None, "")], items
    assert "بيض" in items[0]["text"] and "جبن" in items[1]["text"]
    assert items[2]["name"] == "🥒 خضار طازة" and not items[2]["can_down"]


def test_grams_move_in_weighable_steps():
    assert P.nudge_item(MEAL, 1, +1) == MEAL.replace("60جم", "70جم")
    assert P.nudge_item(MEAL, 1, -1) == MEAL.replace("60جم", "50جم")
    small = "🌰 جوز 15جم"
    assert P.nudge_item(small, 0, +1) == "🌰 جوز 20جم"
    assert P.nudge_item(small, 0, -1) == "🌰 جوز 10جم"
    # ‏من ٥٠ ونازل الخطوة ٥، مش ١٠ -- ٥٠ ناقص ١٠ بيبقى قفزة كبيرة على صنف صغير
    assert P.nudge_item("شوفان 50جم", 0, -1) == "شوفان 45جم"
    assert P.nudge_item("شوربة 250مل", 0, +1) == "شوربة 260مل"


def test_counts_move_by_one_and_never_reach_zero():
    assert P.nudge_item(MEAL, 0, +1) == MEAL.replace("بيض مسلوق 2", "بيض مسلوق 3")
    one = MEAL.replace("بيض مسلوق 2", "بيض مسلوق 1")
    assert P.nudge_item(one, 0, -1) is None
    assert P.nudge_item("🌰 جوز 5جم", 0, -1) is None


def test_a_spoon_of_olive_oil_is_a_spoon_not_olives():
    text = "🐟 سلمون مشوي 150جم + 🫒 زيت زيتون 1 ملعقة"
    assert P.nudge_item(text, 1, +1) == "🐟 سلمون مشوي 150جم + 🫒 زيت زيتون 2 ملعقة"
    assert [i["unit"] for i in P.meal_items(text)] == ["جم", "ملعقة"]


def test_the_rest_of_the_text_is_left_exactly_as_it_was():
    text = "🍝 Ultimate Pasta (مكرونة 150جم + 🍗 دجاج 220جم + 🥬 خضار + 🧀 بارميزان)"
    assert P.nudge_item(text, 1, +1) == text.replace("220جم", "230جم")


def test_a_snacks_written_calories_follow_its_portion():
    assert P.nudge_item("🍎 تفاح 150جم - 80 kcal", 0, +1) == "🍎 تفاح 160جم - 85 kcal"
    assert P.nudge_item("🍎 تفاح 150جم (80 kcal)", 0, -1) == "🍎 تفاح 140جم (75 kcal)"
    assert [i["index"] for i in P.meal_items("🍎 تفاح 150جم - 80 kcal")] == [0]


def test_a_bad_index_changes_nothing():
    assert P.nudge_item(MEAL, 2, +1) is None    # خضار من غير كمية
    assert P.nudge_item(MEAL, 9, +1) is None
    assert P.nudge_item("", 0, +1) is None


# ── من الصفحة ───────────────────────────────────────────────────────

def _staff(**over):
    c = A.app.test_client()
    c.post("/login", data={"action": "login", "email": "admin@nutrax.com",
                           "password": "pw123456"})
    r = c.post("/generate", data=dict(FORM, **over))
    assert r.status_code in (200, 302), r.status_code
    return c


def _plan(c):
    with c.session_transaction() as s:
        ident = s.get(draft_store.KEY)
    row = core.db_row("SELECT * FROM plan_drafts WHERE id=?", (ident,))
    return json.loads(row["plan_json"])


def _set(c, text):
    got = c.post("/edit_meal", data={"day_idx": 0, "meal_type": "breakfast",
                                     "new_text": text}).get_json()
    assert got["ok"], got
    return got


def _nudge(c, item, direction):
    return c.post("/nudge_item", data={"day_idx": 0, "meal_type": "breakfast",
                                       "item": item, "dir": direction})


def test_a_nudge_is_saved_and_moves_the_days_total():
    c = _staff()
    before = _set(c, MEAL)["check"]["total_cal"]
    r = _nudge(c, 1, "+1")
    got = r.get_json()
    assert r.status_code == 200 and got["ok"], got
    assert got["new_meal"] == MEAL.replace("60جم", "70جم")
    assert _plan(c)[0]["breakfast"] == got["new_meal"], "التغيير مااتحفظش في المسودة"
    assert got["check"]["total_cal"] > before, (before, got["check"])
    assert [i["qty"] for i in got["items"]] == [2, 70, None]

    down = _nudge(c, 1, "-1").get_json()
    assert down["check"]["total_cal"] < got["check"]["total_cal"]


def test_a_nudge_is_checked_against_the_clients_conditions():
    """‏الزرار باب تاني لتغيير الوجبة، فلازم يعدّي على نفس الفلتر."""
    c = _staff(symptoms=DIABETES)
    _set(c, "ارز ابيض 200جم + عسل 2 ملعقة")
    got = _nudge(c, 0, "+1").get_json()
    assert got["ok"] and got["check"]["warning"], got


def test_a_nudge_past_the_minimum_or_on_a_bare_item_is_refused():
    c = _staff()
    _set(c, MEAL.replace("بيض مسلوق 2", "بيض مسلوق 1"))
    assert _nudge(c, 0, "-1").status_code == 400
    assert _nudge(c, 2, "+1").status_code == 400
    assert _nudge(c, 0, "sideways").status_code == 400
    assert _plan(c)[0]["breakfast"] == MEAL.replace("بيض مسلوق 2", "بيض مسلوق 1")


def test_the_preview_shows_a_labelled_control_for_each_item():
    c = _staff()
    _set(c, MEAL)
    html = c.get("/preview").get_data(as_text=True)
    m = re.search(r'<div class="qty-row"[^>]*data-day="0"[^>]*data-type="breakfast"[^>]*>(.*?)</div>\s*<!--/qty-row-->',
                  html, re.S)
    assert m, "مفيش صف كميات تحت الفطار"
    row = m.group(1)
    buttons = re.findall(r"<button[^>]*class=\"qty-btn\"[^>]*>", row)
    # ‏حذف على كل صنف (٣)، وناقص + زايد على الاتنين اللي ليهم كمية (٤)
    assert len(buttons) == 7, buttons
    for b in buttons:
        assert 'aria-label="' in b, b
    assert re.search(r'data-item="1"[^>]*data-dir="\+1"|data-dir="\+1"[^>]*data-item="1"', row)



# ── الحذف والإضافة ──────────────────────────────────────────────────
#
# ‏صاحب المشروع: "لما أدوس ناقص على الوجبة أو نوع الأكل يتحذف ويجيلي
# رسالة تأكيد للحذف، وأقدر أضيف مكانه من خانة لوحدها".

def test_removing_an_item_leaves_the_rest_exactly():
    assert P.remove_item(MEAL, 1) == "🥚 بيض مسلوق 2 + 🥒 خضار طازة"
    assert P.remove_item(MEAL, 2) == "🥚 بيض مسلوق 2 + 🧀 جبن قريش 60جم"
    assert P.remove_item(MEAL, 9) is None
    assert P.remove_item("🍎 تفاح 150جم", 0) == ""


def test_a_written_calorie_figure_goes_when_the_items_change():
    """‏"- 99 kcal" بيوصف الوجبة اللي اتكتبت؛ بعد ما صنف يتشال أو يتضاف
    الرقم ده بيبقى كذب مكتوب على ورقة العميل."""
    snack = "🌴 تمر 15جم + 🌰 لوز 10جم - 100 kcal"
    assert P.remove_item(snack, 1) == "🌴 تمر 15جم"
    assert P.add_item(snack, "زبادي 100جم") == "🌴 تمر 15جم + 🌰 لوز 10جم + زبادي 100جم"


def test_adding_an_item_appends_it_cleanly():
    assert P.add_item(MEAL, "  زبادي   يوناني 150جم ") == MEAL + " + زبادي يوناني 150جم"
    assert P.add_item("", "تفاح 150جم") == "تفاح 150جم"
    assert P.add_item(MEAL, "   ") is None
    assert P.add_item(MEAL, "ا" * 200) is None


def _remove(c, item, key="breakfast"):
    return c.post("/remove_item", data={"day_idx": 0, "meal_type": key, "item": item})


def _add(c, text, key="breakfast"):
    return c.post("/add_item", data={"day_idx": 0, "meal_type": key, "text": text})


def test_removing_from_the_page_saves_and_lowers_the_day():
    c = _staff()
    before = _set(c, MEAL)["check"]["total_cal"]
    got = _remove(c, 1).get_json()
    assert got["ok"], got
    assert _plan(c)[0]["breakfast"] == "🥚 بيض مسلوق 2 + 🥒 خضار طازة"
    assert got["check"]["total_cal"] < before
    assert [i["index"] for i in got["items"]] == [0, 1]
    assert _remove(c, 7).status_code == 400


def test_an_emptied_meal_keeps_its_row_so_something_can_be_added_back():
    c = _staff()
    _set(c, "🍎 تفاح 150جم")
    got = _remove(c, 0).get_json()
    assert got["ok"] and got["new_meal"] == "" and got["items"] == []
    html = c.get("/preview").get_data(as_text=True)
    assert re.search(r'class="add-item"[^>]*data-day="0"[^>]*data-type="breakfast"', html), \
        "الوجبة اتمسحت والصف بتاعها اختفى -- مفيش مكان يتضاف فيه"
    back = _add(c, "زبادي 150جم").get_json()
    assert back["ok"] and _plan(c)[0]["breakfast"] == "زبادي 150جم"


def test_an_added_item_is_checked_against_the_clients_conditions():
    c = _staff(symptoms=DIABETES)
    _set(c, MEAL)
    got = _add(c, "عسل 2 ملعقة").get_json()
    assert got["ok"] and got["check"]["warning"], got
    assert _add(c, "   ").status_code == 400


def test_the_preview_asks_before_removing_and_has_a_labelled_add_box():
    c = _staff()
    _set(c, MEAL.replace("بيض مسلوق 2", "بيض مسلوق 1"))
    html = c.get("/preview").get_data(as_text=True)
    m = re.search(r'<div class="qty-row"[^>]*data-day="0"[^>]*data-type="breakfast"[^>]*>(.*?)</div>\s*<!--/qty-row-->',
                  html, re.S)
    row = m.group(1)
    # ‏زرار حذف ثابت على كل صنف -- صاحب المشروع: تفاح ٢٢٠جم كان محتاج
    # ٤٣ ضغطة ناقص قبل ما يتحذف. والناقص على البيضة الواحدة متقفل.
    removes = re.findall(r'<button[^>]*data-remove="1"[^>]*>', row)
    assert len(removes) == 3, removes
    assert re.search(r'<button[^>]*data-item="0"[^>]*data-dir="-1"[^>]*disabled', row), row
    for b in removes:
        assert 'aria-label="' in b, b
    assert re.search(r'<dialog[^>]*id="rmDialog"', html), "مفيش رسالة تأكيد للحذف"
    form = re.search(r'<form class="add-item"[^>]*data-day="0"[^>]*data-type="breakfast".*?</form>', html, re.S)
    assert form, "مفيش خانة إضافة تحت الفطار"
    assert re.search(r'<input[^>]*aria-label="', form.group(0)), form.group(0)


# ── كتابة الكمية والسعرات جنب كل صنف ────────────────────────────────
#
# ‏فكرتين من برنامج تاني صاحب المشروع بعت صورته: الكمية خانة تتكتب،
# وسعرات كل صنف جنبه. التصميم بتاعنا؛ الفكرة بس.

def test_a_quantity_can_be_typed_straight_in():
    assert P.set_item_qty(MEAL, 1, 85) == MEAL.replace("60جم", "85جم")
    assert P.set_item_qty(MEAL, 0, 4) == MEAL.replace("بيض مسلوق 2", "بيض مسلوق 4")
    oil = "🫒 زيت زيتون 1 ملعقة"
    assert P.set_item_qty(oil, 0, 0.5) == "🫒 زيت زيتون 0.5 ملعقة"
    assert P.set_item_qty("🍎 تفاح 150جم - 80 kcal", 0, 300) == "🍎 تفاح 300جم - 160 kcal"


def test_a_typed_quantity_has_to_be_something_you_can_serve():
    assert P.set_item_qty(MEAL, 1, 0) is None          # صفر = حذف، وده زراره لوحده
    assert P.set_item_qty(MEAL, 1, 3) is None          # تحت ٥ جم
    assert P.set_item_qty(MEAL, 1, 5000) is None       # ٥ كيلو جبنة: غلطة كتابة
    assert P.set_item_qty(MEAL, 0, 2.5) is None        # نص بيضة
    assert P.set_item_qty(MEAL, 0, 40) is None         # ٤٠ بيضة
    assert P.set_item_qty(MEAL, 2, 100) is None        # الخضار مالهاش رقم
    assert P.set_item_qty(MEAL, 1, 60) == MEAL         # نفس الرقم: مفيش تغيير


def test_typing_a_quantity_on_the_page_saves_and_moves_the_day():
    c = _staff()
    before = _set(c, MEAL)["check"]["total_cal"]
    r = c.post("/set_item_qty", data={"day_idx": 0, "meal_type": "breakfast",
                                      "item": 1, "qty": "120"})
    got = r.get_json()
    assert r.status_code == 200 and got["ok"], got
    assert _plan(c)[0]["breakfast"] == MEAL.replace("60جم", "120جم")
    assert got["check"]["total_cal"] > before
    for bad in ("0", "abc", "", "99999"):
        assert c.post("/set_item_qty", data={"day_idx": 0, "meal_type": "breakfast",
                                             "item": 1, "qty": bad}).status_code == 400, bad


def test_each_item_carries_its_own_calories():
    items = {i["index"]: i for i in P.meal_items(MEAL)}
    import meal_macros
    assert items[1]["cal"] == meal_macros.macros("🧀 جبن قريش 60جم")["cal"] > 0
    assert items[0]["cal"] > 0
    unknown = P.meal_items("حاجة مش موجودة في الجدول 50جم")[0]
    assert unknown["cal"] is None


def test_the_preview_shows_a_typed_quantity_box_and_the_items_calories():
    c = _staff()
    _set(c, MEAL)
    html = c.get("/preview").get_data(as_text=True)
    m = re.search(r'<div class="qty-row"[^>]*data-day="0"[^>]*data-type="breakfast"[^>]*>(.*?)</div>\s*<!--/qty-row-->',
                  html, re.S)
    row = m.group(1)
    boxes = re.findall(r'<input[^>]*class="qty-in"[^>]*>', row)
    assert len(boxes) == 2, boxes
    for b in boxes:
        assert 'aria-label="' in b and 'inputmode="decimal"' in b, b
    assert 'value="60"' in boxes[1], boxes[1]
    assert len(re.findall(r'class="qty-kcal"', row)) >= 2, row

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

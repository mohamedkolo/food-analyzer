# -*- coding: utf-8 -*-
"""‏إبر التخسيس: الورقة كانت بتقول رقم والجدول متبني على غيره.

‏الملاحظة الإكلينيكية اللي بتتطبع على ورقة عميل على أوزمبيك بتقول
بالنص "المطلوب ١.٢-١.٥ جم/كجم يومياً". والجدول تحتها كان متبني على
جرام/كجم **مستوى النشاط**:

    ‏عميلة ٩٥ كجم، خاملة، على أوزمبيك
    ‏الملاحظة:      ١.٢-١.٥ جم/كجم  (١١٤-١٤٢ جم)
    ‏الهدف المطبوع:  ٩٥ جم  (١.٠ جم/كجم)
    ‏الأكل الفعلي:   ١١٥ جم

‏يعني الورقة بتناقض نفسها. والرقم ١.٥ من إجماع خبراء ٢٠٢٥ (Delphi)
ومراجعات ٢٠٢٦ -- والسبب إن الإبرة بتبطّء تفريغ المعدة، فالنزول سريع
واللي بينزل مش دهون بس.

Run with:  python3 tests/test_glp1_protein.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_glp1_test.db"

import app as A            # noqa: E402
import meal_database as MD  # noqa: E402
import plan_engine         # noqa: E402
import protein_need        # noqa: E402
import zigzag              # noqa: E402

OZEMPIC = "ويجوفي / أوزمبيك (سيماجلوتايد)"
MOUNJARO = "مونجارو / زيباوند (تيرزيباتايد)"
SAXENDA = "ساكسيندا (ليراجلوتايد)"
INJECTIONS = (OZEMPIC, MOUNJARO, SAXENDA)

CLIENT = {"name": "عميلة", "age": "38", "gender": "انثى", "height": "162",
          "weight": "95", "tdee": "1900", "goal_cal": "1500",
          "goal_type": "weight_loss", "culture": "مصري",
          "diet_plan_type": "standard", "fat_pct_cal": "30",
          "allergies": [], "zigzag_mode": "classic",
          "activity_level": "sedentary", "symptoms": []}


def _plan(**over):
    data = dict(CLIENT, **over)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        plan = plan_engine.generate_weekly_plan(data)
        html = plan_engine.plan_html(data, plan)
    return data, plan, html


def test_every_injection_in_the_form_raises_the_floor():
    """‏التلاتة بيبعتوا على خانة symptoms زي الحالات، فلازم التلاتة
    يتعرفوا -- مش واحد."""
    for med in INJECTIONS:
        assert protein_need.on_glp1([med]), med
        rate, raised = protein_need.rate_with_meds(1.0, [med], 38)
        assert raised and rate == protein_need.GLP1_FLOOR_PER_KG, (med, rate)


def test_the_form_and_this_file_name_the_same_injections():
    """‏لو اتضافت إبرة جديدة في الفورم ومااتعرفتش هنا، العميل بياخد
    بروتين ناقص وهو على إبرة -- في صمت."""
    known = {ar for ar, key in MD.CONDITION_MAP.items()
             if key == "glp1"} if hasattr(MD, "CONDITION_MAP") else set()
    try:
        from meal_extra import CONDITION_KEYS
        known |= {ar for ar, key in CONDITION_KEYS.items() if key == "glp1"}
    except Exception:
        pass
    assert known, "‏مافيش إبر مسجّلة في خريطة الحالات خالص"
    for med in known:
        assert protein_need.on_glp1([med]), "‏%s مش متعرّفة كإبرة" % med


def test_a_sedentary_client_on_an_injection_is_not_left_at_one_gram():
    """‏ده اللي كان بيحصل: ٩٥ جم لعميلة ٩٥ كجم، والورقة فوقيها
    مكتوب ١.٢-١.٥."""
    data, _plan_days, _html = _plan(symptoms=[OZEMPIC])
    basis = data["protein_basis"]
    assert basis["per_kg"] >= 1.5, basis
    assert basis["grams"] >= 140, basis


def test_the_floor_never_lowers_what_the_doctor_wrote():
    """‏أرضية مش سقف. الدكتور لو كتب ١.٨ أو اختار رياضي، رقمه يفضل."""
    for over, want in ((dict(activity_level="regular"), 1.6),
                       (dict(activity_level="athlete"), 2.0),
                       (dict(protein_per_kg="1.8"), 1.8)):
        data, _p, _h = _plan(symptoms=[OZEMPIC], **over)
        assert data["protein_basis"]["per_kg"] == want, (over, data["protein_basis"])


def test_a_client_without_an_injection_is_untouched():
    data, _p, _h = _plan(symptoms=["ضغط الدم المرتفع"])
    assert data["protein_basis"]["per_kg"] == 1.0, data["protein_basis"]
    data2, _p2, _h2 = _plan()
    assert data2["protein_basis"]["per_kg"] == 1.0, data2["protein_basis"]


def test_the_paper_and_the_table_are_on_one_number():
    """‏الدرس اللي اتكرر مرتين قبل كده: لو الحساب اتعمل في مكانين،
    الورقة بتطبع رقم والجدول يتبني على غيره. فالرقم المطبوع لازم
    يكون هو نفسه اللي في protein_basis."""
    data, plan, html = _plan(symptoms=[OZEMPIC])
    grams = data["protein_basis"]["grams"]
    rate = data["protein_basis"]["per_kg"]
    text = re.sub(r"<[^>]+>", " ", html)
    assert re.search(r"%d\s*(?:جم|g)" % grams, text), (
        "‏الورقة مش بتطبع %d" % grams)
    assert re.search(r"%s\s*(?:جم/كجم|g/kg)" % rate, text), (
        "‏الورقة مش بتطبع %s جم/كجم" % rate)
    # ‏والأكل نفسه قريب من الهدف
    avg = round(sum(d["total_p"] for d in plan) / len(plan))
    assert abs(avg - grams) / float(grams) < 0.15, (avg, grams)


def test_the_sheet_says_why_the_number_moved():
    """‏الدكتور شايف ١.٥ وهو مختار "خامل" -- لازم يعرف الرقم جه منين."""
    _data, _plan_days, html = _plan(symptoms=[OZEMPIC])
    notes = " ".join(re.findall(r'<div class="pnote"[^>]*>(.*?)</div>',
                                html, re.S))
    assert "اترفع" in notes and "1.5" in notes, notes[:300]
    # ‏ومايظهرش لما مافيش رفع
    _d2, _p2, html2 = _plan(symptoms=[OZEMPIC], activity_level="athlete")
    notes2 = " ".join(re.findall(r'<div class="pnote"[^>]*>(.*?)</div>',
                                 html2, re.S))
    assert "اترفع" not in notes2, notes2[:300]


def test_a_child_on_an_injection_does_not_get_the_adult_floor():
    """‏الدليل كله على البالغين. ومنظمة الصحة العالمية (٢٠٢٦)
    مابتوصيش بالإبر تحت ١٠ سنين أصلاً."""
    data, _p, _h = _plan(age="10", weight="108.8", height="152",
                         tdee="1912", goal_cal="1912", protein_per_kg="1.3",
                         symptoms=[OZEMPIC])
    assert data["protein_basis"]["per_kg"] < 1.5, data["protein_basis"]
    assert "الصحة العالمية" in (data.get("notes") or ""), data.get("notes")


def test_an_adolescent_gets_the_floor_and_a_word_about_it():
    """‏١٤-١٨ هو نفس فاصل التوصيات، والمراهق على إبرة محتاج حماية
    الكتلة العضلية -- بس الإبرة مش خط أول في السن ده."""
    data, _p, _h = _plan(age="15", weight="95", height="168",
                         protein_per_kg="1.1", symptoms=[OZEMPIC])
    assert data["protein_basis"]["per_kg"] >= 1.5, data["protein_basis"]
    assert "الصحة العالمية" in (data.get("notes") or ""), data.get("notes")


def test_the_floor_matches_the_number_the_clinical_note_prints():
    """‏الملاحظة الإكلينيكية بتقول مدى، والأرضية لازم تقع جوّاه --
    وإلا رجعنا لنفس التناقض من ناحية تانية."""
    note = " ".join(MD.get_nutrient_boost_notes([OZEMPIC]))
    found = re.findall(r"(\d\.\d)\s*-\s*(\d\.\d)\s*جم/كجم", note)
    assert found, "‏الملاحظة مش بتقول مدى جرام/كجم: %s" % note[:200]
    low, high = (float(x) for x in found[0])
    assert low <= protein_need.GLP1_FLOOR_PER_KG <= high, (
        "‏الأرضية %.1f برّه المدى المكتوب %.1f-%.1f"
        % (protein_need.GLP1_FLOOR_PER_KG, low, high))


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

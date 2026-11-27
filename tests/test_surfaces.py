# -*- coding: utf-8 -*-
"""One authored day through every surface: preview, save, saved-plan reload, client link, PDF.
Checks that the four macros calculated from the foods show on preview, saved plan and client page, that an
adopted option persists through save and reload, and states where the export (PDF) intentionally carries no analysis.
Run with:  ADMIN_PASSWORD=pw123456 python3 tests/test_surfaces.py"""
import os
import re
import sys

os.environ.setdefault("SECRET_KEY", "k")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_household_measures as H
import test_representative_day as R
import plan_engine

OPTION = "150 جم صدر دجاج مشوي بدون جلد (USDA 171477)"


def _author(c):
    """Writes the three meals of day 0 and fills every other slot of that day with one verified item,
    so the whole day is explicit. Returns the day's texts."""
    import json, draft_store, core
    with c.session_transaction() as s:
        ident = s.get(draft_store.KEY)
    day = json.loads(core.db_row("SELECT * FROM plan_drafts WHERE id=?", (ident,))["plan_json"])[0]
    texts = dict(R.TEXT)
    for slot in day:
        if slot.startswith("snack") and isinstance(day[slot], str):
            texts[slot] = "100 جم تفاح"
    for slot, text in texts.items():
        assert c.post("/edit_meal", data={"day_idx": 0, "meal_type": slot, "new_text": text}).get_json()["ok"]
    return texts


def _macros_line(html):
    """First data-macros-line block with its numbers: (protein, carbs, fat), kcal."""
    m = re.search(r'data-basis="items".*?data-macros-line="1".*?>\s*(.*?)</div>', html, re.S)
    assert m, "no macros line on the page"
    nums = [float(x) for x in re.findall(r'dir="ltr">([\d.]+)', m.group(1))]
    kcal = re.search(r'data-basis="items"[^>]*>\s*[^<]*?<bdi dir="ltr">(\d+) kcal', html, re.S)
    return (int(kcal.group(1)) if kcal else None), nums


def test_the_authored_day_shows_all_macros_on_preview_save_reload_and_client_page():
    c = H._staff()
    texts = _author(c)
    exp = plan_engine.day_calc(dict(texts, total_cal=1800, total_p=100))
    assert exp["basis"] == "items", exp
    want = (exp["computed_cal"], [exp["computed_p"], exp["computed_c"], exp["computed_f"]])
    # preview
    kcal, nums = _macros_line(c.get("/preview").get_data(as_text=True))
    assert (kcal, nums) == (want[0], [float(x) for x in want[1]]), ((kcal, nums), want)
    # save and reload the saved plan
    sid = c.post("/api/save-plan").get_json()["id"]
    c.post("/generate", data=H.FORM)                      # replace the draft, then reopen the SAVED plan
    assert c.get("/saved/%s/open" % sid).status_code == 302
    html = c.get("/preview").get_data(as_text=True)
    kcal, nums = _macros_line(html)
    assert (kcal, nums) == (want[0], [float(x) for x in want[1]]), ((kcal, nums), want)
    # client link
    url = c.post("/api/plan-link").get_json()["url"]
    token = url.rsplit("/", 1)[1]
    page = c.get("/p/%s" % token).get_data(as_text=True)
    kcal, nums = _macros_line(page)
    assert (kcal, nums) == (want[0], [float(x) for x in want[1]]), ((kcal, nums), want)
    # export: a layout of the written table only. It carries no calculated analysis (no kcal/macro totals) on purpose.
    pdf = c.get("/p/%s/pdf" % token)
    assert pdf.status_code == 200 and pdf.mimetype == "application/pdf" and pdf.data[:4] == b"%PDF"


def test_an_adopted_option_persists_through_save_reload_and_the_client_link():
    c = H._staff()
    assert c.post("/edit_meal", data={"day_idx": 0, "meal_type": "lunch", "new_text": "150 جم صدر دجاج + 200 جم أرز أبيض مطبوخ"}).get_json()["ok"]
    html = c.get("/preview").get_data(as_text=True)
    assert 'data-old="150 جم صدر دجاج"' in html, "option not offered"
    assert "data-basis=\"label\"" in html
    adopted = OPTION + " + 200 جم أرز أبيض مطبوخ"
    assert c.post("/edit_meal", data={"day_idx": 0, "meal_type": "lunch", "new_text": adopted}).get_json()["ok"]
    html = c.get("/preview").get_data(as_text=True)
    assert OPTION in html, "adopted text not on the preview"
    assert 'data-old="150 جم صدر دجاج"' not in html, "still offered"
    assert 'data-old="150 جم صدر دجاج مشوي بدون جلد' not in html, "adopted option is flagged again"
    sid = c.post("/api/save-plan").get_json()["id"]
    c.post("/generate", data=H.FORM)
    c.get("/saved/%s/open" % sid)
    assert OPTION in c.get("/preview").get_data(as_text=True)
    token = c.post("/api/plan-link").get_json()["url"].rsplit("/", 1)[1]
    # the client page adds a household measure after the amount, so the option NAME is what must be present
    assert "صدر دجاج مشوي بدون جلد (USDA 171477)" in c.get("/p/%s" % token).get_data(as_text=True)


def test_the_client_plan_history_page_shows_the_same_macros_and_no_adoption_button():
    """/my-plans-history/<id> (view_old_plan) renders a client's own stored plan with the shared calc block."""
    import json, draft_store, core
    from datetime import datetime
    from werkzeug.security import generate_password_hash
    c = H._staff()
    texts = _author(c)
    exp = plan_engine.day_calc(dict(texts, total_cal=1800, total_p=100))
    want = (exp["computed_cal"], [float(exp["computed_p"]), float(exp["computed_c"]), float(exp["computed_f"])])
    with c.session_transaction() as s:
        ident = s.get(draft_store.KEY)
    day = json.loads(core.db_row("SELECT * FROM plan_drafts WHERE id=?", (ident,))["plan_json"])[0]
    core.db_run("INSERT INTO users (name,email,password,role,active,onboarded_at) VALUES (?,?,?,?,1,?)",
                ("Hist", "hist@t.test", generate_password_hash("pw123456"), "client", datetime.now()))
    uid = core.db_row("SELECT id FROM users WHERE email=?", ("hist@t.test",))["id"]
    core.db_run("INSERT INTO plan_requests (client_id, client_name, status, request_data, plan_data) VALUES (?,?,?,?,?)",
                (uid, "Hist", "done", "{}", json.dumps({"data": {}, "plan": [day]}, ensure_ascii=False)))
    pid = core.db_row("SELECT id FROM plan_requests WHERE client_id=?", (uid,))["id"]
    k = H.A.app.test_client()
    with k.session_transaction() as s:
        s["uid"] = uid
    r = k.get("/my-plans-history/%s" % pid)
    assert r.status_code == 200, (r.status_code, r.headers.get("Location"))
    html = r.get_data(as_text=True)
    kcal, nums = _macros_line(html)
    assert (kcal, nums) == (want[0], want[1]), ((kcal, nums), want)
    assert "use-option" not in html and "Use this option" not in html, "adoption button on a read-only history page"


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn(); print(f"  PASS  {name}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {str(e)[:600]}"); failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

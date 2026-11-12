# -*- coding: utf-8 -*-
"""‏ست غلطات صغيرة اتلاحظت وأنا بشتغل على الحجز والبدائل.

‏كل واحدة لوحدها صغيرة، بس اتنين منهم بيلمسوا أرقام العميل كل يوم:

  ‏١) "ارز بني" كان بيتحسب أرز أبيض.
  ‏٢) "زيت زيتون 1 ملعقة صغيرة" كان بيتحسب ١٤ جم (ملعقة كبيرة) بدل ٥ --
     حوالي ٨٠ سعرة زيادة على يوم العميل، من سطر واحد.
  ‏٣) يوم الوجبات كان ماشي بساعة السيرفر (UTC). عميل في القاهرة بيعلّم
     على فطاره الساعة ١٢:٣٠ بعد نص الليل، والعلامة بتتسجّل على إمبارح.
     والتذكير بيوصل متأخر ساعتين.
  ‏٤) زائر اختار موعد وسجّل حساب جديد: بعد التسجيل والاستبيان كان بيرجع
     للرئيسية، والموعد اللي اختاره يضيع.
  ‏٥) القايمة الجانبية عند الأدمن ماكانتش بتعلّم على صفحات زي "طلبات
     العملاء" و"العملاء" -- أسماء الصفحات فيها مكتوبة من غير اسم القسم.
  ‏٦) ملف العميل عند الأدمن كان بيطلّع القايمة الجانبية باسم العميل
     وقايمته هو، لأن الصفحة بتبعت العميل في user.

Run with:  python3 tests/test_daily_fixes.py
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ.setdefault("NUTRAX_DB", "/tmp/nutrax_daily_fixes.db")
if os.path.exists(os.environ["NUTRAX_DB"]):
    os.remove(os.environ["NUTRAX_DB"])

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as A              # noqa: E402
import booking as B          # noqa: E402
import meal_macros as MM     # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

A.app.config["WTF_CSRF_ENABLED"] = False


def _mk(email, role="client", onboarded=True, **cols):
    keys = ["name", "email", "password", "role", "active"] + list(cols)
    vals = [email.split("@")[0], email, generate_password_hash("pw123456"),
            role, 1] + list(cols.values())
    if onboarded:
        keys.append("onboarded_at")
        vals.append(datetime.now())
    A.db_run("INSERT INTO users (%s) VALUES (%s)"
             % (",".join(keys), ",".join("?" * len(keys))), tuple(vals))
    return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]


ADMIN = A.db_row("SELECT id FROM users WHERE email='admin@nutrax.com'")["id"]
ALICE = _mk("alice@d.test", timezone="Africa/Cairo")

WEEK = [{"day": d, "breakfast": "بيض مسلوق 2", "lunch": "صدر دجاج مشوي 150جم",
         "dinner": "زبادي 150جم"}
        for d in ("الاحد", "الاثنين", "الثلاثاء", "الاربعاء", "الخميس",
                  "الجمعة", "السبت")]
A.db_run("INSERT INTO plan_requests (client_id, client_name, status, "
         "request_data, plan_data) VALUES (?,?,?,?,?)",
         (ALICE, "alice", "approved", "{}",
          json.dumps({"data": {"diet_plan_type": "standard"}, "plan": WEEK},
                     ensure_ascii=False)))


def _as(uid=None, lang="en"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["lang"] = lang
        if uid:
            s["uid"] = uid
    return c


class _Clock:
    """Pin "now" (UTC) for the code under test."""

    def __init__(self, utc):
        self.utc = utc

    def __enter__(self):
        self._real = B.utcnow
        B.utcnow = lambda: self.utc
        return self

    def __exit__(self, *exc):
        B.utcnow = self._real


# ‏١٢ نوفمبر ٢٠٢٦، ١١ بالليل UTC = ١ الصبح ١٣ نوفمبر في القاهرة (UTC+2).
LATE_UTC = datetime(2026, 11, 12, 23, 0)
CAIRO_DAY = "2026-11-13"


# ── ١) و٢) قراءة الأصناف ────────────────────────────────────────────

def test_brown_rice_is_read_as_brown_rice():
    assert MM.find_food("ارز بني 140جم")["n"] == "أرز بني مطبوخ"
    assert MM.find_food("🍚 ارز بني 140جم")["n"] == "أرز بني مطبوخ"
    assert MM.find_food("ارز ابيض 140جم")["n"] == "أرز أبيض مطبوخ"
    assert MM.find_food("ارز 140جم")["n"] == "أرز أبيض مطبوخ"


def test_a_spoon_written_in_the_meal_is_the_spoon_that_is_counted():
    """‏"1 ملعقة صغيرة" كانت بتاخد أول وحدة في جدول الصنف -- الملعقة
    الكبيرة (١٤ جم). الرقم اللي قبل الوحدة ماكانش بيتقري أصلاً، لأن العدد
    كان بيتدوّر عليه في آخر الصنف بس."""
    cases = {"زيت زيتون 1 ملعقة صغيرة": 5,
             "🫒 زيت زيتون 1 ملعقة صغيرة": 5,
             "زيت زيتون 2 ملعقة صغيرة": 10,
             "زيت زيتون 1 ملعقة كبيرة": 14,
             "زبدة 1 ملعقة صغيرة": 5}
    for text, grams in cases.items():
        got, how = MM.item_grams(text, MM.find_food(text))
        assert got == grams, (text, got, how)
    # ‏الطرق التانية مالمستش
    assert MM.item_grams("زيت زيتون 10جم", MM.find_food("زيت زيتون"))[0] == 10
    assert MM.item_grams("بيض مسلوق 3", MM.find_food("بيض مسلوق 3"))[0] == 150


def test_the_spoon_fix_moves_the_meal_total_by_the_right_amount():
    big = MM.macros("بيض مسلوق 2 + زيت زيتون 1 ملعقة كبيرة")["cal"]
    small = MM.macros("بيض مسلوق 2 + زيت زيتون 1 ملعقة صغيرة")["cal"]
    assert 70 <= big - small <= 85, (big, small)


# ── ٣) يوم العميل مش يوم السيرفر ────────────────────────────────────

def _checks():
    return A.db_rows("SELECT check_date, meal_key FROM meal_checks "
                     "WHERE user_id=? ORDER BY id", (ALICE,))


def test_a_meal_ticked_after_midnight_in_cairo_lands_on_the_new_day():
    A.db_run("DELETE FROM meal_checks")
    with _Clock(LATE_UTC):
        _as(ALICE).post("/track/meal", data={"meal_key": "breakfast",
                                             "checked": "1"})
    got = _checks()
    assert [str(r["check_date"])[:10] for r in got] == [CAIRO_DAY], got


def test_the_home_page_reads_the_same_day_it_writes():
    with _Clock(LATE_UTC):
        assert A.get_meal_tracking(ALICE)["today_date"] == CAIRO_DAY


def test_a_meal_note_lands_on_the_same_day_as_its_tick():
    A.db_run("DELETE FROM meal_notes")
    with _Clock(LATE_UTC):
        _as(ALICE).post("/track/meal-note", data={"meal_key": "lunch",
                                                  "comment": "late lunch"})
    row = A.db_row("SELECT check_date FROM meal_notes WHERE user_id=?", (ALICE,))
    assert str(row["check_date"])[:10] == CAIRO_DAY, row


def test_the_streak_counts_today_on_the_clients_calendar():
    A.db_run("DELETE FROM meal_checks")
    for key in ("breakfast", "lunch", "dinner"):
        A.db_run("INSERT INTO meal_checks (user_id, check_date, meal_key) "
                 "VALUES (?,?,?)", (ALICE, CAIRO_DAY, key))
    with _Clock(LATE_UTC):
        assert A.get_meal_streak(ALICE)["current_streak"] == 1


def test_meal_reminders_go_by_the_clients_clock():
    """‏الفطار الساعة ٨ والغدا ٢ الضهر بتوقيت العميل. السيرفر شغّال UTC،
    فالتذكير كان بيوصل متأخر ساعتين -- أو في نص الليل."""
    def reminded(utc):
        A.db_run("DELETE FROM meal_reminders_sent")
        A.db_run("DELETE FROM meal_checks")
        with _Clock(utc):
            A.send_meal_time_reminders()
        return sorted(r["meal_key"] for r in A.db_rows(
            "SELECT meal_key FROM meal_reminders_sent WHERE user_id=?", (ALICE,)))

    # ‏١ الصبح في القاهرة: مفيش وجبة فات وقتها
    assert reminded(LATE_UTC) == [], reminded(LATE_UTC)
    # ‏٨:٣٠ الصبح في القاهرة = ٦:٣٠ UTC: الفطار بس
    assert reminded(datetime(2026, 11, 13, 6, 30)) == ["breakfast"]
    # ‏٢:٣٠ الضهر في القاهرة = ١٢:٣٠ UTC: الفطار والغدا
    assert reminded(datetime(2026, 11, 13, 12, 30)) == ["breakfast", "lunch"]


# ── ٤) الموعد اللي اختاره الزائر مايضيعش ───────────────────────────

def _visitor_picks_a_slot():
    A.db_run("DELETE FROM services")
    A.db_run("DELETE FROM availability")
    A.db_run("INSERT INTO services (name, duration_min, price) "
             "VALUES ('Consult', 30, 0)")
    svc = A.db_row("SELECT id FROM services")["id"]
    for wd in range(7):
        A.db_run("INSERT INTO availability (weekday, start_min, end_min) "
                 "VALUES (?,0,1440)", (wd,))
    slot = B.slot_key((B.utcnow() + timedelta(days=3)).replace(
        hour=9, minute=0, second=0, microsecond=0))
    c = _as()
    c.post("/book", data={"service": svc, "date": "", "slot": slot})
    return c, slot


def test_a_new_client_who_registers_comes_back_to_their_slot():
    c, slot = _visitor_picks_a_slot()
    r = c.post("/register", data={
        "name": "Nour", "email": "nour@d.test", "password": "pw123456",
        "phone": "01011112222", "country": "مصر", "age": "30",
        "gender": "انثى", "height": "165", "weight": "70"})
    dest = r.headers.get("Location", "")
    assert dest.startswith("/book?") and "slot=" in dest, dest


def test_a_client_sent_through_onboarding_still_comes_back_to_their_slot():
    """‏حساب اتعمل من تبويب التسجيل في صفحة الدخول مابيعدّيش على الاستبيان،
    فأول دخول بيتحوّل للاستبيان -- والموعد كان بيضيع هناك."""
    _mk("late@d.test", onboarded=False)
    c, slot = _visitor_picks_a_slot()
    r = c.post("/login", data={"action": "login", "email": "late@d.test",
                               "password": "pw123456"})
    assert c.get(r.headers["Location"]).headers.get(
        "Location", "").endswith("/onboarding")
    r = c.post("/onboarding", data={"age": "30", "gender": "ذكر",
                                    "height": "175", "weight": "80"})
    dest = r.headers.get("Location", "")
    assert dest.startswith("/book?") and "slot=" in dest, dest


# ── ٥) و٦) القايمة الجانبية ─────────────────────────────────────────

def _sidebar(page):
    return page[page.index('<nav class="sidebar"'):page.index("</nav>",
                                                                page.index('<nav class="sidebar"'))]


def test_the_admin_menu_marks_the_page_you_are_on():
    c = _as(ADMIN)
    for path in ("/admin/requests", "/admin/users", "/admin/notifications",
                 "/admin/blocked", "/saved"):
        nav = _sidebar(c.get(path).get_data(as_text=True))
        assert re.search(r'href="%s" class="nav-item active' % re.escape(path), nav), path


def test_every_page_name_in_the_menu_is_a_real_page():
    """‏الأسماء دي بتتكتب بإيدنا، والغلطة فيها ساكتة: الصفحة بتفتح عادي
    والعلامة بس هي اللي بتختفي."""
    real = {r.endpoint for r in A.app.url_map.iter_rules()}
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = open(os.path.join(here, "templates", "base.html"), encoding="utf-8").read()
    used = set()
    for group in re.findall(r"request\.endpoint\s*(?:in|==)\s*(\[[^\]]*\]|'[^']*')", base):
        used |= set(re.findall(r"'([^']+)'", group))
    assert not used - real, sorted(used - real)


def test_a_clients_profile_keeps_the_admins_own_menu():
    page = _as(ADMIN).get("/admin/users/%d" % ALICE).get_data(as_text=True)
    nav = _sidebar(page)
    assert "admin@nutrax.com" in nav and "alice@d.test" not in nav, \
        "the sidebar is the client's"
    assert 'href="/admin/calendar"' in nav, "the admin menu is gone"
    assert 'href="/request-plan"' not in nav, "the client menu is showing"
    # ‏والصفحة نفسها لسه بتعرض العميل
    assert "alice@d.test" in page


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

# -*- coding: utf-8 -*-
"""‏نسخة احتياطية بزرار، وفيها كل الجداول.

‏الموقع وقع يوم ٢٠ أكتوبر ٢٠٢٦: حصة قاعدة Neon الشهرية خلصت والمشروع
اتوقف. البيانات ماراحتش (التوقف مش حذف)، بس أول سؤال اتسأل كان "فيه
نسخة احتياطية؟" والإجابة كانت لأ.

‏والسبب مش إهمال: الأداة الموجودة محتاجة Terminal وPython ورابط
القاعدة، والدكتور بيشتغل من المتصفح. **أداة محدش يقدر يشغّلها مش
أداة.**

‏وحاجة تانية طلعت وإحنا بنعملها: قايمة الجداول في الأداة القديمة
**بقت قديمة** -- ناقصها plan_visits (كل الزيارات والأوزان، أهم جدول
في العيادة) وplan_links. يعني نسخة كانت بتتاخد ناقصة المتابعات كلها،
ومحدش هيعرف غير يوم ما يحتاجها. عشان كده القايمة بقت بتتقرا من
القاعدة نفسها.

Run with:  python3 tests/test_backup.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
os.environ["NUTRAX_DB"] = "/tmp/nutrax_backup_test.db"

import app as A          # noqa: E402
import backup            # noqa: E402
import core              # noqa: E402


def _schema_tables():
    """‏الجداول اللي المشروع بيعملها فعلاً، من كود الإنشاء نفسه."""
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "core.py"), encoding="utf-8") as f:
        src = f.read()
    return set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", src))


# ── الجداول ──────────────────────────────────────────────────────────

def test_the_table_list_comes_from_the_database_not_a_hand_written_list():
    """‏القايمة المكتوبة بالإيد بتبقى قديمة، ومحدش بيعرف غير يوم ما
    يحتاج النسخة."""
    with A.app.app_context():
        found = set(backup.tables(core.db_rows))
    assert found, "‏مالقاش ولا جدول"
    missing = _schema_tables() - found - set(backup.SKIP)
    assert not missing, "‏جداول مش في النسخة: %s" % sorted(missing)


def test_the_visits_table_is_in_the_backup():
    """‏plan_visits = كل زيارة وكل وزن ولوحة المتابعة كلها. كان ناقص
    من القايمة القديمة، وده الجدول اللي لو ضاع العيادة تفقد تاريخها."""
    with A.app.app_context():
        found = backup.tables(core.db_rows)
    assert "plan_visits" in found, found
    assert "plan_links" in found, found


def test_what_is_skipped_is_skipped_on_purpose_and_said_out_loud():
    """‏اللي بيتشال لازم يكون مذكور في النسخة نفسها، عشان اللي بيسترجع
    يعرف إيه اللي مش فيها."""
    with A.app.app_context():
        snap = backup.snapshot(core.db_rows)
    assert snap["skipped"] == list(backup.SKIP), snap["skipped"]
    for name in backup.SKIP:
        assert name not in snap["tables"], name


# ── النسخة نفسها ────────────────────────────────────────────────────

def test_the_snapshot_carries_the_rows_not_only_the_names():
    with A.app.app_context():
        core.db_run("DELETE FROM plan_visits")
        core.db_run("""INSERT INTO plan_visits
                       (user_id, client_key, client_name, weight)
                       VALUES (?,?,?,?)""", (1, "k1", "عميل النسخة", 88.5))
        snap = backup.snapshot(core.db_rows)
    rows = snap["tables"]["plan_visits"]
    assert rows, snap["counts"]
    assert any(r.get("client_name") == "عميل النسخة" for r in rows), rows


def test_the_snapshot_counts_every_table_so_a_short_backup_is_visible():
    """‏نسخة ناقصة وساكتة أسوأ من مافيش نسخة -- بتدي إحساس أمان مش
    موجود."""
    with A.app.app_context():
        snap = backup.snapshot(core.db_rows)
    assert set(snap["counts"]) == set(snap["tables"]), (
        set(snap["counts"]) ^ set(snap["tables"]))
    for table, n in snap["counts"].items():
        assert n == len(snap["tables"][table]), table


def test_a_table_that_fails_is_reported_not_swallowed():
    real = core.db_rows
    calls = {"n": 0}

    def flaky(sql, *a, **k):
        calls["n"] += 1
        if "plan_visits" in sql and "information_schema" not in sql \
                and "sqlite_master" not in sql:
            raise RuntimeError("relation does not exist")
        return real(sql, *a, **k)

    with A.app.app_context():
        core.db_rows = flaky
        try:
            snap = backup.snapshot(core.db_rows)
        finally:
            core.db_rows = real
    assert "plan_visits" in snap["failed"], snap["failed"]
    assert "plan_visits" not in snap["tables"], "‏جدول فاشل اتعد كأنه نجح"


def test_the_json_is_readable_arabic_and_parses_back():
    with A.app.app_context():
        snap = backup.snapshot(core.db_rows)
    text = backup.as_json(snap)
    assert "\\u0639" not in text, "‏العربي اتكتب أكواد مش حروف"
    back = json.loads(text)
    assert back["counts"] == snap["counts"]


def test_the_filename_carries_the_date():
    name = backup.filename()
    assert re.match(r"nutrax-\d{4}-\d{2}-\d{2}_\d{4}\.json$", name), name


# ── الصفحة ───────────────────────────────────────────────────────────

def _client(role="admin"):
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["uid"] = 1
        s["role"] = role
        s["lang"] = "ar"
    return c


def test_the_button_downloads_a_file():
    r = _client().get("/admin/backup")
    assert r.status_code == 200, r.status_code
    assert "attachment" in r.headers.get("Content-Disposition", ""), r.headers
    assert ".json" in r.headers.get("Content-Disposition", ""), r.headers
    body = json.loads(r.get_data(as_text=True))
    assert body.get("counts"), body.keys()
    assert "plan_visits" in body["tables"], list(body["tables"])


def test_the_file_is_never_cached():
    """‏الملف فيه بيانات صحية لكل العملاء."""
    r = _client().get("/admin/backup")
    cc = r.headers.get("Cache-Control", "")
    assert "no-store" in cc, cc


def test_only_an_admin_can_take_it():
    """‏ده الملف الطبي كله في طلب واحد.

    ‏والاختبار بيعمل مستخدمين **حقيقيين** في القاعدة: admin_required
    بيقرا الدور من القاعدة مش من الجلسة (وده الصح -- جلسة الكوكي
    مايتبنيش عليها صلاحية). فتزوير الدور في الجلسة مابيختبرش حاجة.
    أول نسخة من الاختبار ده عملت كده وعدّت، وهي مااختبرتش الحارس أصلاً.
    """
    ids = {}
    with A.app.app_context():
        for role in ("client", "nutritionist"):
            email = "bk-%s@test.local" % role
            core.db_run("DELETE FROM users WHERE email=?", (email,))
            core.db_run(
                "INSERT INTO users (name,email,password,role,is_admin,active) "
                "VALUES (?,?,?,?,0,1)",
                ("Test " + role, email, core.hp("pw123456"), role))
            row = core.db_row("SELECT id FROM users WHERE email=?", (email,))
            ids[role] = row["id"]

    for role, uid in ids.items():
        c = A.app.test_client()
        with c.session_transaction() as s:
            s["uid"] = uid
            s["role"] = "admin"      # ‏دور مزوّر في الجلسة بالقصد
        r = c.get("/admin/backup")
        assert r.status_code in (302, 403), (
            "‏%s نزّل القاعدة كلها (%s)" % (role, r.status_code))

    anon = A.app.test_client().get("/admin/backup")
    assert anon.status_code in (302, 403), anon.status_code


def test_the_admin_page_offers_it_next_to_the_csv_export():
    """‏تصدير العملاء مش بديل: ده جدول users بس، والمتابعات مش فيه.
    فالزرارين جنب بعض عشان الفرق يبان."""
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "templates", "admin_users.html"),
            encoding="utf-8") as f:
        html = f.read()
    assert "/admin/backup" in html, "‏مافيش زرار للنسخة"
    assert "/admin/users/export" in html


def test_the_page_warns_what_is_in_the_file():
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "templates", "admin_users.html"),
            encoding="utf-8") as f:
        html = f.read()
    assert "مشفّر" in html, "‏مافيش تنبيه على محتوى الملف"


# ── الأداة القديمة ──────────────────────────────────────────────────

def test_the_command_line_tool_uses_the_same_code():
    """‏نسختين من نفس المنطق معناها إن واحدة هتبقى قديمة -- وده اللي
    حصل بالظبط مع قايمة الجداول."""
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "tools", "backup_db.py"),
            encoding="utf-8") as f:
        src = f.read()
    assert "import backup" in src, "‏الأداة لسه بتعمل الشغل لوحدها"
    assert not re.search(r"^TABLES = \[", src, re.M), (
        "‏قايمة الجداول المكتوبة بالإيد رجعت")


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

# -*- coding: utf-8 -*-
"""‏طبقة الاتصال بقاعدة البيانات -- على Postgres حقيقي.

**ليه الملف ده موجود:** الاستضافة بتشتغل على Postgres، والاختبارات كلها
كانت بتشتغل على SQLite. يعني الكود اللي بيوصل لقاعدة البيانات في الإنتاج
مكانش عليه ولا اختبار واحد -- وده بالظبط المكان اللي الباجات ظهرت فيه.

**الباج اللي مسكه:** من لوج الاستضافة --

    File ".../psycopg2/pool.py", in getconn
        self._lock.acquire()          ← العامل واقف هنا
    File ".../gunicorn/workers/base.py", in handle_abort
        sys.exit(1)
    [ERROR] Worker (pid:87) was sent SIGKILL!

‏الاستضافة بتقطع الطلب بعد ١٢٠ ثانية، والقطع بيوصل للكود كـSystemExit.
والـSystemExit مشتق من BaseException مش من Exception -- فـ"except
Exception" في طبقة الاتصال مكانش بيشوفه، والاتصال مكانش بيرجع للمخزن.
مقيس قبل التصليح: كل قطع بيزوّد اتصال مستخدم ومايرجّعوش (١، ٢، ٣، ٤، ٥)،
وبعد ٢٠ المخزن يخلص وكل طلب يفشل. وأسوأ: لو القطع جه وخيط ماسك قفل
المخزن، القفل يفضل مقفول والخيوط كلها تستنى عليه للأبد.

Run with:  python3 tests/test_db_connection.py
"""

import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

os.environ.setdefault("SECRET_KEY", "test-key")

LOCAL_DSN = "postgresql://postgres:testpw@127.0.0.1:5432/nutrax_dbtest"


def _try_dsn(dsn):
    try:
        import psycopg2
        conn = psycopg2.connect(dsn, connect_timeout=5)
        conn.close()
        return True
    except Exception:
        return False


def _start_local_cluster():
    """‏يشغّل Postgres المحلي ويجهّز قاعدة للاختبار، لو التوزيعة فيها واحد."""
    if not os.path.exists("/usr/bin/pg_ctlcluster"):
        return False
    subprocess.run(["pg_ctlcluster", "16", "main", "start"],
                   capture_output=True, timeout=60)
    for _ in range(15):
        if subprocess.run(["pg_isready", "-q"], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    subprocess.run(["su", "postgres", "-c",
                    "psql -c \"ALTER USER postgres PASSWORD 'testpw';\" "
                    "-c 'CREATE DATABASE nutrax_dbtest;'"],
                   capture_output=True, timeout=60)
    return _try_dsn(LOCAL_DSN)


def _database_url():
    """‏قاعدة Postgres للاختبار: من البيئة، وإلا واحدة محلية."""
    env = os.environ.get("TEST_DATABASE_URL") or ""
    if env and _try_dsn(env):
        return env
    if _try_dsn(LOCAL_DSN) or _start_local_cluster():
        return LOCAL_DSN
    return None


DSN = _database_url()
core = None
if DSN:
    os.environ["DATABASE_URL"] = DSN
    import core          # noqa: E402


def _need_db():
    assert core is not None, (
        "‏محتاج Postgres للاختبار ده. شغّل واحد محلي أو حط TEST_DATABASE_URL. "
        "طبقة الاتصال دي هي اللي الإنتاج ماشي عليها، فاختبارها مش اختياري."
    )


def _open_connections():
    row = core.db_row("SELECT count(*) AS n FROM pg_stat_activity "
                      "WHERE datname = current_database()")
    return int(row["n"])


class _Abort(BaseException):
    """‏زي SystemExit اللي gunicorn بيرميه لما يقطع الطلب."""


def _abort_a_query(sql="SELECT 1 AS ok", write=False):
    """‏يقطع الطلب **بعد** ما الاستعلام بدأ فعلاً.

    ‏التوقيت هو كل الحكاية: لو القطع جه قبل ما الاستعلام يشتغل، مافيش
    معاملة مفتوحة ومافيش حاجة تتلخبط -- وأول نسختين من الاختبار ده كانوا
    بيقطعوا في التوقيت الغلط، فكانوا بيعدّوا على الكود البايظ. القطع
    الحقيقي من الاستضافة بيجي بعد ١٢٠ ثانية، يعني وسط الاستعلام.
    """
    import unittest.mock as mock
    real = core.psycopg2.extras.RealDictCursor.execute

    def cut(self, *a, **k):
        real(self, *a, **k)          # ‏الاستعلام اشتغل والمعاملة مفتوحة
        raise _Abort("gunicorn timeout")

    with mock.patch.object(core.psycopg2.extras.RealDictCursor,
                           "execute", cut):
        try:
            if write:
                core.db_run(sql)
            else:
                core.db_row(sql)
        except BaseException:
            pass


def _observe(pid):
    """‏حالة اتصال معيّن، من **اتصال تاني** -- الاتصال مايقدرش يشوف نفسه."""
    import psycopg2
    obs = psycopg2.connect(DSN)
    try:
        with obs.cursor() as cur:
            cur.execute("SELECT state FROM pg_stat_activity WHERE pid = %s", (pid,))
            row = cur.fetchone()
            state = row[0] if row else None
            cur.execute("SELECT count(*) FROM pg_locks WHERE pid = %s "
                        "AND mode LIKE '%%Exclusive%%'", (pid,))
            locks = cur.fetchone()[0]
        return state, locks
    finally:
        obs.close()


def test_a_cut_off_write_does_not_leave_the_rows_locked():
    """‏أخطر نتيجة للقطع، ومقيسة بالأرقام.

    ‏لما الطلب بيتقطع وسط كتابة والمعاملة مافيهاش rollback، الاتصال
    بيفضل "idle in transaction" وماسك أقفال على الصفوف. أي طلب تاني
    بيلمس نفس الصفوف بيستنى عليه -- يعني الموقع بيقف، مش الطلب ده بس.

    مقيس، بنفس الكود وبفرق سطر واحد (BaseException -> Exception):

        بـrollback:    idle                  و٠ أقفال
        من غيره:       idle in transaction   و٣ أقفال
    """
    _need_db()
    core.db_run("CREATE TABLE IF NOT EXISTS _abort_probe (n INTEGER)")
    core.db_run("DELETE FROM _abort_probe")
    pid = core.db_row("SELECT pg_backend_pid() AS p")["p"]

    _abort_a_query("INSERT INTO _abort_probe (n) VALUES (99)", write=True)

    state, locks = _observe(pid)
    assert state == "idle", (
        "‏الاتصال سايب معاملة مفتوحة (%s) -- ماسك الصفوف وبيوقّف باقي "
        "الطلبات" % state)
    assert locks == 0, "‏الاتصال لسه ماسك %d قفل بعد القطع" % locks
    core.db_run("DROP TABLE _abort_probe")


def test_a_cut_off_request_does_not_leak_its_connection():
    """‏ده الباج نفسه. قبل التصليح: كل قطع بيسرّب اتصال لحد ما الموقع يقف."""
    _need_db()
    core.db_row("SELECT 1 AS ok")
    before = _open_connections()
    for _ in range(25):                     # ‏أكتر من maxconn القديم (٢٠)
        _abort_a_query()
    after = _open_connections()
    assert after <= before + 1, (
        "‏%d قطع سرّبوا اتصالات: %d -> %d" % (25, before, after))
    # ‏والأهم: الاتصال لازم يبقى نضيف بعد القطع. لو القطع ساب معاملة
    # مفتوحة، أي استعلام بعده بيرجع "current transaction is aborted"
    # وكل حاجة على الخيط ده بتقع.
    assert core.db_row("SELECT 1 AS ok")["ok"] == 1, "‏القاعدة وقفت بعد القطع"
    core.db_run("CREATE TABLE IF NOT EXISTS _abort_probe (n INTEGER)")
    core.db_run("INSERT INTO _abort_probe (n) VALUES (1)")
    assert core.db_row("SELECT count(*) AS n FROM _abort_probe")["n"] >= 1, (
        "‏الكتابة بعد القطع مااشتغلتش -- الاتصال ساب معاملة مفتوحة")
    core.db_run("DROP TABLE _abort_probe")


def test_a_slow_query_gives_up_before_the_host_kills_the_worker():
    """‏من غير حد للاستعلام، الطلب بيستنى ١٢٠ ثانية والاستضافة تقتل العامل --
    والموقع كله بيقع مش الطلب ده بس."""
    _need_db()
    shown = core.db_row("SHOW statement_timeout")["statement_timeout"]
    assert shown not in ("0", "", None), "‏مافيش حد لوقت الاستعلام"
    # ‏لازم أقل من ١٢٠ ثانية (حد الاستضافة) بفرق مريح
    seconds = float(shown.rstrip("smin ")) * (60 if shown.endswith("min") else 1)
    if shown.endswith("ms"):
        seconds = float(shown[:-2]) / 1000.0
    assert 1 <= seconds <= 60, "‏الحد %s مش منطقي" % shown

    started = time.time()
    try:
        core.db_row("SELECT pg_sleep(%s)" % (seconds + 15))
    except core.psycopg2.extensions.QueryCanceledError:
        pass
    else:
        raise AssertionError("‏الاستعلام البطيء عدّى الحد ومااتقطعش")
    took = time.time() - started
    assert took < seconds + 10, "‏القطع خد %.0f ثانية" % took
    # ‏وبعده الاتصال بيرجع شغّال، مش بايظ
    assert core.db_row("SELECT 1 AS ok")["ok"] == 1


def test_a_dead_connection_is_replaced_not_reported():
    """‏الاستضافة بتقفل الاتصالات الساكنة. أول طلب بعد سكون مايفشلش."""
    _need_db()
    core.db_row("SELECT 1 AS ok")
    conn = getattr(core._db_local, "conn", None)
    assert conn is not None, "‏الخيط مش ماسك اتصاله"
    conn.close()                     # ‏زي ما الاستضافة بتعمل
    assert core.db_row("SELECT 2 AS ok")["ok"] == 2, "‏اتصال ميّت مااتبدّلش"


def test_each_thread_gets_its_own_connection():
    """‏مافيش قفل مشترك -- ده اللي كان بيهجر ويوقّف كل الخيوط."""
    _need_db()
    seen = {}
    errors = []

    def work(name):
        try:
            core.db_row("SELECT 1 AS ok")
            seen[name] = id(getattr(core._db_local, "conn", None))
        except BaseException as e:      # noqa: BLE001
            errors.append(repr(e))

    threads = [threading.Thread(target=work, args=("t%d" % i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not any(t.is_alive() for t in threads), "‏خيط علّق -- قفل مهجور"
    assert not errors, errors
    assert len(set(seen.values())) == len(seen), "‏خيطين بيستخدموا نفس الاتصال"


def test_a_thread_that_is_cut_off_does_not_freeze_the_others():
    """‏السيناريو اللي كان في اللوج: خيط بيتقطع، والباقي بيستنى للأبد."""
    _need_db()
    core.db_row("SELECT 1 AS ok")
    victim = threading.Thread(target=lambda: [_abort_a_query() for _ in range(5)])
    victim.start()
    victim.join(timeout=30)
    assert not victim.is_alive(), "‏الخيط المقطوع علّق"

    done = []
    other = threading.Thread(
        target=lambda: done.append(core.db_row("SELECT 7 AS ok")["ok"]))
    other.start()
    other.join(timeout=20)
    assert not other.is_alive(), "‏خيط تاني علّق بعد القطع -- القفل مهجور"
    assert done == [7], done


def test_an_ordinary_sql_error_still_reaches_the_caller():
    """‏التصليح مايخفيش الغلطات: غلطة SQL لازم توصل زي ما هي."""
    _need_db()
    try:
        core.db_row("SELECT * FROM table_that_does_not_exist")
    except core.psycopg2.Error:
        pass
    else:
        raise AssertionError("‏غلطة SQL اتاكلت")
    assert core.db_row("SELECT 1 AS ok")["ok"] == 1, "‏الاتصال باظ بعد غلطة SQL"


def test_the_app_boots_and_builds_its_tables_on_postgres():
    """‏كل الاختبارات التانية على SQLite. ده بيتأكد إن الإنتاج بيقوم أصلاً."""
    _need_db()
    tables = {r["tablename"] for r in core.db_rows(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
    for needed in ("users", "plan_visits", "plan_links", "plan_drafts",
                   "saved_plans", "notifications"):
        assert needed in tables, "‏جدول %s مااتعملش على Postgres" % needed


POOLER_DSN = "postgresql://postgres@127.0.0.1:6432/nutrax_dbtest"


def test_nothing_is_passed_as_a_connection_startup_parameter():
    """‏ده الشرط اللي كسر نشر كامل، ولازم يفضل مقفول.

    ‏قاعدة البيانات في الإنتاج بتتوصّل من خلال pooler، والبولر بيرفض أي
    startup parameter مش من اللي بيعرفها:

        FATAL: unsupported startup parameter in options: statement_timeout

    ‏فالتطبيق مقدرش يفتح ولا اتصال واحد ومات وقت التشغيل، والنشر فشل.
    وماظهرش في الاختبار لأن الاختبار كان على Postgres **مباشر** --
    والبولر هو اللي في الإنتاج.

    ‏الحد لازم يتحط بـSQL جوّه المعاملة (SET LOCAL)، مش بارامتر فتح اتصال.
    """
    with open(os.path.join(ROOT, "core.py"), encoding="utf-8") as fh:
        source = fh.read()
    layer = source[source.index("if DATABASE_URL:"):]
    layer = layer[:layer.index("from werkzeug.security import")]
    layer = "\n".join(line.split("#")[0] for line in layer.splitlines())

    connect = layer[layer.index("psycopg2.connect("):]
    connect = connect[:connect.index(")")]
    assert "options" not in connect, (
        "‏فيه startup parameter في فتح الاتصال -- البولر بيرفض الاتصال "
        "من أصله والتطبيق مايقومش: %s" % " ".join(connect.split()))
    # ‏والحد لازم يفضل موجود، بس بالطريقة اللي بتمشي على البولر
    assert "SET LOCAL statement_timeout" in layer, (
        "‏حد وقت الاستعلام اتشال خالص")


def _pooler_ready():
    try:
        import psycopg2
        conn = psycopg2.connect(POOLER_DSN, connect_timeout=5)
        conn.close()
        return True
    except Exception:
        return False


def test_the_app_boots_through_a_transaction_pooler():
    """‏نفس شكل الإنتاج: pooler بيوزّع اتصال السيرفر على عملاء كتير.

    ‏لو مافيش pooler محلي، الاختبار بيتأكد من الشرط اللي كسر النشر بس
    (اللي فوق) -- وده الحاجة اللي بترجع بسطر واحد.
    """
    if not _pooler_ready():
        # ‏مافيش بولر هنا. الشرط الثابت فوق هو اللي بيمنع رجوع الباج،
        # وهو بيشتغل على أي جهاز. فبنتأكد إنه موجود وخلاص.
        test_nothing_is_passed_as_a_connection_startup_parameter()
        return

    import subprocess
    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "import core, psycopg2\n"
        "assert core.db_row('SELECT 1 AS ok')['ok'] == 1\n"
        "print('TIMEOUT=' + core.db_row("
        "  \"SELECT current_setting('statement_timeout') AS t\")['t'])\n"
        "try:\n"
        "    core.db_row('SELECT pg_sleep(40)')\n"
        "    print('SLOW=ran')\n"
        "except psycopg2.extensions.QueryCanceledError:\n"
        "    print('SLOW=cancelled')\n"
        "assert core.db_row('SELECT 2 AS ok')['ok'] == 2\n"
        "print('OK')\n" % ROOT)
    env = dict(os.environ, DATABASE_URL=POOLER_DSN, SECRET_KEY="test-key")
    run = subprocess.run([sys.executable, "-c", script], capture_output=True,
                         text=True, env=env, timeout=180)
    out = run.stdout
    assert "OK" in out, "‏التطبيق مقامش على البولر:\n%s\n%s" % (
        out[-400:], (run.stderr or "")[-600:])
    assert "SLOW=cancelled" in out, (
        "‏الاستعلام البطيء مااتقطعش على البولر -- الحد مش بيوصل: %s" % out)
    assert "TIMEOUT=" in out and "TIMEOUT=0" not in out, out


def test_the_leak_that_was_fixed_cannot_come_back_quietly():
    """‏الباج ده بيرجع بتغيير سطر واحد، فالسطر ده مقفول باختبار.

    مش بديل عن الاختبارات اللي فوق -- ده للحالة اللي حد فيها يشغّل
    الطقم على جهاز مافيهوش Postgres، فالاختبارات الحية مش هتلاقي قاعدة.
    """
    with open(os.path.join(ROOT, "core.py"), encoding="utf-8") as fh:
        source = fh.read()
    layer = source[source.index("if DATABASE_URL:"):]
    layer = layer[:layer.index("from werkzeug.security import")]
    # ‏الكومنتات بتشرح الباج وبتسمّي المخزن القديم بالاسم، فبتتشال قبل
    # الفحص -- وإلا الشرح نفسه يبقى مخالفة.
    layer = "\n".join(line.split("#")[0] for line in layer.splitlines())

    assert "except BaseException:" in layer, (
        "‏طبقة الاتصال بتمسك Exception بس. القطع من الاستضافة بيجي "
        "SystemExit وهو BaseException -- وده اللي كان بيسرّب الاتصالات.")
    assert "ThreadedConnectionPool" not in layer, (
        "‏المخزن المشترك رجع -- قفله بيتهجر لما الطلب يتقطع ويوقّف كل الخيوط")
    assert "_lock" not in layer, "‏قفل مشترك رجع في طبقة الاتصال"
    assert "statement_timeout" in layer, (
        "‏مافيش حد لوقت الاستعلام -- الطلب بيقدر يستنى لحد ما الاستضافة "
        "تقتل العامل")
    assert "threading.local()" in layer, "‏الاتصال مش لكل خيط لوحده"


if __name__ == "__main__":
    if not DSN:
        print("  ⚠️  مافيش Postgres -- الاختبارات الحية هتفشل، وده مقصود.")
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

# -*- coding: utf-8 -*-
"""‏النسخ الاحتياطي اليومي (GitHub Actions -> Cloudflare R2).

‏ليه: النسخة كانت بتتاخد يدوي من كمبيوتر (tools/backup_db.py)، وصاحب
المشروع مالوش كمبيوتر -- يعني بيانات العملاء كانت في نسخة واحدة بس على
Neon. والريبو Public: سجل الـworkflow بيشوفه أي حد، وأي artifact بيتنزّل
لأي حد مسجّل. فالنسخة بتتشفّر قبل ما تخرج من الجهاز، ومفيش artifact.

Run with:  python3 tests/test_backup_workflow.py
"""

import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows", "db-backup.yml")


def _wf():
    with open(WF, encoding="utf-8") as fh:
        return fh.read(), yaml.safe_load(open(WF, encoding="utf-8"))


def _run(doc):
    job = next(iter(doc["jobs"].values()))
    return job, "\n".join(s.get("run", "") for s in job["steps"])


def test_it_runs_every_day_and_on_demand():
    _, doc = _wf()
    on = doc.get("on", doc.get(True))   # ‏yaml بيقرا on كـTrue
    assert on["schedule"][0]["cron"] and "workflow_dispatch" in on, on


def test_no_secret_is_written_in_the_file():
    text, _ = _wf()
    assert not re.search(r"postgres(ql)?://", text), "رابط قاعدة مكتوب في الملف"
    for name in ("DATABASE_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "BACKUP_PASSPHRASE"):
        assert "secrets.%s" % name in text, name


def test_the_dump_is_encrypted_before_it_leaves():
    text, doc = _wf()
    job, run = _run(doc)
    assert "gpg" in run and "--symmetric" in run, "النسخة مش متشفّرة"
    assert run.index("--symmetric") < run.index("s3 cp"), "بيرفع قبل التشفير"
    # ‏اللي بيترفع هو الملف المشفّر بس
    up = re.search(r"s3 cp\s+(\S+)", run).group(1)
    assert up.endswith('.gpg"') or up.endswith(".gpg"), up
    assert "upload-artifact" not in text, "artifact في ريبو Public بيتنزّل لأي حد"
    assert "set -x" not in run, "set -x بيطبع الأوامر في سجل عام"


def test_old_copies_are_removed_and_permissions_are_minimal():
    text, doc = _wf()
    assert doc["permissions"] == {"contents": "read"}, doc.get("permissions")
    assert "KEEP" in text and "delete-object" in text, "النسخ القديمة مابتتمسحش"


def test_a_failed_dump_fails_the_run():
    """‏pg_dump لو فشل والـpipe كمّل، كان هيترفع ملف فاضي ويطلع أخضر."""
    _, doc = _wf()
    job, run = _run(doc)
    assert "set -euo pipefail" in run
    assert "-s " in run or "test -s" in run, "مفيش فحص إن النسخة مش فاضية"


def test_the_restore_is_written_down():
    doc = open(os.path.join(ROOT, "docs", "backups.md"), encoding="utf-8").read()
    assert "db-backup.yml" in doc and "gpg --decrypt" in doc


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, "--", repr(e)[:300])
    print("\n%d passed, %d failed" % (len(tests) - failed, failed))
    sys.exit(1 if failed else 0)

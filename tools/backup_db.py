# -*- coding: utf-8 -*-
"""Take a backup of the live database.

There was no backup mechanism in this project at all -- no pg_dump, nothing.
Render's free Postgres also expires and has to be recreated, which makes an
export something you want in hand rather than something you go looking for
afterwards.

    python3 tools/backup_db.py                  # writes ./backups/nutrax-<date>.sql
    python3 tools/backup_db.py --out /path/dir  # somewhere else
    python3 tools/backup_db.py --json           # portable JSON instead of SQL

SQL (via pg_dump) is the one to restore from. JSON needs no tools to read and
is there for when you want to look inside a backup, or move the data somewhere
that is not Postgres.

Run it from your own machine with DATABASE_URL set to the connection string
from Render (Dashboard -> the database -> "External Database URL"):

    DATABASE_URL='postgres://...' python3 tools/backup_db.py

The file contains every client's personal and health data. Keep it encrypted,
keep it off shared drives, and delete old copies you no longer need.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# tables worth keeping, in an order that restores cleanly
TABLES = [
    "users", "plan_requests", "payments", "subscriptions", "messages",
    "notifications", "meal_checks", "weight_log", "blocked_users",
    "patients", "saved_plans", "api_keys",
]


def _stamp():
    return datetime.now().strftime("%Y-%m-%d_%H%M")


def dump_sql(db_url, out_dir):
    if not shutil.which("pg_dump"):
        print("pg_dump is not installed. Either install the postgresql client\n"
              "(macOS: brew install libpq   Ubuntu: sudo apt install postgresql-client)\n"
              "or run with --json, which needs nothing extra.", file=sys.stderr)
        return None
    path = os.path.join(out_dir, f"nutrax-{_stamp()}.sql")
    print(f"running pg_dump -> {path}")
    with open(path, "w", encoding="utf-8") as fh:
        r = subprocess.run(["pg_dump", "--no-owner", "--no-acl", db_url],
                           stdout=fh, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        os.remove(path)
        print(f"pg_dump failed:\n{r.stderr.strip()[:500]}", file=sys.stderr)
        return None
    return path


def dump_json(out_dir):
    """Table-by-table export through the app's own database helpers."""
    import app as A

    path = os.path.join(out_dir, f"nutrax-{_stamp()}.json")
    data, skipped = {}, []
    for table in TABLES:
        try:
            rows = A.db_rows(f"SELECT * FROM {table}") or []
            data[table] = [dict(r) for r in rows]
            print(f"  {table:18} {len(data[table]):>6} rows")
        except Exception as e:
            skipped.append(table)
            print(f"  {table:18} skipped ({str(e)[:60]})")

    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"taken_at": datetime.now().isoformat(),
                   "tables": data, "skipped": skipped},
                  fh, ensure_ascii=False, indent=2, default=str)
    return path


def main():
    ap = argparse.ArgumentParser(description="Back up the NutraX database.")
    ap.add_argument("--out", default="backups", help="directory to write into")
    ap.add_argument("--json", action="store_true",
                    help="portable JSON export instead of pg_dump SQL")
    args = ap.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    # Only pg_dump needs the connection string. The JSON export goes through the
    # app's own helpers, so it backs up whatever the app itself is talking to --
    # Postgres in production, the local SQLite file in development.
    if not args.json and not db_url:
        print("DATABASE_URL is not set, so there is no Postgres database to dump.\n"
              "Copy the External Database URL from the Render dashboard:\n\n"
              "    DATABASE_URL='postgres://...' python3 tools/backup_db.py\n\n"
              "Or use --json to export whatever database the app is configured "
              "to use right now.\n",
              file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    path = dump_json(args.out) if args.json else dump_sql(db_url, args.out)
    if not path:
        return 1

    size = os.path.getsize(path)
    print(f"\nbackup written: {path}  ({size/1024:.0f} KB)")
    if size < 2048:
        print("WARNING: that file is suspiciously small. Open it and check it "
              "actually holds your data before trusting it.", file=sys.stderr)
    print("\nThis file holds clients' personal and health data. Store it "
          "encrypted and do not leave it in a shared folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""Populate a staging database with accounts for TestSprite to test against.

Creates one nutritionist (the account TestSprite signs in with), one onboarded
client with an active subscription and an approved plan, and one fresh client
with nothing, so the onboarding and paywall paths are both reachable.

Safety: this refuses to run unless ALLOW_SEED=1 AND the database contains
nothing but the bootstrap admin and rows this script created before. Production
holds real clients, so the second check fails there even if ALLOW_SEED is set by
mistake. Nothing here ever deletes or edits a row it did not create.

    ALLOW_SEED=1 python3 tools/seed_staging.py

Re-running is safe: existing seed accounts are left alone, only missing ones are
added. Passwords are printed once, at the end, so you can paste them into
TestSprite.
"""

import json
import os
import secrets
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# every account this script owns lives on this domain, which is not a real one
SEED_DOMAIN = "staging.nutrax.test"
BOOTSTRAP_ADMIN = "admin@nutrax.com"


def _fail(msg):
    print(f"\nREFUSING TO SEED: {msg}\n", file=sys.stderr)
    raise SystemExit(1)


def main():
    if os.environ.get("ALLOW_SEED") != "1":
        _fail("ALLOW_SEED is not set to 1. This is meant for staging only.")

    import app as A
    from werkzeug.security import generate_password_hash

    # ── guard: does this database look like production? ────────────────────
    rows = A.db_rows("SELECT email, role FROM users") or []
    strangers = [r["email"] for r in rows
                 if r["email"] != BOOTSTRAP_ADMIN
                 and not (r["email"] or "").endswith("@" + SEED_DOMAIN)]
    if strangers:
        _fail(
            f"found {len(strangers)} account(s) that this script did not create, "
            f"e.g. {strangers[0]!r}. That means this is not an empty staging "
            f"database -- it may well be production. Point DATABASE_URL at the "
            f"staging database and try again."
        )

    existing = {r["email"] for r in rows}
    created = []

    def add_user(email, name, role, pw, **cols):
        if email in existing:
            print(f"  kept    {email}  (already there)")
            return A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]
        keys = ["name", "email", "password", "role", "active"] + list(cols)
        vals = [name, email, generate_password_hash(pw), role, 1] + list(cols.values())
        A.db_run(f"INSERT INTO users ({','.join(keys)}) "
                 f"VALUES ({','.join(['?'] * len(keys))})", tuple(vals))
        uid = A.db_row("SELECT id FROM users WHERE email=?", (email,))["id"]
        created.append((name, email, pw, role))
        print(f"  created {email}  ({role})")
        return uid

    print("seeding staging accounts:")

    nut_pw = secrets.token_urlsafe(12)
    add_user(f"testsprite@{SEED_DOMAIN}", "TestSprite Bot", "nutritionist", nut_pw,
             onboarded_at=datetime.now(), phone="01000000001", country="مصر")

    cli_pw = secrets.token_urlsafe(12)
    cid = add_user(f"client@{SEED_DOMAIN}", "Test Client", "client", cli_pw,
                   onboarded_at=datetime.now(), height=170, weight=80, age=30,
                   gender="ذكر", phone="01000000002", country="مصر",
                   conditions=json.dumps(["سكري النوع الثاني"], ensure_ascii=False))

    fresh_pw = secrets.token_urlsafe(12)
    add_user(f"fresh@{SEED_DOMAIN}", "Fresh Client", "client", fresh_pw,
             phone="01000000003")

    # give the onboarded client access and a plan, so the paywalled pages and
    # the plan pages are both reachable
    if not A.db_row("SELECT id FROM payments WHERE user_id=?", (cid,)):
        A.db_run(
            "INSERT INTO payments (user_id, stripe_session_id, plan_key, status, "
            "currency, amount, expires_at) VALUES (?,?,?,?,?,?,?)",
            (cid, f"seed_{secrets.token_hex(6)}", "monthly_subscription",
             "completed", "EGP", 100000, datetime.now() + timedelta(days=30)))
        print("  created active subscription for the test client")

    if not A.db_row("SELECT id FROM plan_requests WHERE client_id=?", (cid,)):
        data = {"goal_type": "weight_loss", "culture": "مصري", "goal_cal": 1600,
                "gender": "ذكر", "height": 170, "weight": 80, "age": 30,
                "diet_plan_type": "standard",
                "symptoms": ["سكري النوع الثاني"], "notes": ""}
        info = A.get_diet_plan_info("standard")
        plan = []
        for i, day in enumerate(A.ARABIC_DAYS):
            d = {"day": day, "diet_type": "standard", "total_cal": 1600,
                 "meal_labels": info["meal_labels"], "meal_emojis": info["meal_emojis"]}
            for key in info["meals"]:
                pool = A.get_meal_pool("weight_loss", "مصري").get(
                    key if key in ("breakfast", "lunch", "dinner") else "breakfast", [])
                if pool:
                    d[key] = pool[i % len(pool)]["meal"]
            plan.append(d)
        rd = json.dumps(data, ensure_ascii=False)
        pd = json.dumps({"data": data, "plan": plan}, ensure_ascii=False)
        for status in ("approved", "pending"):
            A.db_run("INSERT INTO plan_requests (client_id, client_name, status, "
                     "request_data, plan_data) VALUES (?,?,?,?,?)",
                     (cid, "Test Client", status, rd, pd))
        print("  created one approved and one pending plan request")

    if not created:
        print("\nnothing new to create -- the staging accounts were already set up.")
        print("Passwords are only shown when an account is first created. To get a")
        print("fresh one, delete the account in Manage Users and re-run this.")
        return

    print("\n" + "=" * 68)
    print("PASSWORDS -- shown once. Copy them now.")
    print("=" * 68)
    for name, email, pw, role in created:
        print(f"  {role:14} {email}")
        print(f"  {'':14} {pw}")
    print("=" * 68)
    print("Put the nutritionist email and password into TestSprite ->")
    print("Authentication. That is the account it signs in with.")


if __name__ == "__main__":
    main()

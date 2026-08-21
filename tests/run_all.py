# -*- coding: utf-8 -*-
"""Run every test suite. Exit code 1 if anything failed.

    python3 tests/run_all.py

Each suite runs in its own process, because they seed the same database and
importing the app twice in one process would collide.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [
    "test_medical_filtering.py",
    "test_access_control.py",
    "test_translation.py",
    "test_zigzag.py",
    "test_food_data.py",
]


def main():
    total_pass = total_fail = 0
    broken = []
    for suite in SUITES:
        print(f"\n{'=' * 62}\n  {suite}\n{'=' * 62}")
        env = dict(os.environ, SECRET_KEY=os.environ.get("SECRET_KEY", "test-key"))
        # each suite seeds from scratch
        if os.path.exists("/tmp/nutrax.db"):
            os.remove("/tmp/nutrax.db")
        r = subprocess.run([sys.executable, os.path.join(HERE, suite)],
                           capture_output=True, text=True, env=env)
        for line in r.stdout.splitlines():
            if line.strip().startswith(("PASS", "FAIL")) or " passed," in line:
                print("  " + line.strip())
                if line.strip().startswith("FAIL"):
                    total_fail += 1
                elif line.strip().startswith("PASS"):
                    total_pass += 1
            elif line.startswith("        "):
                print(line)
        if r.returncode != 0 and total_fail == 0:
            broken.append(suite)
            print(f"  suite crashed:\n{(r.stderr or '')[-600:]}")

    print(f"\n{'=' * 62}")
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed"
          + (f", {len(broken)} suite(s) crashed" if broken else ""))
    print("=" * 62)
    return 1 if (total_fail or broken) else 0


if __name__ == "__main__":
    raise SystemExit(main())

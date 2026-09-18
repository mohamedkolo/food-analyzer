#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# The project's own dependencies.
#
# Without these, 7 of the 8 test suites cannot even import the app: core.py
# does `from flask import ...` at module level, so run_all.py reports them as
# "suite crashed" and only test_food_data.py (pure data, no app import) runs.
# That silently drops coverage from 93 tests to 23 -- including every medical
# filtering and access control test, which are the ones worth having.
#
# Two workarounds are needed on this image, both caused by Debian's patched
# setuptools/pip rather than by anything in requirements.txt:
#
#   1. setuptools upgrade -- pywebpush pulls in http-ece, which still builds
#      via legacy setup.py. Debian's setuptools 68 raises
#      "AttributeError: install_layout" on that path.
#   2. --ignore-installed blinker -- flask wants a newer blinker, but the
#      Debian-installed one has no RECORD file, so pip cannot uninstall it
#      ("Cannot uninstall blinker 1.7.0, RECORD file not found").
pip install --upgrade --ignore-installed setuptools   # errors propagate
#
# The path is derived from this script's own location rather than the working
# directory, which a hook cannot assume.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
pip install -r "$REPO_ROOT/requirements.txt" --ignore-installed blinker   # errors propagate

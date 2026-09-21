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
# ‏قاعدة الاختبارات: منفصلة عن /tmp/nutrax.db بتاعة التشغيل المحلي
TEST_DB = os.environ.get("NUTRAX_TEST_DB", "/tmp/nutrax_suite.db")
SUITES = [
    "test_medical_filtering.py",
    "test_access_control.py",
    "test_translation.py",
    "test_zigzag.py",
    "test_food_data.py",
    "test_followup.py",
    "test_plan_link.py",
    "test_plan_editing.py",
    "test_chemical_diet.py",
    "test_sleeve_diet.py",
    "test_form_prefill.py",
    "test_pdf_unbranded.py",
    "test_accessibility.py",
]


def main():
    total_pass = total_fail = 0
    broken = []
    for suite in SUITES:
        print(f"\n{'=' * 62}\n  {suite}\n{'=' * 62}")
        # ‏الاختبارات ليها قاعدتها. قبل كده كانت بتمسح /tmp/nutrax.db --
        # وهي نفسها القاعدة اللي التطبيق بيستخدمها لما تشغّله محلياً، فتشغيل
        # الاختبارات كان بيضيّع حساب الأدمن واللي إنت مسجّله للتجربة.
        env = dict(os.environ, SECRET_KEY=os.environ.get("SECRET_KEY", "test-key"),
                   NUTRAX_DB=TEST_DB)
        # each suite seeds from scratch
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
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

        # ‏كل def test_ في الملف لازم يطلع في النتيجة. حصل إني كتبت خمس
        # اختبارات بعد بلوك __main__، فالرنر كان بيلف على globals قبل ما
        # تتعرّف -- عدّت ولا مرة، والطقم قال "كل حاجة بتعدّي". اختبار
        # مابيشتغلش أسوأ من اختبار فاشل: الفاشل بيقولك.
        declared = sum(1 for line in
                       open(os.path.join(HERE, suite), encoding="utf-8")
                       if line.startswith("def test_"))
        ran = sum(1 for line in r.stdout.splitlines()
                  if line.strip().startswith(("PASS", "FAIL")))
        if declared != ran:
            broken.append(f"{suite} ({declared} معرّفة، {ran} اشتغلت)")
            print(f"  ⚠️  {declared} اختبار معرّف في الملف و{ran} بس اشتغل"
                  f" -- في اختبارات مش بتتنادى")

    print(f"\n{'=' * 62}")
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed"
          + (f", {len(broken)} suite(s) crashed" if broken else ""))
    print("=" * 62)
    return 1 if (total_fail or broken) else 0


if __name__ == "__main__":
    raise SystemExit(main())

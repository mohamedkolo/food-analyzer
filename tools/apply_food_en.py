# -*- coding: utf-8 -*-
"""Write note_en / tip_en into the FOODS array in templates/analyzer.html.

Reads the translations from food_notes_en.py and injects them next to each
food's Arabic note and tip, so the template stays the single source of truth
for what the page ships. Idempotent -- existing note_en/tip_en are replaced.

  python3 tools/apply_food_en.py --audit    report coverage, change nothing
  python3 tools/apply_food_en.py            write the translations in
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from food_notes_en import NOTES_EN, TIPS_EN  # noqa: E402

TEMPLATE = os.path.join(ROOT, "templates", "analyzer.html")

# one food entry: ...note:"…"[,note_en:"…"],tip:"…"[,tip_en:"…"]}
ENTRY = re.compile(
    r'note:"((?:[^"\\]|\\.)*)"(?:,note_en:"(?:[^"\\]|\\.)*")?'
    r',\s*tip:"((?:[^"\\]|\\.)*)"(?:,tip_en:"(?:[^"\\]|\\.)*")?'
)


def esc(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def main(audit=False):
    src = io.open(TEMPLATE, encoding="utf-8").read()
    stats = {"notes": 0, "tips": 0, "miss_notes": [], "miss_tips": []}

    def repl(m):
        note, tip = m.group(1), m.group(2)
        note_en, tip_en = NOTES_EN.get(note), TIPS_EN.get(tip)
        if note_en:
            stats["notes"] += 1
        else:
            stats["miss_notes"].append(note)
        if tip_en:
            stats["tips"] += 1
        else:
            stats["miss_tips"].append(tip)
        out = f'note:"{note}"'
        if note_en:
            out += f',note_en:"{esc(note_en)}"'
        out += f',tip:"{tip}"'
        if tip_en:
            out += f',tip_en:"{esc(tip_en)}"'
        return out

    new = ENTRY.sub(repl, src)
    total = stats["notes"] + len(stats["miss_notes"])

    print(f"food entries      : {total}")
    print(f"notes translated  : {stats['notes']}/{total}")
    print(f"tips  translated  : {stats['tips']}/{total}")

    remaining = len(stats["miss_notes"]) + len(stats["miss_tips"])
    if remaining:
        print(f"still to do       : {remaining} strings")

    if audit:
        # dedupe, keep order, so batches can be worked through predictably
        def uniq(xs):
            seen, out = set(), []
            for x in xs:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out
        io.open("/tmp/miss_notes.txt", "w", encoding="utf-8").write(
            "\n".join(uniq(stats["miss_notes"])))
        io.open("/tmp/miss_tips.txt", "w", encoding="utf-8").write(
            "\n".join(uniq(stats["miss_tips"])))
        print("unmapped written to /tmp/miss_notes.txt and /tmp/miss_tips.txt")
        return

    io.open(TEMPLATE, "w", encoding="utf-8").write(new)
    print("written to", os.path.relpath(TEMPLATE, ROOT))


if __name__ == "__main__":
    main(audit="--audit" in sys.argv)

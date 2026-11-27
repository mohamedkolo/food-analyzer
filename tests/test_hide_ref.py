# -*- coding: utf-8 -*-
"""The "(USDA n)" key is hidden on display only; stored text, calculation identity and wrong references are never touched."""
import json
import os
import shutil
import subprocess
import sys

os.environ.setdefault("SECRET_KEY", "k"); os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import food_suggest as F
import meal_variant_foods as V

FISH = "سمك بوري نيّء (USDA 175123)"
RICE = "أرز أبيض حبة متوسطة مطبوخ (USDA 168930)"


def test_known_ref_hidden_grams_kept():
    assert F.hide_ref("150جم " + FISH) == "150جم سمك بوري نيّء"
    assert F.hide_ref("دجاج بالكوسة 120 جم + 130جم " + RICE) == "دجاج بالكوسة 120 جم + 130جم أرز أبيض حبة متوسطة مطبوخ"
    assert F.hide_ref(FISH + " 150جم") == "سمك بوري نيّء 150جم"
    assert F.hide_ref("أرز 100جم") == "أرز 100جم" and F.hide_ref("") == "" and F.hide_ref(None) is None


def test_unknown_or_mismatched_reference_stays_visible():
    # 175125 is not any offered row, and a real number after the WRONG name is not hidden either
    assert F.hide_ref("150جم سمك بوري نيّء (USDA 175125)") == "150جم سمك بوري نيّء (USDA 175125)"
    assert F.hide_ref("150جم سمك بوري نيّء (USDA 175124)") == "150جم سمك بوري نيّء (USDA 175124)"
    assert F.hide_ref("150جم سمك بلطي نيّء (USDA 175123)") == "150جم سمك بلطي نيّء (USDA 175123)"


def test_stored_names_keep_key_and_clean_names_are_unique():
    assert all("(USDA %d)" % f["fdc"] in f["n"] for f in V.VARIANT_FOODS)
    pairs = F._ref_names()
    assert len({c for _, c in pairs}) == len(pairs), "two stored names would show the same clean name"


def test_filters_hide_on_display():
    import core
    with core.app.test_request_context("/"):
        assert core.meal_en("150جم " + FISH) == "150جم سمك بوري نيّء"
        assert "USDA" not in core.meal_sheet("150جم " + FISH)


def test_calculation_is_the_same_with_the_key_in_the_stored_text():
    import meal_macros as M
    r = M.macros("150جم سمك بوري مطبوخ بالحرارة الجافة (USDA 175124)")
    assert r["complete"] and r["items"][0]["exact_identity"] and r["cal"] > 0


def _js(case):
    import core
    with core.app.test_request_context("/"):
        names = core.nx_ref_names()
    src = open(os.path.join(HERE, "templates", "preview.html"), encoding="utf-8").read()
    a, b = src.index("const NXN = "), src.index("function attachSuggest")
    code = src[a:b].replace("{{ nx_ref_names()|tojson }}", json.dumps(names, ensure_ascii=False))
    code += "\nconst FISH=%s, RICE=%s;\n%s\n" % (json.dumps(FISH, ensure_ascii=False), json.dumps(RICE, ensure_ascii=False), case)
    out = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr[-500:]
    return out.stdout.strip()


def test_edit_box_restores_only_the_identity_the_line_carried():
    if not shutil.which("node"):
        print("  (node missing: browser logic not run)"); return
    out = _js("""
const S = "دجاج 120 جم + 130جم " + RICE + " + 150جم " + FISH;
const al = new Set(); const h = nxHide(S, al);
const ck = (c, m) => { if (!c) throw new Error(m); };
ck(!h.includes("USDA"), "hidden");
ck(nxExpand(h, al) === S, "round trip");
ck(nxExpand(h.replace("130", "90"), al) === S.replace("130", "90"), "quantity-only edit keeps keys");
ck(nxExpand(S, al) === S, "idempotent, no double key");
ck(nxExpand(h.replace("سمك بوري نيّء", "سمك بلطي نيّء"), al).includes("سمك بلطي نيّء") && !nxExpand(h.replace("سمك بوري نيّء", "سمك بلطي نيّء"), al).includes("175123"), "renamed food gets no stale key");
ck(!nxExpand(h.replace("سمك بوري نيّء", "سمك بوري نيّء مشوي"), al).includes("175123"), "changed food (longer name) gets no stale key");
ck(!nxExpand(h.replace(" + 150جم سمك بوري نيّء", ""), al).includes("175123"), "deleted food leaves no key");
ck(nxExpand(h + " + 50جم سمك بوري نيّء", al).split("175123").length === 3, "same food typed twice gets its own key both times");
ck(nxExpand(h, new Set()) === h, "a name from another meal (not in this line) gets no key");
ck(nxExpand("150جم سمك بوري نيّء (USDA 175125)", al) === "150جم سمك بوري نيّء (USDA 175125)", "unknown key untouched");
const u = new Set(); ck(nxHide("150جم سمك بوري نيّء (USDA 175125)", u).includes("175125"), "unknown key stays visible in the box");
const r = nxExpand(nxHide(S, new Set()).split(" + ").reverse().join(" + "), al);
ck(r.includes(FISH) && r.includes(RICE), "reordered foods keep their own keys");
console.log("ok");
""")
    assert out == "ok", out


if __name__ == "__main__":
    n = 0
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v(); n += 1; print("ok", k)
    print(n, "passed")

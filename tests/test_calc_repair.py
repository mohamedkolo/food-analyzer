import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ADMIN_PASSWORD", "pw123456"); os.environ.setdefault("SECRET_KEY", "k")
import meal_macros as M, meal_variant_foods as V, portion_scale as P
ok = fail = 0
def check(c, m):
    global ok, fail
    if c: ok += 1
    else: fail += 1; print("FAIL", m)
raw = [f for f in V.VARIANT_FOODS if M.basis_of(f) == "raw"]
check(len(raw) == 20, "20 raw rows, got %d" % len(raw))
for f in V.VARIANT_FOODS:
    r = M.macros("100 جم " + f["n"]); it = r["items"][0]
    check(r["complete"] and it.get("exact_identity") and abs(r["cal"] - f["cal"]) <= 1.01, "row " + f["n"])
# unlabelled raw library rows still withheld
for n in ("Chicken thigh, no skin", "لحم بقري مفروم 90/10"):
    check(not M.macros("100جم " + n)["complete"], "unlabelled raw library row withheld: " + n)
r = M.macros("100جم سمك بوري نيّء (USDA 175125)"); check(not r["complete"], "unknown ref withheld")
# chip never shows kcal for a withheld item
for t in ["200جم حليب كامل الدسم مع فيتامين د (USDA 171265)", "150جم سمك بوري نيّء (USDA 175125) + 100جم أرز أبيض نيّء قبل الطبخ (USDA 168877)"]:
    un = set(M.macros(t)["unresolved"])
    for c in P.meal_items(t):
        check(not (c["cal"] is not None and c["text"] in un), "chip vs total " + c["text"])
import app
from routes_plans import _calc_warning
with app.app.test_request_context("/"):
    w = _calc_warning("150جم سمك بوري نيّء (USDA 175125)"); check("175125" in w and "مش محسوب" in w, "unknown warn " + w)
    w = _calc_warning("200جم سمك بوري نيّء (USDA 175123)"); check(w == "", "valid no warn " + w)
    w = _calc_warning("200جم صدر دجاج نيّء"); check("صدر" in w, "named: " + w)
print("PASS %d FAIL %d" % (ok, fail)); sys.exit(1 if fail else 0)

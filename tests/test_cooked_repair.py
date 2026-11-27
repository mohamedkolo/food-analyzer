# Cooked-weight repair (28 Nov 2026): cooked-only picker, reviewed cooked rows, fried egg.
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ADMIN_PASSWORD", "pw123456"); os.environ.setdefault("SECRET_KEY", "k")
import meal_macros as M, food_suggest as S, food_provenance as P
ok = fail = 0
def check(c, m):
    global ok, fail
    if c: ok += 1
    else: fail += 1; print("FAIL", m)
# reviewed cooked rows count only with a compatible cooking method word: 100 g = USDA cooked values
USDA = {"صدر دجاج مشوي": (165, 31.02), "سمك بلطي مشوي": (128, 26.15), "جمبري مسلوق": (99, 23.98), "بوري مشوي": (150, 24.81)}
for n, (kcal, prot) in USDA.items():
    r = M.macros("100جم " + n); it = r["items"][0]
    check(r["complete"] and not it.get("unresolved") and it.get("sourced"), "counted " + n)
    check(abs(r["cal"] - kcal) <= 1.5 and abs(r["p"] - prot) <= 1, "values " + n)
    check(it.get("explicit_quantity"), "explicit " + n)
# no method word, or an incompatible one: the generic cooked weight is not proof of roasted / dry heat
for t in ("100جم صدر دجاج", "100جم صدر دجاج مسلوق", "100جم صدر دجاج مقلي", "100جم سمك بلطي", "100جم بوري",
          "100جم جمبري", "100جم جمبري مشوي", "100جم جمبري مقلي", "100جم كابوريا", "100جم جراد البحر"):
    check(not M.macros(t)["complete"], "method not compatible, withheld: " + t)
# rows that fail the numeric check stay withheld
for n in ("سمك قاروص", "كبدة دجاج", "لحم بقري قليل الدهن", "فخذ دجاج", "فيليه بقري", "كبدة بقري"):
    check(not M.macros("100جم " + n)["complete"], "still withheld " + n)
# a parenthetical list cut by the " + " split is not one food (tuna salad with vegetables is not pure tuna)
r = M.macros("🥗 سلطة تونة كبيرة (تونة 150جم + خضار 250جم) + 🍞 خبز اسمر 100جم")
check(r["items"][0].get("unresolved") == "composite" and r["items"][0].get("cal") is None and r["items"][1].get("cal") == 138 and abs(r["cal"] - (138 + 293)) <= 2, "title piece composite, ingredient pieces counted as before " + str(r["cal"]))
import portion_scale as _PS
check([c["cal"] for c in _PS.meal_items("🥗 سلطة تونة كبيرة (تونة 150جم + خضار 250جم)")] == [None, None], "no chip for split parenthetical")
# a raw word on a cooked-weight row stays withheld
for t in ("100جم صدر دجاج مشوي نيء", "100جم سمك بلطي نيء مشوي", "100جم جمبري نيء"):
    check(not M.macros(t)["complete"], "raw word withheld " + t)
# fried egg
r = M.macros("بيض مقلي بالقليل من الزيت 2"); check(not r["complete"] and r["items"][0]["unresolved"].startswith("size"), "unsized count not counted")
r = M.macros("بيض مقلي بالقليل من الزيت 2 كبيرة"); check(r["complete"] and abs(r["cal"] - 180.3) <= 1, "2 large = 92 g " + str(r["cal"]))
r = M.macros("بيضتين كبار مقلي"); check(r["complete"] and r["items"][0]["grams"] == 92.0, "بيضتين كبار")
r = M.macros("بيض مقلي 100جم"); check(r["complete"] and r["cal"] == 196 and r["items"][0]["exact_identity"], "fried egg 100 g exact")
r = M.macros("بيض مقلي بالقليل من الزيت 2 كبيرة"); check(r["complete"] and not r["items"][0]["exact_identity"], "fried egg with oil words counted, not exact")
import portion_scale as PS
check(PS.meal_items("بيض مقلي 100جم")[0]["cal"] == 196 and PS.meal_items("بيض مقلي 2")[0]["cal"] is None, "chip agrees with total")
r = M.macros("بيض مقلي مع طماطم 100جم"); check(not r["complete"], "fried egg dish withheld")
r = M.macros("بيض بالخضار 2"); check(not r["complete"], "egg with veg withheld")
r = M.macros("بيض مسلوق 2"); check(r["complete"], "boiled egg unchanged")
# picker: cooked-weight raw rows gone, produce/as-sold untouched
cat = S._catalog(); names = [x["text"] for x in cat]
check(not any(x["weigh"] == "raw" and ("سمك" in x["text"] or "دجاج" in x["text"] or "أرز" in x["text"] or "جمبري" in x["text"] or "عدس" in x["text"] or "حمص" in x["text"]) for x in cat), "no raw cooked-food rows offered")
check(not any("نيّء" in n and "بيض" in n for n in names) and any("بيض مقلي" in n for n in names) and any("بيض مسلوق" in n for n in names), "raw eggs not offered, cooked eggs offered")
check(any("تفاح" in n for n in names) and any("طماطم" in n for n in names), "produce still offered")
check(any("بوري مطبوخ" in n for n in names) and any("أرز أبيض" in n and "مطبوخ" in n for n in names), "cooked rows offered")
# engine still computes an old stored raw-labelled text (history untouched)
r = M.macros("100جم سمك بوري نيّء (USDA 175123)"); check(r["complete"], "old raw text still computes")
# warning text
import app
from routes_plans import _calc_warning
with app.app.test_request_context("/"):
    w = _calc_warning("بيض مقلي 2"); check("حجم البيضة" in w, "egg warning " + w)
    w = _calc_warning("150جم صدر دجاج مشوي"); check(w == "", "no warning chicken " + w)

# ── accounting over every generator meal (pools + extra meals): what the guards withhold and what they count, pinned ──
import re as _re
import meal_database as _md
_texts = set()
def _walk(o):
    if isinstance(o, dict):
        if isinstance(o.get("meal"), str): _texts.add(o["meal"])
        for v in o.values(): _walk(v)
    elif isinstance(o, (list, tuple)):
        for v in o: _walk(v)
for _p in ("WEIGHT_LOSS", "MUSCLE_GAIN", "BULKING", "MAINTENANCE"): _walk(getattr(_md, _p))
check(len(_texts) > 900, "generator pool incl. extra meals is loaded: %d" % len(_texts))
_items = [i for t in sorted(_texts) for i in M.macros(t)["items"]]
_counted = lambda i: i.get("cal") is not None and not i.get("unresolved")
# 1) the only dish-title piece withheld by the parenthetical guard is the tuna salad (baseline priced 150 g tuna as the tuna-salad row)
_tit = sorted({i["text"] for i in _items if i.get("unresolved") == "composite" and i["text"].count("(") > i["text"].count(")") and i.get("food")})
check("🥗 سلطة تونة كبيرة (تونة 150جم" in _tit, "tuna-salad title piece withheld as composite")
# 2) a generic chicken-breast / tilapia / shrimp / mullet item is counted ONLY with its method word and its own name
_need = {"صدر دجاج": ("صدر", M._norm(_re.sub("", "", "مشوي|مشوى|مشويه|مشوية|بالفرن|محمص"))), "سمك بلطي": ("بلطي|بلطى", "مشوي|مشوى|مشويه|مشوية|بالفرن"),
         "جمبري": ("جمبري|روبيان", "مطبوخ|مسلوق|بالبخار"), "بوري": ("بوري", "مشوي|مشوى|مشويه|مشوية|بالفرن")}
for i in _items:
    n = i.get("food")
    if n in _need and _counted(i) and M.basis_of(next(f for _n, f in M._table() if f.get("n") == n)) == "unknown":
        nm, meth = _need[n]
        check(_re.search(M._norm(nm), M._norm(i["text"])) and _re.search(M._norm(meth), M._norm(i["text"])), "counted without name+method: " + i["text"])
# 3) the gained cooked cases are exactly the explicitly named ones
_gain = sorted({i["text"] for i in _items if i.get("food") in ("صدر دجاج", "سمك بلطي") and _counted(i)})
check(all(("صدر دجاج مشوي" in g) or ("سمك بلطي مشوي" in g) for g in _gain) and len(_gain) >= 5, "gained cases are explicit: %s" % _gain)
# 4) generic items without name/method stay withheld
for t in ("🍗 دجاج بالفرن 150جم", "🐟 سمك مشوي 120جم", "🍗 صدر دجاج 150جم"):
    check(not M.macros(t)["complete"], "generic withheld: " + t)
# 5) a dish whose title matches no food keeps pricing its first ingredient, and a title that is the same food keeps counting
check(_counted(M.macros("🌮 Chicken Burrito Bowl (ارز بني 100جم + دجاج 100جم)")["items"][0]), "title with no food: first ingredient still counted")

print("PASS %d FAIL %d" % (ok, fail)); sys.exit(1 if fail else 0)

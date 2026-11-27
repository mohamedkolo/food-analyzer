# Manual end-to-end driver (needs headless Chrome + websocket-client): real server, real login, real typing. Not part of the default suite (name has no test_ prefix).
import sys, json, time, re, subprocess, os
sys.path.insert(0, '/tmp/fa/tests'); sys.path.insert(0, '/tmp/fa')
from e2e_cdp import CDP
import test_representative_day as R
B = "http://127.0.0.1:5099"
ap = 5099
APPLE = (52.0, 0.26, 13.81, 0.17)
c = CDP(9333)
c.call("Page.enable"); c.call("Runtime.enable")
c.goto(B + "/login")
FORM = dict(action="generate", name="e2e", phone="01044443333", age="32", gender="ذكر", height="176", weight="95", tdee="2350", goal_cal="1750",
            goal_type="weight_loss", culture="مصري", diet_plan_type="standard", activity_mult="1.55", protein_per_kg="1.8", fat_pct_cal="30", zigzag_mode="off")
post = lambda path, d: "(()=>{const tk=document.querySelector('input[name=csrf_token]'); const p=new URLSearchParams(%s); if(tk) p.set('csrf_token',tk.value); return fetch(%s,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:p}).then(r=>r.status)})()" % (json.dumps(d), json.dumps(path))
print("login", c.js(post("/login", {"action": "login", "email": "admin@nutrax.com", "password": "pw123456"})))
print("generate", c.js(post("/generate", FORM)))
c.goto(B + "/preview")
slots = c.js("[...document.querySelectorAll('.meal-text.editable')].filter(e=>e.dataset.day==='0').map(e=>e.dataset.type)")
print("day0 slots", slots)
# lunch, dinner and every snack are written through the existing route; BREAKFAST is typed in the real editor
for s in slots:
    if s == "breakfast": continue
    t = R.TEXT.get(s, "100 جم تفاح")
    print("set", s, c.js(post("/edit_meal", {"day_idx": "0", "meal_type": s, "new_text": t})))
c.goto(B + "/preview")
snacks = [s for s in slots if s.startswith("snack")]

def open_editor(meal):
    c.js("document.querySelector('.meal-text.editable[data-day=\"0\"][data-type=\"%s\"]').click()" % meal)
    time.sleep(0.2)
def rect(expr):
    return c.js("(()=>{const e=%s; if(!e) return null; e.scrollIntoView({block:'center'}); const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}})()" % expr)

results = {}
def run(width, mobile, tag, pick_by):
    c.viewport(width, 900, mobile)
    c.goto(B + "/preview", 1.0)
    # restore breakfast to a known earlier state with an item the doctor already typed
    c.js(post("/edit_meal", {"day_idx": "0", "meal_type": "breakfast", "new_text": "100 جم موز + 200 جم حليب كامل الدسم"}))
    c.goto(B + "/preview", 1.0)
    open_editor("breakfast")
    c.js("(()=>{const ta=document.querySelector('.meal-edit-textarea'); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);})()")
    c.call("Input.insertText", text=" + 100 جم بيض")      # typed text: fires real input events, fetch goes to the live server
    time.sleep(0.9)
    items = c.js("[...document.querySelectorAll('.fs-item .fs-name')].map(e=>e.textContent)")
    print(tag, "offered:", items)
    meta = c.js("[...document.querySelectorAll('.fs-item')].map(e=>e.innerText)")
    r = rect("document.querySelector('.meal-edit-textarea')")
    c.js("window.scrollBy(0,-80)")
    c.shot("/downloads/f11_%s_list.png" % tag)
    if pick_by == "mouse":
        rr = c.js("(()=>{const r=document.querySelector('.fs-item').getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        c.click(rr["x"], rr["y"])
    else:
        c.key("ArrowDown", "ArrowDown", 40); c.key("Enter", "Enter", 13, "\r")
    time.sleep(0.3)
    val = c.js("document.querySelector('.meal-edit-textarea')?.value")
    print(tag, "after choose:", val)
    results[tag] = val
    c.js("document.querySelector('.meal-edit-textarea').blur()")     # real blur = the editor's normal save
    time.sleep(1.0)
    c.goto(B + "/preview", 1.0)
    txt = c.js("document.querySelector('.meal-text.editable[data-day=\"0\"][data-type=\"breakfast\"]').textContent.trim()")
    mac = c.js("""(()=>{const h=document.querySelector('[data-basis="items"]'); const m=document.querySelector('[data-macros-line="1"]'); return {kcal:h?h.innerText:null, macros:m?m.innerText:null}})()""")
    print(tag, "reloaded breakfast:", txt, "|", mac)
    results[tag + "_reload"] = (txt, mac)

run(420, True, "mob_ar", "key")
run(1280, False, "desk_ar", "mouse")
# English UI
c.goto(B + "/lang/en", 1.0)
run(420, True, "mob_en", "key")
c.goto(B + "/lang/ar", 1.0)
# add-item box on the first snack
c.viewport(420, 900, True)
c.goto(B + "/preview", 1.0)
sn = snacks[0]
c.js("document.querySelector('.add-toggle[data-day=\"0\"][data-type=\"%s\"]').click()" % sn)
c.js("document.querySelector('form.add-item[data-day=\"0\"][data-type=\"%s\"] input').focus()" % sn)
c.call("Input.insertText", text="200 جم ارز"); time.sleep(0.9)
print("addbox offered:", c.js("[...document.querySelectorAll('.fs-item .fs-name')].map(e=>e.textContent)"))
rect("document.querySelector('form.add-item[data-day=\"0\"][data-type=\"%s\"] input')" % sn); c.js("window.scrollBy(0,-80)")
c.shot("/downloads/f11_mob_addbox.png")
c.key("ArrowDown", "ArrowDown", 40); c.key("Enter", "Enter", 13, "\r"); time.sleep(0.2)
v = c.js("document.querySelector('form.add-item[data-day=\"0\"][data-type=\"%s\"] input')?.value" % sn)
print("addbox value after choosing:", v)
c.key("Enter", "Enter", 13, "\r"); time.sleep(1.0)        # second Enter: nothing active, so it submits the form
c.goto(B + "/preview", 1.0)
print("snack after add:", c.js("document.querySelector('.meal-text.editable[data-day=\"0\"][data-type=\"%s\"]').textContent.trim()" % sn))
json.dump(results, open("/tmp/e2e_ui_results.json", "w"), ensure_ascii=False)
# independent USDA arithmetic for the whole day (breakfast+lunch+dinner from R.DAY, one snack of 100 g apple)
exp = [0.0]*4
for slot, ents in R.DAY.items():
    for _t, _f, g, v in ents:
        for j in range(4): exp[j] += v[j]*g/100.0
for j in range(4): exp[j] += APPLE[j]
print("INDEPENDENT USDA day:", [round(x,1) for x in exp])

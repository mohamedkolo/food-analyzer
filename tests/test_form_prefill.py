# -*- coding: utf-8 -*-
"""الملء التلقائي وشكل الخطوات.

الاتنين دول غيروا فورم توليد الخطة، وفيهم حاجات لو اتكسرت مش هتبان بسهولة:

  * الرقم لوحده لازم يلاقي العميل. client_key مبني على الاسم (اسم|آخر٦أرقام)
    فالبحث بيه مستحيل من غير اسم -- والدكتور بيكتب الرقم الأول. والمقارنة
    لازم تبقى على الأرقام المجرّدة: الموبايل متخزّن "+20 100 429 4521"،
    والمسافة واقعة جوه آخر ٦ أرقام، فـLIKE '%294521' مابيلاقيهاش. ده باگ
    وقعنا فيه فعلاً واتصلح.

  * الاسم لازم يتملّى مع الباقي. الحقل required، فلو فضل فاضي المتصفح بيرفض
    الإرسال من غير رسالة مفهومة -- وده اللي حصل أول تجربة.

  * الخطوة المخفية display:none، وحقولها لسه جوه الـ<form>. لو حد غيّرها
    لإزالة من الـDOM، بيانات الخطوات اللي مادخلتهاش هتضيع في صمت.

Run with:  python3 tests/test_form_prefill.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORM = os.path.join(HERE, "templates", "generate.html")


def _seed_clients(uid=77):
    """‏عملاء للاختبار في قاعدة خاصة. كل اختبار بينادي دي بنفسه -- الاعتماد
    على إن اختبار تاني زرع الداتا بيكسر مع أي إعادة ترتيب."""
    os.environ.setdefault("SECRET_KEY", "test-only")
    os.environ["NUTRAX_DB"] = "/tmp/nutrax_search_test.db"
    import core
    core.db_run("DELETE FROM plan_visits WHERE user_id=?", (uid,))
    people = [
        ("mhmd ahmd|294521", "محمد أحمد", "01004294521", 3),
        ("mhmd sayd|551122", "محمد سيد", "01155551122", 1),
        ("fatm aly|443322", "فاطمة علي", "01099443322", 2),
    ]
    for key, name, phone, visit in people:
        core.db_run(
            """INSERT INTO plan_visits (user_id, client_key, client_name, phone,
                 visit_no, age, height, weight, conditions)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (uid, key, name, phone, visit, 40, 175.0, 90.0, "[]"))
    return core


def _form():
    with open(FORM, encoding="utf-8") as fh:
        return fh.read()


def test_the_phone_finds_a_client_in_every_way_it_gets_typed():
    """‏الموبايل بيتكتب بأي شكل، والمقارنة على آخر ٦ أرقام مجرّدة."""
    os.environ.setdefault("SECRET_KEY", "test-only")
    os.environ["NUTRAX_DB"] = "/tmp/nutrax_prefill_test.db"
    if os.path.exists("/tmp/nutrax_prefill_test.db"):
        os.remove("/tmp/nutrax_prefill_test.db")
    import core

    core.db_run(
        """INSERT INTO plan_visits (user_id, client_key, client_name, phone,
             visit_no, age, gender, height, conditions)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (99, "test|294521", "عميل اختبار", "+20 100 429 4521", 2,
         41, "ذكر", 174.0, json.dumps(["سكري النوع الثاني"], ensure_ascii=False)))

    # ‏كل دي نفس الرقم مكتوب بشكل مختلف
    for typed in ("01004294521", "+20 100 429 4521", "0100 429 4521",
                  "429-4521", "4294521", "٤٢٩٤٥٢١".translate(
                      str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))):
        rows = core.visits_by_phone(99, typed, limit=5)
        assert rows, "‏الرقم %r مالقاش العميل" % typed

    # ‏ورقم تاني مايلاقيهوش
    assert not core.visits_by_phone(99, "01111111111", limit=5), \
        "‏رقم مختلف لاقى العميل"
    # ‏وأقل من ٦ أرقام مش تعريف كافي
    assert not core.visits_by_phone(99, "4521", limit=5), \
        "‏٤ أرقام اعتبرها تعريف كافي"
    # ‏ودكتور تاني مايشوفش عملاء غيره
    assert not core.visits_by_phone(98, "01004294521", limit=5), \
        "‏دكتور تاني شاف عميل مش بتاعه"


def test_the_lookup_endpoint_accepts_a_phone_with_no_name():
    """‏الدكتور بيكتب الرقم قبل الاسم، فالـendpoint لازم يقبله لوحده."""
    src = open(os.path.join(HERE, "routes_plans.py"), encoding="utf-8").read()
    block = src[src.index("def followup_lookup"):src.index("def followups")]
    assert "visits_by_phone" in block, "‏البحث بالرقم مش مستخدم في الـendpoint"
    # ‏البحث بالرقم لازم يجي قبل شرط طول الاسم، وإلا بيرجع found:False قبله
    i_phone = block.index("visits_by_phone")
    i_name_guard = block.index("fold_name(name)")
    assert i_phone < i_name_guard, (
        "‏شرط الاسم بيسبق البحث بالرقم، فالرقم لوحده هيرجع مفيش نتيجة")
    assert "matched_by" in block, "‏الواجهة مش بتعرف لقاه بالرقم ولا بالاسم"


def test_the_autofill_fills_the_name_because_the_field_is_required():
    """‏لو الاسم فضل فاضي، المتصفح بيرفض الإرسال والدكتور مش فاهم ليه."""
    html = _form()
    assert 'name="name" id="nameField" required' in html, \
        "‏شكل حقل الاسم اتغير -- الاختبار ده محتاج تحديث"
    assert "setVal(nameField, d.name" in html, \
        "‏الملء التلقائي مش بيملّي الاسم، والحقل required"


def test_the_autofill_never_overwrites_what_was_typed():
    """‏الرقم بيتكتب وسط الكتابة، فالملء مايصحش يمسح شغل الدكتور."""
    html = _form()
    fn = html[html.index("function fuFillEmpty"):html.index("const btn=")]
    # ‏الحماية بقت مشروطة بـforce: الكتابة بالإيد مش بتتمسح إلا لو الدكتور
    # دوس على عميل من القايمة بنفسه (اختيار صريح "ده هو").
    assert "if(!force && String(el.value||'').trim()!=='') return;" in fn, \
        "‏حماية 'المكتوب مايتغيرش' مش موجودة"
    assert "function fuFillEmpty(force)" in html, \
        "‏الملء مابقاش ليه وضعين -- الدوس على عميل لازم يملي كل حاجة"
    # ‏الوزن مالوش يتملّى في الحالتين: ده اللي جاي يتقاس في الزيارة دي
    assert "setVal(w," not in fn and "setVal(wField" not in fn, \
        "‏الوزن بيتملّى من زيارة قديمة -- ده اللي المفروض يتقاس"


def test_saying_different_person_clears_only_what_was_autofilled():
    html = _form()
    skip = html[html.index("document.getElementById('fuSkip').onclick"):]
    skip = skip[:skip.index("fuLastKey='__skipped__")]
    assert "fuAutoFilled" in skip and "fuAutoConds" in skip, \
        "‏'ده شخص تاني' مش بيشيل اللي اتملى تلقائي"


def test_the_conditions_come_back_and_stay_until_changed():
    """‏اللي إنت طلبته: الحالات بتفضل متسجلة لحد ما تغيّرها.

    الحالات بتتخزّن مع كل زيارة (conditions في plan_visits)، والملء بيجيبها
    من آخر زيارة. فلو الدكتور غيّرها، الزيارة الجديدة بتسجّل الجديد، والمرة
    الجاية الجديد هو اللي بيرجع.
    """
    core_src = open(os.path.join(HERE, "core.py"), encoding="utf-8").read()
    ins = core_src[core_src.index("INSERT INTO plan_visits"):]
    ins = ins[:ins.index(")\"\"\"") + 4] if ")\"\"\"" in ins[:900] else ins[:900]
    assert "conditions" in ins, "‏الحالات مش بتتسجل مع الزيارة"

    html = _form()
    fn = html[html.index("function fuFillEmpty"):html.index("const btn=")]
    assert 'name="symptoms"' in fn, "‏الملء مش بيعلّم الحالات"
    assert "cb.checked" in fn, "‏الملء مش بيعلّم الحالات"


def test_the_form_is_four_steps_and_hidden_steps_still_submit():
    """‏الخطوة المخفية display:none -- حقولها لسه بتتبعت.

    لو حد شالها من الـDOM بدل ما يخفيها، بيانات الخطوات اللي الدكتور
    مادخلهاش هتضيع من غير أي رسالة.
    """
    html = _form()
    assert html.count('class="wz-step"') == 4, (
        "‏عدد الخطوات مش 4: %d" % html.count('class="wz-step"'))
    assert html.count('class="wz-tab"') == 4, "‏شريط الخطوات مش 4"
    assert ".wz-step { display:none }" in html, "‏الخطوة بتتخفي بطريقة تانية"
    assert "remove()" not in html.split(".wz-step")[1][:2000], \
        "‏في كود بيشيل الخطوة من الصفحة -- البيانات هتضيع"
    # ‏الأقسام العشرة كلها لسه موجودة
    assert html.count('class="wz-card"') == 10, (
        "‏قسم ضاع في التقسيم: %d من 10" % html.count('class="wz-card"'))


def test_every_step_lives_inside_the_form():
    """‏خطوة برّه الـ<form> = بياناتها مابتتبعتش."""
    html = _form()
    form_start = html.index('<form method="POST" action="/generate">')
    form_end = html.index("</form>", form_start)
    inside = html[form_start:form_end]
    assert inside.count('class="wz-step"') == 4, \
        "‏في خطوة برّه الفورم -- بياناتها هتضيع"


def test_a_required_field_in_a_hidden_step_is_surfaced():
    """‏المتصفح بيرفض الإرسال في صمت لو الحقل المطلوب في خطوة مخفية."""
    html = _form()
    assert "querySelector(':invalid')" in html, \
        "‏مفيش معالجة للحقل المطلوب المخفي"
    assert "reportValidity" in html, "‏الدكتور مش هيعرف الحقل الناقص فين"


def test_the_conditions_list_is_searchable():
    """‏٤٧ حالة = ٢٩٠٠ بكسل على الموبايل.

    تقسيمها لخطوات أكتر مش حل -- الدكتور بيدوّر على حالة بالاسم مش بيقرا
    القايمة. قِسناها: البحث بكلمة "كبد" بينزّل الخطوة من 2936 لـ888 بكسل.
    """
    html = _form()
    assert 'id="condSearch"' in html, "‏مفيش خانة بحث في الحالات"
    assert 'id="condGrid"' in html, "‏الشبكة مالهاش id، فالبحث مش هيلاقيها"
    assert 'id="condNone"' in html, "‏مفيش رسالة لما البحث مايلاقيش"
    assert 'id="condCount"' in html, "‏مفيش عدّاد للمختار"
    js = html[html.index("// ═══ بحث الحالات المرضية"):]
    js = js[:js.index("// ═══ تنقّل الخطوات")]
    # ‏المختار لازم يفضل ظاهر تحت الفلتر، وإلا الدكتور بينساه
    assert "cb.checked" in js, "‏المختار مش مستثنى من الفلتر -- هيختفي ويتنسى"
    assert "type=\"search\"" in html, "‏نوع الخانة مش search"


def test_the_search_box_has_a_name():
    """‏خانة بحث من غير اسم = "مربع نص" لقارئ الشاشة."""
    html = _form()
    # ‏الوسم كله: من <input اللي قبل الـid لحد قفلة الوسم. القطع من غير كده
    # بياخد نص المارك-أب اللي فوقه ويفوّت الـaria-label اللي بعد الـid.
    i = html.index('id="condSearch"')
    tag = html[html.rindex("<input", 0, i):html.index(">", i) + 1]
    assert "aria-label" in tag, "‏خانة البحث مالهاش اسم: %s" % tag[:90]


def test_running_the_tests_does_not_wipe_the_local_database():
    """‏كانوا بيمسحوا /tmp/nutrax.db -- وهي قاعدة التشغيل المحلي نفسها.

    فتشغيل الاختبارات كان بيضيّع حساب الأدمن واللي إنت مسجّله للتجربة، ولازم
    تعيد تشغيل السيرفر بـADMIN_PASSWORD عشان يرجع.
    """
    for name in ("run_all.py", "test_translation.py", "test_access_control.py"):
        src = open(os.path.join(HERE, "tests", name), encoding="utf-8").read()
        code = "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))
        assert 'os.remove("/tmp/nutrax.db")' not in code, (
            "‏%s لسه بيمسح قاعدة التشغيل المحلي" % name)
        assert '"/tmp/nutrax.db"' not in code, (
            "‏%s لسه بيشاور على قاعدة التشغيل المحلي" % name)


def test_health_reports_the_running_commit():
    """‏مفيش طريقة تعرف بيها إن Render نشر الجديد غير إنك تشوف رقم الكوميت."""
    os.environ.setdefault("SECRET_KEY", "test-only")
    import core
    sha = core.running_commit()
    assert sha and sha != "unknown", "‏مش عارف يقرا الكوميت الشغال"
    assert len(sha) == 7, "‏الطول المتوقع 7 حروف، طلع %r" % sha
    src = open(os.path.join(HERE, "core.py"), encoding="utf-8").read()
    block = src[src.index('@app.route("/health")'):]
    block = block[:block.index("@app.after_request")]
    assert "running_commit()" in block, "‏/health مش بيرجّع الكوميت"
    assert "RENDER_GIT_COMMIT" in src, "‏مش بياخد الكوميت من بيئة Render"


def test_no_radio_is_hidden_with_display_none():
    """‏كروت الاختيار كانت راديو بـdisplay:none -- ومعناه إن مينفعش تختار
    الهدف ولا المطبخ ولا النظام **بالكيبورد خالص**، لأن العنصر المخفي كده
    مش بياخد focus. بقى مخفي بصرياً بس لسه قابل للتركيز.
    """
    html = _form()
    # ‏أي input جواه display:none = مستخدم الكيبورد مش قادر يوصله
    for m in re.finditer(r"<input[^>]*>", html):
        tag = m.group(0)
        if 'type="radio"' in tag or 'type="checkbox"' in tag:
            assert "display:none" not in tag.replace(" ", ""), (
                "‏راديو/checkbox مخفي بـdisplay:none: %s" % " ".join(tag.split())[:80])


def test_the_three_option_groups_share_one_card_style():
    """‏كانوا تلات أشكال: الهدف إيموجي 32px ونص في النص، والمطبخ 28px،
    ونظام الأكل نص بس. بقوا كومبوننت واحد -- ده معنى "منسقة"."""
    html = _form()
    body = html[html.index('<form method="POST" action="/generate">'):]
    body = body[:body.index("</form>")]
    for field in ('name="goal_type"', 'name="culture"', 'name="diet_plan_type"'):
        i = body.index(field)
        label_start = body.rindex("<label", 0, i)
        label_tag = body[label_start:body.index(">", label_start) + 1]
        assert 'class="nx-opt"' in label_tag, (
            "‏%s مش مستخدم كارت الاختيار المشترك: %s" % (field, label_tag[:70]))
    # ‏الأشكال القديمة لازم تكون اختفت
    assert "goal-card" not in html, "‏كارت الهدف القديم لسه موجود"
    assert "culture-card" not in html, "‏كارت المطبخ القديم لسه موجود"


def test_the_selected_card_is_not_signalled_by_colour_alone():
    """‏اللون لوحده مايكفيش لحد مش بيفرّق الألوان -- فيه حدود وعلامة صح كمان."""
    html = _form()
    css = html[html.index(".nx-opt {"):html.index(".nx-opt-in:focus-visible")]
    assert "border-color:var(--green)" in css.replace(" ", "")         or "border-color: var(--green)" in css, "‏الحدود مش بتتغير عند الاختيار"
    assert 'content:"✓"' in css.replace(" ", "") or 'content: "✓"' in css,         "‏مفيش علامة صح على الكارت المختار"
    assert "focus-visible" in html, "‏مفيش حلقة تركيز للكيبورد"


def test_the_eating_system_icons_do_not_depend_on_a_cdn():
    """‏Font Awesome بيتحمّل من CDN. لو فشل (شبكة، مانع إعلانات، الـCDN واقع)
    الـ11 كارت بيبانوا مربعات فاضية -- شفتها بعيني في التجربة. فإيموجي."""
    html = _form()
    block = html[html.index("{% set sys_icons"):]
    block = block[:block.index("{% endfor %}")]
    assert "fa-" not in block, "‏أيقونات النظام رجعت تعتمد على Font Awesome"
    assert "sys_icons.get(key," in block, "‏مفيش رمز افتراضي لمفتاح جديد"


def test_the_css_tokens_the_cards_use_are_actually_defined():
    """‏--blue-dark و--gray-dark كانوا مستخدمين في 10 أماكن وهما مش معرّفين،
    فالمتصفح كان بيتجاهل السطر كله: أرقام صفحات المتابعة كانت بلون النص
    العادي بدل الكحلي."""
    base = open(os.path.join(HERE, "templates", "base.html"), encoding="utf-8").read()
    root = base[base.index(":root{"):base.index("}", base.index(":root{"))]
    defined = set(re.findall(r"(--[a-z0-9-]+):", root))
    used = set()
    for name in ("generate.html", "base.html", "followups.html",
                 "followup_detail.html", "preview.html"):
        html = open(os.path.join(HERE, "templates", name), encoding="utf-8").read()
        used |= set(re.findall(r"var\((--[a-z0-9-]+)\)", html))
    missing = sorted(used - defined)
    assert not missing, "‏توكنز مستخدمة ومش معرّفة: %s" % missing


def test_the_search_finds_a_client_from_two_characters():
    """‏قايمة اقتراحات زي جوجل: حرفين من الاسم أو رقمين من الموبايل.

    الفرق عن visits_by_phone: دي عايزة ٦ أرقام كاملة وبترجّع عميل واحد.
    دي بترجّع قايمة يدوس منها، فالدكتور مايستناش لحد ما يكتب الرقم كله.
    """
    core = _seed_clients()

    # ‏حرفين من الاسم
    got = core.search_clients(77, "مح", limit=8)
    assert len(got) == 2, "‏'مح' المفروض تلاقي اتنين، لاقت %d" % len(got)
    # ‏والهمزة والألف موحّدين: "احمد" تلاقي "أحمد"
    assert core.search_clients(77, "احمد", limit=8), "‏التوحيد مش شغال"
    # ‏جزء من الرقم
    assert len(core.search_clients(77, "0115", limit=8)) == 1, "‏جزء الرقم مالقاش"
    assert len(core.search_clients(77, "9944", limit=8)) == 1, "‏وسط الرقم مالقاش"
    # ‏حرف واحد مش كفاية -- بيرجّع كل حاجة ومالوش لازمة
    assert core.search_clients(77, "م", limit=8) == [], "‏حرف واحد رجّع نتايج"
    # ‏دكتور تاني مايشوفش عملاء غيره
    assert core.search_clients(76, "مح", limit=8) == [], "‏دكتور تاني شاف عملاء غيره"
    # ‏العميل الواحد مرة واحدة، مش زيارة لكل صف
    core.db_run(
        """INSERT INTO plan_visits (user_id, client_key, client_name, phone,
             visit_no, conditions) VALUES (?,?,?,?,?,?)""",
        (77, "mhmd ahmd|294521", "محمد أحمد", "01004294521", 4, "[]"))
    again = core.search_clients(77, "محمد أحمد", limit=8)
    assert len(again) == 1, "‏العميل اتكرر بعدد زياراته: %d" % len(again)


def test_each_suggestion_carries_what_tells_two_people_apart():
    """‏اسمين متشابهين: اللي بيفرّق هو الرقم وآخر وزن وعدد الزيارات."""
    core = _seed_clients()
    got = core.search_clients(77, "مح", limit=8)
    assert got, "‏البذرة مازرعتش عملاء"
    for c in got:
        for field in ("key", "name", "phone", "visits"):
            assert field in c, "‏الاقتراح ناقصه %s" % field
        assert c["key"], "‏مفيش مفتاح -- الدوس مش هيعرف يجيب مين"


def test_picking_a_suggestion_looks_the_client_up_by_key():
    """‏الدوس بيجيب العميل بمفتاحه، مش بتخمين بالاسم.

    من غير كده، اتنين بنفس الاسم ممكن ندوس على واحد ونجيب بيانات التاني.
    """
    src = open(os.path.join(HERE, "routes_plans.py"), encoding="utf-8").read()
    block = src[src.index("def followup_lookup"):src.index("def followups")]
    assert 'request.args.get("key")' in block, "‏الـlookup مش بياخد مفتاح"
    i_key = block.index("if key_arg:")
    i_phone = block.index("visits_by_phone(session")
    assert i_key < i_phone, "‏المفتاح المفروض يسبق التخمين بالرقم"
    assert '"pick"' in block, "‏الواجهة مش هتعرف إن الدكتور اختار بنفسه"
    assert "/api/clients/search" in src, "‏مفيش endpoint للبحث"


def test_the_suggestion_list_is_reachable_by_keyboard_and_announced():
    html = _form()
    js = html[html.index("// ═══ بحث العملاء"):]
    js = js[:js.index("// ═══ بحث الحالات المرضية")]
    for key in ("ArrowDown", "ArrowUp", "Enter", "Escape"):
        assert key in js, "‏القايمة مش بتستجيب لـ%s" % key
    assert 'role="combobox"' in html, "‏الخانة مش معلَنة كـcombobox"
    assert 'role="listbox"' in html, "‏القايمة مش معلَنة كـlistbox"
    assert 'role="option"' in js, "‏عناصر القايمة مش معلَنة"
    assert "aria-activedescendant" in js, "‏قارئ الشاشة مش هيعرف المحدّد فين"
    assert 'aria-live="polite"' in html, "‏عدد النتايج مش بيتقال لقارئ الشاشة"


def test_the_suggestion_escapes_names_before_putting_them_in_html():
    """‏الاسم بيجي من الداتابيز وبيتحط كـHTML. اسم فيه < أو " يقدر يكسر
    الصفحة أو أسوأ، فلازم يتـescape قبل ما يتعرض."""
    html = _form()
    js = html[html.index("// ═══ بحث العملاء"):]
    js = js[:js.index("// ═══ بحث الحالات المرضية")]
    assert "function esc(" in js, "‏مفيش escape لأسماء العملاء"
    assert "&amp;" in js and "&lt;" in js, "‏الـescape ناقص"
    assert "esc(c.name" in js or "mark(c.name" in js, "‏الاسم بيتعرض من غير معالجة"
    # ‏mark بتستخدم esc جواها
    mark_fn = js[js.index("function mark("):js.index("function render(")]
    assert "esc(" in mark_fn, "‏التظليل بيتخطى الـescape"


def test_a_stale_search_reply_cannot_overwrite_a_newer_one():
    """‏الدكتور بيكتب بسرعة، فردود البحث بتوصل مش بالترتيب. لو القديم كتب
    فوق الجديد، بيشوف نتايج حرف قديم."""
    html = _form()
    js = html[html.index("// ═══ بحث العملاء"):]
    js = js[:js.index("// ═══ بحث الحالات المرضية")]
    assert "reqSeq" in js, "‏مفيش ترقيم للطلبات"
    assert "mine !== reqSeq" in js, "‏الرد القديم مش بيتجاهل"


def test_two_clients_with_the_same_name_stay_apart():
    """‏ده السبب إن الاقتراح بيعرض الرقم وآخر وزن وعدد الزيارات.

    اسمين متطابقين بالحرف: لو الملء بيخمّن بالاسم، الدوس على واحد بيجيب
    بيانات التاني. المفتاح هو اللي بيمنع ده -- جربتها في المتصفح.
    """
    core = _seed_clients()
    for key, phone, visit in (("aly hsn|111222", "01011111222", 1),
                              ("aly hsn|333444", "01233334444", 4)):
        core.db_run(
            """INSERT INTO plan_visits (user_id, client_key, client_name, phone,
                 visit_no, age, height, weight, conditions)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (77, key, "علي حسن", phone, visit, 30, 170.0, 85.0, "[]"))
    got = core.search_clients(77, "علي حسن", limit=8)
    assert len(got) == 2, "‏الاتنين اندمجوا في واحد: %d" % len(got)
    keys = {c["key"] for c in got}
    assert len(keys) == 2, "‏نفس المفتاح للاتنين -- مش هينفع نفرّقهم"
    phones = {c["phone"] for c in got}
    assert len(phones) == 2, "‏الأرقام مش ظاهرة في الاقتراح، فمفيش حاجة تفرّق"


def test_the_dropdown_is_wide_enough_to_read_on_a_phone():
    """‏خانة الاسم في عمود من اتنين، فعلى الموبايل عرضها 170 بكسل والقايمة
    بتاخد نفس العرض -- قِستها وماكانش ينفع تقرا اسم ورقم فيها. فعلى الشاشة
    الضيقة الاسم بياخد الصف كله."""
    html = _form()
    assert ".grid-2 > .form-group:has(.ac-wrap)" in html,         "‏خانة الاسم مش بتاخد الصف كله على الموبايل، فالقايمة هتبقى ضيقة"


def test_the_form_does_not_open_with_the_last_client_still_in_it():
    """‏أخطر باگ في الفورم: كان بيتملى من session["pdf_data"] دايماً.

    دي بيانات آخر خطة اتولّدت وبتفضل في الجلسة. النتيجة إن فتح "توليد جدول"
    من القايمة كان بيجيب اسم ووزن وحالات آخر عميل. ولو الدكتور غيّر الاسم
    بس، الحالات تفضل من القديم في خطوة ماشافهاش -- فالخطة تطلع على شخص
    وبحالات شخص تاني، من غير أي رسالة غلط.
    """
    src = open(os.path.join(HERE, "routes_plans.py"), encoding="utf-8").read()
    block = src[src.index("def generate"):src.index("def commit_plan")]
    assert 'request.args.get("edit")' in block,         "‏الفورم مش بيفرّق بين تعديل وعميل جديد"
    assert "if editing else {}" in block,         "‏الفورم لسه بيتملى من آخر خطة في كل الحالات"
    # ‏وزرار التعديل لازم يقول إنه تعديل، وإلا الرجوع من المعاينة يفضّي الفورم
    prev_html = open(os.path.join(HERE, "templates", "preview.html"),
                     encoding="utf-8").read()
    assert 'href="/generate?edit=1"' in prev_html,         "‏زرار التعديل مش بيطلب الملء، فالرجوع من المعاينة هيفضّي الفورم"


def test_picking_a_client_overwrites_instead_of_filling_gaps():
    """‏الدوس على عميل اختيار صريح: "ده هو". فالمفروض الفورم يبقى بياناته
    كلها، مش نصها -- عكس كتابة الرقم اللي بتملي الفاضي بس."""
    html = _form()
    fn = html[html.index("function fuFillEmpty"):html.index("const btn=")]
    assert "function fuFillEmpty(force)" in html, "‏مفيش وضع للكتابة فوق"
    assert "if(!force && String(el.value" in fn,         "‏الكتابة فوق مش مشروطة بالدوس -- كده بيمسح شغل الدكتور"
    assert "d.matched_by === 'pick'" in html,         "‏الملء مش عارف يفرّق بين الدوس وكتابة الرقم"
    # ‏والأهداف والنظام لازم يتملوا كمان -- ده اللي طلبه بالنص
    for field in ("goal_type", "diet_plan_type", "L.tdee", "L.goal_cal", "L.bmi"):
        assert field in fn, "‏%s مش بيتملى عند الدوس" % field
    # ‏الوزن برضه مايتملاش: ده اللي جاي يتقاس
    assert "setVal(w," not in fn, "‏الوزن بيتملى من زيارة قديمة"


def test_there_is_only_one_activity_field():
    """‏كانت خانتين بيسألوا نفس السؤال بمقياسين: معامل الـTDEE، ومستوى
    البروتين. الدكتور كان لازم يجاوب مرتين، ولو جاوب متناقض (مكتبي +
    رياضي) الأرقام تطلع متضاربة."""
    html = _form()
    acts = re.findall(r'<select[^>]*name="(activity[^"]*)"', html)
    assert acts == ["activity_mult"], "‏خانات النشاط: %s" % acts
    assert 'name="activity_level"' not in html, "‏خانة مستوى النشاط لسه موجودة"


def test_the_protein_level_is_derived_on_the_server_too():
    """‏لو الاستنتاج في الجافاسكريبت بس، متصفح مقفول فيه الـJS (أو غلطة في
    السكريبت) كان هيبعت البروتين الافتراضي والدكتور مش هيعرف."""
    os.environ.setdefault("SECRET_KEY", "test-only")
    import routes_plans as rp
    cases = {"1.2": "sedentary", "1.375": "light", "1.55": "regular",
             "1.725": "athlete", "1.9": "athlete"}
    for mult, level in cases.items():
        assert rp._activity_level(mult) == level,             "‏×%s المفروض %s وطلع %s" % (mult, level, rp._activity_level(mult))
    # ‏رقم غريب أو فاضي مايكسرش حاجة
    for bad in ("", None, "abc", "9.9"):
        assert rp._activity_level(bad) == "regular", "‏%r كسر الاستنتاج" % (bad,)
    # ‏والقالب لازم يستخدم نفس الخريطة عشان الرقم يبان فوراً
    html = _form()
    assert "MULT_P" in html, "‏القالب مش بيعرض البروتين من نفس الاختيار"
    for mult in cases:
        assert "'%s'" % mult in html, "‏×%s ناقص من خريطة القالب" % mult


def test_the_activity_label_matches_the_protein_it_produces():
    """‏الليبل بيعد بروتين معيّن -- والخانة لازم تدي نفس الرقم.

    دمجنا خانتين في واحدة عشان مايتناقضوش، فلو الليبل بيقول "بروتين 2.0"
    والخريطة بتحسب 1.6، الدكتور بيقرا رقم والخطة بتتحسب برقم تاني -- ومفيش
    حاجة في الشاشة تقول كده.
    """
    html = _form()
    mult_p = dict(re.findall(r"'([\d.]+)':([\d.]+)", html[html.index("const MULT_P="):]
                             .split("}", 1)[0]))
    assert mult_p, "‏خريطة MULT_P مش موجودة"
    opts = re.findall(r'<option value="([\d.]+)"[^>]*>\{\{ \'([^\']*)\'', html)
    assert len(opts) == len(mult_p), (
        "‏عدد اختيارات النشاط (%d) مش قد الخريطة (%d)" % (len(opts), len(mult_p)))
    for value, label in opts:
        said = re.search(r"بروتين ([\d.]+)", label)
        assert said, "‏اختيار ×%s مش مكتوب فيه البروتين" % value
        assert float(said.group(1)) == float(mult_p[value]), (
            "‏×%s الليبل بيقول %s والخريطة بتحسب %s"
            % (value, said.group(1), mult_p[value]))


def test_picking_a_client_resyncs_the_protein_with_the_activity():
    """‏حط قيمة في select من الكود مابيرميش change، فالمستنتج منها
    بيفضل على القديم. حصل فعلاً: النشاط بقى ×1.725 والبروتين فضل 1.6."""
    html = _form()
    fn = html[html.index("function fuFillEmpty"):html.index("const btn=")]
    branch = fn[fn.index("if(actMult && L.activity"):]
    branch = branch[:branch.index("// ")] if "// " in branch[:400] else branch[:400]
    assert "setProteinFromAct()" in branch, (
        "‏الملء بيغيّر النشاط ومابيعيدش حساب البروتين")


def test_the_form_says_why_the_cycling_did_nothing():
    """‏لو الهدف اليومي عند الحد الآمن أو تحته، التدوير مستحيل رياضياً.

    مفيش مساحة ننزّل يوم عن الحد، والمجموع الأسبوعي لازم يفضل زي ما هو،
    فالسبع أيام بيطلعوا متساويين. الصندوق كان بيرسم السبع أعمدة المتساوية دي تحت
    جملة بتقول "سعرات أعلى أيام التمرين" -- ومايقولش ليه. فالدكتور يقعد يبدّل
    في الأنماط ومفيش حاجة بتتغير، ويفترض إن الخانة بايظة.

    والحد لازم يبقى نفسه في الصفحة وفي zigzag.py -- لو اختلفوا، المعاينة
    الحية بتوري حاجة والخطة بتطلع حاجة تانية.
    """
    import zigzag
    html = _form()

    assert 'id="zzWarn"' in html, "‏مفيش مكان للتحذير في صندوق التدوير"
    script = html[html.index("function renderZigzag"):]
    script = script[:script.index("if(zzMode)")]
    assert "noRoom" in script and "floor>=target" in script, (
        "‏المعاينة الحية مش بتكتشف إن مفيش مساحة للتدوير")
    assert "zzWarn.hidden" in script, "‏التحذير مش بيتظهر ولا بيتخفي"
    # ‏مع "بدون تدوير" الأيام المتساوية هي الصح، فمالوش تحذير
    assert "zzMode.value!=='off'" in script, (
        "‏التحذير بيطلع كمان مع 'بدون تدوير'، وده مش غلط أصلاً")

    # ‏نفس أرقام الحد الآمن في الاتنين
    for value in (zigzag.MIN_KCAL_FEMALE, zigzag.MIN_KCAL_MALE):
        assert str(value) in html, (
            "‏الحد الآمن %s موجود في zigzag.py ومش موجود في الصفحة" % value)

    # ‏والرسالة لازم تقول الرقمين: الهدف والحد -- "مفيش مساحة" لوحدها
    # مابتقولش للدكتور يرفع الهدف قد إيه
    msg = script[script.index("zzWarn.textContent"):]
    msg = msg[:msg.index(");")]
    # ‏وبالعربي والإنجليزي الاتنين، مش في نص واحد
    assert msg.count("Math.round(target)") >= 2 and msg.count("+floor+") >= 2, (
        "‏التحذير مش بيقول الهدف الحالي والحد الآمن بالأرقام في اللغتين")


def _js_code_only(script):
    """‏السكريبت بعد شيل النصوص والتعليقات، والطول محفوظ.

    بنسيب مكان كل حرف زي ما هو (بنبدّله بمسافة) عشان الفهارس تفضل مظبوطة،
    فالبحث عن "قبل التعريف" يفضل صح.
    """
    out = list(script)
    i, n = 0, len(script)
    while i < n:
        ch = script[i]
        if ch in "\"'`":
            quote, j = ch, i + 1
            # ‏في الـtemplate literal، اللي جوه ${...} كود حقيقي فبنسيبه
            keep = []
            while j < n:
                if script[j] == "\\":
                    j += 2
                    continue
                if quote == "`" and script.startswith("${", j):
                    depth, k = 1, j + 2
                    while k < n and depth:
                        if script[k] == "{":
                            depth += 1
                        elif script[k] == "}":
                            depth -= 1
                        k += 1
                    keep.append((j + 2, k - 1))
                    j = k
                    continue
                if script[j] == quote:
                    break
                j += 1
            for k in range(i, min(j + 1, n)):
                if out[k] != "\n":
                    out[k] = " "
            for a, b in keep:
                for k in range(a, min(b, n)):
                    out[k] = script[k]
            i = j + 1
            continue
        if script.startswith("//", i):
            j = script.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if script.startswith("/*", i):
            j = script.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out)


def test_no_script_reads_a_const_before_it_is_declared():
    """‏غلطة وقعت فيها فعلاً: نقلت استخدام actMult فوق تعريفه، فالمتصفح رمى
    "Cannot access before initialization" -- وده **قتل باقي السكريبت كله**،
    فبحث العملاء والملء بالمفتاح مكانوش بيتعرّفوا أصلاً. الصفحة كانت شكلها
    سليم والكارت بيظهر، بس الدوس مايملّيش. ده أسوأ نوع: بيفشل في صمت.
    """
    html = _form()
    mark = "<script>\n// ═══ بحث العملاء"
    script = html[html.index(mark) if mark in html else html.index("<script>"):]
    # ‏الـid جوه نص ('nameField' في getElementById) مش استخدام للمتغير، فلازم
    # نشيل النصوص والتعليقات الأول وإلا الاختبار بيرمي غلطة مش موجودة.
    bare = _js_code_only(script)
    for name in ("actMult", "pPerKg", "fatPct", "carbPct", "nameField",
                 "phoneField", "ageField", "fuBox"):
        decl = bare.find("const %s=" % name)
        assert decl != -1, "‏%s مش متعرّف بـconst" % name
        # ‏أول استخدام بعد التعريف: بندوّر على الاسم قبل مكان التعريف
        before = bare[:decl]
        uses = re.findall(r"\b%s\b" % re.escape(name), before)
        assert not uses, (
            "‏%s مستخدم قبل تعريفه -- المتصفح هيرمي غلطة تقتل السكريبت" % name)


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)

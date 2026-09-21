# -*- coding: utf-8 -*-
"""الحصص لازم توصّل اليوم لهدفه.

وجبات القاعدة حصصها ثابتة لكل هدف: فطار التخسيس ٣٠٠ سعر، فطار التضخيم ٨٦٠.
وهدف العميل رقم متغيّر بيتحسب من وزنه وطوله وسنه ونشاطه. فالخطة كانت بتجمع
الوجبات وتحط المجموع جنب الهدف، والرقمين مش نفس الرقم:

    تقليدي:      -١٤٪ لـ -٣٠٪
    خمس وجبات:   -١٤٪ لـ -٢٥٪
    وجبتين:      -٤٤٪ لـ -٥٢٪
    صيام ١٦/٨:   -٤٨٪ لـ -٥٦٪

الأنظمة اللي وجباتها أقل هي الأسوأ، والسبب إنها بتشيل وجبة وتسيب حصص الباقي
زي ما هي -- فمريض نظام الوجبتين كان بياخد نص سعراته والورقة بتقوله إنه ماشي
على هدفه.

Run with:  python3 tests/test_portion_scaling.py
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "pw123456")

import app as A            # noqa: E402
import plan_engine         # noqa: E402
import zigzag              # noqa: E402
from portion_scale import scale_meal   # noqa: E402

BASE = {"name": "اختبار", "age": "30", "gender": "انثى", "height": "165",
        "weight": "80", "protein_per_kg": "1.6", "fat_pct_cal": "30",
        "allergies": [], "culture": "مصري", "symptoms": []}


def _week(**over):
    data = dict(BASE, **over)
    data["zigzag"] = zigzag.zigzag_from_data(data)
    with A.app.test_request_context("/"):
        return data, plan_engine.generate_weekly_plan(data)


def test_grams_scale_and_stay_weighable():
    """‏"١٥٠جم × ١.٤" لازم تطلع رقم يقدر يحطه على الميزان."""
    out, eff = scale_meal("🍗 صدر دجاج مسلوق 150جم + 🍚 أرز أبيض 100جم", 1.4)
    assert "210جم" in out and "140جم" in out, out
    assert abs(eff - 1.4) < 0.05, eff
    small, _ = scale_meal("🌰 لوز 10جم", 1.3)
    assert "15جم" in small, "‏الأرقام الصغيرة لأقرب ٥: %s" % small


def test_things_counted_by_the_piece_stay_whole():
    out, _ = scale_meal("🥚 بيض مسلوق 2 + 🍎 تفاح 1", 2.0)
    assert "بيض مسلوق 4" in out and "تفاح 2" in out, out
    # ‏ومابينزلش تحت الواحدة
    down, _ = scale_meal("🥚 بيض مسلوق 2 + 🍎 تفاح 1", 0.5)
    assert "تفاح 1" in down, down


def test_the_zero_calorie_items_are_left_alone():
    """‏تكبير القرفة والشاي بيخلي النص سخيف من غير أي فايدة."""
    out, _ = scale_meal("🍚 أرز أبيض 100جم + 🍵 شاي + قرفة", 2.0)
    assert "أرز أبيض 200جم" in out, out
    assert "شاي" in out and "قرفة" in out, out
    # ‏بس "شوفان بالماء" مش حاجة صفر سعرات: كلمة "ماء" جوه "بالماء"، والمطابقة
    # الساذجة كانت بتسيب الشوفان كله من غير تكبير
    oats, _ = scale_meal("🥣 شوفان بالماء 40جم", 2.0)
    assert "شوفان بالماء 80جم" in oats, oats


def test_a_spoon_is_not_scaled_twice():
    """‏"زيت زيتون 1 ملعقة" فيها "زيتون" اللي في قايمة الحاجات بالعدد،
    فكانت بتتضرب مرتين -- مرة كعدد ومرة كملعقة -- و×٢ طلعت ٤."""
    out, _ = scale_meal("🫒 زيت زيتون 1 ملعقة صغيرة + 🥚 بيض مسلوق 3", 2.0)
    assert "2 ملعقة صغيرة" in out, out
    assert "بيض مسلوق 6" in out, out


def test_the_snack_calories_move_with_the_portion():
    """‏السناك مكتوب جنبه سعراته، فلو الحصة كبرت والرقم فضل، الورقة بتكدب."""
    out, eff = scale_meal("🍌 موز 1 + 🥛 زبادي 200جم (150 kcal)", 2.0)
    assert "زبادي 400جم" in out, out
    kcal = int(out.split("(")[1].split()[0])
    assert 280 <= kcal <= 320, "‏سعرات السناك مااتحركتش مع الحصة: %s" % out


def test_the_factor_is_capped_so_portions_stay_sane():
    out, _ = scale_meal("🍗 دجاج 150جم", 9.0)
    grams = int(out.split("دجاج ")[1].replace("جم", ""))
    assert grams <= 150 * 3, "‏الحصة طلعت %dجم -- مفيش سقف للمعامل" % grams


def test_every_system_lands_on_its_calorie_target():
    """‏القياس اللي فتح الموضوع: الفرق كان بيوصل -٥٦٪ في نظام الصيام."""
    off = []
    for goal, tdee, gcal in (("weight_loss", "2000", "1500"),
                             ("maintenance", "2200", "2200"),
                             ("muscle_gain", "2600", "2900"),
                             ("bulking", "2800", "3300")):
        for system in ("standard", "five_meals", "two_meals",
                       "intermittent_16_8", "intermittent_18_6",
                       "ramadan", "workout"):
            _data, week = _week(goal_type=goal, tdee=tdee, goal_cal=gcal,
                                diet_plan_type=system, zigzag_mode="off")
            got = sum(d["total_cal"] for d in week) / 7.0
            target = float(gcal)
            gap = abs(got - target) / target * 100
            if gap > 8:
                off.append("%s / %s: هدف %s وطلع %.0f (%.0f%%)"
                           % (goal, system, gcal, got, gap))
    assert not off, "‏أنظمة بعيدة عن هدفها:\n   %s" % "\n   ".join(off)


def test_each_single_day_lands_on_its_own_target_with_cycling_on():
    """‏التدوير بيخلي لكل يوم هدف مختلف، فالحصص لازم تتحرك مع اليوم مش مع
    المتوسط الأسبوعي. يوم +٢٠٪ لازم حصصه تكون أكبر فعلاً."""
    random.seed(3)
    worst = (0.0, None)
    over = 0
    days = 0
    for goal, tdee, gcal in (("weight_loss", "2000", "1400"),
                             ("bulking", "2800", "3400")):
        for system in ("standard", "five_meals", "two_meals",
                       "intermittent_16_8"):
            for mode in ("classic", "refeed", "training"):
                _data, week = _week(goal_type=goal, tdee=tdee, goal_cal=gcal,
                                    diet_plan_type=system, zigzag_mode=mode)
                for day in week:
                    target = day.get("target_cal") or float(gcal)
                    gap = abs(day["total_cal"] - target) / target * 100
                    days += 1
                    if gap > 10:
                        over += 1
                    if gap > worst[0]:
                        worst = (gap, (goal, system, mode, target,
                                       day["total_cal"]))
    assert days >= 160, "‏الاختبار قاس %d يوم بس" % days
    assert not over, (
        "‏%d يوم من %d فرقهم أكبر من ١٠٪. أسوأ: %.0f%% %s"
        % (over, days, worst[0], worst[1]))


def test_the_high_cycling_day_really_gets_more_food():
    """‏لو الحصص مااتحركتش مع هدف اليوم، التدوير يبقى رقم على الورق بس."""
    _data, week = _week(goal_type="weight_loss", tdee="2200", goal_cal="1600",
                        diet_plan_type="standard", zigzag_mode="strong")
    pairs = [(d.get("target_cal"), d["total_cal"]) for d in week
             if d.get("target_cal")]
    assert len(pairs) == 7, "‏التدوير مش شغال في الاختبار ده"
    high = max(pairs, key=lambda x: x[0])
    low = min(pairs, key=lambda x: x[0])
    assert high[1] > low[1] * 1.2, (
        "‏أعلى يوم %s وأقل يوم %s -- الأكل مش بيتحرك مع الهدف" % (high, low))


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

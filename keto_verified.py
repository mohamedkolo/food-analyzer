# -*- coding: utf-8 -*-
"""Keto meals written with explicit grams so every item resolves against the
food table (no bare "🧀" or "🥑", no "بالزبدة 10جم" dishes). cal/p are computed
from the items, not typed. These recipes were authored for arithmetic
coverage. They are NOT clinician-reviewed and are not a clinical rule."""

_BREAKFAST = [
    "🥚 بيض 3 + 🥑 أفوكادو 100جم + 🧀 فيتا 40جم + 🫒 زيت زيتون 1 ملعقة",
    "🥚 بيض 2 + 🐟 سلمون مشوي 100جم + 🥑 أفوكادو 75جم + 🥒 خيار 100جم",
    "🥚 بيض 3 + 🥬 سبانخ 100جم + 🧀 بارميزان 20جم + 🫒 زيت زيتون 1 ملعقة",
    "🥛 زبادي يوناني 150جم + 🌰 جوز 20جم + 🌰 لوز 15جم",
    "🥚 بيض 2 + 🧀 جبنة حلوم مشوية 60جم + 🥒 خيار 100جم + 🌰 لوز 15جم",
]
_LUNCH = [
    "🍗 صدر دجاج مشوي 150جم + 🥗 سلطة خضراء 150جم + 🥑 أفوكادو 75جم + 🫒 زيت زيتون 1 ملعقة",
    "🐟 سلمون مشوي 150جم + 🥦 بروكلي 150جم + 🫒 زيت زيتون 1 ملعقة",
    "🥩 لحم بقري 150جم + 🍄 مشروم 100جم + 🥗 سلطة خضراء 150جم + 🫒 زيت زيتون 1 ملعقة",
    "🦐 جمبري 150جم + 🥒 كوسة 150جم + 🫒 زيت زيتون 1 ملعقة + 🧀 بارميزان 20جم",
    "🐟 تونة معلبة بالماء 120جم + 🥑 أفوكادو 100جم + 🥬 سبانخ 100جم + 🫒 زيت زيتون 1 ملعقة",
]
_DINNER = [
    "🥩 لحم بقري 150جم + 🥒 كوسة 150جم + 🧀 بارميزان 20جم",
    "🍗 صدر دجاج مشوي 150جم + 🥦 بروكلي 150جم + 🫒 زيت زيتون 1 ملعقة",
    "🐟 سلمون مشوي 150جم + 🥬 سبانخ 100جم + 🧀 فيتا 40جم",
    "🥚 بيض 3 + 🥑 أفوكادو 75جم + 🥒 خيار 100جم + 🧀 فيتا 40جم",
]


def _build(texts):
    import meal_macros as mm
    out = []
    for t in texts:
        r = mm.macros(t)
        assert r["complete"], (t, r["unresolved"])
        out.append({"meal": t, "cal": r["cal"], "p": r["p"]})
    return out


def keto_verified():
    return {"breakfast": _build(_BREAKFAST), "lunch": _build(_LUNCH),
            "dinner": _build(_DINNER)}

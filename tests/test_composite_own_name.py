# -*- coding: utf-8 -*-
import os, sys
os.environ.setdefault("SECRET_KEY", "k"); os.environ.setdefault("ADMIN_PASSWORD", "pw123456")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import meal_macros as M
import meal_variant_foods as V

MILK = "حليب كامل الدسم مع فيتامين د (USDA 171265)"


def test_a_name_that_contains_the_word_with_is_not_a_composite():
    r = M.macros("200 جم " + MILK)
    assert r["complete"] and round(r["cal"]) == 122 and r["items"][0]["exact_identity"], r


def test_real_composites_are_still_withheld():
    for t in ("150 جم سمك مع خضار", "100 جم أرز مع دجاج", "200 جم " + MILK + " مع تمر"):
        r = M.macros(t)
        assert not r["complete"] and r["items"][0]["unresolved"] == "composite", t


def test_no_offered_variant_is_withheld_as_composite():
    assert [f["n"] for f in V.VARIANT_FOODS if M.macros("100 جم " + f["n"])["items"][0].get("unresolved") == "composite"] == []


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v(); print("ok", k)

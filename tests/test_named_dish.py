"""
A dish the query names narrows Tier 1's pool (tier_1/symbolic_anchoring.py), and a dish
name that states its spice level corrects the source's taste value (pipeline).
"""

import pytest

from pipeline.build_dataset import spice_from_name
from tier_1.symbolic_anchoring import named_dishes, narrow_to_named_dish

POOL = [
    {"name": "Chicken Karahi (Half)"},
    {"name": "Chicken Alfredo Garlic Bread"},
    {"name": "Coconut Nouc Cham Dumpling Bowl"},
    {"name": "Lahori Chicken Karahi"},
]


def test_a_named_dish_narrows_the_pool_even_under_a_broader_category():
    # how the extractor really returned "spicy chicken karahi under 1500"
    intent = {"craving": "spicy chicken karahi", "preferred_category": "chicken"}
    kept, relaxed = narrow_to_named_dish(POOL, intent)
    assert [c["name"] for c in kept] == ["Chicken Karahi (Half)", "Lahori Chicken Karahi"]
    assert relaxed is None


@pytest.mark.parametrize(
    "text, dishes",
    [
        ("biryani please", ["biryani"]),
        ("seekh kabab and naan", ["kebab"]),
        ("anything but pizza", []),
        ("no more burgers, something light", []),
        ("not spicy karahi", ["karahi"]),  # "not" is about the spice, not the karahi
        ("something with chicken", []),
    ],
)
def test_dish_words_are_read_from_the_query(text, dishes):
    assert named_dishes({"raw_input": text}) == dishes


def test_a_dish_nobody_serves_leaves_the_pool_and_says_so():
    kept, relaxed = narrow_to_named_dish(POOL, {"raw_input": "nihari please"})
    assert kept == POOL
    assert relaxed["constraint"] == "named_dish" and relaxed["old_value"] == "nihari"


@pytest.mark.parametrize(
    "name, spice, corrected",
    [
        ("Chicken Pepperoni (Non Spicy)", 0.8, 0.1),
        ("Mild Chicken Korma", 0.05, None),  # already mild
        ("Chilli Chicken", 0.0, 0.5),
        ("Lahori Chicken Karahi", 0.0, 0.5),
        ("Chicken Karahi (Half)", 0.8, None),  # already spicy
        ("Chicken Shinwari Karahi Half", 0.0, None),  # Shinwari is made mild
        ("Hot Gulab Jamun", 0.0, None),  # served hot, not spiced
    ],
)
def test_a_name_that_states_the_spice_level_corrects_it(name, spice, corrected):
    assert spice_from_name(name, spice) == corrected


def test_asked_for_an_ingredient_a_dish_that_names_it_is_preferred():
    # Regression, 2026-09-21: "something with chicken" picked a mushroom soup whose
    # typical ingredients listed chicken (the stock).
    from tier_1.symbolic_anchoring import NAMED_INGREDIENT_MIN, prefer_named_ingredient

    named = [{"name": f"Chicken Dish {i}"} for i in range(NAMED_INGREDIENT_MIN)]
    pool = [{"name": "Mushroom Soup"}, *named]
    assert prefer_named_ingredient(pool, "chicken") == named


def test_a_meat_the_words_ask_for_is_preferred_even_when_filed_under_the_dish():
    # The extractor files "spicy chicken karahi" under "karahi"; a seekh kebab karahi won.
    from tier_1.symbolic_anchoring import NAMED_INGREDIENT_MIN, prefer_named_ingredient

    chicken = [{"name": f"Chicken Karahi {i}"} for i in range(NAMED_INGREDIENT_MIN)]
    pool = [{"name": "Seekh Kebab Karahi Full"}, *chicken]
    intent = {"raw_input": "spicy chicken karahi under 2000"}
    assert prefer_named_ingredient(pool, "karahi", intent) == chicken


def test_a_negated_meat_is_not_preferred():
    from tier_1.symbolic_anchoring import asked_proteins

    assert asked_proteins({"raw_input": "karahi but not chicken"}) == set()
    assert asked_proteins({"raw_input": "mutton karahi, no chicken"}) == {"mutton"}


def test_too_few_dishes_naming_it_leaves_the_pool_alone():
    from tier_1.symbolic_anchoring import prefer_named_ingredient

    pool = [{"name": "Mushroom Soup"}, {"name": "Chicken Tikka"}]
    assert prefer_named_ingredient(pool, "chicken") == pool
    assert prefer_named_ingredient(pool, "desi") == pool  # a cuisine isn't an ingredient

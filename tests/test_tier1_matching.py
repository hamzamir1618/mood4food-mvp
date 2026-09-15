"""
How Tier 1 reads a requested category or food, and an excluded one. Pure: no database.
"""

from tier_1.symbolic_anchoring import exclusion_terms, requested_match


def test_a_cuisine_request_matches_the_category_not_dish_names():
    afghan = requested_match("Afghan")
    assert afghan["category_key"] == "afghan" and afghan["match_names"] is False
    assert requested_match("fast food")["category_key"] == "fast_food"
    assert requested_match("chinese")["match_names"] is False


def test_a_dish_or_food_request_matches_names_and_ingredients():
    biryani = requested_match("biryani")
    assert biryani["match_names"] is True and biryani["preferred_ingredients"] == []
    assert requested_match("seafood")["preferred_ingredients"] == [
        "fish",
        "prawns",
        "crab",
        "lobster",
        "squid",
    ]
    assert requested_match("chicken")["preferred_ingredients"] == ["chicken"]
    assert requested_match("dairy")["preferred_allergen"] == "dairy"


def test_exclusions_become_allergens_and_ingredients():
    assert exclusion_terms(["bread"]) == (["gluten"], ["bread"])
    allergens, ingredients = exclusion_terms(["meat", "Cheese"])
    assert allergens == ["dairy"]
    assert {"chicken", "beef", "mutton", "cheese"} <= set(ingredients)
    assert exclusion_terms([]) == ([], [])

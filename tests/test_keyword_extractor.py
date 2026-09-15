"""
The keyword extractor is the fallback when Groq is unavailable, and the only extractor
in test mode. Pure: no network.
"""

from tier_1.keyword_extractor import KeywordExtractorImpl

extract = KeywordExtractorImpl().extract


def test_no_bread_excludes_gluten():
    assert extract("something with no bread").allergens_pruned == ["gluten"]
    assert extract("I can't have naan or roti").allergens_pruned == ["gluten"]


def test_a_named_cuisine_or_dish_becomes_the_request():
    assert extract("afghan food").preferred_category == "afghan"
    assert extract("pakistani food please").preferred_category == "desi"
    assert extract("I want a spicy chicken burger").preferred_category == "burger"


def test_a_negated_food_is_excluded_not_requested():
    intent = extract("no chicken, something spicy")
    assert intent.preferred_category is None
    assert intent.allergens_pruned == ["meat"]
    assert intent.mood_vector.spice == 1.0

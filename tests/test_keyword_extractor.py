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
    assert intent.allergens_pruned == ["chicken"]  # that meat, not all meat
    assert intent.mood_vector.spice == 1.0


# ── The word sweep of 2026-09-21 ────────────────────────────────────────────────


def test_an_allergy_stated_in_words_is_excluded():
    # Both matched nothing, so the fallback served nuts and dairy to the people who said so.
    assert extract("i want food, nut allergy").allergens_pruned == ["nuts"]
    assert extract("I am lactose intolerant").allergens_pruned == ["dairy"]
    assert extract("allergic to cashews").allergens_pruned == ["nuts"]
    assert extract("no soy please").allergens_pruned == ["soy"]


def test_excluding_one_meat_keeps_the_others():
    # "mutton karahi, no chicken" had excluded all meat, so every karahi, and served naan.
    intent = extract("mutton karahi, no chicken")
    assert intent.allergens_pruned == ["chicken"]
    assert intent.preferred_category == "karahi"


def test_a_negated_taste_is_not_craved():
    # "not spicy" had been read as spice 1.0.
    assert extract("not spicy please").mood_vector.spice == 0.0
    assert extract("something spicy").mood_vector.spice == 1.0


def test_taste_words_match_whole_words_and_light_is_not_a_flavour():
    assert extract("a delightful dinner").mood_vector.sour == 0.0  # "light" in "delightful"
    assert (
        extract("something light").mood_vector.model_dump()
        == extract("food").mood_vector.model_dump()
    )


def test_foods_and_traditional_are_requests_too():
    assert extract("something with rice").preferred_category == "rice"
    assert extract("noodles please").preferred_category == "noodles"
    assert extract("traditional food").preferred_category == "desi"

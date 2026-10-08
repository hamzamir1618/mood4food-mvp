"""
Every way a request says it doesn't want something (tier_1/query_words.py NEGATION).

A negation that wasn't read didn't just go unread: the next rule read the food as wanted.
"Something that's not sweet and doesn't have onions" was won by fried beef with onions, with
onions in the name of every dish behind it.
"""

import pytest

from dialogue.questions import candidate_questions
from dialogue.state import Conversation
from pipeline.ingredients import ALLERGEN_TAGS
from tier_1 import query_words
from tier_1.keyword_extractor import KeywordExtractorImpl
from tier_1.symbolic_anchoring import FOOD_GROUPS, named_dishes


def wanted(text):
    return query_words.wanted_food(text, ALLERGEN_TAGS, tuple(FOOD_GROUPS))


@pytest.mark.parametrize(
    "text",
    [
        "something thats not sweet and doesn't have onions",
        "no onions",
        "without any onion",
        "nothing with onions",
        "free of onion",
        "onion-free please",
        "i hate onions",
        "not a fan of onions",
        "anything but onions",
        "minus the onions",
        "i don’t want onions",  # a typed curly apostrophe
        "i dont want onions",
        "does not contain onion",
    ],
)
def test_onions_left_out_are_never_onions_asked_for(text):
    assert "onion" in query_words.excluded_foods(text)
    assert wanted(text) is None


def test_onions_asked_for_are_still_asked_for():
    assert wanted("something with onions") == "onions"
    assert query_words.excluded_foods("something with onions") == []


def test_a_list_is_read_to_its_end():
    assert query_words.excluded_foods("no onion, garlic or chilli") == [
        "onion",
        "garlic",
        "green chilli",
    ]


def test_a_comma_that_doesnt_continue_a_list_ends_it():
    assert query_words.excluded_foods("no onions, chicken please") == ["onion"]
    assert wanted("no onions, chicken please") == "chicken"


def test_an_allergen_group_can_be_left_out_in_any_of_these_words():
    for text in ("doesn't contain nuts", "dairy free", "no dairy"):
        assert {"nuts", "dairy"} & set(query_words.excluded_foods(text)), text
    assert wanted("dairy free") is None


@pytest.mark.parametrize(
    ("text", "avoided"),
    [
        ("something not sweet", {"sweet": 0.4}),
        ("nothing sweet", {"sweet": 0.4}),
        ("i don't want anything spicy", {"spice": 0.4}),
        ("not too spicy", {"spice": 0.7}),
        ("less spicy please", {"spice": 0.7}),
        ("a mild karahi", {"spice": 0.7}),
        ("something spicy", {}),
    ],
)
def test_a_flavour_not_wanted_is_read_with_how_strongly(text, avoided):
    assert query_words.avoided_tastes(text) == avoided


@pytest.mark.parametrize("text", ["nothing sweet", "i dont want anything spicy", "not sweet"])
def test_a_flavour_not_wanted_is_never_craved(text):
    mood = KeywordExtractorImpl().extract(text).mood_vector.model_dump()
    assert not any(mood.values()), mood


def test_a_dish_not_wanted_is_never_asked_for():
    assert named_dishes({"raw_input": "i hate biryani, karahi please"}) == ["karahi"]
    assert named_dishes({"raw_input": "anything but pizza"}) == []


SHORT = [{"price_pkr": 300.0 + 200 * i, "category": "desi_traditional"} for i in range(6)]


def test_the_mood_question_never_offers_a_flavour_the_request_ruled_out():
    intent = {"raw_input": "something not sweet", "mood_vector": {}}
    question = next(
        q for q in candidate_questions(intent, {}, Conversation(), SHORT) if q.slot == "taste"
    )
    assert "sweet" not in question.chips
    assert "spicy" in question.chips

"""
The words the extractor's fields can't carry (tier_1/query_words.py), each one found
ignored by the 2026-09-21 word sweep. Pure: no network, no database.
"""

import pytest

from tier_1 import query_words as words
from tier_1.symbolic_anchoring import cannot_sentence, relaxation_sentence

AREAS = [
    {"area": "F-7", "lat": 33.72, "lng": 73.05},
    {"area": "G-9", "lat": 33.69, "lng": 73.03},
    {"area": "Blue Area", "lat": 33.71, "lng": 73.07},
]


# ── Foods the request leaves out ───────────────────────────────────────────────
@pytest.mark.parametrize(
    "text, excluded",
    [
        ("no onion please", ["onion"]),
        ("without garlic and ginger", ["garlic", "ginger"]),
        ("no mushrooms or capsicum", ["mushrooms", "bell pepper"]),
        ("hold the mayo", ["mayonnaise"]),
        ("i'm pescatarian", ["meat"]),  # land meat; fish and prawns stay
        ("something spicy", []),
        ("not too spicy", []),  # a taste, not a food
        ("no onion rings", ["onion"]),
    ],
)
def test_the_words_say_what_to_leave_out(text, excluded):
    assert words.excluded_foods(text) == excluded


def test_a_dislike_does_not_run_on_past_the_food():
    # The exclusion scope in Tier 1 runs through lists, which had excluded whole meals.
    assert words.excluded_foods("no chicken, something with rice") == ["chicken"]


# ── Cooking method ───────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "text, asked, avoids",
    [
        ("something grilled", "grilled", False),
        ("bbq please", "grilled", False),
        ("nothing fried", "grilled", True),
        ("not too oily", "grilled", True),
        ("fried chicken", "fried", False),
        ("a burger", None, False),
    ],
)
def test_a_cooking_method_is_read_from_the_words(text, asked, avoids):
    assert words.cooking_asked(text) == asked
    assert words.avoids_frying(text) is avoids


def test_grilled_names_are_the_ones_cooked_that_way():
    assert words.GRILLED_NAME.search("Chicken Tikka Boti")
    assert words.GRILLED_NAME.search("BBQ Platter")
    assert not words.GRILLED_NAME.search("Chicken Karahi")


# ── An area named in the request ───────────────────────────────────────────────
@pytest.mark.parametrize(
    "text, label",
    [
        ("something desi in F-7", "F-7"),
        ("pizza in f7", "F-7"),
        ("lunch in blue area", "Blue Area"),
        ("g 9 biryani", "G-9"),
        ("anything", None),
        ("under 500", None),  # a price is not a sector
    ],
)
def test_an_area_named_in_the_request_sets_the_location(text, label):
    here = words.area_asked(text, AREAS)
    assert (here or {}).get("label") == label
    if here:
        assert here["lat"] and here["lng"]


# ── What the app cannot do, said out loud ──────────────────────────────────────
@pytest.mark.parametrize(
    "text, phrase",
    [
        ("what's popular", "sort dishes by how popular they are"),
        ("something quick", "know how long a dish takes to make"),
        ("anything with delivery", "check what's available for delivery"),
        ("is it open now", "know a restaurant's opening hours"),
        ("somewhere for a date night", "judge a restaurant's atmosphere"),
        ("something cold", "know how a dish is served"),
    ],
)
def test_an_unsupported_request_is_named_not_ignored(text, phrase):
    assert words.unsupported(text) == [phrase]
    assert phrase in cannot_sentence(text)


def test_the_notice_says_what_was_dropped_and_what_was_widened():
    said = relaxation_sentence(
        [{"constraint": "named_dish", "old_value": "sushi"}], "popular sushi"
    )
    assert said == (
        "I can't sort dishes by how popular they are, so I've gone on the rest of your request. "
        "I couldn't find sushi on the menus I hold, so this is the closest I have."
    )


def test_a_request_the_app_can_meet_says_nothing():
    assert cannot_sentence("spicy chicken karahi under 1500") == ""
    assert relaxation_sentence([], "spicy chicken karahi") == ""


@pytest.mark.parametrize(
    "text, looks_like_a_place",
    [
        ("something desi in F-7", True),
        ("biryani near me", True),
        ("lunch in blue area", True),
        ("something spicy", False),  # an ordinary request never pays for the areas lookup
        ("chicken karahi under 1500", False),
    ],
)
def test_the_areas_are_only_looked_up_when_a_place_is_named(text, looks_like_a_place):
    assert words.mentions_a_place(text) is looks_like_a_place


def test_asking_for_fried_food_is_read_too():
    assert words.cooking_asked("i want something fried") == "fried"
    assert words.cooking_asked("crispy chicken") == "fried"
    assert words.cooking_asked("nothing fried") == "grilled"  # avoiding it asks for the other


def test_near_me_without_a_location_is_recognised():
    assert words.asks_for_nearby("biryani near me") is True
    assert words.asks_for_nearby("somewhere close to me") is True
    assert words.asks_for_nearby("biryani") is False


def test_the_cooking_patterns_match_dish_names_whatever_their_case():
    # Dish names are Title Case: a case-sensitive pattern narrowed nothing.
    assert words.FRIED.search("Chicken Fried Rice")
    assert words.FRIED.search("Crispy Chicken Broast")
    assert not words.FRIED.search("Chicken And Basil Dumplings")


# ── A food the request asks for, when the extractor named none ──────────────────
TAGS = ("dairy", "gluten", "nuts", "fish", "shellfish", "egg", "soy", "sesame")
GROUPS = ("seafood", "meat", "vegetables", "breakfast")


@pytest.mark.parametrize(
    "text, wanted",
    [
        ("something with dairy", "dairy"),  # Groq returns no category for this
        ("something with chicken", "chicken"),
        ("i want seafood", "seafood"),
        ("something with cheese, no onion", "cheese"),
        ("no dairy please", None),  # the opposite of a request
        ("something spicy", None),
        ("anything", None),
    ],
)
def test_a_food_the_words_ask_for_is_read_when_the_extractor_names_none(text, wanted):
    assert words.wanted_food(text, TAGS, GROUPS) == wanted


@pytest.mark.parametrize(
    "text, wanted, cooking",
    [
        ("something grilled, nothing fried", None, "grilled"),
        ("something fried", None, "fried"),
        ("fried chicken", "chicken", "fried"),
    ],
)
def test_how_a_dish_is_cooked_is_not_a_food_to_ask_for(text, wanted, cooking):
    # The vocabulary lists "fried" as a spelling of cooking oil, so "nothing fried" had been
    # read as a request for fried food, and a fried fish won "something grilled".
    assert words.wanted_food(text, TAGS, GROUPS) == wanted
    assert words.cooking_asked(text) == cooking

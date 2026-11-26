"""
The stock photo a dish is shown with. Calls the real function: an earlier check re-implemented
the regex instead, passed, and missed that the real one had been corrupted into matching nothing.
"""

import pytest

from tier_1.symbolic_anchoring import CATEGORY_PHOTOS, KEYWORD_PHOTOS, representative_image


def _photo_for(*words):
    return next(url for keys, url in KEYWORD_PHOTOS if set(words) <= set(keys))


BREAD = _photo_for("paratha")
COFFEE = _photo_for("coffee")
KEBAB = _photo_for("kebab")
DONUT = _photo_for("donut")
BIRYANI = _photo_for("biryani")
FRIED_RICE = _photo_for("fried rice")
DUMPLINGS = _photo_for("dumpling")
WINGS = _photo_for("wing")
FISH = _photo_for("fish")
SANDWICH = _photo_for("sandwich")
SAMOSA = _photo_for("samosa")
SUSHI = _photo_for("sushi")
STIR_FRY = _photo_for("manchurian")
STEAK = _photo_for("steak")


@pytest.mark.parametrize(
    "name, category, expected",
    [
        ("Aloo Paratha", "cafe_bakery", BREAD),
        ("Lahori Halwa Puri", "cafe_bakery", BREAD),
        ("Seekh Kababs", "desi_traditional", KEBAB),  # plurals still match
        ("Iced Coffee", "beverages", COFFEE),
        ("Chocolate Donut", "cafe_bakery", DONUT),
        ("Chicken Biryani", "desi_traditional", BIRYANI),
        ("Steamed White Rice", "chinese_asian", FRIED_RICE),
        ("Korean Dumpling", "chinese_asian", DUMPLINGS),
        ("Honey Glazed Wings", "chinese_asian", WINGS),
        ("Grilled Fish", "continental_upscale", FISH),
        ("Club Sandwich", "fast_food", SANDWICH),
        ("Spring Rolls", "chinese_asian", SAMOSA),  # not shawarma wrap
        ("Sushi Roll", "chinese_asian", SUSHI),  # not shawarma wrap
        ("Chicken Manchurian with Rice", "chinese_asian", STIR_FRY),  # main before side
    ],
)
def test_a_dish_is_shown_as_what_its_name_says(name, category, expected):
    assert representative_image(name, category) == expected


@pytest.mark.parametrize(
    "name, category, expected",
    [
        (
            "Dawat Platter",
            "desi_traditional",
            CATEGORY_PHOTOS["desi_traditional"],
        ),  # "platter" contains "latte"
        ("Chicken Steak", "continental_upscale", STEAK),  # "steak" contains "tea"
        ("Steamed White Rice", "chinese_asian", FRIED_RICE),  # "steamed" contains "tea"
    ],
)
def test_a_word_inside_another_word_is_not_a_match(name, category, expected):
    assert representative_image(name, category) != COFFEE
    assert representative_image(name, category) == expected


def test_a_mixed_category_gets_no_photo_rather_than_a_wrong_one():
    # Café & bakery holds cakes, parathas and full breakfasts; one photo can't be honest for all.
    assert representative_image("Breakfast For 4 Persons", "cafe_bakery") == ""
    assert representative_image("Aloo Paratha", "cafe_bakery") != DONUT


def test_the_patterns_hold_no_control_characters():
    # A shell heredoc once turned the regex's word boundaries into backspace characters.
    from tier_1 import symbolic_anchoring

    for pattern, _ in symbolic_anchoring._KEYWORD_PATTERNS:
        assert "\x08" not in pattern.pattern
        assert r"\b" in pattern.pattern

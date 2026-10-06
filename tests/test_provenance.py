"""
How a dish came to be known (ui/provenance.py): the sentences must say what the fields
support and no more. Pure: no database.
"""

import pytest

from ui import compose
from ui.provenance import TONES, lines, tally

CONFIRMED = {
    "review_status": "human_confirmed",
    "price_status": "trusted",
    "price_note": "confirmed by a reviewer",
    "ingredients_basis": "named + typical ingredients",
    "allergens_known": True,
    "allergens": ["dairy"],
    "nutrition_confidence": "medium",
    "taste_source": "original",
    "source": "https://www.example.com/menu",
    "source_date": "2026-08-24",
}


def said(dish: dict) -> str:
    return " ".join(line["text"] for line in lines(dish))


def test_a_confirmed_dish_says_who_confirmed_it_and_what_is_only_estimated():
    text = said(CONFIRMED)
    assert "confirmed by a person" in text
    assert "inferred from those ingredients, not from a test" in text
    assert "estimated from those ingredients against USDA" in text
    assert "example.com" in text and "2026-08-24" in text


def test_an_unchecked_row_says_so():
    text = said({**CONFIRMED, "review_status": "auto_imported"})
    assert "No person has checked this row" in text


def test_a_price_that_could_not_be_checked_carries_its_reason():
    text = said(
        {
            **CONFIRMED,
            "price_status": "unverified",
            "price_note": "price not found in its OCR evidence",
        }
    )
    assert "could not be checked" in text and "price not found in its OCR evidence" in text


def test_a_price_on_the_menu_does_not_need_the_note():
    assert "confirmed by a reviewer" not in said(CONFIRMED)


def test_unknown_allergens_say_the_dish_is_never_offered():
    text = said({**CONFIRMED, "allergens_known": False, "allergens": []})
    assert "never offered to anyone who excludes one" in text


def test_a_borrowed_flavour_says_it_is_borrowed():
    text = said({**CONFIRMED, "taste_source": "restaurant_average"})
    assert "this restaurant's average" in text and "counts for less" in text


def test_a_flagged_estimate_says_health_counts_for_less():
    text = said({**CONFIRMED, "nutrition_flag": "over 2,500 kcal per serving"})
    assert "failed a plausibility check" in text


def test_it_never_claims_a_dish_is_safe_measured_or_correct():
    for dish in (CONFIRMED, {**CONFIRMED, "allergens_known": False}, {}):
        badges = " ".join(line["badge"] for line in lines(dish))
        printed = f"{said(dish)} {badges}".lower()
        for word in ("safe", "guaranteed", "verified by a lab", "measured", "accurate"):
            assert word not in printed, f"{word!r} in {printed!r}"


def test_a_dish_with_no_history_offers_no_panel():
    assert lines({}) == []
    layout = compose.pick({"winning_dish": {}, "agent_weights": {}}, {})
    assert "provenance" not in [b["id"] for b in layout["blocks"]]


@pytest.mark.parametrize("label", ["The row", "The price", "Its ingredients", "Its nutrition"])
def test_every_line_is_labelled_for_the_panel(label):
    assert label in [line["label"] for line in lines(CONFIRMED)]


def test_every_fact_is_stamped_with_a_mark_a_badge_and_a_tone():
    """The card draws the icon from `id` and the badge's weight from `tone`: both must be there."""
    for facet in lines(CONFIRMED):
        assert facet["id"] and facet["label"] and facet["badge"]
        assert facet["tone"] in TONES, facet
        assert len(facet["badge"]) <= 22, facet["badge"]  # it has to fit on one line


def test_the_badge_says_which_kind_of_knowing_each_fact_is():
    by_id = {f["id"]: f for f in lines(CONFIRMED)}
    assert by_id["row"]["tone"] == "confirmed"  # a person looked at it
    assert by_id["ingredients"]["tone"] == "inferred"  # named plus what is typical
    assert by_id["allergens"]["tone"] == "inferred"  # never "confirmed": no dish was tested
    assert by_id["nutrition"]["tone"] == "estimated"  # against USDA, with error
    assert "medium" in by_id["nutrition"]["badge"]


def test_an_unchecked_row_is_stamped_unchecked_not_merely_worded_so():
    facets = {f["id"]: f for f in lines({**CONFIRMED, "review_status": "auto_imported"})}
    assert facets["row"]["tone"] == "unchecked"
    assert facets["row"]["badge"] == "Not checked"


def test_a_flagged_estimate_says_so_on_the_badge_too():
    facets = {f["id"]: f for f in lines({**CONFIRMED, "nutrition_flag": "over 2,500 kcal"})}
    assert "flagged" in facets["nutrition"]["badge"].lower()


def test_the_tally_counts_the_facts_strongest_first_and_leaves_out_the_citation():
    facets = lines(CONFIRMED)
    counted = tally(facets)
    assert [t["tone"] for t in counted] == [t for t in TONES if t in {c["tone"] for c in counted}]
    assert sum(t["count"] for t in counted) == len([f for f in facets if f["id"] != "source"])
    assert all(str(t["count"]) in t["text"] for t in counted)


def test_the_tally_of_nothing_is_nothing():
    assert tally([]) == []


def test_the_panel_is_part_of_the_layout_the_server_sends():
    layout = compose.pick({"winning_dish": CONFIRMED, "agent_weights": {}}, {})
    block = next(b for b in layout["blocks"] if b["id"] == "provenance")
    assert block["slot"] == "band"
    assert len(block["props"]["lines"]) >= 5

"""
Unit tests for the Phase 1 data pipeline. No database, network or data files needed.
"""

from datetime import datetime

import pytest

from pipeline import paths, prices, servings
from pipeline.areas import area_name, restaurant_locations
from pipeline.build_dataset import (
    KEY_COL,
    _cell_text,
    core_name,
    listed_items,
    nutrition_confidence,
    read_platter_answers,
)
from pipeline.ingredients import (
    VOCABULARY,
    derive_diet_flags,
    detect_ingredients,
    implied_coating,
)
from pipeline.nutrition import estimate, implausible
from pipeline.sources import dish_uid

# ── Ingredients and diet flags ───────────────────────────────────────────────


def test_longer_spelling_is_not_counted_again_through_a_shorter_one():
    assert detect_ingredients("Spring Onion Beef") == ["beef", "spring onion"]


def test_shared_alias_yields_every_ingredient_it_names():
    assert set(detect_ingredients("Hummus")) == {"chickpeas", "tahini"}


def test_dish_names_that_imply_an_allergen():
    assert "egg" in detect_ingredients("Shakshuka")
    assert {"egg", "wheat flour"} <= set(detect_ingredients("Chocolate Lava Cake"))
    assert {"rice", "milk"} <= set(detect_ingredients("Kheer"))


@pytest.mark.parametrize(
    "name, description, ingredients, expected",
    [
        ("Mozzarella Sticks", "Mozzarella cheese, sweet chilli sauce", ["cheese"], ["wheat flour"]),
        ("Chicken Broast With Fries", "", ["chicken", "fries"], ["wheat flour"]),
        ("Fish & Chips", "", ["fish", "potato"], ["wheat flour"]),
        ("Finger Fish", "", ["fish"], ["wheat flour"]),
        ("Grilled Fish", "Breaded and pan fried", ["fish"], ["wheat flour"]),
        # a gluten-free batter, gluten already present, no coating, okra, fries, unknown recipe
        ("Anarkali Pakora", "", ["gram flour", "onion"], []),
        ("Chicken Tempura", "", ["chicken", "egg", "wheat flour"], []),
        ("Grilled Chicken", "Served with crispy onions", ["chicken"], []),
        ("Lady Finger Masala", "", ["okra"], []),
        ("Finger Chips", "", ["fries"], []),
        ("Crispy Special", "", [], []),
    ],
)
def test_a_name_that_means_a_fried_coating_implies_wheat_flour(
    name, description, ingredients, expected
):
    assert implied_coating(name, description, ingredients) == expected


def test_crumbs_named_on_the_menu_are_wheat_flour():
    assert "wheat flour" in detect_ingredients("Panko Prawns")
    assert "wheat flour" in detect_ingredients("Chicken in bread crumbs")


def test_sake_on_a_japanese_menu_is_salmon_not_alcohol():
    ings = detect_ingredients("Sake Salmon Maki")
    assert ings == ["fish", "rice"]
    assert derive_diet_flags(ings)["is_halal"] is True


def test_platter_item_lists_name_their_meat_and_fish():
    # Owner item lists are trusted as the whole dish, so a missed meat would make it vegetarian.
    thaal = detect_ingredients("4pcs Malai Boti, 4pcs Tandoori Boti, Masala Sajji, Naan")
    assert {"chicken", "cream", "naan"} <= set(thaal)
    assert derive_diet_flags(thaal)["is_vegetarian"] is False
    sushi = detect_ingredients("4pcs Assorted Nigiri, 4pcs Assorted Sashimi, 4pcs Hoso Maki")
    assert {"fish", "rice"} <= set(sushi)


def test_platter_items_found_on_the_restaurants_menu_bring_its_ingredients():
    assert core_name("4pcs Malai Boti (Half)") == "malai boti"
    menu = {("Umai", "philadelphia maki"): {"fish", "rice", "cream cheese"}}
    ings, known = listed_items("Umai", "4pcs Philadelphia Maki, 4pcs Hoso Maki", menu)
    assert "fish" in ings
    assert known is True


def test_an_item_list_with_an_unrecognised_item_is_not_the_whole_dish():
    _, known = listed_items("Umai", "4pcs Volcano Surprise, Cold Drink", {})
    assert known is False


def test_pork_or_alcohol_named_makes_a_dish_not_halal():
    assert derive_diet_flags(detect_ingredients("Pork Ribs"))["is_halal"] is False
    assert derive_diet_flags(detect_ingredients("Chicken In Wine Sauce"))["is_halal"] is False


@pytest.mark.parametrize(
    "ingredients, vegetarian, vegan",
    [
        (["paneer", "spinach"], True, False),
        (["honey", "oats"], True, False),
        (["fish", "rice"], False, False),
        (["lentils", "onion"], True, True),
    ],
)
def test_diet_flags_follow_the_ingredients(ingredients, vegetarian, vegan):
    flags = derive_diet_flags(ingredients)
    assert flags["is_vegetarian"] is vegetarian
    assert flags["is_vegan"] is vegan


def test_every_ingredient_has_a_known_role():
    assert {i.role for i in VOCABULARY.values()} <= {"bulk", "fat", "veg", "trace"}


# ── Nutrition ────────────────────────────────────────────────────────────────

REF = {
    name: {"kcal": 100.0, "protein": 10.0, "fat": 4.0, "carbs": 6.0}
    for name in (
        "chicken",
        "rice",
        "onion",
        "cooking oil",
        "wheat flour",
        "spinach",
        "butter",
        "sugar",
    )
}


def test_no_ingredients_means_no_estimate():
    assert estimate([], "desi_traditional", REF) is None


def test_estimate_splits_the_serving_by_role():
    est = estimate(["chicken", "onion", "cooking oil"], "desi_traditional", REF)
    # 400 g serving: 200 g bulk + 60 g fat + 60 g veg, all at 100 kcal / 100 g
    assert est["calories"] == pytest.approx(320.0)
    assert est["defaults_used"] == []


def test_a_vegetable_dish_is_not_padded_with_flour():
    est = estimate(["spinach"], "desi_traditional", REF)
    assert "wheat flour" not in est["defaults_used"]


def test_desserts_get_no_onion_default():
    est = estimate(["sugar"], "cafe_bakery", REF)
    assert "onion" not in est["defaults_used"]
    assert "butter" in est["defaults_used"]


def test_implausible_estimates_are_flagged():
    assert implausible({"calories": 3000, "protein_g": 10, "carbs_g": 10, "fat_g": 10})
    assert implausible({"calories": 500, "protein_g": 1, "carbs_g": 1, "fat_g": 1})
    assert implausible({"calories": 400, "protein_g": 25, "carbs_g": 40, "fat_g": 15.6}) == ""


def test_nutrition_confidence_levels():
    assert nutrition_confidence(None, "none") == "none"
    assert nutrition_confidence({"defaults_used": ["wheat flour"]}, "named ingredients") == "low"
    assert nutrition_confidence({"defaults_used": []}, "named ingredients") == "high"
    assert nutrition_confidence({"defaults_used": []}, "typical ingredients") == "medium"


# ── Prices ───────────────────────────────────────────────────────────────────


def test_reviewed_and_scraped_prices_are_trusted():
    assert prices.price_status(999, "human_confirmed", "", [])[0] == "trusted"
    assert prices.price_status(999, "scraped", "", [])[0] == "trusted"


@pytest.mark.parametrize(
    "price, line",
    [
        (1250, "CHICKEN KARAHI 1,250 RS"),
        (3699, "PORTO ALA BISTECCA 3.699 RS"),
        (3450, "Chicken Chillies & Vegetable 34507"),  # '3450/-' read as a trailing 7
    ],
)
def test_prices_found_in_their_ocr_line_are_verified(price, line):
    assert prices.price_status(price, "auto_imported", line, [])[0] == "verified"


def test_price_matching_an_ocr_candidate_is_verified():
    candidates = [{"price_pkr": None, "price_candidates": [1699.0, 3399.0]}]
    assert prices.price_status(3399, "auto_imported", "garbled", candidates)[0] == "verified"


def test_price_with_no_evidence_is_unverified_not_rejected():
    status, _ = prices.price_status(13490, "auto_imported", "MUTTON MANDI 4", [])
    assert status == "unverified"


def test_gross_price_errors():
    assert prices.gross_error(0, 500, "Naan") == "no price"
    assert prices.gross_error(8, 500, "Naan") == "price under Rs 20"
    assert prices.gross_error(78110, 1828, "Greek Olives")
    assert prices.gross_error(15999, 1450, "Shinwar Platter") == ""  # a platter may be expensive


def test_urdu_digits_are_not_read_as_a_price():
    assert prices.latin_numbers("Greek olives ۷8110") == []


# ── Servings ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, expected",
    [("2", (2, 2)), ("2-3", (2, 3)), ("3 to 2", (2, 3)), ("0", None), ("", None), ("lots", None)],
)
def test_parse_count(text, expected):
    assert servings.parse_count(text) == expected


def test_serving_precedence_owner_menu_double_price_default():
    typical = 500.0
    assert (
        servings.resolve("4", "Family Platter", "", "", 2000, typical)["serves_source"] == "owner"
    )
    assert servings.resolve("", "Platter (6-8 Persons)", "", "", 8800, typical)["serves_min"] == 6
    double = servings.resolve("", "Burrito (Double)", "", "", 1445, typical)
    assert (double["serves_source"], double["serves_min"], double["serves_max"]) == ("double", 2, 2)
    assert servings.resolve("1", "Burrito (Double)", "", "", 1445, typical)["serves_max"] == 1
    guess = servings.resolve("", "Mutton Mandi Full", "", "", 2000, typical)
    assert (guess["serves_source"], guess["serves_min"]) == ("price_estimate", 4)
    assert (
        servings.resolve("", "Chicken Karahi", "", "", 1200, typical)["serves_source"] == "default"
    )


@pytest.mark.parametrize(
    "address, area",
    [
        ("Howdy, اسٹریٹ 3, F-7/3, ایف-7, اسلام آباد", "F-7"),
        ("ایف-10, اسلام آباد, زون 1", "F-10"),
        ("Asian Wok, Mir Chakar Khan Road, آئ-8 مركز, آئی 8 مرکزگراؤنڈ", "I-8"),
        ("Khyber Shinwari, Street 54, جی-9/4, اسلام آباد", "G-9"),
        ("Tandoori, اسٹریٹ 30, ایف-10/1, ایف-10", "F-10"),
        ("Savour Foods, PTE Expert road, Blue Area, جی-7", "G-7"),
        ("wild wings, DHA Phase 2, ڈی ایچ اے فیز II, روات, زون ۵", "DHA"),
        ("Ginyaki, Phase 5, بحریہ ٹاؤن فیز 4, بحریہ ٹاؤن, زون ۵", "Bahria Town"),
        ("Des Pardes, اسٹریٹ 85, سید پور, زون ۳", "Saidpur"),
        ("Rawat Bazaar, روات, زون ۵", "Rawat"),
        ("Sakura Hotel & Restaurant, Chittagong Port Access Road", None),
    ],
)
def test_the_area_comes_from_the_address(address, area):
    assert area_name(address) == area


def test_locations_mark_sector_centres_and_coordinates_outside_the_city():
    def row(name, address, lat, lng):
        return {
            "restaurant_name": name,
            "restaurant_address": address,
            "restaurant_lat": lat,
            "restaurant_lng": lng,
        }

    got = restaurant_locations(
        [
            row("A", "A Grill, ایف-10, اسلام آباد", "33.6918", "73.0067"),
            row("B", "B Cafe, Street 1, ایف-10", "33.6918", "73.0067"),
            row("C", "C Grill, 10th Avenue, ایف-10", "33.6933", "73.0152"),
            row("D", "جی-9, اسلام آباد", "33.6914", "73.0307"),
            row("Sakura", "Sakura Hotel, Chittagong", "22.3156", "91.7877"),
            row("E", "", "", ""),
        ]
    )
    assert got["A"] == got["B"] == {"area": "F-10", "precision": "area"}  # one shared point
    assert got["C"] == {"area": "F-10", "precision": "place"}
    assert got["D"] == {"area": "G-9", "precision": "area"}  # the address is only the sector
    assert got["Sakura"] == got["E"] == {"area": None, "precision": "unknown"}


def test_neighbouring_dishes_on_an_ocr_line_do_not_make_a_dish_a_platter():
    bundle, _ = servings.serving_indicators(
        "Vegetable Rice", "", "Vegetable Rice 450 Whole Fish 2800"
    )
    assert bundle == []


def test_price_per_person_uses_the_middle_of_the_range():
    assert servings.price_per_person(3000, 2, 4) == 1000.0


# ── Identity and worksheet cells ─────────────────────────────────────────────


def test_dish_uid_is_stable_and_ignores_case_and_spacing():
    assert dish_uid("Terrazza", "Tom Yum Gai") == dish_uid(" terrazza ", "tom  yum gai")
    assert dish_uid("Terrazza", "Tom Yum Gai") != dish_uid("Terrazza", "Tom Yum Goong")


def test_excel_dates_and_numbers_read_back_as_serving_text():
    assert _cell_text(datetime(2026, 2, 3)) == "2-3"  # Excel turned '2-3' into 3 February
    assert _cell_text(2.0) == "2"
    assert _cell_text(None) == ""


def test_remove_in_the_platter_worksheet_is_a_removal_not_an_item_list(tmp_path, monkeypatch):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Platters & combos"
    ws.append(["SERVES — you fill", "INCLUDED ITEMS — you fill", "NOTES — you fill", KEY_COL])
    ws.append([None, "remove", None, "Habibi Restaurant | Zinger Meal"])
    ws.append([None, "Whole Roasted Chicken with Pulao", None, "Janaan | Chicken Roast Platter"])
    ws.append([None, None, None, "Janaan | Unanswered Platter"])
    ws.append([None, None, None, None])  # formatted but empty row below the list
    path = tmp_path / "platter.xlsx"
    wb.save(path)
    monkeypatch.setattr(paths, "PLATTER_REVIEW", path)

    answers, total = read_platter_answers()
    assert total == 3
    assert answers["Habibi Restaurant | Zinger Meal"] == {"remove": True}
    assert answers["Janaan | Chicken Roast Platter"]["items"] == "Whole Roasted Chicken with Pulao"
    assert "Janaan | Unanswered Platter" not in answers

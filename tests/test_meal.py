"""
Make it a meal (tier_1/meal.py): the pick, something to eat with it, something to drink.

The pairing rules are plain and pure, so most of this needs no database. The one thing worth
testing against the query itself is that a side cannot dodge the dietary rules the pick was
held to — a suggestion is served to the same person, so it is bound by the same exclusions.
"""

import pytest

from tier_1 import meal
from tier_1.symbolic_anchoring import PRUNE_CYPHER, SAFE_FOR_THE_USER


def side(name, price, category="add_ons"):
    return {
        "dish_id": name.lower().replace(" ", "-"),
        "name": name,
        "category": category,
        "price_pkr": float(price),
        "allergens": [],
    }


MENU = [
    side("Naan Plain", 40),
    side("Roghni Naan", 80),
    side("Fish Crackers", 480),
    side("Steamed Rice", 150),
    side("Mineral Water", 50, "beverages"),
    side("Fresh Peach Juice", 570, "beverages"),
]
KARAHI = {"name": "Chicken Karahi", "price_pkr": 1500.0, "restaurant_name": "Sufi"}
BURGER = {"name": "Zinger Burger", "price_pkr": 700.0, "restaurant_name": "Sufi"}


# ── What goes with what ──────────────────────────────────────────────────────
def test_a_dish_in_a_sauce_is_given_bread_and_told_why():
    bread = meal.to_eat_with(KARAHI, MENU)
    assert bread["name"] == "Naan Plain"  # the cheaper of the two breads
    assert "served in a sauce" in bread["why"]


def test_anything_else_takes_the_plainest_side_rather_than_the_cheapest_thing():
    """Fish crackers are cheaper than nothing, but they are not what a burger wants."""
    with_it = meal.to_eat_with(BURGER, MENU)
    assert with_it["name"] == "Steamed Rice"
    assert "plainest" in with_it["why"]


def test_a_kitchen_with_nothing_plain_is_left_alone():
    assert meal.to_eat_with(BURGER, [side("Fish Crackers", 480)]) is None
    assert meal.to_eat_with(KARAHI, []) is None


def test_the_drink_is_the_cheapest_ordinary_one_not_the_cheapest_thing_called_a_drink():
    drink = meal.to_drink(MENU)
    assert drink["name"] == "Mineral Water"
    only_juice = meal.to_drink([side("Fresh Peach Juice", 570, "beverages")])
    assert only_juice["name"] == "Fresh Peach Juice"
    assert meal.to_drink(MENU[:4]) is None


# ── What it comes to ─────────────────────────────────────────────────────────
def test_the_total_is_the_parts_added_up():
    made = meal.make_a_meal(KARAHI, MENU)
    assert [p["name"] for p in made["parts"]] == ["Naan Plain", "Mineral Water"]
    assert made["total_pkr"] == 1500 + 40 + 50


def test_a_table_is_told_what_it_comes_to_each():
    made = meal.make_a_meal(KARAHI, MENU, party_size=3)
    assert made["per_person_pkr"] == round(made["total_pkr"] / 3)


def test_a_meal_is_never_built_past_what_the_user_said_they_would_spend():
    # Rs 1,500 of karahi and a Rs 40 naan is 1,540, so the Rs 50 water is what has to go.
    made = meal.make_a_meal(KARAHI, MENU, ceiling=1560)
    assert [p["name"] for p in made["parts"]] == ["Naan Plain"]
    assert made["total_pkr"] == 1540

    nothing = meal.make_a_meal(KARAHI, MENU, ceiling=1510)
    assert nothing["parts"] == []
    assert "Rs 1,510" in nothing["note"]


def test_a_kitchen_with_nothing_else_on_its_menu_says_so():
    made = meal.make_a_meal(KARAHI, [])
    assert made["parts"] == []
    assert "don't list anything else" in made["note"]


# ── The same rules as the pick ───────────────────────────────────────────────
def test_the_safety_predicate_is_the_pick_s_own_not_a_copy_of_it():
    """
    One definition of what this person may be offered, used by both queries. A second copy is
    a second thing to keep in step, and the copy that falls behind serves someone nuts.
    """
    assert SAFE_FOR_THE_USER in PRUNE_CYPHER
    assert SAFE_FOR_THE_USER in meal.ALONGSIDE_CYPHER
    for rule in ("$pruned_list", "$req_vegan", "$req_veg", "$req_halal", "$excluded_ingredients"):
        assert rule in meal.ALONGSIDE_CYPHER, rule


def test_a_side_is_filtered_for_exactly_what_the_pick_was(monkeypatch):
    asked = {}

    class Driver:
        def execute_query(self, cypher, **params):
            asked.update(params)
            return [], None, None

    monkeypatch.setattr("accounts.store.get_driver", lambda: Driver())
    meal.alongside(
        "Sufi",
        "d1",
        {"excluded_ingredients": ["nuts", "beef"], "is_vegetarian": True, "is_halal": True},
    )
    assert "nuts" in asked["pruned_list"]
    assert "beef" in asked["excluded_ingredients"]
    assert asked["req_veg"] is True and asked["req_halal"] is True
    assert asked["restaurant"] == "Sufi" and asked["winner_id"] == "d1"


def test_a_menu_that_cannot_be_read_offers_nothing_rather_than_something(monkeypatch):
    class Broken:
        def execute_query(self, *a, **k):
            raise RuntimeError("neo4j is down")

    monkeypatch.setattr("accounts.store.get_driver", lambda: Broken())
    assert meal.alongside("Sufi", "d1", {}) == []


@pytest.mark.parametrize(
    "name, wants_bread",
    [
        ("Chicken Karahi", True),
        ("Mutton Qorma", True),
        ("Daal Chawal", True),
        ("Beef Nihari", True),
        ("Zinger Burger", False),
        ("Chicken Biryani", False),  # a rice dish is already its own plate
        ("Club Sandwich", False),
    ],
)
def test_which_dishes_read_as_wanting_bread(name, wants_bread):
    assert bool(meal.GRAVY.search(name)) is wants_bread

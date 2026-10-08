"""
A request as the things it asked for (tier_1/asks.py): what each dish meets, how close the near
misses are, and what the user's own rules rule out. Pure functions, no database.
"""

from tier_1 import asks


def ask(kind, key, words=None):
    return asks.Ask(f"{kind}:{key}" if kind != "budget" else "budget", kind, key, words or key)


def dish(name, **extra):
    return {"name": name, **extra}


def test_a_request_is_read_as_its_separate_asks():
    found = asks.asks_of(
        {
            "raw_input": "spicy chicken under 200",
            "budget_max_pkr": 200.0,
            "mood_vector": {"spice": 1.0},
            "preferred_category": "chicken",
        }
    )
    assert [(a.id, a.words) for a in found] == [
        ("budget", "Rs 200 or less"),
        ("taste:spice", "spicy"),
        ("food:chicken", "chicken"),
    ]


def test_an_ask_set_aside_is_no_longer_asked():
    found = asks.asks_of(
        {
            "raw_input": "spicy chicken karahi",
            "preferred_category": "karahi",
            "set_aside": ["dish:karahi"],
        }
    )
    assert "dish:karahi" not in {a.id for a in found}
    assert "food:chicken" in {a.id for a in found}


def test_rules_are_never_asks_so_nothing_can_trade_them_away():
    found = asks.asks_of(
        {
            "raw_input": "vegan halal no nuts",
            "is_vegan": True,
            "is_halal": True,
            "allergens_pruned": ["nuts"],
        }
    )
    assert found == []


def test_a_dish_that_names_the_food_meets_it_and_one_that_only_lists_it_comes_close():
    chicken = ask("food", "chicken")
    assert asks.degree(chicken, dish("Chicken Tikka")) == 1.0
    assert asks.degree(chicken, dish("Hot & Sour Soup", ingredients=["chicken"])) == 0.5
    assert asks.degree(chicken, dish("Pogaca", ingredients=["flour"])) == 0.0


def test_another_curry_stands_in_for_a_karahi_but_a_masala_fried_rice_does_not():
    karahi = ask("dish", "karahi")
    assert asks.degree(karahi, dish("Chicken Karahi")) == 1.0
    assert asks.degree(karahi, dish("Daal Maharani")) == 0.5
    assert asks.degree(karahi, dish("Chicken Hara Masala")) == 0.5
    assert asks.degree(karahi, dish("Masala Fried Rice")) == 0.0  # a rice dish
    assert asks.degree(karahi, dish("Masala Curly Fries")) == 0.0  # a snack


def test_a_flavour_is_met_at_the_strength_tier_1_filters_on():
    spicy = ask("taste", "spice", "spicy")
    assert asks.degree(spicy, dish("A", taste_profile={"spice": 0.5})) == 1.0
    assert asks.degree(spicy, dish("B", taste_profile={"spice": 0.25})) == 0.5
    assert asks.degree(spicy, dish("C", taste_profile={"spice": 0.0})) == 0.0


def test_closeness_leaves_the_limit_out_because_tier_1_already_enforced_it():
    wanted = [ask("budget", "200"), ask("food", "chicken"), ask("taste", "spice", "spicy")]
    soup = dish(
        "Hot & Sour Soup", price_pkr=195, ingredients=["chicken"], taste_profile={"spice": 0.6}
    )
    assert asks.closeness(wanted, soup) == 1.5
    assert [m["clause"] for m in asks.meets(wanted, soup)] == [
        "is spicy",
        "lists chicken among its ingredients",
    ]


def test_a_food_your_diet_forbids_is_a_conflict_and_the_diet_wins():
    found = asks.conflicts(
        {
            "raw_input": "vegan chicken karahi",
            "allergens_pruned": ["vegan"],
            "preferred_category": "karahi",
        }
    )
    assert found == [{"id": "food:chicken", "words": "chicken", "reason": "chicken isn't vegan"}]


def test_a_food_carrying_an_allergen_you_avoid_is_a_conflict():
    found = asks.conflicts(
        {"raw_input": "paneer tikka", "preferred_category": "paneer", "allergens_pruned": ["dairy"]}
    )
    assert found and "dairy" in found[0]["reason"]


def test_a_food_your_rules_allow_is_no_conflict():
    assert (
        asks.conflicts(
            {"raw_input": "chicken tikka", "preferred_category": "chicken", "is_halal": True}
        )
        == []
    )

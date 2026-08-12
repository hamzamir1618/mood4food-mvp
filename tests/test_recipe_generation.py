from tier_3.fulfillment_engine import RECIPES, get_recipe


def test_recipe_all_prices_available(monkeypatch):
    test_dish = "Test Dish 1"
    monkeypatch.setitem(
        RECIPES,
        test_dish,
        {
            "grocery_list": [
                {"item": "A", "qty": "1", "est_cost": 10},
                {"item": "B", "qty": "2", "est_cost": 20.5},
            ]
        },
    )
    recipe = get_recipe(test_dish)
    assert recipe["total_cost"] == 30.5
    assert recipe["grocery_list"][0]["est_cost"] == 10
    assert recipe["grocery_list"][1]["est_cost"] == 20.5


def test_recipe_missing_price(monkeypatch):
    test_dish = "Test Dish 2"
    monkeypatch.setitem(
        RECIPES,
        test_dish,
        {
            "grocery_list": [
                {"item": "A", "qty": "1", "est_cost": 10},
                {"item": "B", "qty": "2", "est_cost": None},
                {"item": "C", "qty": "3"},  # completely missing key
            ]
        },
    )
    recipe = get_recipe(test_dish)
    assert recipe["total_cost"] == 10
    assert recipe["grocery_list"][1]["est_cost"] == "price unavailable"
    assert recipe["grocery_list"][2]["est_cost"] == "price unavailable"


def test_recipe_empty_ingredient_list():
    # Test graceful fallback instead of ValueError
    recipe1 = get_recipe("Completely Unknown Dish", ingredients=[])
    assert recipe1["grocery_list"][0]["item"] == "Completely Unknown Dish"

    recipe2 = get_recipe("Another Unknown Dish", ingredients=None)
    assert recipe2["grocery_list"][0]["item"] == "Another Unknown Dish"

from tier_3.fulfillment_engine import MockRestaurantProvider, enrich_blueprint


def test_mock_restaurant_provider_returns_list():
    provider = MockRestaurantProvider()
    restaurants = provider.find_nearby("Dal Tadka")
    assert isinstance(restaurants, list)
    assert len(restaurants) >= 2
    for r in restaurants:
        assert r.name
        assert r.dish_available == "Dal Tadka"
        assert r.delivery_fee >= 0
        assert r.rating >= 0
        assert r.delivery_time


def test_enrich_blueprint():
    blueprint = {
        "winning_dish": {
            "name": "Chicken Karahi",
            "price_pkr": 300,
            "ingredients": ["Chicken", "Tomato"],
        }
    }
    enriched = enrich_blueprint(blueprint)
    assert "fulfillment" in enriched
    assert "recipe" in enriched["fulfillment"]
    assert enriched["fulfillment"]["recipe"]["source"] == "curated"
    assert "restaurants" in enriched["fulfillment"]
    assert len(enriched["fulfillment"]["restaurants"]) >= 2

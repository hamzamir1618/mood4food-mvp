from unittest.mock import patch

from fastapi.testclient import TestClient

from orchestrator import app

client = TestClient(app)


@patch("tier_1.symbolic_anchoring.run_anchoring_pipeline")
@patch("tier_1.multi_modal_ingestion.run_ingestion_pipeline")
def test_fulfillment_endpoint_e2e(mock_ingest, mock_query, monkeypatch):
    import fakeredis

    from tier_3.fulfillment_engine import RECIPES

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    monkeypatch.setitem(RECIPES, "First Dish", {"grocery_list": []})

    # 1. Without session/blueprint, /decision_blueprint should return 400
    res_no_session = client.get("/decision_blueprint")
    assert res_no_session.status_code == 400
    assert "No active decision blueprint found" in res_no_session.json()["detail"]

    # Mocking external pipeline steps
    mock_ingest.return_value = {
        "query_intent": "I want food",
        "hard_constraints": {"budget_max": 2000, "allergens": []},
        "soft_constraints": {"mood_vector_seed": "spicy", "direct_dish_prompt": ""},
    }

    mock_query.return_value = {
        "source_intent": mock_ingest.return_value,
        "safe_candidates": [
            {
                "dish_id": "dish1",
                "name": "First Dish",
                "price_pkr": 500,
                "category": "Main Course",
                "taste_profile": {
                    "sweet": 0.0,
                    "salty": 0.0,
                    "sour": 0.0,
                    "bitter": 0.0,
                    "umami": 0.0,
                    "spice": 1.0,
                },
                "protein_g": 30.0,
                "calories": 400.0,
                "allergens": [],
                "ingredients": ["Chicken", "Spices"],
            },
            {
                "dish_id": "dish2",
                "name": "Second Dish",
                "price_pkr": 600,
                "category": "Main Course",
                "taste_profile": {
                    "sweet": 0.0,
                    "salty": 0.0,
                    "sour": 0.0,
                    "bitter": 0.0,
                    "umami": 0.0,
                    "spice": 1.0,
                },
                "protein_g": 40.0,
                "calories": 500.0,
                "allergens": [],
                "ingredients": ["Beef", "Spices"],
            },
        ],
    }

    # 2. Trigger /submit
    res_submit = client.post("/submit", data={"query": "I want food"})
    assert res_submit.status_code == 200

    # 3. Trigger /recalculate
    # Heavily weight budget so First Dish (500) will definitely win over Second Dish (600)
    res_recalc = client.post(
        "/recalculate",
        json={"w_health": 0.0, "w_budget": 1.0, "w_taste": 0.0, "persona": "budget_saver"},
    )
    assert res_recalc.status_code == 200
    winner_recalc = res_recalc.json()["winning_dish"]["name"]

    # 4. Trigger /decision_blueprint (fulfillment endpoint)
    res_fulfillment = client.get("/decision_blueprint")
    assert res_fulfillment.status_code == 200

    fulfillment_json = res_fulfillment.json()
    winner_fulfill = fulfillment_json["winning_dish"]["name"]

    # 5. Assert fulfillment dish matches /recalculate winner
    assert winner_fulfill == winner_recalc
    assert winner_fulfill == "First Dish"

    # Also assert fulfillment data was enriched
    assert "fulfillment" in fulfillment_json
    assert "recipe" in fulfillment_json["fulfillment"]
    assert "restaurants" in fulfillment_json["fulfillment"]

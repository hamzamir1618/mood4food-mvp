from unittest.mock import patch

from fastapi.testclient import TestClient

from orchestrator import app

client = TestClient(app)


@patch("tier_1.symbolic_anchoring.query_safe_candidates")
@patch("tier_1.multi_modal_ingestion.run_ingestion_pipeline")
@patch("tier_3.fulfillment_engine.enrich_blueprint")
def test_neo4j_call_count_submit_vs_recalculate(mock_enrich, mock_ingest, mock_query, monkeypatch):
    import fakeredis

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    # Mocking external pipeline steps
    mock_ingest.return_value = {
        "query_intent": "I want spicy chicken",
        "hard_constraints": {"budget_max": 2000, "allergens": []},
        "soft_constraints": {"mood_vector_seed": "spicy", "direct_dish_prompt": ""},
    }

    # Mock Neo4j query returning a dummy candidate
    mock_query.return_value = [
        {
            "dish_id": "test_dish",
            "name": "Test Dish",
            "price_pkr": 500,
            "category": "Main Course",
            "image_url": "",
            "human_tags": [],
            "taste_profile": {
                "sweet": 0.0,
                "salty": 0.5,
                "sour": 0.0,
                "bitter": 0.0,
                "umami": 0.5,
                "spice": 1.0,
            },
            "protein_g": 30.0,
            "calories": 400.0,
            "allergens": [],
        }
    ]

    mock_enrich.side_effect = lambda x: x

    # 1. Trigger /submit
    res = client.post("/submit", data={"text": "I want something spicy"})
    assert res.status_code == 200

    # query_safe_candidates must be called exactly once during /submit
    assert mock_query.call_count == 1

    # Reset mock counter
    mock_query.reset_mock()

    # 2. Trigger /recalculate
    # TestClient maintains cookies automatically.

    # Send recalculate request
    res_recalc = client.post(
        "/recalculate",
        json={"w_health": 0.5, "w_budget": 0.3, "w_taste": 0.2, "persona": "budget_saver"},
    )
    assert res_recalc.status_code == 200

    # query_safe_candidates must be called EXACTLY ZERO times during /recalculate
    assert mock_query.call_count == 0

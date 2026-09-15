from unittest.mock import patch

import fakeredis
from fastapi.testclient import TestClient

from orchestrator import app

# We want to patch Redis to use FakeRedis so we don't need a real Redis server
fake_redis = fakeredis.FakeRedis(decode_responses=True)


def mock_ingestion(raw_input=None, audio_path=None, image_path=None):
    return {
        "query_intent": raw_input,
        "hard_constraints": {"budget_max_pkr": 1500, "allergens": []},
        "soft_constraints": {"mood_vector_seed": "spicy chicken", "direct_dish_prompt": "burger"},
    }


def is_neo4j_up():
    try:
        from neo4j import GraphDatabase

        from config import settings

        driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        driver.verify_connectivity()
        return True
    except Exception:
        return False


@patch("tier_1.contracts.session_store.get_redis", return_value=fake_redis)
@patch("tier_3.fulfillment_engine.get_redis", return_value=fake_redis)
@patch("tier_1.multi_modal_ingestion.run_ingestion_pipeline", side_effect=mock_ingestion)
def test_complete_real_data_flow(mock_ingestion, mock_redis_1, mock_redis_2):
    client = TestClient(app)

    # 1. Submit text query
    response = client.post("/submit", data={"text": "I want a spicy chicken burger"})
    assert response.status_code == 200, "Submit failed"
    submit_data = response.json()

    winning_dish = submit_data["winning_dish"]
    runners_up = submit_data.get("top_candidates", [])

    assert winning_dish is not None
    assert len(runners_up) > 0

    # Check that there is no fake rating in the payload
    assert "rating" not in winning_dish

    if "image_url" in winning_dish and winning_dish["image_url"]:
        assert isinstance(winning_dish["image_url"], str)

    # 2. Change persona/sliders
    # Session state is maintained automatically via TestClient's cookies
    recalc_resp = client.post("/recalculate", json={"persona": "frugal_student"})
    assert recalc_resp.status_code == 200, "Recalculate failed"
    recalc_data = recalc_resp.json()

    frugal_winner = recalc_data["winning_dish"]
    # The frugal persona ranks cheaper dishes higher
    assert frugal_winner["price_pkr"] <= winning_dish["price_pkr"]

    # 3. Request fulfillment
    lat, lng = 33.6844, 73.0479
    fulfill_resp = client.get(f"/decision_blueprint?lat={lat}&lon={lng}")
    assert fulfill_resp.status_code == 200, "Fulfillment failed"
    fulfill_data = fulfill_resp.json()

    assert "fulfillment" in fulfill_data
    assert "restaurants" in fulfill_data["fulfillment"]
    restaurants = fulfill_data["fulfillment"]["restaurants"]
    assert len(restaurants) > 0

    for rest in restaurants:
        assert "rating" not in rest or rest["rating"] is None, "Fabricated rating found!"
        assert "distance_km" in rest, "Distance was not computed!"
        assert rest["distance_km"] >= 0, "Distance should be >= 0"

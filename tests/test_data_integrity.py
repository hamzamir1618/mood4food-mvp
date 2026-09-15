import csv
import os
from unittest.mock import patch

import fakeredis
from fastapi.testclient import TestClient

from orchestrator import app

# We want to patch Redis to use FakeRedis so we don't need a real Redis server
# But we DO NOT patch Neo4j or the pipelines, so it hits the REAL database.
fake_redis = fakeredis.FakeRedis(decode_responses=True)

# Try to find the CSV file (could be running from tests/ or root)
csv_path = "handoff_output/mood4food_dishes.csv"
if not os.path.exists(csv_path):
    csv_path = "../handoff_output/mood4food_dishes.csv"


def get_valid_data():
    valid_dishes = set()
    valid_restaurants = set()
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            valid_dishes.add(row["dish_name"])
            valid_restaurants.add(row["restaurant_name"])
    return valid_dishes, valid_restaurants


VALID_DISHES, VALID_RESTAURANTS = get_valid_data()


@patch("tier_1.contracts.session_store.get_redis", return_value=fake_redis)
@patch("tier_3.fulfillment_engine.get_redis", return_value=fake_redis)
def test_data_integrity_against_real_db(mock_redis_2, mock_redis_1):
    client = TestClient(app)

    # A representative sample of queries hitting different agents and constraint branches
    queries = [
        "I want something cheap to eat",
        "Give me the highest protein meal",
        "I'm craving something really sweet and comforting",
        "A heavy dinner that is very spicy",
        "Something vegan",
    ]

    for q in queries:
        response = client.post("/submit", data={"text": q})
        assert response.status_code == 200, f"Query '{q}' failed: {response.text}"
        data = response.json()

        candidates = [data["winning_dish"]] + data.get("top_candidates", [])

        for cand in candidates:
            dish_name = cand["name"]
            # The candidates returned by the pipeline don't explicitly include restaurant_name
            # in the top level Candidate schema unless we fulfill, but let's check what we have.
            # Actually, the blueprint enrichment does give restaurants.

            # Assert dish name is valid
            assert dish_name in VALID_DISHES, (
                f"DATA INTEGRITY VIOLATION: Dish '{dish_name}' returned for query '{q}' "
                f"was NOT found in mood4food_dishes.csv. Is synthetic data leaking?"
            )

        # Fulfill to get restaurant data
        session_id = response.cookies.get("session_id")
        if session_id:
            fulfill_resp = client.get("/fulfill", cookies={"session_id": session_id})
            if fulfill_resp.status_code == 200:
                fulfill_data = fulfill_resp.json()
                if "fulfillment" in fulfill_data and "restaurants" in fulfill_data["fulfillment"]:
                    for rest in fulfill_data["fulfillment"]["restaurants"]:
                        rest_name = rest["name"]
                        assert rest_name in VALID_RESTAURANTS, (
                            f"DATA INTEGRITY VIOLATION: Restaurant '{rest_name}' "
                            f"was NOT found in mood4food_dishes.csv."
                        )

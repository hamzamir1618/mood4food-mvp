from unittest.mock import patch

import fakeredis
import pytest
from fastapi.testclient import TestClient
from neo4j import GraphDatabase

from config import settings
from orchestrator import app

fake_redis = fakeredis.FakeRedis(decode_responses=True)


def is_neo4j_up():
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        driver.verify_connectivity()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def client():
    with patch("tier_1.contracts.session_store.get_redis", return_value=fake_redis):
        yield TestClient(app)


@pytest.mark.skipif(not is_neo4j_up(), reason="Neo4j is required for real data tests")
def test_regression_response_bounds(client):
    res = client.post("/submit", data={"text": "I want food"})
    assert res.status_code == 200
    data = res.json()
    assert not data.get("all_candidate_scores"), (
        "Response should not expose all_candidate_scores (must be empty or absent)"
    )
    assert "top_candidates" in data
    assert len(data["top_candidates"]) <= 10, "Response must return a bounded runners-up list"


@pytest.mark.skipif(not is_neo4j_up(), reason="Neo4j is required for real data tests")
def test_regression_allergen_exclusion(client):
    res = client.post("/submit", data={"text": "no dairy"})
    assert res.status_code == 200
    data = res.json()

    winner = data.get("winning_dish")
    if winner:
        assert "dairy" not in [a.lower() for a in winner.get("allergens", [])]

    for cand in data.get("top_candidates", []):
        assert "dairy" not in [a.lower() for a in cand.get("allergens", [])]


@pytest.mark.skipif(not is_neo4j_up(), reason="Neo4j is required for real data tests")
def test_regression_vegan_request(client):
    res = client.post("/submit", data={"text": "I want something vegan"})
    assert res.status_code == 200
    data = res.json()

    dish_ids = []
    winner = data.get("winning_dish")
    if winner:
        dish_ids.append(winner["dish_id"])
    for cand in data.get("top_candidates", []):
        dish_ids.append(cand["dish_id"])

    assert len(dish_ids) > 0, "Should return at least some vegan dishes"

    driver = GraphDatabase.driver(
        settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    with driver.session() as session:
        result = session.run(
            "MATCH (d:Dish) WHERE toString(id(d)) IN $ids RETURN d.is_vegan AS is_vegan",
            ids=dish_ids,
        )
        for record in result:
            assert record["is_vegan"] is True, "Returned dish is not vegan!"


@pytest.mark.skipif(not is_neo4j_up(), reason="Neo4j is required for real data tests")
def test_regression_taste_sweet_winner(client):
    res = client.post("/submit", data={"text": "craving something sweet"})
    assert res.status_code == 200
    data = res.json()

    winner = data.get("winning_dish")
    assert winner is not None, "Should return a winner"
    sweet_score = winner.get("taste_profile", {}).get("sweet", 0.0)
    assert sweet_score >= 0.3, f"Winner must have taste_sweet >= 0.3, got {sweet_score}"


@pytest.mark.skipif(not is_neo4j_up(), reason="Neo4j is required for real data tests")
def test_regression_taste_vector_quality():
    driver = GraphDatabase.driver(
        settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    with driver.session() as session:
        total_res = session.run("MATCH (d:Dish) RETURN count(d) AS total")
        total = total_res.single()["total"]

        zero_res = session.run("""
        MATCH (d:Dish)
        WHERE (d.taste_sweet = 0.0 OR d.taste_sweet IS NULL)
          AND (d.taste_salty = 0.0 OR d.taste_salty IS NULL)
          AND (d.taste_sour = 0.0 OR d.taste_sour IS NULL)
          AND (d.taste_bitter = 0.0 OR d.taste_bitter IS NULL)
          AND (d.taste_umami = 0.0 OR d.taste_umami IS NULL)
          AND (d.taste_spice = 0.0 OR d.taste_spice IS NULL)
        RETURN count(d) AS zeroes
        """)
        zeros = zero_res.single()["zeroes"]

    assert total > 0, "Database is empty"
    percentage = (zeros / total) * 100
    assert percentage < 10.0, (
        f"Too many all-zero taste vectors: {percentage:.1f}% ({zeros}/{total})"
    )

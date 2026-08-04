from unittest import mock

import pytest
from neo4j import GraphDatabase

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:
    from testcontainers.neo4j import Neo4jContainer

import seed_neo4j
from tier_1.symbolic_anchoring import query_safe_candidates


@pytest.fixture(scope="module")
def neo4j_container():
    with Neo4jContainer("neo4j:5.12", username="neo4j", password="password1234") as neo4j:
        yield neo4j


@pytest.fixture(scope="module")
def seeded_neo4j(neo4j_container):
    uri = neo4j_container.get_connection_url()
    user = "neo4j"
    password = "password1234"
    auth = (user, password)

    driver = GraphDatabase.driver(uri, auth=auth)
    with driver.session() as session:
        session.execute_write(seed_neo4j.seed)
    driver.close()

    with (
        mock.patch("tier_1.symbolic_anchoring.NEO4J_URI", uri),
        mock.patch("tier_1.symbolic_anchoring.NEO4J_AUTH", auth),
    ):
        yield


def test_no_constraints(seeded_neo4j):
    # No allergens, very high budget -> Should return all 55 dishes
    candidates = query_safe_candidates(allergens=[], budget_max=100000)
    assert len(candidates) == 55


def test_budget_only_constraint(seeded_neo4j):
    # No allergens, tight budget -> Should return fewer than 55
    candidates = query_safe_candidates(allergens=[], budget_max=200)
    assert len(candidates) > 0
    assert len(candidates) < 55
    assert all(c["price_pkr"] <= 200 for c in candidates)


def test_allergen_only_constraint(seeded_neo4j):
    # Block chicken, high budget
    candidates = query_safe_candidates(allergens=["chicken"], budget_max=100000)
    assert len(candidates) > 0
    assert len(candidates) < 55

    chicken_dishes = [c for c in candidates if "chicken" in c["name"].lower()]
    assert len(chicken_dishes) == 0


def test_combined_constraint_zero_candidates(seeded_neo4j):
    # Block potato, tomato, onion, garlic, dairy, meat AND set budget very low
    candidates = query_safe_candidates(
        allergens=[
            "potato",
            "tomato",
            "onion",
            "garlic",
            "dairy",
            "meat",
            "fish",
            "chicken",
            "beef",
            "mutton",
            "lentils",
            "rice",
            "wheat",
            "flour",
        ],
        budget_max=10,
    )
    assert len(candidates) == 0

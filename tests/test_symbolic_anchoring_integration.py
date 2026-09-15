import json
from unittest import mock

import pytest
from neo4j import GraphDatabase

try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:
    from testcontainers.neo4j import Neo4jContainer


from tier_1.symbolic_anchoring import query_safe_candidates


def _parse_allergens(raw):
    """Mirror the Dish schema's allergen validator: '' -> [], JSON list -> list.

    The production Cypher reads the flat d.allergens property. An absent property
    is NOT the same as an empty one: an empty list means 'known to contain no
    excluded allergen', while NULL means 'we do not know', and a dish we know
    nothing about must not be served to someone who excluded an allergen.
    """
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [raw]
    except (ValueError, TypeError):
        return [raw]


@pytest.fixture(scope="module")
def neo4j_container():
    with Neo4jContainer("neo4j:2026.07.1", username="neo4j", password="password1234") as neo4j:
        yield neo4j


@pytest.fixture(scope="module")
def seeded_neo4j(neo4j_container):
    uri = neo4j_container.get_connection_url()
    user = "neo4j"
    password = "password1234"
    auth = (user, password)

    driver = GraphDatabase.driver(uri, auth=auth)
    with driver.session() as session:
        # Custom fixture seeder for tests
        fixtures = [
            {
                "restaurant_name": "Najeeb Spot",
                "restaurant_address": "\u0622\u0626\u06cc 8 \u0645\u0631\u06a9\u0632\u06af\u0631\u0627\u0624\u0646\u0688, \u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f, \u0632\u0648\u0646 1, \u0648\u0641\u0627\u0642\u06cc \u062f\u0627\u0631\u0627\u0644\u062d\u06a9\u0648\u0645\u062a \u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f, 44000, \u067e\u0627\u06a9\u0633\u062a\u0627\u0646",
                "restaurant_lat": "33.6688574",
                "restaurant_lng": "73.0729600",
                "dish_name": "Afghan Single Chicken Tikka Burger",
                "price_rs": "330.0",
                "source": "https://www.google.com/maps/search/Najeeb+Gourmet+I8+Islamabad+menu+photos",
                "source_date": "2026-08-23T16:26:07.650364Z",
                "category": "fast_food",
                "protein_g": "34.3",
                "calories": "491.7",
                "allergens": "",
                "taste_sweet": "0.0",
                "taste_salty": "0.5",
                "taste_sour": "0.0",
                "taste_bitter": "0.0",
                "taste_umami": "0.7",
                "taste_spice": "0.5",
            },
            {
                "restaurant_name": "Yum Chinese & Thai",
                "restaurant_address": "Yum Chinese & Thai, \u0627\u0633\u0679\u0631\u06cc\u0679 16, F-7/2, \u0627\u06cc\u0641-7, \u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f, \u0632\u0648\u0646 1, \u0648\u0641\u0627\u0642\u06cc \u062f\u0627\u0631\u0627\u0644\u062d\u06a9\u0648\u0645\u062a \u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f, 44000, \u067e\u0627\u06a9\u0633\u062a\u0627\u0646",
                "restaurant_lat": "33.7215553",
                "restaurant_lng": "73.0508982",
                "dish_name": "Spicy & Sour Chicken Tom Yum Gai",
                "price_rs": "1075.0",
                "source": "https://www.google.com/maps/search/Yum+Chinese+and+Thai+F7+Islamabad+menu+photos",
                "source_date": "2026-08-23T16:39:58.407511Z",
                "category": "chinese_asian",
                "protein_g": "60.0",
                "calories": "860.5",
                "allergens": "",
                "taste_sweet": "0.0",
                "taste_salty": "0.0",
                "taste_sour": "0.8",
                "taste_bitter": "0.0",
                "taste_umami": "0.6",
                "taste_spice": "0.8",
            },
            {
                "restaurant_name": "Brim Burgers",
                "restaurant_address": "BRIM - Big Juicy Burgers, Mir Chakar Khan Road, \u0622\u0626-8 \u0645\u0631\u0643\u0632, \u0622\u0626\u06cc 8 \u0645\u0631\u06a9\u0632\u06af\u0631\u0627\u0624\u0646\u0688, \u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f, \u0632\u0648\u0646 1, \u0648\u0641\u0627\u0642\u06cc \u062f\u0627\u0631\u0627\u0644\u062d\u06a9\u0648\u0645\u062a \u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f, 44000, \u067e\u0627\u06a9\u0633\u062a\u0627\u0646",
                "restaurant_lat": "33.6690923",
                "restaurant_lng": "73.0776054",
                "dish_name": "Cheese Sauce",
                "price_rs": "95.0",
                "source": "https://www.google.com/maps/search/Brim+Burgers+F11+Islamabad+menu+photos",
                "source_date": "2026-08-24T15:35:59.814520Z",
                "category": "other",
                "protein_g": "19.1",
                "calories": "551.0",
                "allergens": '["dairy"]',
                "taste_sweet": "0.0",
                "taste_salty": "0.3",
                "taste_sour": "0.0",
                "taste_bitter": "0.0",
                "taste_umami": "0.5",
                "taste_spice": "0.0",
            },
            {
                "restaurant_name": "Sufi Restaurant",
                "restaurant_address": "Sufi Restaurant, 10th Avenue, \u0627\u06cc\u0641-10, \u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f, \u0632\u0648\u0646 1, \u0648\u0641\u0627\u0642\u06cc \u062f\u0627\u0631\u0627\u0644\u062d\u06a9\u0648\u0645\u062a \u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f, 44000, \u067e\u0627\u06a9\u0633\u062a\u0627\u0646",
                "restaurant_lat": "33.6933190",
                "restaurant_lng": "73.0151834",
                "dish_name": "Chocolate (Small)",
                "price_rs": "180.0",
                "source": "https://www.google.com/maps/search/Sufi+Restaurant+G9+Islamabad+menu+photos",
                "source_date": "2026-08-23T16:30:01.274179Z",
                "category": "cafe_bakery",
                "protein_g": "8.5",
                "calories": "622.3",
                "allergens": '["dairy"]',
                "taste_sweet": "0.9",
                "taste_salty": "0.0",
                "taste_sour": "0.0",
                "taste_bitter": "0.2",
                "taste_umami": "0.0",
                "taste_spice": "0.0",
            },
            {
                "restaurant_name": "Bazaar",
                "restaurant_address": "Rawat Bazaar, \u0631\u0648\u0627\u062a, \u0632\u0648\u0646 \u06f5, \u0648\u0641\u0627\u0642\u06cc \u062f\u0627\u0631\u0627\u0644\u062d\u06a9\u0648\u0645\u062a \u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f, \u067e\u0627\u06a9\u0633\u062a\u0627\u0646",
                "restaurant_lat": "33.4958476",
                "restaurant_lng": "73.1960526",
                "dish_name": "Roghni Naan",
                "price_rs": "55.0",
                "source": "https://www.google.com/maps/search/BBQ+Bazaar+F7+Islamabad+menu+photos",
                "source_date": "2026-08-24T14:11:49.696498Z",
                "category": "other",
                "protein_g": "17.9",
                "calories": "778.4",
                "allergens": '["gluten"]',
                "taste_sweet": "0.0",
                "taste_salty": "0.0",
                "taste_sour": "0.0",
                "taste_bitter": "0.0",
                "taste_umami": "0.0",
                "taste_spice": "0.0",
            },
        ]
        for data in fixtures:
            session.run(
                """
                MERGE (r:Restaurant {name: $restaurant_name})
                MERGE (d:Dish {name: $dish_name, restaurant_name: $restaurant_name})
                SET d.price_rs = $price_rs,
                    d.category = $category,
                    d.allergens = $allergens,
                    d.calories = $calories,
                    d.protein_g = $protein_g,
                    d.taste_sweet = $taste_sweet,
                    d.taste_salty = $taste_salty,
                    d.taste_sour = $taste_sour,
                    d.taste_bitter = $taste_bitter,
                    d.taste_umami = $taste_umami,
                    d.taste_spice = $taste_spice
                MERGE (r)-[:SERVES]->(d)
                """,
                restaurant_name=data["restaurant_name"],
                dish_name=data["dish_name"],
                price_rs=float(data["price_rs"]),
                category=data["category"],
                allergens=_parse_allergens(data.get("allergens", "")),
                calories=float(data["calories"]),
                protein_g=float(data["protein_g"]),
                taste_sweet=float(data["taste_sweet"]),
                taste_salty=float(data["taste_salty"]),
                taste_sour=float(data["taste_sour"]),
                taste_bitter=float(data["taste_bitter"]),
                taste_umami=float(data["taste_umami"]),
                taste_spice=float(data["taste_spice"]),
            )
            # NOTE: this fixture used to also create (:Ingredient) nodes joined by
            # [:CONTAINS]. The production query abandoned that traversal because
            # Ingredient nodes were never populated by real seeding, so seeding them
            # here made the fixture diverge from the database it is meant to model.
    driver.close()

    with (
        mock.patch("tier_1.symbolic_anchoring.NEO4J_URI", uri),
        mock.patch("tier_1.symbolic_anchoring.NEO4J_AUTH", auth),
    ):
        yield


def test_no_constraints(seeded_neo4j):
    # No allergens, very high budget -> Should return all 55 dishes
    candidates = query_safe_candidates(allergens=[], budget_max=100000)
    assert len(candidates) == 5


def test_budget_only_constraint(seeded_neo4j):
    # No allergens, tight budget -> Should return fewer than 55
    candidates = query_safe_candidates(allergens=[], budget_max=200)
    assert len(candidates) > 0
    assert len(candidates) < 5
    assert all(c["price_pkr"] <= 200 for c in candidates)


def test_allergen_only_constraint(seeded_neo4j):
    # Block chicken, high budget
    candidates = query_safe_candidates(allergens=["dairy"], budget_max=100000)
    assert len(candidates) > 0
    assert len(candidates) < 5

    dairy_dishes = [c for c in candidates if "chocolate" in c["name"].lower()]
    assert len(dairy_dishes) == 0


def test_dish_with_unknown_allergens_is_excluded_when_an_allergen_is_named(seeded_neo4j):
    """
    A dish whose allergen data is missing entirely must not be offered to someone
    who excluded an allergen — 'we don't know' is not 'it's safe'.

    Regression guard: the clause previously read `none(a IN d.allergens ...)`,
    and because none() over NULL yields NULL rather than true, such dishes were
    dropped from *every* query instead of only allergen-constrained ones.
    """
    from neo4j import GraphDatabase

    from tier_1.symbolic_anchoring import NEO4J_AUTH, NEO4J_URI

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    try:
        with driver.session() as session:
            session.run(
                "CREATE (d:Dish {name: '__unknown_allergens__', price_rs: 100.0, "
                "category: 'other', calories: 100.0, protein_g: 5.0})"
            )
        try:
            # With no allergen excluded, the dish is visible.
            unconstrained = query_safe_candidates(allergens=[], budget_max=100000)
            assert any(c["name"] == "__unknown_allergens__" for c in unconstrained)

            # With an allergen excluded, unknown data is treated as unsafe.
            constrained = query_safe_candidates(allergens=["dairy"], budget_max=100000)
            assert not any(c["name"] == "__unknown_allergens__" for c in constrained)
        finally:
            with driver.session() as session:
                session.run("MATCH (d:Dish {name: '__unknown_allergens__'}) DELETE d")
    finally:
        driver.close()


def test_quarantine_halal_ingredients_and_stable_ids(seeded_neo4j):
    """
    Phase 1 data reaches Tier 1: quarantined dishes (gross price errors, names the
    owner discarded) are never offered; a halal-only request excludes dishes that
    name pork or alcohol; each candidate carries its ingredients; and dish_uid is
    used as the dish id, because Neo4j's internal ids change on every re-seed.
    """
    from neo4j import GraphDatabase

    from tier_1.symbolic_anchoring import NEO4J_AUTH, NEO4J_URI

    probes = [
        {"name": "__quarantined__", "quarantined": True, "is_halal": True},
        {"name": "__not_halal__", "quarantined": False, "is_halal": False},
    ]
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    try:
        with driver.session() as session:
            for p in probes:
                session.run(
                    "CREATE (d:Dish {name: $name, dish_uid: $name, price_rs: 100.0, category: 'other', "
                    "calories: 100.0, protein_g: 5.0, allergens: [], ingredients: ['chicken'], "
                    "quarantined: $quarantined, is_halal: $is_halal})",
                    **p,
                )
        try:
            everything = {
                c["name"]: c for c in query_safe_candidates(allergens=[], budget_max=100000)
            }
            assert "__quarantined__" not in everything
            assert "__not_halal__" in everything
            assert everything["__not_halal__"]["ingredients"] == ["chicken"]
            assert everything["__not_halal__"]["dish_id"] == "__not_halal__"

            halal_only = {
                c["name"]
                for c in query_safe_candidates(allergens=[], budget_max=100000, is_halal=True)
            }
            assert "__not_halal__" not in halal_only
        finally:
            with driver.session() as session:
                session.run(
                    "MATCH (d:Dish) WHERE d.name IN ['__quarantined__', '__not_halal__'] DELETE d"
                )
    finally:
        driver.close()


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

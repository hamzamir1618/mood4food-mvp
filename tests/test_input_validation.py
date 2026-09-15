import pytest
from fastapi.testclient import TestClient
from neo4j import GraphDatabase

from orchestrator import app

client = TestClient(app)


def test_empty_string():
    response = client.post("/submit", data={"text": "   "})
    assert response.status_code == 400
    assert "Provide exactly one of" in response.json()["detail"]


def test_long_string():
    response = client.post("/submit", data={"text": "a" * 10000})
    assert response.status_code == 400
    assert "exceeds 500 characters" in response.json()["detail"]


try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:
    from testcontainers.neo4j import Neo4jContainer
# noqa: E402


@pytest.fixture(scope="module")
def neo4j_container():
    with Neo4jContainer("neo4j:2026.07.1", username="neo4j", password="password1234") as neo4j:
        yield neo4j


@pytest.fixture(scope="module")
def seeded_neo4j(neo4j_container):
    uri = neo4j_container.get_connection_url()
    auth = ("neo4j", "password1234")

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
                calories=float(data["calories"]),
                protein_g=float(data["protein_g"]),
                taste_sweet=float(data["taste_sweet"]),
                taste_salty=float(data["taste_salty"]),
                taste_sour=float(data["taste_sour"]),
                taste_bitter=float(data["taste_bitter"]),
                taste_umami=float(data["taste_umami"]),
                taste_spice=float(data["taste_spice"]),
            )
            # Add some ingredients
            session.run(
                """
                MATCH (d:Dish {name: $dish_name})
                MERGE (i:Ingredient {name: 'Chicken'})
                MERGE (d)-[:CONTAINS]->(i)
            """,
                dish_name=data["dish_name"],
            )
    driver.close()
    yield uri, auth


def test_cypher_injection(seeded_neo4j, monkeypatch):
    uri, auth = seeded_neo4j
    monkeypatch.setattr("tier_1.symbolic_anchoring.NEO4J_URI", uri)
    monkeypatch.setattr("tier_1.symbolic_anchoring.NEO4J_AUTH", auth)
    # also patch settings so orchestrator health check doesn't fail
    monkeypatch.setattr("config.settings.NEO4J_URI", uri)
    monkeypatch.setattr("config.settings.NEO4J_USER", auth[0])
    monkeypatch.setattr("config.settings.NEO4J_PASSWORD", auth[1])

    import fakeredis

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    # Mock enrich_blueprint because we don't care about fulfillment in this test
    # and the seeded Neo4j mock might not have ingredients for all candidates
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda bp: bp)

    # This should pass validation, hit the graph query, and not delete anything
    response = client.post("/submit", data={"text": "'; MATCH (n) DETACH DELETE n; --"})
    assert response.status_code == 200

    # Verify DB count
    driver = GraphDatabase.driver(uri, auth=auth)
    with driver.session() as session:
        result = session.run("MATCH (d:Dish) RETURN count(d) as c")
        count = result.single()["c"]
    driver.close()
    assert count == 5


def test_oversized_audio_file():
    # 11 MB dummy file
    file_content = b"0" * (11 * 1024 * 1024)
    response = client.post("/submit", files={"audio": ("large.mp3", file_content, "audio/mpeg")})
    assert response.status_code == 413
    assert "10MB limit" in response.json()["detail"]


def test_oversized_image_file():
    # 11 MB dummy file
    file_content = b"0" * (11 * 1024 * 1024)
    response = client.post("/submit", files={"image": ("large.jpg", file_content, "image/jpeg")})
    assert response.status_code == 413
    assert "10MB limit" in response.json()["detail"]


def test_invalid_extension():
    response = client.post("/submit", files={"image": ("test.txt", b"dummy", "text/plain")})
    assert response.status_code == 400
    assert "Unsupported image extension" in response.json()["detail"]

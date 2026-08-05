import pytest
from fastapi.testclient import TestClient
from neo4j import GraphDatabase

from orchestrator import app

client = TestClient(app)


def test_empty_string():
    response = client.post("/submit", data={"query": "   "})
    assert response.status_code == 400
    assert "non-empty text" in response.json()["detail"]


def test_long_string():
    response = client.post("/submit", data={"query": "a" * 10000})
    assert response.status_code == 400
    assert "exceeds 500 characters" in response.json()["detail"]


try:
    from testcontainers.community.neo4j import Neo4jContainer
except ImportError:
    from testcontainers.neo4j import Neo4jContainer
import seed_neo4j  # noqa: E402


@pytest.fixture(scope="module")
def neo4j_container():
    with Neo4jContainer("neo4j:5.12", username="neo4j", password="password1234") as neo4j:
        yield neo4j


@pytest.fixture(scope="module")
def seeded_neo4j(neo4j_container):
    uri = neo4j_container.get_connection_url()
    auth = ("neo4j", "password1234")

    driver = GraphDatabase.driver(uri, auth=auth)
    with driver.session() as session:
        session.execute_write(seed_neo4j.seed)
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
    response = client.post("/submit", data={"query": "'; MATCH (n) DETACH DELETE n; --"})
    assert response.status_code == 200

    # Verify DB count
    driver = GraphDatabase.driver(uri, auth=auth)
    with driver.session() as session:
        result = session.run("MATCH (d:Dish) RETURN count(d) as c")
        count = result.single()["c"]
    driver.close()
    assert count == 55


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

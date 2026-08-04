from fastapi.testclient import TestClient

from orchestrator import app


def test_app_is_not_none():
    assert app is not None


def test_health_endpoint(monkeypatch):
    import fakeredis

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    from unittest.mock import MagicMock

    mock_driver = MagicMock()
    monkeypatch.setattr("neo4j.GraphDatabase.driver", lambda *args, **kwargs: mock_driver)

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "neo4j": "ok", "redis": "ok"}


def test_health_endpoint_neo4j_down(monkeypatch):
    import fakeredis

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    import neo4j

    def mock_graph_database_driver(*args, **kwargs):
        raise neo4j.exceptions.ServiceUnavailable("Fake connection error")

    monkeypatch.setattr("neo4j.GraphDatabase.driver", mock_graph_database_driver)

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "neo4j": "unreachable", "redis": "ok"}


def test_session_isolation():
    client1 = TestClient(app)
    client2 = TestClient(app)

    client1.get("/health")
    client2.get("/health")

    assert "session" in client1.cookies
    assert "session" in client2.cookies
    assert client1.cookies["session"] != client2.cookies["session"]

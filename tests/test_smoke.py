from fastapi.testclient import TestClient

from orchestrator import app


def test_app_is_not_none():
    assert app is not None


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_session_isolation():
    client1 = TestClient(app)
    client2 = TestClient(app)

    client1.get("/health")
    client2.get("/health")

    assert "session" in client1.cookies
    assert "session" in client2.cookies
    assert client1.cookies["session"] != client2.cookies["session"]

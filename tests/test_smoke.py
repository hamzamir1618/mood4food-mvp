from fastapi.testclient import TestClient

from orchestrator import app


def test_app_is_not_none():
    assert app is not None


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

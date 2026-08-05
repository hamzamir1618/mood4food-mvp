from fastapi.testclient import TestClient

from api.rate_limit import limiter
from orchestrator import app

client = TestClient(app)


def test_rate_limiting_429(monkeypatch):
    # Reset limits to ensure a clean slate before this test
    limiter.reset()

    # We need to bypass the session and Neo4j for a fast test.
    # We will mock `load_contract` to return a dummy blueprint to satisfy `/recalculate`.
    def mock_load_contract(*args, **kwargs):
        return {
            "safe_candidates": [],
            "source_intent": {"budget_max_pkr": 1000},
            "soft_constraints": {},
            "message": "",
        }

    def mock_save_contract(*args, **kwargs):
        pass

    def mock_enrich_blueprint(blueprint):
        return blueprint

    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", mock_load_contract)
    monkeypatch.setattr("tier_1.contracts.session_store.save_contract", mock_save_contract)
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", mock_enrich_blueprint)

    payload = {"w_health": 0.5, "w_budget": 0.3, "w_taste": 0.2, "persona": "gym_bro"}

    # Fire 20 successful requests
    for i in range(20):
        response = client.post("/recalculate", json=payload)
        assert response.status_code == 200, (
            f"Request {i + 1} failed unexpectedly with status {response.status_code}"
        )

    # The 21st request should hit the 20/minute rate limit
    response = client.post("/recalculate", json=payload)
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["error"]

import fakeredis
import pytest
from fastapi.testclient import TestClient

from config import settings
from orchestrator import app


@pytest.fixture(autouse=True)
def setup_redis(monkeypatch):
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)


@pytest.mark.skipif(not settings.GROQ_API_KEY, reason="GROQ_API_KEY is not set")
def test_dairy_safety_net():
    client = TestClient(app)

    response = client.post("/submit", data={"text": "something with dairy"})
    assert response.status_code == 200
    data = response.json()

    winner_name = data.get("winning_dish", {}).get("name", "").lower()
    utility = data.get("utility_breakdown", {})
    u_taste = utility.get("u_taste")

    print(f"\nWINNER: {winner_name}")
    print(f"UTILITY TASTE: {u_taste}")

    # A dairy request is a Tier 1 filter now (dishes whose allergens include dairy), so
    # no score is forced outside [0, 1] to make a dairy dish win.
    assert u_taste is None or 0.0 <= u_taste <= 1.0, f"u_taste out of range: {u_taste}"

    allergens = data.get("winning_dish", {}).get("allergens") or []
    assert "dairy" in allergens, f"Winner '{winner_name}' ({allergens}) is not a dairy dish!"

    failing_dish = "afghan single chicken tikka burger"
    assert winner_name != failing_dish, "The fallback dish won instead of a semantic match!"

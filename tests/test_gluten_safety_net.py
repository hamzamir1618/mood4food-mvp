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
def test_no_bread_safety_net():
    client = TestClient(app)

    response = client.post("/submit", data={"text": "something with no bread"})
    assert response.status_code == 200
    data = response.json()
    winner_name = data.get("winning_dish", {}).get("name", "").lower()

    alt_res = client.post("/alternate")
    alt_data = alt_res.json()
    alt_name = alt_data.get("alternate_dish", {}).get("name", "").lower()

    if not alt_name:
        alt_name = alt_data.get("name", "").lower()

    if not winner_name:
        winner_name = data.get("name", "").lower()

    print(f"\nWINNER: {winner_name.encode('utf-8')}")
    print(f"ALT: {alt_name.encode('utf-8')}")

    forbidden_keywords = ["burger", "pizza", "pasta", "bread", "wrap", "roll"]

    for kw in forbidden_keywords:
        assert kw not in winner_name, f"Forbidden keyword '{kw}' found in winner: {winner_name}"
        if alt_name:
            assert kw not in alt_name, f"Forbidden keyword '{kw}' found in alternate: {alt_name}"

    failing_dish = "afghan single chicken tikka burger"
    assert winner_name != failing_dish
    assert alt_name != failing_dish

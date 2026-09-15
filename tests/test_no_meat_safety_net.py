import fakeredis
import pytest
from fastapi.testclient import TestClient

from config import settings
from orchestrator import app
from tier_1.groq_extractor import GroqExtractorImpl


@pytest.fixture(autouse=True)
def setup_redis(monkeypatch):
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)


@pytest.mark.skipif(not settings.GROQ_API_KEY, reason="GROQ_API_KEY is not set")
def test_no_meat_safety_net():
    client = TestClient(app)
    response = client.post("/submit", data={"text": "no meat, lots of vegetables"})
    assert response.status_code == 200
    data = response.json()

    # 1. Check intent via decision blueprint source context
    # (FastAPI orchestrator doesn't expose the intent directly in response,
    # but we can get it from session store or test GroqExtractor separately)
    extractor = GroqExtractorImpl()
    intent = extractor.extract("no meat, lots of vegetables")
    assert intent.is_vegetarian is True, "LLM failed to set is_vegetarian=true for 'no meat'"

    winner_name = data.get("winning_dish", {}).get("name", "").lower()

    alt_res = client.post("/alternate")
    alt_data = alt_res.json()
    alt_name = alt_data.get("alternate_dish", {}).get("name", "").lower()
    if not alt_name:
        alt_name = alt_data.get("name", "").lower()
    if not winner_name:
        winner_name = data.get("name", "").lower()

    print(f"\nWINNER: {winner_name}")
    print(f"ALT: {alt_name}")

    forbidden_keywords = ["shrimp", "seafood", "squid", "calamari", "lamb"]
    for kw in forbidden_keywords:
        assert kw not in winner_name, f"Forbidden keyword '{kw}' found in winner: {winner_name}"
        if alt_name:
            assert kw not in alt_name, f"Forbidden keyword '{kw}' found in alternate: {alt_name}"

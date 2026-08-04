import fakeredis

import tier_1.contracts.session_store as ss
from tier_1.contracts.session_store import load_contract, save_contract


def test_save_and_load_contract(monkeypatch):
    """
    Tests saving and loading a contract to/from Redis.
    Uses fakeredis to avoid needing a live Redis instance.
    """
    # Patch get_redis to return a FakeRedis instance
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(ss, "get_redis", lambda: fake_redis)

    session_id = "test-session-123"
    contract_name = "grounded_intent"
    data = {"budget_max_pkr": 1000, "allergens_pruned": ["dairy"]}

    # Ensure it's empty first
    assert load_contract(session_id, contract_name) is None

    # Save
    save_contract(session_id, contract_name, data)

    # Load
    loaded = load_contract(session_id, contract_name)
    assert loaded == data

    # Verify TTL (should be set to 900 seconds)
    ttl = fake_redis.ttl(f"{session_id}:{contract_name}")
    assert 0 < ttl <= 900

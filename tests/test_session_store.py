import fakeredis

import tier_1.contracts.session_store as ss
from tier_1.contracts.schemas import GroundedIntent
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
    data = GroundedIntent(budget_max_pkr=1000, allergens_pruned=["dairy"])

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


def test_submit_session_isolation(monkeypatch):
    """
    Simulates two distinct browsers hitting /submit with different queries,
    verifying their contracts are saved under distinct session keys in Redis.
    """
    import json

    from fastapi.testclient import TestClient

    from orchestrator import DECISION_BLUEPRINT_PATH, app

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(ss, "get_redis", lambda: fake_redis)

    # Mock the pipelines to avoid needing live Neo4j / LLMs
    def mock_ingest(raw_input, *args, **kwargs):
        return {"query_intent": raw_input}

    def mock_anchor(*args, **kwargs):
        return {"safe_candidates": [{"name": "fake candidate"}]}

    def mock_debate(session_id, *args, **kwargs):
        from tier_1.contracts.session_store import save_contract

        save_contract(session_id, "decision_blueprint", {"winning_dish": {"name": "dummy"}})
        return {}

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", mock_ingest)
    monkeypatch.setattr("tier_1.symbolic_anchoring.run_anchoring_pipeline", mock_anchor)
    monkeypatch.setattr("tier_2.consensus_manager.run_debate_pipeline", mock_debate)
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda x: x)

    # Ensure the dummy blueprint file exists so orchestrator doesn't crash reading it
    DECISION_BLUEPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISION_BLUEPRINT_PATH, "w", encoding="utf-8") as f:
        json.dump({"winning_dish": {"name": "dummy"}}, f)

    client1 = TestClient(app)
    client2 = TestClient(app)

    res1 = client1.post("/submit", data={"query": "I want pizza"})
    res2 = client2.post("/submit", data={"query": "I want salad"})

    assert res1.status_code == 200
    assert res2.status_code == 200

    # The session_id comes from Starlette SessionMiddleware's internal tracking
    # but we can look directly inside fakeredis to find the keys since the
    # test_save_and_load_contract asserts redis works.

    # Let's extract the session IDs from the cookies by decoding them?
    # No need, we can just inspect FakeRedis keys.
    keys = fake_redis.keys("*")

    # We expect 2 session IDs, each with 3 contracts
    assert len(keys) == 6

    pizza_intents = [
        k
        for k in keys
        if "grounded_intent" in k
        and json.loads(fake_redis.get(k)).get("query_intent") == "I want pizza"
    ]
    salad_intents = [
        k
        for k in keys
        if "grounded_intent" in k
        and json.loads(fake_redis.get(k)).get("query_intent") == "I want salad"
    ]

    assert len(pizza_intents) == 1
    assert len(salad_intents) == 1

    # Ensure they have different session prefixes
    pizza_session_id = pizza_intents[0].split(":")[0]
    salad_session_id = salad_intents[0].split(":")[0]

    assert pizza_session_id != salad_session_id
    assert pizza_session_id != ""
    assert salad_session_id != ""


def test_recalculate_no_session_400(monkeypatch):
    import fakeredis

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    from fastapi.testclient import TestClient

    from orchestrator import app

    client = TestClient(app)
    # Never called /submit
    res = client.post("/recalculate", json={"w_health": 0.5, "w_budget": 0.3, "w_taste": 0.2})

    assert res.status_code == 400
    assert "No active session data found" in res.json()["detail"]


def test_recalculate_after_submit_200(monkeypatch):
    import json

    import fakeredis

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    # Mock pipelines
    def mock_ingest(*args, **kwargs):
        return {"query_intent": "foo", "hard_constraints": {}, "soft_constraints": {}}

    def mock_anchor(*args, **kwargs):
        return {
            "source_intent": {},
            "safe_candidates": [{"name": "fake candidate", "taste_profile": {}}],
        }

    def mock_debate(session_id, *args, **kwargs):
        from tier_1.contracts.session_store import save_contract

        save_contract(session_id, "decision_blueprint", {"winning_dish": {"name": "dummy"}})
        return {}

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", mock_ingest)
    monkeypatch.setattr("tier_1.symbolic_anchoring.run_anchoring_pipeline", mock_anchor)
    monkeypatch.setattr("tier_2.consensus_manager.run_debate_pipeline", mock_debate)
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda x: x)
    monkeypatch.setattr("tier_2.agents.TasteAgent.score", lambda self, x: 0.5)

    from fastapi.testclient import TestClient

    from orchestrator import DECISION_BLUEPRINT_PATH, app

    DECISION_BLUEPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISION_BLUEPRINT_PATH, "w", encoding="utf-8") as f:
        json.dump({"winning_dish": {"name": "dummy"}}, f)

    client = TestClient(app)

    # 1. Call /submit to populate session
    res1 = client.post("/submit", data={"query": "pizza"})
    assert res1.status_code == 200

    # 2. Call /recalculate (session cookie will be automatically sent by TestClient)
    res2 = client.post("/recalculate", json={"w_health": 0.5, "w_budget": 0.3, "w_taste": 0.2})
    assert res2.status_code == 200

    # Assert data is consistent
    data = res2.json()
    assert "utility_breakdown" in data
    assert "agent_weights" in data
    assert data["agent_weights"]["w_h"] == 0.5

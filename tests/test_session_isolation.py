import json

import fakeredis
from fastapi.testclient import TestClient

from orchestrator import DECISION_BLUEPRINT_PATH, app


def test_full_session_isolation(monkeypatch):
    """
    Simulates two concurrent sessions (two TestClient instances with separate cookies)
    each submitting a different query, then each calling /recalculate.
    Asserts each response only ever reflects its own submitted query's candidates,
    proving that the original race condition (shared files) is fixed via session_store.
    """
    # Mock Redis
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    # Mock pipelines with stateful pops to simulate distinct processing per request
    ingest_responses = [
        {"query_intent": "I want pizza", "hard_constraints": {}, "soft_constraints": {}},
        {"query_intent": "I want salad", "hard_constraints": {}, "soft_constraints": {}},
    ]
    anchor_responses = [
        {
            "source_intent": {},
            "safe_candidates": [
                {"name": "pizza margherita", "price_pkr": 1000, "taste_profile": {}}
            ],
        },
        {
            "source_intent": {},
            "safe_candidates": [{"name": "caesar salad", "price_pkr": 500, "taste_profile": {}}],
        },
    ]

    def mock_ingest(*args, **kwargs):
        return ingest_responses.pop(0)

    def mock_anchor(*args, **kwargs):
        return anchor_responses.pop(0)

    def mock_debate(session_id, *args, **kwargs):
        from tier_1.contracts.session_store import save_contract

        save_contract(session_id, "decision_blueprint", {"winning_dish": {"name": "dummy"}})
        return {}

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", mock_ingest)
    monkeypatch.setattr("tier_1.symbolic_anchoring.run_anchoring_pipeline", mock_anchor)
    monkeypatch.setattr("tier_2.consensus_manager.run_debate_pipeline", mock_debate)
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda x: x)
    monkeypatch.setattr("tier_2.agents.TasteAgent.score", lambda self, x: 0.5)

    # Ensure the dummy blueprint file exists so orchestrator doesn't crash reading it in /submit
    DECISION_BLUEPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISION_BLUEPRINT_PATH, "w", encoding="utf-8") as f:
        json.dump({"winning_dish": {"name": "dummy"}}, f)

    # Create two isolated clients (simulating two browsers with separate cookie jars)
    client1 = TestClient(app)
    client2 = TestClient(app)

    # Session 1 submits
    res1_submit = client1.post("/submit", data={"query": "I want pizza"})
    assert res1_submit.status_code == 200

    # Session 2 submits
    res2_submit = client2.post("/submit", data={"query": "I want salad"})
    assert res2_submit.status_code == 200

    # Both call /recalculate
    res1_recalc = client1.post(
        "/recalculate", json={"w_health": 0.5, "w_budget": 0.3, "w_taste": 0.2}
    )
    res2_recalc = client2.post(
        "/recalculate", json={"w_health": 0.5, "w_budget": 0.3, "w_taste": 0.2}
    )

    assert res1_recalc.status_code == 200
    assert res2_recalc.status_code == 200

    # Assert isolation! Client 1 should only see pizza
    data1 = res1_recalc.json()
    candidates1 = [c["name"] for c in data1.get("all_candidate_scores", [])]
    assert "pizza margherita" in candidates1
    assert "caesar salad" not in candidates1

    # Client 2 should only see salad
    data2 = res2_recalc.json()
    candidates2 = [c["name"] for c in data2.get("all_candidate_scores", [])]
    assert "caesar salad" in candidates2
    assert "pizza margherita" not in candidates2

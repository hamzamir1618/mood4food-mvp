import fakeredis
from fastapi.testclient import TestClient

from orchestrator import app


def test_alternate_endpoint_normal(monkeypatch):
    client = TestClient(app)
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    import uuid

    monkeypatch.setattr(uuid, "uuid4", lambda: type("obj", (object,), {"hex": "test_session"})())

    from tier_1.contracts.schemas import Candidate, DecisionBlueprint
    from tier_1.contracts.session_store import save_contract

    blueprint = DecisionBlueprint(
        winning_dish={"dish_id": "dish1", "name": "First Dish"},
        top_candidates=[
            Candidate(dish_id="dish1", name="First Dish", price_pkr=500.0),
            Candidate(dish_id="dish2", name="Second Dish", price_pkr=600.0),
            Candidate(dish_id="dish3", name="Third Dish", price_pkr=700.0),
        ],
    )

    save_contract("test_session", "decision_blueprint", blueprint.model_dump())

    # We don't need to mock load/save contract or enrich_blueprint anymore.
    monkeypatch.setattr("api.alternate.enrich_blueprint", lambda bp: bp)

    # Force a session ID by setting it in the request state via dependency or middleware
    # Actually, we can just hit the endpoint. If session_id is None, it fails. But TestClient
    # hits the middleware which assigns one (uuid.uuid4() -> "test_session").
    res = client.post("/alternate", json={"already_rejected": ["dish1"]})
    assert res.status_code == 200
    data = res.json()
    assert data["winning_dish"]["dish_id"] == "dish2"


def test_alternate_endpoint_exhausted(monkeypatch):
    client = TestClient(app)
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    import uuid

    monkeypatch.setattr(uuid, "uuid4", lambda: type("obj", (object,), {"hex": "test_session2"})())

    from tier_1.contracts.schemas import Candidate, DecisionBlueprint
    from tier_1.contracts.session_store import save_contract

    blueprint = DecisionBlueprint(
        winning_dish={"dish_id": "dish1", "name": "First Dish"},
        top_candidates=[
            Candidate(dish_id="dish1", name="First Dish", price_pkr=500.0),
            Candidate(dish_id="dish2", name="Second Dish", price_pkr=600.0),
        ],
    )

    save_contract("test_session2", "decision_blueprint", blueprint.model_dump())

    res = client.post("/alternate", json={"already_rejected": ["dish1", "dish2"]})
    assert res.status_code == 200
    data = res.json()
    assert data.get("no_more_alternates") is True

"""
Phase 2 accounts. Unit tests for passwords, tokens and saved constraints, then the
account API end to end against a throwaway Neo4j container, with fakeredis for sessions
and guest history.
"""

import uuid
from datetime import datetime, timedelta, timezone

import fakeredis
import pytest
from fastapi.testclient import TestClient
from neo4j import GraphDatabase

from accounts import security, store, taste_index
from accounts.constraints import apply_dietary_profile
from accounts.models import TASTE_DIMS, DietaryProfile, Event, TasteModel
from tier_1.contracts.schemas import GroundedIntent

PASSWORD = "a-long-test-password"


# ── Units (no database) ──────────────────────────────────────────────────────


def test_passwords_are_argon2id_and_verify():
    stored = security.hash_password(PASSWORD)
    assert stored.startswith("$argon2id$")
    assert security.verify_password(stored, PASSWORD)
    assert not security.verify_password(stored, "not-the-password")
    assert not security.verify_password_or_dummy(None, PASSWORD)  # no account


def test_tokens_expire_and_need_the_secret(monkeypatch):
    token = security.issue_token("u1", 3)
    assert security.read_token(token) == ("u1", 3)
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    assert security.read_token(security.issue_token("u1", 3, now=month_ago)) is None
    monkeypatch.setattr(security.settings, "AUTH_SECRET", "a-different-secret")
    assert security.read_token(token) is None


def test_only_known_allergens_can_be_saved():
    with pytest.raises(ValueError):
        DietaryProfile(allergies=["kryptonite"])
    assert DietaryProfile(allergies=[" Dairy ", "dairy", "nuts"]).allergies == ["dairy", "nuts"]


def test_saved_constraints_only_ever_add_to_a_query():
    intent = {"allergens_pruned": ["Nuts"], "is_vegan": False, "is_vegetarian": True}
    merged = apply_dietary_profile(
        intent, DietaryProfile(allergies=["dairy"], diet="vegan", halal_only=True)
    )
    assert merged["allergens_pruned"] == ["dairy", "nuts"]
    assert merged["is_vegan"] and merged["is_vegetarian"] and merged["is_halal"]
    # an empty profile never removes what the query itself asked for
    assert apply_dietary_profile(intent, DietaryProfile())["is_vegetarian"] is True


def _set_by_hand(persona: str, **values: float) -> TasteModel:
    base = TasteModel.from_persona(persona)
    return base.model_copy(
        update={
            "vector": {**base.vector, **values},
            "confidence": {**base.confidence, **{d: 1.0 for d in values}},
        }
    )


def test_a_persona_alone_is_not_indexed_as_a_taste():
    taste_index.rebuild([])
    taste_index.sync("persona-only", TasteModel.from_persona("sweet_tooth"))
    assert taste_index.count() == 0
    mine = _set_by_hand("sweet_tooth", sweet=0.9)
    taste_index.sync("u-a", mine)
    taste_index.sync("u-b", mine)
    match = taste_index.similar("u-a", mine.as_list())
    assert [m["user_id"] for m in match] == ["u-b"]
    assert match[0]["similarity"] == pytest.approx(1.0, abs=1e-3)
    taste_index.rebuild([])


# ── API against a throwaway Neo4j ────────────────────────────────────────────


@pytest.fixture(scope="module")
def neo4j_url():
    try:
        from testcontainers.community.neo4j import Neo4jContainer
    except ImportError:
        from testcontainers.neo4j import Neo4jContainer
    with Neo4jContainer("neo4j:2026.07.1", username="neo4j", password="password1234") as neo4j:
        yield neo4j.get_connection_url()


@pytest.fixture
def api(neo4j_url, monkeypatch):
    driver = GraphDatabase.driver(neo4j_url, auth=("neo4j", "password1234"))
    monkeypatch.setattr(store, "_driver", driver)
    store.ensure_schema()
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)
    taste_index.rebuild([])
    from orchestrator import app

    yield app
    driver.execute_query(
        "MATCH (n) WHERE n:User OR n:DietaryProfile OR n:GoalProfile OR n:TasteModel "
        "OR n:InteractionEvent DETACH DELETE n"
    )
    driver.close()
    taste_index.rebuild([])


def _register(client: TestClient, **extra) -> str:
    email = extra.pop("email", f"{uuid.uuid4().hex[:10]}@m4f-test.invalid")
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD, **extra})
    assert r.status_code == 201, r.text
    return email


def _mock_pipeline(monkeypatch, seen: list) -> None:
    """Stands in for the recommendation tiers, recording the intent Tier 1b receives."""

    def ingest(**kwargs):
        return {"raw_input": kwargs.get("raw_input") or "", "allergens_pruned": []}

    def anchor(intent):
        seen.append(intent)
        return {"source_intent": {}, "safe_candidates": []}

    def debate(session_id, *args, **kwargs):
        from tier_1.contracts.session_store import save_contract

        shown = [{"dish_id": "abc123", "name": "Chicken Karahi"}, {"dish_id": "def456"}]
        save_contract(
            session_id,
            "decision_blueprint",
            {"winning_dish": shown[0], "top_candidates": shown},
        )

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", ingest)
    monkeypatch.setattr("tier_1.symbolic_anchoring.run_anchoring_pipeline", anchor)
    monkeypatch.setattr("tier_2.consensus_manager.run_debate_pipeline", debate)
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda x: x)


def test_register_then_sign_in_on_a_second_device(api):
    device1 = TestClient(api)
    bad = {"email": "not-an-email", "password": PASSWORD}
    assert device1.post("/auth/register", json=bad).status_code == 422
    short = {"email": "x@m4f-test.invalid", "password": "short"}
    assert device1.post("/auth/register", json=short).status_code == 422

    r = device1.post(
        "/auth/register",
        json={"email": "Asha@M4F-test.invalid", "password": PASSWORD, "display_name": "Asha"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "asha@m4f-test.invalid"
    assert security.COOKIE_NAME in r.cookies
    assert device1.get("/auth/me").json()["user"]["display_name"] == "Asha"
    again = {"email": "ASHA@m4f-test.invalid", "password": PASSWORD}
    assert device1.post("/auth/register", json=again).status_code == 409
    saved = {"allergies": ["nuts"], "diet": "vegetarian", "halal_only": True}
    assert device1.put("/profile/dietary", json=saved).status_code == 200

    device2 = TestClient(api)
    assert device2.get("/auth/me").json()["user"] is None
    assert device2.get("/profile").status_code == 401
    wrong = {"email": "asha@m4f-test.invalid", "password": "not-the-password"}
    assert device2.post("/auth/login", json=wrong).status_code == 401
    nobody = {"email": "nobody@m4f-test.invalid", "password": PASSWORD}
    assert device2.post("/auth/login", json=nobody).status_code == 401
    right = {"email": "asha@m4f-test.invalid", "password": PASSWORD}
    assert device2.post("/auth/login", json=right).status_code == 200
    assert device2.get("/profile").json()["dietary"] == saved


def test_sign_out_everywhere_ends_every_session(api):
    device1 = TestClient(api)
    email = _register(device1)
    device2 = TestClient(api)
    device2.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert device2.post("/auth/logout", params={"everywhere": "true"}).status_code == 200
    assert device1.get("/auth/me").json()["user"] is None
    assert device1.get("/profile").status_code == 401
    assert device2.get("/auth/me").json()["user"] is None


def test_login_is_rate_limited(api):
    client = TestClient(api)
    wrong = {"email": "nobody@m4f-test.invalid", "password": "not-the-password"}
    codes = [client.post("/auth/login", json=wrong).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_guest_history_moves_to_the_account_and_saved_allergies_join_queries(api, monkeypatch):
    seen = []
    _mock_pipeline(monkeypatch, seen)
    browser = TestClient(api)
    assert browser.post("/submit", data={"text": "something spicy"}).status_code == 200

    r = browser.post(
        "/auth/register", json={"email": "guest@m4f-test.invalid", "password": PASSWORD}
    )
    assert r.json()["guest_events_claimed"] == 1
    saved = {"allergies": ["dairy"], "diet": "none", "halal_only": False}
    browser.put("/profile/dietary", json=saved)
    assert browser.post("/submit", data={"text": "anything"}).status_code == 200

    assert seen[0]["allergens_pruned"] == []  # the guest query was left alone
    assert seen[1]["allergens_pruned"] == ["dairy"]  # the saved allergy joined this one
    history = browser.get("/profile/history").json()["events"]
    assert [e["kind"] for e in history] == ["query", "query"]
    assert sorted(e["constraints"]["allergens_pruned"] for e in history) == [[], ["dairy"]]
    assert all(e["shown"] == ["abc123", "def456"] for e in history)
    assert {e["dish_uid"] for e in history} == {"abc123"}


def test_export_holds_everything_but_the_password_and_delete_removes_it(api):
    client = TestClient(api)
    email = _register(client)
    exported = client.get("/profile/export")
    assert "attachment" in exported.headers["content-disposition"]
    assert exported.json()["profile"]["user"]["email"] == email
    assert "password_hash" not in exported.text and "argon2" not in exported.text

    assert client.post("/profile/delete", json={"password": "wrong"}).status_code == 401
    assert client.post("/profile/delete", json={"password": PASSWORD}).json() == {"deleted": True}
    assert client.get("/auth/me").json()["user"] is None
    login = {"email": email, "password": PASSWORD}
    assert TestClient(api).post("/auth/login", json=login).status_code == 401
    records, _, _ = store.get_driver().execute_query(
        "MATCH (n) WHERE n:User OR n:DietaryProfile OR n:GoalProfile OR n:TasteModel "
        "RETURN count(n) AS n"
    )
    assert records[0]["n"] == 0


def test_history_keeps_only_the_newest_events(api, monkeypatch):
    monkeypatch.setattr(store.settings, "EVENTS_PER_USER", 3)
    client = TestClient(api)
    _register(client)
    user_id = client.get("/auth/me").json()["user"]["user_id"]
    store.record_events(
        user_id,
        [
            Event(event_id=f"e{i}", kind="query", at=f"2026-09-14T10:00:0{i}+00:00")
            for i in range(5)
        ],
    )
    assert [e.event_id for e in store.list_events(user_id)] == ["e4", "e3", "e2"]


def test_new_accounts_pause_before_the_graph_limit(api, monkeypatch):
    usage = store.graph_usage()
    full_account = 4 + store.settings.EVENTS_PER_USER
    other_nodes = usage["nodes"] - usage["account_nodes"]
    room_for_one = int((other_nodes + full_account) / store.settings.GRAPH_HEADROOM) + 1
    monkeypatch.setattr(store.settings, "GRAPH_NODE_LIMIT", room_for_one)
    _register(TestClient(api))
    late = {"email": "late@m4f-test.invalid", "password": PASSWORD}
    assert TestClient(api).post("/auth/register", json=late).status_code == 503


def test_taste_set_by_hand_is_found_by_similar_tastes(api):
    a = TestClient(api)
    _register(a, persona="sweet_tooth")
    b = TestClient(api)
    _register(b, persona="sweet_tooth")
    assert a.get("/profile/similar-tastes").json()["matches"] == []  # persona only
    assert a.put("/profile/taste", json={"values": {"sweet": 2.0}}).status_code == 422

    profile = a.put("/profile/taste", json={"values": {"sweet": 0.9, "spice": 0.1}}).json()
    assert profile["taste"]["confidence"]["sweet"] == 1.0
    assert profile["taste"]["confidence"]["umami"] == 0.0
    b.put("/profile/taste", json={"values": {"sweet": 0.8, "spice": 0.2}})
    matches = a.get("/profile/similar-tastes").json()["matches"]
    assert len(matches) == 1 and 0.9 < matches[0]["similarity"] <= 1.0
    assert set(matches[0]) == {"similarity"}  # no other user is identified

    reset = a.post("/profile/taste/reset", json={}).json()["taste"]
    assert reset["confidence"] == {d: 0.0 for d in TASTE_DIMS}
    assert a.get("/profile/similar-tastes").json()["matches"] == []
    assert taste_index.count() == 1  # only b is left in the index


# ── Phase 4: approvals and learning ──────────────────────────────────────────


def _mock_shortlist(monkeypatch) -> None:
    """A recommendation of two dishes: a mild top pick and a spicier, cheaper runner-up."""

    def ingest(**kwargs):
        return {"raw_input": kwargs.get("raw_input") or "", "allergens_pruned": []}

    def anchor(intent):
        return {"source_intent": {}, "safe_candidates": []}

    def debate(session_id, *args, **kwargs):
        from tier_1.contracts.session_store import save_contract

        top = {
            "dish_id": "mild",
            "name": "Mild Korma",
            "taste_source": "original",
            "taste_profile": {"sweet": 0.3, "salty": 0.5, "umami": 0.6, "spice": 0.1},
            "u_health": 0.7,
            "u_budget": 0.5,
            "u_taste": 0.8,
            "u_total": 0.7,
        }
        spicy = {
            "dish_id": "spicy",
            "name": "Spicy Karahi",
            "taste_source": "original",
            "taste_profile": {"salty": 0.6, "umami": 0.7, "spice": 0.95},
            "u_health": 0.6,
            "u_budget": 1.0,
            "u_taste": 0.6,
            "u_total": 0.65,
        }
        save_contract(
            session_id, "decision_blueprint", {"winning_dish": top, "top_candidates": [top, spicy]}
        )

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", ingest)
    monkeypatch.setattr("tier_1.symbolic_anchoring.run_anchoring_pipeline", anchor)
    monkeypatch.setattr("tier_2.consensus_manager.run_debate_pipeline", debate)
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda x: x)


def test_an_approval_teaches_the_taste_model_and_never_the_dietary_profile(api, monkeypatch):
    _mock_shortlist(monkeypatch)
    client = TestClient(api)
    _register(client)
    saved = {"allergies": ["nuts"], "diet": "vegetarian", "halal_only": True}
    client.put("/profile/dietary", json=saved)
    assert client.post("/approve", json={"dish_id": "spicy"}).status_code == 400  # none shown

    client.post("/submit", data={"text": "dinner"})
    assert client.post("/approve", json={"dish_id": "not-shown"}).status_code == 404
    first = client.post("/approve", json={"dish_id": "spicy"}).json()
    assert first["approved"] == "Spicy Karahi" and first["learned"]
    again = client.post("/approve", json={"dish_id": "spicy"}).json()
    assert again["learned"] == [] and "Already" in again["note"]

    profile = client.get("/profile").json()
    assert profile["taste"]["updates"] == 1
    assert profile["taste"]["vector"]["spice"] > 0.4  # the balanced persona's starting value
    assert profile["taste"]["agent_weights"]["w_budget"] > 0.33  # chose the cheaper runner-up
    assert profile["dietary"] == saved  # learning never touches hard constraints
    kinds = [e["kind"] for e in client.get("/profile/history").json()["events"]]
    assert "approved" in kinds
    assert client.get("/profile/learning").json()["approvals"] == 1

    reset = client.post("/profile/taste/reset", json={}).json()["taste"]
    assert reset["updates"] == 0 and reset["agent_weights"] is None


def test_weights_can_be_set_by_hand(api):
    client = TestClient(api)
    _register(client)
    bad = {"w_health": 0, "w_budget": 0, "w_taste": 0}
    assert client.put("/profile/weights", json=bad).status_code == 422
    weights = client.put(
        "/profile/weights", json={"w_health": 2 / 10, "w_budget": 0, "w_taste": 3 / 10}
    ).json()["taste"]["agent_weights"]
    assert weights == pytest.approx({"w_health": 0.4, "w_budget": 0.0, "w_taste": 0.6})


def test_a_guests_approval_is_learned_from_when_they_sign_up(api, monkeypatch):
    _mock_shortlist(monkeypatch)
    browser = TestClient(api)
    browser.post("/submit", data={"text": "dinner"})
    as_guest = browser.post("/approve", json={"dish_id": "spicy"}).json()
    assert as_guest["learned"] == [] and "Sign in" in as_guest["note"]
    _register(browser)
    assert browser.get("/profile").json()["taste"]["updates"] == 1


# ── Phase 5: what a conversation offers to save ──────────────────────────────


def test_a_conversation_offers_to_save_what_it_heard_but_never_saves_it(api, monkeypatch):
    def ingest(**kwargs):
        return {
            **GroundedIntent().model_dump(),
            "raw_input": kwargs.get("raw_input") or "",
            "allergens_pruned": ["dairy"],
            "is_vegetarian": True,
            "mood_vector": {"spice": 0.8},
            "preferred_category": "desi",
            "budget_max_pkr": 1500.0,
        }

    found = [
        {
            "dish_id": f"v{i}",
            "name": f"Veg {i}",
            "category": "desi_traditional",
            "price_pkr": 500.0 + 100 * i,
            "allergens": [],
            "taste_profile": {"spice": 0.2 * i},
        }
        for i in range(5)
    ]
    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", ingest)
    monkeypatch.setattr(
        "tier_1.symbolic_anchoring.run_anchoring_pipeline",
        lambda intent: {"source_intent": intent, "safe_candidates": found, "message": ""},
    )
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda bp: dict(bp))
    client = TestClient(api)
    _register(client)

    reply = client.post("/chat", json={"text": "no dairy, vegetarian, spicy desi"}).json()
    assert reply["type"] == "recommendation"
    [suggestion] = reply["suggestions"]
    assert suggestion["path"] == "/profile/dietary"
    assert suggestion["body"]["allergies"] == ["dairy"]
    assert suggestion["body"]["diet"] == "vegetarian"
    assert client.get("/profile").json()["dietary"]["allergies"] == []  # offered, not saved

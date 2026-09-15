"""
Users, profiles and interaction events in Neo4j (Phase 2).

    (:User)-[:HAS_DIETARY]->(:DietaryProfile)
    (:User)-[:HAS_GOALS]->(:GoalProfile)
    (:User)-[:HAS_TASTE]->(:TasteModel)
    (:User)-[:DID]->(:InteractionEvent)-[:ABOUT]->(:Dish)

Taste vectors are stored as lists in TASTE_DIMS order, because Neo4j properties cannot
be maps. Each event is one node with at most one relationship, to the dish it is about;
the other dishes shown are a list property. That keeps the graph small, since AuraDB
Free caps nodes and relationships.
"""

import json
import uuid
from datetime import datetime, timezone

from neo4j import GraphDatabase
from neo4j.exceptions import ConstraintError

from accounts.models import (
    TASTE_DIMS,
    WEIGHT_KEYS,
    DietaryProfile,
    Event,
    GoalProfile,
    Profile,
    TasteModel,
    UserPublic,
)
from config import settings
from tier_1.persona_manager import DEFAULT_PERSONA

SCHEMA = (
    "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
    "CREATE CONSTRAINT user_email_unique IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
    "CREATE CONSTRAINT event_id_unique IF NOT EXISTS "
    "FOR (e:InteractionEvent) REQUIRE e.event_id IS UNIQUE",
)

_driver = None


class EmailTaken(Exception):
    pass


class ProfileIncomplete(Exception):
    """A user exists without all three profile nodes. Never papered over with defaults."""


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    return _driver


def _run(cypher: str, **params) -> list[dict]:
    records, _, _ = get_driver().execute_query(cypher, params)
    return [r.data() for r in records]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_schema() -> None:
    for statement in SCHEMA:
        _run(statement)


# ── Capacity ─────────────────────────────────────────────────────────────────
def graph_usage() -> dict:
    """Node and relationship counts, overall and for accounts."""
    return _run(
        """
        CALL { MATCH (n) RETURN count(n) AS nodes }
        CALL { MATCH ()-[r]->() RETURN count(r) AS relationships }
        CALL { MATCH (u:User) RETURN count(u) AS users }
        CALL { MATCH (n) WHERE n:User OR n:DietaryProfile OR n:GoalProfile OR n:TasteModel
                               OR n:InteractionEvent
               RETURN count(n) AS account_nodes }
        CALL { MATCH ()-[r:HAS_DIETARY|HAS_GOALS|HAS_TASTE|DID|ABOUT]->()
               RETURN count(r) AS account_relationships }
        RETURN nodes, relationships, users, account_nodes, account_relationships
        """
    )[0]


def account_capacity(usage: dict | None = None) -> dict:
    """
    How many accounts fit if every one filled its history to EVENTS_PER_USER, staying
    under GRAPH_HEADROOM of the node and relationship limits. A full account is the user,
    three profile nodes and its events, each event with a DID and an ABOUT relationship.
    """
    usage = usage or graph_usage()
    per_user_nodes = 4 + settings.EVENTS_PER_USER
    per_user_relationships = 3 + 2 * settings.EVENTS_PER_USER
    other_nodes = usage["nodes"] - usage["account_nodes"]
    other_relationships = usage["relationships"] - usage["account_relationships"]
    node_room = settings.GRAPH_NODE_LIMIT * settings.GRAPH_HEADROOM - other_nodes
    relationship_room = (
        settings.GRAPH_RELATIONSHIP_LIMIT * settings.GRAPH_HEADROOM - other_relationships
    )
    max_users = int(min(node_room // per_user_nodes, relationship_room // per_user_relationships))
    return {**usage, "max_users": max(0, max_users)}


def has_room_for_another_user() -> bool:
    capacity = account_capacity()
    return capacity["users"] < capacity["max_users"]


def public(user: dict) -> UserPublic:
    return UserPublic(
        user_id=user["user_id"],
        email=user["email"],
        display_name=user.get("display_name", ""),
        created_at=user.get("created_at", ""),
    )


# ── Users ────────────────────────────────────────────────────────────────────
def create_user(email: str, display_name: str, password_hash: str, persona: str) -> dict:
    """Creates the user and all three profile nodes in one transaction; returns the user."""
    taste = TasteModel.from_persona(persona)
    try:
        rows = _run(
            """
            CREATE (u:User {user_id: $user_id, email: $email, display_name: $display_name,
                            password_hash: $password_hash, token_version: 0, created_at: $now})
            CREATE (u)-[:HAS_DIETARY]->(:DietaryProfile {allergies: [], diet: 'none',
                                                         halal_only: false})
            CREATE (u)-[:HAS_GOALS]->(:GoalProfile {goal: 'balanced'})
            CREATE (u)-[:HAS_TASTE]->(:TasteModel {vector: $vector, confidence: $confidence,
                                                   updates: 0, persona_prior: $persona})
            RETURN u
            """,
            user_id=uuid.uuid4().hex,
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            now=now_iso(),
            vector=taste.as_list(),
            confidence=[taste.confidence[d] for d in TASTE_DIMS],
            persona=taste.persona_prior,
        )
    except ConstraintError as exc:
        raise EmailTaken(email) from exc
    return rows[0]["u"]


def get_user_by_email(email: str) -> dict | None:
    rows = _run("MATCH (u:User {email: $email}) RETURN u", email=email)
    return rows[0]["u"] if rows else None


def get_user(user_id: str) -> dict | None:
    rows = _run("MATCH (u:User {user_id: $user_id}) RETURN u", user_id=user_id)
    return rows[0]["u"] if rows else None


def set_password_hash(user_id: str, password_hash: str) -> None:
    _run(
        "MATCH (u:User {user_id: $user_id}) SET u.password_hash = $password_hash",
        user_id=user_id,
        password_hash=password_hash,
    )


def bump_token_version(user_id: str) -> int:
    rows = _run(
        """
        MATCH (u:User {user_id: $user_id})
        SET u.token_version = coalesce(u.token_version, 0) + 1
        RETURN u.token_version AS version
        """,
        user_id=user_id,
    )
    return rows[0]["version"] if rows else 0


# ── Profile ──────────────────────────────────────────────────────────────────
def _taste(t: dict) -> TasteModel:
    """A TasteModel node's properties as the model. Lists are in TASTE_DIMS / WEIGHT_KEYS order."""
    return TasteModel(
        vector=dict(zip(TASTE_DIMS, t["vector"])),
        confidence=dict(zip(TASTE_DIMS, t["confidence"])),
        importance=(
            dict(zip(TASTE_DIMS, t["importance"]))
            if t.get("importance")
            else {d: 1.0 for d in TASTE_DIMS}
        ),
        agent_weights=dict(zip(WEIGHT_KEYS, t["agent_weights"]))
        if t.get("agent_weights")
        else None,
        updates=t.get("updates", 0),
        persona_prior=t.get("persona_prior") or DEFAULT_PERSONA,
    )


def get_profile(user_id: str) -> Profile | None:
    rows = _run(
        """
        MATCH (u:User {user_id: $user_id})
        OPTIONAL MATCH (u)-[:HAS_DIETARY]->(d:DietaryProfile)
        OPTIONAL MATCH (u)-[:HAS_GOALS]->(g:GoalProfile)
        OPTIONAL MATCH (u)-[:HAS_TASTE]->(t:TasteModel)
        RETURN u, d, g, t
        """,
        user_id=user_id,
    )
    if not rows:
        return None
    r = rows[0]
    if r["d"] is None or r["g"] is None or r["t"] is None:
        raise ProfileIncomplete(user_id)
    d, g, t = r["d"], r["g"], r["t"]
    return Profile(
        user=public(r["u"]),
        dietary=DietaryProfile(
            allergies=d.get("allergies", []),
            diet=d.get("diet", "none"),
            halal_only=d.get("halal_only", False),
        ),
        goals=GoalProfile(
            goal=g.get("goal", "balanced"), typical_spend_pkr=g.get("typical_spend_pkr")
        ),
        taste=_taste(t),
    )


def set_dietary(user_id: str, dietary: DietaryProfile) -> None:
    _run(
        """
        MATCH (:User {user_id: $user_id})-[:HAS_DIETARY]->(d:DietaryProfile)
        SET d.allergies = $allergies, d.diet = $diet, d.halal_only = $halal_only
        """,
        user_id=user_id,
        **dietary.model_dump(),
    )


def set_goals(user_id: str, goals: GoalProfile) -> None:
    _run(
        """
        MATCH (:User {user_id: $user_id})-[:HAS_GOALS]->(g:GoalProfile)
        SET g.goal = $goal, g.typical_spend_pkr = $typical_spend_pkr
        """,
        user_id=user_id,
        **goals.model_dump(),
    )


def set_taste(user_id: str, taste: TasteModel) -> None:
    _run(
        """
        MATCH (:User {user_id: $user_id})-[:HAS_TASTE]->(t:TasteModel)
        SET t.vector = $vector, t.confidence = $confidence, t.updates = $updates,
            t.persona_prior = $persona_prior, t.importance = $importance,
            t.agent_weights = $agent_weights
        """,
        user_id=user_id,
        vector=taste.as_list(),
        confidence=[taste.confidence[d] for d in TASTE_DIMS],
        updates=taste.updates,
        persona_prior=taste.persona_prior,
        importance=[taste.importance[d] for d in TASTE_DIMS],
        agent_weights=(
            [taste.agent_weights[k] for k in WEIGHT_KEYS] if taste.agent_weights else None
        ),
    )


def all_taste_models() -> list[tuple[str, TasteModel]]:
    rows = _run(
        """
        MATCH (u:User)-[:HAS_TASTE]->(t:TasteModel)
        RETURN u.user_id AS user_id, t.vector AS vector, t.confidence AS confidence
        """
    )
    return [
        (
            r["user_id"],
            TasteModel(
                vector=dict(zip(TASTE_DIMS, r["vector"])),
                confidence=dict(zip(TASTE_DIMS, r["confidence"])),
            ),
        )
        for r in rows
    ]


# ── Events ───────────────────────────────────────────────────────────────────
def record_events(user_id: str, events: list[Event]) -> None:
    """
    Attaches events to the user. Idempotent by event_id, so a retried claim adds nothing.
    Only the newest EVENTS_PER_USER are kept, which bounds what one account can occupy;
    the Phase 4 learning loop should fold events into the taste model before they go.
    """
    if not events:
        return
    _run(
        """
        MATCH (u:User {user_id: $user_id})
        UNWIND $events AS e
        MERGE (ev:InteractionEvent {event_id: e.event_id})
        ON CREATE SET ev += e
        MERGE (u)-[:DID]->(ev)
        WITH ev
        OPTIONAL MATCH (d:Dish {dish_uid: ev.dish_uid})
        FOREACH (_ IN CASE WHEN d IS NULL THEN [] ELSE [1] END | MERGE (ev)-[:ABOUT]->(d))
        """,
        user_id=user_id,
        events=[
            {
                **e.model_dump(),
                "constraints": json.dumps(e.constraints),
                "detail": json.dumps(e.detail),
            }
            for e in events
        ],
    )
    _run(
        """
        MATCH (:User {user_id: $user_id})-[:DID]->(ev:InteractionEvent)
        WITH ev ORDER BY ev.at DESC, ev.event_id DESC
        SKIP $keep
        DETACH DELETE ev
        """,
        user_id=user_id,
        keep=settings.EVENTS_PER_USER,
    )


def list_events(user_id: str, limit: int = 50) -> list[Event]:
    rows = _run(
        """
        MATCH (:User {user_id: $user_id})-[:DID]->(e:InteractionEvent)
        RETURN e ORDER BY e.at DESC LIMIT $limit
        """,
        user_id=user_id,
        limit=limit,
    )
    return [
        Event(
            **{
                **r["e"],
                "constraints": json.loads(r["e"].get("constraints") or "{}"),
                "detail": json.loads(r["e"].get("detail") or "{}"),
            }
        )
        for r in rows
    ]


def approvals_by(user_ids: list[str], since: str) -> dict[str, int]:
    """How many of these users approved each dish since the given time (ISO 8601)."""
    rows = _run(
        """
        MATCH (u:User)-[:DID]->(e:InteractionEvent {kind: 'approved'})
        WHERE u.user_id IN $user_ids AND e.at >= $since AND e.dish_uid IS NOT NULL
        RETURN e.dish_uid AS dish_uid, count(DISTINCT u) AS users
        """,
        user_ids=user_ids,
        since=since,
    )
    return {r["dish_uid"]: r["users"] for r in rows}


# ── Data rights ──────────────────────────────────────────────────────────────
def export_user(user_id: str) -> dict:
    """Everything stored about the user, except the password hash."""
    profile = get_profile(user_id)
    return {
        "exported_at": now_iso(),
        "profile": profile.model_dump() if profile else None,
        "events": [e.model_dump() for e in list_events(user_id, limit=1_000_000)],
    }


def delete_user(user_id: str) -> int:
    """Deletes the user, their profile nodes and their events. Returns the nodes removed."""
    rows = _run(
        """
        MATCH (u:User {user_id: $user_id})
        OPTIONAL MATCH (u)-[:HAS_DIETARY|HAS_GOALS|HAS_TASTE|DID]->(x)
        WITH u, collect(x) AS owned
        FOREACH (n IN owned | DETACH DELETE n)
        DETACH DELETE u
        RETURN size(owned) + 1 AS removed
        """,
        user_id=user_id,
    )
    return rows[0]["removed"] if rows else 0

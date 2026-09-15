"""
Interaction events: what a user asked for, what they were shown and what they passed
over. The Phase 4 learning loop learns from them.

A signed-in user's events go straight to Neo4j. A guest's are kept in Redis under their
session for as long as the session cookie lives, and move to their account when they
register or sign in on the same browser.
"""

import logging
import uuid

from accounts import store
from accounts.models import Event
from tier_1.contracts import session_store
from tier_2.scoring import TASTE_SOURCE_CONFIDENCE

log = logging.getLogger(__name__)

GUEST_TTL_S = 14 * 24 * 3600  # the session cookie's lifetime
GUEST_MAX_EVENTS = 200
CONSTRAINT_KEYS = (
    "budget_max_pkr",
    "allergens_pruned",
    "is_vegan",
    "is_vegetarian",
    "is_halal",
    "preferred_category",
)


def _guest_key(session_id: str) -> str:
    return f"{session_id}:events"


def query_event(session_id: str, intent: dict, blueprint: dict) -> Event:
    winner = blueprint.get("winning_dish") or {}
    return Event(
        event_id=uuid.uuid4().hex,
        kind="query",
        at=store.now_iso(),
        session_id=session_id,
        query=str(intent.get("raw_input") or "")[:500],
        dish_uid=winner.get("dish_id") or None,
        dish_name=winner.get("name", ""),
        shown=[c["dish_id"] for c in blueprint.get("top_candidates") or [] if c.get("dish_id")],
        constraints={k: intent.get(k) for k in CONSTRAINT_KEYS},
    )


def rejected_event(session_id: str, dish: dict) -> Event:
    return Event(
        event_id=uuid.uuid4().hex,
        kind="rejected",
        at=store.now_iso(),
        session_id=session_id,
        dish_uid=dish.get("dish_id") or None,
        dish_name=dish.get("name", ""),
    )


def approved_event(session_id: str, chosen, top, query: str = "") -> Event:
    """An approval of `chosen`, with what learning needs; `top` is the top-ranked option."""
    c = chosen.model_dump() if hasattr(chosen, "model_dump") else dict(chosen)
    t = top.model_dump() if hasattr(top, "model_dump") else dict(top)

    def utilities(d: dict) -> dict:
        return {k: d.get(k) for k in ("u_health", "u_budget", "u_taste")}

    return Event(
        event_id=uuid.uuid4().hex,
        kind="approved",
        at=store.now_iso(),
        session_id=session_id,
        query=str(query or "")[:500],
        dish_uid=c.get("dish_id") or None,
        dish_name=c.get("name", ""),
        detail={
            "taste": c.get("taste_profile") or {},
            "taste_trust": TASTE_SOURCE_CONFIDENCE.get(c.get("taste_source") or "", 0.5),
            "category": c.get("category"),
            "price_pkr": c.get("price_pkr"),
            "utilities": utilities(c),
            "top_dish_uid": t.get("dish_id"),
            "top_utilities": utilities(t),
        },
    )


def refined_event(session_id: str, critique: str, dish: dict) -> Event:
    """A refinement ("cheaper", "milder"...) and the dish it led to. Learning ignores it."""
    return Event(
        event_id=uuid.uuid4().hex,
        kind="refined",
        at=store.now_iso(),
        session_id=session_id,
        dish_uid=dish.get("dish_id") or None,
        dish_name=dish.get("name", ""),
        detail={"critique": critique},
    )


def record(session_id: str, user_id: str | None, event: Event) -> None:
    """Stores one event. Failure is logged, never raised: a lost event must not cost the
    user their recommendation."""
    try:
        if user_id:
            store.record_events(user_id, [event])
            return
        client = session_store.get_redis()
        key = _guest_key(session_id)
        client.rpush(key, event.model_dump_json())
        client.ltrim(key, -GUEST_MAX_EVENTS, -1)
        client.expire(key, GUEST_TTL_S)
    except Exception as exc:
        log.warning("interaction event not recorded (%s): %s", event.kind, exc)


def guest_events(session_id: str) -> list[Event]:
    """This browser's guest events, oldest first."""
    raw = session_store.get_redis().lrange(_guest_key(session_id), 0, -1)
    return [Event.model_validate_json(x) for x in raw]


def claim_guest_events(session_id: str, user_id: str) -> list[Event]:
    """Moves this browser's guest events to the account; returns the events moved."""
    client = session_store.get_redis()
    key = _guest_key(session_id)
    claimed = [Event.model_validate_json(x) for x in client.lrange(key, 0, -1)]
    if claimed:
        store.record_events(user_id, claimed)
        client.delete(key)
    return claimed

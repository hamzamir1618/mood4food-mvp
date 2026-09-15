"""
The learning loop (Phase 4): what an approval teaches the preference model.

Three things move, each by a rule a person can read, check and undo (docs/LEARNING.md):

  taste       moves toward the approved dish's taste by a step that starts at 0.3 and
              halves by the tenth approval, scaled by how far the dish's flavour data
              can be trusted
  importance  per taste dimension, from the last 20 approvals: a dimension where the
              approved dishes sit consistently at one level matters more
  weights     health, budget and taste: when the approved dish wasn't the top pick,
              whatever it did better on counts a little more

A pass teaches nothing: it could mean the price, the mood or yesterday's lunch, so it
only lowers that dish for a week (the novelty term). Learning never touches the dietary
profile: allergies, diet and halal are the user's to set, and no approval can loosen them.
"""

import logging
import statistics
from datetime import datetime, timedelta, timezone

from accounts import store, taste_index
from accounts.models import TASTE_DIMS, WEIGHT_KEYS, Event, TasteModel
from tier_1.persona_manager import get_persona
from tier_2.scoring import TASTE_WORDS, normalise_weights

log = logging.getLogger(__name__)

STEP = 0.3  # how far the first approval moves the taste
HALVING = 10  # the step halves by this many approvals
MENTION = 0.02  # smaller taste moves aren't mentioned
IMPORTANCE_WINDOW = 20  # approvals the importance is learned from
IMPORTANCE_MIN_APPROVALS = 3
IMPORTANCE_RANGE = (0.5, 2.0)
IMPORTANCE_VARIANCE_FLOOR = 0.01  # so one perfectly consistent dimension can't dominate
WEIGHT_STEP = 0.2
MIN_WEIGHT = 0.05  # no trade-off is ever learned away completely
PEER_NEIGHBOURS = 10
PEER_SIMILARITY = 0.9  # cosine similarity for "tastes like yours"
PEER_DAYS = 30
AGENT_WORDS = {"w_health": "health", "w_budget": "price", "w_taste": "taste"}
UTILITY_OF = {"w_health": "u_health", "w_budget": "u_budget", "w_taste": "u_taste"}


# ── The rules (pure) ─────────────────────────────────────────────────────────
def step_size(updates: int) -> float:
    return STEP / (1 + updates / HALVING)


def update_taste(model: TasteModel, dish_taste: dict, trust: float) -> tuple[TasteModel, list[str]]:
    """Moves the taste toward an approved dish's; trust is the dish's flavour confidence."""
    alpha = step_size(model.updates) * max(0.0, min(1.0, trust))
    target = {d: float(dish_taste.get(d) or 0.0) for d in TASTE_DIMS}
    vector = {d: round((1 - alpha) * model.vector[d] + alpha * target[d], 4) for d in TASTE_DIMS}
    confidence = {d: round(c + (1 - c) * alpha, 4) for d, c in model.confidence.items()}
    moves = [
        f"{TASTE_WORDS[d]} {model.vector[d]:.2f} → {vector[d]:.2f}"
        for d in TASTE_DIMS
        if abs(vector[d] - model.vector[d]) >= MENTION
    ]
    said = [f"Your taste moved: {', '.join(moves)}."] if moves else []
    updated = model.model_copy(
        update={"vector": vector, "confidence": confidence, "updates": model.updates + 1}
    )
    return updated, said


def learned_importance(tastes: list[dict]) -> dict[str, float] | None:
    """
    Per-dimension importance from approved dishes' tastes: the inverse of each dimension's
    spread, scaled so the average is 1 and clamped to IMPORTANCE_RANGE. None until there
    are enough approvals to say anything.
    """
    if len(tastes) < IMPORTANCE_MIN_APPROVALS:
        return None
    inverse = {
        d: 1
        / (
            statistics.pvariance([float(t.get(d) or 0.0) for t in tastes])
            + IMPORTANCE_VARIANCE_FLOOR
        )
        for d in TASTE_DIMS
    }
    mean = sum(inverse.values()) / len(inverse)
    low, high = IMPORTANCE_RANGE
    return {d: round(min(high, max(low, v / mean)), 4) for d, v in inverse.items()}


def nudge_weights(
    weights: dict, chosen: dict, top: dict, updates: int
) -> tuple[dict[str, float], list[str]]:
    """
    Revealed preference: when the user approves a dish other than the top pick, each
    weight moves along the gap between the two dishes' utilities on that term.
    Unassessed utilities (None) teach nothing.
    """
    gaps = {
        w: chosen[u] - top[u]
        for w, u in UTILITY_OF.items()
        if chosen.get(u) is not None and top.get(u) is not None
    }
    if not gaps or max(abs(g) for g in gaps.values()) < MENTION:
        return weights, []
    step = WEIGHT_STEP / (1 + updates / HALVING)
    moved = normalise_weights(
        {k: max(MIN_WEIGHT, weights[k] + step * gaps.get(k, 0.0)) for k in WEIGHT_KEYS}
    )
    best = max(gaps, key=gaps.get)
    said = []
    if gaps[best] > 0:
        word = AGENT_WORDS[best]
        said.append(
            f"You picked something better on {word} than the top pick, so {word} now counts "
            f"{weights[best]:.0%} → {moved[best]:.0%}."
        )
    return moved, said


def learning_summary(taste: TasteModel) -> dict:
    """What the model has learned, in sentences, for the profile screen."""
    if taste.updates == 0:
        return {
            "approvals": 0,
            "summary": ["Nothing learned yet. Approve a recommendation and I'll start learning."],
        }
    persona = get_persona(taste.persona_prior)
    prior = persona["taste_preference"]
    lines = []
    for d in sorted(TASTE_DIMS, key=lambda d: -abs(taste.vector[d] - prior[d]))[:2]:
        diff = taste.vector[d] - prior[d]
        if abs(diff) >= 0.1:
            lines.append(
                f"You like it {'more' if diff > 0 else 'less'} {TASTE_WORDS[d]} than your "
                f"starting persona, {persona['display_name']} "
                f"({prior[d]:.2f} → {taste.vector[d]:.2f})."
            )
    top = max(taste.importance, key=taste.importance.get)
    if taste.importance[top] >= 1.3:
        lines.append(f"How {TASTE_WORDS[top]} a dish is matters most to you.")
    if taste.agent_weights:
        base = normalise_weights(persona["weights"])
        k = max(WEIGHT_KEYS, key=lambda k: abs(taste.agent_weights[k] - base[k]))
        if abs(taste.agent_weights[k] - base[k]) >= 0.05:
            more = "more" if taste.agent_weights[k] > base[k] else "less"
            lines.append(
                f"{AGENT_WORDS[k].capitalize()} counts {more} for you than the persona assumed "
                f"({base[k]:.0%} → {taste.agent_weights[k]:.0%})."
            )
    if not lines:
        lines.append("Your approvals so far match your starting point closely.")
    plural = "s" if taste.updates != 1 else ""
    lines.append(f"Learned from {taste.updates} approval{plural}. You can edit or reset this.")
    return {"approvals": taste.updates, "summary": lines}


# ── Applying them to an account ──────────────────────────────────────────────
def learn_from_approval(user_id: str, event: Event) -> list[str]:
    """Updates the user's preference model from one approval; returns what it learned."""
    profile = store.get_profile(user_id)
    if profile is None:
        return []
    detail = event.detail or {}
    taste, said = update_taste(
        profile.taste, detail.get("taste") or {}, detail.get("taste_trust", 0.5)
    )

    earlier = [
        e.detail["taste"]
        for e in store.list_events(user_id, 200)
        if e.kind == "approved" and e.event_id != event.event_id and (e.detail or {}).get("taste")
    ][: IMPORTANCE_WINDOW - 1]
    importance = learned_importance([detail.get("taste") or {}, *earlier])
    if importance:
        taste = taste.model_copy(update={"importance": importance})

    top_uid = detail.get("top_dish_uid")
    if top_uid and top_uid != event.dish_uid:
        current = taste.agent_weights or normalise_weights(
            get_persona(taste.persona_prior)["weights"]
        )
        weights, more = nudge_weights(
            current,
            detail.get("utilities") or {},
            detail.get("top_utilities") or {},
            profile.taste.updates,
        )
        if more:
            taste = taste.model_copy(update={"agent_weights": weights})
            said += more

    store.set_taste(user_id, taste)
    try:
        taste_index.sync(user_id, taste)
    except Exception as exc:  # the index is derived; the next startup rebuild repairs it
        log.warning("similar-tastes index not updated after an approval: %s", exc)
    return said


def replay(user_id: str, claimed: list[Event]) -> int:
    """Learns from a guest's approvals once they have an account; returns how many."""
    approvals = sorted((e for e in claimed if e.kind == "approved"), key=lambda e: e.at)
    for e in approvals:
        learn_from_approval(user_id, e)
    return len(approvals)


def peer_approvals(user_id: str, taste: TasteModel) -> dict[str, int]:
    """
    Dishes that users with a similar taste (cosine similarity in the ChromaDB index)
    approved in the last PEER_DAYS days, with how many of them did. Anonymous: only
    counts leave this function.
    """
    neighbours = [
        m["user_id"]
        for m in taste_index.similar(user_id, taste.as_list(), PEER_NEIGHBOURS)
        if m["similarity"] >= PEER_SIMILARITY
    ]
    if not neighbours:
        return {}
    since = (datetime.now(timezone.utc) - timedelta(days=PEER_DAYS)).isoformat(timespec="seconds")
    return store.approvals_by(neighbours, since)

"""
The approve action (Phase 4): "this one". Approving one of the dishes just shown teaches
the signed-in user's preference model (accounts/learning.py); a guest's approval is kept
and learned from when they sign up. See docs/LEARNING.md.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from accounts import events, learning
from accounts.deps import current_user_id
from api.rate_limit import limiter

log = logging.getLogger(__name__)
router = APIRouter(tags=["learning"])


class ApproveRequest(BaseModel):
    dish_id: str = Field(min_length=1, max_length=200)


@router.post("/approve")
@limiter.limit("30/minute")
def approve(request: Request, body: ApproveRequest):
    """
    Approves one of the current recommendation's options. Only dishes that were shown
    can be approved, and each only once per recommendation, so learning can't be steered
    by approving arbitrary dishes or the same one repeatedly.
    """
    from tier_1.contracts.session_store import load_contract, save_contract

    session_id = request.state.session_id
    blueprint = load_contract(session_id, "decision_blueprint")
    if not blueprint or not blueprint.top_candidates:
        raise HTTPException(400, "There's no recommendation to approve yet.")
    shortlist = blueprint.top_candidates
    chosen = next((c for c in shortlist if c.dish_id == body.dish_id), None)
    if chosen is None:
        raise HTTPException(404, "That dish isn't one of the options you were shown.")

    approved = load_contract(session_id, "approved") or []
    if body.dish_id in approved:
        return {"approved": chosen.name, "learned": [], "note": "Already noted for this one."}

    intent = load_contract(session_id, "grounded_intent")
    event = events.approved_event(
        session_id, chosen, shortlist[0], getattr(intent, "raw_input", "") if intent else ""
    )
    try:
        user_id = current_user_id(request)
        learned = learning.learn_from_approval(user_id, event) if user_id else []
    except Exception as exc:
        log.error("approval not learned: %s", exc)
        raise HTTPException(503, "Couldn't save your approval. Please try again.")

    events.record(session_id, user_id, event)
    save_contract(session_id, "approved", [*approved, body.dish_id])
    return {
        "approved": chosen.name,
        "learned": learned,
        "note": None if user_id else "Sign in and I'll learn from this.",
    }

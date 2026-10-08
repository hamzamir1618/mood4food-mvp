import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from accounts import events
from accounts.deps import current_user_id
from tier_1.contracts.session_store import load_contract, save_contract
from tier_2.consensus_manager import WINNER_FIELDS, get_alternate
from tier_3.fulfillment_engine import enrich_blueprint
from ui.compose import pick_for_session

log = logging.getLogger(__name__)
router = APIRouter()


class AlternateRequest(BaseModel):
    already_rejected: List[str] = []
    # A runner-up chosen from the list: that dish rather than the next one down
    dish_id: Optional[str] = None


@router.post("/alternate")
async def get_alternate_dish(request: Request, body: AlternateRequest):
    """
    Finds an alternative dish from the top candidates that has not been rejected yet.
    Updates the session blueprint with the new winner and returns the enriched blueprint.
    """
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        raise HTTPException(status_code=400, detail="No active session")

    blueprint = load_contract(session_id, "decision_blueprint")
    if not blueprint:
        raise HTTPException(status_code=400, detail="No active decision blueprint found")

    passed_over = blueprint.winning_dish or {}
    if body.dish_id:
        alternate_result = next(
            (c for c in blueprint.top_candidates if c.dish_id == body.dish_id),
            {"error": "not on the shortlist"},
        )
    else:
        alternate_result = get_alternate(session_id, body.already_rejected)
    if passed_over.get("dish_id"):
        try:
            user_id = current_user_id(request)
        except Exception:  # kept as a guest event, claimed at the next sign-in
            user_id = None
        events.record(session_id, user_id, events.rejected_event(session_id, passed_over))
    if isinstance(alternate_result, dict) and alternate_result.get("error"):
        return {"no_more_alternates": True}

    # alternate_result is a Candidate model: the whole of it, so the card, its evidence and
    # its ingredients are this dish's and not the last one's.
    full = alternate_result.model_dump()
    blueprint.winning_dish = {k: full.get(k) for k in WINNER_FIELDS}

    blueprint.utility_breakdown = {
        k: getattr(alternate_result, k)
        for k in ("u_health", "u_budget", "u_taste", "u_context", "u_distance", "u_total")
    }

    save_contract(session_id, "decision_blueprint", blueprint)

    blueprint_dict = blueprint.model_dump()
    blueprint_dict = enrich_blueprint(blueprint_dict)
    blueprint_dict.pop("all_candidate_scores", None)
    blueprint_dict["layout"] = pick_for_session(session_id, blueprint_dict)
    return blueprint_dict

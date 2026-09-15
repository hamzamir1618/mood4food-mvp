import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from accounts import events
from accounts.deps import current_user_id
from tier_1.contracts.session_store import load_contract, save_contract
from tier_2.consensus_manager import get_alternate
from tier_3.fulfillment_engine import enrich_blueprint

log = logging.getLogger(__name__)
router = APIRouter()


class AlternateRequest(BaseModel):
    already_rejected: List[str] = []


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
    alternate_result = get_alternate(session_id, body.already_rejected)
    if passed_over.get("dish_id"):
        try:
            user_id = current_user_id(request)
        except Exception:  # kept as a guest event, claimed at the next sign-in
            user_id = None
        events.record(session_id, user_id, events.rejected_event(session_id, passed_over))
    if isinstance(alternate_result, dict) and alternate_result.get("error"):
        return {"no_more_alternates": True}

    # alternate_result is a Candidate model
    blueprint.winning_dish = {
        "dish_id": alternate_result.dish_id,
        "name": alternate_result.name,
        "price_pkr": alternate_result.price_pkr,
        "category": alternate_result.category,
        "image_url": alternate_result.image_url,
        "is_rep_image": alternate_result.is_rep_image,
        "human_tags": alternate_result.human_tags,
        "ingredients": alternate_result.ingredients,
        "allergens": alternate_result.allergens,
        "reasons": alternate_result.reasons,
        "confidence": alternate_result.confidence,
    }

    blueprint.utility_breakdown = {
        k: getattr(alternate_result, k)
        for k in ("u_health", "u_budget", "u_taste", "u_context", "u_total")
    }

    save_contract(session_id, "decision_blueprint", blueprint)

    blueprint_dict = blueprint.model_dump()
    blueprint_dict = enrich_blueprint(blueprint_dict)

    return blueprint_dict

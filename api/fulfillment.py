import logging
from typing import Dict

from fastapi import APIRouter, HTTPException, Request

from tier_1.contracts.schemas import DecisionBlueprint, Persona

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/decision_blueprint", response_model=DecisionBlueprint)
def get_decision_blueprint(request: Request):
    """Returns the current decision_blueprint.json to the frontend."""
    from tier_1.contracts.session_store import load_contract
    from tier_3.fulfillment_engine import enrich_blueprint

    blueprint = load_contract(request.state.session_id, "decision_blueprint")
    if not blueprint:
        raise HTTPException(
            400, "No active decision blueprint found. Please submit a new query first."
        )

    if hasattr(blueprint, "model_dump"):
        blueprint = blueprint.model_dump()

    return enrich_blueprint(blueprint)


@router.get("/personas", response_model=Dict[str, Persona])
def get_personas():
    """Returns all available persona definitions for the frontend to render."""
    from tier_1.persona_manager import get_all_personas

    return get_all_personas()

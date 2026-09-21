import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.rate_limit import limiter
from tier_1.contracts.schemas import DecisionBlueprint

log = logging.getLogger(__name__)

router = APIRouter()


class WeightUpdate(BaseModel):
    w_health: Optional[float] = None
    w_budget: Optional[float] = None
    w_taste: Optional[float] = None
    # Legacy single-slider support
    w_budget_legacy: Optional[float] = None
    persona: Optional[str] = None


@router.post("/recalculate", response_model=DecisionBlueprint)
@limiter.limit("20/minute")
def recalculate(request: Request, payload: WeightUpdate):
    """
    Re-ranks the session's candidates with new weights (the sliders) or a new persona,
    using the same decision core and scoring context as the query. No LLM or database
    call, so it's instant.
    """
    from dialogue import state as conversation_state
    from dialogue.pool import adjusted, allows
    from tier_1.contracts.session_store import load_contract, save_contract
    from tier_2.consensus_manager import build_blueprint, run_debate
    from tier_2.scoring import build_preferences, health_term
    from tier_3.fulfillment_engine import enrich_blueprint

    session_id = request.state.session_id
    evaluation = load_contract(session_id, "candidate_evaluation")
    if not evaluation:
        raise HTTPException(400, "No active session data found. Please submit a new query first.")
    if hasattr(evaluation, "model_dump"):
        evaluation = evaluation.model_dump()
    context = load_contract(session_id, "scoring_context") or {}

    weights = None
    if (
        payload.w_health is not None
        and payload.w_budget is not None
        and payload.w_taste is not None
    ):
        weights = {
            "w_health": payload.w_health,
            "w_budget": payload.w_budget,
            "w_taste": payload.w_taste,
        }
    elif payload.w_budget_legacy is not None:
        w_b = max(0.0, min(1.0, payload.w_budget_legacy))
        weights = {"w_health": (1 - w_b) / 2, "w_budget": w_b, "w_taste": (1 - w_b) / 2}

    # The conversation narrows the query's pool — an answer ("Desi"), a refinement
    # ("Cheaper") — and the sliders re-rank what is left of it. Re-ranking the whole pool
    # threw the answers away: choose Desi, move a slider, get a fast-food burger.
    intent = evaluation.get("source_intent") or {}
    pool = evaluation.get("safe_candidates", [])
    conversation = conversation_state.load(session_id)
    adj = conversation.adjustments if conversation else None
    if adj is not None:
        intent, context = adjusted(intent, context, adj)
        narrowed = [c for c in pool if allows(adj, c)]
        pool = narrowed or pool  # never re-rank to nothing: the pick on screen came from here
    prefs = build_preferences(intent, context, weights, payload.persona)
    if adj is not None and adj.health_above is not None:
        healthier = [
            c
            for c in pool
            if (t := health_term(c, prefs.goal)).confidence > 0 and t.utility > adj.health_above
        ]
        pool = healthier or pool
    debate = run_debate(pool, prefs)
    blueprint = enrich_blueprint(build_blueprint(debate, {**evaluation, "source_intent": intent}))
    save_contract(session_id, "decision_blueprint", blueprint)

    winner = debate["winner"]
    log.info(
        "recalculated with %s (persona=%s) → winner: %s",
        debate["final_weights"],
        prefs.persona,
        winner["name"] if winner else "None",
    )
    blueprint.pop("all_candidate_scores", None)  # never sent; candidate_count carries the size
    return blueprint

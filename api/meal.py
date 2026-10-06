"""
GET /meal: the pick, something to eat with it, something to drink, and the total.

One tap on the card. It reads the recommendation the session already holds and asks the same
restaurant's menu what else this person may be offered — the dietary rules, the party size and
the budget all come from the request that produced the pick, so the meal is bound by exactly
what the dish was (tier_1/meal.py).

Nothing here places an order. It says what the meal would come to, which is the part the app
can honestly answer.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

log = logging.getLogger(__name__)
router = APIRouter(tags=["meal"])


@router.get("/meal")
def meal(request: Request):
    """What the current pick would come to as a meal. 400 when there is no pick to build on."""
    from tier_1.contracts.session_store import load_contract
    from tier_1.meal import alongside, make_a_meal

    session_id = request.state.session_id
    blueprint = load_contract(session_id, "decision_blueprint")
    if hasattr(blueprint, "model_dump"):
        blueprint = blueprint.model_dump()
    winner = (blueprint or {}).get("winning_dish")
    if not winner:
        raise HTTPException(400, "There's no pick to build a meal around yet.")

    intent = load_contract(session_id, "grounded_intent") or {}
    if hasattr(intent, "model_dump"):
        intent = intent.model_dump()
    context = load_contract(session_id, "scoring_context") or {}

    # What the user said they'd spend, whether they said it in the query or in conversation.
    ceiling = intent.get("budget_max_pkr")
    try:
        from dialogue import state

        said_later = state.load(session_id).adjustments.ceiling
        ceiling = said_later or ceiling
    except Exception as exc:  # a budget we can't read is one we don't apply
        log.warning("the conversation's budget could not be read: %s", exc)
    if ceiling and ceiling >= 999_999:
        ceiling = None

    options = alongside(winner.get("restaurant_name") or "", winner.get("dish_id") or "", intent)
    return make_a_meal(
        winner,
        options,
        party_size=context.get("party_size") or 1,
        ceiling=float(ceiling) if ceiling else None,
    )

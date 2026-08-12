import logging
import math
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
    Accepts new weights from the UI sliders (w_health, w_budget, w_taste)
    and an optional persona key. Re-scores all candidates with new weights
    **without re-querying the LLM or database**. Instant.
    """
    from tier_1.contracts.schemas import Candidate, TasteProfile
    from tier_1.contracts.session_store import load_contract, save_contract
    from tier_1.persona_manager import DEFAULT_PERSONA, get_all_personas, get_persona
    from tier_2.agents import TasteAgent
    from tier_3.fulfillment_engine import enrich_blueprint

    evaluation = load_contract(request.state.session_id, "candidate_evaluation")
    if not evaluation:
        raise HTTPException(400, "No active session data found. Please submit a new query first.")

    if hasattr(evaluation, "model_dump"):
        evaluation = evaluation.model_dump()

    candidates = evaluation.get("safe_candidates", [])
    budget_max = evaluation.get("source_intent", {}).get("budget_max_pkr", 1000)
    mood_seed = evaluation.get("soft_constraints", {}).get("mood_vector_seed", "neutral")
    direct_dish_prompt = evaluation.get("soft_constraints", {}).get("direct_dish_prompt", "")

    # Determine persona and weights
    persona_key = payload.persona or DEFAULT_PERSONA
    persona = get_persona(persona_key)
    persona_taste = persona["taste_preference"]

    # Use explicitly provided weights, or fall back to persona defaults
    if (
        payload.w_health is not None
        and payload.w_budget is not None
        and payload.w_taste is not None
    ):
        raw_h, raw_b, raw_t = payload.w_health, payload.w_budget, payload.w_taste
    elif payload.w_budget_legacy is not None:
        # Legacy single-slider mode
        w_b = max(0.0, min(1.0, payload.w_budget_legacy))
        remaining = 1.0 - w_b
        raw_h, raw_b, raw_t = remaining / 2.0, w_b, remaining / 2.0
    else:
        pw = persona["weights"]
        raw_h, raw_b, raw_t = pw["w_health"], pw["w_budget"], pw["w_taste"]

    # Normalize weights to sum to 1.0
    total = raw_h + raw_b + raw_t
    if total > 0:
        w_h, w_b, w_t = raw_h / total, raw_b / total, raw_t / total
    else:
        w_h, w_b, w_t = 0.34, 0.33, 0.33

    xai_traces = [
        f"slider_override: w_h={w_h:.2f} w_b={w_b:.2f} w_t={w_t:.2f} (persona={persona_key})"
    ]

    scored = []
    for cand in candidates:
        macros = cand.get("macros", {})
        protein = macros.get("protein_g", 15.0)
        calories = macros.get("calories", 500.0)
        price = cand.get("price_pkr", 0.0)

        u_h = min(1.0, (protein / max(calories, 1)) / 0.05)

        # Log-scaled budget utility for better spread
        if price < 0:
            u_b = 1.0
        elif budget_max is None or budget_max <= 0:
            u_b = math.exp(-0.002 * price)
        else:
            u_b = max(0.0, 1.0 - math.log(1 + price) / math.log(1 + budget_max))

        # 6D taste profile utility
        dish_taste_profile = cand.get("taste_profile", {})
        if dish_taste_profile and persona_taste:
            agent = TasteAgent(persona_taste=TasteProfile(**persona_taste))
            c_model = Candidate(taste_profile=TasteProfile(**dish_taste_profile))
            u_t = agent.score(c_model)
        else:
            u_t = 0.5  # fallback without taste data

        u_total = (w_h * u_h) + (w_b * u_b) + (w_t * u_t)

        cand_name_lower = cand.get("name", "").lower()
        if (
            direct_dish_prompt
            and len(direct_dish_prompt) > 3
            and (cand_name_lower in direct_dish_prompt or direct_dish_prompt in cand_name_lower)
        ):
            u_total = 1000.0

        entry = {
            "dish_id": cand.get("dish_id", "?"),
            "name": cand.get("name", "unnamed"),
            "u_health": round(u_h, 6),
            "u_budget": round(u_b, 6),
            "u_taste": round(u_t, 6),
            "u_total": round(u_total, 6),
            "price_pkr": price,
            "category": cand.get("category", ""),
            "image_url": cand.get("image_url", ""),
            "human_tags": cand.get("human_tags", []),
            "taste_profile": dish_taste_profile,
        }
        scored.append(entry)
        xai_traces.append(
            f"  {entry['name']} → U_h={u_h:.4f} U_b={u_b:.4f} U_t={u_t:.4f} | U_total={u_total:.4f}"
        )

    if scored:
        winner = max(scored, key=lambda x: x["u_total"])
        winning_dish = {
            "dish_id": winner["dish_id"],
            "name": winner["name"],
            "price_pkr": winner.get("price_pkr", 0),
            "category": winner.get("category", ""),
            "image_url": winner.get("image_url", ""),
            "human_tags": winner.get("human_tags", []),
        }
        utility_breakdown = {
            "u_health": winner["u_health"],
            "u_budget": winner["u_budget"],
            "u_taste": winner["u_taste"],
            "u_total": winner["u_total"],
        }
        xai_traces.append(f"winner: {winner['name']} (U_total={winner['u_total']:.4f})")
    else:
        winning_dish = None
        utility_breakdown = {"u_health": 0.0, "u_budget": 0.0, "u_taste": 0.0, "u_total": 0.0}
        xai_traces.append("FALLBACK: no candidates to score")

    relaxation_notice = evaluation.get("message", "") or None

    blueprint = {
        "winning_dish": winning_dish,
        "utility_breakdown": utility_breakdown,
        "agent_weights": {"w_h": round(w_h, 4), "w_b": round(w_b, 4), "w_t": round(w_t, 4)},
        "persona": persona_key,
        "relaxation_rounds": 0,
        "xai_traces": xai_traces,
        "all_candidate_scores": scored,
        "top_candidates": sorted(scored, key=lambda x: x.get("u_total", 0.0), reverse=True)[:5],
        "source_context": {
            "budget_max_pkr": budget_max,
            "allergens_pruned": evaluation.get("source_intent", {}).get("allergens_pruned", []),
            "mood_vector_seed": mood_seed,
        },
        "personas_available": {
            k: {
                "display_name": v["display_name"],
                "icon": v["icon"],
                "description": v["description"],
            }
            for k, v in get_all_personas().items()
        },
        "relaxation_notice": relaxation_notice,
    }

    # Enrich with fulfillment data
    blueprint = enrich_blueprint(blueprint)

    # Persist updated blueprint
    save_contract(request.state.session_id, "decision_blueprint", blueprint)
    log.info(
        "recalculated blueprint with w_h=%.2f w_b=%.2f w_t=%.2f persona=%s → winner: %s",
        w_h,
        w_b,
        w_t,
        persona_key,
        winner["name"] if scored else "None",
    )

    return blueprint

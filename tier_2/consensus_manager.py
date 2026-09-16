"""
Tier 2 — the decision.

Ranks Tier 1's safe candidates with the decision core (tier_2/scoring.py) and writes the
decision blueprint the API returns. Tier 2 only ranks what Tier 1 let through and never
adds a dish, so every hard constraint Tier 1 applied holds for the winner and for every
runner-up. See docs/DECISION_CORE.md.
"""

import logging

from tier_1.contracts.schemas import Candidate
from tier_1.persona_manager import get_all_personas
from tier_2.scoring import Preferences, build_preferences, rank, traces

log = logging.getLogger(__name__)

TOP_N = 5
WINNER_FIELDS = (
    "dish_id",
    "name",
    "restaurant_name",
    "restaurant_area",
    "location_precision",
    "restaurant_lat",
    "restaurant_lng",
    "distance_km",
    "price_pkr",
    "price_status",
    "serves_min",
    "serves_max",
    "serves_source",
    "category",
    "image_url",
    "is_rep_image",
    "human_tags",
    "ingredients",
    "taste_profile",
    "allergens",
    "macros",
    "reasons",
    "summary",
    "confidence",
    "coverage",
)
# How a category reads in "Something different: an Afghan dish."
CATEGORY_NAMES = {
    "desi_traditional": "desi",
    "afghan": "Afghan",
    "middle_eastern": "Middle Eastern",
    "chinese_asian": "Chinese or Asian",
    "continental_upscale": "continental",
    "fast_food": "fast food",
    "pizza": "pizza",
    "sandwich": "sandwich",
    "cafe_bakery": "café",
}
UTILITIES = ("u_health", "u_budget", "u_taste", "u_context", "u_distance", "u_total")


def run_debate(candidates: list[dict], prefs: Preferences) -> dict:
    """Ranks the candidates. The best-ranked wins, and a lone candidate always wins."""
    ranked = rank(candidates, prefs)
    if ranked:
        log.info(
            "winner: %s (U_total=%.4f) of %d candidates",
            ranked[0]["name"],
            ranked[0]["u_total"],
            len(ranked),
        )
    w = prefs.weights
    return {
        "winner": ranked[0] if ranked else None,
        "ranked": ranked,
        "final_weights": {
            "w_h": round(w["w_health"], 4),
            "w_b": round(w["w_budget"], 4),
            "w_t": round(w["w_taste"], 4),
        },
        "persona": prefs.persona,
        "goal": prefs.goal,
        "relaxation_rounds": 0,
        "xai_traces": traces(ranked, prefs),
    }


STRETCH_MIN_SHARE = 0.8  # a stretch must score at least 80% of the winner


def shortlist(ranked: list[dict]) -> list[dict]:
    """
    The top TOP_N, except that the last place goes to a deliberate stretch when there is
    one: the best dish from a category none of the others share, scoring at least
    STRETCH_MIN_SHARE of the winner. A concierge that only confirms its own model becomes
    a filter bubble; the stretch is labelled, never hidden.
    """
    if len(ranked) <= TOP_N:
        return ranked
    usual = {c.get("category") for c in ranked[: TOP_N - 1]}
    floor = STRETCH_MIN_SHARE * ranked[0]["u_total"]
    stretch = next(
        (
            c
            for c in ranked[TOP_N - 1 :]
            if c.get("category") not in usual and c["u_total"] >= floor
        ),
        None,
    )
    if stretch is None:
        return ranked[:TOP_N]
    kind = CATEGORY_NAMES.get(stretch.get("category") or "")
    if kind:
        article = "an" if kind[0].lower() in "aeiou" else "a"
        note = f"Something different: {article} {kind} dish."
    else:
        note = "Something different to try."
    reasons = {**stretch.get("reasons", {}), "exploration": note}
    return [*ranked[: TOP_N - 1], {**stretch, "exploration": True, "reasons": reasons}]


def build_blueprint(debate: dict, evaluation: dict) -> dict:
    """The winner with its reasons, the runners-up, and what the query asked for."""
    winner, ranked = debate["winner"], debate["ranked"]
    intent = evaluation.get("source_intent") or {}
    soft = evaluation.get("soft_constraints") or {}
    return {
        "winning_dish": {k: winner.get(k) for k in WINNER_FIELDS} if winner else None,
        "utility_breakdown": (
            {k: winner.get(k) for k in UTILITIES}
            if winner
            else {**{k: None for k in UTILITIES}, "u_total": 0.0}
        ),
        "agent_weights": debate["final_weights"],
        "persona": debate["persona"],
        "relaxation_rounds": 0,
        "xai_traces": debate["xai_traces"],
        "top_candidates": shortlist(ranked),
        "candidate_count": len(ranked),
        "source_context": {
            "budget_max_pkr": intent.get("budget_max_pkr"),
            "allergens_pruned": intent.get("allergens_pruned", []),
            "mood_vector_seed": soft.get("mood_vector_seed", "neutral"),
        },
        "personas_available": {
            k: {
                "display_name": v["display_name"],
                "icon": v["icon"],
                "description": v["description"],
            }
            for k, v in get_all_personas().items()
        },
        "relaxation_notice": evaluation.get("message") or None,
    }


def run_debate_pipeline(session_id: str = "default_session") -> dict:
    """Loads the session's candidates and scoring context, ranks, and saves the blueprint."""
    log.info("─── Tier 2: decision START (session %s) ───", session_id)
    from tier_1.contracts.session_store import load_contract, save_contract

    evaluation = load_contract(session_id, "candidate_evaluation")
    if not evaluation:
        raise ValueError(f"No candidate_evaluation found for session {session_id}")
    if hasattr(evaluation, "model_dump"):
        evaluation = evaluation.model_dump()

    context = load_contract(session_id, "scoring_context") or {}
    prefs = build_preferences(evaluation.get("source_intent") or {}, context)
    debate = run_debate(evaluation.get("safe_candidates", []), prefs)
    save_contract(session_id, "decision_blueprint", build_blueprint(debate, evaluation))
    log.info("─── Tier 2: decision DONE ───")
    return debate


def get_alternate(session_id: str, excluded_dish_ids: list[str]) -> Candidate | dict:
    """
    Returns the next-highest-ranked candidate from the cached runners-up shortlist
    that is not in excluded_dish_ids. If exhausted, returns a signal dict.
    """
    from tier_1.contracts.session_store import load_contract

    blueprint = load_contract(session_id, "decision_blueprint")
    if not blueprint:
        return {"error": "no more alternates"}

    for cand in blueprint.top_candidates:
        if cand.dish_id not in excluded_dish_ids:
            return cand

    return {"error": "no more alternates"}

"""
Ranking the candidates a query already found, under the conversation's adjustments.
Tier 1 ran once for the query; everything here filters and re-scores its result, which
is why answering a question or refining is instant and needs no database or LLM call.
"""

from dialogue.state import Adjustments
from tier_2.consensus_manager import build_blueprint, run_debate
from tier_2.scoring import Preferences, build_preferences, health_term, rank


def allows(adj: Adjustments, dish: dict) -> bool:
    price = float(dish.get("price_pkr") or 0.0)
    kcal = (dish.get("macros") or {}).get("calories")
    spice = float((dish.get("taste_profile") or {}).get("spice") or 0.0)
    return all(
        (
            adj.ceiling is None or price <= adj.ceiling,
            adj.price_below is None or price < adj.price_below,
            adj.category is None or dish.get("category") == adj.category,
            dish.get("category") not in adj.exclude_categories,
            adj.calories_below is None or (kcal is not None and kcal < adj.calories_below),
            adj.calories_above is None or (kcal is not None and kcal > adj.calories_above),
            adj.spice_above is None or spice > adj.spice_above,
            adj.spice_below is None or spice < adj.spice_below,
        )
    )


def adjusted(intent: dict, context: dict, adj: Adjustments) -> tuple[dict, dict]:
    """The query and scoring context with the conversation's answers folded in."""
    intent, context = dict(intent), dict(context)
    if adj.ceiling is not None:
        asked = intent.get("budget_max_pkr")
        intent["budget_max_pkr"] = min(asked, adj.ceiling) if asked else adj.ceiling
    if adj.craved:
        intent["mood_vector"] = {**(intent.get("mood_vector") or {}), **adj.craved}
    if adj.category:
        intent["preferred_category"] = adj.category
    if adj.party_size:
        context["party_size"] = adj.party_size
    if adj.goal:
        context["goal"] = adj.goal
    return intent, context


def candidates_under(
    pool: list[dict], intent: dict, context: dict, adj: Adjustments
) -> tuple[list[dict], Preferences, dict]:
    """(the candidates the adjustments allow, the preferences to rank them by, the intent)."""
    intent, context = adjusted(intent, context, adj)
    prefs = build_preferences(intent, context)
    kept = [c for c in pool if allows(adj, c)]
    if adj.health_above is not None:
        kept = [
            c
            for c in kept
            if (t := health_term(c, prefs.goal)).confidence > 0 and t.utility > adj.health_above
        ]
    return kept, prefs, intent


def winner_under(pool: list[dict], intent: dict, context: dict, adj: Adjustments) -> str | None:
    kept, prefs, _ = candidates_under(pool, intent, context, adj)
    ranked = rank(kept, prefs)
    return ranked[0]["dish_id"] if ranked else None


def held(session_id: str) -> tuple[dict, dict]:
    """The session's candidate evaluation (the query's pool) and scoring context."""
    from tier_1.contracts.session_store import load_contract

    evaluation = load_contract(session_id, "candidate_evaluation")
    if hasattr(evaluation, "model_dump"):
        evaluation = evaluation.model_dump()
    return evaluation or {}, load_contract(session_id, "scoring_context") or {}


def rerank(session_id: str, adj: Adjustments) -> dict | None:
    """
    Re-ranks the session's pool under the adjustments, saves the new blueprint and
    returns it enriched, or None (saving nothing) when no candidate is left.
    """
    from tier_1.contracts.session_store import save_contract
    from tier_3.fulfillment_engine import enrich_blueprint

    evaluation, context = held(session_id)
    kept, prefs, intent = candidates_under(
        evaluation.get("safe_candidates", []), evaluation.get("source_intent") or {}, context, adj
    )
    if not kept:
        return None
    blueprint = build_blueprint(run_debate(kept, prefs), {**evaluation, "source_intent": intent})
    save_contract(session_id, "decision_blueprint", blueprint)
    enriched = enrich_blueprint(blueprint)
    enriched.pop("all_candidate_scores", None)
    return enriched

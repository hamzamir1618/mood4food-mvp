"""
The recommendation pipeline for one query, shared by /submit (one shot) and /chat (a
conversation): Tier 1a intent, the signed-in user's saved constraints, the scoring
context, Tier 1b hard constraints, Tier 2 ranking and Tier 3 fulfillment.
"""

import logging

from fastapi import HTTPException, Request

log = logging.getLogger(__name__)


def _known_areas() -> list[dict]:
    """The areas the picker offers, for matching an area named in the request. Never fatal."""
    from api.areas import areas

    try:
        return areas().get("areas") or []
    except Exception as exc:
        log.warning("areas unavailable, so an area named in the request is ignored: %s", exc)
        return []


def recommend(
    request: Request,
    text: str | None = None,
    audio_path: str | None = None,
    image_path: str | None = None,
    location: dict | None = None,
) -> dict:
    """
    Runs the whole pipeline for one query and returns the enriched blueprint. A location
    ({lat, lng, label}) is kept with the session; without one, the session's last is used.
    """
    from accounts import events, learning
    from accounts.constraints import apply_dietary_profile
    from accounts.deps import current_user_id
    from accounts.store import get_profile, list_events
    from api.location import load_location, nearby, save_location, with_distances
    from tier_1 import query_words
    from tier_1.contracts.session_store import load_contract, save_contract
    from tier_1.multi_modal_ingestion import run_ingestion_pipeline
    from tier_1.persona_manager import DEFAULT_PERSONA
    from tier_1.symbolic_anchoring import run_anchoring_pipeline
    from tier_2.consensus_manager import run_debate_pipeline
    from tier_2.context import scoring_context
    from tier_3.fulfillment_engine import enrich_blueprint

    # Stage 1: Multimodal Intent Parsing
    try:
        intent = run_ingestion_pipeline(
            raw_input=text or None,
            audio_path=audio_path,
            image_path=image_path,
        )
    except Exception as exc:
        log.error("Tier 1a failed: %s", exc)
        raise HTTPException(500, f"Intent parsing failed: {exc}")

    # Stage 1a-ii: what the words say that the extractor's fields can't carry — foods the
    # request leaves out ("no onion", pescatarian) and the area it names ("in F-7").
    said = str(intent.get("raw_input") or text or "")
    excluded = query_words.excluded_foods(said)
    if excluded:
        intent["allergens_pruned"] = sorted(
            set(intent.get("allergens_pruned") or []) | set(excluded)
        )
        log.info("the words exclude %s", excluded)
    if not intent.get("preferred_category"):
        from pipeline.ingredients import ALLERGEN_TAGS
        from tier_1.symbolic_anchoring import FOOD_GROUPS

        wanted = query_words.wanted_food(said, ALLERGEN_TAGS, tuple(FOOD_GROUPS))
        if wanted:
            intent["preferred_category"] = wanted
            intent["preferred_category_raw_phrase"] = wanted
            log.info("the words ask for '%s', which the extractor didn't name", wanted)
    if location is None and query_words.mentions_a_place(said):
        here = query_words.area_asked(said, _known_areas())
        if here:
            location = here
            log.info("measuring from %s, named in the request", here["label"])

    # Stage 1b: a signed-in user's saved dietary constraints join the query. If they
    # can't be loaded, stop: recommending without a saved allergy is not a fallback.
    profile = None
    try:
        user_id = current_user_id(request)
        if user_id:
            profile = get_profile(user_id)
            if profile is None:
                raise RuntimeError("account not found")
            intent = apply_dietary_profile(intent, profile.dietary)
    except Exception as exc:
        log.error("saved profile could not be loaded: %s", exc)
        raise HTTPException(
            503,
            "Your saved dietary profile couldn't be loaded, so no recommendation was made. "
            "Please try again.",
        )

    # Stage 1c: the scoring context. A signed-in user's goal, usual spend and learned
    # model; recent history, for variety; dishes similar users approved; the hour and
    # the weather. Saved with the session so later re-ranking uses the same inputs.
    session_id = request.state.session_id
    try:
        history = list_events(user_id, 50) if user_id else events.guest_events(session_id)
    except Exception as exc:
        log.warning("recent history unavailable, so variety is left out: %s", exc)
        history = []
    peers = {}
    if profile is not None and profile.taste.has_evidence():
        try:
            peers = learning.peer_approvals(user_id, profile.taste)
        except Exception as exc:
            log.warning("similar tastes unavailable, so left out: %s", exc)
    context = scoring_context(DEFAULT_PERSONA, profile, history, peers)

    try:
        save_contract(session_id, "grounded_intent", intent)
        save_contract(session_id, "scoring_context", context)
        save_contract(session_id, "approved", [])  # approvals belong to one recommendation
        if location is not None:
            save_location(session_id, location)
        else:
            location = load_location(session_id)
    except Exception as exc:
        log.error("Tier 1a failed: %s", exc)
        raise HTTPException(500, f"Intent parsing failed: {exc}")

    # Stage 2: Neo4j hard constraints, then each dish's distance from the user; far-off
    # restaurants drop out when closer ones match
    try:
        evaluation = run_anchoring_pipeline(intent)
        if hasattr(evaluation, "model_dump"):
            evaluation = evaluation.model_dump()
        candidates = with_distances(evaluation.get("safe_candidates") or [], location)
        evaluation["safe_candidates"] = nearby(candidates)
        # "Near me" with nowhere to measure from: say so rather than ignore it.
        if location is None and query_words.asks_for_nearby(said):
            said_so = "I don't know where you are, so choose your area to sort by distance."
            evaluation["message"] = " ".join(
                s for s in (said_so, evaluation.get("message") or "") if s
            )
        save_contract(session_id, "candidate_evaluation", evaluation)
    except Exception as exc:
        log.error("Tier 1b failed: %s", exc)
        raise HTTPException(503, f"Neo4j query failed — is the database running? ({exc})")

    # Stage 3: ranking
    try:
        run_debate_pipeline(session_id)
    except Exception as exc:
        log.error("Tier 2 failed: %s", exc)
        raise HTTPException(500, f"Debate pipeline failed: {exc}")

    blueprint = load_contract(session_id, "decision_blueprint")
    if not blueprint:
        raise HTTPException(500, "Pipeline completed but decision_blueprint was not created.")
    if hasattr(blueprint, "model_dump"):
        blueprint = blueprint.model_dump()

    # Enrich with fulfillment data (recipe + restaurants)
    blueprint = enrich_blueprint(blueprint)

    winner = blueprint.get("winning_dish") or {}
    log.info("─── recommendation complete → winner: %s ───", winner.get("name", "?"))
    events.record(session_id, user_id, events.query_event(session_id, intent, blueprint))
    blueprint.pop("all_candidate_scores", None)  # never sent; candidate_count carries the size
    return blueprint

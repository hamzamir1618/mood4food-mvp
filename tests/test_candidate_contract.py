"""
Candidates travel from Tier 1 to Tier 2 through the session store as Candidate models.
A field the model doesn't declare is silently dropped on the way, so the decision core
would score without it. This guards every field scoring reads.
"""

from tier_1.contracts.schemas import CandidateEvaluation
from tier_2.scoring import build_preferences, score_dish

TIER1_CANDIDATE = {
    "dish_id": "abc",
    "name": "Chicken Karahi",
    "restaurant_name": "Savour Foods",
    "price_pkr": 1200.0,
    "price_status": "verified",
    "serves_min": 2,
    "serves_max": 3,
    "macros": {"calories": 650.0, "protein_g": 40.0, "carbs_g": 20.0, "fat_g": 45.0},
    "nutrition_confidence": "medium",
    "nutrition_flag": None,
    "review_status": "auto_imported",
    "taste_source": "keyword",
    "allergens": None,
    "category": "desi_traditional",
    "taste_profile": {"salty": 0.6, "umami": 0.8, "spice": 0.7},
    "ingredients": ["chicken", "tomato"],
}


def test_every_field_scoring_reads_survives_the_session_store():
    stored = CandidateEvaluation.model_validate_json(
        CandidateEvaluation(safe_candidates=[TIER1_CANDIDATE]).model_dump_json()
    )
    candidate = stored.model_dump()["safe_candidates"][0]
    for key in (
        "restaurant_name",
        "price_status",
        "serves_min",
        "serves_max",
        "macros",
        "nutrition_confidence",
        "review_status",
        "taste_source",
        "allergens",
    ):
        assert candidate[key] == TIER1_CANDIDATE[key], key

    # and so the round trip scores exactly like the original
    prefs = build_preferences({"budget_max_pkr": 1500})
    scoring_output = ("u_health", "u_budget", "u_taste", "u_total", "confidence", "reasons")
    after, before = score_dish(candidate, prefs), score_dish(TIER1_CANDIDATE, prefs)
    assert {k: after[k] for k in scoring_output} == {k: before[k] for k in scoring_output}


# The same trap, one hop further on: a scored dish is a *new* dict, and the winner is built
# from a named list of its fields. A field that survives the store can still be dropped there,
# which is how "how we know this" arrived with two of its seven lines (2026-09-26).
PROVENANCE_FIELDS = (
    "review_status",
    "name_status",
    "price_status",
    "price_note",
    "ingredients_basis",
    "allergens_known",
    "nutrition_confidence",
    "taste_source",
    "ingredients_named",
    "ingredients_typical",
    "nutrition_defaults",
    "category_source",
    "category_before",
    "halal_note",
    "is_halal",
    "location_precision",
    "source",
    "source_date",
)
WITH_HISTORY = {
    **TIER1_CANDIDATE,
    "name_status": "fixed_by_owner",
    "price_note": "confirmed by a reviewer",
    "ingredients_basis": "named + typical ingredients",
    "ingredients_named": ["chicken"],
    "ingredients_typical": ["chicken", "cooking oil"],
    "allergens_known": True,
    "allergens": ["gluten"],
    "nutrition_defaults": ["onion"],
    "category_source": "llm:openai/gpt-oss-120b (a side is an add-on)",
    "category_before": "starters",
    "halal_note": "no pork or alcohol detected",
    "is_halal": True,
    "location_precision": "area",
    "source": "https://example.com/menu",
    "source_date": "2026-08-24",
}


def test_how_we_know_this_survives_all_the_way_to_the_card():
    from tier_2.consensus_manager import WINNER_FIELDS
    from ui.provenance import lines

    stored = CandidateEvaluation.model_validate_json(
        CandidateEvaluation(safe_candidates=[WITH_HISTORY]).model_dump_json()
    )
    candidate = stored.model_dump()["safe_candidates"][0]
    scored = score_dish(candidate, build_preferences({}))
    for field in PROVENANCE_FIELDS:
        assert candidate[field] == WITH_HISTORY[field], f"{field} lost in the session store"
        assert scored[field] == WITH_HISTORY[field], f"{field} lost when the dish was scored"
        assert field in WINNER_FIELDS, f"{field} never reaches the winning dish"

    winner = {k: scored.get(k) for k in WINNER_FIELDS}
    assert len(lines(winner)) >= 11, lines(winner)


def test_every_history_field_is_declared_in_all_five_places():
    """
    A field about how a dish is known has to be named five times to arrive: in the Cypher
    projection, in the candidate dict Tier 1 builds from it, in the Candidate model, in the
    dict score_dish returns, and in WINNER_FIELDS. Miss one and the panel silently loses a
    line — which is how the first four were lost. This reads the source and checks all five.
    """
    import inspect

    from tier_1 import symbolic_anchoring
    from tier_1.contracts.schemas import Candidate
    from tier_2 import scoring
    from tier_2.consensus_manager import WINNER_FIELDS

    prune = inspect.getsource(symbolic_anchoring.query_safe_candidates)
    scored = inspect.getsource(scoring.score_dish)
    for field in PROVENANCE_FIELDS:
        assert f"d.{field} AS {field}" in symbolic_anchoring.PRUNE_CYPHER, f"{field}: not queried"
        assert f'"{field}": record.get("{field}")' in prune, f"{field}: not put on the candidate"
        assert field in Candidate.model_fields, f"{field}: not in the candidate contract"
        assert f'"{field}"' in scored, f"{field}: dropped when the dish is scored"
        assert field in WINNER_FIELDS, f"{field}: never reaches the winning dish"

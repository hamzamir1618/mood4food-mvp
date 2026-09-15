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

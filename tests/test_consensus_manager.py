from tier_1.contracts.schemas import DecisionBlueprint
from tier_2.consensus_manager import build_blueprint, run_debate, shortlist
from tier_2.scoring import build_preferences

CANDIDATE = {
    "dish_id": "test_1",
    "name": "Test Dish",
    "price_pkr": 350.0,
    "price_status": "trusted",
    "taste_source": "original",
    "nutrition_confidence": "high",
    "macros": {"calories": 400.0, "protein_g": 30.0, "carbs_g": 40.0, "fat_g": 12.0},
    "taste_profile": {
        "sweet": 0.5,
        "salty": 0.5,
        "sour": 0.0,
        "bitter": 0.0,
        "umami": 0.0,
        "spice": 0.0,
    },
}


def test_debate_names_a_winner_and_explains_it():
    result = run_debate([CANDIDATE], build_preferences({"budget_max_pkr": 500}))
    winner = result["winner"]
    assert winner["dish_id"] == "test_1"
    assert 0.0 <= winner["u_total"] <= 1.0
    assert set(result["final_weights"]) == {"w_h", "w_b", "w_t"}

    joined = "\n".join(result["xai_traces"])
    for agent in ("Health Agent:", "Budget Agent:", "Taste Agent:"):
        assert agent in joined
    assert "Rs 350, within your Rs 500 limit." in joined


def test_the_blueprint_carries_the_winners_reasons_and_not_the_full_pool():
    evaluation = {"source_intent": {"budget_max_pkr": 500}, "safe_candidates": [CANDIDATE]}
    debate = run_debate([CANDIDATE], build_preferences({"budget_max_pkr": 500}))
    blueprint = build_blueprint(debate, evaluation)
    assert blueprint["winning_dish"]["reasons"]["budget"] == "Rs 350, within your Rs 500 limit."
    assert blueprint["candidate_count"] == 1 and "all_candidate_scores" not in blueprint
    assert blueprint["utility_breakdown"]["u_total"] == blueprint["top_candidates"][0]["u_total"]
    assert blueprint["relaxation_notice"] is None
    DecisionBlueprint.model_validate(blueprint)  # the API's response model accepts it


def test_no_candidates_means_no_winner():
    blueprint = build_blueprint(run_debate([], build_preferences({})), {"message": "No matches"})
    assert blueprint["winning_dish"] is None
    assert blueprint["relaxation_notice"] == "No matches"


def test_the_last_shortlist_place_goes_to_something_different():
    ranked = [
        {"dish_id": f"d{i}", "name": f"D{i}", "category": "fast_food", "u_total": 0.9 - i / 100}
        for i in range(6)
    ]
    different = {"dish_id": "x", "name": "X", "category": "afghan", "u_total": 0.8}
    top = shortlist([*ranked, different])
    assert [c["dish_id"] for c in top] == ["d0", "d1", "d2", "d3", "x"]
    assert top[-1]["exploration"] is True
    assert top[-1]["reasons"]["exploration"] == "Something different: an afghan dish."
    # nothing different scores close enough to the winner: the plain top five
    too_weak = {**different, "u_total": 0.3}
    assert [c["dish_id"] for c in shortlist([*ranked, too_weak])] == ["d0", "d1", "d2", "d3", "d4"]

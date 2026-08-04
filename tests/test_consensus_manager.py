from tier_2.consensus_manager import run_debate


def test_consensus_xai_trace_and_sum():
    # Setup candidate
    candidate = {
        "dish_id": "test_1",
        "name": "Test Dish",
        "price_pkr": 350.0,
        "protein_g": 30.0,
        "calories": 400.0,
        "taste_profile": {
            "sweet": 0.5,
            "salty": 0.5,
            "sour": 0.0,
            "bitter": 0.0,
            "umami": 0.0,
            "spice": 0.0,
        },
    }

    candidates = [candidate]
    budget_max = 500

    # Run the debate pipeline directly
    result = run_debate(candidates=candidates, mood_vector=[], budget_max=budget_max)

    # Assert winner is found
    assert result["winner"]["dish_id"] == "test_1"

    winner = result["winner"]
    u_h = winner["u_health"]
    u_b = winner["u_budget"]
    u_t = winner["u_taste"]
    u_total = winner["u_total"]

    weights = result["final_weights"]
    w_h = weights["w_h"]
    w_b = weights["w_b"]
    w_t = weights["w_t"]

    # Calculate sum of weight-adjusted contributions
    w_h_contrib = w_h * u_h
    w_b_contrib = w_b * u_b
    w_t_contrib = w_t * u_t

    expected_sum = w_h_contrib + w_b_contrib + w_t_contrib

    # Assert the sum matches the final U_total (which is rounded to 6 decimals inside run_debate)
    assert abs(u_total - round(expected_sum, 6)) < 1e-9

    # Inspect XAI trace to ensure strings match requirements
    traces = result["xai_traces"]

    trace_joined = "\n".join(traces)
    assert "Health Agent:" in trace_joined
    assert "Budget Agent:" in trace_joined
    assert "Taste Agent:" in trace_joined
    assert "Rs. 350.0 well under your Rs. 500 limit" in trace_joined

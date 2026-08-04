from tier_2.consensus_manager import run_debate_pipeline


def test_top_candidates_ranked_correctly(monkeypatch):
    """
    Test that the consensus manager pipeline computes and returns a ranked list
    of the top 5 candidates in the decision blueprint, correctly sorted by u_total.
    """
    # Create 6 candidates with varying simulated u_total scores.
    # To control their final scores, we mock the Agents.
    candidates = [
        {
            "dish_id": "cand_1",
            "name": "Dish 1",
            "price_pkr": 100,
            "taste_profile": {},
            "u_health": 0.1,
            "u_budget": 0.1,
            "u_taste": 0.1,
        },
        {
            "dish_id": "cand_2",
            "name": "Dish 2",
            "price_pkr": 100,
            "taste_profile": {},
            "u_health": 0.5,
            "u_budget": 0.5,
            "u_taste": 0.5,
        },
        {
            "dish_id": "cand_3",
            "name": "Dish 3",
            "price_pkr": 100,
            "taste_profile": {},
            "u_health": 0.9,
            "u_budget": 0.9,
            "u_taste": 0.9,
        },
        {
            "dish_id": "cand_4",
            "name": "Dish 4",
            "price_pkr": 100,
            "taste_profile": {},
            "u_health": 0.3,
            "u_budget": 0.3,
            "u_taste": 0.3,
        },
        {
            "dish_id": "cand_5",
            "name": "Dish 5",
            "price_pkr": 100,
            "taste_profile": {},
            "u_health": 0.7,
            "u_budget": 0.7,
            "u_taste": 0.7,
        },
        {
            "dish_id": "cand_6",
            "name": "Dish 6",
            "price_pkr": 100,
            "taste_profile": {},
            "u_health": 0.2,
            "u_budget": 0.2,
            "u_taste": 0.2,
        },
    ]

    # Let's mock load_contract to return these candidates
    def mock_load_contract(session_id, key):
        if key == "candidate_evaluation":
            return {
                "safe_candidates": candidates,
                "source_intent": {"budget_max_pkr": 1000},
                "soft_constraints": {},
            }
        return None

    # Mock save_contract so we can capture the output blueprint
    saved_blueprint = {}

    def mock_save_contract(session_id, key, value):
        if key == "decision_blueprint":
            saved_blueprint.update(value)

    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", mock_load_contract)
    monkeypatch.setattr("tier_1.contracts.session_store.save_contract", mock_save_contract)

    # Mock vector store so we don't try to use chromadb
    monkeypatch.setattr("tier_2.consensus_manager.get_vector_store", lambda: None)
    monkeypatch.setattr("tier_2.consensus_manager.retrieve_mood_vector", lambda store, seed: [])

    # Map dish_id to scores so agents can retrieve them without needing
    # them to be passed through Candidate
    score_map = {c["dish_id"]: c for c in candidates}

    # Mock agent scoring so the provided raw values translate into u_total properly
    monkeypatch.setattr(
        "tier_2.agents.HealthAgent.score",
        lambda self, cand: score_map[cand.dish_id].get("u_health", 0.0),
    )
    monkeypatch.setattr(
        "tier_2.agents.BudgetAgent.score",
        lambda self, cand: score_map[cand.dish_id].get("u_budget", 0.0),
    )
    monkeypatch.setattr(
        "tier_2.agents.TasteAgent.score",
        lambda self, cand: score_map[cand.dish_id].get("u_taste", 0.0),
    )

    # Run the debate pipeline
    run_debate_pipeline("test_session")

    # Assert blueprint is populated
    assert "top_candidates" in saved_blueprint
    top_cands = saved_blueprint["top_candidates"]

    # We provided 6 candidates, we only expect top 5
    assert len(top_cands) == 5

    # Check they are sorted by u_total descending
    u_totals = [cand["u_total"] for cand in top_cands]
    assert u_totals == sorted(u_totals, reverse=True)

    # Dish 3 should be the winner (highest stats)
    assert top_cands[0]["dish_id"] == "cand_3"
    assert saved_blueprint["winning_dish"]["dish_id"] == "cand_3"

    # The lowest stats (Dish 1 with 0.1 and Dish 6 with 0.2)
    # So top 5 should be cand_3, cand_5, cand_2, cand_4, cand_6
    assert [cand["dish_id"] for cand in top_cands] == [
        "cand_3",
        "cand_5",
        "cand_2",
        "cand_4",
        "cand_6",
    ]

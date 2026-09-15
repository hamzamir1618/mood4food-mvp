from tier_2.consensus_manager import run_debate_pipeline


def test_top_candidates_ranked_correctly(monkeypatch):
    """
    The blueprint keeps the five best candidates, best first, and the best one wins.
    Each dish's score is fixed here, so this checks ranking and selection, not formulas.
    """
    totals = {
        "cand_1": 0.1,
        "cand_2": 0.5,
        "cand_3": 0.9,
        "cand_4": 0.3,
        "cand_5": 0.7,
        "cand_6": 0.2,
    }
    candidates = [{"dish_id": k, "name": f"Dish {k[-1]}", "price_pkr": 100} for k in totals]

    def mock_load_contract(session_id, key):
        if key == "candidate_evaluation":
            return {
                "safe_candidates": candidates,
                "source_intent": {"budget_max_pkr": 1000},
                "soft_constraints": {},
            }
        return None

    saved_blueprint = {}

    def mock_save_contract(session_id, key, value):
        if key == "decision_blueprint":
            saved_blueprint.update(value)

    def fixed_score(dish, prefs):
        return {
            **dish,
            "u_health": None,
            "u_budget": None,
            "u_taste": None,
            "u_context": None,
            "u_total": totals[dish["dish_id"]],
            "confidence": {},
            "reasons": {},
        }

    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", mock_load_contract)
    monkeypatch.setattr("tier_1.contracts.session_store.save_contract", mock_save_contract)
    monkeypatch.setattr("tier_2.scoring.score_dish", fixed_score)

    run_debate_pipeline("test_session")

    top = saved_blueprint["top_candidates"]
    assert len(top) == 5
    assert [c["u_total"] for c in top] == sorted((c["u_total"] for c in top), reverse=True)
    assert saved_blueprint["winning_dish"]["dish_id"] == "cand_3"
    assert [c["dish_id"] for c in top] == ["cand_3", "cand_5", "cand_2", "cand_4", "cand_6"]
    assert saved_blueprint["candidate_count"] == 6

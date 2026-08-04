from tier_2.consensus_manager import run_debate_pipeline


def test_blueprint_relaxation_no_relaxation(monkeypatch):
    """Test when no relaxation occurred, the notice is None."""
    candidates = [{"dish_id": "cand_1", "name": "Dish 1", "u_total": 0.9}]

    def mock_load_contract(session_id, key):
        if key == "candidate_evaluation":
            return {
                "safe_candidates": candidates,
                "message": "",  # Empty message means no relaxation
            }
        return None

    saved_blueprint = {}

    def mock_save_contract(session_id, key, value):
        if key == "decision_blueprint":
            saved_blueprint.update(value)

    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", mock_load_contract)
    monkeypatch.setattr("tier_1.contracts.session_store.save_contract", mock_save_contract)
    monkeypatch.setattr("tier_2.consensus_manager.get_vector_store", lambda: None)
    monkeypatch.setattr("tier_2.consensus_manager.retrieve_mood_vector", lambda store, seed: [])
    monkeypatch.setattr(
        "tier_2.agents.HealthAgent.score", lambda self, cand: getattr(cand, "u_health", 0.0)
    )
    monkeypatch.setattr(
        "tier_2.agents.BudgetAgent.score", lambda self, cand: getattr(cand, "u_budget", 0.0)
    )
    monkeypatch.setattr(
        "tier_2.agents.TasteAgent.score", lambda self, cand: getattr(cand, "u_taste", 0.0)
    )

    run_debate_pipeline("test_session")

    assert saved_blueprint["relaxation_notice"] is None
    assert saved_blueprint["winning_dish"]["dish_id"] == "cand_1"


def test_blueprint_relaxation_one_step(monkeypatch):
    """Test when one relaxation occurred, the message is populated."""
    candidates = [{"dish_id": "cand_1", "name": "Dish 1", "u_total": 0.9}]

    def mock_load_contract(session_id, key):
        if key == "candidate_evaluation":
            return {
                "safe_candidates": candidates,
                "message": "No exact match under Rs. 500 — showing options up to Rs. 600",
            }
        return None

    saved_blueprint = {}

    def mock_save_contract(session_id, key, value):
        if key == "decision_blueprint":
            saved_blueprint.update(value)

    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", mock_load_contract)
    monkeypatch.setattr("tier_1.contracts.session_store.save_contract", mock_save_contract)
    monkeypatch.setattr("tier_2.consensus_manager.get_vector_store", lambda: None)
    monkeypatch.setattr("tier_2.consensus_manager.retrieve_mood_vector", lambda store, seed: [])
    monkeypatch.setattr(
        "tier_2.agents.HealthAgent.score", lambda self, cand: getattr(cand, "u_health", 0.0)
    )
    monkeypatch.setattr(
        "tier_2.agents.BudgetAgent.score", lambda self, cand: getattr(cand, "u_budget", 0.0)
    )
    monkeypatch.setattr(
        "tier_2.agents.TasteAgent.score", lambda self, cand: getattr(cand, "u_taste", 0.0)
    )

    run_debate_pipeline("test_session")

    assert (
        saved_blueprint["relaxation_notice"]
        == "No exact match under Rs. 500 — showing options up to Rs. 600"
    )
    assert saved_blueprint["winning_dish"]["dish_id"] == "cand_1"


def test_blueprint_relaxation_true_zero_match(monkeypatch):
    """Test when even after relaxation there are 0 candidates, winning_dish is None."""
    candidates = []

    def mock_load_contract(session_id, key):
        if key == "candidate_evaluation":
            return {
                "safe_candidates": candidates,
                "message": "No matches even after maximum relaxation attempts.",
            }
        return None

    saved_blueprint = {}

    def mock_save_contract(session_id, key, value):
        if key == "decision_blueprint":
            saved_blueprint.update(value)

    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", mock_load_contract)
    monkeypatch.setattr("tier_1.contracts.session_store.save_contract", mock_save_contract)
    monkeypatch.setattr("tier_2.consensus_manager.get_vector_store", lambda: None)
    monkeypatch.setattr("tier_2.consensus_manager.retrieve_mood_vector", lambda store, seed: [])
    monkeypatch.setattr(
        "tier_2.agents.HealthAgent.score", lambda self, cand: getattr(cand, "u_health", 0.0)
    )
    monkeypatch.setattr(
        "tier_2.agents.BudgetAgent.score", lambda self, cand: getattr(cand, "u_budget", 0.0)
    )
    monkeypatch.setattr(
        "tier_2.agents.TasteAgent.score", lambda self, cand: getattr(cand, "u_taste", 0.0)
    )

    run_debate_pipeline("test_session")

    assert (
        saved_blueprint["relaxation_notice"] == "No matches even after maximum relaxation attempts."
    )
    assert saved_blueprint["winning_dish"] is None

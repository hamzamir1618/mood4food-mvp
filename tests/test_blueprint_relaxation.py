from tier_2.consensus_manager import run_debate_pipeline


def _run(monkeypatch, candidates: list, message: str) -> dict:
    def mock_load_contract(session_id, key):
        if key == "candidate_evaluation":
            return {"safe_candidates": candidates, "message": message}
        return None

    saved_blueprint = {}

    def mock_save_contract(session_id, key, value):
        if key == "decision_blueprint":
            saved_blueprint.update(value)

    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", mock_load_contract)
    monkeypatch.setattr("tier_1.contracts.session_store.save_contract", mock_save_contract)
    run_debate_pipeline("test_session")
    return saved_blueprint


def test_blueprint_relaxation_no_relaxation(monkeypatch):
    """When no relaxation occurred, the notice is None."""
    blueprint = _run(monkeypatch, [{"dish_id": "cand_1", "name": "Dish 1"}], "")
    assert blueprint["relaxation_notice"] is None
    assert blueprint["winning_dish"]["dish_id"] == "cand_1"


def test_blueprint_relaxation_one_step(monkeypatch):
    """When Tier 1 relaxed a constraint, its message is passed through word for word."""
    message = "No exact match under Rs. 500 — showing options up to Rs. 600"
    blueprint = _run(monkeypatch, [{"dish_id": "cand_1", "name": "Dish 1"}], message)
    assert blueprint["relaxation_notice"] == message
    assert blueprint["winning_dish"]["dish_id"] == "cand_1"


def test_blueprint_relaxation_true_zero_match(monkeypatch):
    """With no candidates even after relaxation, there is no winner and the notice stays."""
    message = "No matches even after maximum relaxation attempts."
    blueprint = _run(monkeypatch, [], message)
    assert blueprint["relaxation_notice"] == message
    assert blueprint["winning_dish"] is None

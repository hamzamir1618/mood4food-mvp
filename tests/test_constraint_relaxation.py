from tier_1.symbolic_anchoring import run_anchoring_pipeline


def test_no_relaxation(monkeypatch):
    intent = {"budget_max_pkr": 1000, "allergens_pruned": []}
    monkeypatch.setattr("tier_1.symbolic_anchoring.load_grounded_intent", lambda: intent)

    # Mock query to return candidates on first try
    monkeypatch.setattr(
        "tier_1.symbolic_anchoring.query_safe_candidates",
        lambda allergens, budget: [{"dish_id": "1"}],
    )
    monkeypatch.setattr("tier_1.symbolic_anchoring.write_candidate_evaluation", lambda *args: None)

    result = run_anchoring_pipeline()
    assert result["candidate_count"] == 1
    assert len(result["relaxations"]) == 0
    assert "Found" in result["message"]


def test_one_relaxation(monkeypatch):
    intent = {"budget_max_pkr": 100, "allergens_pruned": []}
    monkeypatch.setattr("tier_1.symbolic_anchoring.load_grounded_intent", lambda: intent)

    # Mock query to return candidates ONLY if budget is >= 115
    def mock_query(allergens, budget):
        if budget >= 115:
            return [{"dish_id": "2"}]
        return []

    monkeypatch.setattr("tier_1.symbolic_anchoring.query_safe_candidates", mock_query)
    monkeypatch.setattr("tier_1.symbolic_anchoring.write_candidate_evaluation", lambda *args: None)

    result = run_anchoring_pipeline()
    assert result["candidate_count"] == 1
    assert len(result["relaxations"]) == 1
    assert result["relaxations"][0]["new_value"] == 120.0
    assert "Found" in result["message"]


def test_max_relaxation_fails(monkeypatch):
    intent = {"budget_max_pkr": 10, "allergens_pruned": ["dairy"]}
    monkeypatch.setattr("tier_1.symbolic_anchoring.load_grounded_intent", lambda: intent)

    # Mock query to ALWAYS return []
    def mock_query(allergens, budget):
        # Assert allergen is never dropped
        assert allergens == ["dairy"]
        return []

    monkeypatch.setattr("tier_1.symbolic_anchoring.query_safe_candidates", mock_query)
    monkeypatch.setattr("tier_1.symbolic_anchoring.write_candidate_evaluation", lambda *args: None)

    result = run_anchoring_pipeline()
    assert result["candidate_count"] == 0
    assert len(result["relaxations"]) == 2  # Max 2 relaxations
    assert "No matches even after maximum relaxation attempts" in result["message"]

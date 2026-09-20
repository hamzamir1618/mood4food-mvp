"""
Tier 1 constraint-relaxation behaviour.

Budget is deliberately NOT relaxed. An explicitly stated budget ceiling is a hard
must-have (Tier 1 = hard constraints, Tier 2 = soft trade-offs), so a dish over
budget is eliminated rather than down-scored. The relaxations that do exist are
the preferred-category drop and the dominant-mood relevance floor.

These tests previously mocked a two-argument `query_safe_candidates` and asserted
a budget-relaxation ladder that was removed when budget became a hard filter.
"""

import pytest

from tier_1.symbolic_anchoring import run_anchoring_pipeline

TASTE_KEYS = ("sweet", "salty", "sour", "bitter", "umami", "spice")


@pytest.fixture(autouse=True)
def no_contract_writes(monkeypatch):
    """Keep the pipeline off disk; these tests exercise control flow only."""
    monkeypatch.setattr(
        "tier_1.symbolic_anchoring.write_candidate_evaluation", lambda *a, **k: None
    )


def _dish(name, **taste):
    profile = dict.fromkeys(TASTE_KEYS, 0.0)
    profile.update(taste)
    return {"dish_id": name, "name": name, "taste_profile": profile}


def test_no_relaxation_when_enough_candidates(monkeypatch):
    monkeypatch.setattr(
        "tier_1.symbolic_anchoring.query_safe_candidates",
        lambda allergens, budget, category="", vegan=False, veg=False, **_: [
            _dish("a"),
            _dish("b"),
            _dish("c"),
        ],
    )

    result = run_anchoring_pipeline({"budget_max_pkr": 1000, "allergens_pruned": []})

    assert result["candidate_count"] == 3
    assert result["relaxations"] == []
    # The message reaches the user as the notice above the pick, so it stays empty when
    # nothing was given up. It used to carry a count written for the logs.
    assert result["message"] == ""


def test_preferred_category_is_relaxed_when_too_few_matches(monkeypatch):
    calls = []

    def mock_query(allergens, budget, category="", vegan=False, veg=False, **_):
        calls.append(category)
        if category:
            return [_dish("only-one")]  # below the 3-candidate floor
        return [_dish("a"), _dish("b"), _dish("c")]

    monkeypatch.setattr("tier_1.symbolic_anchoring.query_safe_candidates", mock_query)

    result = run_anchoring_pipeline(
        {"budget_max_pkr": 1000, "allergens_pruned": [], "preferred_category": "seafood"}
    )

    assert calls == ["seafood", ""], "category should be dropped on the retry"
    assert result["candidate_count"] == 3

    relaxations = result["relaxations"]
    assert len(relaxations) == 1
    assert relaxations[0]["constraint"] == "preferred_category"
    assert relaxations[0]["old_value"] == "seafood"
    assert relaxations[0]["new_value"] is None
    # ...and the user is told, rather than being handed a substitute as though it matched.
    assert "seafood" in result["message"]
    assert result["message"].startswith("I couldn't find")


def test_budget_is_never_relaxed(monkeypatch):
    """A stated budget ceiling is a hard constraint, not a soft preference."""
    budgets = []

    def mock_query(allergens, budget, category="", vegan=False, veg=False, **_):
        budgets.append(budget)
        return []

    monkeypatch.setattr("tier_1.symbolic_anchoring.query_safe_candidates", mock_query)

    result = run_anchoring_pipeline({"budget_max_pkr": 250, "allergens_pruned": []})

    assert set(budgets) == {250}, f"budget was altered across retries: {budgets}"
    assert result["candidate_count"] == 0
    assert "No matches" in result["message"]


def test_allergens_are_never_dropped(monkeypatch):
    """Safety constraint: allergens must survive every relaxation round."""
    seen = []

    def mock_query(allergens, budget, category="", vegan=False, veg=False, **_):
        seen.append(list(allergens))
        return []

    monkeypatch.setattr("tier_1.symbolic_anchoring.query_safe_candidates", mock_query)

    run_anchoring_pipeline(
        {
            "budget_max_pkr": 10,
            "allergens_pruned": ["dairy"],
            "preferred_category": "cheese",
        }
    )

    assert seen, "query_safe_candidates was never called"
    assert all(a == ["dairy"] for a in seen), seen


def test_dominant_mood_relevance_floor_relaxes_rather_than_empty_handing(monkeypatch):
    """
    A strongly stated craving imposes a minimum-relevance floor, but when nothing
    clears it the filter is relaxed instead of returning an empty result.
    """
    weak_matches = [_dish(f"weak{i}", sweet=0.1) for i in range(5)]
    monkeypatch.setattr(
        "tier_1.symbolic_anchoring.query_safe_candidates",
        lambda allergens, budget, category="", vegan=False, veg=False, **_: weak_matches,
    )

    result = run_anchoring_pipeline(
        {
            "budget_max_pkr": 1000,
            "allergens_pruned": [],
            "mood_vector": dict(dict.fromkeys(TASTE_KEYS, 0.0), sweet=0.9),
        }
    )

    assert result["candidate_count"] == 5, "filter should have been relaxed, not applied"
    assert any(r["constraint"] == "minimum_relevance_sweet" for r in result["relaxations"]), result[
        "relaxations"
    ]

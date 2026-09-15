"""
Phase 4 learning rules (accounts/learning.py). Pure: no database.
"""

import random

import pytest

from accounts import learning
from accounts.models import TASTE_DIMS, TasteModel
from tier_2.scoring import build_preferences, score_dish

SPICY = {"sweet": 0.1, "salty": 0.5, "sour": 0.1, "bitter": 0.0, "umami": 0.5, "spice": 0.9}


def test_an_approval_moves_taste_toward_the_dish_by_a_shrinking_step():
    start = TasteModel.from_persona("balanced")  # spice 0.4
    once, said = learning.update_taste(start, SPICY, trust=1.0)
    assert once.vector["spice"] == pytest.approx(0.4 + 0.3 * (0.9 - 0.4))
    assert once.updates == 1 and once.has_evidence()
    assert "spicy 0.40 → 0.55" in said[0]
    twice, _ = learning.update_taste(once, SPICY, trust=1.0)
    assert twice.vector["spice"] - once.vector["spice"] < once.vector["spice"] - 0.4


def test_a_flavour_we_only_estimated_teaches_less():
    start = TasteModel.from_persona("balanced")
    trusted, _ = learning.update_taste(start, SPICY, trust=1.0)
    estimated, _ = learning.update_taste(start, SPICY, trust=0.25)
    assert estimated.vector["spice"] - 0.4 == pytest.approx((trusted.vector["spice"] - 0.4) / 4)


def test_a_consistent_user_reshapes_the_model_within_ten_approvals():
    # The plan's exit criterion: someone who keeps approving spicy food, whatever else
    # the dish is like, measurably moves their model in about ten approvals.
    rng = random.Random(1)
    model, approved = TasteModel.from_persona("balanced"), []
    for _ in range(10):
        dish_taste = {d: rng.random() for d in TASTE_DIMS} | {"spice": 0.9}
        approved.append(dish_taste)
        model, _ = learning.update_taste(model, dish_taste, trust=1.0)
    model = model.model_copy(update={"importance": learning.learned_importance(approved)})

    assert model.vector["spice"] > 0.8  # from the persona's 0.4
    assert max(model.importance, key=model.importance.get) == "spice"
    # with no craving in the query, a spicy dish now beats an otherwise identical mild one
    prefs = build_preferences({}, {"taste": model.vector, "importance": model.importance})

    def with_spice(level: float) -> dict:
        taste = {**model.vector, "spice": level}
        return {"dish_id": "x", "name": "x", "taste_source": "original", "taste_profile": taste}

    assert (
        score_dish(with_spice(0.9), prefs)["u_taste"]
        > score_dish(with_spice(0.1), prefs)["u_taste"]
    )


def test_importance_needs_a_few_approvals_and_stays_in_range():
    assert learning.learned_importance([SPICY, SPICY]) is None
    importance = learning.learned_importance(
        [SPICY, {**SPICY, "sweet": 0.9}, {**SPICY, "sweet": 0.5}]
    )
    low, high = learning.IMPORTANCE_RANGE
    assert all(low <= v <= high for v in importance.values())
    assert importance["sweet"] < importance["spice"]  # sweetness varied, spice didn't


def test_choosing_a_cheaper_runner_up_makes_price_count_more():
    weights = {"w_health": 0.34, "w_budget": 0.33, "w_taste": 0.33}
    chosen = {"u_health": 0.5, "u_budget": 1.0, "u_taste": 0.6}
    top = {"u_health": 0.6, "u_budget": 0.4, "u_taste": 0.7}
    moved, said = learning.nudge_weights(weights, chosen, top, updates=0)
    assert moved["w_budget"] > weights["w_budget"]
    assert sum(moved.values()) == pytest.approx(1.0)
    assert min(moved.values()) >= learning.MIN_WEIGHT / sum(moved.values())
    assert "price" in said[0]


def test_unassessed_utilities_and_ties_teach_nothing():
    weights = {"w_health": 0.34, "w_budget": 0.33, "w_taste": 0.33}
    chosen = {"u_health": None, "u_budget": 0.5, "u_taste": 0.5}
    top = {"u_health": 0.9, "u_budget": 0.5, "u_taste": 0.5}
    assert learning.nudge_weights(weights, chosen, top, 0) == (weights, [])


def test_the_summary_says_what_was_learned_in_plain_words():
    assert learning.learning_summary(TasteModel.from_persona("balanced"))["approvals"] == 0
    model = TasteModel.from_persona("balanced")
    for _ in range(5):
        model, _ = learning.update_taste(model, SPICY, 1.0)
    summary = learning.learning_summary(model)
    assert summary["approvals"] == 5
    assert any("more spicy" in line for line in summary["summary"])
    assert summary["summary"][-1].startswith("Learned from 5 approvals")

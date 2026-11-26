"""
Unit tests for hybrid semantic–symbolic context retrieval (tier_2/semantic_index.py
and the semantic term in tier_2/scoring.py).
"""

import pytest

from tier_2.scoring import SEMANTIC_CONFIDENCE, Preferences, rank, score_dish, semantic_term
from tier_2.semantic_index import (
    SEMANTIC_CEIL,
    SEMANTIC_FLOOR,
    calibrate_similarity,
    dish_document,
)


def _base_prefs(**overrides) -> Preferences:
    defaults = dict(
        taste={"sweet": 0.2, "salty": 0.4, "sour": 0.2, "bitter": 0.1, "umami": 0.5, "spice": 0.4},
        weights={"w_health": 1 / 3, "w_budget": 1 / 3, "w_taste": 1 / 3},
        goal="balanced",
    )
    defaults.update(overrides)
    return Preferences(**defaults)


def _sample_dish(dish_id: str, name: str, category: str, **extra) -> dict:
    base = {
        "dish_id": dish_id,
        "name": name,
        "category": category,
        "price_pkr": 900.0,
        "price_status": "trusted",
        "macros": {"calories": 550, "protein_g": 28, "carbs_g": 45, "fat_g": 22},
        "nutrition_confidence": "high",
        "taste_profile": {
            "sweet": 0.1,
            "salty": 0.4,
            "sour": 0.1,
            "bitter": 0.0,
            "umami": 0.6,
            "spice": 0.5,
        },
        "taste_source": "original",
        "ingredients": [],
    }
    base.update(extra)
    return base


def test_dish_document_captures_culinary_and_occasion_context():
    doc = dish_document(
        {
            "dish_name": "Hot & Sour Soup",
            "category": "chinese_asian",
            "ingredients": ["chicken", "mushroom", "vinegar", "black pepper"],
            "taste_spice": 0.6,
            "taste_sour": 0.5,
            "calories": 280,
            "protein_g": 18,
            "serves_max": 2,
        }
    )
    assert "Hot & Sour Soup" in doc
    assert "warm comforting rainy cold weather" in doc
    assert "spicy" in doc
    assert "tangy" in doc
    assert "sharing" in doc


def test_calibrate_similarity_uses_fixed_honest_bounds():
    assert calibrate_similarity(0.05) == 0.0
    assert calibrate_similarity(SEMANTIC_FLOOR) == 0.0
    assert calibrate_similarity(SEMANTIC_CEIL) == 1.0
    assert calibrate_similarity(0.95) == 1.0
    mid = calibrate_similarity((SEMANTIC_FLOOR + SEMANTIC_CEIL) / 2)
    assert mid == pytest.approx(0.5, abs=1e-6)


def test_semantic_term_sits_out_without_scores():
    dish = _sample_dish("d1", "Chicken Karahi", "desi_traditional")
    term = semantic_term(dish, _base_prefs())
    assert term.applies is False


def test_semantic_term_scores_with_honest_confidence_and_reason():
    dish = _sample_dish("d1", "Chicken Karahi", "desi_traditional")
    prefs = _base_prefs(semantic_scores={"d1": 0.58})
    term = semantic_term(dish, prefs)
    assert term.applies is True
    assert term.confidence == SEMANTIC_CONFIDENCE
    assert term.confidence < 1.0
    assert term.utility > 0.8
    assert "semantic fit" in term.sentence


def test_score_dish_prefers_semantically_matching_candidate():
    soup = _sample_dish("d_soup", "Chicken Corn Soup", "chinese_asian")
    cake = _sample_dish("d_cake", "Chocolate Fudge Cake", "cafe_bakery")
    prefs = _base_prefs(semantic_scores={"d_soup": 0.58, "d_cake": 0.18})
    s_soup = score_dish(soup, prefs)
    s_cake = score_dish(cake, prefs)
    assert s_soup["u_semantic"] > s_cake["u_semantic"]
    assert s_soup["u_total"] > s_cake["u_total"]
    assert "semantic" in s_soup["reasons"]


def test_rank_respects_semantic_search_toggle(monkeypatch):
    soup = _sample_dish("d_soup", "Chicken Corn Soup", "chinese_asian")
    salad = _sample_dish("d_salad", "Greek Salad", "cafe_bakery")
    prefs = _base_prefs(query_text="warm comforting soup for a rainy night")

    monkeypatch.setenv("SEMANTIC_SEARCH", "0")
    off_ranked = rank([soup, salad], prefs)
    assert all(r["u_semantic"] is None for r in off_ranked)

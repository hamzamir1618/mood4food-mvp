from unittest.mock import MagicMock

from tier_1.symbolic_anchoring import query_safe_candidates


def test_neo4j_retry_logic(monkeypatch):
    """
    Test that query_safe_candidates retries on failure (2 failures, 1 success)
    and successfully returns data without raising an exception.
    """
    import neo4j

    # Mock driver and session
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    # Mock result
    mock_record = {
        "dish_id": "D001",
        "name": "Test Dish",
        "price_pkr": 100,
        "protein_g": 10,
        "calories": 200,
        "category": "Test",
        "image_url": "",
        "human_tags": [],
        "taste_sweet": 0.1,
        "taste_salty": 0.1,
        "taste_sour": 0.1,
        "taste_bitter": 0.1,
        "taste_umami": 0.1,
        "taste_spice": 0.1,
    }
    mock_session.run.return_value = [mock_record]

    # Create a driver factory that fails twice then succeeds
    attempt = 0

    def mock_graph_database_driver(*args, **kwargs):
        nonlocal attempt
        attempt += 1
        if attempt <= 2:
            raise neo4j.exceptions.ServiceUnavailable("Fake connection error")
        return mock_driver

    monkeypatch.setattr(
        "tier_1.symbolic_anchoring.GraphDatabase.driver", mock_graph_database_driver
    )

    # We also need to speed up time.sleep so the test runs quickly
    monkeypatch.setattr("time.sleep", lambda x: None)

    candidates = query_safe_candidates(["peanut"], 1000)

    assert attempt == 3
    assert len(candidates) == 1
    assert candidates[0]["name"] == "Test Dish"

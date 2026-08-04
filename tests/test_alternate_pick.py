import pytest

from tier_1.contracts.schemas import Candidate, DecisionBlueprint
from tier_2.consensus_manager import get_alternate


@pytest.fixture
def mock_blueprint(monkeypatch):
    def mock_load_contract(session_id, contract_name):
        if contract_name != "decision_blueprint":
            return None

        return DecisionBlueprint(
            active_persona="balanced",
            top_candidates=[
                Candidate(dish_id="D001", name="Rank 1 Dish"),
                Candidate(dish_id="D002", name="Rank 2 Dish"),
                Candidate(dish_id="D003", name="Rank 3 Dish"),
            ],
        )

    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", mock_load_contract)


def test_alternate_first_call_returns_rank_2(mock_blueprint):
    # Exclude rank 1
    alt = get_alternate("test_session", ["D001"])
    assert isinstance(alt, Candidate)
    assert alt.dish_id == "D002"
    assert alt.name == "Rank 2 Dish"


def test_alternate_second_call_returns_rank_3(mock_blueprint):
    # Exclude rank 1 and 2
    alt = get_alternate("test_session", ["D001", "D002"])
    assert isinstance(alt, Candidate)
    assert alt.dish_id == "D003"
    assert alt.name == "Rank 3 Dish"


def test_alternate_exhausted_returns_signal(mock_blueprint):
    # Exclude all top candidates
    alt = get_alternate("test_session", ["D001", "D002", "D003"])
    assert isinstance(alt, dict)
    assert alt.get("error") == "no more alternates"


def test_alternate_empty_blueprint(monkeypatch):
    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", lambda s, c: None)
    alt = get_alternate("test_session", [])
    assert isinstance(alt, dict)
    assert alt.get("error") == "no more alternates"

from tier_1.contracts.schemas import Candidate
from tier_2.agents import HealthAgent


def test_health_agent_perfect_score():
    # 25g protein, 500 cal -> ratio = 0.05 -> normalized to 1.0
    agent = HealthAgent()
    c = Candidate(macros={"protein_g": 25.0, "calories": 500.0})
    assert abs(agent.score(c) - 1.0) < 1e-9


def test_health_agent_low_protein():
    # 10g protein, 800 cal -> ratio = 0.0125 -> normalized to 0.25
    agent = HealthAgent()
    c = Candidate(macros={"protein_g": 10.0, "calories": 800.0})
    assert abs(agent.score(c) - 0.25) < 1e-9


def test_health_agent_excess_protein():
    # 40g protein, 400 cal -> ratio = 0.1 -> normalized to 2.0 -> clamped to 1.0
    agent = HealthAgent()
    c = Candidate(macros={"protein_g": 40.0, "calories": 400.0})
    assert abs(agent.score(c) - 1.0) < 1e-9


def test_health_agent_zero_calories():
    # 10g protein, 0 cal -> edge case, should handle div by zero and return 0.0
    agent = HealthAgent()
    c = Candidate(macros={"protein_g": 10.0, "calories": 0.0})
    assert agent.score(c) == 0.0

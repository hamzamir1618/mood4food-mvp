import math

from tier_1.contracts.schemas import Candidate
from tier_2.agents import BudgetAgent


def test_budget_agent_sensitivity():
    max_budget = 2000.0
    agent = BudgetAgent(max_budget=max_budget)

    # 1. Calculate scores in the low range: Rs. 100, 300, 500
    p100 = Candidate(price_pkr=100.0)
    p300 = Candidate(price_pkr=300.0)
    p500 = Candidate(price_pkr=500.0)

    score_100 = agent.score(p100)
    score_300 = agent.score(p300)
    score_500 = agent.score(p500)

    # Expected hand-calculated values (tolerance 1e-5)
    # U_b = 1 - ln(1 + price) / ln(1 + max_budget)
    assert abs(score_100 - (1 - math.log(101) / math.log(2001))) < 1e-5
    assert abs(score_300 - (1 - math.log(301) / math.log(2001))) < 1e-5
    assert abs(score_500 - (1 - math.log(501) / math.log(2001))) < 1e-5

    delta_low_1 = score_100 - score_300
    delta_low_2 = score_300 - score_500
    avg_delta_low = (score_100 - score_500) / 400.0  # delta per rupee

    # 2. Calculate scores in the high range: Rs. 1500, 1700, 1900
    p1500 = Candidate(price_pkr=1500.0)
    p1700 = Candidate(price_pkr=1700.0)
    p1900 = Candidate(price_pkr=1900.0)

    score_1500 = agent.score(p1500)
    score_1700 = agent.score(p1700)
    score_1900 = agent.score(p1900)

    # Expected hand-calculated values
    assert abs(score_1500 - (1 - math.log(1501) / math.log(2001))) < 1e-5
    assert abs(score_1700 - (1 - math.log(1701) / math.log(2001))) < 1e-5
    assert abs(score_1900 - (1 - math.log(1901) / math.log(2001))) < 1e-5

    delta_high_1 = score_1500 - score_1700
    delta_high_2 = score_1700 - score_1900
    avg_delta_high = (score_1500 - score_1900) / 400.0  # delta per rupee

    # 3. Assert sensitivity difference
    # Log scaling means utility drops faster at lower prices than at higher prices
    assert avg_delta_low > avg_delta_high, (
        f"Low range sensitivity {avg_delta_low} should be > high range {avg_delta_high}"
    )
    assert delta_low_1 > delta_high_1
    assert delta_low_2 > delta_high_2

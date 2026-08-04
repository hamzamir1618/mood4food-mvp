from tier_1.contracts.schemas import Candidate, TasteProfile
from tier_2.agents import BudgetAgent, HealthAgent, TasteAgent


def test_agents_regression():
    # Candidate 1: Chicken Salad
    c1 = Candidate(
        name="Chicken Salad",
        price_pkr=500,
        macros={"protein_g": 30.0, "calories": 300.0},
        taste_profile=TasteProfile(
            sweet=0.1, salty=0.5, sour=0.2, bitter=0.1, umami=0.3, spice=0.1
        ),
    )
    # Candidate 2: Beef Burger
    c2 = Candidate(
        name="Beef Burger",
        price_pkr=1200,
        macros={"protein_g": 25.0, "calories": 800.0},
        taste_profile=TasteProfile(
            sweet=0.2, salty=0.8, sour=0.1, bitter=0.0, umami=0.9, spice=0.2
        ),
    )
    # Candidate 3: Spicy Biryani
    c3 = Candidate(
        name="Spicy Biryani",
        price_pkr=400,
        macros={"protein_g": 15.0, "calories": 600.0},
        taste_profile=TasteProfile(
            sweet=0.0, salty=0.7, sour=0.1, bitter=0.1, umami=0.6, spice=1.0
        ),
    )
    # Candidate 4: Lentil Soup
    c4 = Candidate(
        name="Lentil Soup",
        price_pkr=200,
        macros={"protein_g": 10.0, "calories": 250.0},
        taste_profile=TasteProfile(
            sweet=0.1, salty=0.4, sour=0.0, bitter=0.1, umami=0.4, spice=0.3
        ),
    )
    # Candidate 5: Ice Cream
    c5 = Candidate(
        name="Ice Cream",
        price_pkr=300,
        macros={"protein_g": 2.0, "calories": 400.0},
        taste_profile=TasteProfile(
            sweet=1.0, salty=0.1, sour=0.0, bitter=0.0, umami=0.1, spice=0.0
        ),
    )

    budget_max = 1000
    persona_taste = TasteProfile(sweet=0.2, salty=0.6, sour=0.2, bitter=0.1, umami=0.9, spice=0.5)

    health_agent = HealthAgent()
    budget_agent = BudgetAgent(max_budget=budget_max)
    taste_agent = TasteAgent(persona_taste=persona_taste)

    # 1
    assert abs(health_agent.score(c1) - 1.0) < 1e-9
    assert abs(budget_agent.score(c1) - 0.10018428795629652) < 1e-9
    assert abs(taste_agent.score(c1) - 0.8769375944159772) < 1e-9

    # 2
    assert abs(health_agent.score(c2) - 0.625) < 1e-9
    assert abs(budget_agent.score(c2) - 0.0) < 1e-9
    assert abs(taste_agent.score(c2) - 0.9508656705081013) < 1e-9

    # 3
    assert abs(health_agent.score(c3) - 0.5) < 1e-9
    assert abs(budget_agent.score(c3) - 0.13241074277922527) < 1e-9
    assert abs(taste_agent.score(c3) - 0.8867005778686783) < 1e-9

    # 4
    assert abs(health_agent.score(c4) - 0.7999999999999999) < 1e-9
    assert abs(budget_agent.score(c4) - 0.23237904984887492) < 1e-9
    assert abs(taste_agent.score(c4) - 0.9679922968230499) < 1e-9

    # 5
    assert abs(health_agent.score(c5) - 0.09999999999999999) < 1e-9
    assert abs(budget_agent.score(c5) - 0.17393069416272566) < 1e-9
    assert abs(taste_agent.score(c5) - 0.28201972503426337) < 1e-9

from tier_1.contracts.schemas import Candidate, TasteProfile
from tier_2.agents import TasteAgent


def test_taste_agent_identical():
    # Pair 1: Identical vectors -> Cosine = 1.0
    persona_taste = TasteProfile(sweet=1.0, salty=1.0, sour=1.0, bitter=1.0, umami=1.0, spice=1.0)
    dish_taste = TasteProfile(sweet=1.0, salty=1.0, sour=1.0, bitter=1.0, umami=1.0, spice=1.0)

    agent = TasteAgent(persona_taste=persona_taste)
    cand = Candidate(taste_profile=dish_taste)

    assert abs(agent.score(cand) - 1.0) < 1e-9


def test_taste_agent_orthogonal():
    # Pair 2: Orthogonal vectors -> Cosine = 0.0
    persona_taste = TasteProfile(sweet=1.0, salty=0.0, sour=0.0, bitter=0.0, umami=0.0, spice=0.0)
    dish_taste = TasteProfile(sweet=0.0, salty=1.0, sour=0.0, bitter=0.0, umami=0.0, spice=0.0)

    agent = TasteAgent(persona_taste=persona_taste)
    cand = Candidate(taste_profile=dish_taste)

    assert abs(agent.score(cand) - 0.0) < 1e-9


def test_taste_agent_partial_overlap():
    # Pair 3: Partial Overlap
    # A = (1, 1, 0, 0, 0, 0) -> mag = sqrt(2)
    # B = (0, 1, 1, 0, 0, 0) -> mag = sqrt(2)
    # Dot = 1
    # Cosine = 1 / 2 = 0.5
    persona_taste = TasteProfile(sweet=1.0, salty=1.0, sour=0.0, bitter=0.0, umami=0.0, spice=0.0)
    dish_taste = TasteProfile(sweet=0.0, salty=1.0, sour=1.0, bitter=0.0, umami=0.0, spice=0.0)

    agent = TasteAgent(persona_taste=persona_taste)
    cand = Candidate(taste_profile=dish_taste)

    assert abs(agent.score(cand) - 0.5) < 1e-9


def test_taste_agent_zero_vector():
    # Edge case: Zero vector -> Should not divide by zero, returns 0.0
    persona_taste = TasteProfile(sweet=1.0, salty=1.0, sour=1.0, bitter=1.0, umami=1.0, spice=1.0)
    dish_taste = TasteProfile(sweet=0.0, salty=0.0, sour=0.0, bitter=0.0, umami=0.0, spice=0.0)

    agent = TasteAgent(persona_taste=persona_taste)
    cand = Candidate(taste_profile=dish_taste)

    assert agent.score(cand) == 0.0

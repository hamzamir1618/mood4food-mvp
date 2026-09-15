from tier_1.symbolic_anchoring import run_anchoring_pipeline
from tier_2.consensus_manager import run_debate_pipeline


def test_strict_budget_enforcement():
    """
    Ensure that when a budget is explicitly stated, NO candidates over that budget
    are returned by the anchoring pipeline or scored by the debate pipeline.
    """
    test_cases = [
        {"raw_input": "spicy chicken biryani under rs 1000", "budget_max_pkr": 1000.0},
        {"raw_input": "burger under 500", "budget_max_pkr": 500.0},
        {"raw_input": "cheap food under 200", "budget_max_pkr": 200.0},
    ]

    for case in test_cases:
        intent = {
            "raw_input": case["raw_input"],
            "budget_max_pkr": case["budget_max_pkr"],
            "allergens_pruned": [],
            "mood_vector": {},
            "craving": "",
            "is_vegan": False,
            "is_vegetarian": False,
            "preferred_category": None,
            "preferred_category_raw_phrase": None,
        }

        # 1. Check Symbolic Anchoring Output
        evaluation = run_anchoring_pipeline(intent)
        candidates = evaluation["safe_candidates"]

        # Verify no candidate violates budget
        violations = [c for c in candidates if c["price_pkr"] > case["budget_max_pkr"]]
        assert len(violations) == 0, (
            f"Budget {case['budget_max_pkr']} violated by {len(violations)} candidates in Tier 1b."
        )

        # If no candidates found, that's perfectly fine (strict enforcement)
        if len(candidates) == 0:
            continue

        # 2. Check Tier 2 output (Mocking the load_contract to avoid needing Redis/session)
        import uuid

        from tier_1.contracts.session_store import load_contract, save_contract

        session_id = uuid.uuid4().hex
        save_contract(session_id, "grounded_intent", intent)
        save_contract(session_id, "candidate_evaluation", evaluation)

        run_debate_pipeline(session_id)

        blueprint = load_contract(session_id, "decision_blueprint")

        # Winner must be under budget
        w_price = (
            blueprint.winning_dish.get("price_pkr")
            if isinstance(blueprint.winning_dish, dict)
            else getattr(blueprint.winning_dish, "price_pkr")
        )
        w_name = (
            blueprint.winning_dish.get("name")
            if isinstance(blueprint.winning_dish, dict)
            else getattr(blueprint.winning_dish, "name")
        )
        assert w_price <= case["budget_max_pkr"], f"Winner {w_name} violates budget."

        # Alternates must be under budget
        for alt in blueprint.top_candidates:
            a_price = alt.get("price_pkr") if isinstance(alt, dict) else getattr(alt, "price_pkr")
            a_name = alt.get("name") if isinstance(alt, dict) else getattr(alt, "name")
            assert a_price <= case["budget_max_pkr"], f"Alternate {a_name} violates budget."

        print(f"Passed budget {case['budget_max_pkr']}")


if __name__ == "__main__":
    test_strict_budget_enforcement()

import math

from tier_1.persona_manager import get_all_personas, validate_persona_weights


def test_all_persona_weights_sum_to_one():
    # Calling validate_persona_weights() directly should not raise an exception
    validate_persona_weights()

    # We also manually verify the weights here to ensure the logic works.
    personas = get_all_personas()
    assert len(personas) == 7, "Expected exactly 7 personas to be defined"

    for persona_key, persona_data in personas.items():
        weights = persona_data["weights"]
        total = sum(weights.values())
        assert math.isclose(total, 1.0, rel_tol=1e-5), (
            f"Persona '{persona_key}' weights {weights} sum to {total}, not 1.0"
        )

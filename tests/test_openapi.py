from fastapi.testclient import TestClient

from orchestrator import app

client = TestClient(app)


def test_openapi_schema_is_valid_and_complete():
    """
    Fetches the OpenAPI JSON schema and ensures it parses correctly and
    contains all the expected routes with explicit response schemas.
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()

    # Basic assertions for OpenAPI validity
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema

    paths = schema["paths"]

    # Assert expected routes exist
    assert "/submit" in paths
    assert "/recalculate" in paths
    assert "/decision_blueprint" in paths
    assert "/personas" in paths

    # Verify explicit response models are defined (instead of raw dict/any)
    # /submit
    submit_responses = paths["/submit"]["post"]["responses"]
    assert "200" in submit_responses
    submit_200 = submit_responses["200"]
    assert "$ref" in submit_200["content"]["application/json"]["schema"]
    assert "DecisionBlueprint" in submit_200["content"]["application/json"]["schema"]["$ref"]

    # /recalculate
    recalculate_responses = paths["/recalculate"]["post"]["responses"]
    assert "200" in recalculate_responses
    recalculate_200 = recalculate_responses["200"]
    assert "$ref" in recalculate_200["content"]["application/json"]["schema"]
    assert "DecisionBlueprint" in recalculate_200["content"]["application/json"]["schema"]["$ref"]

    # /decision_blueprint
    db_responses = paths["/decision_blueprint"]["get"]["responses"]
    assert "200" in db_responses
    db_200 = db_responses["200"]
    assert "$ref" in db_200["content"]["application/json"]["schema"]
    assert "DecisionBlueprint" in db_200["content"]["application/json"]["schema"]["$ref"]

    # /personas
    personas_responses = paths["/personas"]["get"]["responses"]
    assert "200" in personas_responses
    personas_200 = personas_responses["200"]
    # Dict[str, Persona] -> additionalProperties with $ref to Persona
    assert "additionalProperties" in personas_200["content"]["application/json"]["schema"]
    assert "$ref" in personas_200["content"]["application/json"]["schema"]["additionalProperties"]
    assert (
        "Persona"
        in personas_200["content"]["application/json"]["schema"]["additionalProperties"]["$ref"]
    )

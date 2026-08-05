from fastapi.testclient import TestClient

from orchestrator import app

client = TestClient(app, raise_server_exceptions=False)


def test_global_exception_handler_hides_details(monkeypatch):
    def mock_load_contract(*args, **kwargs):
        raise RuntimeError("Something exploded deep inside")

    # Monkeypatch a dependency inside the /decision_blueprint route
    monkeypatch.setattr("api.fulfillment.load_contract", mock_load_contract, raising=False)
    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", mock_load_contract)

    # Calling the endpoint should trigger the exception
    response = client.get("/decision_blueprint")

    # We should get a generic 500 internal server error
    assert response.status_code == 500
    assert response.json() == {"error": "internal_server_error"}

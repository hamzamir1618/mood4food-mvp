from fastapi.testclient import TestClient

from orchestrator import app


def test_cors_middleware():
    client = TestClient(app)

    # Test allowed origin (default is http://localhost:8000)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8000"

    # Test disallowed origin
    response_disallowed = client.options(
        "/health",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response_disallowed.status_code == 400
    # The allow-origin header should NOT be evil.com, or absent
    assert response_disallowed.headers.get("access-control-allow-origin") != "http://evil.com"

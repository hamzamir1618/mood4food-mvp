import pytest
from fastapi.testclient import TestClient

from config import settings
from orchestrator import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_dummy_files(tmp_path, monkeypatch):
    # Ensure uploads dir exists for testing
    from api.submit import UPLOADS_DIR

    UPLOADS_DIR.mkdir(exist_ok=True)

    audio_path = UPLOADS_DIR / "Recording.m4a"
    if not audio_path.exists():
        audio_path.write_bytes(b"dummy audio data")

    image_path = UPLOADS_DIR / "spicy_chicken_biryani.jpg"
    if not image_path.exists():
        image_path.write_bytes(b"dummy image data")

    import fakeredis

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    # We will mock the external pipelines so they don't actually run neo4j etc.
    def mock_ingestion(*args, **kwargs):
        return {"query_intent": "mock intent", "hard_constraints": {}, "soft_constraints": {}}

    def mock_anchoring(*args, **kwargs):
        return {"source_intent": {}, "safe_candidates": [], "soft_constraints": {}, "message": ""}

    def mock_debate(*args, **kwargs):
        from tier_1.contracts.session_store import save_contract

        save_contract(args[0], "decision_blueprint", {"winning_dish": {"name": "dummy"}})

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", mock_ingestion)
    monkeypatch.setattr("tier_1.symbolic_anchoring.run_anchoring_pipeline", mock_anchoring)
    monkeypatch.setattr("tier_2.consensus_manager.run_debate_pipeline", mock_debate)
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda x: x)

    # Reset DEPLOY_MODE to default "full"
    monkeypatch.setattr(settings, "DEPLOY_MODE", "full")

    yield


def test_submit_text_only():
    response = client.post("/submit", data={"text": "I want something spicy"})
    assert response.status_code == 200


def test_submit_audio_only():
    from api.submit import UPLOADS_DIR

    audio_path = UPLOADS_DIR / "Recording.m4a"
    with open(audio_path, "rb") as f:
        files = {"audio": ("Recording.m4a", f, "audio/mp4")}
        response = client.post("/submit", files=files)
    assert response.status_code == 200


def test_submit_image_only():
    from api.submit import UPLOADS_DIR

    image_path = UPLOADS_DIR / "spicy_chicken_biryani.jpg"
    with open(image_path, "rb") as f:
        files = {"image": ("spicy_chicken_biryani.jpg", f, "image/jpeg")}
        response = client.post("/submit", files=files)
    assert response.status_code == 200


def test_submit_multiple_or_zero():
    # Zero
    response = client.post("/submit")
    assert response.status_code == 400
    assert "exactly one" in response.json()["detail"]

    # Multiple (Text and Image)
    from api.submit import UPLOADS_DIR

    image_path = UPLOADS_DIR / "spicy_chicken_biryani.jpg"
    with open(image_path, "rb") as f:
        files = {"image": ("spicy_chicken_biryani.jpg", f, "image/jpeg")}
        data = {"text": "some text"}
        response = client.post("/submit", files=files, data=data)
    assert response.status_code == 400
    assert "exactly one" in response.json()["detail"]


def test_submit_lite_mode_rejects_media(monkeypatch):
    monkeypatch.setattr(settings, "DEPLOY_MODE", "lite")

    from api.submit import UPLOADS_DIR

    audio_path = UPLOADS_DIR / "Recording.m4a"
    with open(audio_path, "rb") as f:
        files = {"audio": ("Recording.m4a", f, "audio/mp4")}
        response = client.post("/submit", files=files)

    # Should reject with 501
    assert response.status_code == 501
    assert "not supported in lite mode" in response.json()["detail"]

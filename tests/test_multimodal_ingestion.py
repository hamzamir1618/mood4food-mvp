import os

from tier_1.multi_modal_ingestion import run_ingestion_pipeline


def test_text_input():
    result = run_ingestion_pipeline(raw_input="I want a spicy chicken biryani under 500 rupees")
    assert result["budget_max_pkr"] == 500.0
    assert "spicy chicken biryani" in result["raw_input"].lower()


def test_audio_input():
    audio_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "Recording.m4a")
    result = run_ingestion_pipeline(audio_path=audio_path)
    # The transcript length should be > 0 and populated in raw_input
    assert len(result["raw_input"]) > 10


def test_image_input():
    image_path = os.path.join(
        os.path.dirname(__file__), "..", "uploads", "spicy_chicken_biryani.jpg"
    )
    result = run_ingestion_pipeline(image_path=image_path)
    assert result["craving"] is not None
    assert "biryani" in result["craving"].lower()
    assert result["raw_input"].startswith("Image upload of")

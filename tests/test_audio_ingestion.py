import os

from tier_1.audio_ingestion import transcribe


def test_transcribe_audio():
    audio_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "Recording.m4a")
    transcript = transcribe(audio_path)
    assert isinstance(transcript, str)
    assert len(transcript) > 10

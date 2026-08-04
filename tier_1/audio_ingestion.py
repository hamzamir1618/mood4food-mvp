import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        log.info("loading faster-whisper 'base' model...")
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        log.info("faster-whisper model loaded ✓")
    return _whisper_model


def transcribe(audio_path: str) -> str:
    path = Path(audio_path)
    if not path.exists():
        log.warning("audio file not found: %s — skipping", audio_path)
        return ""

    log.info(
        "🎤 transcribing audio (faster-whisper): %s (%.1f KB)",
        path.name,
        path.stat().st_size / 1024,
    )
    model = _get_whisper_model()

    segments, info = model.transcribe(str(path), beam_size=5)

    transcript = " ".join([segment.text for segment in segments]).strip()
    log.info("🎤 transcript: %s", transcript)
    return transcript

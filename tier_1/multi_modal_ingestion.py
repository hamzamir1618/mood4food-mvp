"""
Tier 1a — Multimodal Intent Parsing Pipeline
Ingests audio (Whisper), images (smart stub), and text inputs,
merges them, extracts structured intent, and emits grounded_intent.json.
"""

import json
import logging
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent / "contracts"
GROUNDED_INTENT_PATH = OUTPUT_DIR / "grounded_intent.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def ingest_audio(audio_path: str) -> str:
    """
    Transcribes an audio file using faster-whisper.
    """
    from tier_1.audio_ingestion import transcribe

    return transcribe(audio_path)


def ingest_vision(image_path: str) -> str:
    """
    Classifies the image against known dish names using CLIP.
    """
    path = Path(image_path)
    if not path.exists():
        log.warning("image file not found: %s — skipping", image_path)
        return ""

    from tier_1.image_ingestion import classify_dish
    from tier_1.symbolic_anchoring import get_all_dish_names

    labels = get_all_dish_names()
    if not labels:
        labels = ["food", "drink", "pizza", "burger", "biryani"]

    caption = classify_dish(image_path, labels)
    return caption


# ═══════════════════════════════════════════════════════════════════════════
# INTENT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════


def extract_intent(raw_input: str) -> dict:
    """
    Primary intent extraction: uses the configured IntentExtractor.
    """
    from tier_1.intent_extractor_interface import get_extractor

    extractor = get_extractor()
    intent_obj = extractor.extract(raw_input)
    return intent_obj.model_dump()


# ═══════════════════════════════════════════════════════════════════════════
# JSON CONTRACT WRITER
# ═══════════════════════════════════════════════════════════════════════════


def write_grounded_intent(intent: dict) -> Path:
    """Atomically writes the grounded intent to the JSON contract file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(GROUNDED_INTENT_PATH, "w", encoding="utf-8") as fh:
        json.dump(intent, fh, indent=4, ensure_ascii=False)
    log.info("grounded_intent written → %s", GROUNDED_INTENT_PATH)
    return GROUNDED_INTENT_PATH


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════


def run_ingestion_pipeline(
    raw_input: str | None = None,
    audio_path: str | None = None,
    image_path: str | None = None,
) -> dict:
    """
    Full Tier-1a multimodal pipeline with discriminated routing:
      - text: -> IntentExtractor directly
      - audio: -> transcribe() -> IntentExtractor
      - image: -> classify_dish() -> mapped directly to GroundedIntent (craving)
    Returns the intent dict for downstream callers.
    """
    log.info("─── Tier 1a: Multimodal Intent Pipeline START ───")

    if raw_input:
        log.info("📝 Routing text input")
        intent = extract_intent(raw_input)
    elif audio_path:
        log.info("🎤 Routing audio input")
        transcript = ingest_audio(audio_path)
        if not transcript.strip():
            transcript = "I am hungry"
        intent = extract_intent(transcript)
    elif image_path:
        log.info("📷 Routing image input")
        caption = ingest_vision(image_path)
        from tier_1.contracts.schemas import GroundedIntent

        intent_obj = GroundedIntent(raw_input=f"Image upload of {caption}", craving=caption)
        intent = intent_obj.model_dump()
    else:
        log.warning("no input provided, using default text")
        intent = extract_intent("I want something spicy under 800 rupees, no meat")

    log.info("extracted intent: %s", json.dumps(intent, indent=2))

    # Persist contract
    write_grounded_intent(intent)

    log.info("─── Tier 1a: Multimodal Intent Pipeline DONE ────")
    return intent


# ── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_ingestion_pipeline()
    print(json.dumps(result, indent=4))

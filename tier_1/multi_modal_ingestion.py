"""
Tier 1 — Intent Parsing Pipeline
Ingests raw multi-modal input (audio/vision/text stubs) and emits grounded_intent.json.
"""

import json
import logging
import os
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent / "contracts"
GROUNDED_INTENT_PATH = OUTPUT_DIR / "grounded_intent.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ── Stub Ingestors ──────────────────────────────────────────────────────────
# These are lightweight placeholders. In production, they would call Whisper,
# Moondream, or spaCy respectively.  For the MVP they simply pass through.

def ingest_audio(audio_path: str) -> str:
    """Stub: simulates Whisper transcription of an audio file."""
    log.info("audio_stub | path=%s — returning placeholder transcript", audio_path)
    return "I want something spicy under 800 rupees, no meat"


def ingest_vision(image_path: str) -> str:
    """Stub: simulates Moondream/BLIP captioning of a food image."""
    log.info("vision_stub | path=%s — returning placeholder caption", image_path)
    return "a plate of spicy vegetable biryani"


def ingest_text(raw_text: str) -> str:
    """Stub: normalises raw text input (lowercased, stripped)."""
    cleaned = raw_text.strip().lower()
    log.info("text_stub | cleaned=%s", cleaned)
    return cleaned


# ── Intent Extraction ───────────────────────────────────────────────────────

def extract_intent(raw_input: str) -> dict:
    """
    Deterministic intent parser.
    Takes a raw natural-language string and produces a structured intent dict.

    In production this would call a local Phi-3.5 GGUF model via llama-cpp.
    For the MVP it uses simple keyword matching to stay fully offline and
    reproducible.
    """
    text = raw_input.strip().lower()

    # ── Budget extraction (first number found, defaults to 1000) ──
    budget = 1000
    for token in text.split():
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits:
            budget = int(digits)
            break

    # ── Allergen / exclusion extraction ──
    exclusion_keywords = {
        "meat":      "meat",
        "chicken":   "meat",
        "beef":      "meat",
        "mutton":    "meat",
        "pork":      "meat",
        "dairy":     "dairy",
        "milk":      "dairy",
        "cheese":    "dairy",
        "gluten":    "gluten",
        "wheat":     "gluten",
        "nuts":      "nuts",
        "peanut":    "nuts",
        "shellfish": "shellfish",
        "shrimp":    "shellfish",
        "egg":       "egg",
        "eggs":      "egg",
    }
    allergens_found: set[str] = set()
    for word in text.split():
        word_clean = word.strip(".,!?;:")
        if word_clean in exclusion_keywords:
            allergens_found.add(exclusion_keywords[word_clean])

    # ── Protein priority ──
    protein_priority = "high" if any(k in text for k in ("protein", "gym", "muscle", "high protein")) else "normal"

    # ── Mood vector seed ──
    mood_map = {"spicy": "spicy", "sweet": "sweet", "comfort": "comfort",
                "light": "light", "hearty": "hearty", "fresh": "fresh"}
    mood = "neutral"
    for keyword, mood_label in mood_map.items():
        if keyword in text:
            mood = mood_label
            break

    intent = {
        "hard_constraints": {
            "budget_max_pkr": budget,
            "allergens_pruned": sorted(allergens_found),
        },
        "soft_constraints": {
            "protein_priority": protein_priority,
            "mood_vector_seed": mood,
        },
    }
    return intent


# ── JSON Contract Writer ────────────────────────────────────────────────────

def write_grounded_intent(intent: dict) -> Path:
    """Atomically writes the grounded intent to the JSON contract file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(GROUNDED_INTENT_PATH, "w", encoding="utf-8") as fh:
        json.dump(intent, fh, indent=4, ensure_ascii=False)
    log.info("grounded_intent written → %s", GROUNDED_INTENT_PATH)
    return GROUNDED_INTENT_PATH


# ── Pipeline Entry Point ────────────────────────────────────────────────────

def run_ingestion_pipeline(raw_input: str | None = None) -> dict:
    """
    Full Tier-1a pipeline:
      1. Ingest (stubs)
      2. Extract intent
      3. Write grounded_intent.json
    Returns the intent dict for downstream callers.
    """
    if raw_input is None:
        # Default demo input when run standalone
        raw_input = "I want something spicy under 800 rupees, no meat"

    log.info("─── Tier 1a: Intent Parsing Pipeline START ───")

    # Step 1 — stubs (results unused in MVP; wired for future multimodal merge)
    _transcript = ingest_audio("demo.wav")
    _caption = ingest_vision("demo.jpg")
    cleaned = ingest_text(raw_input)

    # Step 2 — extract structured intent
    intent = extract_intent(cleaned)
    log.info("extracted intent: %s", json.dumps(intent, indent=2))

    # Step 3 — persist contract
    write_grounded_intent(intent)

    log.info("─── Tier 1a: Intent Parsing Pipeline DONE ────")
    return intent


# ── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_ingestion_pipeline()
    print(json.dumps(result, indent=4))

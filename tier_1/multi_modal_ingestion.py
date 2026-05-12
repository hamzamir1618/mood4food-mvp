"""
Tier 1a — Multimodal Intent Parsing Pipeline
Ingests audio (Whisper), images (smart stub), and text inputs,
merges them, extracts structured intent, and emits grounded_intent.json.
"""

import json
import logging
import os
import re
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent / "contracts"
GROUNDED_INTENT_PATH = OUTPUT_DIR / "grounded_intent.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ── Whisper Model (lazy-loaded singleton) ───────────────────────────────────
_whisper_model = None


def _get_whisper_model():
    """Lazy-load the Whisper base model on first audio ingest."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        log.info("loading Whisper 'base' model (74 MB, first run downloads it)…")
        _whisper_model = whisper.load_model("base")
        log.info("Whisper model loaded ✓")
    return _whisper_model


# ═══════════════════════════════════════════════════════════════════════════
# INGESTORS
# ═══════════════════════════════════════════════════════════════════════════


def ingest_audio(audio_path: str) -> str:
    """
    Transcribes an audio file using OpenAI Whisper (base model).
    Supports: .wav, .mp3, .m4a, .flac, .ogg, .webm
    Returns the transcribed text.
    """
    path = Path(audio_path)
    if not path.exists():
        log.warning("audio file not found: %s — skipping", audio_path)
        return ""

    log.info("🎤 transcribing audio: %s (%.1f KB)", path.name, path.stat().st_size / 1024)
    model = _get_whisper_model()
    result = model.transcribe(str(path), language="en", fp16=False)
    transcript = result.get("text", "").strip()
    log.info("🎤 transcript: %s", transcript)
    return transcript


def ingest_vision(image_path: str) -> str:
    """
    Smart stub: extracts food-related keywords from the image filename
    and common metadata patterns. In production, this would use Moondream2
    or BLIP for actual image captioning.

    Examples:
        "spicy_chicken_biryani.jpg"  →  "spicy chicken biryani"
        "IMG_20240101_dinner.png"    →  "dinner"
    """
    path = Path(image_path)
    if not path.exists():
        log.warning("image file not found: %s — skipping", image_path)
        return ""

    # Extract keywords from filename (strip extension, split on separators)
    stem = path.stem.lower()
    # Remove common camera prefixes
    stem = re.sub(r"^(img|dsc|photo|pic|image|screenshot)[_\-]?\d*[_\-]?", "", stem)
    # Remove timestamps (8+ consecutive digits)
    stem = re.sub(r"\d{8,}", "", stem)
    # Split on underscores, hyphens, spaces
    words = re.split(r"[_\-\s]+", stem)
    # Filter out empty tokens and very short ones
    words = [w for w in words if len(w) > 1]

    caption = " ".join(words) if words else "food image"
    log.info("📷 vision stub | file=%s → caption='%s'", path.name, caption)
    return caption


def ingest_text(raw_text: str) -> str:
    """Normalises raw text input (lowercased, stripped, collapsed whitespace)."""
    cleaned = re.sub(r"\s+", " ", raw_text.strip().lower())
    log.info("📝 text input: %s", cleaned)
    return cleaned


# ═══════════════════════════════════════════════════════════════════════════
# MULTIMODAL MERGE
# ═══════════════════════════════════════════════════════════════════════════


def merge_modalities(text: str = "", audio_transcript: str = "", image_caption: str = "") -> str:
    """
    Combines outputs from all active modalities into a single string
    for downstream intent extraction. Deduplicates overlapping content.
    """
    parts = []
    if text:
        parts.append(text)
    if audio_transcript:
        # Only add audio if it's meaningfully different from typed text
        if text and _overlap_ratio(text, audio_transcript) > 0.7:
            log.info("merge | audio transcript overlaps with text, skipping duplicate")
        else:
            parts.append(audio_transcript)
    if image_caption:
        parts.append(image_caption)

    merged = " ".join(parts)
    log.info("merge | combined: '%s'", merged)
    return merged


def _overlap_ratio(a: str, b: str) -> float:
    """Simple word overlap ratio between two strings."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / min(len(words_a), len(words_b))


# ═══════════════════════════════════════════════════════════════════════════
# INTENT EXTRACTION — LLM (PRIMARY) + KEYWORD FALLBACK
# ═══════════════════════════════════════════════════════════════════════════

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mood4food"


def extract_intent_llm(raw_input: str) -> dict | None:
    """
    Calls the fine-tuned Phi-3.5 model via Ollama to extract structured intent.
    The model is a deterministic semantic translator — no conversation, no
    decision-making. Raw string in, Grounded Intent JSON out.

    Returns the parsed intent dict, or None if Ollama is unreachable or
    the model returns invalid JSON (triggering keyword fallback).
    """
    import httpx

    try:
        log.info("🧠 LLM | sending to Ollama (%s)…", OLLAMA_MODEL)
        resp = httpx.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": raw_input,
                "stream": False,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        raw_output = payload.get("response", "").strip()
        log.info("🧠 LLM | raw response: %s", raw_output)

        # Parse the JSON from model output
        intent = json.loads(raw_output)

        # Normalize to downstream contract format
        return _normalize_llm_intent(intent)

    except httpx.ConnectError:
        log.warning("🧠 LLM | Ollama not running — falling back to keyword parser")
        return None
    except httpx.HTTPStatusError as exc:
        log.warning("🧠 LLM | Ollama HTTP error %s — falling back to keyword parser", exc.response.status_code)
        return None
    except httpx.TimeoutException:
        log.warning("🧠 LLM | Ollama timed out — falling back to keyword parser")
        return None
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        log.warning("🧠 LLM | failed to parse model output: %s — falling back to keyword parser", exc)
        return None


def _normalize_llm_intent(raw: dict) -> dict:
    """
    Maps the LLM output schema to the downstream pipeline contract.
    Handles differences between the model's training format and what
    symbolic_anchoring.py / consensus_manager.py expect.
    """
    hard = raw.get("hard_constraints", {})
    soft = raw.get("soft_constraints", {})

    # budget_max_pkr=0 means "not specified" in training data → default to 1000
    budget = hard.get("budget_max_pkr", 0)
    if budget == 0:
        budget = 1000

    # protein_priority: model outputs "none" for unspecified → map to "normal"
    protein = soft.get("protein_priority", "normal")
    if protein == "none":
        protein = "normal"

    intent = {
        "hard_constraints": {
            "budget_max_pkr": budget,
            "allergens_pruned": sorted(hard.get("allergens_pruned", [])),
        },
        "soft_constraints": {
            "protein_priority": protein,
            "mood_vector_seed": soft.get("mood_vector_seed", "neutral"),
        },
    }
    log.info("🧠 LLM | normalized intent: %s", json.dumps(intent))
    return intent


def extract_intent_keywords(raw_input: str) -> dict:
    """
    Deterministic keyword-based intent parser.
    Used as a fallback when Ollama / the LLM is unavailable.
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
        "fish":      "fish",
        "seafood":   "fish",
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
                "light": "light", "hearty": "hearty", "fresh": "fresh",
                "crispy": "comfort", "rich": "hearty", "creamy": "comfort",
                "tangy": "fresh", "hot": "spicy", "mild": "light"}
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


def extract_intent(raw_input: str) -> dict:
    """
    Primary intent extraction: tries LLM first, falls back to keywords.
    This function is the single entry point used by the pipeline.
    """
    # Try LLM (Ollama + fine-tuned Phi-3.5)
    intent = extract_intent_llm(raw_input)
    if intent is not None:
        return intent

    # Fallback to keyword parser
    log.info("📋 using keyword fallback parser")
    return extract_intent_keywords(raw_input)


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
    Full Tier-1a multimodal pipeline:
      1. Ingest each modality (audio/vision/text)
      2. Merge modality outputs
      3. Extract structured intent (LLM primary, keyword fallback)
      4. Write grounded_intent.json
    Returns the intent dict for downstream callers.
    """
    if raw_input is None and audio_path is None and image_path is None:
        # Default demo input when run standalone
        raw_input = "I want something spicy under 800 rupees, no meat"

    log.info("─── Tier 1a: Multimodal Intent Pipeline START ───")

    # Step 1 — Ingest each modality
    text_out = ingest_text(raw_input) if raw_input else ""
    audio_out = ingest_audio(audio_path) if audio_path else ""
    vision_out = ingest_vision(image_path) if image_path else ""

    # Step 2 — Merge modalities
    merged = merge_modalities(text=text_out, audio_transcript=audio_out, image_caption=vision_out)
    if not merged.strip():
        merged = "I want food under 1000 rupees"
        log.warning("no input from any modality, using default: '%s'", merged)

    # Step 3 — Extract structured intent (LLM → keyword fallback)
    intent = extract_intent(merged)
    log.info("extracted intent: %s", json.dumps(intent, indent=2))

    # Step 4 — Persist contract
    write_grounded_intent(intent)

    log.info("─── Tier 1a: Multimodal Intent Pipeline DONE ────")
    return intent


# ── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_ingestion_pipeline()
    print(json.dumps(result, indent=4))

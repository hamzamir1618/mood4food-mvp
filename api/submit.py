import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from api.rate_limit import limiter
from tier_1.contracts.schemas import DecisionBlueprint

log = logging.getLogger(__name__)
router = APIRouter()

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


@router.post("/submit", response_model=DecisionBlueprint)
@limiter.limit("20/minute")
async def submit_query(
    request: Request,
    text: str = Form(default=""),
    audio: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
):
    """
    Accepts a natural language food query (text), plus optional audio and
    image file uploads. Runs the full 3-stage multimodal pipeline:
      Tier 1a (intent parsing) → Tier 1b (Neo4j pruning) → Tier 2 (debate)
    Returns the resulting decision_blueprint enriched with fulfillment data.
    """
    from config import settings
    from tier_1.contracts.session_store import load_contract, save_contract
    from tier_1.multi_modal_ingestion import run_ingestion_pipeline
    from tier_1.symbolic_anchoring import run_anchoring_pipeline
    from tier_2.consensus_manager import run_debate_pipeline
    from tier_3.fulfillment_engine import enrich_blueprint

    text = text.strip() if text else ""
    has_audio = bool(audio and audio.filename)
    has_image = bool(image and image.filename)

    provided = sum([bool(text), has_audio, has_image])
    if provided != 1:
        raise HTTPException(400, "Provide exactly one of: text, audio file, or image file.")

    if (has_audio or has_image) and settings.DEPLOY_MODE == "lite":
        raise HTTPException(501, "Audio and Image processing are not supported in lite mode.")

    if len(text) > 500:
        raise HTTPException(400, "Text query exceeds 500 characters.")

    audio_path = None
    image_path = None

    # Save uploaded audio file
    if has_audio:
        ext = audio.filename.split(".")[-1].lower()
        if ext not in ["m4a", "mp3", "wav"]:
            raise HTTPException(400, f"Unsupported audio extension: {ext}")
        content = await audio.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "Audio file exceeds 10MB limit.")
        audio_path = str(UPLOADS_DIR / audio.filename)
        with open(audio_path, "wb") as f:
            f.write(content)
        log.info("saved audio upload: %s", audio_path)

    # Save uploaded image file
    if has_image:
        ext = image.filename.split(".")[-1].lower()
        if ext not in ["jpg", "jpeg", "png"]:
            raise HTTPException(400, f"Unsupported image extension: {ext}")
        content = await image.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "Image file exceeds 10MB limit.")
        image_path = str(UPLOADS_DIR / image.filename)
        with open(image_path, "wb") as f:
            f.write(content)
        log.info("saved image upload: %s", image_path)

    log.info(
        "─── /submit received: text='%s' audio=%s image=%s ───",
        text[:80] if text else "(none)",
        audio.filename if has_audio else "(none)",
        image.filename if has_image else "(none)",
    )

    # Stage 1: Multimodal Intent Parsing
    try:
        intent = run_ingestion_pipeline(  # noqa: F841
            raw_input=text or None,
            audio_path=audio_path,
            image_path=image_path,
        )
        save_contract(request.state.session_id, "grounded_intent", intent)
    except Exception as exc:
        log.error("Tier 1a failed: %s", exc)
        raise HTTPException(500, f"Intent parsing failed: {exc}")

    # Stage 2: Neo4j Allergen Pruning
    try:
        evaluation = run_anchoring_pipeline(intent)
        save_contract(request.state.session_id, "candidate_evaluation", evaluation)
    except Exception as exc:
        log.error("Tier 1b failed: %s", exc)
        raise HTTPException(503, f"Neo4j query failed — is the database running? ({exc})")

    # Stage 3: Multi-Agent Debate
    try:
        run_debate_pipeline(request.state.session_id)
    except Exception as exc:
        log.error("Tier 2 failed: %s", exc)
        raise HTTPException(500, f"Debate pipeline failed: {exc}")

    # Return the freshly written blueprint from the session store
    blueprint = load_contract(request.state.session_id, "decision_blueprint")
    if not blueprint:
        raise HTTPException(500, "Pipeline completed but decision_blueprint was not created.")

    if hasattr(blueprint, "model_dump"):
        blueprint = blueprint.model_dump()

    # Enrich with fulfillment data (recipe + restaurants)
    blueprint = enrich_blueprint(blueprint)

    winner_name = "?"
    winning_dish = blueprint.get("winning_dish")
    if winning_dish:
        winner_name = winning_dish.get("name", "?")

    log.info("─── /submit complete → winner: %s ───", winner_name)
    return blueprint

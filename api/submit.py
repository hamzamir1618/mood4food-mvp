import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

from api.location import Location
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
    lat: float | None = Form(default=None),
    lng: float | None = Form(default=None),
    location_label: str | None = Form(default=None),
):
    """
    Accepts a natural language food query (text), or an audio or image file upload,
    and returns one recommendation from the full pipeline (api/pipeline.py). For a
    conversation that can ask a question or be refined, use /chat. An optional location
    (lat, lng, and a label to show) adds a straight-line distance to each dish.
    """
    from api.pipeline import recommend
    from config import settings

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

    location = None
    if (lat is None) != (lng is None):
        raise HTTPException(400, "Send both lat and lng, or neither.")
    if lat is not None:
        try:
            location = Location(lat=lat, lng=lng, label=location_label or None).model_dump()
        except ValidationError as exc:
            raise HTTPException(422, f"Invalid location: {exc.errors()[0]['msg']}")

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
    return recommend(request, text or None, audio_path, image_path, location=location)

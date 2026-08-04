"""
FastAPI Orchestrator — serves the web UI, runs the full ingestion-to-debate
pipeline from user queries, and handles weight recalculation.

Run:  uvicorn orchestrator:app --host 0.0.0.0 --port 8000 --reload
Open: http://localhost:8000/
"""

import json
import logging
import math
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

# ── Config ──────────────────────────────────────────────────────────────────
CONTRACTS_DIR = Path(__file__).resolve().parent / "tier_1" / "contracts"
DECISION_BLUEPRINT_PATH = CONTRACTS_DIR / "decision_blueprint.json"
CANDIDATE_EVAL_PATH = CONTRACTS_DIR / "candidate_evaluation.json"
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

WEB_UI_DIR = Path(__file__).resolve().parent / "web_ui"

app = FastAPI(title="FIPE Orchestrator", version="0.2.0")


class SessionIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "session_id" not in request.session:
            request.session["session_id"] = uuid.uuid4().hex
        request.state.session_id = request.session["session_id"]
        response = await call_next(request)
        return response


app.add_middleware(SessionIDMiddleware)
app.add_middleware(SessionMiddleware, secret_key="fipe-secret-key-change-in-prod")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving for web UI ──────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(WEB_UI_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serves the Mood4Food web UI."""
    return FileResponse(str(WEB_UI_DIR / "index.html"))


@app.get("/health")
def health_check():
    """Health check endpoint: pings Neo4j and Redis."""
    from fastapi.responses import JSONResponse
    from neo4j import GraphDatabase

    from config import settings
    from tier_1.contracts.session_store import get_redis

    health_status = {"neo4j": "ok", "redis": "ok"}
    status_code = 200

    # Ping Neo4j
    try:
        with GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        ) as driver:
            driver.verify_connectivity()
    except Exception:
        health_status["neo4j"] = "unreachable"
        status_code = 503

    # Ping Redis
    try:
        redis_client = get_redis()
        redis_client.ping()
    except Exception:
        health_status["redis"] = "unreachable"
        status_code = 503

    if status_code == 200:
        return {"status": "ok", **health_status}
    else:
        return JSONResponse(status_code=503, content={"status": "error", **health_status})


# ── Models ──────────────────────────────────────────────────────────────────


class WeightUpdate(BaseModel):
    w_health: Optional[float] = None
    w_budget: Optional[float] = None
    w_taste: Optional[float] = None
    # Legacy single-slider support
    w_budget_legacy: Optional[float] = None
    persona: Optional[str] = None


class QueryInput(BaseModel):
    query: str


# ── Routes ──────────────────────────────────────────────────────────────────


@app.post("/submit")
async def submit_query(
    request: Request,
    query: str = Form(default=""),
    audio: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
):
    """
    Accepts a natural language food query (text), plus optional audio and
    image file uploads. Runs the full 3-stage multimodal pipeline:
      Tier 1a (intent parsing) → Tier 1b (Neo4j pruning) → Tier 2 (debate)
    Returns the resulting decision_blueprint enriched with fulfillment data.
    """
    from tier_1.contracts.session_store import load_contract, save_contract
    from tier_1.multi_modal_ingestion import run_ingestion_pipeline
    from tier_1.symbolic_anchoring import run_anchoring_pipeline
    from tier_2.consensus_manager import run_debate_pipeline
    from tier_3.fulfillment_engine import enrich_blueprint

    text = query.strip() if query else ""
    if len(text) > 500:
        raise HTTPException(400, "Text query exceeds 500 characters.")

    audio_path = None
    image_path = None

    # Save uploaded audio file
    if audio and audio.filename:
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
    if image and image.filename:
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

    if not text and not audio_path and not image_path:
        raise HTTPException(400, "Provide at least a non-empty text query, audio file, or image.")

    log.info(
        "─── /submit received: text='%s' audio=%s image=%s ───",
        text[:80] if text else "(none)",
        audio.filename if audio and audio.filename else "(none)",
        image.filename if image and image.filename else "(none)",
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
        evaluation = run_anchoring_pipeline()
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

    log.info(
        "─── /submit complete → winner: %s ───", blueprint.get("winning_dish", {}).get("name", "?")
    )
    return blueprint


@app.get("/decision_blueprint")
def get_decision_blueprint():
    """Returns the current decision_blueprint.json to the frontend."""
    from tier_3.fulfillment_engine import enrich_blueprint

    if not DECISION_BLUEPRINT_PATH.exists():
        raise HTTPException(404, "decision_blueprint.json not found — run Tier 2 first")
    with open(DECISION_BLUEPRINT_PATH, "r", encoding="utf-8") as fh:
        blueprint = json.load(fh)
    return enrich_blueprint(blueprint)


@app.get("/personas")
def get_personas():
    """Returns all available persona definitions for the frontend to render."""
    from tier_1.persona_manager import get_all_personas

    return get_all_personas()


@app.post("/recalculate")
def recalculate(request: Request, payload: WeightUpdate):
    """
    Accepts new weights from the UI sliders (w_health, w_budget, w_taste)
    and an optional persona key. Re-scores all candidates with new weights
    **without re-querying the LLM or database**. Instant.
    """
    from tier_1.contracts.schemas import Candidate, TasteProfile
    from tier_1.contracts.session_store import load_contract
    from tier_1.persona_manager import DEFAULT_PERSONA, get_all_personas, get_persona
    from tier_2.agents import TasteAgent
    from tier_3.fulfillment_engine import enrich_blueprint

    evaluation = load_contract(request.state.session_id, "candidate_evaluation")
    if not evaluation:
        raise HTTPException(400, "No active session data found. Please submit a new query first.")

    if hasattr(evaluation, "model_dump"):
        evaluation = evaluation.model_dump()

    candidates = evaluation.get("safe_candidates", [])
    budget_max = evaluation.get("source_intent", {}).get("budget_max_pkr", 1000)
    mood_seed = evaluation.get("soft_constraints", {}).get("mood_vector_seed", "neutral")
    direct_dish_prompt = evaluation.get("soft_constraints", {}).get("direct_dish_prompt", "")

    # Determine persona and weights
    persona_key = payload.persona or DEFAULT_PERSONA
    persona = get_persona(persona_key)
    persona_taste = persona["taste_preference"]

    # Use explicitly provided weights, or fall back to persona defaults
    if (
        payload.w_health is not None
        and payload.w_budget is not None
        and payload.w_taste is not None
    ):
        raw_h, raw_b, raw_t = payload.w_health, payload.w_budget, payload.w_taste
    elif payload.w_budget_legacy is not None:
        # Legacy single-slider mode
        w_b = max(0.0, min(1.0, payload.w_budget_legacy))
        remaining = 1.0 - w_b
        raw_h, raw_b, raw_t = remaining / 2.0, w_b, remaining / 2.0
    else:
        pw = persona["weights"]
        raw_h, raw_b, raw_t = pw["w_health"], pw["w_budget"], pw["w_taste"]

    # Normalize weights to sum to 1.0
    total = raw_h + raw_b + raw_t
    if total > 0:
        w_h, w_b, w_t = raw_h / total, raw_b / total, raw_t / total
    else:
        w_h, w_b, w_t = 0.34, 0.33, 0.33

    xai_traces = [
        f"slider_override: w_h={w_h:.2f} w_b={w_b:.2f} w_t={w_t:.2f} (persona={persona_key})"
    ]

    scored = []
    for cand in candidates:
        protein = cand.get("protein_g", 15.0)
        calories = cand.get("calories", 500.0)
        price = cand.get("price_pkr", 0.0)

        u_h = min(1.0, (protein / max(calories, 1)) / 0.05)

        # Log-scaled budget utility for better spread
        if price < 0:
            u_b = 1.0
        elif budget_max is None or budget_max <= 0:
            u_b = math.exp(-0.002 * price)
        else:
            u_b = max(0.0, 1.0 - math.log(1 + price) / math.log(1 + budget_max))

        # 6D taste profile utility
        dish_taste_profile = cand.get("taste_profile", {})
        if dish_taste_profile and persona_taste:
            agent = TasteAgent(persona_taste=TasteProfile(**persona_taste))
            c_model = Candidate(taste_profile=TasteProfile(**dish_taste_profile))
            u_t = agent.score(c_model)
        else:
            u_t = 0.5  # fallback without taste data

        u_total = (w_h * u_h) + (w_b * u_b) + (w_t * u_t)

        cand_name_lower = cand.get("name", "").lower()
        if (
            direct_dish_prompt
            and len(direct_dish_prompt) > 3
            and (cand_name_lower in direct_dish_prompt or direct_dish_prompt in cand_name_lower)
        ):
            u_total = 1000.0

        entry = {
            "dish_id": cand.get("dish_id", "?"),
            "name": cand.get("name", "unnamed"),
            "u_health": round(u_h, 6),
            "u_budget": round(u_b, 6),
            "u_taste": round(u_t, 6),
            "u_total": round(u_total, 6),
            "price_pkr": price,
            "category": cand.get("category", ""),
            "image_url": cand.get("image_url", ""),
            "human_tags": cand.get("human_tags", []),
            "taste_profile": dish_taste_profile,
        }
        scored.append(entry)
        xai_traces.append(
            f"  {entry['name']} → U_h={u_h:.4f} U_b={u_b:.4f} U_t={u_t:.4f} | U_total={u_total:.4f}"
        )

    if scored:
        winner = max(scored, key=lambda x: x["u_total"])
        winning_dish = {
            "dish_id": winner["dish_id"],
            "name": winner["name"],
            "price_pkr": winner.get("price_pkr", 0),
            "category": winner.get("category", ""),
            "image_url": winner.get("image_url", ""),
            "human_tags": winner.get("human_tags", []),
        }
        utility_breakdown = {
            "u_health": winner["u_health"],
            "u_budget": winner["u_budget"],
            "u_taste": winner["u_taste"],
            "u_total": winner["u_total"],
        }
        xai_traces.append(f"winner: {winner['name']} (U_total={winner['u_total']:.4f})")
    else:
        winning_dish = None
        utility_breakdown = {"u_health": 0.0, "u_budget": 0.0, "u_taste": 0.0, "u_total": 0.0}
        xai_traces.append("FALLBACK: no candidates to score")

    relaxation_notice = evaluation.get("message", "") or None

    blueprint = {
        "winning_dish": winning_dish,
        "utility_breakdown": utility_breakdown,
        "agent_weights": {"w_h": round(w_h, 4), "w_b": round(w_b, 4), "w_t": round(w_t, 4)},
        "persona": persona_key,
        "relaxation_rounds": 0,
        "xai_traces": xai_traces,
        "all_candidate_scores": scored,
        "top_candidates": sorted(scored, key=lambda x: x.get("u_total", 0.0), reverse=True)[:5],
        "source_context": {
            "budget_max_pkr": budget_max,
            "allergens_pruned": evaluation.get("source_intent", {}).get("allergens_pruned", []),
            "mood_vector_seed": mood_seed,
        },
        "personas_available": {
            k: {
                "display_name": v["display_name"],
                "icon": v["icon"],
                "description": v["description"],
            }
            for k, v in get_all_personas().items()
        },
        "relaxation_notice": relaxation_notice,
    }

    # Enrich with fulfillment data
    blueprint = enrich_blueprint(blueprint)

    # Persist updated blueprint
    with open(DECISION_BLUEPRINT_PATH, "w", encoding="utf-8") as fh:
        json.dump(blueprint, fh, indent=4, ensure_ascii=False)
    log.info(
        "recalculated blueprint with w_h=%.2f w_b=%.2f w_t=%.2f persona=%s → winner: %s",
        w_h,
        w_b,
        w_t,
        persona_key,
        winner["name"],
    )

    return blueprint

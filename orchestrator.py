"""
FastAPI Orchestrator — serves the web UI, runs the full ingestion-to-debate
pipeline from user queries, and handles weight recalculation.

Run:  uvicorn orchestrator:app --host 0.0.0.0 --port 8000 --reload
Open: http://localhost:8000/
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Config ──────────────────────────────────────────────────────────────────
CONTRACTS_DIR = Path(__file__).resolve().parent / "tier_1" / "contracts"
DECISION_BLUEPRINT_PATH = CONTRACTS_DIR / "decision_blueprint.json"
CANDIDATE_EVAL_PATH = CONTRACTS_DIR / "candidate_evaluation.json"
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

WEB_UI_DIR = Path(__file__).resolve().parent / "web_ui"

app = FastAPI(title="FIPE Orchestrator", version="0.1.0")

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


# ── Models ──────────────────────────────────────────────────────────────────

class WeightUpdate(BaseModel):
    w_budget: float


class QueryInput(BaseModel):
    query: str


# ── Routes ──────────────────────────────────────────────────────────────────


@app.post("/submit")
async def submit_query(
    query: str = Form(default=""),
    audio: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
):
    """
    Accepts a natural language food query (text), plus optional audio and
    image file uploads. Runs the full 3-stage multimodal pipeline:
      Tier 1a (intent parsing) → Tier 1b (Neo4j pruning) → Tier 2 (debate)
    Returns the resulting decision_blueprint.
    """
    from tier_1.multi_modal_ingestion import run_ingestion_pipeline
    from tier_1.symbolic_anchoring import run_anchoring_pipeline
    from tier_2.consensus_manager import run_debate_pipeline

    text = query.strip() if query else ""
    audio_path = None
    image_path = None

    # Save uploaded audio file
    if audio and audio.filename:
        audio_path = str(UPLOADS_DIR / audio.filename)
        with open(audio_path, "wb") as f:
            f.write(await audio.read())
        log.info("saved audio upload: %s", audio_path)

    # Save uploaded image file
    if image and image.filename:
        image_path = str(UPLOADS_DIR / image.filename)
        with open(image_path, "wb") as f:
            f.write(await image.read())
        log.info("saved image upload: %s", image_path)

    if not text and not audio_path and not image_path:
        raise HTTPException(400, "Provide at least a text query, audio file, or image.")

    log.info("─── /submit received: text='%s' audio=%s image=%s ───",
             text[:80] if text else '(none)',
             audio.filename if audio and audio.filename else '(none)',
             image.filename if image and image.filename else '(none)')

    # Stage 1: Multimodal Intent Parsing
    try:
        intent = run_ingestion_pipeline(
            raw_input=text or None,
            audio_path=audio_path,
            image_path=image_path,
        )
    except Exception as exc:
        log.error("Tier 1a failed: %s", exc)
        raise HTTPException(500, f"Intent parsing failed: {exc}")

    # Stage 2: Neo4j Allergen Pruning
    try:
        run_anchoring_pipeline()
    except Exception as exc:
        log.error("Tier 1b failed: %s", exc)
        raise HTTPException(503, f"Neo4j query failed — is the database running? ({exc})")

    # Stage 3: Multi-Agent Debate
    try:
        run_debate_pipeline()
    except Exception as exc:
        log.error("Tier 2 failed: %s", exc)
        raise HTTPException(500, f"Debate pipeline failed: {exc}")

    # Return the freshly written blueprint
    if not DECISION_BLUEPRINT_PATH.exists():
        raise HTTPException(500, "Pipeline completed but decision_blueprint.json was not created.")

    with open(DECISION_BLUEPRINT_PATH, "r", encoding="utf-8") as fh:
        blueprint = json.load(fh)

    log.info("─── /submit complete → winner: %s ───", blueprint.get("winning_dish", {}).get("name", "?"))
    return blueprint


@app.get("/decision_blueprint")
def get_decision_blueprint():
    """Returns the current decision_blueprint.json to the Flutter frontend."""
    if not DECISION_BLUEPRINT_PATH.exists():
        raise HTTPException(404, "decision_blueprint.json not found — run Tier 2 first")
    with open(DECISION_BLUEPRINT_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@app.post("/recalculate")
def recalculate(payload: WeightUpdate):
    """
    Accepts a new w_budget weight from the Flutter slider,
    re-runs the Tier 2 debate with updated weights, and returns
    the new decision_blueprint.
    """
    import math

    if not CANDIDATE_EVAL_PATH.exists():
        raise HTTPException(404, "candidate_evaluation.json not found — run Tier 1 first")

    with open(CANDIDATE_EVAL_PATH, "r", encoding="utf-8") as fh:
        evaluation = json.load(fh)

    candidates = evaluation.get("safe_candidates", [])
    budget_max = evaluation.get("source_intent", {}).get("budget_max_pkr", 1000)
    mood_seed = evaluation.get("soft_constraints", {}).get("mood_vector_seed", "neutral")
    direct_dish_prompt = evaluation.get("soft_constraints", {}).get("direct_dish_prompt", "")

    # Rebalance weights: user controls w_b, remainder split equally
    w_b = max(0.0, min(1.0, payload.w_budget))
    remaining = 1.0 - w_b
    w_h = remaining / 2.0
    w_t = remaining / 2.0

    xai_traces = [f"slider_override: w_h={w_h:.2f} w_b={w_b:.2f} w_t={w_t:.2f}"]

    scored = []
    for cand in candidates:
        protein = cand.get("protein_g", 15.0)
        calories = cand.get("calories", 500.0)
        price = cand.get("price_pkr", 0.0)

        u_h = min(1.0, (protein / max(calories, 1)) / 0.05)
        u_b = math.exp(-0.01 * price)
        u_t = 0.5  # default without live vectors

        u_total = (w_h * u_h) + (w_b * u_b) + (w_t * u_t)
        
        cand_name_lower = cand.get("name", "").lower()
        if direct_dish_prompt and len(direct_dish_prompt) > 3 and (cand_name_lower in direct_dish_prompt or direct_dish_prompt in cand_name_lower):
            u_total = 1000.0
            
        entry = {
            "dish_id": cand.get("dish_id", "?"),
            "name": cand.get("name", "unnamed"),
            "u_health": round(u_h, 6),
            "u_budget": round(u_b, 6),
            "u_taste": round(u_t, 6),
            "u_total": round(u_total, 6),
            "price_pkr": price,
        }
        scored.append(entry)
        xai_traces.append(
            f"  {entry['name']} → U_h={u_h:.4f} U_b={u_b:.4f} U_t={u_t:.4f} | U_total={u_total:.4f}"
        )

    winner = max(scored, key=lambda x: x["u_total"]) if scored else {
        "dish_id": "none", "name": "no_candidates",
        "u_health": 0, "u_budget": 0, "u_taste": 0, "u_total": 0, "price_pkr": 0,
    }
    xai_traces.append(f"winner: {winner['name']} (U_total={winner['u_total']:.4f})")

    blueprint = {
        "winning_dish": {
            "dish_id": winner["dish_id"],
            "name": winner["name"],
            "price_pkr": winner.get("price_pkr", 0),
        },
        "utility_breakdown": {
            "u_health": winner["u_health"],
            "u_budget": winner["u_budget"],
            "u_taste": winner["u_taste"],
            "u_total": winner["u_total"],
        },
        "agent_weights": {"w_h": round(w_h, 4), "w_b": round(w_b, 4), "w_t": round(w_t, 4)},
        "relaxation_rounds": 0,
        "xai_traces": xai_traces,
        "all_candidate_scores": scored,
        "source_context": {
            "budget_max_pkr": budget_max,
            "allergens_pruned": evaluation.get("source_intent", {}).get("allergens_pruned", []),
            "mood_vector_seed": mood_seed,
        },
    }

    # Persist updated blueprint
    with open(DECISION_BLUEPRINT_PATH, "w", encoding="utf-8") as fh:
        json.dump(blueprint, fh, indent=4, ensure_ascii=False)
    log.info("recalculated blueprint with w_b=%.2f → winner: %s", w_b, winner["name"])

    return blueprint

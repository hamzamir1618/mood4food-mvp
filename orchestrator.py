"""
FastAPI Orchestrator — serves the web UI, runs the full ingestion-to-debate
pipeline from user queries, and handles weight recalculation.

Run:  uvicorn orchestrator:app --host 0.0.0.0 --port 8000 --reload
Open: http://localhost:8000/
"""

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.fulfillment import router as fulfillment_router
from api.health import router as health_router
from api.recalculate import router as recalculate_router
from api.submit import router as submit_router

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


# ── Include API Routers ─────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(submit_router)
app.include_router(recalculate_router)
app.include_router(fulfillment_router)

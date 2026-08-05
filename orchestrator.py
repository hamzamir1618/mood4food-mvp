from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.rate_limit import limiter

"""
FastAPI Orchestrator — serves the web UI, runs the full ingestion-to-debate
pipeline from user queries, and handles weight recalculation.

Run:  uvicorn orchestrator:app --host 0.0.0.0 --port 8000 --reload
Open: http://localhost:8000/
"""

import logging
import uuid
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.alternate import router as alternate_router
from api.fulfillment import router as fulfillment_router
from api.health import router as health_router
from api.recalculate import router as recalculate_router
from api.submit import router as submit_router
from config import settings

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

frontend_origins = [
    origin.strip() for origin in settings.FRONTEND_ORIGIN.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving for web UI ──────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(WEB_UI_DIR)), name="static")



app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

structlog_logger = structlog.get_logger(__name__)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    structlog_logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(status_code=500, content={"error": "internal_server_error"})


@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serves the Mood4Food web UI."""
    return FileResponse(str(WEB_UI_DIR / "index.html"))


# ── Include API Routers ─────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(submit_router)
app.include_router(recalculate_router)
app.include_router(fulfillment_router)
app.include_router(alternate_router)

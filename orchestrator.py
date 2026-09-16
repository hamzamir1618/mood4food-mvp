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
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.alternate import router as alternate_router
from api.approve import router as approve_router
from api.areas import router as areas_router
from api.auth import router as auth_router
from api.chat import router as chat_router
from api.fulfillment import router as fulfillment_router
from api.health import router as health_router
from api.profile import router as profile_router
from api.rate_limit import limiter
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
# The Phase 6 frontend, built by Vite. Served from here so the app and the API share
# an origin: the login cookie is SameSite=lax, so a split origin would drop it.
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend" / "dist"
FRONTEND_BUILT = (FRONTEND_DIR / "index.html").exists()

app = FastAPI(title="FIPE Orchestrator", version="0.2.0")


@app.on_event("startup")
async def startup_event():
    import os

    import groq

    from config import DEV_AUTH_SECRET, DEV_SESSION_SECRET, settings
    from tier_1.groq_extractor import GROQ_MODEL

    if settings.SESSION_SECRET == DEV_SESSION_SECRET:
        log.warning(
            "STARTUP: SESSION_SECRET is the built-in dev placeholder. "
            "Set SESSION_SECRET in the environment before deploying."
        )
    if settings.AUTH_SECRET == DEV_AUTH_SECRET:
        log.warning(
            "STARTUP: AUTH_SECRET is the built-in dev placeholder. "
            "Set AUTH_SECRET in the environment before deploying."
        )

    # Accounts: Neo4j constraints, then the similar-tastes index rebuilt from Neo4j
    # (it lives in memory, because free hosts have no persistent disk).
    try:
        from accounts import store, taste_index

        store.ensure_schema()
        indexed = taste_index.rebuild(store.all_taste_models())
        log.info(f"STARTUP: accounts ready; {indexed} users in the similar-tastes index.")
        cap = store.account_capacity()
        log.info(
            f"STARTUP: Neo4j holds {cap['nodes']} nodes and {cap['relationships']} "
            f"relationships; {cap['users']} of {cap['max_users']} accounts in use."
        )
    except Exception as e:
        log.warning(
            f"STARTUP: accounts setup failed ({e}). Sign-in needs Neo4j; the similar-tastes "
            "index stays empty until the next restart."
        )

    provider = os.environ.get("RESTAURANT_PROVIDER", "neo4j").upper()
    log.info(f"STARTUP: Active restaurant data source is: {provider}")

    if settings.INTENT_EXTRACTOR == "groq":
        log.info(f"STARTUP: Performing health check for Groq API using model {GROQ_MODEL}...")
        if not settings.GROQ_API_KEY:
            log.warning(
                "STARTUP: INTENT_EXTRACTOR is 'groq' but GROQ_API_KEY is not set. "
                "Intent extraction will use the keyword fallback."
            )
            return

        try:
            client = groq.Groq(api_key=settings.GROQ_API_KEY)
            client.chat.completions.create(
                messages=[{"role": "user", "content": "ping"}],
                model=GROQ_MODEL,
                max_tokens=5,
            )
            log.info("STARTUP: Groq API health check passed.")
        except Exception as e:
            # Degrade rather than exit: GroqExtractorImpl already falls back to the
            # keyword extractor per request, and a cold-start blip on a free tier
            # should not permanently kill the instance.
            log.warning(
                f"STARTUP: Groq health check failed for model {GROQ_MODEL} ({e}). "
                "Continuing with the keyword extractor as fallback."
            )


class SessionIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "session_id" not in request.session:
            request.session["session_id"] = uuid.uuid4().hex
        request.state.session_id = request.session["session_id"]
        response = await call_next(request)
        return response


app.add_middleware(SessionIDMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

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

# ── Static file serving ─────────────────────────────────────────────────────
# /static keeps the Phase 1 web UI (it still backs the style guide); /assets carries
# the built frontend's own files.
app.mount("/static", StaticFiles(directory=str(WEB_UI_DIR)), name="static")
if FRONTEND_BUILT:
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
else:
    log.warning("frontend/dist is missing — run `npm run build` in frontend/ to serve the app")


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

structlog_logger = structlog.get_logger(__name__)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    structlog_logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(status_code=500, content={"error": "internal_server_error"})


@app.get("/", include_in_schema=False)
def serve_frontend():
    """The Phase 6 app when it has been built; the Phase 1 web UI until then."""
    if FRONTEND_BUILT:
        return FileResponse(str(FRONTEND_DIR / "index.html"))
    return FileResponse(str(WEB_UI_DIR / "index.html"))


@app.get("/legacy", include_in_schema=False)
def serve_legacy_ui():
    """The Phase 1 web UI, kept reachable for the style guide and for comparison."""
    return FileResponse(str(WEB_UI_DIR / "index.html"))


# ── Include API Routers ─────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(submit_router)
app.include_router(recalculate_router)
app.include_router(fulfillment_router)
app.include_router(alternate_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(approve_router)
app.include_router(chat_router)
app.include_router(areas_router)

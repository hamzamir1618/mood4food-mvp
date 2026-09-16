# Mood4Food: one image, one origin. The frontend is built and then served by the
# API itself, so the login cookie (SameSite=lax) is never sent cross-site.

# ── Stage 1: build the frontend ─────────────────────────────────────────────
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: the API, with the built frontend inside it ─────────────────────
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Dependencies first, so a code change doesn't reinstall them.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The application. The dataset under data/ is deliberately not copied: it is
# ODbL-licensed and git-ignored, and the graph is seeded separately (see
# docs/DEPLOYMENT.md), so the image holds no restaurant data.
COPY accounts/ ./accounts/
COPY api/ ./api/
COPY dialogue/ ./dialogue/
COPY pipeline/ ./pipeline/
COPY tier_1/ ./tier_1/
COPY tier_2/ ./tier_2/
COPY tier_3/ ./tier_3/
COPY web_ui/ ./web_ui/
COPY config.py orchestrator.py ./
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Uploads are written at runtime; the container filesystem is fine for them
# because nothing depends on them surviving a restart.
RUN mkdir -p uploads

EXPOSE 8000
# The host's PORT wins where the platform sets one (Render, Fly and the like).
CMD ["sh", "-c", "uvicorn orchestrator:app --host 0.0.0.0 --port ${PORT}"]

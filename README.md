# FIPE — Mood4Food MVP

> **AI-powered food recommendation engine** built on three academic pillars:  
> Graph Theory · Game Theory · Compiler Design

Mood4Food is a local-first, offline-capable decision-support system that recommends the best dish for a user based on their budget, dietary restrictions, health goals, and taste preferences. It uses a 3-tier pipeline architecture with deterministic reasoning and full explainability.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    TIER 3 — WEB UI (HTML/CSS/JS)                   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│   │ Query Bar     │  │ Winner Card  │  │ Budget Slider        │    │
│   │ POST /submit  │  │ Score Bars   │  │ POST /recalculate    │    │
│   └──────┬───────┘  └──────────────┘  └──────────┬───────────┘    │
│          │          GET /decision_blueprint       │                │
└──────────┼───────────────────────────────────────┼────────────────┘
           │                                       │
           ▼                                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                    FASTAPI ORCHESTRATOR (:8000)                    │
│         POST /submit → Tier 1a → Tier 1b → Tier 2 → respond      │
└──────────┬────────────────────────────────────────────────────────┘
           │
     ┌─────┴──────────────────────────────────┐
     ▼                                        ▼
┌──────────────┐                    ┌──────────────────┐
│   TIER 1     │                    │      TIER 2      │
│ Neo4j (:7687)│                    │ Local Vector Store│
│ Cypher Prune │                    │ Nash Debate Loop  │
└──────────────┘                    └──────────────────┘

JSON Contract Flow:
  grounded_intent.json → candidate_evaluation.json → decision_blueprint.json
```

### Three Pillars

| Pillar | Implementation | Role |
|--------|---------------|------|
| **Graph Theory** | Neo4j Cypher queries with topological allergen pruning (up to 5 hops) | Filters unsafe dishes deterministically |
| **Game Theory** | Nash Equilibrium weighted utility aggregation with constraint relaxation | Selects the optimal dish across health, budget, and taste |
| **Compiler Design** | Server-Driven UI — frontend is a pure function of `decision_blueprint.json` | Real-time UI updates without page reload |

---

## Project Structure

```
MVP/
├── orchestrator.py              # FastAPI server — serves UI + API
├── seed_neo4j.py                # Seeds Neo4j with 55 dishes & 74 ingredients
├── requirements.txt             # Python dependencies
│
├── web_ui/                      # Web frontend (served at http://localhost:8000/)
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── tier_1/                      # Perception & Grounding
│   ├── multi_modal_ingestion.py # Multimodal intent parsing (Whisper audio + vision stub + text)
│   ├── symbolic_anchoring.py    # Neo4j allergen pruning → candidate_evaluation.json
│   └── contracts/               # JSON contract files (pipeline output)
│       ├── grounded_intent.json
│       ├── candidate_evaluation.json
│       └── decision_blueprint.json
│
├── tier_2/                      # Multi-Agent Debate
│   ├── agents.py                # Utility calculators (health, budget, taste)
│   └── consensus_manager.py     # Nash equilibrium debate → decision_blueprint.json
│
└── fipe_flutter/                # (Legacy) Flutter SDUI frontend
    └── lib/main.dart
```

---

## Prerequisites

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Docker | Any recent | Neo4j container |
| FFmpeg | Any | Required by Whisper for audio transcription |
| Git | Any | Version control |
| Flutter *(optional)* | 3.x | Only if using the legacy Flutter frontend |

> **FFmpeg install:** `winget install Gyan.FFmpeg` (Windows) · `brew install ffmpeg` (macOS) · `apt install ffmpeg` (Linux)

---

## Setup & Deployment

### 1. Clone & Create Virtual Environment

```powershell
git clone <repo-url>
cd MVP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Verify:

```bash
python -c "import fastapi, neo4j; print('All dependencies OK')"
```

### 3. Start Neo4j (Docker)

```powershell
docker run --name neo4j_mood4food -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/Mood4Food -d neo4j:latest
```

Wait until it's healthy:

```bash
docker logs neo4j_mood4food --tail 5
```

Look for `Started.` in the output. The Neo4j Browser is at `http://localhost:7474` (credentials: `neo4j` / `Mood4Food`).

### 4. Seed the Database

```bash
python seed_neo4j.py
```

Expected output:

```
[OK]  Connected to Neo4j at bolt://localhost:7687
[OK]  Seeded 55 Dish nodes
[OK]  Seeded 74 Ingredient nodes
[OK]  Created 626 CONTAINS relationships
[OK]  Neo4j seed complete — ready for symbolic_anchoring.py
```

### 5. Run the Processing Pipeline (One-Shot)

These three commands generate the JSON contracts that feed the UI:

```bash
# Tier 1a — Parse user intent
python tier_1/multi_modal_ingestion.py

# Tier 1b — Query Neo4j, prune allergens
python tier_1/symbolic_anchoring.py

# Tier 2 — Nash equilibrium debate
python -m tier_2.consensus_manager
```

### 6. Launch the Application

```bash
uvicorn orchestrator:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000/** in your browser. Done.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the Mood4Food web UI |
| `GET` | `/decision_blueprint` | Returns the current decision blueprint JSON |
| `POST` | `/submit` | Accepts `multipart/form-data`: `query` (text), `audio` (file), `image` (file) — runs full pipeline |
| `POST` | `/recalculate` | Accepts `{"w_budget": float}`, returns recalculated blueprint |

---

## Usage

1. **Search for food** — Type a natural language query in the search bar, e.g. `"food under 300 rupees, no meat no dairy"`.
2. **Attach audio** — Click 🎤 to upload an audio file (`.wav`, `.mp3`, `.m4a`). Whisper transcribes it and merges with your text.
3. **Attach image** — Click 📷 to upload a food photo. Keywords are extracted from the filename.
4. **View the recommendation** — The app shows the best dish based on your constraints.
5. **Adjust budget priority** — Use the slider to control how much weight is given to price.
6. **View all options** — Scroll down to see every candidate dish ranked by score.
7. **Understand the reasoning** — Click "How It Works" to see the full AI reasoning trace.

---

## Validation Tests

### Test 1: Graph Theory — Allergen Pruning

Re-run the pipeline with different allergens and verify dishes are correctly excluded:

```bash
python -c "from tier_1.multi_modal_ingestion import run_ingestion_pipeline; run_ingestion_pipeline('I want food under 500 rupees, no meat no dairy')"
python tier_1/symbolic_anchoring.py
python -m tier_2.consensus_manager
```

**Pass:** `candidate_evaluation.json` contains zero dishes linked to meat or dairy.

### Test 2: Game Theory — Nash Equilibrium

Move the Budget Priority slider to maximum (100%). The cheapest dish should win.

**Pass:** The winning dish changes to the one with the lowest `price_pkr`.

### Test 3: Compiler Design — SDUI Live Mapping

Move the slider and observe the UI updating in real-time without a page refresh.

**Pass:** All UI components update from the JSON response via a single `POST /recalculate` call.

---

## Teardown

```bash
# Stop the server
Ctrl+C

# Stop and remove Neo4j
docker stop neo4j_mood4food
docker rm neo4j_mood4food

# Deactivate the virtual environment
deactivate
```

---

## Tech Stack

- **Backend:** FastAPI + Uvicorn
- **Graph DB:** Neo4j (Docker)
- **Vector Store:** Local JSON-backed stub (swappable for ChromaDB)
- **Frontend:** Vanilla HTML / CSS / JavaScript (served by FastAPI)
- **Data Format:** JSON contracts between tiers

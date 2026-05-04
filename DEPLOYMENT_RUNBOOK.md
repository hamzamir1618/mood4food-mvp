# DEPLOYMENT RUNBOOK — FIPE Mood4Food MVP

> **Topology**: 3-Tier Local-First Offline Stack  
> **Backend**: FastAPI + Neo4j + ChromaDB  
> **Frontend**: Flutter SDUI Engine  
> **JSON Contracts**: `grounded_intent.json` → `candidate_evaluation.json` → `decision_blueprint.json`

---

## 1. Prerequisites & Environment Setup

### 1.1 Python Virtual Environment

**Windows (PowerShell):**
```powershell
cd "D:\OFFICE WORK\FIPE\Code\MVP"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
cd /path/to/MVP
python3 -m venv .venv
source .venv/bin/activate
```

### 1.2 Install Python Dependencies

```bash
pip install -r requirements.txt
```

Verify critical packages:

```bash
python -c "import fastapi, neo4j, chromadb; print('All dependencies OK')"
```

### 1.3 Flutter SDK

Ensure the Flutter SDK is installed and on `PATH`. Verify:

```bash
flutter doctor
```

Required checks (must show `[✓]`):
- Flutter SDK
- Chrome (for `-d chrome` target)
- Connected device or desktop toolchain

Install Flutter frontend dependencies:

```bash
cd fipe_flutter
flutter pub get
cd ..
```

### 1.4 Docker

Docker must be installed and the daemon running. Verify:

```bash
docker --version
```

---

## 2. Substrate Initialization

### 2.1 Neo4j (Graph Database — Tier 1b)

Spin up the local Neo4j instance:

```bash
docker run --name neo4j_mood4food \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/Mood4Food \
  -d neo4j:latest
```

**Windows (single-line):**
```powershell
docker run --name neo4j_mood4food -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/Mood4Food -d neo4j:latest
```

Verify Neo4j is healthy:

```bash
docker logs neo4j_mood4food --tail 5
```

Wait until you see `Started.` in the output. The Neo4j Browser is accessible at `http://localhost:7474` (credentials: `neo4j` / `Mood4Food`).

### 2.2 ChromaDB (Vector Store — Tier 2a)

No manual setup required. ChromaDB runs as an embedded persistent client. The directory `tier_2/chroma_store/` is auto-created on first execution of the backend.

---

## 3. Backend Execution

### 3.1 Run the Tier 1a Intent Parsing Pipeline (One-Shot)

This generates the initial `grounded_intent.json` contract:

```bash
python tier_1/multi_modal_ingestion.py
```

**Expected terminal output:**
```
Tier 1a: Intent Parsing Pipeline START
text_stub | cleaned=i want something spicy under 800 rupees, no meat
grounded_intent written → .../tier_1/contracts/grounded_intent.json
Tier 1a: Intent Parsing Pipeline DONE
```

Verify the contract:

```bash
cat tier_1/contracts/grounded_intent.json
```

```json
{
    "hard_constraints": {
        "budget_max_pkr": 800,
        "allergens_pruned": ["meat"]
    },
    "soft_constraints": {
        "protein_priority": "normal",
        "mood_vector_seed": "spicy"
    }
}
```

### 3.2 Run the Tier 1b Graph Constraint Pipeline (One-Shot)

This reads `grounded_intent.json`, queries Neo4j, and writes `candidate_evaluation.json`:

```bash
python tier_1/symbolic_anchoring.py
```

> **Note**: This requires Neo4j to be running and seeded with `:Dish` and `:Ingredient` nodes. If the graph is empty, `candidate_evaluation.json` will contain `"candidate_count": 0`.

### 3.3 Run the Tier 2 Debate Pipeline (One-Shot)

This reads `candidate_evaluation.json`, runs the Nash Equilibrium aggregation, and writes `decision_blueprint.json`:

```bash
python -m tier_2.consensus_manager
```

### 3.4 Launch the FastAPI Orchestrator (Persistent)

This is the long-running backend process that serves the Flutter frontend:

```bash
uvicorn orchestrator:app --host 0.0.0.0 --port 8000 --reload
```

**Expected terminal output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
```

Keep this terminal open. All reasoning traces from the Intent Parsing, Graph Constraint, and Multi-Agent Debate pipelines will stream to this terminal when triggered by the frontend.

API endpoints now live:

| Method | Endpoint               | Function                              |
|--------|------------------------|---------------------------------------|
| `GET`  | `/decision_blueprint`  | Returns current `decision_blueprint.json` |
| `POST` | `/recalculate`         | Accepts `{"w_budget": float}`, returns recalculated blueprint |

Verify manually:

```bash
curl http://localhost:8000/decision_blueprint
```

---

## 4. Frontend Execution

### 4.1 Launch the Flutter SDUI Engine

Open a **new terminal** (keep the FastAPI terminal running):

```bash
cd fipe_flutter
flutter run -d chrome
```

**Alternative targets:**

| Target     | Command                        |
|------------|--------------------------------|
| Chrome     | `flutter run -d chrome`        |
| Windows    | `flutter run -d windows`       |
| macOS      | `flutter run -d macos`         |
| Linux      | `flutter run -d linux`         |
| Edge       | `flutter run -d edge`          |

The app will launch and immediately issue `GET /decision_blueprint` to the FastAPI backend.

---

## 5. Use Case Testing Protocol — Validation Matrix

### TEST 1: Pillar 1 — Graph Theory (Topological Allergen Pruning)

**Objective:** Verify that submitting a hard constraint triggers deterministic graph pruning via Neo4j Cypher.

**Steps:**

1. In the FastAPI terminal, re-run the ingestion pipeline with a meat allergy constraint:

   ```bash
   python -c "from tier_1.multi_modal_ingestion import run_ingestion_pipeline; run_ingestion_pipeline('I want food under 500 rupees, no meat no dairy')"
   ```

2. Verify `grounded_intent.json` now contains the updated allergens:

   ```bash
   cat tier_1/contracts/grounded_intent.json
   ```

   **Expected:**
   ```json
   {
       "hard_constraints": {
           "budget_max_pkr": 500,
           "allergens_pruned": ["dairy", "meat"]
       }
   }
   ```

3. Run the symbolic anchoring pipeline:

   ```bash
   python tier_1/symbolic_anchoring.py
   ```

4. **Verify in the terminal output** that Neo4j executed the topological pruning Cypher:

   ```
   neo4j query | pruned_list=['dairy', 'meat'], budget_max=500
   neo4j returned N safe candidates
   ```

5. Inspect `candidate_evaluation.json` to confirm unsafe nodes (dishes containing meat or dairy within 5 hops) have been dropped:

   ```bash
   cat tier_1/contracts/candidate_evaluation.json
   ```

**Pass Criteria:** `safe_candidates` array contains zero dishes linked to meat or dairy ingredient nodes. The `candidate_count` reflects the pruned set.

---

### TEST 2: Pillar 2 — Game Theory (Nash Equilibrium Recalculation)

**Objective:** Verify that adjusting the Budget Priority slider triggers a weighted utility recalculation and selects a cheaper dish.

**Steps:**

1. Ensure the FastAPI orchestrator is running (`uvicorn orchestrator:app --reload`).

2. In the Flutter app, locate the **Budget Priority** slider at the bottom of the dashboard.

3. Slide the **Budget Priority** to **maximum** (`w_b = 1.00`).

4. **Observe the FastAPI terminal.** It must log the recalculation with updated weights:

   ```
   INFO | recalculated blueprint with w_b=1.00 → winner: <dish_name>
   ```

5. The recalculation formula logged in the XAI traces must show:

   ```
   slider_override: w_h=0.00 w_b=1.00 w_t=0.00
   <dish_a> → U_h=0.XXXX U_b=0.XXXX U_t=0.XXXX | U_total=0.XXXX
   <dish_b> → U_h=0.XXXX U_b=0.XXXX U_t=0.XXXX | U_total=0.XXXX
   winner: <cheapest_dish> (U_total=0.XXXX)
   ```

   Since `w_b = 1.0` and `U_b = exp(-0.01 × price)`, the dish with the lowest `price_pkr` will have the highest `U_total`.

6. Verify `decision_blueprint.json` was overwritten with the new winner:

   ```bash
   cat tier_1/contracts/decision_blueprint.json
   ```

**Pass Criteria:** The winning dish changes to the cheapest candidate. The `utility_breakdown.u_total` is dominated entirely by `U_b`. The `agent_weights` object reads `{"w_h": 0.0, "w_b": 1.0, "w_t": 0.0}`.

---

### TEST 3: Pillar 3 — Compiler Design (SDUI AST Live Mapping)

**Objective:** Verify that the Flutter frontend deterministically maps the newly generated `decision_blueprint.json` into the Equilibrium Card widget tree without requiring a manual page refresh.

**Steps:**

1. With the Flutter app open, note the current values displayed on the **Equilibrium Card**:
   - Dish name
   - `U = X.XXXX` total score
   - Utility bar values (U_h, U_b, U_t)
   - XAI trace step count

2. Move the **Budget Priority** slider to a new position (e.g., from `0.30` to `0.80`).

3. **Immediately observe the Flutter UI** (no page refresh, no app restart):

   | Component             | Expected Behaviour                                         |
   |-----------------------|------------------------------------------------------------|
   | Equilibrium Card      | Dish name updates to reflect the new winner                |
   | `U = X.XXXX` badge    | Total utility score recalculates inline                    |
   | Health bar (green)    | `U_h` value and bar width update                           |
   | Budget bar (blue)     | `U_b` value and bar width update (dominant when `w_b` is high) |
   | Taste bar (pink)      | `U_t` value and bar width update                           |
   | XAI Trace panel       | Displays new `slider_override:` trace with updated weights |
   | `w_b = X.XX` badge    | Reflects the slider's current position                     |

4. Verify the update was driven by the `POST /recalculate` → JSON response → `setState()` cycle, not by a page reload. The FastAPI terminal should show exactly one `recalculated blueprint` log entry per slider interaction.

**Pass Criteria:** All UI components update in real-time from the JSON response. The Equilibrium Card acts as a pure function of `decision_blueprint.json` — no stale state, no manual refresh.

---

## 6. Full Stack Topology Summary

```
┌────────────────────────────────────────────────────────────────────┐
│                        TIER 3 — FLUTTER                           │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│   │ Equilibrium  │  │ Utility Bars │  │ Budget Slider        │    │
│   │ Card         │  │ U_h, U_b, U_t│  │ POST /recalculate    │    │
│   └──────┬───────┘  └──────────────┘  └──────────┬───────────┘    │
│          │          GET /decision_blueprint       │                │
└──────────┼───────────────────────────────────────┼────────────────┘
           │                                       │
           ▼                                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                    FASTAPI ORCHESTRATOR (:8000)                    │
└──────────┬────────────────────────────────────────────────────────┘
           │
     ┌─────┴──────────────────────────────────┐
     ▼                                        ▼
┌──────────────┐                    ┌──────────────────┐
│   TIER 1     │                    │      TIER 2      │
│ Neo4j (:7687)│                    │ ChromaDB (embed) │
│ Cypher Prune │                    │ Vector Retrieval │
└──────────────┘                    │ Nash Debate Loop │
                                    └──────────────────┘

JSON Contract Flow:
  grounded_intent.json → candidate_evaluation.json → decision_blueprint.json
```

---

## 7. Teardown

Stop the Flutter app: `Ctrl+C` in the Flutter terminal.

Stop the FastAPI server: `Ctrl+C` in the Uvicorn terminal.

Stop and remove the Neo4j container:

```bash
docker stop neo4j_mood4food
docker rm neo4j_mood4food
```

Deactivate the virtual environment:

```bash
deactivate
```

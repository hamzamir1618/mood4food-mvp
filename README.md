# Overview

# Architecture

# Setup

1. **Python Environment**
Run the following to install dependencies and pre-commit hooks:
```bash
pip install -r requirements.txt
pip install pre-commit && pre-commit install
```

2. **Groq API Key (Semantic Intent Extraction)**
The natural language intent parser uses the `openai/gpt-oss-120b` model via Groq for high-speed, accurate constraint extraction. 
- Sign up for a free account at [console.groq.com](https://console.groq.com/) (No credit card required).
- Generate a new API Key.
- Copy `.env.example` to `.env` and add your key:
```env
GROQ_API_KEY=gsk_your_key_here
```
*(No local model downloads or GPUs are required. If the API rate limits or times out, the app will gracefully fall back to a local regex keyword extractor).*

3. **Secrets for Sessions and Sign-in**
Accounts (sign-in, saved profiles, history) are described in [docs/ACCOUNTS.md](docs/ACCOUNTS.md). Before deploying, set two different random values in `.env`; startup warns while either is still the built-in placeholder:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
```env
SESSION_SECRET=<first value>
AUTH_SECRET=<second value>
AUTH_COOKIE_SECURE=true   # when served over HTTPS
```

# Running Locally

To launch the full stack application locally:

1. **Start Substrate Services**
Make sure Docker is running, then spin up Neo4j and Redis:
```bash
docker run --name neo4j_mood4food -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/Mood4Food -d neo4j:2026.07.1
docker run --name redis_mood4food -p 6379:6379 -d redis:latest
```

2. **Load the Dish Data**
Build the dataset and seed Neo4j. The one-time USDA download and the full run order are in [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md).
```bash
python -m pipeline.build_dataset
python seed_real_data.py --reset
```

3. **Start the FastAPI Orchestrator Backend**
In your Python virtual environment, start the Uvicorn server:
```bash
uvicorn orchestrator:app --host 0.0.0.0 --port 8000 --reload
```

4. **Launch the React Frontend**
Open a new terminal and start the Vite dev server (requires Node.js 18+):
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The dev server proxies API calls to the backend on port 8000.
The legacy vanilla-JS UI is still served by the backend at http://localhost:8000/.

# Running Tests

Run the full pytest suite:
```bash
pytest tests/
```

# Deployment
See [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md) for deployment instructions.

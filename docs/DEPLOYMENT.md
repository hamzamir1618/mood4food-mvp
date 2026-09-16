# Deployment

Mood4Food deploys as **one container on one origin**: the API serves the built
frontend itself. That is not a detail of taste — the login cookie is `httpOnly`,
`SameSite=lax`, so if the app and the API sat on different domains the browser
would drop the cookie on every API call and sign-in would silently fail.

The whole stack runs on free tiers, and nothing here needs a card.

## What runs where

| Piece | Where | Notes |
|---|---|---|
| App and API | One container, from the repo's `Dockerfile` | Serves `frontend/dist` at `/`, the API on the same origin |
| Graph | A hosted Neo4j (AuraDB Free) | `GRAPH_NODE_LIMIT` and `GRAPH_RELATIONSHIP_LIMIT` are already sized for it |
| Sessions | A hosted Redis | Sessions, the conversation and the decision contracts |
| Intent extraction | Groq's free tier | Or the keyword extractor, which costs nothing |

Confirm each provider's current free limits before committing to one: they change,
and some sleep when idle, which shows up as a slow first request.

## Access: a private link

The deployment is **not public**. Sign-up is open to anyone who can reach the
service, so the link is shared rather than published, for two reasons:

- the Groq free tier is a daily allowance that a public link would exhaust; and
- open sign-up would mean holding strangers' emails and password hashes for a
  student project.

Groq stays on for the demo: it is the real intent extractor, and it is what the
project claims. Running out of the daily allowance does not break anything —
`GroqExtractorImpl` falls back to the keyword extractor on a rate limit, a timeout,
a network error, an API error or a malformed reply, and logs each one with a
`reason`. A fallback request is simply understood a little more bluntly; the rest of
the pipeline is untouched.

Only one Groq call is made per **new request**. Answers, skips and refinements are
deterministic and never reach the LLM, so a whole conversation costs one extraction.

Set `INTENT_EXTRACTOR=keyword` when you want no LLM calls at all — a long demo, or a
day when the allowance is already spent.

## The dataset is not in the image

`data/` is ODbL-licensed and git-ignored, and the `Dockerfile` deliberately does
not copy it. The image holds no restaurant data. Seed the hosted graph from your
own machine instead:

```bash
# Build the dataset locally if it isn't built already
python -m pipeline.build_dataset

# Point at the hosted graph and seed it
NEO4J_URI=neo4j+s://<your-instance>.databases.neo4j.io \
NEO4J_USER=neo4j \
NEO4J_PASSWORD=<password> \
python -m pipeline.seed --reset
```

Re-run it whenever the dataset changes. Nothing in the running service writes
dishes or restaurants, so this is the only way data reaches the graph.

## Configuration

Copy `.env.example` and fill it in. For a deployed instance:

| Variable | Deployed value |
|---|---|
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | From the hosted graph |
| `REDIS_URL` | From the hosted Redis, with TLS (`rediss://`) where offered |
| `SESSION_SECRET`, `AUTH_SECRET` | Two different fresh secrets. The app warns loudly at startup if the dev placeholders are still in use |
| `AUTH_COOKIE_SECURE` | `true` — the service is behind HTTPS |
| `FRONTEND_ORIGIN` | The deployed origin, e.g. `https://mood4food.example.com` |
| `GROQ_API_KEY` | Only when `INTENT_EXTRACTOR` is `groq` |
| `INTENT_EXTRACTOR` | `keyword` to spend no Groq quota, `groq` for the full extractor |

## Building and running the image

```bash
docker build -t mood4food .
docker run --rm -p 8000:8000 --env-file .env mood4food
```

The build runs `npm ci && npm run build` for the frontend, then installs the
Python dependencies and copies the application in. The container reads `PORT`
where the platform sets one.

## Before sharing the link

- [ ] Both secrets replaced, and `AUTH_COOKIE_SECURE=true`
- [ ] `FRONTEND_ORIGIN` set to the deployed origin
- [ ] Graph seeded, and `GET /health` reports `neo4j` and `redis` both `ok`
- [x] Attribution shown in the app: a line on the home screen opens "Where the data
      comes from", crediting Open Food Facts and USDA for nutrition, OpenStreetMap
      for locations and Open-Meteo for weather, with links (see `ATTRIBUTIONS.md`)
- [ ] The accent's contrast checked on small labels (orange on white is ~3.6:1,
      which is below the 4.5:1 minimum for small text)
- [ ] One end-to-end run against the deployed instance: ask, answer, pick, approve

## What the deployment does not include

- **Audio and image input.** They work locally; `DEPLOY_MODE=lite` turns them off.
- **The Phase 1 web UI.** Still in the image and reachable at `/legacy`, because
  the style guide references it.

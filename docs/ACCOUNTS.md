# Accounts

Phase 2 adds user accounts, a saved profile, an interaction history for the learning loop, and a "similar tastes" index. This page covers what is stored, how sign-in works, and what is still missing. The code is in `accounts/`, with routes in `api/auth.py` and `api/profile.py`.

## What is stored

Everything lives in the same Neo4j database as the dishes:

```
(:User)-[:HAS_DIETARY]->(:DietaryProfile)   allergies, diet, halal_only
(:User)-[:HAS_GOALS]->(:GoalProfile)        goal, typical_spend_pkr
(:User)-[:HAS_TASTE]->(:TasteModel)         vector, confidence, updates, persona_prior
(:User)-[:DID]->(:InteractionEvent)-[:ABOUT]->(:Dish)
```

- **User.** Email (lower-cased, unique), display name, Argon2id password hash, token version and creation time.
- **DietaryProfile.** Hard constraints. Allergies must come from the dataset's allergen tags: dairy, egg, fish, shellfish, gluten, nuts, soy and sesame. They are applied to every query while the user is signed in (see below).
- **GoalProfile.** A fitness goal (balanced, muscle gain, weight loss or light) and a usual spend. Phase 3 scoring uses both.
- **TasteModel.** The six taste dimensions, each 0–1, with a confidence per dimension.
  - It starts as the chosen persona's taste, with every confidence at 0.
  - A value the user sets by hand gets confidence 1.
  - Approvals move them, along with how much each dimension matters and learned weights for health, budget and taste (see `LEARNING.md`).
  - Vectors are stored as lists in the order sweet, salty, sour, bitter, umami, spice, because Neo4j properties can't be maps.
- **InteractionEvent.** One recommendation the user asked for, or one dish they passed over.
  - It records the query text, the winning dish, the dishes shown and the constraints in force.
  - It has at most one relationship: to the dish it is about. The other dishes shown are a list property. That keeps the graph small, because AuraDB Free caps nodes and relationships.
  - An approval (`POST /approve`) also keeps what the learning loop needs; see `LEARNING.md`.

## Sign-in

- **Passwords** are hashed with Argon2id at OWASP's recommended minimum: 19 MiB of memory, 2 passes, 1 lane.
  - argon2-cffi's default uses 64 MiB per hash. A burst of sign-ins at that setting could exhaust a 512 MB free instance.
  - Each hash records its own parameters, so raising them later only takes a rehash at the user's next sign-in, which is already wired in.
- **The session** is a signed JWT (HS256, `AUTH_SECRET`) in an httpOnly, SameSite=Lax cookie named `m4f_auth`. It lasts `AUTH_TOKEN_DAYS`, 7 by default.
- **"Sign out everywhere"** increments the user's token version, and every older token stops working. Each request checks the token version in Neo4j.
- **Sign-in timing** doesn't reveal which emails are registered: an unknown email still costs one password check.
- **Rate limits** are per IP: registration 5 an hour, sign-in 10 a minute, account deletion 5 a minute.

## Saved constraints join every query

When a signed-in user submits a query, `/submit` adds their saved allergies, diet and halal requirement to the parsed intent before Tier 1 runs. It only ever adds: nothing typed in a query can loosen a saved constraint.

If the profile can't be loaded, `/submit` returns 503 and makes no recommendation. Carrying on as if the user were a guest would silently drop their allergies.

## History, and guests who sign up

`/submit` records a "query" event, and `/alternate` records a "rejected" event for the dish passed over.

- **A guest's events** are kept in Redis under their session for 14 days, the session cookie's lifetime.
- **Registering or signing in** on the same browser moves those events to the account. The move is idempotent, so a retry adds nothing twice.
- **A lost event is logged, never raised.** Failing to record history must not cost the user their recommendation.

## Similar tastes (cosine similarity, ChromaDB)

Users' taste vectors are indexed in a ChromaDB collection and searched by cosine similarity.

- **Neo4j is the source of truth.** The index is rebuilt from Neo4j at startup and updated whenever a taste changes. It is held in memory, because free hosts have no persistent disk.
- **Only tastes with evidence are indexed.** Two users who merely picked the same persona would otherwise match perfectly, with nothing real behind it. So a user enters the index only once their taste has some confidence behind it: an approval, or a value they set by hand.
- **`GET /profile/similar-tastes` is anonymous.** It returns similarity scores only and never identifies another user. The same index feeds recommendations: dishes that users with a similar taste approved get a small, anonymous pull (see `LEARNING.md`).
- **Chroma never embeds text.** Vectors are always passed in, so Chroma never downloads its default text-embedding model. Its telemetry is switched off.

At this dataset's size ChromaDB is slower than plain NumPy and slightly approximate: a top-10 search took 2.1 ms against 0.13 ms and agreed on 98% of results, measured on 2,545 dishes. It is used here for the architecture the project proposed and because it scales.

## Staying inside AuraDB Free

Neo4j's published limits for AuraDB Free disagree: the FAQ says 200,000 nodes and 400,000 relationships, the product page 50,000 and 175,000. The app is sized for the lower figures (decided 2026-09-14):

- **Each account keeps its newest 200 events** (`EVENTS_PER_USER`). Older ones are deleted as new ones arrive. The Phase 4 learning loop should fold events into the taste model before they're trimmed.
- **A full account occupies 204 nodes and 403 relationships:** the user, three profile nodes and 200 events, each with a `DID` and an `ABOUT` relationship.
- **Registration returns 503** once one more account, with every account assumed full, would take the database past 90% of either limit (`GRAPH_HEADROOM`). That leaves room for the dish data to grow and for two sign-ups arriving at the same moment.
- **Current capacity is about 207 accounts,** with today's dataset of about 2,600 nodes and 2,500 relationships. Lowering `EVENTS_PER_USER` to 100 raises it to about 400.
- **Startup logs the numbers:** the current node and relationship counts, and how many accounts are in use out of how many fit.

## Endpoints

| Method and path | Does |
|---|---|
| `POST /auth/register` | Creates the account (email, password of at least 10 characters, optional display name and starting persona) and signs in |
| `POST /auth/login` | Signs in |
| `POST /auth/logout?everywhere=true` | Signs this browser out; with `everywhere`, every device |
| `GET /auth/me` | The signed-in user, or `{"user": null}` |
| `GET /profile` | Profile: user, dietary, goals and taste |
| `PUT /profile/dietary` | Replaces allergies, diet and halal |
| `PUT /profile/goals` | Replaces goal and usual spend |
| `PUT /profile/taste` | Sets taste dimensions by hand, e.g. `{"values": {"spice": 0.9}}` |
| `POST /profile/taste/reset` | Starts the taste again from a persona |
| `GET /profile/history` | Recent events |
| `GET /profile/similar-tastes` | Anonymous cosine-similarity matches |
| `GET /profile/learning` | What approvals have taught the model, in sentences |
| `PUT /profile/weights` | Sets health, budget and taste weights by hand |
| `POST /approve` | Approves one of the current recommendation's options (see `LEARNING.md`) |
| `GET /profile/export` | Everything stored about the user, as a JSON download (never the password hash) |
| `POST /profile/delete` | Deletes the account, profile and history; needs the password |

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `AUTH_SECRET` | dev placeholder | Signs sign-in tokens. Startup warns while it is the placeholder. Use a different value from `SESSION_SECRET`. |
| `AUTH_TOKEN_DAYS` | 7 | How long a sign-in lasts |
| `AUTH_COOKIE_SECURE` | false | Set to true when served over HTTPS |
| `EVENTS_PER_USER` | 200 | Newest events kept per account |
| `GRAPH_NODE_LIMIT` | 50000 | AuraDB Free's lower published node limit |
| `GRAPH_RELATIONSHIP_LIMIT` | 175000 | AuraDB Free's lower published relationship limit |
| `GRAPH_HEADROOM` | 0.9 | Share of either limit that accounts may fill |

In development the Vite dev server proxies the API, so the frontend and backend share an origin and the SameSite=Lax cookie works. A deployment should keep them on one origin too, by serving the built frontend from the backend.

## Not built yet

- **No email verification or password reset, by decision** (2026-09-14). Both would need an email-sending service. An email address is just a username.
- **No password change.**
- **Registration reveals whether an email is taken** (409). Without email verification this can't be avoided. The rate limit bounds it.
- **No screens.** Sign-in, onboarding and profile screens arrive with the Phase 6 frontend. Until then the endpoints can be used from FastAPI's `/docs` page.

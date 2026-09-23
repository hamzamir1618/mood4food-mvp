# Conversation

Phase 5 turns a single request into a short conversation:
- **It asks first, but only when worth it.** The concierge asks a question only when the answer would change what it recommends.
- **Refinements reuse what the request found.** "Cheaper", "milder" and the rest work on the dishes the request already turned up.

**The request's own words answer questions too (2026-09-21).** "Dinner for 4 people" sets the party size, so "Who's eating?" isn't asked and the pick is priced and portioned for four. Other words the extractor's fields can't carry — dislikes, a cooking method, an area, a nutrition goal, and the things the app has no data for — are read in `tier_1/query_words.py`; see `DECISION_CORE.md`.

It adds no LLM calls. The first message of a request goes through the intent extractor as before, and everything after it is deterministic. The code is in `dialogue/` and the endpoint in `api/chat.py`. `/submit` still gives a single recommendation; both run the same pipeline (`api/pipeline.py`).

## The turn contract

`POST /chat` takes exactly one of these per turn:

| Turn | Body | What happens |
|---|---|---|
| New request | `{"text": "I'm hungry"}` | Runs the full pipeline: intent extraction, saved constraints, Tier 1, Tier 2 |
| Answer | `{"answer": {"question": "taste", "value": "spicy"}}` | Answers the open question |
| Refinement | `{"critique": "cheaper"}` | Asks for something better than the current pick in one direction |
| Just pick | `{"skip": true}` | Stops asking and recommends |

Any turn may also carry `"location": {"lat": 33.69, "lng": 73.03, "label": "G-9 Markaz"}`. It is kept with the session, and from the next new request each dish carries a straight-line `distance_km` to its restaurant (none when the restaurant's coordinates are unknown). `/submit` takes the same as the form fields `lat`, `lng` and `location_label`. `GET /areas` lists areas to pick from.

Typed text is read as the most likely of these:
1. **While a question is open,** text that names one of its answers counts as that answer: "something hot", "around 1,200", "for 3 people".
2. **After a recommendation,** a short message (8 words or fewer) that asks for a refinement is one: "same but cheaper", "not so spicy".
3. **Anything else** is a new request.

Every reply is one of two shapes:

- **A question:** `{"type": "question", "question": {"id", "text", "why", "chips": [{"value", "label"}], "skip_label"}, "leading": "<the current best dish>"}`. The `why` says how many of the answers would change the pick.
- **A recommendation:** `{"type": "recommendation", "recommendation": <the blueprint>, "refinements": [...], "suggestions": [...]}`.

Both carry a `reply` sentence, a `conversation_id` and the `turn` number.

## When it asks

Four questions can be asked, each only while the request and the conversation haven't already settled it:

| Question | Asked when | Answers |
|---|---|---|
| What are you in the mood for? | The request named no taste | Spicy, Savoury, Something sweet, Fresh & tangy |
| Any cuisine in mind? | The request named no category or dish | The top four categories among the leading dishes |
| Roughly how much do you want to spend? | No budget in the request or the profile | Two amounts from the leading dishes' price spread |
| Who's eating? | Some leading dishes serve more than one | Just me, Two of us, Three or four, Five or more |

**How a question is chosen:**
1. For every possible question, each answer on offer is tried: the leading 150 candidates are re-ranked as if the user had given it.
2. An answer that would leave nothing to recommend is never offered.
3. The question where the most answers change the winner is asked, but only if at least half of them do (`ASK_THRESHOLD`).

**Limits:**
- At most two questions per request (`MAX_QUESTIONS`).
- None when fewer than 5 dishes are left.
- Every question has "Just pick for me".

A precise request ("spicy desi food under 2,000") settles every slot, so it goes straight to a recommendation.

## Refinements

Each refinement asks for a dish better than the current pick in one direction, and narrows the candidates the request found:

| Refinement | Keeps dishes that are… | Also |
|---|---|---|
| Cheaper | priced below the current pick | |
| Lighter | lower in calories than it | scores health for a light meal |
| Healthier | better on health, for the user's goal | |
| More filling | at least 10% higher in calories, with at least as much protein | |
| Spicier | spicier | asks for spice 0.3 above the current pick |
| Milder | milder | asks for spice 0.3 below it |
| Something different | from another cuisine; see below | |

**How refinements behave:**
- **They accumulate,** and limits only ever tighten.
- **"Something different" reads the table first.** It used to mean "another category" only, and
  failed in about half of realistic flows (measured on 12): every dish a search for pizza, nihari
  or dessert finds shares one category, and after answering a cuisine it contradicted the answer.
  Now:
  - a cuisine was answered: a different cuisine, and the answer steps aside ("Here's something
    other than Middle Eastern");
  - the dishes span several cuisines: another one;
  - they're all one cuisine: the same kind of dish from another restaurant ("Everything here is
    pizza, so here's one from somewhere else"); with a single restaurant, another dish there,
    setting aside every size of the current one so it can't return the half portion.
  Measured again on 10 flows: useful in all 10.
- **If nothing is left, it asks what to loosen** rather than stopping: "Can I loosen one thing?",
  offering only the user's own earlier choices (a budget answered, a cuisine, an earlier
  refinement), only those that would then find a dish, and never the refinement just asked for.
  Allergies, diet and halal are Tier 1 rules, not adjustments, so they are never offered.
  "Keep my pick" leaves everything as it was.
- **With nothing of the user's to loosen, the pick stays and the reply says so:** "Nothing
  cheaper is left in what you asked for, so I've kept …. A new search is the way to widen it."
- **A refinement never re-queries** the database or calls an LLM. The tests check this by counting calls.

## Saving what it heard

At a recommendation, a signed-in user gets `suggestions` for anything the conversation revealed that their profile doesn't have yet:
- an allergy or diet from the request (one combined dietary update);
- a budget they chose (their usual spend).

Each suggestion carries the exact profile update to send, and the client sends it only if the user agrees. Nothing is saved silently, because allergies, diet and budget are the user's to set.

## State and history

- **Where it lives:** the conversation is kept with the session in Redis, like the other session contracts, holding the open question, the answers and the accumulated refinements.
- **What stays in sync:** every turn writes the session's decision blueprint, so `/approve`, `/alternate` and `/recalculate` work on the conversation's current pick.
- **What's recorded:** refinements are recorded as `refined` events in the user's history. Learning ignores them; approvals are the learning signal.

## Trying it

`DEPLOY_MODE=test python -m scripts.conversation_demo` runs scripted conversations against the real dataset, using the keyword extractor so no Groq quota is spent. It prints each turn and how long it took.

## Limits

- **Only four questions exist,** and their answers are fixed lists plus typed budgets and head counts. Anything else typed while a question is open starts a new request.
- **Refinements only narrow.** "I could spend more" or "show me more options" needs a new request, because the candidates were found under the original budget.
- **The party size only changes price per person** (see `DECISION_CORE.md`). It doesn't yet favour dishes meant for sharing.
- **Screens come with Phase 6.** Until then the endpoint can be used from FastAPI's `/docs` page.

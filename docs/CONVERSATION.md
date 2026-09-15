# Conversation

Phase 5 turns a single request into a short conversation:
- **It asks first, but only when worth it.** The concierge asks a question only when the answer would change what it recommends.
- **Refinements reuse what the request found.** "Cheaper", "milder" and the rest work on the dishes the request already turned up.

It adds no LLM calls. The first message of a request goes through the intent extractor as before, and everything after it is deterministic. The code is in `dialogue/` and the endpoint in `api/chat.py`. `/submit` still gives a single recommendation; both run the same pipeline (`api/pipeline.py`).

## The turn contract

`POST /chat` takes exactly one of these per turn:

| Turn | Body | What happens |
|---|---|---|
| New request | `{"text": "I'm hungry"}` | Runs the full pipeline: intent extraction, saved constraints, Tier 1, Tier 2 |
| Answer | `{"answer": {"question": "taste", "value": "spicy"}}` | Answers the open question |
| Refinement | `{"critique": "cheaper"}` | Asks for something better than the current pick in one direction |
| Just pick | `{"skip": true}` | Stops asking and recommends |

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
| More filling | higher in calories | |
| Spicier | spicier | asks for spice 0.3 above the current pick |
| Milder | milder | asks for spice 0.3 below it |
| Something different | from another category | |

**How refinements behave:**
- **They accumulate,** and limits only ever tighten.
- **If nothing is left, the pick stays and the reply says so,** for example "Nothing cheaper fits everything you asked, so I've kept …".
- **They can't break what the request asked for.** After "spicy desi food", "something different" finds nothing, because only desi dishes were found.
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

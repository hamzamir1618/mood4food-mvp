# Learning Loop

Phase 4 makes Mood4Food adapt to the dishes a user approves. Every update is a rule a person can read, check and reset. A black-box model might handle a new user better, but it would destroy the explainability this project depends on. The rules are in `accounts/learning.py`, the approve action in `api/approve.py`. Every number below is a named constant in `accounts/learning.py`.

## The approve action

`POST /approve {"dish_id": ...}` marks one of the current recommendation's options as "this one".

- **Only the options shown can be approved:** the winner and the runners-up. Anything else returns 404, so learning can't be steered with arbitrary dishes.
- **Each dish can be approved once per recommendation.** Repeats return "Already noted" and teach nothing.
- **A signed-in user's model updates immediately.** The response lists what changed, for example: "Your taste moved: spicy 0.40 → 0.55."
- **A guest's approval is kept with their session.** When they register or sign in on the same browser, it is replayed into their new model.
- **Every approval is recorded as an `approved` event.** The event keeps the dish's taste values, how far that data can be trusted, and its scores next to the top pick's. Learning then never has to look the dish up again, and still works after a data reload.

## What an approval teaches

### Taste

```
α     = 0.3 / (1 + n / 10) × trust
taste ← (1 − α) · taste + α · dish taste
```

- **`n` is the number of approvals learned from so far.** The first approval moves the taste 30% of the way toward the dish. By the tenth, the step has halved. Early approvals shape the model quickly and later ones refine it.
- **`trust` is how far the dish's flavour data can be trusted.** It's the same confidence the decision core uses: 1.0 for original values, 0.25 for a global prior. A flavour we only estimated teaches a quarter as much.
- **Each dimension's confidence rises by the same step.** The user's taste replaces the persona's in scoring as soon as it has any evidence behind it.

### Which flavours matter

- **Rule:** importance comes from the last 20 approvals. A dimension where the approved dishes sit consistently at one level matters more; one where they are scattered matters less.
- **Formula:** importance is the inverse of each dimension's variance (plus 0.01, so a perfectly consistent dimension can't take over), scaled to an average of 1 and clamped to 0.5–2.0.
- **When it starts:** after 3 approvals. Before that there's nothing to compare.
- **How it's used:** in the taste distance, each dimension is weighted by its importance, times 4 for a taste the query asks for.

This is the signal "this person cares about spice, not sweetness".

### How much health, budget and taste count

- **When:** only when the user approves a dish other than the top pick.
- **Rule:** each weight moves along the gap between the two dishes' scores on that term, by a step of 0.2 that halves by the tenth approval.
- **Example:** choosing a cheaper runner-up makes price count a little more.
- **Limits:** no weight falls below 0.05, and the weights always sum to 1.
- **Missing data:** a term that couldn't be assessed for either dish teaches nothing.

### What a pass teaches

Nothing. Passing on a dish can mean the price, the mood or what the person ate yesterday, so there is no reliable direction to learn. A pass only lowers that dish's rank for a week, through the decision core's novelty term.

## The safety rule

Learning changes the taste model only: taste, importance and weights. It never reads or writes the dietary profile. Allergies, diet and halal are set by the user and applied to every query by Tier 1, and no approval can loosen them. A test approves dishes and checks that the dietary profile is unchanged.

## The persona is a starting point

- **Guests** use the persona's taste and weights.
- **Signed-in users start from their persona too.** Their taste moves away from it one approval at a time, with the shrinking step, so the persona's influence fades as evidence grows.
- **Choosing a persona for one ranking** (the persona chips in `/recalculate`) overrides the learned weights for that ranking only. The sliders override everything.

## People with tastes like yours

Once a user's taste has evidence behind it, their taste vector is in the ChromaDB similar-tastes index (see `ACCOUNTS.md`).

- **Who counts as similar:** each query looks up to 10 other users with a cosine similarity of at least 0.9.
- **What they contribute:** the dishes those users approved in the last 30 days.
- **The pull:** a dish some of them approved moves toward a perfect score by up to 15% of the gap, reaching the full 15% at three approvals.
- **It is a pull, not an averaged-in term.** Averaging would lower a dish that already scores well. The pull can only raise a score, and never past 1.
- **It is anonymous.** The reason says "2 people with tastes like yours approved this recently" and never who.
- **With few users it rarely fires,** and nothing is invented to fill the gap.

## Something different

- **The rule:** the shortlist keeps its fifth place for a deliberate stretch. That's the best dish from a category none of the other four share, scoring at least 80% of the winner.
- **Labelling:** it is marked `exploration: true` and says so ("Something different: an afghan dish.").
- **If nothing qualifies,** the shortlist is the plain top five.
- **Why:** a concierge that only confirms its own model narrows into a filter bubble. The stretch is shown openly, never hidden.

## Seeing and undoing it

| Endpoint | Does |
|---|---|
| `GET /profile/learning` | What approvals have taught the model, in sentences |
| `GET /profile` | The model itself: taste, confidence, importance, weights, approvals learned from |
| `PUT /profile/taste` | Sets taste dimensions by hand |
| `PUT /profile/weights` | Sets health, budget and taste weights by hand; approvals keep refining them |
| `POST /profile/taste/reset` | Forgets everything learned and starts again from a persona |

Each recommendation's reasons also say when the taste they compare against was learned, for example "learned from 7 approvals".

## Storage

The model is stored on the user's `TasteModel` node and updated at each approval. Old events are trimmed to the newest 200 per account (see `ACCOUNTS.md`), which loses history but not learning. Importance is recomputed from whichever of the last 20 approvals are still on file.

## Tests

`tests/test_learning.py` covers the rules and the plan's exit criteria:
- A simulated user who keeps approving spicy dishes, whatever else the dish is like, moves spice from 0.4 to above 0.8 within ten approvals.
- Spice then becomes that user's most important dimension.
- With no craving in the query, a spicy dish now beats an otherwise identical mild one.

`tests/test_accounts.py` checks the API end to end:
- only shown dishes can be approved, and only once;
- the dietary profile never changes;
- learned weights move toward the runner-up's strengths;
- a guest's approvals are learned from at sign-up;
- the summary and reset work.

## Limits

- **This is a demonstrable mechanism, not a validated model.** One user approving a handful of dishes is a weak statistical signal. The rules are sensible and inspectable, but no user study has measured whether they improve recommendations.
- **Importance assumes low spread means it matters.** Someone indifferent to sweetness who happens to approve only savoury dishes will look like they care about low sweetness.
- **The runner-up signal is confounded.** An approval of the "something different" slot, or of a dish the novelty term pushed down, still nudges the weights.
- **Screens come with Phase 6.** Until then everything here is usable through the API and FastAPI's `/docs` page.

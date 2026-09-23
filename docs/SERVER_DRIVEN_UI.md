# Server-driven UI

The server decides what the Pick screen shows, in what order, and with what emphasis, from
what it knows about the user. The frontend draws the layout it is sent. Two users who get the
same dish can see two different screens, and each difference says why.

No language model writes the interface. The layout is composed by deterministic rules
(`ui/compose.py`), so the same recommendation and the same user always give the same layout,
it can be tested, and it adds no latency or LLM use (runtime LLM use stays intent extraction
only).

## How it flows

1. A new request (`/chat` with text) works out the user's **signals** once
   (`ui/signals.py`) and keeps them with the session as `ui_signals`.
2. Every recommendation reply (`/chat`) and every slider re-rank (`/recalculate`) composes a
   **layout** from the current recommendation and those signals, and sends it as
   `recommendation.layout` (`/chat`) or `layout` (`/recalculate`).
3. The frontend draws the blocks it is given. If `layout` is missing or `null`, or it names
   a block the frontend doesn't know, it draws the fixed Pick screen. A layout is never worth
   failing a recommendation over: a composition error is logged and sends `null`.

## Signals

| Signal | From | Explicit or learned |
|---|---|---|
| `persona`, `goal` | The profile or the persona the user chose | explicit |
| `dietary` | Saved allergies, diet and halal | explicit |
| `allergens`, `vegan`, `vegetarian`, `halal` | The request, with the saved rules merged in | explicit |
| `cheap_query` | The request asked for something cheap | explicit |
| `refinements` | How often each refinement was asked for (`refined` events) | learned |
| `approvals` | Dishes chosen before, and how often (`approved` events) | learned |
| `peers` | Dishes that users with a similar taste chose (cosine, ChromaDB) | learned |
| `learned_from` | How many approvals the taste model has learned from | learned |
| `queries` | Earlier requests (guests too, for this browser) | learned |

The slider weights are read from the recommendation itself, so moving a slider re-composes
the screen.

## The layout contract (version 1)

```json
{
  "version": 1,
  "screen": "pick",
  "blocks": [
    {"id": "safety", "type": "safety", "slot": "main", "variant": "default",
     "props": {"lines": ["No dishes with nuts — from your profile", "Halal only"]}},
    {"id": "match", "type": "match", "slot": "main", "variant": "default", "props": {}}
  ],
  "actions": {"refinements": ["more_filling", "cheaper", "..."], "lead": "more_filling"},
  "why": [
    {"text": "Protein is shown beside the price: your goal is building muscle.",
     "source": "profile", "block": "nutrition"}
  ]
}
```

- **`slot`**: `top` (above the card), `main` and `side` (the two columns on a wide screen,
  one column on a phone), `band` (full width under both). The server decides what goes where;
  the frontend decides how each slot looks at each width.
- **`variant`**: how a block is drawn. The server never sends colours, sizes or fonts.
- **`actions.refinements`**: every refinement, in order; `lead` is the one moved first.
- **`why`**: one line per adaptation, shown only when the user opens "Why the page looks like
  this". `source` is `profile`, `persona`, `query`, `weights` or `learned`.

### Blocks

| Block | Default slot | Variants and props |
|---|---|---|
| `notice` | top | `props.text`: the search had to widen. **Pinned** when present |
| `safety` | main | `props.lines`: the food rules applied. Never says a dish is "safe" |
| `match`, `name`, `place` | main | — |
| `price` | main | `headline` with `props.per_person` (null when it serves one) |
| `nutrition` | main | `protein` or `calories`; `props.protein_g`, `calories`, `confidence` |
| `summary` | main | — |
| `allergens` | main | `emphasised` when food rules apply. **Pinned**: always sent |
| `weights` | main | the sliders |
| `photo` | side | — |
| `reasons` | side | `props.order`: the reasons in the order the user weighs them |
| `history` | side | `props.lines`: chosen before, by the user or by similar tastes |
| `learning` | side | `new`, `tuned` or `guest`; `props.text` |
| `runners` | band | `props.badges`: `{dish_id: "Your usual" \| "Liked by similar tastes"}` |

## The rules, in order of precedence

Only one refinement can lead. The first rule to choose one wins.

1. **Notice.** Shown only when the search widened.
2. **Food rules.** Any allergy, diet or halal rule puts a `safety` block first in the card and
   emphasises the allergen line.
3. **Habit.** A refinement asked for at least 3 times, and in at least 40% of all
   refinements, leads.
4. **Goal.** Building muscle shows protein beside the price and leads with "More filling";
   losing weight or eating light shows calories and leads with "Lighter". The persona is
   used when the profile sets no goal. The block is left out when the number isn't known.
5. **Budget.** The frugal persona, a request for something cheap, or a budget weight of at
   least 0.45 that is also the highest makes the price the headline (per person where the dish
   serves more than one) and leads with "Cheaper".
6. **Exploring.** The adventurous persona leads with "Something different".
7. **Reasons.** Listed in the order of the weights, rounded to one decimal so near-even weights
   keep the usual order. Distance stays last.
8. **History.** On the winner: how often the user chose it, and how many similar users did.
   Among the runners: "Your usual" (chosen twice or more) and "Liked by similar tastes".
9. **Learning.** Signed in: "Still learning you" or "Tuned by N of your choices". A returning
   guest: an invitation to sign in. Nothing on a guest's first request.

## Guarantees, and where they are tested

`tests/test_ui_compose.py`:

- With nothing known, the layout is exactly today's Pick screen.
- The allergen line can't be removed by any rule, and the safety block never claims a dish is safe.
- The same dish is composed differently for different users.
- Every layout is well formed: unique blocks, known slots, every refinement present, every
  adaptation explained.
- A composition error gives `null`, and the fixed screen is drawn.

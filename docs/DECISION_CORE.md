# Decision Core

Phase 3 replaced every scoring function in Tier 2. The tier boundary is unchanged:
- **Tier 1** removes every dish that breaks a hard constraint.
- **Tier 2** ranks what is left and never adds a dish.

What changed is how Tier 2 ranks, and how Tier 1 reads a request. The code is in `tier_2/scoring.py` (terms, aggregation, reasons), `tier_2/context.py` (hour, weather, recent history) and `tier_2/consensus_manager.py` (ranking and the blueprint). Every number below is a named constant in `tier_2/scoring.py`.

## What was removed

Each of these forced a result instead of explaining one:

- **The `u_taste = 2.0` override** for dishes whose name matched a word in the query, and its dairy, meat and seafood synonym lists.
- **The `u_total = 1000.0` override** in `/recalculate`, which had its own separate copy of the scoring.
- **Taste-weight boosts** for a dominant mood or a direct craving.
- **Budget-weight "relaxation rounds"** that ran when every score was zero.
- **A hidden 1,000 kcal cap** in Tier 1's query. The user never asked for it.
- **`LocalVectorStore`**, a JSON-file stand-in for ChromaDB that was never populated.

## Tier 1: reading a request

**A requested category, dish or food group** (`requested_match`):
- A cuisine request (afghan, chinese, desi, fast food and the other categories) matches the dish's category only. An "Afghan Burger" at a burger shop is not Afghan food.
- A dish request ("biryani", "salad") matches dish names.
- A dish the query names narrows the pool to dishes with that name (`narrow_to_named_dish`), even when the extractor filed the request under something broader. "Spicy chicken karahi" came back as the food group "chicken", and a Thai dumpling bowl won. Negated dishes ("anything but pizza") don't count. When no dish has the name, the pool is left as it was and the relaxation says so.
- A food group or ingredient request matches dishes containing it: "seafood" means fish, prawns, crab, lobster or squid, and "chicken" means chicken.
- An allergen group ("dairy") matches by allergen.
- If fewer than 3 dishes match, the request is relaxed as before, and the notice says so.

**An exclusion** (`exclusion_terms`):
- A food word becomes the allergen tag that covers it: "no bread" becomes gluten, "no cheese" dairy.
- A group becomes every ingredient in it: "no meat" removes chicken, beef, mutton and the rest.
- This only ever excludes more than was meant, never less.
- The older name-keyword safety net is still in place underneath.

**The keyword extractor** (the fallback when Groq is unavailable) now also:
- reads "no bread / naan / roti / pasta" as excluding gluten;
- turns the first cuisine or dish named, and not negated, into the request.

## Tier 2: the terms

Every term returns a utility (0–1), a confidence (0–1) and a sentence.

| Term | What it measures | Confidence comes from |
|---|---|---|
| Taste | Weighted distance between the dish's six taste values and what the user wants | The dish's `taste_source` (original 1.0 … global prior 0.25) |
| Budget | Price against a target band | The dish's `price_status` (trusted 1.0, verified 0.9, unverified 0.6) |
| Health | A goal-specific nutrition score | The dish's `nutrition_confidence` (high 1.0, medium 0.7, low 0.4, none 0) |
| Context | Meal fit, time of day, weather | 1.0 when a rule applies; otherwise the term is left out |
| Novelty | A multiplier for dishes recommended or passed over in the last 7 days | — |

Dishes no person reviewed (`review_status = auto_imported`) have their taste and health confidence multiplied by 0.85. Their names and prices came straight from OCR.

### Taste

```
u_taste = 1 − Σ_d w_d · |dish_d − want_d| / Σ_d w_d
```

- **What the user wants:** for a taste the query asks for ("something sweet"), the query's value; for every other dimension, the user's usual taste. That is the learned taste once it has evidence, otherwise the persona's.
- **Weights:** each dimension counts by its learned importance (1 until the user has approved at least three dishes; see `LEARNING.md`). A dimension the query asks for counts 4 times that (`CRAVING_IMPORTANCE`).
- **Why not cosine:** cosine similarity scored an intensely sweet dessert and a barely sweet side identically (0.9234). This measure separates them.
- **The sentence names what was asked for and how strong the dish is,** for example "You asked for sweet; this is strongly sweet."

### Budget

- **A ceiling in the query ("under 1,000"):**
  - the dish scores 1 within 40–100% of the ceiling;
  - below that it falls gently to 0.6 (`CHEAP_FLOOR`): cheaper is fine, just further from what was asked;
  - the ceiling itself is a Tier 1 filter, never a score.
- **A usual spend in the profile:**
  - the dish scores 1 within 70–120% of it;
  - dearer dishes fall to 0 at double the band's top.
- **No budget at all:**
  - anything up to a typical option's price (the median of the current options) scores 1, so a Rs 30 side gains nothing from being cheap;
  - dearer dishes fall to 0 at the dearest 5%;
  - price counts at half confidence (`NO_BUDGET_CONFIDENCE`).
- **The Frugal Student persona:** cheaper always ranks higher, by the dish's rank in price among the options.
- **Shared dishes:** the cost is divided by the number of people sharing, capped at the dish's servings. The party size is 1 until Phase 5 asks for it.

### Health

The goal comes from the profile, or from the persona: Gym Bro means muscle gain, Health Nut means light, and everyone else balanced.

| Goal | Utility |
|---|---|
| Muscle gain | 75% protein density (8 g per 100 kcal scores full), 25% a 400–900 kcal serving |
| Weight loss | 70% calories (full at 450 kcal or less, 0 at 900), 30% protein density (6 g per 100 kcal scores full) |
| Light | 60% calories (full at 400 kcal or less, 0 at 800), 40% share of energy from fat (full at 30% or less) |
| Balanced | 80% how close protein, carbohydrate and fat are to the Acceptable Macronutrient Distribution Ranges (10–35%, 45–65%, 20–35% of energy), 20% a 300–900 kcal serving |

- **Estimates are worded as estimates.** Every sentence says "About…", because all nutrition here is estimated, and the app says so beside the numbers.
- **The main problem is named.** In the balanced goal, a macro over its range is named before one under it. A karahi with 70% of its energy from fat and 3% from carbs is "heavy on fat", not "light on carbs" (which it said before, from a tie).
- **A Double for one counts in full.** One person ordering a Double eats both servings (the owner's rule), so health scores the calories and macros of both, and says so. For a party of two or more, each person eats one. Other dishes that serve several are shared, one serving each.
- **Implausible estimates count half.** A dish whose estimate failed the Phase 1 plausibility check has its health confidence halved.

### Context

Context usually has weight 0.1. When the query names a meal it has 0.3, because what the query says outweighs what the clock suggests.

- **Meal fit:** unless the query asks for something sweet, a dessert, a cake, coffee or a snack, a café or bakery item fits at 0.6 and a main dish at 1.
  - This is only said out loud when the dish doesn't fit, or when the query named the meal.
  - "Breakfast" or "brunch" in the query, or the hours 6–11 when no meal is named, favour breakfast dishes instead.
- **Late night (23:00–04:00):** fast food, pizza and sandwiches fit best.
- **Weather** (Open-Meteo, Islamabad, cached 30 minutes):
  - at 32°C or more, lighter dishes (550 kcal or less, or a salad);
  - at 12°C or less, soups and desi or Afghan dishes.

### Novelty

A dish multiplies its total by:
- 0.7 if the user passed on it in the last week;
- 0.8 if it was recommended in the last 3 days;
- 0.9 if it was recommended in the last 7.

History comes from the account (Phase 2), or from the guest's session.

### People with tastes like yours

For a signed-in user whose taste has evidence behind it, dishes that users with a similar taste approved in the last 30 days move toward a perfect score. The pull is up to 15% of the gap (`PEER_PULL`), reaching the full 15% at three approvals. It is applied after novelty, so it can only raise a score and never past 1. The similar users come from the ChromaDB index (cosine similarity of at least 0.9), and the reason is anonymous. See `LEARNING.md`.

## Aggregation

```
u_total = Σ_t w_t · (c_t · u_t + (1 − c_t) · 0.5) / Σ_t w_t      × novelty
```

- **Each term counts in proportion to its confidence.** The rest of its weight counts as a neutral 0.5 (`NEUTRAL_UTILITY`).
- **Missing data is neither a zero nor a free pass:**
  - A dish with no nutrition estimate is no longer eliminated for a health-first user, as it was when missing macros scored 0.
  - It also can't beat dishes whose nutrition we know is good, as it could when unknown terms were simply dropped.
- **The explanation says so:** "Its health couldn't be assessed, so it counts as average there." The UI shows the term as "Not assessed" rather than 0%.
- **Weights:** health, budget and taste come from the first of these that exists, normalised to sum to 1:
  1. the sliders;
  2. a persona picked for this ranking;
  3. the user's learned weights;
  4. the persona's weights.

  Context adds 0.1 or 0.3.

## Shortlist

The blueprint's `top_candidates` is the best five, with one exception. The fifth place goes to a deliberate stretch when there is one: the best dish from a category none of the other four share, scoring at least 80% of the winner. It is marked `exploration: true` and labelled "Something different". See `LEARNING.md`.

## Explanations

The traces keep the shape the current frontend reads: the winner's "Candidate Breakdown" line, then Health, Budget and Taste lines. Context, coverage and novelty lines follow them. The winning dish and every runner-up also carry a `reasons` map and a per-term `confidence`, for the "How it scored" screen.

Each dish also carries a `summary`: its reasons in one short paragraph, for the recommendation screen.
- It names up to two points in the dish's favour: terms scoring at least 0.7, the two that count most, told in the order taste, budget, health.
- Then its most serious caveat: the weakest term below 0.5.
- A term is mentioned only when its confidence is at least 0.5, so the summary never repeats a guess.
- For the karahi: "It's properly spicy, as you asked, and comes in Rs 100 under your limit. It's also rich, at around 890 kcal and mostly fat."

The sentences read as plain speech: no semicolons, and no chains of colons.

Each dish also carries its restaurant (`restaurant_name`, `restaurant_area`, `location_precision`) and, when the request sent a location, `distance_km`. See `PHASE1_DATA_DECISIONS.md` (Locations).

## Golden set

`python -m scripts.golden_set --label <name> --compare baseline` runs 22 realistic queries against the real dataset and checks each winner using its own Neo4j record:
- **Safety** (34 checks): budget, allergens, vegan, vegetarian, halal, not quarantined.
- **Relevance** (27 checks), where the query asks for something specific.

Intents are written the way the extractor produces them, so extraction quality doesn't move the result.

| | Safety | Relevance |
|---|---|---|
| Before Phase 3 | 34 / 34 | 22 / 27 |
| After Phase 3 | 34 / 34 | 27 / 27 |

The five that now pass:

| Query | Before | After |
|---|---|---|
| "something sweet" | Badashahi Kheer (sweetness below 0.6) | Baked Cheese Cake |
| "spicy desi food under 1000" | Chicken Tikka (spice below 0.6) | Arabian Spicy Rice With Tikka Sajji |
| "a heavy protein meal for the gym" (Gym Bro) | Fish Crackers | Chicken With Jalapeno Cheese Sauce |
| "vegetarian dinner under 1500" | a café item named "Vegetarian" | Pide With Cheese |
| "filling but low calorie" (Health Nut, weight loss) | Mediterranean Black Cod, Rs 12,999, over 600 kcal | Big Zing, 600 kcal or less |

The checks are the project's own judgement of a sensible winner, not a user study. Re-run the golden set after every data rebuild; results were recorded while 580 dishes still awaited the automated category pass.

## Known limitations

- **Data errors still decide some rankings.**
  - "Hot Gulab Jamun" carries a spice value of 0.6, because "hot" means served warm.
  - One restaurant's "Fresh Lime" and "Black Olives" still sit in meal categories from the old handoff data.
  - The remaining automated pass will fix some of these; nothing in scoring can.
- **The nutrition method's 15% fat share keeps oily dishes high,** and some soups and salads come out over 600 kcal (see `PHASE1_DATA_DECISIONS.md`).
- **The context rules are heuristics.** Their weight is deliberately small, and each one explains itself when it matters.
- **Learned importance, weights and similar-taste pulls start from nothing.** With few approvals and few users they barely move a ranking. See `LEARNING.md`.
- **Party size is always 1** until Phase 5's conversation asks.
- **The current UI shows only the health, budget and taste sentences.** The context, coverage and novelty reasons reach the blueprint but aren't rendered until Phase 6.

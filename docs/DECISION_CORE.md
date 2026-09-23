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
| Distance | How far the restaurant is from the location the user sent | 1.0 for the restaurant's own coordinates, 0.7 for its sector's centre; left out without a location |
| Novelty | A multiplier for dishes recommended or passed over in the last 7 days | — |

Dishes no person reviewed (`review_status = auto_imported`) have their taste and health confidence multiplied by 0.85. Their names and prices came straight from OCR.

### Taste

```
u_taste = 1 − Σ_d w_d · |dish_d − want_d| / Σ_d w_d
```

- **What the user wants:** for a taste the query asks for ("something sweet"), the query's value; for every other dimension, the user's usual taste. That is the taste learned from approvals or set by hand.
- **No known taste, no craving: taste doesn't apply (2026-09-21).**
  - Before, a guest's dishes were scored against the persona's made-up profile and described as "your usual taste".
  - The dish tastes it compared with are largely templates: 1,139 "original" values share 72 profiles, and 378 dishes are exactly "umami 0.6, the rest 0".
  - Across 1,850 candidates the taste score's spread was 0.06, against 0.30 for health. At taste 100% it picked whichever dish sat nearest the stereotype: an Afghan tikka burger.
  - Now the term is left out, like distance without a location. The sliders show taste as off, with a line saying what would turn it on.
  - With a craving but no known taste, only the craved dimensions count.
- **Weights:** each dimension counts by its learned importance (1 until the user has approved at least three dishes; see `LEARNING.md`). A dimension the query asks for counts 4 times that (`CRAVING_IMPORTANCE`).
- **Why not cosine:** cosine similarity scored an intensely sweet dessert and a barely sweet side identically (0.9234). This measure separates them.
- **A dish's taste is an estimate, and counts as one (2026-09-21).** "Original" means the value arrived with the source data, which generated it; 1,139 dishes share 72 profiles. Its confidence is 0.8, the same as the keyword estimate, not the 1.0 that would say someone tasted the dish.
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
- **"Cheap" without a figure** ("cheap eats", "affordable", "sasta") sets no ceiling. The
  extraction prompt used to teach the model `"cheap eats" -> Rs 300`, and a ceiling is a hard
  filter: it cut 1,859 recommendable dishes to 48, which is why one Rs 220 burger (the only dish
  under Rs 300 in I-8, its price never verified) kept winning. Now the word raises the budget
  weight to 0.6 (`CHEAP_WORDS`, `CHEAP_BUDGET_WEIGHT`), so cheap dishes rank higher from the full
  pool. A budget reaches the filter only when the text contains a number; the extractor drops any
  other, whatever the model returns. Weights the user sets on the sliders still overrule it.
  - The word also makes cheaper better, as for the Frugal Student persona, with price counting
    in full (2026-09-21). It had been scored like no budget at all: price at half confidence,
    and every dish up to the median price scoring 1. Once health could tell dishes apart, a Rs 720
    soup beat a Rs 150 pogaca for "something cheap". A rupee figure still sets a band instead.

## What the words say that the fields can't carry

`GroundedIntent` has nine fields, so everything else a person says was dropped in silence until
the 2026-09-21 word sweep. Rather than widen the schema and the prompt for each one, the words
are read by rule in `tier_1/query_words.py`, after extraction, so the Groq extractor and the
keyword fallback get the same reading. Every rule only ever adds what the user asked for.

| The words | What happens | Where |
|---|---|---|
| "no onion", "hold the mayo", "without garlic" | The ingredient is excluded, as a hard filter | `dislikes` |
| "pescatarian" | Land meat is excluded; fish and prawns stay | `excluded_foods` |
| "grilled", "bbq", "nothing fried" | The pool narrows to dishes named that way, and fried ones drop out | Tier 1 |
| "fried", "crispy" | The pool narrows to fried dishes | Tier 1 |
| "in F-7", "in Blue Area" | The area sets the location for this request, so distance counts | `area_asked` |
| "near me", with no area chosen | Says so: the app can't know where you are | `asks_for_nearby` |
| "healthy", "high protein", "low calorie", "light", "keto", "sugar free" | Lean the weights and set how health is judged | `HEALTH_WORDS`, `GOAL_WORDS` |
| "fancy", "premium", "expensive", "a treat" | Price counts for little (0.15): the opposite of "cheap" | `PRICEY_WORDS` |
| "rice", "noodles", "traditional" | A request the fallback used to drop | keyword extractor |
| "something with dairy", "with cheese" | The food asked for, when the extractor named no category. Groq returns none for "something with dairy", so any dish could win it | `wanted_food` |
| "popular", "quick", "delivery", "open now", "date night", "cold" | **Said, not ignored:** "I can't sort dishes by how popular they are, so I've gone on the rest of your request." | `unsupported` |

The last row is the point of the exercise: a request the app has no data for now gets an answer
that says so, in the same notice that already explains a widened search.

**Health words** (`HEALTH_WORDS`, `GOAL_WORDS`, 2026-09-21).
- "Healthy" leans the weights to health 0.6, as "cheap" leans them to budget; both at once share 0.8.
- A nutrition goal named in the request sets how health is judged, over any saved goal, for that request only:
  - "high protein" → muscle gain;
  - "low calorie" → weight loss;
  - "light" or "low fat" → light.
- The word sweep found every one of these ignored: neither extractor has a field for them.

**Asked for an ingredient, a dish that names it** (Tier 1, `prefer_named_ingredient`).
"Something with chicken" matched a mushroom soup whose ingredient list had chicken (the stock),
and "spicy chicken karahi" (filed under "karahi") matched a seekh kebab karahi. The meat or
seafood a query's words ask for, not negated, and the requested food group now narrow the pool
to dishes that name it, after any named-dish narrowing. This only applies when at least five
dishes name it; with fewer, the pool is left alone.
- **The budget slider:** a band is flat — every dish under the median ties on it — so raising the
  budget weight against a flat term changed nothing, which is what made the sliders feel dead. As
  the weight rises past the even third, the score mixes smoothly from the band into the persona's
  rank-by-price, reaching it fully at 100%. Past halfway the explanation switches with it, from
  "no pricier than a typical option here" to "cheaper than 80% of the options". Measured on a
  393-dish pool: moving the slider from 33 to 66 took the pick from a Rs 2,789 fajita to a Rs 355
  tikka leg, where before it did not move at all.
- **Shared dishes:** the cost is divided by the number of people sharing, capped at the dish's servings. The party size is 1 until Phase 5 asks for it.

### Health

The goal comes from the profile, or from the persona: Gym Bro means muscle gain, Health Nut means light, and everyone else balanced.

| Goal | Utility |
|---|---|
| Muscle gain | 75% protein density (8 g per 100 kcal scores full), 25% a 400–900 kcal serving |
| Weight loss | 70% calories (full at 450 kcal or less, 0 at 900), 30% protein density (6 g per 100 kcal scores full) |
| Light | 60% calories (full at 400 kcal or less, 0 at 800), 40% share of energy from fat (full at 30% or less) |
| Balanced | 80% how close protein, carbohydrate and fat are to the Acceptable Macronutrient Distribution Ranges (10–35%, 45–65%, 20–35% of energy), 20% a 300–900 kcal serving |
| Low carb | 60% carbohydrate share (full at 25% of energy or less, none at 50%), 40% protein density. Asked for by "keto", "low carb", "sugar free" or "diabetic" |

- **The balanced split (revised 2026-09-21).**
  - A macro loses its credit over 15 percentage points outside its range (20 before).
  - A macro *over* its range counts for half on its own. Too much fat can no longer hide behind two macros in range, which had let a kulfi 44% fat score 0.81 while its sentence said "Heavy on fat" (now 0.62).
  - Too little of a macro is only averaged: a low-carb karahi isn't an unhealthy dish.
- **Sugar isn't known, so a sugary dish's health counts for less (half its confidence).**
  - A dish is sugary when its taste is clearly sweet (0.6 or more), or when it is a sweet or bake whose ingredients include sugar, honey, syrup, chocolate, condensed milk or ice cream.
  - Many desserts carry only their restaurant's average taste, so taste alone missed them.
  - A savoury dish's sweetener is a dressing or marinade, and doesn't count.
  - The rule is skipped when the user asked for something sweet, because then the sugar is the point.
  - The reason says so: "It's sweetened, and its sugar isn't known, so this counts for less."
- **Measured on the golden set.** Safety stayed at 36/36 and relevance at 29/29. Five winners changed, all still passing:
  - "something sweet": Sütlac → Baked Cheese Cake;
  - "cake": Biscoff → Baked Cheese Cake;
  - "seafood": Fish Garlic Sauce → Spicy Thai Mixed Seafood Soup;
  - the nut-allergic Chinese request: Crispy Honey Chicken → Duck Roast;
  - "filling but low calorie": Burrito → Indonesian Thick Ramen, from the filling rule.
  - The first attempt counted any sweetener in the ingredients. It sent "gluten free please" to a dessert, because Tangy Chicken Salad lists sugar for its dressing, and was narrowed to sweets and bakes.

- **Estimates are worded as estimates.** Every sentence says "About…", because all nutrition here is estimated, and the app says so beside the numbers.
- **The main problem is named.** In the balanced goal, a macro over its range is named before one under it. A karahi with 70% of its energy from fat and 3% from carbs is "heavy on fat", not "light on carbs" (which it said before, from a tie).
- **A Double for one counts in full.** One person ordering a Double eats both servings (the owner's rule), so health scores the calories and macros of both, and says so. For a party of two or more, each person eats one. Other dishes that serve several are shared, one serving each.
- **Implausible estimates count half.** A dish whose estimate failed the Phase 1 plausibility check has its health confidence halved.

### Context

Context usually has weight 0.1. When the query names a meal, or asks for something filling, it has 0.3, because what the query says outweighs what the clock suggests.

- **Filling** ("filling", "hearty", "hungry", "starving", "pet bhar"). Neither extractor has a field for it, so like "cheap" it is read from the words.
  - The fit is 60% energy (full credit from 550 kcal, none at 200 kcal) and 40% protein (full credit at 20 g).
  - Before this, "something cheap but filling" lost the word "filling" entirely. After "Cheaper" and the health slider at 70%, a 267 kcal kulfi won because it was the least fat-heavy of six fried options.

- **Meal fit:** unless the query asks for something sweet, a dessert, a cake, coffee or a snack, a café or bakery item fits at 0.6 and a main dish at 1.
  - This is only said out loud when the dish doesn't fit, or when the query named the meal.
  - "Breakfast" or "brunch" in the query, or the hours 6–11 when no meal is named, favour breakfast dishes instead.
- **Late night (23:00–04:00):** fast food, pizza and sandwiches fit best.
- **Weather** (Open-Meteo, Islamabad, cached 30 minutes):
  - at 32°C or more, lighter dishes (550 kcal or less, or a salad);
  - at 12°C or less, soups and desi or Afghan dishes.

### Distance

Distance has weight 0.15 (`DISTANCE_WEIGHT`), beside health, budget and taste, which sum to 1. It is kept small deliberately: `api/location.py` already drops restaurants beyond 10 km when closer ones match, so the term only separates the ones that survived. Nearly every remaining restaurant scores about 1 on it, so a larger weight would add a constant to every dish and mute the three weights the user controls. It scores 1 up to 3 km and falls linearly to 0 at 12 km. Most of the dataset's restaurants are within 8 km of G-9; Bahria Town, DHA and Rawat are 18–27 km out. A dish more than 7.5 km away (a distance score under 0.5) names it as a caveat in its summary: "It's also 22 km away."

Before ranking, restaurants more than 10 km away are left out when anything closer matches (`api/location.py`, `nearby`). When nothing does, every match stays: a far match beats none. A restaurant with no known coordinates is never left out for distance.

Distance used to be shown but never scored, so a dish 22 km away could win outright.

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

  Context adds 0.1 or 0.3, and distance 0.15 when the request sent a location.

- **Ties** are broken by the other terms, then by name. A term the weights have turned off
  saturates — with budget alone, every dish inside the limit scores the same — and breaking those
  ties alphabetically clustered one restaurant's dishes at the top.

## Re-ranking with the sliders

`POST /recalculate` re-ranks the pool the query found under new weights, **after** applying what
the conversation narrowed it to: a cuisine answered, "Cheaper", "Healthier". It used to re-rank
the whole pool, so moving a slider silently discarded the answers — choose Desi, move a slider,
get a fast-food burger.

## Shortlist

Only the best size of a dish appears: "Chicken Fajita (Medium)" and "(Large)" from one restaurant
are one entry, and the other sizes are still reachable through "Next". A shortlist that reads as the
same dish three times looks like a system with nothing to say.

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
| 2026-09-21, 23 queries, before the day's changes | 36 / 36 | 29 / 29 |
| 2026-09-21, after the health, filling, cheap, named-ingredient and calibrated-nutrition changes | 36 / 36 | 29 / 29 |

Across the 2026-09-21 changes, 16 of the 23 winners moved and all still pass. Examples:
- "something with chicken": Pide With Chicken & Cheese → Grilled Chicken Sandwich;
- "something sweet": Sütlac → Biscoff Cheese Cake;
- "sour": Coconut Nouc Cham Dumpling Bowl → Tangy Chicken Salad.

The per-run files are in `data/golden/`.

**Plausibility (added 2026-09-21).**
- Every winner is also checked for believable data: a meal rather than a side or drink; 100–2,000 kcal (40–450 for a soup, 40 and up for a salad); under 75% of energy from fat; calories that agree with the macros.
- A line under the table counts the dataset's recommendable dishes that break the same bounds, with the median fat share.
- Safety and relevance had passed for months while the median dish got 68% of its energy from fat. This line would have shown it on the first run.
- After the audit: plausibility 92 / 92. Dataset median fat share 48%; 10 dishes over 75% (oil-dressed salads, palak paneer); 2 with unbelievable calories.

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
- **Nutrition is estimated, not measured.** The split of a serving and a soup's broth share are now calibrated against dishes USDA measured whole (`PHASE1_DATA_DECISIONS.md`). One fat share still covers every cooking method, and the automated pass's ingredient lists decide a lot.
- **The context rules are heuristics.** Their weight is deliberately small, and each one explains itself when it matters.
- **Balanced health judges the macro split, not sugar or portion.**
  - Sugar is only inferred: from a sweet taste, or a sweetener among a sweet's ingredients. It lowers trust in the estimate, not the score.
  - A dessert whose ingredients miss the sugar, and whose taste is a restaurant average, isn't caught.
  - With health weighted high and no word about a meal, a small, fairly balanced dessert can still beat a fried main.
- **Learned importance, weights and similar-taste pulls start from nothing.** With few approvals and few users they barely move a ranking. See `LEARNING.md`.
- **Party size** comes from the conversation's question, or from the request's own words ("for 4 people", "the two of us"). In the second case the question isn't asked.
- **Words still ignored, after the sweep's fixes:** "something new" (novelty only counts against the last week's history), "the best" (too vague to act on), and "family dinner" as a party size (how many is a family?). "Lunch" and "late night" count in the context term, which is small by design.
- **The current UI shows only the health, budget and taste sentences.** The context, coverage and novelty reasons reach the blueprint but aren't rendered until Phase 6.

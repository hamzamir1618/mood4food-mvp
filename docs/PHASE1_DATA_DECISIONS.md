# Phase 1 Data Decisions

Recorded on 2026-09-14. This covers what the project owner decided for the Phase 1 data rebuild, what the build does about each decision, and what the build found along the way. Current figures are in `data/build_report.md`, which every build regenerates. How to run the pipeline is in `DATA_PIPELINE.md`.

## Decisions

| Topic | Decision | What the build does |
|---|---|---|
| Upstream data | The sourcing project (`../Data-Scraper/mood4food-data-sourcing`) is available. | Reads its review flags, OCR evidence, menu descriptions and photo links. `data/master_menu.csv` joins 1:1 with the handoff CSV on restaurant plus dish name. |
| Re-seed | A destructive re-seed of the local Neo4j database is fine. | `python seed_real_data.py --reset` |
| Unconfirmed rows | Keep all 1,150 `human_confirmed=False` rows. They were auto-imported, not rejected (see `DIAGNOSTIC_HISTORY.md`). | Tagged `review_status = auto_imported`. Kept; scored with lower confidence in Phase 3. |
| Serving sizes | The owner fills in servings and included items for platters and combos in `data_review/platter_combo_review.xlsx`. Half and full portions are optional. Filled in on 2026-09-14: 19 platters got an item list, and none got a serving count. | Blank serving counts fall back to a count stated on the menu, then to a price-based guess. Both are recorded as estimates (`serves_source`). An item list is read for ingredients and counts as the whole dish. |
| Removed platters | The owner typed `remove` for 19 platters and combos (2026-09-14): all 10 Habibi Restaurant deals, 6 at Zaviya Fine Dine, 2 at Bar B Q Tonight and Wrap Lab, and Najeeb Spot's "Deal". | Quarantined with the reason "owner removed the dish". `remove` in any answer cell counts, and the word is never read as an item list. |
| OCR-damaged names | The owner marks keep, fix or discard in `ocr_damage_review.xlsx` and the later batch files (`ocr_damage_review_batch2.xlsx`, …). On 2026-09-14 the owner discarded every row of the first two worksheets: 191 names. | `discard` means quarantined: excluded from recommendations, kept on file, never deleted. The rows in both worksheets now read `discard`. |
| Category | Classified per dish, automatically. Restaurant-level cuisine was rejected because restaurants serve several cuisines. New category: `afghan`. | `category_source` records how each category was set. `afghan` still needs a design-system accent colour and typeface (Phase 6). |
| Human review | The owner reviews only the worksheets. No human price check, nutrition spot-check or per-dish category review. | Replaced by the automated methods below. |
| Images | Labelled stock images are acceptable. | Already in place (Phase 0 label fix). |
| Halal | `is_halal` is a first-class Tier 1 filter. It means "no pork or alcohol named", not certification. Confirmed by the owner on 2026-09-14: Terrazza's bacon is turkey, and Sakura and Umai use halal mirin substitutes. | Wired through both intent extractors to the Neo4j query. |
| Nutrition fields | Protein and calories, plus carbs and fat. No sodium, sugar or fibre. | All four stored per dish. |
| Dataset publication | Keep the dataset out of the public repository. | `handoff_output/`, `data/` and `data_review/` are git-ignored. See `ATTRIBUTIONS.md`. |
| Spice level (#8), deadline (#11) | Dropped for now. | — |

## How the automated methods work

### Category and typical ingredients

One Groq pass over every dish (`pipeline/classify_categories.py`) returns a category, a damaged-name flag, and the dish's typical ingredients from a fixed vocabulary of 126 ingredients. Answers are cached per dish, and the prompt version is recorded with each one.

It runs at low reasoning effort. On a 30-dish comparison, low reasoning agreed with default reasoning on 28 categories and used roughly 40% fewer tokens.

Validation without human review:
- the build report gives agreement with the old category;
- the largest groups of changes were spot-checked. The old category was often the restaurant's cuisine rather than the dish's, so a burger at a desi restaurant had been filed as desi.

Two definitions worth knowing:
- Desserts of every cuisine are `cafe_bakery`, because the sweet-craving filter depends on it.
- Plain bread or rice ordered as a side is `add_ons`, and so is never recommended.
  - The automated pass filed ten plain breads as meals (Sada Nan, Kalonji Naan, Makkai Roti). As meals they got a 400 g serving and ~1,100 kcal. A dish whose name is a bread's, names no filling, and holds only dough, fat and a topping is now `add_ons` (`plain_bread` in `pipeline/build_dataset.py`). Aloo paratha, cheese naan, halwa puri and puri chanay stay meals.
  - For nutrition, a prepared bread is not counted again as wheat flour or generic bread.

### Ingredients, allergens and diet flags

- A dish's ingredients are the ones named in its name or description, plus the typical ingredients from the pass. The vocabulary includes Urdu spellings and dish names that imply an ingredient: *shakshuka* → egg, *kheer* → milk and rice, cakes and pancakes → egg and flour.
- **Named detection is authoritative.** The model's lists can miss allergens: it left egg out of shakshuka even when the prompt gave that exact example. Allergen data is therefore still an estimate, and the app should say so.
- An owner's item list adds its ingredients to the platter. An item that is also on the same restaurant's menu brings that dish's ingredients with it: *Philadelphia Maki* names no fish, but Umai's own menu entry for it does. The list counts as the whole dish, and so can support a vegetarian claim, only when every item on it was recognised. Without these two rules, Umai's Zen and Hanami sushi platters were marked vegetarian. The vocabulary also covers platter terms: *malai*, *tandoori*, *tikka* and *patakha boti*, *reshmi kabab* and *sajji* → chicken; *maki*, *nigiri* and *sushi* → rice; *sashimi*, *nigiri*, *toro* and *sake* → fish. *Chapli kebab* is left out, because it comes in beef, chicken and mutton here.
- A name that means a fried coating adds wheat flour: *nuggets*, *broast*, *zinger*, *strips*, *crispy*, *katsu*, *cordon bleu*, *fried chicken/fish*, *fish & chips*, *mozzarella sticks* and similar, or *breaded*, *crumbed* or *battered* in the description. Menus rarely list the batter and the pass often left it out, so 31 recommendable dishes read as gluten-free, and Mozzarella Sticks won the gluten-free query in the golden set. The rule only adds an allergen. It skips dishes that already carry gluten, dishes that name gram flour (pakoras), and dishes with no known ingredients, which stay unknown. The flour counts for allergens and exclusions but not for nutrition, because breading is a small share of a serving and would otherwise displace the protein. *Lady finger* (okra) and *finger chips* (fries) are excluded. *Breadcrumbs* and *panko* map to wheat flour.
- Pork and alcohol count only when the dish itself names them. Suggestions from the pass are ignored, and the build report lists them.
- A dish is vegan or vegetarian only when the whole dish was assessed, meaning the pass answered or the owner listed what it includes.
- A dish with no ingredients has unknown allergens and is excluded for anyone who declares an allergy.

### Nutrition

- USDA SR Legacy values for every ingredient (`data/reference/ingredient_nutrition.csv`, with the FDC id on each row) replace the sourcing project's Open Food Facts matches. For 43 of 82 ingredients those matches were a different food.
- The apportioning method is the same (a category serving weight split 50% bulk, 15% fat, 15% vegetables), with three fixes:
  - no estimate for a dish without ingredients;
  - vegetable dishes are not padded with flour;
  - desserts and drinks get no onion default.
- `nutrition_confidence` is `high`, `medium`, `low` or `none`. Estimates are also flagged when they fail an energy-consistency check or exceed 2,500 kcal.
- Known limitation: the method's 15% fat share (for example 60 g of oil or butter in a 400 g curry) keeps oily dishes high. Revisit it in Phase 3 if health scoring needs finer resolution.

### Price check

- **Trusted:** human-confirmed, scraped or manually entered.
- **Verified:** the price appears in the dish's OCR evidence, reading "3.699" as 3,699 and a trailing "7" as the menu's "/-".
- **Unverified:** kept, and shown as unverified.
- **Quarantined as a gross error:** under Rs 20, or over 8× the restaurant's median with no size or serving word.
- Urdu and Arabic digits in OCR lines are never read as prices.

### Servings

The order of precedence is owner → menu → "Double" in the name (two servings, the owner's rule of 2026-09-15; before it, Burrito (Double) carried single-burrito calories per person and won the weight-loss query) → price-based estimate (platters, combos and half/full portions only) → default of one. `price_per_person` uses the middle of the range. Tier 1's budget filter uses the menu price. Phase 3's budget term divides the price by the number of people sharing (the party size, capped at the dish's servings); the party size itself is 1 until Phase 5's conversation asks for it. See `DECISION_CORE.md`.

### Taste: spice stated in the name

The source's taste values sometimes contradict the dish's own name: "Chicken Pepperoni (Non Spicy)" was recorded at spice 0.8, and several chicken karahis at 0. A name that states the level wins:
- "non spicy", "not spicy", "no spice" or "mild" caps spice at 0.1;
- a chilli word ("spicy", "chilli", "mirchi", "jalapeño", "peri peri", "sriracha", "Szechuan") raises it to at least 0.5;
- so does "karahi", which is cooked with green chilli. A Shinwari karahi is left alone, because it is traditionally made with salt and tomato.

"Hot" is not a chilli word: a hot gulab jamun is served hot. Corrected dishes are marked `taste_source: name_rule`, which scoring trusts at 0.8, a little below the original values, and the build report lists them.

### Locations

Addresses are OpenStreetMap geocodes, mostly in Urdu script. `pipeline/areas.py` turns each into a short area name: a sector from its Latin or Urdu spelling ("F-7/2" and "ایف-7" are both F-7), otherwise a named place (DHA, Bahria Town, Saidpur, Blue Area, Rawat). It also records `location_precision`:
- `place`: the coordinates are the restaurant's own.
- `area`: the centre of its sector, so a distance is approximate. Either several restaurants share the point (all five F-10 restaurants without a street address do), or the address names nothing below the sector.
- `unknown`: missing, or outside Islamabad and Rawalpindi. Sakura was geocoded to Chittagong, Bangladesh. These coordinates are never used for a distance, and the dish shows no area.

Distances are straight lines from the location the user sends, never by road. The location picker's areas (`GET /areas`) are the mean of their restaurants' own coordinates.

## Still open

- The rest of the automated pass. It was restarted on 2026-09-14 for the last 830 dishes. Groq's free tier allows 200,000 tokens a day, refilled gradually, and the app's own intent extraction shares that allowance. If the pass stops, `python -m pipeline.classify_categories` resumes where it left off. When it finishes, `python -m pipeline.review_sheets --ocr-next` writes a third OCR worksheet for any newly flagged names, then rebuild and reseed.
- The optional half-and-full tab of the platter worksheet (261 rows) is unanswered. Those dishes use the menu count or the price-based guess.
- The Afghan category's accent colour and typeface (Phase 6).

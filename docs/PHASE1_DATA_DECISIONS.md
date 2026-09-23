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
- Seafood crackers and plain side salads are `add_ons` too (`plain_side`, 2026-09-21).
  - Fish crackers had been filed as a Chinese main, and "fish" in the name made them a plate of fried fish: 726 kcal with 43 g of protein, which won a health-weighted query. A Rs 30 "Salad" at Savour Foods was filed as continental, with 500 kcal from olive oil.
  - Any name with *fish*, *prawn* or *shrimp crackers* counts ("Chinese Fish Crackers", "Prawns Cracker (Half)"), as does a bare *Salad* or *Kachumber Salad*. A named salad (Green, Caesar, Fattoush) can be a meal and is left alone.
  - The rule wins over the one that keeps a dish naming seafood out of `add_ons`.
  - Nine dishes moved. *Fish crackers* and *prawn crackers* are vocabulary entries that keep the fish or shellfish allergen. For nutrition they stand for their seafood, with USDA's extruded corn chips as the stand-in (USDA has no fish crackers).

### Ingredients, allergens and diet flags

- A dish's ingredients are the ones named in its name or description, plus the typical ingredients from the pass. The vocabulary includes Urdu spellings and dish names that imply an ingredient: *shakshuka* → egg, *kheer* → milk and rice, cakes and pancakes → egg and flour.
- **Named detection is authoritative.** The model's lists can miss allergens: it left egg out of shakshuka even when the prompt gave that exact example. Allergen data is therefore still an estimate, and the app should say so.
- An owner's item list adds its ingredients to the platter. An item that is also on the same restaurant's menu brings that dish's ingredients with it: *Philadelphia Maki* names no fish, but Umai's own menu entry for it does. The list counts as the whole dish, and so can support a vegetarian claim, only when every item on it was recognised. Without these two rules, Umai's Zen and Hanami sushi platters were marked vegetarian. The vocabulary also covers platter terms: *malai*, *tandoori*, *tikka* and *patakha boti*, *reshmi kabab* and *sajji* → chicken; *maki*, *nigiri* and *sushi* → rice; *sashimi*, *nigiri*, *toro* and *sake* → fish. *Chapli kebab* is left out, because it comes in beef, chicken and mutton here.
- A name that means a fried coating adds wheat flour: *nuggets*, *broast*, *zinger*, *strips*, *crispy*, *katsu*, *cordon bleu*, *fried chicken/fish*, *fish & chips*, *mozzarella sticks* and similar, or *breaded*, *crumbed* or *battered* in the description. Menus rarely list the batter and the pass often left it out, so 31 recommendable dishes read as gluten-free, and Mozzarella Sticks won the gluten-free query in the golden set. The rule only adds an allergen. It skips dishes that already carry gluten, dishes that name gram flour (pakoras), and dishes with no known ingredients, which stay unknown. The flour counts for allergens and exclusions but not for nutrition, because breading is a small share of a serving and would otherwise displace the protein. *Lady finger* (okra) and *finger chips* (fries) are excluded. *Breadcrumbs* and *panko* map to wheat flour.
- **The allergen audit (2026-09-21)** checked every recommendable dish's name against words that name an allergen source and against standard recipes. Only additions resulted; no tag was removed.
  - Names: *mussels*, *scallops* and *clams* are shellfish (they had read as fish only); *Nutella*, *hazelnut* and *praline* are nuts; *edamame* is soy; dumpling, wonton, momo and gyoza wrappers are wheat. *Oyster* stays with oyster sauce, which is what it means on these menus.
  - Standard recipes (`RECIPE_IMPLIES`), which count for allergens and exclusions only, never nutrition:
    - nihari and haleem → wheat;
    - kunafa → wheat and nuts;
    - kung pao → peanuts;
    - chapli kebab and kofta → egg;
    - katsu, schnitzel and cordon bleu → egg;
    - tikka and tandoori → yogurt (namkeen tikka excepted);
    - tom yum and tom kha → fish sauce;
    - korma → nuts;
    - Caesar → anchovy;
    - kabuli pulao → nuts.
  - 56 tags were added across 55 dishes. Tom Kha Vegetable is no longer marked vegetarian (fish sauce), which is the cautious reading.
- Pork and alcohol count only when the dish itself names them. Suggestions from the pass are ignored, and the build report lists them.
- A dish is vegan or vegetarian only when the whole dish was assessed, meaning the pass answered or the owner listed what it includes.
- A dish with no ingredients has unknown allergens and is excluded for anyone who declares an allergy.

### Nutrition

- USDA SR Legacy values for every ingredient (`data/reference/ingredient_nutrition.csv`, with the FDC id on each row) replace the sourcing project's Open Food Facts matches. For 43 of 82 ingredients those matches were a different food.
- The apportioning method is the sourcing project's (a category serving weight split between bulk, fat and vegetables), with three fixes:
  - no estimate for a dish without ingredients;
  - vegetable dishes are not padded with flour;
  - desserts and drinks get no onion default.
- **The split is calibrated against dishes USDA measured whole (2026-09-21, `scripts/calibrate_nutrition.py`).**
  - USDA SR Legacy includes lab-analysed restaurant plates ("Restaurant, Chinese, kung pao chicken", "Fast foods, cheeseburger"). 113 of our dishes are the same food as 28 of them.
  - The sourcing project's 50% bulk / 15% fat put 15% of every plate's weight down as pure oil: 60 g in a desi serving. The median dish got 68% of its energy from fat, and 78% of dishes were over 50%. USDA's measured dishes sit at a median of 44%, and only 5 of 135 are over 60%.
  - A grid of splits was scored on the matched dishes by median error in fat share and in calories per 100 g. Among splits within 0.005 of the best, the least biased was chosen: **71% bulk, 7% fat, 15% vegetables.**
  - Fat share error went from +20 points to +2. Calories per 100 g were no worse (median error 20.5% before, 19.2% after).
  - After the rebuild, the median dish gets 48% of its energy from fat (was 69%), and 16% of dishes are over 60% (was 74%).
  - It fits Chinese dishes and fast food best. Deep-fried Italian and family-style dishes (mozzarella sticks, fried prawns) now come out 13 points under, because frying adds fat that one share can't capture.
- **A soup is mostly broth.** Split like a plate, a hot and sour soup was 250 g of chicken: 749 kcal and 74 g of protein. USDA measures a Chinese restaurant's hot and sour soup at 39 kcal per 100 g.
  - A dish named as a soup (*soup*, *shorba*, *yakhni*, *broth*, *chowder*, *bisque*, *tom yum*) counts only 20% of its serving as solids; the rest is broth.
  - This was calibrated on 36 of our soups matched to 9 measured ones. As plates they were +367% on calories per 100 g; at 20% the median error is 26%.
- **A dish with no main ingredient is made of what it does have.** A vegetable dish is its vegetables (as before), and a cheese plate is its cheese: the table files cheese as a fat, so "Jibne Kurdiyey" (cheese and herbs) came out at 61 kcal, now 208. Only fats that are foods count — cheese, cream, tahini, nuts, coconut — never the oil, ghee or butter a dish was cooked in, or a "Duck Roast" listing oil and soy sauce would be a plate of oil (2,434 kcal).
- `nutrition_confidence` is `high`, `medium`, `low` or `none`. Estimates are also flagged when they fail an energy-consistency check or exceed 2,500 kcal.
- Known limitation: one fat share for every cooking method. Fried food is under-estimated and dishes cooked with little oil slightly over. The ingredient lists from the automated pass also decide a lot: a mushroom soup listing chicken (the stock) is estimated with chicken.

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

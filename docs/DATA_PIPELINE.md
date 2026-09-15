# Data Pipeline

How the dish dataset is built and loaded into Neo4j (Phase 1). Everything the pipeline produces lives under `data/` and `data_review/`, which are git-ignored, so the dataset stays out of the public repository (see `ATTRIBUTIONS.md`). The decisions behind each rule are in `PHASE1_DATA_DECISIONS.md`.

## Run order

```bash
# One-time: the USDA SR Legacy CSV (public domain, ~6 MB)
curl -L -o data/reference/usda/sr_legacy.zip \
  https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip
python -c "import zipfile; zipfile.ZipFile('data/reference/usda/sr_legacy.zip').extractall('data/reference/usda/sr_legacy')"

python -m pipeline.usda_reference              # 1. ingredient nutrition table
python -m pipeline.classify_categories         # 2. category, damaged-name flag, typical ingredients
python -m pipeline.review_sheets --ocr-next    # 3. names step 2 flagged that no worksheet lists yet
python -m pipeline.build_dataset               # 4. data/dishes_v2.csv and data/build_report.md
python seed_real_data.py --reset               # 5. wipe Neo4j and load the dataset
```

Step 2 calls Groq, one request per 25 dishes, and paces itself under the free tier's per-minute token limit. It caches every answer in `data/cache/category_llm.json`. If it hits a daily limit it saves and stops; run it again to continue.

**After the owner fills in a worksheet, re-run steps 4 and 5 only.**

## Inputs

| Input | Where | Used for |
|---|---|---|
| Handoff dataset | `handoff_output/mood4food_dishes.csv` | The 2,545 dishes, prices, coordinates and taste values |
| Review flags, OCR line, menu description | sourcing project `data/master_menu.csv` | Review status, price evidence, ingredient detection |
| OCR candidates | sourcing project `data/ocr_results.json` (both batches) | Price evidence and links to menu photos |
| USDA SR Legacy | `data/reference/usda/` | Nutrition per 100 g for every ingredient |
| Automated pass | `data/cache/category_llm.json` | Category, damaged-name flag, typical ingredients |
| Owner worksheets | `data_review/*.xlsx` | Serving counts, included items, name decisions |

The sourcing project is expected next to this repository (`../Data-Scraper/mood4food-data-sourcing`). Set `MOOD4FOOD_SOURCING_DIR` if it lives elsewhere.

## What every dish gets

- **`dish_uid`** — a stable id derived from the original restaurant and dish name. Neo4j's internal ids change on every re-seed; this one doesn't, so user history can refer to it.
- **Name.** `dish_name` is the owner's fix if there is one. `raw_dish_name` always keeps the original. `name_status` says whether the name was kept, fixed, discarded, or is still flagged.
- **Category** from the automated pass, recorded with `category_source`. Dishes the pass could not judge keep their old category.
- **Ingredients.**
  - Those named in the dish text, matched against the vocabulary in `pipeline/ingredients.py`, which includes Urdu spellings and dish names such as *shakshuka* → egg.
  - Plus the typical ingredients from the automated pass.
  - `ingredients_basis` says which of the two a dish's list came from.
- **Allergens and diet flags** derived from those ingredients.
  - A dish with no ingredients has `allergens_known = false`, is not vegan or vegetarian, and is never offered to someone who excluded an allergen.
  - `is_halal` means *no pork or alcohol detected*, not certification.
- **Nutrition** per serving (calories, protein, carbs, fat), computed from USDA values. `nutrition_confidence` is `high`, `medium`, `low` or `none`.
- **Price check.** `price_status` is `trusted`, `verified` or `unverified`. A price that can't be right (under Rs 20, or over 8× the restaurant's median with no size word) quarantines the dish.
- **Servings.** `serves_min` / `serves_max` and `price_per_person`. `serves_source` is one of `owner`, `menu`, `price_estimate` or `default`.
- **Quarantine.** `quarantined` and `quarantine_reason`. The reasons are:
  - a gross price error;
  - an OCR name the owner discarded;
  - a platter the owner marked `remove` (typed into any answer cell of the platter worksheet).

  Quarantined dishes stay in Neo4j and are filtered out of recommendations.

Every automated value carries its source (`category_source`, `ingredients_basis`, `nutrition_confidence`, `price_status`, `serves_source`, `taste_source`, `halal_note`). The app can then say "estimated" wherever that's true, instead of presenting a guess as a measured value.

## Modules

| Module | Does |
|---|---|
| `pipeline/paths.py` | Every input and output location |
| `pipeline/sources.py` | Readers for the handoff CSV and the sourcing project; `dish_uid` |
| `pipeline/ingredients.py` | The ingredient vocabulary, name matching, allergen and diet flags |
| `pipeline/usda_reference.py` | Maps each ingredient to one USDA entry and builds the nutrition table |
| `pipeline/classify_categories.py` | The automated category and ingredient pass |
| `pipeline/nutrition.py` | Per-serving estimate and plausibility check |
| `pipeline/prices.py` | Price evidence and gross-error rules |
| `pipeline/servings.py` | Serving counts and price per person |
| `pipeline/review_sheets.py` | Owner worksheets (never overwrites an existing one) |
| `pipeline/build_dataset.py` | Joins everything; writes the dataset and the build report |
| `pipeline/seed.py` | Loads the dataset into Neo4j |

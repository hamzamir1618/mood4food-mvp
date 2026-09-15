# Diagnostic History

Compacted on 2026-09-14 from 24 diagnostic, trace and audit documents written between 2026-08-12 and 2026-08-31, which were removed from the repo root during cleanup. Read this before re-diagnosing something that feels familiar — several bugs in this project were root-caused more than once.

The originals were never committed to git.

## Resolved root causes

| Symptom | Root cause | Fix | Still relevant |
|---|---|---|---|
| "Craving something sweet" won by a burger with zero sweetness | The Taste agent scored against the persona's taste vector; the parsed `mood_vector` never reached it | `run_debate` overrides the persona taste with the user's mood vector when any dimension is > 0 | Yes — the override lives in `consensus_manager.py` |
| Sweet queries won by *Sweet and Sour Prawns* (Rs 2,050–2,600) | A savoury dish with a sweet sauce scores `u_taste = 1.0` under cosine similarity, and `u_health = 1.0` let it outvote real desserts despite `u_budget = 0` | Dessert semantic gate (restrict to `cafe_bakery` when sweet is dominant), 0.4 minimum-relevance floor, taste-weight boost | Mitigated, not solved. The root cause is the magnitude-blind taste metric (Phase 3) |
| A Rs 4,795 dish won an "under Rs 1000" query | **Not a pipeline bug.** The diagnostic script called `query_safe_candidates([], 99999)`, bypassing the Tier 1 budget filter, then scored in Python | None needed. The live pipeline binds `budget_max` correctly, verified by capturing the Cypher parameters | Lesson: diagnostics must go through `run_anchoring_pipeline`, or they measure a pipeline that doesn't exist |
| "Something with fish" / "biryani please" ignored | No positive-preference field in `GroundedIntent`, no Cypher clause, and Tier 2 used a `u_total = 1000.0` dish-name substring hack | `preferred_category` field plus a Tier 1 filter with relaxation; the 1000.0 hack removed | The `u_taste = 2.0` override later reintroduced the same shape (Phase 3 removes it) |
| The Mood chip always showed "Neutral" | `mood_vector_seed` was hardcoded to `"neutral"` in `symbolic_anchoring.py` | `get_mood_summary()` derives it from the parsed mood | Resolved |
| 44.6% of dishes had all-zero taste vectors | The gap is in the source CSV, not the seeder — a 20-dish Neo4j-vs-CSV comparison matched 1:1 | `taste_enrichment.py` fills priors at seed time with a `taste_source` provenance tag (see `ENRICHMENT_METHODOLOGY.md`) | Resolved at seed time, which means 44.6% of taste profiles are estimates |
| Different queries returned the same winner | Suspected session/cache staleness — **ruled out**: four fresh sessions produced distinct intents and distinct utilities | The cause was scoring and extraction, not state | Resolved as a diagnosis |
| "I'm vegan" / "I'm vegetarian" not parsed | The keyword extractor required a negation word | Vocabulary plus a negation bypass in `keyword_extractor.py` | Superseded by Groq extraction; the keyword path is now fallback only |
| Cheese Sauce (Rs 95) recommended as a meal | The Budget agent over-rewards cheap add-ons | Tier 1 excludes `add_ons`, `sides`, `beverages` | Resolved. There is no `sides` category in the real data |
| Nutrition estimates far off (a fish dish at 1,590 kcal, a soup at 900) | The sourcing project's ingredient reference table: for 43 of 82 ingredients the "curated" Open Food Facts match was a different product — egg → a snack stick (503 kcal/100 g), fish → 582 kcal/100 g with 1.3 g protein, rice → wheat, tomato → bread. Its methodology doc describes the curation as AI-simulated. | Phase 1 rebuilt the table from USDA SR Legacy, with the FDC id on every row (`pipeline/usda_reference.py`) | The handoff CSV still carries the old values; the v2 dataset does not |
| Meat, egg and dairy dishes marked vegan | The sourcing pipeline set `is_vegan = not (meat or egg or dairy detected)`, so any dish whose name matched no ingredient was marked vegan | Phase 1 asserts vegan and vegetarian only when the whole dish was assessed; a dish with no ingredients is neither | Resolved in the v2 dataset; the build report counts the withdrawn flags |
| Phase 3's health term never counted, and every price read as unverified (2026-09-14) | Candidates reach Tier 2 through the session store as `Candidate` models, and Pydantic silently drops undeclared fields, so `nutrition_confidence`, `price_status`, `taste_source`, servings and review status never arrived. The golden set (`scripts/golden_set.py`) caught it: every winner showed `u_health = None` | Declared the fields on `Candidate`; `tests/test_candidate_contract.py` round-trips a Tier 1 candidate and checks it scores the same | Yes. It is the same "wired up, never arrives" shape as `taste_source` before it: any new field scoring reads must be declared on `Candidate` |

## What `human_confirmed` means

Established on 2026-09-14 from the sourcing project's code. It contradicts `handoff_output/HANDOFF_NOTES.md`, which describes the 1,150 `False` rows as "explicitly rejected during the review". They were not rejected.

- **`True` (1,157 rows)** — confirmed by a person in `src/ocr_review.py`, which writes `human_confirmed=True` on confirm.
- **`False` (1,150 rows)** — imported automatically by `scripts/auto_populate_clean.py` with no human pass: any OCR candidate with status `success` or `success_price_disambiguated` whose name has at least 3 letters and is at least 40% alphabetic. The sourcing project's own `progress_tracker.py` counts these rows as "auto".
- **Blank (238 rows)** — scraped from restaurant websites (237) or entered manually (1).

Discarded OCR candidates never reach the CSV at all, so no row in the dataset is a rejected one. The `False` rows split into about 240 auto-imports inside the restaurants reviewer A worked on, plus every row from reviewer B's 24 restaurants — none of which were confirmed through the review tool, although the partner kit's copy of `ocr_review.py` does set the flag on confirm. OCR damage concentrates in these rows: 38 of the 44 dishes with damaged names, all 4 price-split fragments and 14 of the 20 prices under Rs 50 are `False`.

## Intent extraction

Three generations were measured on the same kind of 20-phrase matrix:

- **Keyword extractor (v1)** — brittle regex. Phrases that extracted nothing included "halal food only", "i hate tomatoes" and "healthy salad with high protein". The briefing puts it at roughly 6/20.
- **Local Phi-3.5 via Ollama (v2)** — retired. Up to 18.8 s per query.
- **Groq `openai/gpt-oss-120b` (v3)** — current. 0.44–7.46 s per query.

**Caveat — the v2 and v3 "20 / 20 meaningful extractions" headline was not a measurement.** The harness printed `len(phrases) / len(phrases)` unconditionally and labelled every row "Groq" whether or not the keyword fallback had answered. The per-row outputs look sensible, but treat the score as unverified. Two things in the v3 table deserve a check: three rows took 5.9–7.5 s against the extractor's 5 s client timeout (probably succeeding on an SDK retry), and "healthy low calorie meal" returned no structured field at all. The harness is kept, with computed scores, as `scripts/eval_intent_matrix.py`.

Extraction gaps that matter for the concierge work:

- **Health goals** have no field. "i need a heavy protein meal for the gym" came back as `preferred_category: "protein"`, which is not a category.
- **Soft dislikes** ("i hate tomatoes") have no field — only hard exclusions exist.
- **Halal** is not represented anywhere.

## UX audit — 2026-08-12

Run against the old vanilla-JS UI and the 87-dish synthetic dataset, using a "Balanced Eater / busy young professional" persona and Nielsen's ten heuristics. Its screenshots were deleted on 2026-09-14.

Fixed at the time: the hostile "no active decision blueprint" landing error, false network-error toasts on successful loads, reasoning hidden behind generic tags, generic recipe text ("prepare proteins if needed" for a raita), the ambiguous "+Rs 40" label, and persona chips that gave no feedback. The post-fix verdict was GO for deployment.

Still open, to carry into the frontend rebuild:

- **Session amnesia** — no accounts, so preferences reset every visit (Phase 2).
- The runner-up expand chevron reads as a "trend down" arrow on touch devices, where its tooltip never shows.
- The low-budget warning (under Rs 50) adds a click for people who genuinely want a cheap snack.
- Persona chips animate the sliders instantly, but the winner updates about 0.5 s later, so the two briefly disagree.
- Recipes open in a modal, which makes comparing recipes across runners-up slow.

Lessons that held up:

- Reasoning has to read as **sentences**. Shown as tags, it looked like any delivery app's filter chips and the differentiator disappeared.
- **Honest gaps beat plausible filler.** "Recipe not available yet" rebuilt trust that generic steps had destroyed.
- The weight **sliders** were the most novel interaction — neither ChatGPT nor Foodpanda offers it.

## Superseded by the move to real data

Everything user-facing was synthetic until 2026-08-27: 55, then 87, hand-authored dishes in `seed_neo4j.py` (since deleted), LoremFlickr and Unsplash images, and invented restaurant ratings and delivery fees. The audit that established this (2026-08-13) prompted the switch to `handoff_output/mood4food_dishes.csv`.

Two lessons survived the switch:

- **The health score saturates.** One synthetic soup with a protein-to-calorie ratio above the Health agent's 0.05 ceiling swept the Gym Bro persona. Any real dish above that ceiling will do the same.
- **`MockRestaurantProvider` still exists**, with invented ratings and fees. It is opt-in (`RESTAURANT_PROVIDER=mock`); the default is `neo4j`.

## Persona weights

After the switch to real data, persona weights were retuned by hand, because real macros and taste vectors cluster more tightly than the synthetic ones did:

| Persona | Health | Budget | Taste |
|---|---|---|---|
| Gym Bro | 0.80 | 0.00 | 0.20 |
| Comfort Seeker | 0.00 | 0.25 | 0.75 |
| Frugal Student | 0.00 | 0.80 | 0.20 |
| Adventurous Foodie | 0.10 | 0.10 | 0.80 |
| Health Nut | 0.80 | 0.10 | 0.10 |

These weights are fitted to the current scoring functions. Revisit them once Phase 3 replaces those functions, because they will no longer mean the same thing.

## What was removed

Cleanup on 2026-09-14 removed the following from the repo root:

- **24 diagnostic documents**, compacted above: the `*_TRACE.md`, `*_CHECK.md` and `*_AUDIT.md` files, three intent-extraction matrices, two friction logs, the overhaul backlog, the diff summary, the final audit summary, the viability notes and `DATA_INTEGRATION_NOTES.md`.
- **64 one-off Python scripts**: code-mod scripts (`fix_*`, `update_*`, `patch_*`, `add_*`, `remove_*`) whose edits are already in the code; ad-hoc probes (`check_*`, `debug_*`, `verify_*`, `find_*`); the synthetic-data generators; `inject_fake.py`; `clear_db.py`; and the obsolete root `test_suite.py`, whose allergen cases now live in the eval harness.
- **`scratch/`** — throwaway probes. `run_matrix_v3.py` was kept as `scripts/eval_intent_matrix.py`.
- **Logs and dumps** — CI error logs, a `git log -p` dump, server traces and candidate lists.
- **Retired Ollama assets** — `Modelfile` and the Phi fine-tuning `dataset.jsonl`.
- **`DATA_QUALITY_NOTES.md`**, which described the deleted synthetic seed.

The tracked files among these (`Modelfile`, `dataset.jsonl`, `test_suite.py`, `DATA_QUALITY_NOTES.md`) are recoverable from git history. The rest were untracked.

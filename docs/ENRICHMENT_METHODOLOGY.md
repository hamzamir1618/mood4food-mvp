# Taste Enrichment Methodology

## Context
44.6% of dishes (1,134 / 2,545) in the dataset have all-zero taste vectors due to gaps in the upstream OCR/scraping enrichment pipeline. The TasteAgent uses cosine similarity and returns 0.0 when either vector's magnitude is zero, making these dishes invisible to taste-driven queries.

This module applies defensible fallback priors at database seeding time. **These are explicitly labeled defaults, not measured data.** Every enriched dish carries a `taste_source` provenance field to distinguish between original data and fallback values.

## Design Principles
1. **Never overwrite original data**: If any taste dimension in the CSV is non-zero, the dish is skipped entirely.
2. **Keyword-first ordering**: Keyword scanning runs before category priors, producing distinct per-dish vectors rather than uniform blocks.
3. **Moderate prior values (0.3–0.5)**: Keeps cheap beverages/desserts from dominating budget-sensitive persona recommendations.
4. **Per-restaurant averages**: The `other` category contains 51% of dishes across 26 cuisines. Averages are computed per-restaurant, not per-category.
5. **Transparent provenance**: Every dish is tagged with its enrichment source.

## Phase 1: Keyword Dictionary Scan
Scans `dish_name` for flavor-indicating words. Multiple keyword matches combine (each dimension capped at 1.0).

### Keyword Table
| Keyword | sweet | salty | sour | bitter | umami | spice | Notes |
|---|---|---|---|---|---|---|---|
| mango | 0.7 | | 0.2 | | | | Tropical fruit |
| peach | 0.6 | | 0.2 | | | | Stone fruit |
| strawberry | 0.6 | | | | | | Berry |
| raspberry | 0.5 | | 0.3 | | | | Tart berry |
| blueberry | 0.4 | | | | | | Mild berry |
| pomegranate | 0.3 | | 0.4 | | | | Tart seed fruit |
| apple | 0.5 | | 0.2 | | | | Pome fruit |
| orange | 0.5 | | 0.3 | | | | Citrus |
| lemon | 0.2 | | 0.6 | | | | Citrus |
| lime | | | 0.6 | | | | Citrus |
| grapefruit | | | 0.5 | 0.3 | | | Bitter citrus |
| passion fruit | 0.5 | | 0.3 | | | | Tropical |
| pineapple | 0.6 | | 0.3 | | | | Tropical |
| banana | 0.6 | | | | | | Starchy fruit |
| cherry | 0.5 | | 0.2 | | | | Stone fruit |
| honey | 0.7 | | | | | | Natural sweetener |
| caramel | 0.7 | | | | | | Cooked sugar |
| chocolate | 0.6 | | | 0.2 | | | Cocoa |
| oreo | 0.6 | | | | | | Cookie brand |
| nutella | 0.7 | | | | | | Hazelnut spread |
| butter | | | | | 0.4 | | Dairy fat, savory |
| cream/creamy | 0.2 | | | | 0.3 | | Rich dairy |
| cheese | | 0.3 | | | 0.4 | | Fermented dairy |
| malai | 0.2 | | | | 0.3 | | South Asian cream |
| chilli/chili | | | | | | 0.5 | Capsaicin heat |
| achari | | | 0.4 | | | 0.4 | Pickled/spiced |
| masala | | | | | 0.3 | 0.5 | Spice blend |
| pepper | | | | | | 0.3 | Mild heat |
| schezuan/szechuan | | | 0.2 | | | 0.6 | Numbing spice |
| peri peri | | | | | | 0.5 | Chili marinade |
| mirchi/mirchilli | | | | | | 0.6 | Green/red chili |
| hot | | | | | | 0.4 | General heat |
| spicy | | | | | | 0.5 | General heat |
| namkeen | | 0.5 | | | | 0.2 | Savory/salty |
| qeema/keema | | | | | 0.5 | 0.3 | Minced meat |
| gravy | | 0.3 | | | 0.4 | | Sauce-based |
| broth | | 0.2 | | | 0.4 | | Liquid base |
| soup | | 0.2 | | | 0.3 | | Liquid dish |
| sour | | | 0.6 | | | | Direct flavor |
| tangy | | | 0.5 | | | | Acidic flavor |
| tamarind | 0.2 | | 0.5 | | | | Sweet-sour |
| coffee | 0.1 | | | 0.5 | | | Roasted bean |
| green tea | | | | 0.3 | | | Unoxidized leaf |

`taste_source` = `"keyword"` for dishes enriched by this phase.

## Phase 2: Category-Based Fallback Priors
Applied only when Phase 1 produces all-zero values. Detection is by dish name substring matching.

### Beverage Detection
**Pattern words:** juice, tea, shake, smoothie, lemonade, cola, fanta, sprite, pepsi, soda, soft drink, mojito, margarita, mocktail, cocktail, lassi, frappe, latte, cappuccino, mocha, milkshake, sharbat, cooler, squash, dew, 7up, mineral water

**Baseline prior:** `sweet=0.4`

**Citrus/tea sub-rule:** If the beverage name also contains tea, lemon, lime, grapefruit, or orange → add `sour=0.25`

**Exceptions (remain all-zero, tagged `"neutral"`):** Exact match "water" or "plain water", or name contains "black coffee", "diet", "sugar free", "unsweetened", "zero"

**Rationale:** Most commercial beverages in Pakistan (soft drinks, iced teas, margaritas, lassis, shakes) are sweetened. The 0.4 prior is moderate — high enough to give beverages visibility in taste queries but low enough that a Rs. 100 Soft Drink won't dominate the Sweet Tooth persona over a Rs. 300 Suji Halwa (sweet=0.9) or Mango Lassi (sweet=0.8).

### Dessert Detection
**Pattern words:** cake, brownie, cookie, ice cream, kheer, halwa, gulab, kunafa, cheesecake, pudding, mousse, tiramisu, sundae, waffle, pancake, donut, muffin, tart, flan, pastry, pie, barfi, mithai, jalebi, ras malai

**Baseline prior:** `sweet=0.5`

**Rationale:** Desserts are inherently sweet. 0.5 is a conservative default — real desserts like Suji Halwa (0.9) and Kheer (0.9) score much higher, so fallback-enriched desserts won't displace known-good entries.

### BBQ/Grill/Karahi Detection
**Pattern words:** karahi, tikka, kebab, kabab, seekh, chapli, sajji, tandoor, tandoori, bbq, barbeque, grill, roast, boti

**Baseline prior:** `umami=0.4, spice=0.35`

**Rationale:** Grilled and karahi-style dishes are characterized by protein umami and spice blends. These moderate values position them correctly for Comfort Seeker and Adventurous Foodie personas without overwhelming Health Nut or Gym Bro scoring.

`taste_source` = `"category_prior"` for dishes enriched by this phase.

## Phase 3: Restaurant-Cuisine-Average Fallback
Applied only when Phases 1 and 2 both produce all-zero values. These are "ambiguous" dishes whose names don't indicate flavor (e.g., "Gin Fam", "Twosome", "Three Sisters", "Quzu Qovurma").

**Method:**
1. Group all dishes by `restaurant_name`.
2. For each restaurant, compute the mean of each taste dimension across dishes that have at least one non-zero value (from original data or Phases 1-2).
3. Apply that mean to the remaining zero-taste dishes in the restaurant.

**Why per-restaurant, not per-category?** The `other` category contains 1,306 dishes (51%) spanning 26 different restaurants with wildly different cuisines (Chinese, Lebanese, Afghan, BBQ). A global `other` average would be meaningless. A Kim Mun Chinese combo deal should inherit Kim Mun's Chinese flavor profile, not a blend of Afghan and Italian.

**Last-resort fallback:** If a restaurant has zero non-zero dishes (extremely unlikely after Phases 1-2), apply a minimal category-level generic:
- chinese_asian → umami=0.35, salty=0.25
- desi_traditional → umami=0.25, spice=0.3, salty=0.2
- middle_eastern → umami=0.25, salty=0.25, sour=0.15
- fast_food → salty=0.35, umami=0.25
- cafe_bakery → sweet=0.35, bitter=0.15
- continental_upscale → umami=0.25, salty=0.2
- pizza → salty=0.35, umami=0.35
- sandwich → salty=0.25, umami=0.2
- other → restaurant-level average across all categories (if available), or umami=0.2, salty=0.2

`taste_source` = `"restaurant_average"` or `"global_prior"` for dishes enriched by this phase.

## Phase 4: Provenance Tracking
Every dish receives a `taste_source` field stored on the Neo4j Dish node:

| Value | Meaning |
|---|---|
| `original` | CSV had non-zero taste values; untouched |
| `keyword` | Phase 1 keyword scan produced values |
| `category_prior` | Phase 2 category rule applied |
| `restaurant_average` | Phase 3 restaurant mean applied |
| `global_prior` | Phase 3 last-resort category generic applied |
| `neutral` | Matched an exception (e.g., "Water"); intentionally zero |

This field is for audit purposes only. It is not used by the scoring pipeline.

## Verification Criteria
1. `Soft Drink` → taste_sweet ≈ 0.4 (beverage prior)
2. `Peach Iced Tea` → taste_sweet ≈ 0.6, taste_sour ≈ 0.2 (keyword: peach + tea)
3. `Mint Margarita` → taste_sweet ≈ 0.4 (beverage prior)
4. `Water` → all-zero (exception match, source=neutral)
5. Global all-zero percentage < 10%
6. No block of >10 dishes sharing an identical non-zero vector

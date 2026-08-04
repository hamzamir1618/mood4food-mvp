# Project Transformation: FIPE Mood4Food to End-to-End Consumer App

This document outlines the architectural changes and granular action plan required to evolve the MVP from a mathematical recommendation engine into a highly viable, daily-use consumer application.

## Open Questions
> [!IMPORTANT]
> **Clarification needed on prioritization:**
> 1. For "Actionability" (Fulfillment), should we focus first on **Delivery Integration** (e.g., mocking a Foodpanda/UberEats API) or **Home Cooking** (generating recipes and grocery lists)?
> 2. For "Visuals", do you want to use static asset images for dishes, or should we dynamically generate them on the fly using a local image generation model (e.g., Stable Diffusion)?
> 3. Should we implement persistent user accounts for personalization, or rely on local device storage (browser localStorage / Flutter shared_preferences) to remember preferences anonymously?

---

## Part 1: Additional Features & Improvements

Beyond the core Actionability, Visuals, Context, and Memory, the following features will drastically increase user retention and product value:

1. **Taste Personas & Profiles:**
   - **Concept:** Users can select or be assigned personas (e.g., "The Gym Bro", "The Comfort Seeker", "The Adventurous Foodie", "The Frugal Student"). This defines baseline weights and multi-dimensional taste profiles (sweet, savory, umami, sour, bitter) instead of a simple 1D mood vector.
   - **Value:** Deepens personalization and makes the app feel tailored to lifestyles rather than just individual meals.

2. **Hyper-Reactive Parameter Tweaking (Distinct Dish per Tweak):**
   - **Concept:** Expose all utility axes (Health, Taste, Budget, Adventure) as interconnected sliders. Enhance the utility curves and candidate density so that *any* slight adjustment dynamically shifts the Nash Equilibrium, crowning a distinct new winner instantly.
   - **Value:** Turns the app into a fun, interactive "playground" where users feel totally in control of the outcome.

3. **Group Dining Mode (The "We Don't Know What to Eat" Solver):**
   - **Concept:** Users describe constraints for a group ("3 people, one vegan, one hates spicy, budget 4000 total"). 
   - **Value:** Eliminates the classic group argument over food.

4. **Pantry / "Cook With What I Have" Mode:**
   - **Concept:** The user snaps a photo of their fridge. Tier 1a Vision extracts the available ingredients, and Tier 1b prioritizes dishes that maximize the use of those ingredients.
   - **Value:** Solves food waste and immediate convenience.

---

## Part 2: Granular Action Plan

### Phase 1: Visual Appetite & UX Humanization
*Goal: Make the app look delicious and hide the math.*

#### [MODIFY] `seed_neo4j.py`
- Add an `image_url` property to all `:Dish` nodes (using high-quality stock photos or AI-generated placeholders).
- Add a `human_tags` property (e.g., `["High Protein", "Cheap", "Spicy"]`).

#### [MODIFY] Frontend (`web_ui/` & `fipe_flutter/`)
- Replace the text-heavy Winner Card with a full-bleed background image of the dish.
- Translate the Math: Hide exact utility percentages. Display chips like `🔥 High Protein` and `💸 Wallet Friendly`.
- Expose **multi-parameter sliders** (Budget, Health, Comfort) rather than just a single Budget slider.
- Move the XAI Trace panel behind a "Developer Mode" toggle in the settings.

---

### Phase 2: Taste Personas & Hyper-Reactive Tweaking
*Goal: Every tweak yields a new, personalized result.*

#### [MODIFY] `tier_2/agents.py`
- Re-map the `TasteAgent` to compute cosine similarity against a multi-dimensional profile (Sweet, Salty, Sour, Bitter, Umami, Spice) rather than a single 384-dimensional text embedding.
- Introduce non-linear sensitivity to the Utility formulas so that candidates cluster closely. This ensures that adjusting a slider by even 5% flips the winner, giving the user a "distinct dish per tweak".

#### [MODIFY] `orchestrator.py` & Frontend
- Update the `/recalculate` endpoint to accept an array of weights `[w_budget, w_health, w_taste, w_adventure]`.
- Frontend: Implement interconnected UI sliders where pushing one parameter (e.g., Health) automatically dynamically lowers the others, immediately flashing a new distinct dish.

#### [NEW] `tier_1/persona_manager.py`
- Introduce a pre-processor that reads user personas (e.g., "The Gym Bro") and overrides the starting `w_health`, `w_budget`, etc., before the first calculation.

---

### Phase 3: Actionability (Fulfillment)
*Goal: Bridge the gap between recommendation and eating.*

#### [NEW] `tier_3/fulfillment_engine.py`
- Create a new module that triggers after the `decision_blueprint.json` is generated.
- **Path A (Order):** Mock integration with a restaurant API. Takes the winning dish (e.g., "Anda Curry") and searches a mock database of local restaurants to append `restaurant_name`, `delivery_time`, and `order_url` to the blueprint.
- **Path B (Cook):** Utilize the local LLM to generate a step-by-step recipe and a shopping list based on the dish's Neo4j `:Ingredient` nodes.

#### [MODIFY] Frontend (`web_ui/` & `fipe_flutter/`)
- Add two primary Call-to-Action buttons on the Winner Card:
  1. `🛵 Order via [Restaurant]`
  2. `🍳 View Recipe & Grocery List`

---

### Phase 4: Context Awareness, Memory & Advanced Features
*Goal: The system knows who you are, where you are, what time it is, and who you are with.*

#### [MODIFY] `seed_neo4j.py` & Graph Schema
- Introduce `:User` nodes with relationships: `(u:User)-[:LIKES]->(d:Dish)`, `(u)-[:DISLIKES]->(i:Ingredient)`.
- Greatly expand the dish dataset to ensure a dense enough graph so that small tweaks always find a valid distinct dish.

#### [MODIFY] `tier_1/multi_modal_ingestion.py`
- **Group Mode:** Update the `extract_intent_llm()` prompt to handle plural constraints. Return a merged constraint JSON (summed budgets, union of allergens).
- **Pantry Mode:** Integrate a dedicated prompt for Image Ingestion to extract a list of visible ingredients from a fridge photo. Pass this as an `available_ingredients` array in `grounded_intent.json`.

#### [MODIFY] `tier_2/consensus_manager.py`
- **Add a Contextual Utility Agent (`U_context`):** Scores dishes based on time of day and weather.
- **Add a Personalization Agent (`U_personal`):** Rewards dishes connected via `[:LIKES]` in Neo4j.

## Verification Plan

1. **Phase 1 Verification:** Ensure the UI displays images and human-readable tags instead of math.
2. **Phase 2 Verification:** Move the Health, Taste, and Budget sliders incrementally. Verify that a visually distinct, logically sound new dish takes the #1 spot with almost every adjustment.
3. **Phase 3 Verification:** Test the fulfillment endpoints to confirm order links and recipes are correctly appended to the blueprint.
4. **Phase 4 Verification:** Send a query at 8:00 AM vs 8:00 PM and verify `U_context` shifts the winner. Upload an image of tomatoes and onions; verify that dishes requiring those ingredients are ranked higher.

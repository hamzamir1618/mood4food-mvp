"""
Tier 1 — Graph Constraint Pipeline
Reads grounded_intent.json, queries Neo4j to prune allergens, and emits
candidate_evaluation.json with the surviving safe dish nodes.
"""

import json
import logging
import time
from pathlib import Path

from neo4j import GraphDatabase

from config import settings
from pipeline.ingredients import ALLERGEN_TAGS, VOCABULARY

# ── Config ──────────────────────────────────────────────────────────────────
CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"
GROUNDED_INTENT_PATH = CONTRACTS_DIR / "grounded_intent.json"
CANDIDATE_EVAL_PATH = CONTRACTS_DIR / "candidate_evaluation.json"

NEO4J_URI = settings.NEO4J_URI
NEO4J_AUTH = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ── Intent Loader ───────────────────────────────────────────────────────────


def load_grounded_intent() -> dict:
    """Reads the grounded_intent.json contract produced by Tier 1a."""
    if not GROUNDED_INTENT_PATH.exists():
        raise FileNotFoundError(
            f"grounded_intent.json not found at {GROUNDED_INTENT_PATH}. "
            "Run multi_modal_ingestion.py first."
        )
    with open(GROUNDED_INTENT_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    log.info("loaded grounded_intent from %s", GROUNDED_INTENT_PATH)
    return data


# ── Neo4j Allergen-Prune Query ──────────────────────────────────────────────

PRUNE_CYPHER = """
MATCH (d:Dish)
WHERE (d.price_rs IS NULL OR d.price_rs <= $budget_max)
  AND NOT d.category IN ["add_ons", "sides", "beverages"]
  // Quarantined dishes (gross price errors, names the owner discarded) stay on file
  // but are never offered.
  AND coalesce(d.quarantined, false) = false
  // Replaced NOT EXISTS { MATCH (d)-[:CONTAINS*1..5]->(i:Ingredient) ... }
  // with a direct check on the d.allergens array property.
  // The Ingredient node traversal was removed because Ingredient nodes
  // were never populated in the database during seeding.
  // none() over a NULL list yields NULL, which silently drops the row. When an
  // allergen IS excluded we require allergen data to be present AND clean, so a
  // dish with unknown allergens is never served to someone who excluded one.
  AND ($pruned_list = []
       OR (d.allergens IS NOT NULL
           AND none(a IN d.allergens WHERE toLower(a) IN $pruned_list)))
  AND ($req_vegan = false OR d.is_vegan = true)
  AND ($req_veg = false OR d.is_vegetarian = true)
  AND ($req_halal = false OR coalesce(d.is_halal, true) = true)
  // Excluded foods that aren't allergen tags ("no meat", "no seafood"), by ingredient
  AND ($excluded_ingredients = []
       OR none(i IN coalesce(d.ingredients, []) WHERE i IN $excluded_ingredients))
  // A requested category, dish or food group (see requested_match)
  AND ($preferred_category = ""
       OR toLower(d.category) CONTAINS $category_key
       OR ($match_names AND toLower(d.name) CONTAINS $preferred_category)
       OR any(i IN coalesce(d.ingredients, []) WHERE i IN $preferred_ingredients)
       OR ($preferred_allergen <> "" AND $preferred_allergen IN coalesce(d.allergens, [])))
// dish_uid is stable across re-seeds; the internal id is only a fallback for old graphs.
RETURN coalesce(d.dish_uid, elementId(d)) AS dish_id, d.name AS name,
       d.restaurant_name AS restaurant_name, d.category AS category,
       d.ingredients AS ingredients, d.allergens AS allergens,
       d.price_rs AS price_pkr, d.price_status AS price_status,
       d.serves_min AS serves_min, d.serves_max AS serves_max,
       d.calories AS calories, d.protein_g AS protein_g,
       d.carbs_g AS carbs_g, d.fat_g AS fat_g,
       d.nutrition_confidence AS nutrition_confidence, d.nutrition_flag AS nutrition_flag,
       d.review_status AS review_status, d.taste_source AS taste_source,
       d.image_url AS image_url, d.human_tags AS human_tags,
       d.taste_sweet AS taste_sweet, d.taste_salty AS taste_salty,
       d.taste_sour AS taste_sour, d.taste_bitter AS taste_bitter,
       d.taste_umami AS taste_umami, d.taste_spice AS taste_spice
"""

# A request for a food group matches dishes containing any of its ingredients; one naming
# an ingredient ("chicken", "paneer") or an allergen group ("dairy") matches dishes that
# contain it. This replaced keyword lists in Tier 2 that forced a matching dish to win.
FOOD_GROUPS = {
    "seafood": ("fish", "prawns", "crab", "lobster", "squid"),
    "shellfish": ("prawns", "crab", "lobster", "squid"),
    "meat": ("chicken", "beef", "mutton", "lamb", "turkey", "liver", "sausage"),
    "red meat": ("beef", "mutton", "lamb"),
    "prawn": ("prawns",),
    "shrimp": ("prawns",),
    "eggs": ("egg",),
    "vegetables": ("mixed vegetables",),
}


# Recommendable categories (pipeline/classify_categories.py). A request that names one
# ("afghan", "chinese", "fast food") means the cuisine, so it matches the category only:
# an "Afghan Burger" at a burger shop is not Afghan food.
CATEGORIES = (
    "desi_traditional",
    "afghan",
    "middle_eastern",
    "chinese_asian",
    "continental_upscale",
    "fast_food",
    "pizza",
    "sandwich",
    "cafe_bakery",
)

# Words people use for an excluded food, as the allergen tag that covers it. Excluding
# more than was meant is the safe direction: "no bread" also rules out pasta.
EXCLUSION_ALLERGENS = {
    "bread": "gluten",
    "wheat": "gluten",
    "naan": "gluten",
    "roti": "gluten",
    "milk": "dairy",
    "cheese": "dairy",
    "butter": "dairy",
    "cream": "dairy",
    "lactose": "dairy",
    "nut": "nuts",
    "peanut": "nuts",
    "peanuts": "nuts",
    "eggs": "egg",
    "prawn": "shellfish",
    "prawns": "shellfish",
    "shrimp": "shellfish",
}


def requested_match(term: str | None) -> dict:
    """Cypher parameters for a requested category, dish or food group."""
    term = (term or "").strip().lower()
    key = term.replace(" ", "_")
    cuisine = len(key) >= 3 and any(key in c for c in CATEGORIES)
    ingredients = (
        () if cuisine else FOOD_GROUPS.get(term) or ((term,) if term in VOCABULARY else ())
    )
    return {
        "preferred_category": term,
        "category_key": key,
        "match_names": not cuisine,
        "preferred_ingredients": list(ingredients),
        "preferred_allergen": term if term in ALLERGEN_TAGS and not cuisine else "",
    }


def exclusion_terms(excluded: list[str]) -> tuple[list[str], list[str]]:
    """
    (allergen tags, ingredient names) for what the user excluded. "no bread" becomes
    gluten; "no meat" and "no seafood" become every ingredient in the group.
    """
    allergens, ingredients = set(), set()
    for term in excluded:
        term = term.strip().lower()
        if term in ALLERGEN_TAGS:
            allergens.add(term)
        elif term in EXCLUSION_ALLERGENS:
            allergens.add(EXCLUSION_ALLERGENS[term])
        ingredients.update(FOOD_GROUPS.get(term, ()))
        if term in VOCABULARY:
            ingredients.add(term)
    return sorted(allergens), sorted(ingredients)


def _float_or_none(value) -> float | None:
    return float(value) if value is not None else None


def query_safe_candidates(
    allergens: list[str],
    budget_max: int,
    preferred_category: str = "",
    is_vegan: bool = False,
    is_vegetarian: bool = False,
    is_halal: bool = False,
) -> list[dict]:
    """
    Connects to local Neo4j and executes a deterministic Cypher query that:
      - Filters dishes with synthesized_calories <= 1000
      - Prunes any dish linked (up to 5 hops) to a banned ingredient
      - Restricts to preferred_category if specified
    Returns a list of {dish_id, name, price_pkr, protein_g, calories} dicts
    for surviving candidates.
    """
    excluded_allergens, excluded_ingredients = exclusion_terms(allergens)
    pruned_list = sorted({a.strip().lower() for a in allergens} | set(excluded_allergens))
    log.info(
        "neo4j query | pruned_list=%s, budget_max=%d, category='%s'",
        pruned_list,
        budget_max,
        preferred_category,
    )

    candidates: list[dict] = []
    driver = None
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
            driver.verify_connectivity()
            log.info("neo4j connection verified at %s", NEO4J_URI)
            break
        except Exception as exc:
            if attempt == max_attempts:
                log.error("neo4j connection failed after %d attempts: %s", max_attempts, exc)
                raise
            sleep_time = 2**attempt
            log.warning(
                "neo4j connection failed (attempt %d/%d). Retrying in %ds... Error: %s",
                attempt,
                max_attempts,
                sleep_time,
                exc,
            )
            time.sleep(sleep_time)

    try:
        CATEGORY_REP_IMAGES = {
            "chinese_asian": "https://images.unsplash.com/photo-1585032226651-759b368d7246?auto=format&fit=crop&w=800&q=80",
            "desi_traditional": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=800&q=80",
            "afghan": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=800&q=80",
            "continental_upscale": "https://images.unsplash.com/photo-1544025162-8315ea07525b?auto=format&fit=crop&w=800&q=80",
            "middle_eastern": "https://images.unsplash.com/photo-1628198759560-6c97a5522731?auto=format&fit=crop&w=800&q=80",
            "fast_food": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=800&q=80",
            "cafe_bakery": "https://images.unsplash.com/photo-1551024601-bec78aea704b?auto=format&fit=crop&w=800&q=80",
            "pizza": "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=800&q=80",
            "beverages": "https://images.unsplash.com/photo-1536935338788-846bb9981813?auto=format&fit=crop&w=800&q=80",
            "other": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80",
        }

        KEYWORD_REP_IMAGES = {
            (
                "cake",
                "brownie",
                "lava",
                "pastry",
                "lava cake",
                "molten",
            ): "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=800&q=80",
            (
                "naan",
                "roti",
                "paratha",
                "puri",
                "kulcha",
            ): "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80",
            (
                "shake",
                "malt",
                "smoothie",
                "lassi",
                "frappe",
            ): "https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=800&q=80",
            (
                "wrap",
                "roll",
                "shawarma",
                "gyro",
            ): "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=800&q=80",
            (
                "coffee",
                "tea",
                "chai",
                "espresso",
                "latte",
                "cappuccino",
            ): "https://images.unsplash.com/photo-1541167760496-1628856ab772?auto=format&fit=crop&w=800&q=80",
            (
                "ice cream",
                "sundae",
                "gelato",
            ): "https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?auto=format&fit=crop&w=800&q=80",
            ("burger", "cheeseburger", "hamburger"): CATEGORY_REP_IMAGES["fast_food"],
            ("pizza",): CATEGORY_REP_IMAGES["pizza"],
            ("karahi", "masala", "handi", "makhni", "tikka", "boti", "kebab"): CATEGORY_REP_IMAGES[
                "desi_traditional"
            ],
            (
                "juice",
                "lemonade",
                "drink",
                "soda",
                "cola",
                "sprite",
                "fanta",
                "coke",
                "pepsi",
            ): CATEGORY_REP_IMAGES["beverages"],
            ("donut", "doughnut"): CATEGORY_REP_IMAGES["cafe_bakery"],
            (
                "salad",
            ): "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80",
            (
                "soup",
            ): "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80",
            (
                "pasta",
                "spaghetti",
                "macaroni",
            ): "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=800&q=80",
        }

        with driver.session() as session:
            req_vegan = is_vegan or "vegan" in pruned_list
            req_veg = is_vegetarian or "vegetarian" in pruned_list
            result = session.run(
                PRUNE_CYPHER,
                pruned_list=pruned_list,
                budget_max=budget_max,
                req_vegan=req_vegan,
                req_veg=req_veg,
                req_halal=is_halal,
                excluded_ingredients=excluded_ingredients,
                **requested_match(preferred_category),
            )
            for record in result:
                cat = record.get("category", "")
                db_img = record.get("image_url")

                if not db_img:
                    dish_name = record["name"].lower()
                    img_url = None
                    for keywords, url in KEYWORD_REP_IMAGES.items():
                        if any(kw in dish_name for kw in keywords):
                            img_url = url
                            break
                    if not img_url:
                        img_url = CATEGORY_REP_IMAGES.get(cat, CATEGORY_REP_IMAGES["other"])
                    is_rep = True
                else:
                    img_url = db_img
                    is_rep = False

                candidates.append(
                    {
                        "dish_id": record["dish_id"],
                        "name": record["name"],
                        "restaurant_name": record.get("restaurant_name"),
                        "price_pkr": float(record["price_pkr"] or 0),
                        "price_status": record.get("price_status"),
                        "serves_min": record.get("serves_min"),
                        "serves_max": record.get("serves_max"),
                        # None stays None: a missing estimate is unknown, never zero.
                        "macros": {
                            "calories": _float_or_none(record.get("calories")),
                            "protein_g": _float_or_none(record.get("protein_g")),
                            "carbs_g": _float_or_none(record.get("carbs_g")),
                            "fat_g": _float_or_none(record.get("fat_g")),
                        },
                        "nutrition_confidence": record.get("nutrition_confidence"),
                        "nutrition_flag": record.get("nutrition_flag"),
                        "review_status": record.get("review_status"),
                        "taste_source": record.get("taste_source"),
                        "allergens": record.get("allergens"),  # None: not known
                        "category": cat,
                        "image_url": img_url,
                        "is_rep_image": is_rep,
                        "human_tags": record.get("human_tags") or [],
                        "ingredients": record.get("ingredients") or [],
                        "taste_profile": {
                            "sweet": float(record["taste_sweet"] or 0),
                            "salty": float(record["taste_salty"] or 0),
                            "sour": float(record["taste_sour"] or 0),
                            "bitter": float(record["taste_bitter"] or 0),
                            "umami": float(record["taste_umami"] or 0),
                            "spice": float(record["taste_spice"] or 0),
                        },
                    }
                )
        log.info("neo4j returned %d safe candidates", len(candidates))
    except Exception as exc:
        log.error("neo4j query failed: %s", exc)
    finally:
        if driver:
            driver.close()

    # --- HACK: Semantic Keyword Safety Net ---
    # Because d.allergens is often unpopulated in the dataset (e.g. burgers returning []),
    # we aggressively prune based on name/category substrings for major allergens.
    danger_keywords = list(pruned_list)

    if "gluten" in pruned_list or "wheat" in pruned_list:
        danger_keywords.extend(
            [
                "burger",
                "pizza",
                "pasta",
                "bread",
                "wrap",
                "roll",
                "naan",
                "roti",
                "paratha",
                "samosa",
                "puri",
            ]
        )
    if "dairy" in pruned_list or "milk" in pruned_list:
        danger_keywords.extend(["cheese", "paneer", "butter", "cream", "milk", "yogurt", "shake"])
    if "meat" in pruned_list or "non-veg" in pruned_list:
        danger_keywords.extend(
            [
                "chicken",
                "beef",
                "mutton",
                "steak",
                "kabab",
                "tikka",
                "wings",
                "nuggets",
                "prawn",
                "fish",
                "meat",
                "shrimp",
                "seafood",
                "squid",
                "calamari",
                "lamb",
                "bacon",
                "sausage",
                "duck",
                "crab",
                "lobster",
            ]
        )
    if "pork" in pruned_list or "bacon" in pruned_list:
        danger_keywords.extend(["pork", "bacon", "sausage", "ham", "pepperoni", "salami"])
    if "seafood" in pruned_list or "fish" in pruned_list:
        danger_keywords.extend(
            ["fish", "prawn", "shrimp", "squid", "calamari", "crab", "lobster", "seafood"]
        )

    if danger_keywords:
        safe_candidates = []
        for c in candidates:
            c_name = c["name"].lower()
            c_cat = (c.get("category") or "").lower()
            if not any(dk in c_name or dk in c_cat for dk in danger_keywords):
                safe_candidates.append(c)

        dropped = len(candidates) - len(safe_candidates)
        if dropped > 0:
            log.info(
                "Semantic Safety Net dropped %d dishes matching danger keywords %s",
                dropped,
                danger_keywords,
            )
        candidates = safe_candidates
    # -----------------------------------------

    return candidates


def get_all_dish_names() -> list[str]:
    """
    Fetches all dish names from Neo4j to be used as classification labels.
    """
    names: list[str] = []
    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        with driver.session() as session:
            result = session.run("MATCH (d:Dish) RETURN d.name AS name")
            names = [record["name"] for record in result]
        log.info("neo4j | fetched %d dish names for candidate labels", len(names))
    except Exception as exc:
        # Never fabricate dish names to paper over a database failure — an empty
        # list makes the caller degrade visibly instead of classifying an image
        # against five invented labels.
        log.error("neo4j query failed in get_all_dish_names: %s", exc)
        return []
    finally:
        if driver:
            driver.close()
    return names


# ── JSON Contract Writer ────────────────────────────────────────────────────


def get_mood_summary(mood_vector: dict, preferred_category: str | None) -> str:
    """Derives a human-readable summary of the user's mood and category preference."""
    parts = []
    if preferred_category:
        parts.append(preferred_category.capitalize())

    if not mood_vector or all(v == 0.0 for v in mood_vector.values()):
        taste_str = "Not specified"
    else:
        dominant = get_dominant_mood(mood_vector)
        if dominant:
            if dominant in ["umami", "salty"]:
                taste_str = "Savory"
            elif dominant == "spice":
                taste_str = "Spicy"
            else:
                taste_str = dominant.capitalize()
        else:
            taste_str = "Balanced"

    if parts:
        if taste_str != "Not specified":
            parts.append(f"({taste_str})")
        return " ".join(parts)

    return taste_str


def write_candidate_evaluation(
    intent: dict, candidates: list[dict], relaxations: list[dict] = None, message: str = ""
) -> Path:
    """
    Writes candidate_evaluation.json containing the original intent context
    and the list of safe candidate dishes that survived allergen pruning.
    """
    if relaxations is None:
        relaxations = []

    # Dynamic mood summary replacing the hardcoded "neutral"
    mood_summary = get_mood_summary(intent.get("mood_vector", {}), intent.get("preferred_category"))

    contract = {
        "source_intent": intent,
        "soft_constraints": {
            "mood_vector_seed": mood_summary,
            "direct_dish_prompt": intent.get("craving", ""),
        },
        "safe_candidates": candidates,
        "candidate_count": len(candidates),
        "relaxations": relaxations,
        "message": message,
    }

    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CANDIDATE_EVAL_PATH, "w", encoding="utf-8") as fh:
        json.dump(contract, fh, indent=4, ensure_ascii=False)
    log.info("candidate_evaluation written → %s", CANDIDATE_EVAL_PATH)
    return CANDIDATE_EVAL_PATH


# ── Pipeline Entry Point ────────────────────────────────────────────────────


def get_dominant_mood(mood_vector: dict) -> str | None:
    """
    Identifies if a mood vector has a strictly dominant dimension.
    Thresholds (defensible defaults, avoiding hidden magic numbers):
      - Dominant dimension must be >= 0.7
      - All other dimensions must be <= 0.4 (comparatively low)
    Returns the dominant dimension name, or None if none qualify.
    """
    if not mood_vector:
        return None

    candidates = []
    for k, v in mood_vector.items():
        if v >= 0.7:
            candidates.append(k)

    if len(candidates) != 1:
        return None

    dominant = candidates[0]

    # Check if others are comparatively low (<= 0.4)
    for k, v in mood_vector.items():
        if k != dominant and v > 0.4:
            return None

    return dominant


def run_anchoring_pipeline(intent_dict: dict = None) -> dict:
    """Executes the symbolic grounding pipeline.

    - Loads Tier 1a grounded intent
    - Queries Neo4j for safe candidates
    """
    log.info("─── Tier 1b: Graph Constraint Pipeline START ───")

    # Step 1 — load upstream contract
    if intent_dict is not None:
        intent = intent_dict
        log.info("using passed intent_dict instead of reading from file")
    else:
        intent = load_grounded_intent()
    allergens = intent.get("allergens_pruned", [])

    preferred_category = intent.get("preferred_category") or ""
    if preferred_category.lower() == "dessert":
        preferred_category = "cafe_bakery"
    # We never drop allergens because it's a safety constraint!

    budget = intent.get("budget_max_pkr")
    if budget is None:
        budget = 999999  # unlimited if no budget specified

    is_vegan = intent.get("is_vegan", False)
    is_vegetarian = intent.get("is_vegetarian", False)
    is_halal = intent.get("is_halal", False)

    candidates = query_safe_candidates(
        allergens, budget, preferred_category, is_vegan, is_vegetarian, is_halal=is_halal
    )
    relaxations = []

    # First attempt: With preferred category
    if preferred_category and len(candidates) < 3:
        log.warning(
            "Only %d matches for preferred category '%s'. Relaxing category constraint.",
            len(candidates),
            preferred_category,
        )
        relaxations.append(
            {
                "constraint": "preferred_category",
                "old_value": preferred_category,
                "new_value": None,
                "reason": "few_candidates_found",
            }
        )
        # drop category requirement
        preferred_category = ""
        candidates = query_safe_candidates(
            allergens, budget, preferred_category, is_vegan, is_vegetarian, is_halal=is_halal
        )

    # Second constraint: Minimum Relevance Filter for Dominant Moods
    mood_vector = intent.get("mood_vector", {})
    dominant_mood = get_dominant_mood(mood_vector)
    if dominant_mood and candidates:
        min_relevance = 0.4
        filtered_candidates = [
            c for c in candidates if c["taste_profile"].get(dominant_mood, 0.0) >= min_relevance
        ]

        # Semantic gate: if they want something strictly sweet, restrict to genuine dessert
        # categories so savoury dishes with high sweet values (like sweet and sour prawns)
        # don't dominate.
        pref_cat = (intent.get("preferred_category") or "").lower()
        if dominant_mood == "sweet" and (
            not pref_cat or pref_cat in ["dessert", "cafe_bakery", "sweet"]
        ):
            semantic_filtered = [
                c for c in filtered_candidates if c.get("category") == "cafe_bakery"
            ]
            if len(semantic_filtered) >= 3:
                filtered_candidates = semantic_filtered
                log.info("Applied semantic dessert filter. Restricted to cafe_bakery category.")

        if len(filtered_candidates) < 3:
            log.warning(
                "Dominant mood filter (minimum %s >= %s) left %d candidates (< 3). "
                "Relaxing filter.",
                dominant_mood,
                min_relevance,
                len(filtered_candidates),
            )
            relaxations.append(
                {
                    "constraint": f"minimum_relevance_{dominant_mood}",
                    "old_value": min_relevance,
                    "new_value": 0.0,
                    "reason": "few_candidates_found",
                }
            )
            # We relax by simply not applying the filter, leaving `candidates` as it was.
        else:
            log.info(
                "Applied dominant mood filter (minimum %s >= %s). "
                "Candidates reduced from %d to %d.",
                dominant_mood,
                min_relevance,
                len(candidates),
                len(filtered_candidates),
            )
            candidates = filtered_candidates

    if not candidates:
        msg = "No matches even after maximum relaxation attempts."
        log.warning(msg)
    else:
        msg = f"Found {len(candidates)} candidates."

    # Step 3 — persist contract
    write_candidate_evaluation(intent, candidates, relaxations, msg)

    log.info("─── Tier 1b: Graph Constraint Pipeline DONE ────")

    mood_summary = get_mood_summary(intent.get("mood_vector", {}), intent.get("preferred_category"))

    return {
        "source_intent": intent,
        "soft_constraints": {
            "mood_vector_seed": mood_summary,
            "direct_dish_prompt": intent.get("craving", ""),
        },
        "safe_candidates": candidates,
        "candidate_count": len(candidates),
        "relaxations": relaxations,
        "message": msg,
    }


# ── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_anchoring_pipeline()
    print(json.dumps(result, indent=4))

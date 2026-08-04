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
WHERE d.synthesized_calories <= 1000
  AND d.price_pkr <= $budget_max
  AND NOT EXISTS {
    MATCH (d)-[:CONTAINS*1..5]->(i:Ingredient)
    WHERE toLower(i.name) IN $pruned_list
  }
RETURN d.dish_id AS dish_id, d.name AS name,
       d.price_pkr AS price_pkr, d.protein_g AS protein_g,
       d.calories AS calories,
       d.category AS category, d.image_url AS image_url,
       d.human_tags AS human_tags,
       d.taste_sweet AS taste_sweet, d.taste_salty AS taste_salty,
       d.taste_sour AS taste_sour, d.taste_bitter AS taste_bitter,
       d.taste_umami AS taste_umami, d.taste_spice AS taste_spice
"""


def query_safe_candidates(allergens: list[str], budget_max: int) -> list[dict]:
    """
    Connects to local Neo4j and executes a deterministic Cypher query that:
      - Filters dishes with synthesized_calories <= 1000
      - Prunes any dish linked (up to 5 hops) to a banned ingredient
    Returns a list of {dish_id, name, price_pkr, protein_g, calories} dicts
    for surviving candidates.
    """
    pruned_list = [a.strip().lower() for a in allergens]
    log.info("neo4j query | pruned_list=%s, budget_max=%d", pruned_list, budget_max)

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
        with driver.session() as session:
            result = session.run(PRUNE_CYPHER, pruned_list=pruned_list, budget_max=budget_max)
            for record in result:
                candidates.append(
                    {
                        "dish_id": record["dish_id"],
                        "name": record["name"],
                        "price_pkr": record["price_pkr"],
                        "protein_g": record["protein_g"],
                        "calories": record["calories"],
                        "category": record.get("category", ""),
                        "image_url": record.get("image_url", ""),
                        "human_tags": record.get("human_tags", []),
                        "taste_profile": {
                            "sweet": record.get("taste_sweet", 0.0) or 0.0,
                            "salty": record.get("taste_salty", 0.0) or 0.0,
                            "sour": record.get("taste_sour", 0.0) or 0.0,
                            "bitter": record.get("taste_bitter", 0.0) or 0.0,
                            "umami": record.get("taste_umami", 0.0) or 0.0,
                            "spice": record.get("taste_spice", 0.0) or 0.0,
                        },
                    }
                )
        log.info("neo4j returned %d safe candidates", len(candidates))
    except Exception as exc:
        log.error("neo4j query failed: %s", exc)
        raise
    finally:
        driver.close()

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
        log.error("neo4j query failed in get_all_dish_names: %s", exc)
        # return a fallback list just in case
        return ["pizza", "burger", "biryani", "salad", "pasta"]
    finally:
        if driver:
            driver.close()
    return names


# ── JSON Contract Writer ────────────────────────────────────────────────────


def write_candidate_evaluation(
    intent: dict, candidates: list[dict], relaxations: list[dict] = None, message: str = ""
) -> Path:
    """
    Writes candidate_evaluation.json containing the original intent context
    and the list of safe candidate dishes that survived allergen pruning.
    """
    if relaxations is None:
        relaxations = []

    contract = {
        "source_intent": intent,
        "soft_constraints": {
            "mood_vector_seed": "neutral",
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


def run_anchoring_pipeline() -> dict:
    """
    Full Tier-1b pipeline:
      1. Load grounded_intent.json
      2. Query Neo4j to prune allergens
      3. Write candidate_evaluation.json
    Returns the candidate evaluation dict.
    """
    log.info("─── Tier 1b: Graph Constraint Pipeline START ───")

    # Step 1 — load upstream contract
    intent = load_grounded_intent()
    allergens = intent.get("allergens_pruned", [])

    # We never drop allergens because it's a safety constraint!

    budget = intent.get("budget_max_pkr")
    if budget is None:
        budget = 999999  # unlimited if no budget specified

    candidates = []
    relaxations = []

    # Attempt up to 3 times (1 initial + 2 relaxations)
    for attempt in range(3):
        candidates = query_safe_candidates(allergens, budget)
        if candidates:
            break

        if attempt < 2:
            old_budget = budget
            budget = budget * 1.2
            relaxations.append(
                {
                    "constraint": "budget_max_pkr",
                    "old_value": old_budget,
                    "new_value": budget,
                    "reason": "zero_candidates_found",
                }
            )
            log.warning(
                "0 candidates found. Relaxing budget to %.2f (attempt %d/2)", budget, attempt + 1
            )

    if not candidates:
        msg = "No matches even after maximum relaxation attempts."
        log.warning(msg)
    else:
        msg = f"Found {len(candidates)} candidates."

    # Step 3 — persist contract
    write_candidate_evaluation(intent, candidates, relaxations, msg)

    log.info("─── Tier 1b: Graph Constraint Pipeline DONE ────")

    return {
        "source_intent": intent,
        "safe_candidates": candidates,
        "candidate_count": len(candidates),
        "relaxations": relaxations,
        "message": msg,
    }


# ── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_anchoring_pipeline()
    print(json.dumps(result, indent=4))

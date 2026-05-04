"""
Tier 1 — Graph Constraint Pipeline
Reads grounded_intent.json, queries Neo4j to prune allergens, and emits
candidate_evaluation.json with the surviving safe dish nodes.
"""

import json
import logging
from pathlib import Path

from neo4j import GraphDatabase

# ── Config ──────────────────────────────────────────────────────────────────
CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"
GROUNDED_INTENT_PATH = CONTRACTS_DIR / "grounded_intent.json"
CANDIDATE_EVAL_PATH = CONTRACTS_DIR / "candidate_evaluation.json"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "Mood4Food")

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
  AND NOT EXISTS {
    MATCH (d)-[:CONTAINS*1..5]->(i:Ingredient)
    WHERE toLower(i.name) IN $pruned_list
  }
RETURN d.dish_id AS dish_id, d.name AS name,
       d.price_pkr AS price_pkr, d.protein_g AS protein_g,
       d.calories AS calories
"""


def query_safe_candidates(allergens: list[str], budget_max: int) -> list[dict]:
    """
    Connects to local Neo4j and executes a deterministic Cypher query that:
      - Filters dishes with synthesized_calories <= 1000
      - Prunes any dish linked (up to 5 hops) to a banned ingredient
    Returns a list of {dish_id, name, price_pkr, protein_g, calories} dicts for surviving candidates.
    """
    pruned_list = [a.strip().lower() for a in allergens]
    log.info("neo4j query | pruned_list=%s, budget_max=%d", pruned_list, budget_max)

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    candidates: list[dict] = []

    try:
        driver.verify_connectivity()
        log.info("neo4j connection verified at %s", NEO4J_URI)

        with driver.session() as session:
            result = session.run(PRUNE_CYPHER, pruned_list=pruned_list)
            for record in result:
                candidates.append({
                    "dish_id": record["dish_id"],
                    "name": record["name"],
                    "price_pkr": record["price_pkr"],
                    "protein_g": record["protein_g"],
                    "calories": record["calories"],
                })
        log.info("neo4j returned %d safe candidates", len(candidates))
    except Exception as exc:
        log.error("neo4j query failed: %s", exc)
        raise
    finally:
        driver.close()

    return candidates


# ── JSON Contract Writer ────────────────────────────────────────────────────

def write_candidate_evaluation(intent: dict, candidates: list[dict]) -> Path:
    """
    Writes candidate_evaluation.json containing the original intent context
    and the list of safe candidate dishes that survived allergen pruning.
    """
    contract = {
        "source_intent": {
            "budget_max_pkr": intent["hard_constraints"]["budget_max_pkr"],
            "allergens_pruned": intent["hard_constraints"]["allergens_pruned"],
        },
        "soft_constraints": intent["soft_constraints"],
        "safe_candidates": candidates,
        "candidate_count": len(candidates),
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
    allergens = intent["hard_constraints"]["allergens_pruned"]
    budget = intent["hard_constraints"]["budget_max_pkr"]

    # Step 2 — deterministic graph query
    candidates = query_safe_candidates(allergens, budget)

    # Step 3 — persist contract
    write_candidate_evaluation(intent, candidates)

    log.info("─── Tier 1b: Graph Constraint Pipeline DONE ────")

    return {
        "source_intent": intent,
        "safe_candidates": candidates,
        "candidate_count": len(candidates),
    }


# ── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_anchoring_pipeline()
    print(json.dumps(result, indent=4))

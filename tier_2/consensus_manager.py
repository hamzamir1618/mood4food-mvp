"""
Tier 2 — Multi-Agent Debate Pipeline
Reads candidate_evaluation.json, runs a Nash-equilibrium-style weighted
utility aggregation with constraint relaxation, and emits decision_blueprint.json.
"""

import json
import logging
import math
from pathlib import Path

from tier_2.agents import (
    calculate_budget_utility,
    calculate_health_utility,
    calculate_taste_utility,
    get_vector_store,
    retrieve_dish_vector,
    retrieve_mood_vector,
)

# ── Config ──────────────────────────────────────────────────────────────────
CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "tier_1" / "contracts"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "tier_1" / "contracts"  # shared contracts dir
CANDIDATE_EVAL_PATH = CONTRACTS_DIR / "candidate_evaluation.json"
DECISION_BLUEPRINT_PATH = OUTPUT_DIR / "decision_blueprint.json"

# Initial agent weights (must sum to 1.0)
W_HEALTH = 0.4
W_BUDGET = 0.3
W_TASTE = 0.3

# Constraint relaxation
RELAXATION_STEP = 0.1
MIN_BUDGET_WEIGHT = 0.0
MAX_RELAXATION_ROUNDS = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ── Contract Loader ─────────────────────────────────────────────────────────

def load_candidate_evaluation() -> dict:
    """Reads candidate_evaluation.json produced by Tier 1b."""
    if not CANDIDATE_EVAL_PATH.exists():
        raise FileNotFoundError(
            f"candidate_evaluation.json not found at {CANDIDATE_EVAL_PATH}. "
            "Run symbolic_anchoring.py first."
        )
    with open(CANDIDATE_EVAL_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    log.info("loaded candidate_evaluation — %d candidates", data.get("candidate_count", 0))
    return data


# ── Utility Scorer ──────────────────────────────────────────────────────────

def score_candidate(candidate: dict,
                    mood_vector: list[float],
                    budget_max: int,
                    dish_collection) -> dict:
    """
    Computes U_h, U_b, U_t for a single candidate dish.
    Returns a dict with individual utilities and metadata.
    """
    dish_id = candidate.get("dish_id", "unknown")
    name = candidate.get("name", "unnamed")

    # ── Health utility ──
    dish_data = {
        "protein_g": candidate.get("protein_g", 15.0),
        "calories": candidate.get("calories", 500.0),
    }
    u_health = calculate_health_utility(dish_data)

    # ── Budget utility ──
    price = candidate.get("price_pkr", 0.0)
    u_budget = calculate_budget_utility(price, budget_max)

    # ── Taste utility ──
    dish_vector = candidate.get("embedding", [])
    if not dish_vector and dish_collection is not None:
        dish_vector = retrieve_dish_vector(dish_collection, str(dish_id))
    u_taste = calculate_taste_utility(dish_vector, mood_vector) if dish_vector and mood_vector else 0.5

    return {
        "dish_id": dish_id,
        "name": name,
        "u_health": round(u_health, 6),
        "u_budget": round(u_budget, 6),
        "u_taste": round(u_taste, 6),
        "price_pkr": price,
    }


# ── Nash Equilibrium Aggregation with Constraint Relaxation ─────────────────

def run_debate(candidates: list[dict],
               mood_vector: list[float],
               budget_max: int,
               dish_collection=None) -> dict:
    """
    Weighted utility aggregation loop:
      U_total = (w_h * U_h) + (w_b * U_b) + (w_t * U_t)

    If max U_total == 0 after scoring, auto-degrades w_b by 0.1 and re-runs.
    Returns the winning dish, its utility breakdown, and XAI traces.
    """
    w_h = W_HEALTH
    w_b = W_BUDGET
    w_t = W_TASTE

    xai_traces: list[str] = []
    relaxation_round = 0
    winner = None

    while relaxation_round <= MAX_RELAXATION_ROUNDS:
        xai_traces.append(
            f"round_{relaxation_round}: weights w_h={w_h:.2f} w_b={w_b:.2f} w_t={w_t:.2f}"
        )
        log.info("debate round %d | w_h=%.2f w_b=%.2f w_t=%.2f",
                 relaxation_round, w_h, w_b, w_t)

        scored: list[dict] = []
        for cand in candidates:
            sc = score_candidate(cand, mood_vector, budget_max, dish_collection)
            u_total = (w_h * sc["u_health"]) + (w_b * sc["u_budget"]) + (w_t * sc["u_taste"])
            sc["u_total"] = round(u_total, 6)
            scored.append(sc)

            xai_traces.append(
                f"  {sc['name']} → U_h={sc['u_health']:.4f} "
                f"U_b={sc['u_budget']:.4f} U_t={sc['u_taste']:.4f} "
                f"| U_total={sc['u_total']:.4f}"
            )

        # Find the winner
        if scored:
            best = max(scored, key=lambda x: x["u_total"])
            if best["u_total"] > 0.0:
                winner = best
                winner["all_scores"] = [dict(s) for s in scored]
                xai_traces.append(
                    f"winner: {best['name']} (U_total={best['u_total']:.4f})"
                )
                log.info("winner elected: %s (U_total=%.4f)", best["name"], best["u_total"])
                break

        # ── Constraint relaxation: degrade budget weight ──
        xai_traces.append(
            f"round_{relaxation_round}: all U_total=0 — relaxing w_b by {RELAXATION_STEP}"
        )
        log.warning("all utilities zero — relaxing budget weight")
        w_b = max(MIN_BUDGET_WEIGHT, w_b - RELAXATION_STEP)

        # Redistribute freed weight equally to health and taste
        freed = W_BUDGET - w_b  # total freed so far
        w_h = W_HEALTH + (freed / 2.0)
        w_t = W_TASTE + (freed / 2.0)

        relaxation_round += 1

    if winner is None:
        xai_traces.append("FALLBACK: no winner after max relaxation — selecting first candidate")
        log.warning("no winner found after relaxation — falling back to first candidate")
        if scored:
            winner = scored[0]
            winner["all_scores"] = scored
        else:
            winner = {
                "dish_id": "none",
                "name": "no_candidates",
                "u_health": 0.0,
                "u_budget": 0.0,
                "u_taste": 0.0,
                "u_total": 0.0,
                "all_scores": [],
            }

    return {
        "winner": winner,
        "final_weights": {"w_h": round(w_h, 4), "w_b": round(w_b, 4), "w_t": round(w_t, 4)},
        "relaxation_rounds": relaxation_round,
        "xai_traces": xai_traces,
    }


# ── JSON Contract Writer ────────────────────────────────────────────────────

def write_decision_blueprint(debate_result: dict, intent_context: dict) -> Path:
    """
    Writes decision_blueprint.json with the winning dish, utility breakdown,
    XAI traces, and the originating intent context.
    """
    winner = debate_result["winner"]
    blueprint = {
        "winning_dish": {
            "dish_id": winner["dish_id"],
            "name": winner["name"],
            "price_pkr": winner.get("price_pkr", 0),
        },
        "utility_breakdown": {
            "u_health": winner["u_health"],
            "u_budget": winner["u_budget"],
            "u_taste": winner["u_taste"],
            "u_total": winner["u_total"],
        },
        "agent_weights": debate_result["final_weights"],
        "relaxation_rounds": debate_result["relaxation_rounds"],
        "xai_traces": debate_result["xai_traces"],
        "all_candidate_scores": winner.get("all_scores", []),
        "source_context": {
            "budget_max_pkr": intent_context.get("budget_max_pkr", 0),
            "allergens_pruned": intent_context.get("allergens_pruned", []),
            "mood_vector_seed": intent_context.get("mood_vector_seed", "neutral"),
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(DECISION_BLUEPRINT_PATH, "w", encoding="utf-8") as fh:
        json.dump(blueprint, fh, indent=4, ensure_ascii=False)
    log.info("decision_blueprint written → %s", DECISION_BLUEPRINT_PATH)
    return DECISION_BLUEPRINT_PATH


# ── Pipeline Entry Point ────────────────────────────────────────────────────

def run_debate_pipeline() -> dict:
    """
    Full Tier-2b pipeline:
      1. Load candidate_evaluation.json
      2. Initialise ChromaDB (best-effort; runs without vectors)
      3. Run Nash-equilibrium debate with constraint relaxation
      4. Write decision_blueprint.json
    """
    log.info("─── Tier 2b: Multi-Agent Debate Pipeline START ───")

    # Step 1 — load upstream contract
    evaluation = load_candidate_evaluation()
    candidates = evaluation.get("safe_candidates", [])
    budget_max = evaluation.get("source_intent", {}).get("budget_max_pkr", 1000)
    mood_seed = evaluation.get("soft_constraints", {}).get("mood_vector_seed", "neutral")

    # Step 2 — Vector store (best-effort — pipeline still works without embeddings)
    vector_store = None
    mood_vector: list[float] = []
    try:
        vector_store = get_vector_store()
        mood_vector = retrieve_mood_vector(vector_store, mood_seed)
    except Exception as exc:
        log.warning("vector store unavailable, proceeding without vectors: %s", exc)

    # Step 3 — debate
    debate_result = run_debate(candidates, mood_vector, budget_max, vector_store)

    # Step 4 — persist contract
    intent_context = {
        "budget_max_pkr": budget_max,
        "allergens_pruned": evaluation.get("source_intent", {}).get("allergens_pruned", []),
        "mood_vector_seed": mood_seed,
    }
    write_decision_blueprint(debate_result, intent_context)

    log.info("─── Tier 2b: Multi-Agent Debate Pipeline DONE ────")
    return debate_result


# ── Standalone execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_debate_pipeline()
    print(json.dumps(result, indent=4, default=str))

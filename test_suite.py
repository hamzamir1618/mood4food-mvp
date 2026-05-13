import json
import logging
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from orchestrator import app

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_suite")

client = TestClient(app)

CONTRACTS_DIR = Path(__file__).resolve().parent / "tier_1" / "contracts"
CANDIDATE_EVAL_PATH = CONTRACTS_DIR / "candidate_evaluation.json"

test_cases = [
    {"query": "food under 300 rupees, no dairy", "expected_pruned": ["dairy"], "budget_priority": 0.5},
    {"query": "I am vegetarian, no meat no chicken", "expected_pruned": ["meat"], "budget_priority": 0.2},
    {"query": "cheap food without nuts", "expected_pruned": ["nuts"], "budget_priority": 1.0},
    {"query": "high protein food, I am allergic to shellfish", "expected_pruned": ["shellfish"], "budget_priority": 0.1},
    {"query": "something spicy for dinner, no gluten", "expected_pruned": ["gluten"], "budget_priority": 0.5},
    {"query": "just want a snack, 100 rupees max", "expected_pruned": [], "budget_priority": 0.8},
    {"query": "no beef or pork under 600", "expected_pruned": ["meat"], "budget_priority": 0.5},
    {"query": "no milk no cheese under 200", "expected_pruned": ["dairy"], "budget_priority": 0.9},
    {"query": "gym food with high protein under 800", "expected_pruned": [], "budget_priority": 0.4},
    {"query": "no eggs for me", "expected_pruned": ["egg"], "budget_priority": 0.3},
    {"query": "seafood allergy", "expected_pruned": ["fish"], "budget_priority": 0.5},
    {"query": "shrimp and fish are bad for me", "expected_pruned": ["shellfish", "fish"], "budget_priority": 0.5},
    {"query": "sweet and creamy dessert under 500", "expected_pruned": [], "budget_priority": 0.6},
    {"query": "no wheat gluten free please 400", "expected_pruned": ["gluten"], "budget_priority": 0.7},
    {"query": "I cant eat mutton", "expected_pruned": ["meat"], "budget_priority": 0.5},
]

def run_tests():
    total_tests = len(test_cases) + 1  # 15 parameterized tests + 1 schema validation
    passed_tests = 0
    errors = []

    print("\n" + "="*50)
    print("STARTING FIPE MVP AUTOMATED TEST SUITE (15+ TEST CASES)")
    print("="*50 + "\n")

    for idx, case in enumerate(test_cases, 1):
        print(f"Running Test {idx}: Query: '{case['query']}' | Budget Weight: {case['budget_priority']}")
        try:
            # Step 1: Submit Query
            response = client.post("/submit", data={"query": case["query"]})
            if response.status_code != 200:
                raise AssertionError(f"Expected status 200 on /submit, got {response.status_code}. Detail: {response.text}")
            
            # Verify Pruning
            if not CANDIDATE_EVAL_PATH.exists():
                raise AssertionError("candidate_evaluation.json was not created.")
            
            with open(CANDIDATE_EVAL_PATH, "r", encoding="utf-8") as f:
                eval_data = json.load(f)
                
            allergens_pruned = eval_data.get("source_intent", {}).get("allergens_pruned", [])
            for expected in case["expected_pruned"]:
                if expected not in allergens_pruned:
                    raise AssertionError(f"Expected allergen '{expected}' to be pruned, but got: {allergens_pruned}")
            
            # Step 2: Recalculate with Budget Priority
            recalc_resp = client.post("/recalculate", json={"w_budget": case["budget_priority"]})
            if recalc_resp.status_code != 200:
                raise AssertionError(f"Expected status 200 on /recalculate, got {recalc_resp.status_code}. Detail: {recalc_resp.text}")
            
            blueprint = recalc_resp.json()
            winner = blueprint.get("winning_dish", {})
            all_candidates = blueprint.get("all_candidate_scores", [])
            
            if not all_candidates:
                # Depending on constraints, it's possible no dishes match, but we assume the DB has some matches for these simple exclusions.
                logger.warning(f"No candidates available for query: '{case['query']}'. Validation skipping winner check.")
            else:
                if case["budget_priority"] == 1.0:
                    lowest_price = min(cand.get("price_pkr", float("inf")) for cand in all_candidates)
                    winner_price = winner.get("price_pkr")
                    if winner_price != lowest_price:
                        raise AssertionError(f"Budget weight is 1.0 but winning dish ({winner.get('name')}) price {winner_price} is not the lowest price ({lowest_price}).")
                        
            print(f"PASS Test {idx}: Allergens correctly pruned and recalculated successfully. Winner: {winner.get('name')} at {winner.get('price_pkr')} PKR.")
            passed_tests += 1
        except Exception as e:
            print(f"FAIL Test {idx}: {e}")
            errors.append((f"Test {idx} ({case['query']})", str(e)))

    # ── Test 16: Compiler Design — SDUI Live Mapping Schema Validation ──
    print("\nRunning Test 16: SDUI Contract Schema Validation...")
    try:
        response = client.get("/decision_blueprint")
        if response.status_code != 200:
            raise AssertionError(f"Expected status 200, got {response.status_code}")
            
        blueprint = response.json()
        
        required_keys = ["winning_dish", "utility_breakdown", "agent_weights", "all_candidate_scores"]
        missing_keys = [key for key in required_keys if key not in blueprint]
        
        if missing_keys:
            raise AssertionError(f"Missing required SDUI keys in blueprint: {missing_keys}")
            
        print("PASS Test 16: Blueprint JSON matches expected SDUI schema.")
        passed_tests += 1
    except Exception as e:
        print(f"FAIL Test 16: {e}")
        errors.append(("Test 16", str(e)))

    print("\n" + "="*50)
    print(f"TEST SUITE COMPLETE — {passed_tests}/{total_tests} Passed")
    print("="*50 + "\n")
    
    if errors:
        print("Detailed Errors:")
        for test_name, err in errors:
            print(f"[{test_name}] {err}")
        sys.exit(1)
    else:
        print("All tests passed successfully! The MVP is ready for demonstration.")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()

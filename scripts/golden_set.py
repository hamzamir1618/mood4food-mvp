"""
Golden set for the decision core (Phase 3).

    python -m scripts.golden_set --label baseline
    python -m scripts.golden_set --label v3 --compare baseline

Runs realistic queries through Tier 1 (the real Neo4j data) and Tier 2, then checks
each winner against the query using the dish's own record in Neo4j:
  - safety, always: the budget ceiling, excluded allergens, vegan, vegetarian, halal
  - relevance, where the query asks for something specific: a biryani for "biryani",
    fish or prawns for "seafood", a protein-dense dish for the gym, and so on

Intents are written the way the intent extractor produces them, so extraction quality
doesn't affect the result. Each case can also carry a persona and goal, saved as the
session's scoring context. Results go to data/golden/<label>.json (git-ignored).
"""

import argparse
import json
import logging
import sys

import fakeredis
from neo4j import GraphDatabase

from config import settings
from pipeline import paths
from tier_1.contracts import session_store
from tier_1.contracts.schemas import GroundedIntent

GOLDEN_DIR = paths.DATA_DIR / "golden"
MEALS = {
    "desi_traditional",
    "afghan",
    "middle_eastern",
    "chinese_asian",
    "continental_upscale",
    "fast_food",
    "pizza",
    "sandwich",
    "other",
}
SEAFOOD = ("fish", "prawns", "crab", "lobster", "squid")


# ── Checks on the winning dish's Neo4j record ────────────────────────────────
def _protein_density(d: dict) -> float | None:
    if not d.get("calories") or d.get("protein_g") is None:
        return None
    return 100 * d["protein_g"] / d["calories"]


def taste_at_least(dim: str, value: float):
    return (f"{dim} ≥ {value}", lambda d: (d.get(f"taste_{dim}") or 0) >= value)


def category_is(*cats: str):
    return (f"category in {cats}", lambda d: d.get("category") in cats)


def name_has(word: str):
    return (f"name contains '{word}'", lambda d: word in (d.get("name") or "").lower())


def has_ingredient(*names: str):
    return (
        f"ingredients include {names}",
        lambda d: bool(set(names) & set(d.get("ingredients") or [])),
    )


def has_allergen(tag: str):
    return (f"allergens include {tag}", lambda d: tag in (d.get("allergens") or []))


def is_meal():
    return ("a meal, not a dessert or snack", lambda d: d.get("category") in MEALS)


def protein_dense(min_g_per_100kcal: float):
    return (
        f"protein ≥ {min_g_per_100kcal} g per 100 kcal",
        lambda d: (_protein_density(d) or 0) >= min_g_per_100kcal,
    )


def calories_at_most(kcal: float):
    return (
        f"calories known and ≤ {kcal}",
        lambda d: bool(d.get("calories")) and d["calories"] <= kcal,
    )


def safety_checks(intent: dict) -> list:
    checks = []
    if intent.get("budget_max_pkr"):
        b = intent["budget_max_pkr"]
        checks.append((f"price ≤ Rs {b:.0f}", lambda d: (d.get("price_rs") or 0) <= b))
    for a in intent.get("allergens_pruned") or []:
        checks.append(
            (
                f"no {a}, and allergens known",
                lambda d, a=a: d.get("allergens") is not None and a not in d["allergens"],
            )
        )
    if intent.get("is_vegan"):
        checks.append(("vegan", lambda d: bool(d.get("is_vegan"))))
    if intent.get("is_vegetarian"):
        checks.append(("vegetarian", lambda d: bool(d.get("is_vegetarian"))))
    if intent.get("is_halal"):
        checks.append(("halal", lambda d: d.get("is_halal", True) is not False))
    checks.append(("not quarantined", lambda d: not d.get("quarantined")))
    return checks


# ── Cases ────────────────────────────────────────────────────────────────────
def case(cid, query, intent, expect=(), persona="balanced", goal=None):
    return {
        "id": cid,
        "query": query,
        "intent": intent,
        "expect": list(expect),
        "context": {"persona": persona, "goal": goal},
    }


CASES = [
    case(
        "sweet",
        "something sweet",
        {
            "mood_vector": {"sweet": 1.0},
            "craving": "something sweet",
            "preferred_category": "dessert",
            "preferred_category_raw_phrase": "sweet",
        },
        [taste_at_least("sweet", 0.6), category_is("cafe_bakery")],
    ),
    case(
        "spicy_desi",
        "spicy desi food under 1000",
        {
            "mood_vector": {"spice": 0.9},
            "budget_max_pkr": 1000.0,
            "craving": "spicy desi food",
            "preferred_category": "desi",
        },
        [taste_at_least("spice", 0.6), category_is("desi_traditional")],
    ),
    case(
        "gym",
        "i need a heavy protein meal for the gym",
        {"craving": "heavy protein meal", "mood_vector": {"umami": 0.6}},
        [protein_dense(6.0), is_meal()],
        persona="gym_bro",
        goal="muscle_gain",
    ),
    case(
        "cheap_lunch",
        "cheap lunch under 500",
        {"budget_max_pkr": 500.0, "craving": "cheap lunch"},
        [is_meal()],
    ),
    case(
        "veg_dinner",
        "vegetarian dinner under 1500",
        {"is_vegetarian": True, "budget_max_pkr": 1500.0, "craving": "vegetarian dinner"},
        [is_meal()],
    ),
    case(
        "allergic_chinese",
        "I'm allergic to nuts and dairy, something chinese",
        {
            "allergens_pruned": ["nuts", "dairy"],
            "craving": "something chinese",
            "preferred_category": "chinese",
            "preferred_category_raw_phrase": "chinese",
        },
        [category_is("chinese_asian")],
    ),
    case(
        "biryani",
        "biryani please",
        {
            "craving": "biryani",
            "preferred_category": "biryani",
            "preferred_category_raw_phrase": "biryani",
        },
        [name_has("biryani")],
    ),
    case(
        "dairy",
        "something with dairy",
        {
            "craving": "something with dairy",
            "preferred_category": "dairy",
            "preferred_category_raw_phrase": "dairy",
        },
        [has_allergen("dairy")],
    ),
    case(
        "salad",
        "a light healthy salad",
        {
            "craving": "light healthy salad",
            "preferred_category": "salad",
            "preferred_category_raw_phrase": "salad",
            "mood_vector": {"sour": 0.3},
        },
        [name_has("salad"), calories_at_most(600)],
        persona="health_nut",
        goal="light",
    ),
    case(
        "pizza",
        "pizza for 4 people under 5000",
        {
            "budget_max_pkr": 5000.0,
            "craving": "pizza",
            "preferred_category": "pizza",
            "preferred_category_raw_phrase": "pizza",
        },
        [category_is("pizza")],
    ),
    case(
        "halal_fast_food",
        "halal fast food",
        {
            "is_halal": True,
            "craving": "halal fast food",
            "preferred_category": "fast food",
            "preferred_category_raw_phrase": "fast food",
        },
        [category_is("fast_food")],
    ),
    case(
        "comfort",
        "comfort food",
        {"mood_vector": {"salty": 0.5, "umami": 0.8}, "craving": "comfort food"},
        [taste_at_least("umami", 0.5), is_meal()],
        persona="comfort_seeker",
    ),
    case(
        "sour",
        "something sour and tangy",
        {"mood_vector": {"sour": 0.9}, "craving": "something sour and tangy"},
        [taste_at_least("sour", 0.5)],
    ),
    case("vegan", "I'm vegan", {"is_vegan": True, "craving": "vegan"}, [is_meal()]),
    case(
        "seafood",
        "I want seafood",
        {
            "craving": "I want seafood",
            "preferred_category": "seafood",
            "preferred_category_raw_phrase": "seafood",
        },
        [has_ingredient(*SEAFOOD)],
    ),
    case(
        "no_meat_spicy",
        "no meat, something spicy",
        {"is_vegetarian": True, "mood_vector": {"spice": 0.8}, "craving": "something spicy"},
        [taste_at_least("spice", 0.5)],
    ),
    case(
        "cake",
        "coffee and cake",
        {
            "craving": "cake",
            "preferred_category": "cake",
            "preferred_category_raw_phrase": "cake",
            "mood_vector": {"sweet": 0.7, "bitter": 0.3},
        },
        [name_has("cake")],
    ),
    case(
        "gluten_free",
        "gluten free please",
        {"allergens_pruned": ["gluten"], "craving": "gluten free"},
        [is_meal()],
    ),
    case(
        "afghan",
        "afghan food",
        {
            "craving": "afghan food",
            "preferred_category": "afghan",
            "preferred_category_raw_phrase": "afghan",
        },
        [category_is("afghan")],
    ),
    case("under_300", "anything under 300", {"budget_max_pkr": 300.0, "craving": "anything"}),
    case(
        "chicken",
        "something with chicken",
        {
            "craving": "something with chicken",
            "preferred_category": "chicken",
            "preferred_category_raw_phrase": "chicken",
        },
        [has_ingredient("chicken")],
    ),
    case(
        "weight_loss",
        "something filling but low calorie",
        {"craving": "filling but low calorie"},
        [calories_at_most(600), is_meal()],
        persona="health_nut",
        goal="weight_loss",
    ),
]


# ── Runner ───────────────────────────────────────────────────────────────────
def _dish(driver, dish_id: str) -> dict:
    records, _, _ = driver.execute_query("MATCH (d:Dish {dish_uid: $id}) RETURN d", {"id": dish_id})
    return dict(records[0]["d"]) if records else {}


def run_case(c: dict, driver) -> dict:
    from tier_1.contracts.session_store import load_contract, save_contract
    from tier_1.symbolic_anchoring import run_anchoring_pipeline
    from tier_2.consensus_manager import run_debate_pipeline

    session = f"golden-{c['id']}"
    intent = {**GroundedIntent().model_dump(), "raw_input": c["query"], **c["intent"]}
    evaluation = run_anchoring_pipeline(intent)
    save_contract(session, "candidate_evaluation", evaluation)
    save_contract(session, "scoring_context", c["context"])
    run_debate_pipeline(session)
    bp = load_contract(session, "decision_blueprint")
    bp = bp.model_dump() if hasattr(bp, "model_dump") else bp

    winner = bp.get("winning_dish") or {}
    d = _dish(driver, winner["dish_id"]) if winner.get("dish_id") else {}
    checks = [
        {"check": desc, "kind": kind, "passed": bool(d) and bool(fn(d))}
        for kind, group in (("safety", safety_checks(intent)), ("relevance", c["expect"]))
        for desc, fn in group
    ]
    density = _protein_density(d) if d else None
    return {
        "id": c["id"],
        "query": c["query"],
        "candidates": evaluation.get("candidate_count", len(evaluation.get("safe_candidates", []))),
        "winner": {
            "name": d.get("name"),
            "restaurant": d.get("restaurant_name"),
            "price_rs": d.get("price_rs"),
            "category": d.get("category"),
            "calories": d.get("calories"),
            "protein_g": d.get("protein_g"),
            "protein_per_100kcal": round(density, 1) if density else None,
        },
        "scores": bp.get("utility_breakdown"),
        "top5": [t.get("name") for t in bp.get("top_candidates", [])],
        "checks": checks,
    }


def _summary(results: list[dict]) -> tuple[int, int, int, int]:
    safety = [c for r in results for c in r["checks"] if c["kind"] == "safety"]
    relevance = [c for r in results for c in r["checks"] if c["kind"] == "relevance"]
    return (
        sum(c["passed"] for c in safety),
        len(safety),
        sum(c["passed"] for c in relevance),
        len(relevance),
    )


def main():
    parser = argparse.ArgumentParser(description="Run the decision-core golden set.")
    parser.add_argument("--label", required=True, help="name for this run, e.g. baseline")
    parser.add_argument("--compare", help="label of an earlier run to compare against")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    logging.disable(logging.WARNING)
    session_store._redis_client = fakeredis.FakeRedis(decode_responses=True)

    driver = GraphDatabase.driver(
        settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    try:
        results = [run_case(c, driver) for c in CASES]
    finally:
        driver.close()

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    (GOLDEN_DIR / f"{args.label}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    before = {}
    if args.compare:
        before = {
            r["id"]: r for r in json.loads((GOLDEN_DIR / f"{args.compare}.json").read_text("utf-8"))
        }
    for r in results:
        w = r["winner"]
        failed = [c["check"] for c in r["checks"] if not c["passed"]]
        price = f"Rs {w['price_rs'] or 0:>6.0f}"
        line = f"{r['id']:17} {str(w['name'])[:34]:34} {price}  {str(w['category']):19}"
        line += "  ok" if not failed else f"  FAILED: {'; '.join(failed)}"
        print(line)
        if r["id"] in before:
            b = before[r["id"]]
            b_failed = sum(not c["passed"] for c in b["checks"])
            print(f"{'':17} was: {str(b['winner']['name'])[:34]:34} ({b_failed} failed)")
    s_ok, s_n, r_ok, r_n = _summary(results)
    print(f"\n{args.label}: safety {s_ok}/{s_n}, relevance {r_ok}/{r_n}")
    if before:
        s_ok, s_n, r_ok, r_n = _summary(list(before.values()))
        print(f"{args.compare}: safety {s_ok}/{s_n}, relevance {r_ok}/{r_n}")


if __name__ == "__main__":
    main()

"""
Seed Neo4j from the v2 dataset (Phase 1).

Reads data/dishes_v2.csv — build it first with `python -m pipeline.build_dataset`
— and writes one :Restaurant node per restaurant and one :Dish node per dish,
joined by [:SERVES]. Dishes are keyed by dish_uid, which stays the same across
re-seeds, so anything that refers to a dish later (history, learned
preferences) keeps pointing at the same one.

    python -m pipeline.seed --reset     # wipe the graph first (destructive)
    python -m pipeline.seed             # upsert without deleting

Quarantined dishes are written too, with quarantined = true, so they stay on
file; the recommendation query leaves them out. Allergens are written as null
when unknown, so a dish we know nothing about is never offered to someone who
has excluded an allergen (see tier_1/symbolic_anchoring.py).
"""

import argparse
import csv
import json
import sys

from neo4j import GraphDatabase

from config import settings
from pipeline import paths

BATCH_SIZE = 500
BOOLS = ("allergens_known", "is_vegan", "is_vegetarian", "is_halal", "quarantined")
FLOATS = (
    "price_rs",
    "price_per_person",
    "restaurant_lat",
    "restaurant_lng",
    "calories",
    "protein_g",
    "carbs_g",
    "fat_g",
    "taste_sweet",
    "taste_salty",
    "taste_sour",
    "taste_bitter",
    "taste_umami",
    "taste_spice",
)
INTS = ("serves_min", "serves_max")
LISTS = (
    "ingredients",
    "ingredients_named",
    "ingredients_typical",
    "allergens",
    "nutrition_defaults",
)
TEXT = (
    "raw_dish_name",
    "name_status",
    "category",
    "category_source",
    "category_before",
    "price_status",
    "price_note",
    "serves_source",
    "included_items",
    "ingredients_basis",
    "halal_note",
    "nutrition_confidence",
    "nutrition_flag",
    "taste_source",
    "review_status",
    "entry_method",
    "source",
    "source_date",
    "quarantine_reason",
    "restaurant_name",
    "restaurant_area",
    "location_precision",
)

CONSTRAINTS = (
    "CREATE CONSTRAINT dish_uid IF NOT EXISTS FOR (d:Dish) REQUIRE d.dish_uid IS UNIQUE",
    "CREATE CONSTRAINT restaurant_name IF NOT EXISTS FOR (r:Restaurant) REQUIRE r.name IS UNIQUE",
)
UPSERT = """
UNWIND $batch AS row
MERGE (r:Restaurant {name: row.restaurant.name})
SET r.address = row.restaurant.address, r.lat = row.restaurant.lat, r.lng = row.restaurant.lng,
    r.area = row.restaurant.area, r.location_precision = row.restaurant.precision
MERGE (d:Dish {dish_uid: row.dish_uid})
SET d += row.props
MERGE (r)-[:SERVES]->(d)
"""


def _float(v):
    try:
        return float(v) if v not in ("", None) else None
    except ValueError:
        return None


def to_record(row: dict) -> dict:
    """One dataset row as Neo4j properties. Empty values become null, so they are not stored."""
    props = {"name": row["dish_name"]}
    props.update({k: (row[k] or None) for k in TEXT})
    props.update({k: row[k] == "True" for k in BOOLS})
    props.update({k: _float(row[k]) for k in FLOATS})
    props.update({k: int(row[k]) if row[k] else None for k in INTS})
    props.update({k: json.loads(row[k] or "[]") for k in LISTS})
    if not props["allergens_known"]:
        props["allergens"] = None  # unknown, not "none"
    return {
        "dish_uid": row["dish_uid"],
        "restaurant": {
            "name": row["restaurant_name"],
            "address": row["restaurant_address"] or None,
            "lat": _float(row["restaurant_lat"]),
            "lng": _float(row["restaurant_lng"]),
            "area": row["restaurant_area"] or None,
            "precision": row["location_precision"] or None,
        },
        "props": props,
    }


def seed(reset: bool) -> dict:
    if not paths.DATASET_CSV.exists():
        sys.exit(f"{paths.DATASET_CSV} not found. Build it first: python -m pipeline.build_dataset")
    with open(paths.DATASET_CSV, encoding="utf-8") as f:
        records = [to_record(r) for r in csv.DictReader(f)]

    driver = GraphDatabase.driver(
        settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    try:
        with driver.session() as session:
            if reset:
                session.run("MATCH (n) DETACH DELETE n").consume()
            for statement in CONSTRAINTS:
                session.run(statement).consume()
            for i in range(0, len(records), BATCH_SIZE):
                session.run(UPSERT, batch=records[i : i + BATCH_SIZE]).consume()
            counts = (
                session.run(
                    """
                MATCH (d:Dish)
                RETURN count(d) AS dishes,
                       sum(CASE WHEN d.quarantined THEN 1 ELSE 0 END) AS quarantined,
                       sum(CASE WHEN d.allergens IS NULL THEN 1 ELSE 0 END) AS allergens_unknown
                """
                )
                .single()
                .data()
            )
            counts["restaurants"] = session.run(
                "MATCH (r:Restaurant) RETURN count(r) AS c"
            ).single()["c"]
    finally:
        driver.close()
    return counts


def main():
    parser = argparse.ArgumentParser(description="Seed Neo4j from data/dishes_v2.csv.")
    parser.add_argument(
        "--reset", action="store_true", help="delete every node first (destructive)"
    )
    args = parser.parse_args()
    counts = seed(args.reset)
    print(
        f"Seeded {counts['dishes']} dishes across {counts['restaurants']} restaurants "
        f"({counts['quarantined']} quarantined, "
        f"{counts['allergens_unknown']} with unknown allergens)."
    )


if __name__ == "__main__":
    main()

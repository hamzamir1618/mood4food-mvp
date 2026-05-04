"""
Neo4j Seed Script — FIPE Mood4Food MVP
Seeds :Dish and :Ingredient nodes with :CONTAINS relationships.

Run AFTER Neo4j is up (Step 2.1 in DEPLOYMENT_RUNBOOK):
    python seed_neo4j.py

Nodes created:
    (:Dish {dish_id, name, price_pkr, protein_g, calories, synthesized_calories})
    (:Ingredient {name})

Relationships:
    (:Dish)-[:CONTAINS]->(:Ingredient)
"""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "Mood4Food")

# ── Ingredient catalogue ────────────────────────────────────────────────────
INGREDIENTS = [
    "chicken", "mutton", "beef", "meat", "fish",
    "rice", "lentils", "chickpeas", "paneer", "tofu",
    "onion", "tomato", "garlic", "ginger", "potato",
    "spinach", "okra", "cauliflower", "eggplant", "capsicum",
    "yogurt", "cream", "butter", "ghee", "cheese",
    "milk", "dairy",
    "wheat", "flour", "bread", "naan",
    "chili", "turmeric", "cumin", "coriander", "garam masala",
    "oil", "salt", "sugar", "lemon",
    "egg",
]

# ── Dish catalogue ──────────────────────────────────────────────────────────
# Each dish: (dish_id, name, price_pkr, protein_g, calories, ingredients[])
DISHES = [
    # ── Vegetarian / Vegan ──────────────────────────────────────────────────
    ("D001", "Dal Tadka",            250, 12.0, 320,
     ["lentils", "onion", "tomato", "garlic", "ginger",
      "cumin", "turmeric", "chili", "ghee", "coriander", "salt"]),

    ("D002", "Chana Masala",         280, 14.0, 350,
     ["chickpeas", "onion", "tomato", "garlic", "ginger",
      "cumin", "coriander", "garam masala", "chili", "oil", "salt", "lemon"]),

    ("D003", "Palak Paneer",         350, 18.0, 400,
     ["paneer", "spinach", "onion", "tomato", "garlic",
      "ginger", "cream", "dairy", "cumin", "garam masala", "salt"]),

    ("D004", "Aloo Gobi",            200, 6.0,  280,
     ["potato", "cauliflower", "onion", "tomato", "garlic",
      "turmeric", "cumin", "chili", "oil", "coriander", "salt"]),

    ("D005", "Baingan Bharta",       220, 5.0,  260,
     ["eggplant", "onion", "tomato", "garlic", "ginger",
      "chili", "cumin", "coriander", "oil", "salt"]),

    ("D006", "Vegetable Biryani",    300, 10.0, 450,
     ["rice", "potato", "onion", "tomato", "capsicum",
      "garlic", "ginger", "cumin", "garam masala", "turmeric",
      "ghee", "coriander", "chili", "salt", "yogurt", "dairy"]),

    ("D007", "Dahi Bhalle",          180, 8.0,  300,
     ["lentils", "yogurt", "dairy", "onion", "cumin",
      "chili", "coriander", "tamarind", "salt"]),

    # ── Chicken ─────────────────────────────────────────────────────────────
    ("D008", "Chicken Karahi",       550, 35.0, 520,
     ["chicken", "meat", "tomato", "onion", "garlic", "ginger",
      "capsicum", "chili", "garam masala", "coriander", "oil", "salt"]),

    ("D009", "Butter Chicken",       600, 32.0, 580,
     ["chicken", "meat", "butter", "cream", "dairy", "tomato",
      "onion", "garlic", "ginger", "garam masala", "chili",
      "cumin", "sugar", "salt"]),

    ("D010", "Chicken Biryani",      450, 30.0, 600,
     ["chicken", "meat", "rice", "onion", "tomato", "garlic",
      "ginger", "yogurt", "dairy", "cumin", "garam masala",
      "turmeric", "chili", "ghee", "coriander", "salt"]),

    ("D011", "Chicken Tikka",        400, 38.0, 350,
     ["chicken", "meat", "yogurt", "dairy", "garlic", "ginger",
      "chili", "cumin", "garam masala", "lemon", "oil", "salt"]),

    # ── Mutton / Beef ───────────────────────────────────────────────────────
    ("D012", "Mutton Nihari",        700, 28.0, 620,
     ["mutton", "meat", "onion", "garlic", "ginger", "flour",
      "chili", "garam masala", "turmeric", "ghee", "coriander", "salt"]),

    ("D013", "Beef Chapli Kebab",    350, 25.0, 480,
     ["beef", "meat", "onion", "tomato", "garlic", "ginger",
      "egg", "flour", "cumin", "coriander", "chili", "oil", "salt"]),

    ("D014", "Mutton Korma",         750, 26.0, 600,
     ["mutton", "meat", "yogurt", "dairy", "cream", "onion",
      "garlic", "ginger", "garam masala", "cumin", "turmeric",
      "ghee", "salt"]),

    # ── Fish ────────────────────────────────────────────────────────────────
    ("D015", "Fish Fry Lahori",      500, 30.0, 400,
     ["fish", "flour", "garlic", "ginger", "chili",
      "turmeric", "cumin", "lemon", "oil", "salt"]),

    # ── Egg ─────────────────────────────────────────────────────────────────
    ("D016", "Anda Curry",           180, 14.0, 280,
     ["egg", "onion", "tomato", "garlic", "ginger",
      "chili", "turmeric", "cumin", "oil", "coriander", "salt"]),

    # ── Bread / Light ───────────────────────────────────────────────────────
    ("D017", "Plain Naan",            50, 3.0,  260,
     ["flour", "wheat", "yogurt", "dairy", "sugar", "salt", "oil"]),

    ("D018", "Spicy Tofu Stir-Fry",  320, 20.0, 310,
     ["tofu", "capsicum", "onion", "garlic", "ginger",
      "chili", "cumin", "coriander", "oil", "salt"]),

    # ── Lentil / Rice combos ────────────────────────────────────────────────
    ("D019", "Khichdi",              150, 10.0, 350,
     ["rice", "lentils", "onion", "garlic", "turmeric",
      "cumin", "ghee", "salt"]),

    ("D020", "Haleem",               400, 22.0, 500,
     ["lentils", "wheat", "beef", "meat", "onion", "garlic",
      "ginger", "garam masala", "chili", "ghee", "coriander",
      "lemon", "salt"]),
]


def seed(tx):
    """Run inside a single transaction — idempotent via MERGE."""

    # ── Create Ingredient nodes ─────────────────────────────────────────
    for name in INGREDIENTS:
        tx.run("MERGE (:Ingredient {name: $name})", name=name)

    # ── Create Dish nodes + relationships ───────────────────────────────
    for dish_id, name, price, protein, cals, ingredients in DISHES:
        tx.run(
            """
            MERGE (d:Dish {dish_id: $dish_id})
            SET d.name                 = $name,
                d.price_pkr            = $price,
                d.protein_g            = $protein,
                d.calories             = $cals,
                d.synthesized_calories = $cals
            """,
            dish_id=dish_id, name=name, price=price,
            protein=protein, cals=cals,
        )
        for ing_name in ingredients:
            tx.run(
                """
                MATCH (d:Dish {dish_id: $dish_id})
                MATCH (i:Ingredient {name: $ing_name})
                MERGE (d)-[:CONTAINS]->(i)
                """,
                dish_id=dish_id, ing_name=ing_name,
            )


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    driver.verify_connectivity()
    print("[OK]  Connected to Neo4j at", NEO4J_URI)

    with driver.session() as session:
        session.execute_write(seed)

    # Quick verification
    with driver.session() as session:
        dish_count = session.run("MATCH (d:Dish) RETURN count(d) AS c").single()["c"]
        ing_count  = session.run("MATCH (i:Ingredient) RETURN count(i) AS c").single()["c"]
        rel_count  = session.run("MATCH ()-[r:CONTAINS]->() RETURN count(r) AS c").single()["c"]

    driver.close()

    print(f"[OK]  Seeded {dish_count} Dish nodes")
    print(f"[OK]  Seeded {ing_count} Ingredient nodes")
    print(f"[OK]  Created {rel_count} CONTAINS relationships")
    print("[OK]  Neo4j seed complete — ready for symbolic_anchoring.py")


if __name__ == "__main__":
    main()

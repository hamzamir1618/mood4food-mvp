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
    # Proteins
    "chicken", "mutton", "beef", "meat", "fish",
    "prawns", "shrimp", "shellfish",
    "egg",
    "paneer", "tofu",
    # Legumes & grains
    "rice", "lentils", "chickpeas", "kidney beans",
    "wheat", "flour", "bread", "naan", "semolina",
    "corn", "oats",
    # Vegetables
    "onion", "tomato", "garlic", "ginger", "potato",
    "spinach", "okra", "cauliflower", "eggplant", "capsicum",
    "carrot", "peas", "mushroom", "cabbage", "lettuce",
    "cucumber", "radish",
    # Dairy
    "yogurt", "cream", "butter", "ghee", "cheese",
    "milk", "dairy",
    # Nuts & seeds
    "cashew", "almond", "peanut", "nuts",
    "coconut", "sesame",
    # Fruits
    "mango", "banana", "pomegranate", "raisin", "tamarind",
    # Spices & seasonings
    "chili", "turmeric", "cumin", "coriander", "garam masala",
    "mint", "basil", "oregano", "soy sauce", "cardamom",
    # Pantry
    "oil", "salt", "sugar", "jaggery", "honey", "lemon",
    # Gluten markers
    "gluten",
]

# ── Dish catalogue ──────────────────────────────────────────────────────────
# Each dish: (dish_id, name, price_pkr, protein_g, calories, ingredients[])
DISHES = [
    # ═══════════════════════════════════════════════════════════════════════
    # VEGETARIAN / VEGAN
    # ═══════════════════════════════════════════════════════════════════════
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

    ("D021", "Rajma Chawal",         200, 13.0, 380,
     ["kidney beans", "rice", "onion", "tomato", "garlic",
      "ginger", "cumin", "chili", "coriander", "oil", "salt"]),

    ("D022", "Bhindi Masala",        180, 4.0,  220,
     ["okra", "onion", "tomato", "garlic", "turmeric",
      "cumin", "chili", "coriander", "oil", "salt"]),

    ("D023", "Mushroom Matar",       260, 9.0,  240,
     ["mushroom", "peas", "onion", "tomato", "garlic",
      "ginger", "cumin", "garam masala", "oil", "salt"]),

    ("D024", "Mixed Veg Curry",      220, 7.0,  270,
     ["potato", "peas", "carrot", "capsicum", "onion",
      "tomato", "garlic", "ginger", "turmeric", "cumin", "oil", "salt"]),

    ("D025", "Coconut Chickpea Curry", 300, 15.0, 370,
     ["chickpeas", "coconut", "onion", "tomato", "garlic",
      "ginger", "turmeric", "cumin", "chili", "coriander", "oil", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # CHICKEN
    # ═══════════════════════════════════════════════════════════════════════
    ("D008", "Chicken Karahi",       550, 35.0, 520,
     ["chicken", "meat", "tomato", "onion", "garlic", "ginger",
      "capsicum", "chili", "garam masala", "coriander", "oil", "salt"]),

    ("D009", "Butter Chicken",       600, 32.0, 580,
     ["chicken", "meat", "butter", "cream", "dairy", "tomato",
      "onion", "garlic", "ginger", "garam masala", "chili",
      "cumin", "sugar", "salt", "cashew", "nuts"]),

    ("D010", "Chicken Biryani",      450, 30.0, 600,
     ["chicken", "meat", "rice", "onion", "tomato", "garlic",
      "ginger", "yogurt", "dairy", "cumin", "garam masala",
      "turmeric", "chili", "ghee", "coriander", "salt"]),

    ("D011", "Chicken Tikka",        400, 38.0, 350,
     ["chicken", "meat", "yogurt", "dairy", "garlic", "ginger",
      "chili", "cumin", "garam masala", "lemon", "oil", "salt"]),

    ("D026", "Chicken Corn Soup",    180, 16.0, 200,
     ["chicken", "meat", "corn", "egg", "garlic", "ginger",
      "salt", "oil"]),

    ("D027", "Chicken Shawarma",     350, 28.0, 420,
     ["chicken", "meat", "flour", "wheat", "gluten",
      "garlic", "yogurt", "dairy", "lettuce", "tomato",
      "onion", "lemon", "cumin", "chili", "oil", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # MUTTON / BEEF
    # ═══════════════════════════════════════════════════════════════════════
    ("D012", "Mutton Nihari",        700, 28.0, 620,
     ["mutton", "meat", "onion", "garlic", "ginger", "flour",
      "wheat", "gluten", "chili", "garam masala", "turmeric",
      "ghee", "coriander", "salt"]),

    ("D013", "Beef Chapli Kebab",    350, 25.0, 480,
     ["beef", "meat", "onion", "tomato", "garlic", "ginger",
      "egg", "flour", "wheat", "gluten", "cumin", "coriander",
      "chili", "oil", "salt"]),

    ("D014", "Mutton Korma",         750, 26.0, 600,
     ["mutton", "meat", "yogurt", "dairy", "cream", "onion",
      "garlic", "ginger", "garam masala", "cumin", "turmeric",
      "ghee", "cashew", "nuts", "salt"]),

    ("D028", "Beef Biryani",         500, 32.0, 650,
     ["beef", "meat", "rice", "onion", "tomato", "garlic",
      "ginger", "yogurt", "dairy", "cumin", "garam masala",
      "turmeric", "ghee", "chili", "coriander", "salt"]),

    ("D029", "Seekh Kebab",          300, 22.0, 380,
     ["beef", "meat", "onion", "garlic", "ginger", "chili",
      "cumin", "coriander", "garam masala", "oil", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # FISH & SEAFOOD
    # ═══════════════════════════════════════════════════════════════════════
    ("D015", "Fish Fry Lahori",      500, 30.0, 400,
     ["fish", "flour", "wheat", "gluten", "garlic", "ginger",
      "chili", "turmeric", "cumin", "lemon", "oil", "salt"]),

    ("D030", "Prawn Karahi",         800, 28.0, 380,
     ["prawns", "shrimp", "shellfish", "tomato", "onion",
      "garlic", "ginger", "capsicum", "chili", "garam masala",
      "coriander", "oil", "salt"]),

    ("D031", "Fish Tikka",           550, 32.0, 320,
     ["fish", "yogurt", "dairy", "garlic", "ginger", "chili",
      "cumin", "turmeric", "lemon", "oil", "salt"]),

    ("D032", "Shrimp Rice Bowl",     650, 26.0, 450,
     ["prawns", "shrimp", "shellfish", "rice", "onion",
      "garlic", "ginger", "capsicum", "soy sauce",
      "sesame", "chili", "oil", "salt"]),

    ("D033", "Coconut Fish Curry",   600, 27.0, 390,
     ["fish", "coconut", "onion", "tomato", "garlic",
      "ginger", "turmeric", "chili", "cumin",
      "coriander", "oil", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # EGG
    # ═══════════════════════════════════════════════════════════════════════
    ("D016", "Anda Curry",           180, 14.0, 280,
     ["egg", "onion", "tomato", "garlic", "ginger",
      "chili", "turmeric", "cumin", "oil", "coriander", "salt"]),

    ("D034", "Egg Fried Rice",       200, 12.0, 400,
     ["egg", "rice", "onion", "garlic", "peas", "carrot",
      "soy sauce", "oil", "salt"]),

    ("D035", "Omelette Paratha",     120, 15.0, 420,
     ["egg", "flour", "wheat", "gluten", "onion", "tomato",
      "chili", "oil", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # BREAD / LIGHT
    # ═══════════════════════════════════════════════════════════════════════
    ("D017", "Plain Naan",            50, 3.0,  260,
     ["flour", "wheat", "gluten", "yogurt", "dairy",
      "sugar", "salt", "oil"]),

    ("D036", "Garlic Naan",           80, 4.0,  290,
     ["flour", "wheat", "gluten", "garlic", "butter",
      "dairy", "salt", "oil"]),

    ("D037", "Missi Roti",            40, 6.0,  200,
     ["chickpeas", "flour", "wheat", "gluten", "onion",
      "chili", "cumin", "coriander", "salt", "oil"]),

    # ═══════════════════════════════════════════════════════════════════════
    # TOFU / VEGAN PROTEIN
    # ═══════════════════════════════════════════════════════════════════════
    ("D018", "Spicy Tofu Stir-Fry",  320, 20.0, 310,
     ["tofu", "capsicum", "onion", "garlic", "ginger",
      "chili", "cumin", "coriander", "oil", "salt"]),

    ("D038", "Tofu Rice Bowl",       280, 18.0, 380,
     ["tofu", "rice", "carrot", "capsicum", "onion",
      "garlic", "soy sauce", "sesame", "chili", "oil", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # LENTIL / RICE COMBOS
    # ═══════════════════════════════════════════════════════════════════════
    ("D019", "Khichdi",              150, 10.0, 350,
     ["rice", "lentils", "onion", "garlic", "turmeric",
      "cumin", "ghee", "salt"]),

    ("D020", "Haleem",               400, 22.0, 500,
     ["lentils", "wheat", "gluten", "beef", "meat", "onion",
      "garlic", "ginger", "garam masala", "chili", "ghee",
      "coriander", "lemon", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # SWEET / DESSERT
    # ═══════════════════════════════════════════════════════════════════════
    ("D039", "Kheer",                200, 6.0,  350,
     ["rice", "milk", "dairy", "sugar", "cashew", "nuts",
      "raisin", "cardamom", "salt"]),

    ("D040", "Gulab Jamun",          150, 3.0,  400,
     ["milk", "dairy", "flour", "wheat", "gluten",
      "sugar", "ghee", "cardamom"]),

    ("D041", "Gajar Halwa",          250, 5.0,  380,
     ["carrot", "milk", "dairy", "sugar", "ghee",
      "cashew", "almond", "nuts", "raisin", "cardamom"]),

    ("D042", "Suji Halwa",           100, 3.0,  300,
     ["semolina", "wheat", "gluten", "sugar", "ghee",
      "cashew", "nuts", "raisin", "cardamom"]),

    ("D043", "Mango Lassi",          120, 4.0,  220,
     ["mango", "yogurt", "dairy", "sugar", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # STREET FOOD
    # ═══════════════════════════════════════════════════════════════════════
    ("D044", "Samosa (2 pcs)",        60, 4.0,  320,
     ["potato", "peas", "flour", "wheat", "gluten",
      "onion", "cumin", "chili", "coriander", "oil", "salt"]),

    ("D045", "Pakora Plate",          80, 5.0,  350,
     ["chickpeas", "onion", "potato", "spinach",
      "chili", "cumin", "turmeric", "oil", "salt"]),

    ("D046", "Gol Gappay (6 pcs)",    50, 2.0,  180,
     ["semolina", "wheat", "gluten", "potato", "chickpeas",
      "onion", "tamarind", "chili", "cumin", "mint",
      "coriander", "salt"]),

    ("D047", "Aloo Tikki Chaat",     100, 5.0,  290,
     ["potato", "chickpeas", "yogurt", "dairy", "onion",
      "tamarind", "chili", "cumin", "mint",
      "coriander", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # NUT-BASED / RICH
    # ═══════════════════════════════════════════════════════════════════════
    ("D048", "Cashew Paneer Masala",  450, 16.0, 480,
     ["paneer", "cashew", "nuts", "cream", "dairy",
      "onion", "tomato", "garlic", "ginger",
      "garam masala", "cumin", "turmeric", "oil", "salt"]),

    ("D049", "Peanut Chaat Salad",   120, 10.0, 250,
     ["peanut", "nuts", "onion", "tomato", "cucumber",
      "lemon", "chili", "cumin", "coriander", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # FRESH / LIGHT
    # ═══════════════════════════════════════════════════════════════════════
    ("D050", "Raita Bowl",            80, 5.0,  120,
     ["yogurt", "dairy", "cucumber", "onion", "mint",
      "cumin", "salt"]),

    ("D051", "Pomegranate Salad",    150, 3.0,  160,
     ["pomegranate", "cucumber", "lettuce", "onion",
      "mint", "lemon", "sesame", "oil", "salt"]),

    ("D052", "Corn Chaat",           100, 4.0,  200,
     ["corn", "onion", "tomato", "lemon", "chili",
      "cumin", "coriander", "butter", "dairy", "salt"]),

    # ═══════════════════════════════════════════════════════════════════════
    # PREMIUM / SPECIAL
    # ═══════════════════════════════════════════════════════════════════════
    ("D053", "Mutton Biryani",       650, 30.0, 680,
     ["mutton", "meat", "rice", "onion", "tomato",
      "garlic", "ginger", "yogurt", "dairy", "cumin",
      "garam masala", "turmeric", "ghee", "coriander",
      "chili", "salt", "mint"]),

    ("D054", "Prawn Biryani",        900, 26.0, 550,
     ["prawns", "shrimp", "shellfish", "rice", "onion",
      "tomato", "garlic", "ginger", "yogurt", "dairy",
      "cumin", "garam masala", "turmeric", "ghee",
      "coriander", "chili", "salt", "mint"]),

    ("D055", "Lamb Chops",           850, 35.0, 500,
     ["mutton", "meat", "garlic", "ginger", "yogurt",
      "dairy", "cumin", "garam masala", "chili",
      "lemon", "oil", "salt"]),
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

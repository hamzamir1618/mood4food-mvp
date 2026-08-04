"""
Neo4j Seed Script — FIPE Mood4Food MVP
Seeds :Dish and :Ingredient nodes with :CONTAINS relationships.

Run AFTER Neo4j is up (Step 2.1 in DEPLOYMENT_RUNBOOK):
    python seed_neo4j.py

Nodes created:
    (:Dish {dish_id, name, price_pkr, protein_g, calories, synthesized_calories,
            category, image_url, human_tags,
            taste_sweet, taste_salty, taste_sour, taste_bitter, taste_umami, taste_spice})
    (:Ingredient {name})

Relationships:
    (:Dish)-[:CONTAINS]->(:Ingredient)
"""

from neo4j import GraphDatabase

from config import settings

NEO4J_URI = settings.NEO4J_URI
NEO4J_AUTH = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)

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
# Each dish: (dish_id, name, price_pkr, protein_g, calories, ingredients[],
#             category, image_url, human_tags[], taste_profile{})
DISHES = [
    # ═══════════════════════════════════════════════════════════════════════
    # VEGETARIAN / VEGAN
    # ═══════════════════════════════════════════════════════════════════════
    ("D001", "Dal Tadka",            250, 12.0, 320,
     ["lentils", "onion", "tomato", "garlic", "ginger",
      "cumin", "turmeric", "chili", "ghee", "coriander", "salt"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&h=600&fit=crop",
     ["Budget Friendly", "Comfort Food", "High Protein", "Vegetarian"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.2, "bitter": 0.1, "umami": 0.6, "spice": 0.5}),

    ("D002", "Chana Masala",         280, 14.0, 350,
     ["chickpeas", "onion", "tomato", "garlic", "ginger",
      "cumin", "coriander", "garam masala", "chili", "oil", "salt", "lemon"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&h=600&fit=crop&q=80",
     ["High Protein", "Budget Friendly", "Spicy", "Vegan"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.3, "bitter": 0.1, "umami": 0.5, "spice": 0.7}),

    ("D003", "Palak Paneer",         350, 18.0, 400,
     ["paneer", "spinach", "onion", "tomato", "garlic",
      "ginger", "cream", "dairy", "cumin", "garam masala", "salt"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=800&h=600&fit=crop",
     ["Rich & Creamy", "High Protein", "Vegetarian", "Comfort Food"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.1, "bitter": 0.2, "umami": 0.6, "spice": 0.4}),

    ("D004", "Aloo Gobi",            200, 6.0,  280,
     ["potato", "cauliflower", "onion", "tomato", "garlic",
      "turmeric", "cumin", "chili", "oil", "coriander", "salt"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&h=600&fit=crop",
     ["Budget Friendly", "Comfort Food", "Vegetarian", "Vegan"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.1, "bitter": 0.1, "umami": 0.3, "spice": 0.5}),

    ("D005", "Baingan Bharta",       220, 5.0,  260,
     ["eggplant", "onion", "tomato", "garlic", "ginger",
      "chili", "cumin", "coriander", "oil", "salt"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&h=600&fit=crop&q=80",
     ["Budget Friendly", "Light & Fresh", "Vegan"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.2, "bitter": 0.2, "umami": 0.5, "spice": 0.6}),

    ("D006", "Vegetable Biryani",    300, 10.0, 450,
     ["rice", "potato", "onion", "tomato", "capsicum",
      "garlic", "ginger", "cumin", "garam masala", "turmeric",
      "ghee", "coriander", "chili", "salt", "yogurt", "dairy"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f4?w=800&h=600&fit=crop",
     ["Hearty", "Comfort Food", "Vegetarian"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.2, "bitter": 0.1, "umami": 0.5, "spice": 0.6}),

    ("D007", "Dahi Bhalle",          180, 8.0,  300,
     ["lentils", "yogurt", "dairy", "onion", "cumin",
      "chili", "coriander", "tamarind", "salt"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=800&h=600&fit=crop&q=75",
     ["Light & Fresh", "Street Style", "Vegetarian"],
     {"sweet": 0.3, "salty": 0.4, "sour": 0.6, "bitter": 0.0, "umami": 0.3, "spice": 0.4}),

    ("D021", "Rajma Chawal",         200, 13.0, 380,
     ["kidney beans", "rice", "onion", "tomato", "garlic",
      "ginger", "cumin", "chili", "coriander", "oil", "salt"],
     "Lentil/Rice",
     "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&h=600&fit=crop&q=75",
     ["Budget Friendly", "High Protein", "Hearty", "Comfort Food"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.2, "bitter": 0.1, "umami": 0.6, "spice": 0.5}),

    ("D022", "Bhindi Masala",        180, 4.0,  220,
     ["okra", "onion", "tomato", "garlic", "turmeric",
      "cumin", "chili", "coriander", "oil", "salt"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&h=600&fit=crop&q=75",
     ["Budget Friendly", "Light & Fresh", "Vegan"],
     {"sweet": 0.1, "salty": 0.4, "sour": 0.1, "bitter": 0.1, "umami": 0.3, "spice": 0.5}),

    ("D023", "Mushroom Matar",       260, 9.0,  240,
     ["mushroom", "peas", "onion", "tomato", "garlic",
      "ginger", "cumin", "garam masala", "oil", "salt"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&h=600&fit=crop&q=70",
     ["Light & Fresh", "Vegetarian", "Comfort Food"],
     {"sweet": 0.2, "salty": 0.5, "sour": 0.1, "bitter": 0.1, "umami": 0.7, "spice": 0.3}),

    ("D024", "Mixed Veg Curry",      220, 7.0,  270,
     ["potato", "peas", "carrot", "capsicum", "onion",
      "tomato", "garlic", "ginger", "turmeric", "cumin", "oil", "salt"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&h=600&fit=crop&q=65",
     ["Budget Friendly", "Comfort Food", "Vegetarian", "Vegan"],
     {"sweet": 0.2, "salty": 0.5, "sour": 0.2, "bitter": 0.1, "umami": 0.4, "spice": 0.4}),

    ("D025", "Coconut Chickpea Curry", 300, 15.0, 370,
     ["chickpeas", "coconut", "onion", "tomato", "garlic",
      "ginger", "turmeric", "cumin", "chili", "coriander", "oil", "salt"],
     "Vegetarian",
     "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&h=600&fit=crop&q=70",
     ["Rich & Creamy", "Vegan", "High Protein", "Gluten Free"],
     {"sweet": 0.2, "salty": 0.4, "sour": 0.2, "bitter": 0.1, "umami": 0.5, "spice": 0.5}),

    # ═══════════════════════════════════════════════════════════════════════
    # CHICKEN
    # ═══════════════════════════════════════════════════════════════════════
    ("D008", "Chicken Karahi",       550, 35.0, 520,
     ["chicken", "meat", "tomato", "onion", "garlic", "ginger",
      "capsicum", "chili", "garam masala", "coriander", "oil", "salt"],
     "Chicken",
     "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=800&h=600&fit=crop",
     ["High Protein", "Spicy", "Comfort Food", "Hearty"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.3, "bitter": 0.1, "umami": 0.8, "spice": 0.9}),

    ("D009", "Butter Chicken",       600, 32.0, 580,
     ["chicken", "meat", "butter", "cream", "dairy", "tomato",
      "onion", "garlic", "ginger", "garam masala", "chili",
      "cumin", "sugar", "salt", "cashew", "nuts"],
     "Chicken",
     "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=800&h=600&fit=crop&q=80",
     ["Rich & Creamy", "Comfort Food", "High Protein", "Premium"],
     {"sweet": 0.3, "salty": 0.5, "sour": 0.2, "bitter": 0.1, "umami": 0.8, "spice": 0.5}),

    ("D010", "Chicken Biryani",      450, 30.0, 600,
     ["chicken", "meat", "rice", "onion", "tomato", "garlic",
      "ginger", "yogurt", "dairy", "cumin", "garam masala",
      "turmeric", "chili", "ghee", "coriander", "salt"],
     "Chicken",
     "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f4?w=800&h=600&fit=crop&q=80",
     ["Hearty", "Comfort Food", "High Protein", "Spicy"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.2, "bitter": 0.1, "umami": 0.7, "spice": 0.7}),

    ("D011", "Chicken Tikka",        400, 38.0, 350,
     ["chicken", "meat", "yogurt", "dairy", "garlic", "ginger",
      "chili", "cumin", "garam masala", "lemon", "oil", "salt"],
     "Chicken",
     "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=800&h=600&fit=crop&q=75",
     ["High Protein", "Spicy", "Gluten Free", "Quick Bite"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.3, "bitter": 0.1, "umami": 0.7, "spice": 0.8}),

    ("D026", "Chicken Corn Soup",    180, 16.0, 200,
     ["chicken", "meat", "corn", "egg", "garlic", "ginger",
      "salt", "oil"],
     "Chicken",
     "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=800&h=600&fit=crop",
     ["Light & Fresh", "Budget Friendly", "Comfort Food"],
     {"sweet": 0.2, "salty": 0.5, "sour": 0.1, "bitter": 0.0, "umami": 0.6, "spice": 0.2}),

    ("D027", "Chicken Shawarma",     350, 28.0, 420,
     ["chicken", "meat", "flour", "wheat", "gluten",
      "garlic", "yogurt", "dairy", "lettuce", "tomato",
      "onion", "lemon", "cumin", "chili", "oil", "salt"],
     "Chicken",
     "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=800&h=600&fit=crop&q=70",
     ["High Protein", "Street Style", "Quick Bite", "Spicy"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.3, "bitter": 0.1, "umami": 0.6, "spice": 0.6}),

    # ═══════════════════════════════════════════════════════════════════════
    # MUTTON / BEEF
    # ═══════════════════════════════════════════════════════════════════════
    ("D012", "Mutton Nihari",        700, 28.0, 620,
     ["mutton", "meat", "onion", "garlic", "ginger", "flour",
      "wheat", "gluten", "chili", "garam masala", "turmeric",
      "ghee", "coriander", "salt"],
     "Mutton/Beef",
     "https://images.unsplash.com/photo-1544025162-d76694265947?w=800&h=600&fit=crop",
     ["Rich & Creamy", "Hearty", "Spicy", "Premium"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.1, "bitter": 0.1, "umami": 0.9, "spice": 0.8}),

    ("D013", "Beef Chapli Kebab",    350, 25.0, 480,
     ["beef", "meat", "onion", "tomato", "garlic", "ginger",
      "egg", "flour", "wheat", "gluten", "cumin", "coriander",
      "chili", "oil", "salt"],
     "Mutton/Beef",
     "https://images.unsplash.com/photo-1544025162-d76694265947?w=800&h=600&fit=crop&q=80",
     ["High Protein", "Spicy", "Street Style", "Quick Bite"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.2, "bitter": 0.1, "umami": 0.8, "spice": 0.7}),

    ("D014", "Mutton Korma",         750, 26.0, 600,
     ["mutton", "meat", "yogurt", "dairy", "cream", "onion",
      "garlic", "ginger", "garam masala", "cumin", "turmeric",
      "ghee", "cashew", "nuts", "salt"],
     "Mutton/Beef",
     "https://images.unsplash.com/photo-1544025162-d76694265947?w=800&h=600&fit=crop&q=75",
     ["Rich & Creamy", "Premium", "Comfort Food", "Hearty"],
     {"sweet": 0.2, "salty": 0.5, "sour": 0.1, "bitter": 0.1, "umami": 0.9, "spice": 0.5}),

    ("D028", "Beef Biryani",         500, 32.0, 650,
     ["beef", "meat", "rice", "onion", "tomato", "garlic",
      "ginger", "yogurt", "dairy", "cumin", "garam masala",
      "turmeric", "ghee", "chili", "coriander", "salt"],
     "Mutton/Beef",
     "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f4?w=800&h=600&fit=crop&q=75",
     ["Hearty", "Comfort Food", "High Protein", "Spicy"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.2, "bitter": 0.1, "umami": 0.8, "spice": 0.7}),

    ("D029", "Seekh Kebab",          300, 22.0, 380,
     ["beef", "meat", "onion", "garlic", "ginger", "chili",
      "cumin", "coriander", "garam masala", "oil", "salt"],
     "Mutton/Beef",
     "https://images.unsplash.com/photo-1544025162-d76694265947?w=800&h=600&fit=crop&q=70",
     ["High Protein", "Spicy", "Quick Bite", "Gluten Free"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.1, "bitter": 0.1, "umami": 0.8, "spice": 0.8}),

    # ═══════════════════════════════════════════════════════════════════════
    # FISH & SEAFOOD
    # ═══════════════════════════════════════════════════════════════════════
    ("D015", "Fish Fry Lahori",      500, 30.0, 400,
     ["fish", "flour", "wheat", "gluten", "garlic", "ginger",
      "chili", "turmeric", "cumin", "lemon", "oil", "salt"],
     "Fish/Seafood",
     "https://images.unsplash.com/photo-1580476262798-bddd9f4b7369?w=800&h=600&fit=crop",
     ["High Protein", "Spicy", "Street Style"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.3, "bitter": 0.1, "umami": 0.7, "spice": 0.8}),

    ("D030", "Prawn Karahi",         800, 28.0, 380,
     ["prawns", "shrimp", "shellfish", "tomato", "onion",
      "garlic", "ginger", "capsicum", "chili", "garam masala",
      "coriander", "oil", "salt"],
     "Fish/Seafood",
     "https://images.unsplash.com/photo-1580476262798-bddd9f4b7369?w=800&h=600&fit=crop&q=80",
     ["High Protein", "Spicy", "Premium", "Gluten Free"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.3, "bitter": 0.1, "umami": 0.9, "spice": 0.8}),

    ("D031", "Fish Tikka",           550, 32.0, 320,
     ["fish", "yogurt", "dairy", "garlic", "ginger", "chili",
      "cumin", "turmeric", "lemon", "oil", "salt"],
     "Fish/Seafood",
     "https://images.unsplash.com/photo-1580476262798-bddd9f4b7369?w=800&h=600&fit=crop&q=75",
     ["High Protein", "Spicy", "Gluten Free", "Light & Fresh"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.3, "bitter": 0.1, "umami": 0.7, "spice": 0.7}),

    ("D032", "Shrimp Rice Bowl",     650, 26.0, 450,
     ["prawns", "shrimp", "shellfish", "rice", "onion",
      "garlic", "ginger", "capsicum", "soy sauce",
      "sesame", "chili", "oil", "salt"],
     "Fish/Seafood",
     "https://images.unsplash.com/photo-1580476262798-bddd9f4b7369?w=800&h=600&fit=crop&q=70",
     ["High Protein", "Hearty", "Comfort Food"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.2, "bitter": 0.1, "umami": 0.8, "spice": 0.5}),

    ("D033", "Coconut Fish Curry",   600, 27.0, 390,
     ["fish", "coconut", "onion", "tomato", "garlic",
      "ginger", "turmeric", "chili", "cumin",
      "coriander", "oil", "salt"],
     "Fish/Seafood",
     "https://images.unsplash.com/photo-1580476262798-bddd9f4b7369?w=800&h=600&fit=crop&q=65",
     ["Rich & Creamy", "Gluten Free", "High Protein"],
     {"sweet": 0.2, "salty": 0.5, "sour": 0.2, "bitter": 0.1, "umami": 0.7, "spice": 0.6}),

    # ═══════════════════════════════════════════════════════════════════════
    # EGG
    # ═══════════════════════════════════════════════════════════════════════
    ("D016", "Anda Curry",           180, 14.0, 280,
     ["egg", "onion", "tomato", "garlic", "ginger",
      "chili", "turmeric", "cumin", "oil", "coriander", "salt"],
     "Egg",
     "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=800&h=600&fit=crop",
     ["Budget Friendly", "High Protein", "Comfort Food", "Spicy"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.3, "bitter": 0.1, "umami": 0.6, "spice": 0.6}),

    ("D034", "Egg Fried Rice",       200, 12.0, 400,
     ["egg", "rice", "onion", "garlic", "peas", "carrot",
      "soy sauce", "oil", "salt"],
     "Egg",
     "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=800&h=600&fit=crop&q=80",
     ["Quick Bite", "Comfort Food", "Budget Friendly"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.1, "bitter": 0.0, "umami": 0.6, "spice": 0.2}),

    ("D035", "Omelette Paratha",     120, 15.0, 420,
     ["egg", "flour", "wheat", "gluten", "onion", "tomato",
      "chili", "oil", "salt"],
     "Egg",
     "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=800&h=600&fit=crop&q=75",
     ["Budget Friendly", "Quick Bite", "High Protein", "Street Style"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.1, "bitter": 0.0, "umami": 0.5, "spice": 0.4}),

    # ═══════════════════════════════════════════════════════════════════════
    # BREAD / LIGHT
    # ═══════════════════════════════════════════════════════════════════════
    ("D017", "Plain Naan",            50, 3.0,  260,
     ["flour", "wheat", "gluten", "yogurt", "dairy",
      "sugar", "salt", "oil"],
     "Bread",
     "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&h=600&fit=crop",
     ["Budget Friendly", "Comfort Food", "Vegetarian"],
     {"sweet": 0.1, "salty": 0.3, "sour": 0.0, "bitter": 0.0, "umami": 0.2, "spice": 0.0}),

    ("D036", "Garlic Naan",           80, 4.0,  290,
     ["flour", "wheat", "gluten", "garlic", "butter",
      "dairy", "salt", "oil"],
     "Bread",
     "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&h=600&fit=crop&q=80",
     ["Budget Friendly", "Comfort Food", "Vegetarian"],
     {"sweet": 0.1, "salty": 0.4, "sour": 0.0, "bitter": 0.1, "umami": 0.3, "spice": 0.1}),

    ("D037", "Missi Roti",            40, 6.0,  200,
     ["chickpeas", "flour", "wheat", "gluten", "onion",
      "chili", "cumin", "coriander", "salt", "oil"],
     "Bread",
     "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&h=600&fit=crop&q=75",
     ["Budget Friendly", "High Protein", "Vegan"],
     {"sweet": 0.0, "salty": 0.4, "sour": 0.0, "bitter": 0.1, "umami": 0.3, "spice": 0.3}),

    # ═══════════════════════════════════════════════════════════════════════
    # TOFU / VEGAN PROTEIN
    # ═══════════════════════════════════════════════════════════════════════
    ("D018", "Spicy Tofu Stir-Fry",  320, 20.0, 310,
     ["tofu", "capsicum", "onion", "garlic", "ginger",
      "chili", "cumin", "coriander", "oil", "salt"],
     "Tofu/Vegan",
     "https://images.unsplash.com/photo-1546069901-5ec6a79120b0?w=800&h=600&fit=crop",
     ["High Protein", "Vegan", "Spicy", "Gluten Free"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.1, "bitter": 0.1, "umami": 0.6, "spice": 0.8}),

    ("D038", "Tofu Rice Bowl",       280, 18.0, 380,
     ["tofu", "rice", "carrot", "capsicum", "onion",
      "garlic", "soy sauce", "sesame", "chili", "oil", "salt"],
     "Tofu/Vegan",
     "https://images.unsplash.com/photo-1546069901-5ec6a79120b0?w=800&h=600&fit=crop&q=80",
     ["High Protein", "Vegan", "Hearty", "Comfort Food"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.1, "bitter": 0.1, "umami": 0.7, "spice": 0.4}),

    # ═══════════════════════════════════════════════════════════════════════
    # LENTIL / RICE COMBOS
    # ═══════════════════════════════════════════════════════════════════════
    ("D019", "Khichdi",              150, 10.0, 350,
     ["rice", "lentils", "onion", "garlic", "turmeric",
      "cumin", "ghee", "salt"],
     "Lentil/Rice",
     "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f4?w=800&h=600&fit=crop&q=70",
     ["Budget Friendly", "Comfort Food", "Light & Fresh", "Gluten Free"],
     {"sweet": 0.1, "salty": 0.4, "sour": 0.0, "bitter": 0.1, "umami": 0.4, "spice": 0.2}),

    ("D020", "Haleem",               400, 22.0, 500,
     ["lentils", "wheat", "gluten", "beef", "meat", "onion",
      "garlic", "ginger", "garam masala", "chili", "ghee",
      "coriander", "lemon", "salt"],
     "Lentil/Rice",
     "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&h=600&fit=crop&q=65",
     ["High Protein", "Hearty", "Rich & Creamy", "Spicy"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.2, "bitter": 0.1, "umami": 0.9, "spice": 0.7}),

    # ═══════════════════════════════════════════════════════════════════════
    # SWEET / DESSERT
    # ═══════════════════════════════════════════════════════════════════════
    ("D039", "Kheer",                200, 6.0,  350,
     ["rice", "milk", "dairy", "sugar", "cashew", "nuts",
      "raisin", "cardamom", "salt"],
     "Sweet/Dessert",
     "https://images.unsplash.com/photo-1551024506-0bccd828d307?w=800&h=600&fit=crop",
     ["Comfort Food", "Rich & Creamy", "Vegetarian", "Gluten Free"],
     {"sweet": 0.9, "salty": 0.1, "sour": 0.0, "bitter": 0.0, "umami": 0.2, "spice": 0.1}),

    ("D040", "Gulab Jamun",          150, 3.0,  400,
     ["milk", "dairy", "flour", "wheat", "gluten",
      "sugar", "ghee", "cardamom"],
     "Sweet/Dessert",
     "https://images.unsplash.com/photo-1551024506-0bccd828d307?w=800&h=600&fit=crop&q=80",
     ["Comfort Food", "Rich & Creamy", "Vegetarian"],
     {"sweet": 1.0, "salty": 0.0, "sour": 0.0, "bitter": 0.0, "umami": 0.1, "spice": 0.1}),

    ("D041", "Gajar Halwa",          250, 5.0,  380,
     ["carrot", "milk", "dairy", "sugar", "ghee",
      "cashew", "almond", "nuts", "raisin", "cardamom"],
     "Sweet/Dessert",
     "https://images.unsplash.com/photo-1551024506-0bccd828d307?w=800&h=600&fit=crop&q=75",
     ["Rich & Creamy", "Comfort Food", "Vegetarian", "Premium"],
     {"sweet": 0.9, "salty": 0.1, "sour": 0.0, "bitter": 0.0, "umami": 0.2, "spice": 0.2}),

    ("D042", "Suji Halwa",           100, 3.0,  300,
     ["semolina", "wheat", "gluten", "sugar", "ghee",
      "cashew", "nuts", "raisin", "cardamom"],
     "Sweet/Dessert",
     "https://images.unsplash.com/photo-1551024506-0bccd828d307?w=800&h=600&fit=crop&q=70",
     ["Budget Friendly", "Comfort Food", "Vegetarian"],
     {"sweet": 0.9, "salty": 0.1, "sour": 0.0, "bitter": 0.0, "umami": 0.1, "spice": 0.1}),

    ("D043", "Mango Lassi",          120, 4.0,  220,
     ["mango", "yogurt", "dairy", "sugar", "salt"],
     "Sweet/Dessert",
     "https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=800&h=600&fit=crop",
     ["Light & Fresh", "Vegetarian", "Gluten Free", "Quick Bite"],
     {"sweet": 0.8, "salty": 0.1, "sour": 0.3, "bitter": 0.0, "umami": 0.1, "spice": 0.0}),

    # ═══════════════════════════════════════════════════════════════════════
    # STREET FOOD
    # ═══════════════════════════════════════════════════════════════════════
    ("D044", "Samosa (2 pcs)",        60, 4.0,  320,
     ["potato", "peas", "flour", "wheat", "gluten",
      "onion", "cumin", "chili", "coriander", "oil", "salt"],
     "Street Food",
     "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=800&h=600&fit=crop",
     ["Budget Friendly", "Street Style", "Quick Bite", "Vegetarian"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.1, "bitter": 0.0, "umami": 0.3, "spice": 0.6}),

    ("D045", "Pakora Plate",          80, 5.0,  350,
     ["chickpeas", "onion", "potato", "spinach",
      "chili", "cumin", "turmeric", "oil", "salt"],
     "Street Food",
     "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=800&h=600&fit=crop&q=80",
     ["Budget Friendly", "Street Style", "Spicy", "Vegan"],
     {"sweet": 0.0, "salty": 0.5, "sour": 0.1, "bitter": 0.1, "umami": 0.3, "spice": 0.6}),

    ("D046", "Gol Gappay (6 pcs)",    50, 2.0,  180,
     ["semolina", "wheat", "gluten", "potato", "chickpeas",
      "onion", "tamarind", "chili", "cumin", "mint",
      "coriander", "salt"],
     "Street Food",
     "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=800&h=600&fit=crop&q=75",
     ["Budget Friendly", "Street Style", "Spicy", "Quick Bite"],
     {"sweet": 0.2, "salty": 0.4, "sour": 0.7, "bitter": 0.0, "umami": 0.2, "spice": 0.7}),

    ("D047", "Aloo Tikki Chaat",     100, 5.0,  290,
     ["potato", "chickpeas", "yogurt", "dairy", "onion",
      "tamarind", "chili", "cumin", "mint",
      "coriander", "salt"],
     "Street Food",
     "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=800&h=600&fit=crop&q=70",
     ["Budget Friendly", "Street Style", "Spicy", "Vegetarian"],
     {"sweet": 0.2, "salty": 0.5, "sour": 0.5, "bitter": 0.0, "umami": 0.3, "spice": 0.6}),

    # ═══════════════════════════════════════════════════════════════════════
    # NUT-BASED / RICH
    # ═══════════════════════════════════════════════════════════════════════
    ("D048", "Cashew Paneer Masala",  450, 16.0, 480,
     ["paneer", "cashew", "nuts", "cream", "dairy",
      "onion", "tomato", "garlic", "ginger",
      "garam masala", "cumin", "turmeric", "oil", "salt"],
     "Nut-Based",
     "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=800&h=600&fit=crop&q=80",
     ["Rich & Creamy", "Premium", "Vegetarian", "High Protein"],
     {"sweet": 0.2, "salty": 0.5, "sour": 0.1, "bitter": 0.1, "umami": 0.7, "spice": 0.4}),

    ("D049", "Peanut Chaat Salad",   120, 10.0, 250,
     ["peanut", "nuts", "onion", "tomato", "cucumber",
      "lemon", "chili", "cumin", "coriander", "salt"],
     "Nut-Based",
     "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&h=600&fit=crop&q=80",
     ["Light & Fresh", "Budget Friendly", "Vegan", "Gluten Free"],
     {"sweet": 0.1, "salty": 0.5, "sour": 0.4, "bitter": 0.0, "umami": 0.4, "spice": 0.5}),

    # ═══════════════════════════════════════════════════════════════════════
    # FRESH / LIGHT
    # ═══════════════════════════════════════════════════════════════════════
    ("D050", "Raita Bowl",            80, 5.0,  120,
     ["yogurt", "dairy", "cucumber", "onion", "mint",
      "cumin", "salt"],
     "Fresh/Light",
     "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&h=600&fit=crop",
     ["Light & Fresh", "Vegetarian", "Gluten Free", "Quick Bite"],
     {"sweet": 0.1, "salty": 0.4, "sour": 0.2, "bitter": 0.0, "umami": 0.2, "spice": 0.1}),

    ("D051", "Pomegranate Salad",    150, 3.0,  160,
     ["pomegranate", "cucumber", "lettuce", "onion",
      "mint", "lemon", "sesame", "oil", "salt"],
     "Fresh/Light",
     "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&h=600&fit=crop&q=75",
     ["Light & Fresh", "Vegan", "Gluten Free"],
     {"sweet": 0.4, "salty": 0.3, "sour": 0.4, "bitter": 0.1, "umami": 0.1, "spice": 0.0}),

    ("D052", "Corn Chaat",           100, 4.0,  200,
     ["corn", "onion", "tomato", "lemon", "chili",
      "cumin", "coriander", "butter", "dairy", "salt"],
     "Fresh/Light",
     "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&h=600&fit=crop&q=70",
     ["Light & Fresh", "Budget Friendly", "Vegetarian", "Quick Bite"],
     {"sweet": 0.3, "salty": 0.4, "sour": 0.3, "bitter": 0.0, "umami": 0.3, "spice": 0.4}),

    # ═══════════════════════════════════════════════════════════════════════
    # PREMIUM / SPECIAL
    # ═══════════════════════════════════════════════════════════════════════
    ("D053", "Mutton Biryani",       650, 30.0, 680,
     ["mutton", "meat", "rice", "onion", "tomato",
      "garlic", "ginger", "yogurt", "dairy", "cumin",
      "garam masala", "turmeric", "ghee", "coriander",
      "chili", "salt", "mint"],
     "Premium",
     "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f4?w=800&h=600&fit=crop&q=65",
     ["Premium", "Hearty", "Comfort Food", "Spicy"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.2, "bitter": 0.1, "umami": 0.9, "spice": 0.7}),

    ("D054", "Prawn Biryani",        900, 26.0, 550,
     ["prawns", "shrimp", "shellfish", "rice", "onion",
      "tomato", "garlic", "ginger", "yogurt", "dairy",
      "cumin", "garam masala", "turmeric", "ghee",
      "coriander", "chili", "salt", "mint"],
     "Premium",
     "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f4?w=800&h=600&fit=crop&q=60",
     ["Premium", "Hearty", "High Protein", "Spicy"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.2, "bitter": 0.1, "umami": 0.9, "spice": 0.6}),

    ("D055", "Lamb Chops",           850, 35.0, 500,
     ["mutton", "meat", "garlic", "ginger", "yogurt",
      "dairy", "cumin", "garam masala", "chili",
      "lemon", "oil", "salt"],
     "Premium",
     "https://images.unsplash.com/photo-1544025162-d76694265947?w=800&h=600&fit=crop&q=65",
     ["Premium", "High Protein", "Gluten Free", "Hearty"],
     {"sweet": 0.1, "salty": 0.6, "sour": 0.2, "bitter": 0.1, "umami": 0.9, "spice": 0.7}),
]


def seed(tx):
    """Run inside a single transaction — idempotent via MERGE."""

    # ── Create Ingredient nodes ─────────────────────────────────────────
    for name in INGREDIENTS:
        tx.run("MERGE (:Ingredient {name: $name})", name=name)

    # ── Create Dish nodes + relationships ───────────────────────────────
    for (dish_id, name, price, protein, cals, ingredients,
         category, image_url, human_tags, taste_profile) in DISHES:
        tx.run(
            """
            MERGE (d:Dish {dish_id: $dish_id})
            SET d.name                 = $name,
                d.price_pkr            = $price,
                d.protein_g            = $protein,
                d.calories             = $cals,
                d.synthesized_calories = $cals,
                d.category             = $category,
                d.image_url            = $image_url,
                d.human_tags           = $human_tags,
                d.taste_sweet          = $taste_sweet,
                d.taste_salty          = $taste_salty,
                d.taste_sour           = $taste_sour,
                d.taste_bitter         = $taste_bitter,
                d.taste_umami          = $taste_umami,
                d.taste_spice          = $taste_spice
            """,
            dish_id=dish_id, name=name, price=price,
            protein=protein, cals=cals,
            category=category, image_url=image_url,
            human_tags=human_tags,
            taste_sweet=taste_profile["sweet"],
            taste_salty=taste_profile["salty"],
            taste_sour=taste_profile["sour"],
            taste_bitter=taste_profile["bitter"],
            taste_umami=taste_profile["umami"],
            taste_spice=taste_profile["spice"],
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
        cat_count  = session.run(
            "MATCH (d:Dish) WHERE d.category IS NOT NULL "
            "RETURN count(DISTINCT d.category) AS c"
        ).single()["c"]
        tag_count  = session.run(
            "MATCH (d:Dish) WHERE d.human_tags IS NOT NULL "
            "RETURN count(d) AS c"
        ).single()["c"]
        taste_count = session.run(
            "MATCH (d:Dish) WHERE d.taste_sweet IS NOT NULL "
            "RETURN count(d) AS c"
        ).single()["c"]

    driver.close()

    print(f"[OK]  Seeded {dish_count} Dish nodes")
    print(f"[OK]  Seeded {ing_count} Ingredient nodes")
    print(f"[OK]  Created {rel_count} CONTAINS relationships")
    print(f"[OK]  {cat_count} distinct categories assigned")
    print(f"[OK]  {tag_count} dishes with human_tags")
    print(f"[OK]  {taste_count} dishes with taste_profile")
    print("[OK]  Neo4j seed complete — ready for symbolic_anchoring.py")


if __name__ == "__main__":
    main()

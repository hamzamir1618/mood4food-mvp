"""
Ingredient nutrition reference from USDA FoodData Central (Phase 1).

Maps every vocabulary ingredient (pipeline.ingredients) to one USDA SR Legacy
entry and writes data/reference/ingredient_nutrition.csv with its calories,
protein, fat and carbohydrate per 100 g, plus the FDC id and the entry's exact
description, so every number can be looked up. USDA FoodData Central is public
domain (CC0); see ATTRIBUTIONS.md.

Values are for the ingredient as it is usually eaten in a dish — cooked rice,
boiled lentils, roasted chicken — not dry or raw weights, because the estimator
apportions a cooked serving. Where USDA has no entry for an ingredient itself,
the closest food stands in and the row's note says so.

    python -m pipeline.usda_reference            # build the table
    python -m pipeline.usda_reference --check    # list entries that don't resolve

Sauces, condiments and alcohol are trace ingredients: they matter for allergens
and halal status but carry no weight in the estimate, so they have no row.
"""

import argparse
import csv
import sys

from pipeline import paths
from pipeline.ingredients import VOCABULARY

NUTRIENT_IDS = {"1008": "kcal", "1003": "protein", "1004": "fat", "1005": "carbs"}

# ingredient -> (exact SR Legacy description, note for stand-ins)
CHOICES = {
    "chicken": ("Chicken, broilers or fryers, meat only, cooked, roasted", ""),
    "beef": (
        "Beef, ground, 85% lean meat / 15% fat, patty, cooked, broiled",
        "ground beef stands in for curry cuts",
    ),
    "mutton": ("Game meat, goat, cooked, roasted", "mutton in Pakistan is goat"),
    "lamb": (
        'Lamb, composite of trimmed retail cuts, separable lean and fat, trimmed to 1/4" fat, choice, cooked',
        "",
    ),
    "lamb fat": (
        'Lamb, composite of trimmed retail cuts, separable fat, trimmed to 1/4" fat, choice, cooked',
        "",
    ),
    "turkey": ("Turkey, whole, meat only, cooked, roasted", ""),
    "liver": ("Chicken, liver, all classes, cooked, simmered", ""),
    "fish": ("Fish, cod, Atlantic, cooked, dry heat", "a white fish stands in for fish in general"),
    "prawns": (
        "Crustaceans, shrimp, mixed species, cooked, moist heat (may contain additives to retain moisture)",
        "",
    ),
    "crab": ("Crustaceans, crab, blue, cooked, moist heat", ""),
    "lobster": ("Crustaceans, lobster, northern, cooked, moist heat", ""),
    "squid": ("Mollusks, squid, mixed species, cooked, fried", ""),
    "egg": ("Egg, whole, cooked, hard-boiled", ""),
    "paneer": (
        "Cheese, fresh, queso fresco",
        "USDA has no paneer; a fresh unaged cheese stands in",
    ),
    "tofu": ("Tofu, raw, firm, prepared with calcium sulfate", ""),
    "chickpeas": (
        "Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, without salt",
        "",
    ),
    "lentils": ("Lentils, mature seeds, cooked, boiled, without salt", ""),
    "kidney beans": ("Beans, kidney, all types, mature seeds, cooked, boiled, without salt", ""),
    "beans": ("Beans, baked, canned, plain or vegetarian", ""),
    "sausage": (
        "Frankfurter, chicken",
        "a chicken frankfurter stands in for the halal sausages served here",
    ),
    "pork": (
        "Pork, fresh, composite of trimmed retail cuts (leg, loin, shoulder, and spareribs), separable lean and fat, cooked",
        "",
    ),
    "rice": ("Rice, white, long-grain, regular, enriched, cooked", ""),
    "wheat flour": ("Wheat flour, white, all-purpose, enriched, bleached", ""),
    "bread": ("Bread, white, commercially prepared (includes soft bread crumbs)", ""),
    "bun": ("Rolls, hamburger or hotdog, plain", ""),
    "naan": ("Bread, naan, plain, commercially prepared, refrigerated", ""),
    "roti": ("Bread, chapati or roti, plain, commercially prepared", ""),
    "paratha": ("Bread, paratha, whole wheat, commercially prepared, frozen", ""),
    "puri": (
        "Bread, paratha, whole wheat, commercially prepared, frozen",
        "paratha stands in for puri, another fried wheat flatbread",
    ),
    "pita": ("Bread, pita, white, enriched", ""),
    "tortilla": ("Tortillas, ready-to-bake or -fry, flour, refrigerated", ""),
    "pizza base": (
        "Bread, white, commercially prepared (includes soft bread crumbs)",
        "white bread stands in for pizza dough",
    ),
    "pastry": ("Puff pastry, frozen, ready-to-bake, baked", ""),
    "noodles": ("Noodles, egg, enriched, cooked", ""),
    "rice noodles": ("Rice noodles, cooked", ""),
    "pasta": ("Pasta, cooked, enriched, without added salt", ""),
    "vermicelli": (
        "Pasta, cooked, enriched, without added salt",
        "cooked pasta stands in for vermicelli",
    ),
    "semolina": ("Semolina, enriched", ""),
    "bulgur": ("Bulgur, cooked", ""),
    "oats": (
        "Cereals, oats, regular and quick, unenriched, cooked with water (includes boiling and microwaving), without salt",
        "",
    ),
    "gram flour": ("Chickpea flour (besan)", ""),
    "corn": ("Corn, sweet, yellow, cooked, boiled, drained, without salt", ""),
    "potato": ("Potatoes, boiled, cooked without skin, flesh, without salt", ""),
    "fries": ("Fast foods, potato, french fried in vegetable oil", ""),
    "molluscs": (
        "Mollusks, scallop, (bay and sea), cooked, steamed",
        "scallop stands in for mussels, clams and oysters",
    ),
    "edamame": ("Edamame, frozen, prepared", ""),
    "fish crackers": (
        "Snacks, corn-based, extruded, chips, plain",
        "USDA has no fish or prawn crackers; an extruded, fried starch snack stands in",
    ),
    "prawn crackers": (
        "Snacks, corn-based, extruded, chips, plain",
        "USDA has no fish or prawn crackers; an extruded, fried starch snack stands in",
    ),
    "milk": ("Milk, whole, 3.25% milkfat, with added vitamin D", ""),
    "yogurt": ("Yogurt, plain, whole milk", ""),
    "cream": ("Cream, fluid, heavy whipping", ""),
    "butter": ("Butter, salted", ""),
    "ghee": ("Butter oil, anhydrous", "anhydrous butter oil is ghee"),
    "cheese": ("Cheese, mozzarella, whole milk", "mozzarella stands in for cheese in general"),
    "cream cheese": ("Cheese, cream", ""),
    "condensed milk": ("Milk, canned, condensed, sweetened", ""),
    "ice cream": ("Ice creams, vanilla", ""),
    "khoya": ("Milk, dry, whole, without added vitamin D", "dried whole milk stands in for khoya"),
    "custard": ("Egg custards, dry mix, prepared with whole milk", ""),
    "cooking oil": ("Oil, canola", ""),
    "olive oil": ("Oil, olive, salad or cooking", ""),
    "mayonnaise": ("Salad dressing, mayonnaise, regular", ""),
    "tahini": (
        "Seeds, sesame butter, tahini, from roasted and toasted kernels (most common type)",
        "",
    ),
    "coconut milk": (
        "Nuts, coconut milk, canned (liquid expressed from grated meat and water)",
        "",
    ),
    "onion": ("Onions, raw", ""),
    "tomato": ("Tomatoes, red, ripe, raw, year round average", ""),
    "garlic": ("Garlic, raw", ""),
    "ginger": ("Ginger root, raw", ""),
    "green chilli": ("Peppers, hot chili, green, raw", ""),
    "bell pepper": ("Peppers, sweet, green, raw", ""),
    "spinach": ("Spinach, cooked, boiled, drained, without salt", ""),
    "eggplant": ("Eggplant, cooked, boiled, drained, without salt", ""),
    "okra": ("Okra, cooked, boiled, drained, without salt", ""),
    "cauliflower": ("Cauliflower, cooked, boiled, drained, without salt", ""),
    "cabbage": ("Cabbage, raw", ""),
    "carrot": ("Carrots, raw", ""),
    "peas": ("Peas, green, cooked, boiled, drained, without salt", ""),
    "mushrooms": ("Mushrooms, white, raw", ""),
    "cucumber": ("Cucumber, with peel, raw", ""),
    "lettuce": ("Lettuce, iceberg (includes crisphead types), raw", ""),
    "spring onion": ("Onions, spring or scallions (includes tops and bulb), raw", ""),
    "broccoli": ("Broccoli, raw", ""),
    "zucchini": ("Squash, summer, zucchini, includes skin, raw", ""),
    "green beans": ("Beans, snap, green, raw", ""),
    "herbs": ("Coriander (cilantro) leaves, raw", "coriander stands in for fresh herbs"),
    "lemon": ("Lemon juice, raw", ""),
    "olives": ("Olives, ripe, canned (small-extra large)", ""),
    "pickles": ("Pickles, cucumber, dill or kosher dill", ""),
    "avocado": ("Avocados, raw, all commercial varieties", ""),
    "beetroot": ("Beets, raw", ""),
    "pumpkin": ("Pumpkin, cooked, boiled, drained, without salt", ""),
    "mixed vegetables": ("Vegetables, mixed, frozen, cooked, boiled, drained, without salt", ""),
    "almonds": ("Nuts, almonds", ""),
    "cashews": ("Nuts, cashew nuts, raw", ""),
    "pistachios": ("Nuts, pistachio nuts, raw", ""),
    "peanuts": ("Peanuts, all types, raw", ""),
    "walnuts": ("Nuts, walnuts, english", ""),
    "sesame": ("Seeds, sesame seeds, whole, dried", ""),
    "coconut": ("Nuts, coconut meat, raw", ""),
    "sugar": ("Sugars, granulated", ""),
    "honey": ("Honey", ""),
    "chocolate": ("Candies, milk chocolate", ""),
    "dates": ("Dates, deglet noor", ""),
    "fruit": (
        "Fruit cocktail, (peach and pineapple and pear and grape and cherry), canned, juice pack, solids and liquids",
        "mixed fruit stands in for unnamed fruit",
    ),
    "mango": ("Mangos, raw", ""),
    "strawberry": ("Strawberries, raw", ""),
    "banana": ("Bananas, raw", ""),
    "apple": ("Apples, raw, with skin (Includes foods for USDA's Food Distribution Program)", ""),
    "pineapple": ("Pineapple, raw, all varieties", ""),
    "pomegranate": ("Pomegranates, raw", ""),
    "raisins": (
        "Raisins, dark, seedless (Includes foods for USDA's Food Distribution Program)",
        "",
    ),
    "apricots": ("Apricots, raw", ""),
    "syrup": ("Syrups, table blends, pancake", ""),
    "caramel": ("Candies, caramels", ""),
    "jam": ("Jams and preserves", ""),
    "tea": ("Beverages, tea, black, brewed, prepared with tap water", ""),
    "coffee": ("Beverages, coffee, brewed, prepared with tap water", ""),
    "soft drink": ("Beverages, carbonated, cola, regular", ""),
    "juice": ("Orange juice, canned, unsweetened", "orange juice stands in for juice in general"),
    "water": ("Beverages, water, tap, drinking", ""),
}
TRACE = {name for name, ing in VOCABULARY.items() if ing.role == "trace"}


def _read(name):
    with open(paths.USDA_SR_DIR / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _suggest(target: str, foods: dict[str, str], n: int = 6) -> list[str]:
    words = {w.strip(",()").lower() for w in target.split() if len(w.strip(",()")) > 3}
    scored = sorted(foods, key=lambda d: (-sum(w in d.lower() for w in words), len(d)))
    return scored[:n]


def build(check_only: bool = False) -> list[dict]:
    foods = {r["description"]: r["fdc_id"] for r in _read("food.csv")}
    names = {r["id"]: f"{r['name']} ({r['unit_name']})" for r in _read("nutrient.csv")}
    print("nutrients used:", {NUTRIENT_IDS[i]: names.get(i) for i in NUTRIENT_IDS})

    missing_choice = [n for n in VOCABULARY if n not in TRACE and n not in CHOICES]
    unresolved = {n: d for n, (d, _) in CHOICES.items() if d not in foods}
    for n in missing_choice:
        print(f"  NO CHOICE for '{n}'")
    for n, d in unresolved.items():
        print(f"  NOT IN SR LEGACY: {n!r}: {d!r}")
        for s in _suggest(d, foods):
            print(f"      maybe: {s}")
    if check_only or missing_choice or unresolved:
        return []

    wanted = {foods[d]: n for n, (d, _) in CHOICES.items()}
    values: dict[str, dict] = {}
    with open(paths.USDA_SR_DIR / "food_nutrient.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["fdc_id"] in wanted and r["nutrient_id"] in NUTRIENT_IDS:
                values.setdefault(r["fdc_id"], {})[NUTRIENT_IDS[r["nutrient_id"]]] = float(
                    r["amount"]
                )

    rows = []
    for name, (desc, note) in CHOICES.items():
        fdc = foods[desc]
        v = values.get(fdc, {})
        rows.append(
            {
                "ingredient": name,
                "kcal": v.get("kcal"),
                "protein": v.get("protein"),
                "fat": v.get("fat"),
                "carbs": v.get("carbs", 0.0),  # USDA omits carbohydrate for foods that have none
                "fdc_id": fdc,
                "usda_description": desc,
                "note": note,
            }
        )
    paths.NUTRITION_REFERENCE.parent.mkdir(parents=True, exist_ok=True)
    with open(paths.NUTRITION_REFERENCE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def load_reference() -> dict[str, dict]:
    """ingredient -> {kcal, protein, fat, carbs} per 100 g, from the built table."""
    with open(paths.NUTRITION_REFERENCE, encoding="utf-8") as f:
        return {
            r["ingredient"]: {k: float(r[k]) for k in ("kcal", "protein", "fat", "carbs")}
            for r in csv.DictReader(f)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Build the ingredient nutrition table from USDA SR Legacy."
    )
    parser.add_argument(
        "--check", action="store_true", help="only report choices that don't resolve"
    )
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rows = build(check_only=args.check)
    if rows:
        incomplete = [r["ingredient"] for r in rows if None in (r["kcal"], r["protein"], r["fat"])]
        print(
            f"wrote {len(rows)} rows -> {paths.NUTRITION_REFERENCE}; incomplete: {incomplete or 'none'}"
        )


if __name__ == "__main__":
    main()

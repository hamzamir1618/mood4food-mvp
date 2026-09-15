"""
Per-serving nutrition estimate from a dish's ingredients (Phase 1).

Keeps the sourcing project's apportioning method (its
NUTRITION_ESTIMATION_METHODOLOGY.md): a category-specific serving weight is
split 50% bulk, 15% fat, 15% vegetables and 20% water and trace ingredients,
shared equally among the ingredients found in each group.

What changes:
  * Values per 100 g come from USDA FoodData Central (pipeline.usda_reference).
    The Open Food Facts matches used before were, for 43 of 82 ingredients, a
    different food entirely (egg: a snack stick; fish: 582 kcal per 100 g;
    rice: wheat).
  * Carbohydrate and fat are reported alongside calories and protein.
  * A dish with no ingredients gets no estimate. Before, it received flour, oil
    and onion defaults and a figure that looked measured.
  * A dish whose only main ingredients are vegetables is treated as a vegetable
    dish (they fill the bulk share) rather than padded with flour.
  * Desserts, drinks and add-ons no longer get the onion default; drinks get no
    oil default, desserts default to butter.
Defaults still applied to a missing group are listed in the result, so the
build can lower its confidence accordingly.
"""

from pipeline.ingredients import VOCABULARY

SERVING_G = {
    "desi_traditional": 400,
    "afghan": 400,
    "chinese_asian": 350,
    "continental_upscale": 350,
    "middle_eastern": 300,
    "pizza": 250,
    "fast_food": 200,
    "sandwich": 200,
    "cafe_bakery": 150,
    "beverages": 300,
    "add_ons": 100,
    "other": 250,
}
SHARES = {"bulk": 0.50, "fat": 0.15, "veg": 0.15}
NUTRIENTS = ("kcal", "protein", "fat", "carbs")


def _defaults(category: str) -> dict:
    return {
        "bulk": None if category == "beverages" else "wheat flour",
        "fat": None
        if category == "beverages"
        else ("butter" if category == "cafe_bakery" else "cooking oil"),
        "veg": None if category in ("cafe_bakery", "beverages", "add_ons") else "onion",
    }


def estimate(ingredients: list[str], category: str, reference: dict) -> dict | None:
    """Calories, protein, fat and carbs for one serving, or None when there are no ingredients."""
    if not ingredients:
        return None
    grams = SERVING_G.get(category, SERVING_G["other"])
    groups = {role: [n for n in ingredients if VOCABULARY[n].role == role] for role in SHARES}
    if not groups["bulk"] and groups["veg"]:
        groups["bulk"] = list(groups["veg"])
    defaults_used = []
    for role, fallback in _defaults(category).items():
        if not groups[role] and fallback:
            groups[role] = [fallback]
            defaults_used.append(fallback)

    totals = dict.fromkeys(NUTRIENTS, 0.0)
    unreferenced = []
    for role, names in groups.items():
        if not names:
            continue
        each_g = grams * SHARES[role] / len(names)
        for name in names:
            ref = reference.get(name)
            if ref is None:
                unreferenced.append(name)
                continue
            for key in NUTRIENTS:
                totals[key] += ref[key] * each_g / 100
    return {
        "calories": round(totals["kcal"], 1),
        "protein_g": round(totals["protein"], 1),
        "fat_g": round(totals["fat"], 1),
        "carbs_g": round(totals["carbs"], 1),
        "serving_g": grams,
        "defaults_used": defaults_used,
        "unreferenced": unreferenced,
    }


def implausible(est: dict | None) -> str:
    """A reason a per-serving estimate cannot be right, or ''."""
    if est is None:
        return ""
    kcal = est["calories"]
    if kcal > 2500:
        return "over 2,500 kcal per serving"
    from_macros = 4 * est["protein_g"] + 4 * est["carbs_g"] + 9 * est["fat_g"]
    if kcal > 50 and abs(from_macros - kcal) / kcal > 0.20:
        return "calories disagree with protein, carbs and fat by more than 20%"
    return ""

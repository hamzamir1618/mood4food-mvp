"""
Per-serving nutrition estimate from a dish's ingredients (Phase 1).

Keeps the sourcing project's apportioning method (its
NUTRITION_ESTIMATION_METHODOLOGY.md): a category-specific serving weight is
split between bulk, fat, vegetables, and water and trace ingredients, shared
equally among the ingredients found in each group. The split is now calibrated
(see SHARES).

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
  * A prepared bread (naan, roti, a bun) is not counted again as wheat flour or as
    generic bread. A plain naan was being estimated as 100 g of flour plus 100 g of naan.
  * Fish or prawn crackers are not counted again as fish or prawns.
Defaults still applied to a missing group are listed in the result, so the
build can lower its confidence accordingly.
"""

import re

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
# The split of a serving, calibrated on 2026-09-21 against USDA SR Legacy's measured restaurant
# dishes (scripts/calibrate_nutrition.py): 113 of our dishes matched 28 of them by name.
# The sourcing project's 50% bulk / 15% fat put pure oil at 15% of every plate's weight,
# 60 g in a desi serving. Measured dishes get a median 44% of their energy from fat; ours
# got 68%, and 78% of dishes read over 50%. At 71% bulk / 7% fat / 15% veg, the median error
# in fat share against the measured dishes fell from +20 to +2 percentage points, with
# calories per 100 g no worse (median error 20.5% before, 19.2% after).
SHARES = {"bulk": 0.71, "fat": 0.07, "veg": 0.15}
NUTRIENTS = ("kcal", "protein", "fat", "carbs")
# A prepared bread already is its flour (and its fat): counting "naan" and "wheat flour"
# side by side weighs the flour twice, and "bread" beside "bun" is the same burger bun.
PREPARED_BREADS = ("naan", "roti", "paratha", "puri", "pita", "tortilla", "bun", "pizza base")
# Crackers already are their fish or prawns: the flavouring is a small share of a starch snack.
CRACKERS = {"fish crackers": "fish", "prawn crackers": "prawns"}
# Fats a dish can be made of, as against the oil, ghee and butter it was cooked in.
FAT_AS_FOOD = frozenset(
    {"cheese", "cream cheese", "cream", "tahini", "almonds", "cashews", "pistachios",
     "peanuts", "walnuts", "coconut", "coconut milk"}
)  # fmt: skip
# A soup is mostly broth. Split like a plate, a hot and sour soup was 250 g of chicken, 749 kcal
# and 74 g of protein, where USDA measures a Chinese restaurant's at 39 kcal per 100 g. In a soup
# the solids are SOUP_SOLIDS of the bowl (split as SHARES) and the rest is broth with no energy,
# calibrated the same way against USDA's measured soups (scripts/calibrate_nutrition.py).
SOUP_NAME = re.compile(
    r"\b(soups?|shorba|shorwa|yakhni|broth|chowder|bisque|consomm[eé]|tom yum|tom kha)\b", re.I
)
# 36 of our soups matched 9 measured ones: as a plate they were +367% on calories per 100 g;
# at 0.20 the median error is 26% (bias -6.5%).
SOUP_SOLIDS = 0.20


def is_soup(name: str) -> bool:
    return bool(SOUP_NAME.search(name or ""))


def _without_duplicates(ingredients: list[str]) -> list[str]:
    """The ingredients without the flour, generic bread or seafood that a prepared bread or
    a cracker already accounts for."""
    prepared = any(n in PREPARED_BREADS for n in ingredients)
    if prepared:
        drop = {"wheat flour", "bread"}
    else:
        drop = {"wheat flour"} if "bread" in ingredients else set()
    drop |= {seafood for cracker, seafood in CRACKERS.items() if cracker in ingredients}
    return [n for n in ingredients if n not in drop] or ingredients


def _defaults(category: str) -> dict:
    return {
        "bulk": None if category == "beverages" else "wheat flour",
        "fat": None
        if category == "beverages"
        else ("butter" if category == "cafe_bakery" else "cooking oil"),
        "veg": None if category in ("cafe_bakery", "beverages", "add_ons") else "onion",
    }


def estimate(
    ingredients: list[str], category: str, reference: dict, soup: bool = False
) -> dict | None:
    """Calories, protein, fat and carbs for one serving, or None when there are no ingredients.
    A soup's solids are SOUP_SOLIDS of its serving; the rest is broth."""
    if not ingredients:
        return None
    grams = SERVING_G.get(category, SERVING_G["other"])
    solids = SOUP_SOLIDS if soup else 1.0
    ingredients = _without_duplicates(ingredients)
    groups = {role: [n for n in ingredients if VOCABULARY[n].role == role] for role in SHARES}
    # A dish with no main ingredient is made of what it does have: a vegetable dish of its
    # vegetables, and a cheese plate of its cheese (which the table calls a fat, so "Jibne
    # Kurdiyey" — cheese and herbs — came out at 61 kcal). Cooking fats never stand in: a
    # "Duck Roast" whose ingredients are oil and soy sauce is not a plate of oil (2,434 kcal).
    if not groups["bulk"]:
        eaten = [n for n in groups["fat"] if n in FAT_AS_FOOD]
        groups["bulk"] = [*groups["veg"], *eaten]
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
        each_g = grams * solids * SHARES[role] / len(names)
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

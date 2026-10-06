"""
Make it a meal: the pick, something to eat with it, something to drink, and the total.

The app recommends a dish. A concierge suggests the meal — this karahi, a naan, a drink, Rs
1,240 altogether — which is also what gives the 153 sides and 332 drinks their purpose. They
are deliberately held out of being *picked* (a plain naan is not an answer to "what should I
eat tonight"), and this is where they belong instead.

Three rules, all plain on purpose. A cleverer pairing model would be guessing, and guessing
about food someone is going to order is the thing this app doesn't do:

  same kitchen    only dishes from the restaurant the pick came from, so the meal is one
                  order at one counter
  same rules      the user's allergies, diet and halal setting apply exactly as they do to the
                  pick, through the one predicate both queries share (SAFE_FOR_THE_USER)
  bread with a    a gravy dish wants bread, anything else takes the plainest side on the menu,
  gravy dish      and the drink is the cheapest they have. Each suggestion says why it is there

The budget, when the user gave one, is a ceiling on the *total*: a meal that takes them over
what they said they'd spend is not a meal they asked for, so it is not offered.
"""

import logging
import re

from tier_1.symbolic_anchoring import SAFE_FOR_THE_USER, exclusion_terms

log = logging.getLogger(__name__)

# A dish served in a sauce, which is what bread is for.
GRAVY = re.compile(
    r"\b(karahi|handi|qorma|korma|curry|masala|daal|dal|gravy|nihari|haleem|saalan|salan|"
    r"qeema|keema|bhuna|tikka masala|butter chicken|paya|shorba|kadai|kadhai)\b",
    re.I,
)
BREAD = re.compile(
    r"\b(naan|nan|roti|paratha|parantha|kulcha|chapati|sheermal|taftan|pita|khubz|bread)\b", re.I
)
# Sides that are sides rather than a small meal of their own.
PLAIN_SIDE = re.compile(r"\b(rice|chawal|fries|salad|raita|chutney|yogurt|dahi|soup)\b", re.I)
# Drinks a person orders without thinking about it, ahead of a Rs 570 pressed juice.
PLAIN_DRINK = re.compile(
    r"\b(water|cola|coke|pepsi|sprite|7 ?up|dew|soft drink|drink|lassi|chai|tea|coffee|"
    r"lemonade|limca|fanta|mineral)\b",
    re.I,
)

ALONGSIDE_CYPHER = (
    """
MATCH (d:Dish)
WHERE d.restaurant_name = $restaurant
  AND d.category IN ['add_ons', 'beverages']
  AND coalesce(d.dish_uid, elementId(d)) <> $winner_id
  AND d.price_rs IS NOT NULL AND d.price_rs > 0
  AND """
    + SAFE_FOR_THE_USER
    + """
RETURN coalesce(d.dish_uid, elementId(d)) AS dish_id, d.name AS name, d.category AS category,
       d.price_rs AS price_pkr, d.allergens AS allergens, d.allergens_known AS allergens_known,
       d.calories AS calories, d.is_vegan AS is_vegan, d.is_vegetarian AS is_vegetarian
ORDER BY d.price_rs
"""
)


def alongside(restaurant: str, winner_id: str, intent: dict) -> list[dict]:
    """
    Everything else on that restaurant's menu this person may be offered.

    The dietary half of the intent is read exactly as the pick read it — same exclusions, same
    vegan, vegetarian and halal flags — so a side can never be suggested that the pick itself
    would have been rejected for.
    """
    allergens = list(intent.get("excluded_ingredients") or intent.get("allergens") or [])
    excluded_allergens, excluded_ingredients = exclusion_terms(allergens)
    pruned_list = sorted({a.strip().lower() for a in allergens} | set(excluded_allergens))
    try:
        from accounts.store import get_driver

        records, _, _ = get_driver().execute_query(
            ALONGSIDE_CYPHER,
            restaurant=restaurant,
            winner_id=winner_id,
            pruned_list=pruned_list,
            excluded_ingredients=excluded_ingredients,
            req_vegan=bool(intent.get("is_vegan")) or "vegan" in pruned_list,
            req_veg=bool(intent.get("is_vegetarian")) or "vegetarian" in pruned_list,
            req_halal=bool(intent.get("is_halal")),
        )
        return [dict(r) for r in records]
    except Exception as exc:
        # Nothing to add is a fine answer; a wrong suggestion is not.
        log.warning("what else is on that menu could not be read: %s", exc)
        return []


def _cheapest(options: list[dict], wanted: re.Pattern | None = None) -> dict | None:
    """The cheapest option, preferring ones whose name matches `wanted`."""
    if wanted:
        named = [o for o in options if wanted.search(o["name"] or "")]
        if named:
            options = named
    return min(options, key=lambda o: (o["price_pkr"], o["name"])) if options else None


def to_eat_with(main: dict, options: list[dict]) -> dict | None:
    """
    Something to eat alongside, and why it is there.

    A dish served in a sauce wants bread; anything else takes the plainest side the kitchen
    has. Where neither reads as plain, nothing is suggested rather than something arbitrary.
    """
    sides = [o for o in options if o["category"] == "add_ons"]
    if not sides:
        return None
    name = main.get("name") or ""
    if GRAVY.search(name):
        bread = _cheapest(sides, BREAD)
        if bread and BREAD.search(bread["name"] or ""):
            return {**bread, "why": f"{name} is served in a sauce, so it wants bread."}
    plain = _cheapest(sides, PLAIN_SIDE)
    if plain and PLAIN_SIDE.search(plain["name"] or ""):
        return {**plain, "why": "The plainest side on their menu."}
    return None


def to_drink(options: list[dict]) -> dict | None:
    """The cheapest ordinary drink they have, ahead of a pressed juice at four times the price."""
    drinks = [o for o in options if o["category"] == "beverages"]
    if not drinks:
        return None
    drink = _cheapest(drinks, PLAIN_DRINK)
    ordinary = bool(PLAIN_DRINK.search(drink["name"] or ""))
    return {
        **drink,
        "why": (
            "The cheapest ordinary drink they have."
            if ordinary
            else "The cheapest drink on their menu."
        ),
    }


def make_a_meal(
    main: dict, options: list[dict], party_size: int = 1, ceiling: float | None = None
) -> dict:
    """
    The pick, what to eat with it, what to drink, and what it comes to.

    `ceiling` is what the user said they'd spend, and it applies to the whole order, not to
    the dish alone: a meal that takes them over it is not offered, and the reply says the
    budget is why. Each part carries its own price so the total is arithmetic the reader can
    check, not a number to trust.
    """
    main_price = float(main.get("price_pkr") or 0)
    left = (ceiling - main_price) if ceiling else None
    affordable = [o for o in options if left is None or float(o["price_pkr"]) <= left]

    parts, spent = [], main_price
    for part in (to_eat_with(main, affordable), to_drink(affordable)):
        if not part:
            continue
        price = float(part["price_pkr"])
        if left is not None and spent + price > ceiling:
            continue  # the second part is what usually doesn't fit, and it is the one to drop
        parts.append(part)
        spent += price

    meal = {
        "restaurant_name": main.get("restaurant_name"),
        "main": {"name": main.get("name"), "price_pkr": main_price},
        "parts": parts,
        "total_pkr": round(spent),
        "party_size": max(1, int(party_size or 1)),
    }
    meal["per_person_pkr"] = round(spent / meal["party_size"])
    if not parts:
        meal["note"] = (
            f"Nothing else on their menu fits under Rs {round(ceiling):,}."
            if ceiling and options
            else "They don't list anything else to go with it."
        )
    return meal

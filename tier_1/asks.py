"""
What a request asked for, one thing at a time.

"Spicy chicken under 200" is three asks: spicy, chicken, Rs 200 or less. Tier 1 enforces them as
filters. When the menus can't meet all of them, it used to drop a word and take whatever was
left — "chicken" went, and a kulfi won "spicy chicken under 200". With each ask a test a dish
meets fully, partly or not at all, the app can instead:

  - put the dishes closest to the request first (`closeness`), and say which asks each meets;
  - say exactly what couldn't be had, and why (ui/walkthrough.py);
  - offer the other ways to read the request — give up the limit, or the spice — with the dish
    that would win each (tier_2/trade_offs.py).

Allergies, diet, halal and exclusions are never asks. They are rules, and nothing in this module
can loosen one. A request that asks for something its own rules forbid ("vegan chicken karahi")
is a conflict, and the rule wins (`conflicts`).

How alike two dishes are (`FAMILIES`) is a judgement written down here, not something read
from data: a curry stands in for a karahi, a pulao for a biryani.
"""

import functools
import re
from dataclasses import dataclass

from pipeline.ingredients import ALLERGEN_TAGS, VOCABULARY, derive_diet_flags, detect_ingredients

MOOD_FLOOR = 0.4  # a dish this strong in a flavour has it (Tier 1's mood filter uses the same)
MOOD_HINT = 0.2  # ...and one this strong has a little of it
TASTE_WORDS = {
    "spice": "spicy",
    "sweet": "sweet",
    "salty": "salty",
    "sour": "sour",
    "bitter": "bitter",
    "umami": "savoury",
}
CUISINE_WORDS = {
    "desi_traditional": "desi",
    "afghan": "Afghan",
    "middle_eastern": "Middle Eastern",
    "chinese_asian": "Chinese or Asian",
    "continental_upscale": "continental",
    "fast_food": "fast food",
    "pizza": "pizza",
    "sandwich": "sandwich",
    "cafe_bakery": "café",
}
# Dishes that stand in for one another. A dish asked for by name that isn't there is better
# answered with another of its kind than with whatever scores best. Each family also names the
# words a menu uses for its members when they aren't one of the named dishes ("Chicken Masala").
FAMILIES = {
    "a curry": (
        ("karahi", "handi", "korma", "qeema", "daal", "nihari", "haleem", "paye"),
        ("curry", "masala", "salan", "saalan", "makhni", "makhani", "bhuna", "jalfrezi", "qorma"),
    ),
    "a rice dish": (
        ("biryani", "pulao", "kabuli pulao", "mandi", "kabsa", "fried rice"),
        ("rice", "chawal"),
    ),
    "a grill or barbecue": (
        (
            "tikka",
            "kebab",
            "boti",
            "malai boti",
            "sajji",
            "chapli",
            "bihari",
            "tandoori",
            "shashlik",
            "chargha",
            "kofta",
            "shinwari",
        ),
        ("grill", "grilled", "bbq", "seekh", "barbecue"),
    ),  # fmt: skip
    "something in bread": (
        ("burger", "sandwich", "wrap", "shawarma", "doner", "taco", "quesadilla", "falafel"),
        ("roll", "panini", "sub", "club"),
    ),
    "noodles or pasta": (
        ("chow mein", "ramen", "pasta", "lasagna"),
        ("noodle", "noodles", "spaghetti", "fettuccine", "penne", "macaroni"),
    ),
    "a sweet": (
        ("halwa", "kheer", "firni", "gulab jamun", "jalebi", "cheesecake", "brownie"),
        ("cake", "dessert", "pudding", "kulfi", "ice cream", "sundae", "mousse", "custard"),
    ),
    "a desi breakfast": (("halwa puri", "puri", "paratha", "chaat"), ("nashta", "channay")),
    "a snack": (("samosa", "pakora", "chaat", "wings", "broast"), ("fries", "nuggets", "rolls")),
    "a dumpling or sushi": (("dumpling", "sushi"), ("wonton", "dim sum", "gyoza")),
    "a soup": (("soup",), ("shorba", "broth")),
    "a salad": (("salad",), ("greens",)),
}


@dataclass(frozen=True)
class Ask:
    """One thing a request asked for. `id` is stable: it is what a trade-off sets aside."""

    id: str  # "budget", "dish:karahi", "food:chicken", "cuisine:afghan", "taste:spice"
    kind: str  # budget | dish | food | cuisine | taste
    key: str  # the dish, food, category or flavour; the limit for a budget
    words: str  # how a sentence names it: "Rs 200 or less", "karahi", "chicken", "spicy"


def rupees(amount: float) -> str:
    return f"Rs {round(amount):,}"


def _spellings(dish: str) -> tuple[str, ...]:
    from tier_1.symbolic_anchoring import DISH_NAMES

    return DISH_NAMES.get(dish, (dish,))


def _names(words: tuple[str, ...]) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")s?\b", re.I)


def family_of(dish: str) -> tuple[str, re.Pattern] | None:
    """The family a named dish belongs to, as (its name, a pattern for its other members)."""
    for name, (members, words) in FAMILIES.items():
        if dish in members:
            others = [s for m in members if m != dish for s in _spellings(m)]
            return name, _names((*others, *words))
    return None


@functools.cache
def _family_patterns() -> dict[str, re.Pattern]:
    """Every family's members and words, as one pattern each."""
    return {
        name: _names((*(s for m in members for s in _spellings(m)), *words))
        for name, (members, words) in FAMILIES.items()
    }


def _food_terms(key: str) -> tuple[str, ...]:
    from tier_1.symbolic_anchoring import FOOD_GROUPS

    return FOOD_GROUPS.get(key) or ((key,) if key in VOCABULARY else ())


def asks_of(intent: dict) -> list[Ask]:
    """Everything the request asked for, minus what it has since set aside."""
    from tier_1.symbolic_anchoring import (
        CATEGORIES,
        DISH_NAMES,
        asked_proteins,
        get_dominant_mood,
        named_dishes,
    )

    aside = set(intent.get("set_aside") or [])
    out: dict[str, Ask] = {}

    def add(ask: Ask) -> None:
        if ask.id not in aside and ask.id not in out:
            out[ask.id] = ask

    budget = intent.get("budget_max_pkr")
    if budget:
        add(Ask("budget", "budget", str(float(budget)), f"{rupees(float(budget))} or less"))

    mood = {k: float(v or 0) for k, v in (intent.get("mood_vector") or {}).items()}
    dominant = get_dominant_mood(mood)
    if dominant:
        add(Ask(f"taste:{dominant}", "taste", dominant, TASTE_WORDS.get(dominant, dominant)))

    term = (intent.get("preferred_category") or "").strip().lower()
    if term == "dessert":
        term = "cafe_bakery"
    if term:
        key = term.replace(" ", "_")
        if len(key) >= 3 and any(key in c for c in CATEGORIES):
            category = next(c for c in CATEGORIES if key in c)
            add(Ask(f"cuisine:{category}", "cuisine", category, CUISINE_WORDS[category]))
        elif term in DISH_NAMES:
            add(Ask(f"dish:{term}", "dish", term, term))
        else:
            add(Ask(f"food:{term}", "food", term, term))
    for dish in named_dishes(intent):
        add(Ask(f"dish:{dish}", "dish", dish, dish))
    for food in sorted(asked_proteins(intent)):
        add(Ask(f"food:{food}", "food", food, food))
    return list(out.values())


def degree(ask: Ask, dish: dict) -> float:
    """1 when the dish meets the ask, 0.5 when it comes close, 0 when it doesn't."""
    name = dish.get("name") or ""
    if ask.kind == "budget":
        price = dish.get("price_pkr")
        return 1.0 if price is None or float(price) <= float(ask.key) else 0.0
    if ask.kind == "taste":
        value = float((dish.get("taste_profile") or {}).get(ask.key) or 0.0)
        return 1.0 if value >= MOOD_FLOOR else 0.5 if value >= MOOD_HINT else 0.0
    if ask.kind == "cuisine":
        return 1.0 if (dish.get("category") or "") == ask.key else 0.0
    if ask.kind == "dish":
        if _names(_spellings(ask.key)).search(name):
            return 1.0
        family = family_of(ask.key)
        if not family or not family[1].search(name):
            return 0.0
        # "Masala Fried Rice" says masala but is a rice dish: a dish another family claims
        # isn't a stand-in for this one.
        claimed = any(
            p.search(name) for other, p in _family_patterns().items() if other != family[0]
        )
        return 0.0 if claimed else 0.5
    # food: a dish that names it is what was meant; one that only lists it is close
    terms = _food_terms(ask.key)
    if not terms:
        if ask.key in ALLERGEN_TAGS:
            return 1.0 if ask.key in (dish.get("allergens") or []) else 0.0
        return 1.0 if re.search(rf"\b{re.escape(ask.key)}", name, re.I) else 0.0
    if set(terms) & set(detect_ingredients(name)):
        return 1.0
    return 0.5 if set(terms) & set(dish.get("ingredients") or []) else 0.0


def how_met(ask: Ask, value: float) -> tuple[str, str]:
    """The ask as a dish meets it: a short tag, and a clause for "it ..."."""
    if ask.kind == "food":
        if value >= 1:
            return ask.words, f"has {ask.words}"
        return f"{ask.words} inside", f"lists {ask.words} among its ingredients"
    if ask.kind == "taste":
        return (
            (ask.words, f"is {ask.words}")
            if value >= 1
            else (
                f"a little {ask.words}",
                f"is a little {ask.words}",
            )
        )
    if ask.kind == "dish":
        if value >= 1:
            return ask.words, f"is a {ask.words}"
        family = family_of(ask.key)
        kind = family[0] if family else "something like it"
        return kind, f"is {kind}, like a {ask.words}"
    return ask.words, f"is {ask.words}"


def meets(asks: list[Ask], dish: dict) -> list[dict]:
    """The asks this dish meets or comes close to, strongest first."""
    found = [(a, degree(a, dish)) for a in asks if a.kind != "budget"]
    out = []
    for a, v in sorted(found, key=lambda av: -av[1]):
        if v > 0:
            tag, clause = how_met(a, v)
            out.append({"id": a.id, "degree": v, "words": tag, "clause": clause})
    return out


def closeness(asks: list[Ask], dish: dict) -> float:
    """How much of the request a dish meets, the limit aside (Tier 1 already enforced it)."""
    return round(sum(degree(a, dish) for a in asks if a.kind != "budget"), 3)


def phrase(asks: list[Ask]) -> str:
    """The request in a few words, as a menu would say it: "spicy chicken karahi"."""
    order = {"taste": 0, "cuisine": 1, "food": 2, "dish": 3}
    words = [a.words for a in sorted(asks, key=lambda a: order.get(a.kind, 9)) if a.kind in order]
    return " ".join(words)


# ── Conflicts: asking for what your own rules forbid ─────────────────────────
def rules_of(intent: dict) -> dict:
    """The rules a request carries, read the way Tier 1 reads them."""
    from tier_1.symbolic_anchoring import exclusion_terms

    pruned = [str(a).strip().lower() for a in intent.get("allergens_pruned") or []]
    allergens, ingredients = exclusion_terms(pruned)
    return {
        "vegan": bool(intent.get("is_vegan")) or "vegan" in pruned,
        "vegetarian": bool(intent.get("is_vegetarian")) or "vegetarian" in pruned,
        "halal": bool(intent.get("is_halal")),
        "allergens": sorted(set(allergens) | {a for a in pruned if a in ALLERGEN_TAGS}),
        "ingredients": ingredients,
    }


def conflicts(intent: dict) -> list[dict]:
    """
    Foods the request asks for that its own rules rule out: chicken for a vegan, paneer for
    someone avoiding dairy. The rule always wins, so these are set aside, and said.
    """
    rules = rules_of(intent)
    found = []
    for ask in asks_of(intent):
        if ask.kind != "food":
            continue
        terms = [t for t in _food_terms(ask.key) if t in VOCABULARY]
        if not terms:
            continue
        flags = derive_diet_flags(terms)
        reason = None
        if rules["vegan"] and not flags["is_vegan"]:
            reason = f"{ask.words} isn't vegan"
        elif rules["vegetarian"] and not flags["is_vegetarian"]:
            reason = f"{ask.words} isn't vegetarian"
        elif rules["halal"] and not flags["is_halal"]:
            reason = f"{ask.words} isn't halal"
        elif clash := sorted(set(flags["allergens"]) & set(rules["allergens"])):
            reason = f"{ask.words} has {' and '.join(clash)}, which you're avoiding"
        elif set(terms) <= set(rules["ingredients"]):
            reason = f"you asked for no {ask.words}"
        if reason:
            found.append({"id": ask.id, "words": ask.words, "reason": reason})
    return found

"""
Refinements, known in recommender research as critiquing: each asks for a dish better
than the current pick in one direction ("cheaper than this", "milder than this"), and is
applied to the candidates the query already found.
"""

import re

CRITIQUES = {
    "cheaper": "Cheaper",
    "lighter": "Lighter",
    "healthier": "Healthier",
    "more_filling": "More filling",
    "spicier": "Spicier",
    "milder": "Milder",
    "different": "Something different",
}
WORDS = {
    "cheaper": "cheaper",
    "lighter": "lighter",
    "healthier": "healthier",
    "more_filling": "more filling",
    "spicier": "spicier",
    "milder": "milder",
    "different": "different",
}
# Checked in order, so "less spicy" is read as milder before "spicy" can match spicier.
PATTERNS = (
    ("milder", r"\b(milder|less spicy|not (so |too )?spicy|too spicy|less hot)\b"),
    ("spicier", r"\b(spicier|more spicy|hotter|more heat|extra spicy)\b"),
    ("cheaper", r"\b(cheaper|less expensive|lower price|too expensive|too pricey)\b"),
    ("more_filling", r"\b(more filling|heavier|bigger|more food|still hungry)\b"),
    ("lighter", r"\b(lighter|less heavy|fewer calories|low[- ]?cal(orie)?)\b"),
    ("healthier", r"\b(healthier|more healthy|something healthy)\b"),
    ("different", r"\b(something (else|different)|different|another (one|cuisine)|not this)\b"),
)
MAX_WORDS = 8  # longer messages are read as a new request


def parse(text: str) -> str | None:
    """A short message that asks for a refinement, as the critique's name."""
    if len(text.split()) > MAX_WORDS:
        return None
    lowered = text.lower()
    return next((name for name, pattern in PATTERNS if re.search(pattern, lowered)), None)


def adjustment(critique: str, winner: dict, utilities: dict) -> dict | None:
    """The change that asks for a dish better than `winner` this way; None without the data."""
    price = float(winner.get("price_pkr") or 0.0)
    kcal = (winner.get("macros") or {}).get("calories")
    spice = float((winner.get("taste_profile") or {}).get("spice") or 0.0)
    if critique == "cheaper":
        return {"price_below": price}
    if critique == "lighter":
        return {"calories_below": kcal, "goal": "light"} if kcal else None
    if critique == "more_filling":
        return {"calories_above": kcal} if kcal else None
    if critique == "spicier":
        return {"spice_above": spice, "craved": {"spice": min(1.0, spice + 0.3)}}
    if critique == "milder":
        return (
            {"spice_below": spice, "craved": {"spice": max(0.05, spice - 0.3)}} if spice else None
        )
    if critique == "healthier":
        health = utilities.get("u_health")
        return {"health_above": health} if health is not None else None
    if critique == "different":
        return {"exclude_categories": [winner["category"]]} if winner.get("category") else None
    return None


def missing(critique: str, winner: dict) -> str:
    """Why a refinement can't be applied to this dish."""
    name = winner.get("name", "this dish")
    if critique in ("lighter", "more_filling"):
        return f"I don't have a calorie estimate for {name}, so I can't compare."
    if critique == "healthier":
        return f"I couldn't assess {name}'s nutrition, so I can't find something healthier."
    if critique == "milder":
        return f"{name} isn't spicy at all."
    return f"I don't know {name}'s cuisine, so I can't look for a different one."

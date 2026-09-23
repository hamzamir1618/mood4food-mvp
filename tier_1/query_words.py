"""
What the words say that the extractor's fields can't carry (Phase 3, 2026-09-21).

`GroundedIntent` has nine fields: a budget, allergens, six tastes, halal, vegan, vegetarian
and a category. A word sweep found that everything else a person might say was dropped in
silence: "nut allergy" by the fallback, and "healthy", "keto", "grilled", "for 4 people",
"in F-7", "pescatarian", "no onion", "popular" by both extractors.

Rather than widen the schema (and the prompt) for each one, the words are read here, by rule,
after extraction, so both the Groq extractor and the keyword fallback get the same reading:

  - dislikes and pescatarian become exclusions, which Tier 1 already applies as hard filters;
  - a cooking method narrows the pool (tier_1/symbolic_anchoring.py);
  - an area sets the location for this request (api/pipeline.py);
  - price level and nutrition goals lean the weights (tier_2/scoring.py reads them);
  - what the app genuinely cannot do is *said*, not ignored (`unsupported`).

Everything here only ever adds a constraint the user asked for, and each rule names the words
that trigger it.
"""

import re

from pipeline.ingredients import SPELLING_TO_NAMES, VOCABULARY

# "No onion", "without garlic", "hold the mayo", "no onion or garlic": the words right after
# the negation, up to a stop word. The scope is deliberately short — the exclusion in
# tier_1/symbolic_anchoring.py runs on through lists, and a long scope excluded whole meals.
_NEGATION = r"(?:no|without|hold the|skip|minus|avoid|don'?t want|can'?t eat|allergic to)"
_DISLIKE = re.compile(rf"\b{_NEGATION}\s+((?:[\w'-]+(?:\s+(?:or|and|,)\s*)?){{1,4}})", re.I)
_STOP = {
    "too", "much", "very", "more", "less", "a", "an", "the", "any", "some", "please",
    "i", "it", "that", "this", "with", "but", "and", "or", "spicy", "sweet", "sour",
    "salty", "bitter", "hot", "mild", "expensive", "cheap", "heavy", "oily", "fried",
}  # fmt: skip
PESCATARIAN = re.compile(r"\b(pescatarian|pescetarian|no meat but fish|fish but no meat)\b", re.I)
# Land meat, as tier_1/symbolic_anchoring.py's FOOD_GROUPS defines it: fish and prawns stay.
PESCATARIAN_EXCLUDES = "meat"

GRILLED = re.compile(
    r"\b(grilled|grill|bbq|barbecue|barbeque|tandoori|roast(ed)?|smoked|char[- ]?grilled|"
    r"not fried|no(t| ) deep[- ]fried|nothing fried|not oily|less oil)\b",
    re.I,
)
FRIED = re.compile(
    r"\b(fried|deep[- ]fried|crispy|broast(ed)?|tempura|katsu|pakora|nuggets?)\b", re.I
)
NOT_FRIED = re.compile(
    r"\b(not|no|nothing|non)[- ]?(too |very |so )?(deep[- ])?(fried|oily|greasy)\b", re.I
)
# Grilled names in the data: what a dish is called when it is cooked this way.
GRILLED_NAME = re.compile(
    r"\b(grill(ed)?|bbq|barbecue|tandoori|tikka|seekh|sajji|kebab|kabab|shawarma|steak|"
    r"roast(ed)?|smoked|shashlik|boti)\b",
    re.I,
)

# An Islamabad sector or a named place, so "something desi in F-7" measures from F-7.
SECTOR = re.compile(r"\b([a-i])[-\s]?(\d{1,2})\b", re.I)
# Worth looking the areas up for: a sector, or a word people use for a place. The lookup is a
# database read, so an ordinary request ("something spicy") never pays for it.
PLACE_WORDS = re.compile(r"\b(area|markaz|sector|town|chowk|road|enclave|near|close to)\b", re.I)


def mentions_a_place(text: str) -> bool:
    said = text or ""
    return bool(SECTOR.search(said) or PLACE_WORDS.search(said))


# "Near me" with no location: the app has no way to know where the user is until they choose.
NEAR_ME = re.compile(r"\b(near(by| me| here)?|close to me|around me|walking distance)\b", re.I)


def asks_for_nearby(text: str) -> bool:
    return bool(NEAR_ME.search(text or ""))


# What the app cannot do. Saying so is the difference between a silent miss and an honest one.
UNSUPPORTED = (
    (
        re.compile(
            r"\b(popular|best[- ]?sell(er|ing)|famous|trending|most ordered|top rated)\b", re.I
        ),
        "sort dishes by how popular they are",
    ),
    (
        re.compile(r"\b(quick(ly)?|fast(est)?|in a hurry|asap|ready in|takes? long)\b", re.I),
        "know how long a dish takes to make",
    ),
    (
        re.compile(r"\b(deliver(y|ed)?|takeaway|take[- ]away|home delivery|foodpanda)\b", re.I),
        "check what's available for delivery",
    ),
    (
        re.compile(r"\b(open now|still open|closing|timings?|opening hours)\b", re.I),
        "know a restaurant's opening hours",
    ),
    (
        re.compile(
            r"\b(kid[- ]friendly|for kids|for children|date night|romantic|ambien[ct]e|"
            r"seating|outdoor|rooftop)\b",
            re.I,
        ),
        "judge a restaurant's atmosphere",
    ),
    (
        re.compile(r"\b(cold|chilled|iced|piping hot|served hot)\b", re.I),
        "know how a dish is served",
    ),
)


def dislikes(text: str) -> list[str]:
    """Vocabulary ingredients the words ask to leave out ("no onion" -> ["onion"])."""
    found: list[str] = []
    for match in _DISLIKE.finditer(text or ""):
        for word in re.split(r"[\s,]+(?:or|and)?\s*", match.group(1)):
            word = word.strip(".,!?;:'\" ").lower()
            if not word or word in _STOP:
                break  # the negation's scope ends at anything that isn't a food
            for name in SPELLING_TO_NAMES.get(word, ()):
                if name not in found and VOCABULARY[name].role != "trace":
                    found.append(name)
    return found


def excluded_foods(text: str) -> list[str]:
    """Everything the words exclude: dislikes, and land meat for a pescatarian."""
    out = list(dislikes(text))
    if PESCATARIAN.search(text or "") and PESCATARIAN_EXCLUDES not in out:
        out.append(PESCATARIAN_EXCLUDES)
    return out


def cooking_asked(text: str) -> str | None:
    """ "grilled" or "fried" when the words ask for it, else None. Avoiding frying asks for
    grilled, which is what the menus name."""
    said = text or ""
    if GRILLED.search(said) or NOT_FRIED.search(said):
        return "grilled"
    return "fried" if FRIED.search(said) else None


def avoids_frying(text: str) -> bool:
    return bool(NOT_FRIED.search(text or ""))


def area_asked(text: str, areas: list[dict]) -> dict | None:
    """The area the words name, as {lat, lng, label}, matched against the areas on offer."""
    said = (text or "").lower()
    for area in areas:
        name = str(area.get("area") or "")
        if not name:
            continue
        if name.lower() in said:
            return {"lat": area["lat"], "lng": area["lng"], "label": name[:40]}
    for match in SECTOR.finditer(said):  # "f7", "f 7" and "f-7" all mean F-7
        wanted = f"{match.group(1).upper()}-{int(match.group(2))}"
        for area in areas:
            if str(area.get("area") or "").upper() == wanted:
                return {"lat": area["lat"], "lng": area["lng"], "label": wanted}
    return None


# How a dish is cooked is not a food to ask for: the vocabulary lists "fried" as a spelling of
# cooking oil, so "nothing fried" was read as a request for fried food.
METHOD_WORDS = frozenset(
    {"fried", "deep fried", "crispy", "grilled", "roasted", "smoked", "broast", "broasted"}
)


# A food the request asks *for*, when the extractor named no category. Groq returns nothing
# for "something with dairy", so any dish could win it. Checked longest spelling first, so
# "fish crackers" wins over "fish", and never for a food the request excludes.
def wanted_food(text: str, allergen_tags: tuple, food_groups: tuple) -> str | None:
    """The food or allergen group the words ask for ("something with dairy" -> "dairy")."""
    said = (text or "").lower()
    if not said:
        return None
    excluded = set(dislikes(said))
    named = sorted(
        (
            spelling
            for spelling in (*allergen_tags, *food_groups, *SPELLING_TO_NAMES)
            if spelling not in METHOD_WORDS and re.search(rf"\b{re.escape(spelling)}\b", said)
        ),
        key=len,
        reverse=True,
    )
    for spelling in named:
        if re.search(rf"{_NEGATION}\s+(?:\w+\s+){{0,2}}{re.escape(spelling)}\b", said):
            continue  # "no cheese" asks for the opposite
        if set(SPELLING_TO_NAMES.get(spelling, ())) & excluded:
            continue
        return spelling
    return None


def unsupported(text: str) -> list[str]:
    """What the request asks for that the app has no data for, in plain phrases."""
    said = text or ""
    return [phrase for pattern, phrase in UNSUPPORTED if pattern.search(said)]

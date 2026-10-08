"""
Is this a request for food at all? The out-of-domain check, run before anything else reads it.

Before this, "(" or "what is the capital of France" went to the extractor, came back with no
constraints, and the app asked "What are you in the mood for?" as though it had understood. Now a
request has to say something about food — a dish, an ingredient, a flavour, a meal, a price, a
diet, a mood, a hunger — before the pipeline runs. It runs before the intent extractor, so a
request that isn't about food never spends a language-model call.

It is a lexicon check, deliberately. Every word that counts is listed here or read from the
data (the ingredient vocabulary, the dish names the app knows, every dish name on the menus), so
a refusal can always say why, and a word that should have counted can be added and tested. A
misspelling close to a known word counts too ("chiken", "biriyani"), measured by edit similarity.

Three answers besides "yes": nothing in it but symbols or numbers; a greeting; and writing in a
script the app can't read yet (Urdu and Arabic script — Roman Urdu is read).
"""

import difflib
import functools
import logging
import re
import time
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

SIMILAR = 0.84  # how close a misspelling must be to a known word to count as it
SIMILAR_MIN_LENGTH = 5  # shorter words are too easily close to something by accident
NAMES_TTL = 15 * 60  # the menus' own words are re-read this often

# Words that make a request about food even though no dish or ingredient is named.
FOOD_WORDS = frozenset(
    """
    eat eating eaten ate food foods foodie hungry hunger hangry starving starved peckish
    craving crave craves cravings dish dishes meal meals menu menus restaurant restaurants
    order ordering takeaway lunch dinner breakfast brunch supper snack snacks nashta iftar
    sehri sehr dessert desserts drink drinks thirsty beverage bite munch munchies feed fed
    tonight midnight late
    something anything whatever surprise recommend recommendation suggest suggestion pick
    choose decide
    spicy spice spiced hot mild sweet sour tangy salty savoury savory umami bitter zesty
    cheesy creamy crispy crunchy juicy smoky fresh rich heavy light greasy oily tasty
    delicious yummy flavour flavor flavours flavors
    healthy healthier protein calorie calories keto carb carbs diet dieting filling hearty
    vegan vegetarian veg halal pescatarian allergy allergic allergies intolerant
    cheap cheaper cheapest affordable budget expensive fancy premium treat rs rupees pkr
    price under below
    grilled fried roasted baked bbq barbecue steamed tandoori
    desi pakistani afghan arabic turkish lebanese chinese asian thai japanese continental
    italian mexican american fast cafe café bakery
    sad happy tired stressed bored lazy sick ill cold rainy celebrate celebrating comfort
    cozy cosy homesick upset exhausted mood feeling
    khana khaana bhook bhookh bhooka bhooki mirch mirchi teekha teekhi meetha meethi namkeen
    khatta garam thanda gosht sabzi anda machli chawal kuch acha achha sasta
    gol gappay gappe golgappay golgappe panipuri bhallay bhalle chholay cholay channay
    chanay bun kabab kababs lassi chai doodh patti
    """.split()
)
GREETINGS = frozenset(
    """
    hi hello hey hiya yo salam salaam assalam assalamualaikum aoa thanks thank ok okay there
    good morning afternoon evening
    """.split()
)
# Words that carry nothing alone ("the", "special"): never evidence of food, however often a
# menu prints them.
NOT_EVIDENCE = frozenset(
    """
    the and with for from of in on at to a an or is it its this that what who how why when
    where which are was be you your my me i we our special house classic deal deals new
    original signature regular large small medium half full single double family style
    platter combo plate box bowl piece pieces pcs serving mini jumbo
    """.split()
)
SCRIPT = re.compile(r"[؀-ۿݐ-ݿ]")  # Arabic and Urdu
WORD = re.compile(r"[a-zà-ÿ]+(?:'[a-z]+)?", re.I)
SECTOR = re.compile(r"\b[a-i]-?\d{1,2}\b", re.I)  # "F-7": a place to eat in


@dataclass
class Verdict:
    food: bool
    kind: str  # food | empty | greeting | script | other
    heard: list[str] = field(default_factory=list)  # the words that made it about food
    reply: str = ""


@functools.cache
def _known_words() -> frozenset[str]:
    """Every word the app knows as food, without the database."""
    from pipeline.ingredients import ALLERGEN_TAGS, SPELLING_TO_NAMES
    from tier_1.asks import FAMILIES
    from tier_1.symbolic_anchoring import CATEGORIES, DISH_NAMES, FOOD_GROUPS

    phrases = [
        *SPELLING_TO_NAMES,
        *ALLERGEN_TAGS,
        *FOOD_GROUPS,
        *(s for spellings in DISH_NAMES.values() for s in spellings),
        *(w for members, words in FAMILIES.values() for w in (*members, *words)),
        *(c.replace("_", " ") for c in CATEGORIES),
    ]
    words = {w for p in phrases for w in WORD.findall(p.lower())}
    return frozenset((words | FOOD_WORDS) - NOT_EVIDENCE)


_MENU: dict = {"at": 0.0, "words": frozenset()}


def _menu_words() -> frozenset[str]:
    """Words from every dish name on the menus. Read from the graph; empty if it can't be."""
    if time.monotonic() - _MENU["at"] < NAMES_TTL:
        return _MENU["words"]
    words: set[str] = set()
    try:
        from accounts.store import get_driver

        records, _, _ = get_driver().execute_query("MATCH (d:Dish) RETURN d.name AS name")
        for r in records:
            words.update(w for w in WORD.findall((r["name"] or "").lower()) if len(w) >= 4)
    except Exception as exc:  # the built-in words still stand
        log.warning("dish names couldn't be read for the food check: %s", exc)
    _MENU.update(at=time.monotonic(), words=frozenset(words - NOT_EVIDENCE))
    return _MENU["words"]


def _vocabulary() -> frozenset[str]:
    return _known_words() | _menu_words()


def _sounds_like(word: str, known: frozenset[str]) -> str | None:
    if len(word) < SIMILAR_MIN_LENGTH:
        return None
    close = difflib.get_close_matches(word, known, n=1, cutoff=SIMILAR)
    return close[0] if close else None


def check(text: str) -> Verdict:
    """Whether a request is about food, and if not, what to say."""
    said = (text or "").strip()
    words = [w.lower() for w in WORD.findall(said)]
    if not words:
        if SCRIPT.search(said):
            return Verdict(False, "script", reply=SCRIPT_REPLY)
        return Verdict(False, "empty", reply=EMPTY_REPLY)

    known = _vocabulary()
    heard = [w for w in words if w in known]
    if not heard:
        heard = [f"{w} (as {m})" for w in words if (m := _sounds_like(w, known))]
    if not heard and SECTOR.search(said):
        heard = SECTOR.findall(said)
    if heard:
        return Verdict(True, "food", heard)
    if any(w in GREETINGS for w in words) and all(
        w in GREETINGS or w in NOT_EVIDENCE for w in words
    ):
        return Verdict(False, "greeting", reply=GREETING_REPLY)
    quoted = said if len(said) <= 60 else said[:57] + "…"
    return Verdict(
        False,
        "other",
        reply=(
            f"I only find food, and I couldn't find anything about food in “{quoted}”. "
            "Name a dish, a flavour, a price or something you can't eat."
        ),
    )


EMPTY_REPLY = "There aren't any words in that. Tell me what you'd like to eat."
GREETING_REPLY = "Hello. Tell me what you're in the mood for: a dish, a flavour or a budget."
SCRIPT_REPLY = (
    "I can't read Urdu script yet, only English and Roman Urdu. Try “kuch teekha” or "
    "“something spicy under 1000”."
)
EXAMPLES = ("something spicy under 1000", "chicken karahi for two", "kuch meetha", "a light lunch")

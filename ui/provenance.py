"""
How this dish came to be known, as labelled evidence.

Every dish carries its own history: whether a person confirmed the row, whether the price was
found in the OCR evidence, whether its ingredients were named on the menu or assumed from what
a dish like this usually has, how its nutrition was estimated, where its flavour values came
from. All of it was recorded during the Phase 1 build (docs/PHASE1_DATA_DECISIONS.md) and none
of it was ever shown.

Showing it does two things. It lets a reader judge how far to trust the dish in front of them —
transparency and scrutability, in the terms the explanation literature uses — and it puts the
curation behind the dataset where it can be inspected, rather than described in a report.

Each fact is one facet: an id the card draws an icon from, a heading, a short badge, a tone, and
a sentence. The tone is what the badges are for — it separates what a person confirmed from what
was inferred from what was only estimated, at a glance, before any of the sentences are read.
Four tones, strongest evidence first:

    confirmed   a person looked at it, or it is printed on the menu
    inferred    derived by rule from something confirmed
    estimated   computed from reference values, so it carries error
    unchecked   nobody has checked it, or it isn't known at all

Each rule reads one field and says only what that field supports. Nothing here asserts that a
dish is safe, correct or measured: allergens are inferred, nutrition is estimated, and both the
sentences and the badges say so.
"""

from urllib.parse import urlparse

TONES = ("confirmed", "inferred", "estimated", "unchecked")
TONE_WORD = {
    "confirmed": "from the menu or a person",
    "inferred": "inferred by rule",
    "estimated": "estimated",
    "unchecked": "unchecked",
}

# field value -> (badge, tone, sentence)
REVIEW = {
    "human_confirmed": (
        "Person checked",
        "confirmed",
        "Read from a photograph of the menu by OCR, then confirmed by a person.",
    ),
    "auto_imported": (
        "Not checked",
        "unchecked",
        "Read from a photograph of the menu by OCR and imported automatically. "
        "No person has checked this row.",
    ),
    "scraped": ("From the site", "inferred", "Taken from the restaurant's own website."),
    "manual": ("Entered by hand", "confirmed", "Entered by hand."),
}
NAME = {
    "ok": (
        "Not flagged",
        "inferred",
        "Its name is the one the menu listed, and neither the OCR check nor the name check "
        "flagged it.",
    ),
    "fixed_by_owner": (
        "Corrected",
        "confirmed",
        "Its name was corrected by hand against the menu photograph.",
    ),
    "kept_by_owner": (
        "Checked",
        "confirmed",
        "Its name was checked by hand and kept as it stands.",
    ),
    "flagged_pending_review": (
        "Awaiting check",
        "unchecked",
        "Its name is as OCR read it, and is still waiting to be checked.",
    ),
}
PRICE = {
    "trusted": ("On the menu", "confirmed", "The price is the one on the menu."),
    "verified": (
        "Checked",
        "confirmed",
        "The price was checked against the menu it was read from.",
    ),
    "unverified": (
        "Unchecked",
        "unchecked",
        "The price could not be checked against the menu, so it counts for less.",
    ),
}
INGREDIENTS = {
    "named ingredients": (
        "From the menu",
        "confirmed",
        "Its ingredients are the ones its name and description state.",
    ),
    "named + typical ingredients": (
        "Named + typical",
        "inferred",
        "Its ingredients are the ones its name states, plus the ones a dish like this usually has.",
    ),
    "typical ingredients": (
        "Typical for its kind",
        "inferred",
        "Its ingredients are what a dish of this kind usually has — nothing on the menu "
        "listed them.",
    ),
    "none": ("None known", "unchecked", "No ingredients are known for it."),
}
TASTE = {
    "original": ("From the source", "confirmed", "Its flavour values came with the source data."),
    "name_rule": ("From its name", "inferred", "Its spice level was read from its name."),
    "keyword": ("From its name", "inferred", "Its flavour was estimated from words in its name."),
    "category_prior": (
        "Usual for its kind",
        "inferred",
        "Its flavour is the usual one for its kind of dish.",
    ),
    "restaurant_average": (
        "This kitchen's average",
        "estimated",
        "Its flavour is this restaurant's average, because nothing was recorded for the "
        "dish itself, so it counts for less.",
    ),
    "global_prior": (
        "Dataset average",
        "estimated",
        "Its flavour is the dataset's average, so it counts for little.",
    ),
    "neutral": ("Not recorded", "unchecked", "No flavour was recorded for it."),
}
WHERE = {
    "place": (
        "Mapped to the door",
        "confirmed",
        "Its restaurant is mapped to its own address, so any distance is to the door.",
    ),
    "area": (
        "Area centre",
        "estimated",
        "Its restaurant is mapped to the centre of its area, not to its door, so any distance "
        "is approximate.",
    ),
    "unknown": (
        "Not mapped",
        "unchecked",
        "Its restaurant could not be placed on the map, so distance counted for nothing in "
        "its score.",
    ),
}
SERVES = {
    "menu": ("On the menu", "confirmed", "The menu says how many it serves."),
    "owner": (
        "Owner said",
        "confirmed",
        "The restaurant's owner said how many it serves.",
    ),
    "default": (
        "Counted as one",
        "estimated",
        "Nothing said how many it serves, so it is counted as one serving — which is what its "
        "price per person and its calories are worked out from.",
    ),
    "double": (
        "Owner confirmed",
        "confirmed",
        "It is a Double, which the owner confirmed is two servings.",
    ),
    "price_estimate": (
        "From its price",
        "estimated",
        "How many it serves is estimated from its price against the menu.",
    ),
}


def _and(items: list[str]) -> str:
    """One name, two joined by "and", or a list with "and" before the last."""
    items = [str(i) for i in items if i]
    if len(items) < 2:
        return items[0] if items else ""
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or url
    except ValueError:
        return url


def lines(dish: dict) -> list[dict]:
    """
    What is known about this dish and how, in reading order.

    Each facet is {"id", "label", "badge", "tone", "text"}: `id` is what the card draws its icon
    from, `tone` is one of TONES. A facet whose field is missing is left out rather than guessed
    at, so a dish with no history at all gives an empty list, and no panel.
    """
    out: list[dict] = []

    def say(facet: str, label: str, found: tuple[str, str, str] | None) -> None:
        if found:
            badge, tone, text = found
            out.append({"id": facet, "label": label, "badge": badge, "tone": tone, "text": text})

    say("row", "The row", REVIEW.get(dish.get("review_status") or ""))
    say("name", "Its name", NAME.get(dish.get("name_status") or ""))

    price = PRICE.get(dish.get("price_status") or "")
    note = (dish.get("price_note") or "").strip()
    if price and note and dish.get("price_status") == "unverified":
        badge, tone, text = price  # the note is what explains the doubt
        price = (badge, tone, f"{text} ({note})")
    # Which kind of dish it was sorted as, and by what. The model ran during the build, on a
    # machine, months ago — not while this person waited — and the note is the rule that
    # corrected it afterwards, so both belong in the sentence.
    sorted_by = (dish.get("category_source") or "").strip()
    kind = (dish.get("category") or "").replace("_", " ")
    if sorted_by and kind:
        note = sorted_by[sorted_by.index("(") + 1 : -1] if "(" in sorted_by else ""
        if sorted_by.startswith("llm:"):
            badge, tone = "Sorted by model", "inferred"
            text = (
                f"It was sorted as {kind} by a language model while the dataset was being "
                "built, not while you were waiting."
            )
        else:
            badge, tone = "Sorted by rule", "inferred"
            text = f"It was sorted as {kind} by a rule while the dataset was being built."
        if note and not note.startswith("llm:"):
            text += f" A rule then corrected it: {note}."
        before = (dish.get("category_before") or "").replace("_", " ")
        if before and before != kind:
            text += f" The data it came from had it as {before}."
        say("kind", "Its kind", (badge, tone, text))

    say("price", "The price", price)

    basis = INGREDIENTS.get(dish.get("ingredients_basis") or "")
    named = [i for i in (dish.get("ingredients_named") or []) if i]
    typical = [i for i in (dish.get("ingredients_typical") or []) if i]
    if basis and named:
        badge, tone, text = basis
        assumed = [i for i in typical if i not in named]
        counted = f"{len(named)} named on the menu"
        if assumed:
            counted += f", {len(assumed)} more typical of the kind: {_and(assumed)}"
        basis = (badge, tone, f"{text.rstrip('.')} — {counted}.")
    say("ingredients", "Its ingredients", basis)

    if dish.get("allergens_known") is False:
        say(
            "allergens",
            "Allergens",
            (
                "Not known",
                "unchecked",
                "Its allergens are not known, so it is never offered to anyone who excludes one.",
            ),
        )
    elif dish.get("allergens"):
        say(
            "allergens",
            "Allergens",
            (
                "Inferred",
                "inferred",
                "Its allergens are inferred from those ingredients, not from a test of the dish.",
            ),
        )
    elif dish.get("allergens_known") is True:
        say(
            "allergens",
            "Allergens",
            (
                "None found",
                "inferred",
                "None of the eight allergen groups the build tags for — dairy, egg, fish, "
                "shellfish, gluten, nuts, soy and sesame — were found among its ingredients. "
                "That is a "
                "reading of the ingredients, not a test of the dish.",
            ),
        )

    confidence = (dish.get("nutrition_confidence") or "").lower()
    if confidence in ("high", "medium", "low"):
        text = (
            "Its calories and macros are estimated from those ingredients against USDA "
            f"reference values ({confidence} confidence)."
        )
        badge = f"Estimated, {confidence}"
        assumed = [i for i in (dish.get("nutrition_defaults") or []) if i]
        if assumed:
            text += (
                f" The estimate assumes {_and(assumed)}, which the menu never lists and most "
                "kitchens use."
            )
        if dish.get("nutrition_flag"):
            text += " The estimate failed a plausibility check, so health counts for less."
            badge = "Estimated, flagged"
        say("nutrition", "Its nutrition", (badge, "estimated", text))

    # Halal is a rule reading the ingredients, never a certificate, unless the owner said so.
    note = (dish.get("halal_note") or "").strip()
    if note and dish.get("is_halal") is not False:
        if note.startswith("owner confirmed"):
            say("halal", "Halal", ("Owner confirmed", "confirmed", f"The {note[len('owner ') :]}."))
        else:
            say(
                "halal",
                "Halal",
                (
                    "By rule",
                    "inferred",
                    "No pork or alcohol was found among its ingredients. That is a rule reading "
                    "the ingredients, not a certificate from the kitchen.",
                ),
            )

    say("taste", "Its flavour", TASTE.get(dish.get("taste_source") or ""))
    say("serves", "Servings", SERVES.get(dish.get("serves_source") or ""))
    say("where", "Where it is", WHERE.get(dish.get("location_precision") or ""))

    source, date = dish.get("source"), (dish.get("source_date") or "")[:10]
    if source:
        where = _host(source) if str(source).startswith("http") else str(source)
        say(
            "source",
            "Recorded",
            (date or "On record", "confirmed", f"From {where}{f', {date}' if date else ''}."),
        )
    return out


def tally(facets: list[dict]) -> list[dict]:
    """
    How much of this dish is confirmed, inferred, estimated or unchecked, strongest first.

    The panel leads with this so the shape of the evidence is readable before any sentence is:
    five facts a person confirmed and two estimates is a different dish from the reverse. The
    citation is left out of the count — where a row came from is not a claim about the dish.
    """
    facts = [f for f in facets if f["id"] != "source"]
    counts = ((tone, sum(1 for f in facts if f["tone"] == tone)) for tone in TONES)
    return [
        {"tone": tone, "count": count, "text": f"{count} {TONE_WORD[tone]}"}
        for tone, count in counts
        if count
    ]

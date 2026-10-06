"""
Taste in fifteen seconds: six dishes, tap the ones you'd eat.

Until a user approves something, the app has nothing to go on, so the taste term sits out
entirely and the card says "No flavour to go on yet". Scoring against a persona's invented
profile was worse than sitting out — it was noise presented as knowledge — so the term was
switched off instead. This turns the first fifteen seconds into real evidence, the same way
an approval is: a small, hedged move with a confidence attached to it, never a claim to know.

Two rules, both readable:

  the six       real dishes, with a photograph and flavour values that came with the source
                data rather than inferred by us, spread as far apart in flavour as the
                collection allows, one per restaurant. Asking someone to judge a dish whose
                flavour we guessed would be collecting evidence about our own guess.

  the fold      the taste is the average of what they tapped, and the confidence in each
                dimension is how far that average departs from the six dishes they were
                shown. A tap is a choice between what was on offer, so the offer is the
                baseline: picking the two spicy plates out of six says something about
                spice, while every dish on the screen happening to have no sourness says
                nothing at all about sour. Recorded flavours are sparse — mostly zeroes with
                a couple of strong values — so reading a shared zero as agreement would have
                the app announce a dislike nobody expressed. Where a dimension was not a
                choice, its confidence is near zero and the scorer shrinks it to neutral.

Nothing here is an approval: `updates` is untouched, so the learning rate stays where a first
approval expects it (accounts/learning.py), and a single dish approved later moves the taste
further than these taps did.
"""

import logging
import statistics
import time

from accounts.learning import IMPORTANCE_RANGE
from accounts.models import TASTE_DIMS, TasteModel
from tier_2.scoring import TASTE_WORDS

log = logging.getLogger(__name__)

SHOWN = 6  # dishes offered
LEAST = 2  # picks below this say too little to fold into a taste
START = 0.4  # confidence a whole-hearted lean earns, against 1.0 for a value set by hand
LEAN_FULL = 0.25  # how far from the offered average counts as having chosen a flavour outright
STRONG = 0.06  # a lean smaller than this is not worth saying out loud
FLOOR = 0.25  # what a dimension still counts for when the taps said nothing about it
TTL_SECONDS = 15 * 60

# Dishes worth asking about: ones the app could actually recommend, whose row a person
# confirmed, and whose flavour values came with the source data rather than being inferred by
# us (ui/provenance.py calls this "From the source"). 523 dishes across 19 kitchens qualify.
# No dish in the collection carries a photograph of its own, so the card shows the same
# representative image the Pick screen does, labelled as one.
OFFER_CYPHER = """
MATCH (d:Dish)
WHERE NOT coalesce(d.quarantined, false)
  AND NOT d.category IN ['beverages', 'add_ons']
  AND d.taste_source = 'original'
  AND d.review_status = 'human_confirmed'
RETURN coalesce(d.dish_uid, elementId(d)) AS dish_id, d.name AS name,
       d.restaurant_name AS restaurant_name, d.restaurant_area AS restaurant_area,
       d.category AS category,
       d.taste_sweet AS sweet, d.taste_salty AS salty, d.taste_sour AS sour,
       d.taste_bitter AS bitter, d.taste_umami AS umami, d.taste_spice AS spice
"""

_CACHE: dict = {"at": 0.0, "dishes": None}


def _taste_of(dish: dict) -> dict:
    return {d: float(dish.get(d) or 0.0) for d in TASTE_DIMS}


def _apart(a: dict, b: dict) -> float:
    """How far apart two flavours are, squared — the ordering is all this is used for."""
    return sum((a[d] - b[d]) ** 2 for d in TASTE_DIMS)


def spread_out(dishes: list[dict], how_many: int = SHOWN, looks=None) -> list[dict]:
    """
    The `how_many` dishes that are furthest apart in flavour: one per restaurant, and — where
    `looks` gives each dish the picture it will be shown under — no two under the same picture.

    Greedy: start from the dish furthest from the average plate, then keep adding whichever
    dish is furthest from everything picked so far. A dish that tastes like one already on
    screen tells us nothing new when it is tapped, six plates from one kitchen would ask about
    the kitchen rather than the taste, and two cards carrying the same photograph would ask
    the reader to choose between two pictures of the same thing. Ties break on dish_id, so the
    six are the same six for everyone until the data changes.
    """
    if not dishes:
        return []
    tastes = {d["dish_id"]: _taste_of(d) for d in dishes}
    look = {d["dish_id"]: (looks(d) if looks else d["dish_id"]) for d in dishes}
    middle = {dim: statistics.fmean([t[dim] for t in tastes.values()]) for dim in TASTE_DIMS}
    order = sorted(dishes, key=lambda d: (-_apart(tastes[d["dish_id"]], middle), d["dish_id"]))
    picked = [order[0]]
    kitchens, pictures = {order[0].get("restaurant_name")}, {look[order[0]["dish_id"]]}
    while len(picked) < how_many:
        rest = [
            d
            for d in order
            if d not in picked
            and d.get("restaurant_name") not in kitchens
            and look[d["dish_id"]] not in pictures
        ]
        if not rest:  # rather than show fewer than six, let a kitchen repeat before a picture
            rest = [d for d in order if d not in picked and look[d["dish_id"]] not in pictures]
        if not rest:
            break
        furthest = max(
            rest,
            key=lambda d: (
                min(_apart(tastes[d["dish_id"]], tastes[p["dish_id"]]) for p in picked),
                d["dish_id"],
            ),
        )
        picked.append(furthest)
        kitchens.add(furthest.get("restaurant_name"))
        pictures.add(look[furthest["dish_id"]])
    return picked


def offered(fresh: bool = False) -> list[dict]:
    """The six dishes to ask about, cached. Empty when the graph can't be reached."""
    if not fresh and _CACHE["dishes"] and time.time() - _CACHE["at"] < TTL_SECONDS:
        return _CACHE["dishes"]
    try:
        from accounts.store import get_driver
        from tier_1.symbolic_anchoring import representative_image

        records, _, _ = get_driver().execute_query(OFFER_CYPHER)
        dishes = spread_out(
            [dict(r) for r in records],
            looks=lambda d: representative_image(d["name"], d.get("category") or ""),
        )
    except Exception as exc:
        log.error("the taste starter could not be built: %s", exc)
        return []
    if dishes:
        _CACHE.update(at=time.time(), dishes=dishes)
    return dishes


def fold(picked: list[dict], offered: list[dict]) -> dict:
    """
    What the taps said: {"vector", "confidence", "lean"}.

    The vector is the average flavour of the dishes tapped — an absolute value, so it can be
    compared with a dish's own flavour the way a learned taste is. The lean is that average
    against the average of everything they were shown, which is the part that was actually a
    choice, and the confidence is how whole-hearted that choice was. A dimension nobody could
    have chosen on — because the six dishes all sat at the same value — earns no confidence,
    and the scorer then shrinks it back to neutral instead of acting on it.
    """
    tastes = [_taste_of(d) for d in picked]
    baseline = [_taste_of(d) for d in (offered or picked)]
    vector, confidence, lean = {}, {}, {}
    for dim in TASTE_DIMS:
        chosen = statistics.fmean([t[dim] for t in tastes])
        on_offer = statistics.fmean([t[dim] for t in baseline])
        vector[dim] = round(chosen, 4)
        lean[dim] = round(chosen - on_offer, 4)
        confidence[dim] = round(START * min(1.0, abs(lean[dim]) / LEAN_FULL), 4)
    return {"vector": vector, "confidence": confidence, "lean": lean}


def weighting(told: dict) -> dict[str, float]:
    """
    How much each dimension should count, from how much of a choice it was.

    The user's per-dimension confidence never reaches the scorer — only importance does, and
    it multiplies the dimension's weight in the flavour distance. So a dimension the six
    dishes could not distinguish on would otherwise be scored at full weight against a target
    that is really just the average of some zeroes, which is how a signal nobody gave becomes
    a penalty on every sour dish. Here it is turned down instead. Same shape as the rule
    approvals use (accounts/learning.py): scaled to an average of 1, clamped to
    IMPORTANCE_RANGE, so no dimension is ever switched off altogether.
    """
    raw = {d: FLOOR + told["confidence"][d] for d in TASTE_DIMS}
    mean = statistics.fmean(raw.values())
    low, high = IMPORTANCE_RANGE
    return {d: round(min(high, max(low, v / mean)), 4) for d, v in raw.items()}


def started(taste: TasteModel, told: dict) -> TasteModel:
    """
    The taste model these picks start from.

    It replaces the persona's prior rather than averaging with it: the prior is a guess about
    someone who has said nothing, and this person has now said something. Anything the user
    set by hand (confidence 1.0) is left exactly as it was — a tap never overrides a value
    somebody typed. `updates` stays where it was, because this is not an approval.
    """
    vector, confidence = told["vector"], told["confidence"]
    kept = {d: taste.confidence.get(d, 0.0) >= 1.0 for d in TASTE_DIMS}
    update = {
        "vector": {d: taste.vector[d] if kept[d] else vector[d] for d in TASTE_DIMS},
        "confidence": {
            d: taste.confidence[d] if kept[d] else max(taste.confidence.get(d, 0.0), confidence[d])
            for d in TASTE_DIMS
        },
    }
    # Importance is learned from approvals once there are any; until then, the taps set it.
    if not taste.updates:
        update["importance"] = weighting(told)
    return taste.model_copy(update=update)


def in_words(told: dict) -> str:
    """
    What the taps said, in a sentence — and honestly nothing when they said nothing.

    Only the flavours they leaned toward or away from are named, ranked by how far they
    leaned, so picks that look like the menu itself get "I'll learn as you go" rather than an
    invented summary.
    """
    lean = told["lean"]
    strong = sorted(((abs(lean[d]), d) for d in TASTE_DIMS if abs(lean[d]) >= STRONG), reverse=True)
    if not strong:
        return "Those look much like the six I showed you, so I'll learn as you go."
    toward = [TASTE_WORDS[d] for _, d in strong[:2] if lean[d] > 0]
    away = [TASTE_WORDS[d] for _, d in strong[:2] if lean[d] < 0]
    said = []
    if toward:
        said.append(f"you lean {' and '.join(toward)}")
    if away:
        said.append(f"you steer clear of {' and '.join(away)}")
    return f"Noted: {', and '.join(said)}. Approvals will keep refining it."

"""
Tier 2 scoring (Phase 3): the decision core.

Every term returns a Term: a utility in [0, 1], a confidence in [0, 1] saying how far
the data behind it can be trusted, and a sentence explaining it.

  taste    intensity-aware distance between the dish's six taste values and what the
           user wants, with the dimensions the query asked for counting more
  budget   a target band on the price, rather than "cheaper is always better"
  health   conditioned on a goal: muscle gain, weight loss, light, or balanced
  context  time of day and weather; small, and silent when no rule applies
  novelty  a penalty for dishes recommended or passed over in the last week

Aggregation shrinks each term toward a neutral 0.5 in proportion to how little its data
can be trusted, so missing data neither counts as a zero nor lets a dish win by
default. Hard constraints (allergens, diet, halal, the budget ceiling) are never scored
here: Tier 1 has already removed every dish that breaks one.

Every number that shapes a ranking is a named constant below. The reasoning behind each
is in docs/DECISION_CORE.md.
"""

import bisect
import re
from dataclasses import dataclass, field, replace

from tier_1.persona_manager import DEFAULT_PERSONA, get_persona

TASTE_DIMS = ("sweet", "salty", "sour", "bitter", "umami", "spice")
AGENTS = ("health", "budget", "taste")

# ── Parameters ───────────────────────────────────────────────────────────────
CRAVING_IMPORTANCE = 4.0  # a taste the query asks for counts four times as much
TASTE_SOURCE_CONFIDENCE = {
    "original": 1.0,
    "keyword": 0.8,
    "neutral": 0.8,
    "name_rule": 0.8,  # the spice level corrected from the dish's name (pipeline)
    "category_prior": 0.5,
    "restaurant_average": 0.4,
    "global_prior": 0.25,
}
PRICE_STATUS_CONFIDENCE = {"trusted": 1.0, "verified": 0.9, "unverified": 0.6}
NUTRITION_CONFIDENCE = {"high": 1.0, "medium": 0.7, "low": 0.4}
IMPLAUSIBLE_NUTRITION_FACTOR = 0.5
AUTO_IMPORTED_FACTOR = 0.85  # rows no person reviewed: name and price came from OCR

LIMIT_BAND = (0.4, 1.0)  # of the query's ceiling
USUAL_BAND = (0.7, 1.2)  # of the user's usual spend
CHEAP_FLOOR = 0.6  # utility of a very cheap dish: fine, just less like what was asked
NO_BUDGET_CONFIDENCE = 0.5  # with no budget, price counts only a little
CHEAPER_IS_BETTER = {"frugal_student"}  # personas that want the lowest price, not a band

PROTEIN_TARGET = {"muscle_gain": 8.0, "weight_loss": 6.0}  # g protein per 100 kcal
AMDR = {"protein": (0.10, 0.35), "carbs": (0.45, 0.65), "fat": (0.20, 0.35)}

CONTEXT_WEIGHT = 0.1  # the clock, the weather, the usual expectation of a meal
CONTEXT_WEIGHT_EXPLICIT = 0.3  # the query itself names the meal: "lunch", "dinner"...
NEUTRAL_UTILITY = 0.5  # what a term counts as where the data behind it is missing
SNACK_FIT = 0.6  # context fit of a snack or dessert when a meal was expected
NOVELTY_REJECTED = 0.7
NOVELTY_WITHIN_3_DAYS = 0.8
NOVELTY_WITHIN_7_DAYS = 0.9
PEER_PULL = 0.15  # similar users' approvals close up to 15% of the gap to a perfect score
PEER_SATURATION = 3  # ...fully once three of them approved the dish
DOUBLE_SERVINGS = 2  # a "Double" is two servings (the owner's rule)
SUMMARY_GOOD = 0.7  # a term at least this strong is a point in the dish's favour
SUMMARY_CAVEAT = 0.5  # ...and one below this is its caveat
SUMMARY_MIN_CONFIDENCE = 0.5  # the summary only repeats what the data can support
SUMMARY_ORDER = ("taste", "budget", "health")

PERSONA_GOALS = {"gym_bro": "muscle_gain", "health_nut": "light"}
MEALS = ("breakfast", "brunch", "lunch", "dinner")
SNACK_REQUESTS = ("dessert", "cake", "cafe", "bakery", "sweet", "snack", "coffee", "tea")
TASTE_WORDS = {
    "sweet": "sweet",
    "salty": "salty",
    "sour": "sour",
    "bitter": "bitter",
    "umami": "savoury",
    "spice": "spicy",
}
TASTE_ADVERB = {"strongly": "properly", "fairly": "fairly", "mildly": "only mildly"}


@dataclass(frozen=True)
class Term:
    utility: float
    confidence: float
    sentence: str
    applies: bool = True  # False when the user has no preference this term could judge
    phrase: str = ""  # the point as a verb phrase for the summary: "is properly spicy"


@dataclass
class Preferences:
    """Everything scoring knows about the person asking."""

    taste: dict[str, float]  # the usual taste: learned, or the persona's
    weights: dict[str, float]  # w_health, w_budget, w_taste, summing to 1
    craved: dict[str, float] = field(default_factory=dict)  # tastes this query asked for
    goal: str = "balanced"
    budget_ceiling: float | None = None
    typical_spend: float | None = None
    party_size: int = 1
    history: list[dict] = field(default_factory=list)  # {"dish_uid", "kind", "days_ago"}
    hour: int | None = None
    temperature_c: float | None = None
    persona: str = DEFAULT_PERSONA
    price_pool: list[float] = field(default_factory=list)  # every candidate's cost, sorted
    meal: str | None = None  # "breakfast", "brunch", "lunch" or "dinner", if the query says
    expects_meal: bool = True  # False when the query asked for something sweet or a snack
    importance: dict[str, float] = field(default_factory=lambda: {d: 1.0 for d in TASTE_DIMS})
    learned_from: int = 0  # approvals the taste and importance were learned from
    peers: dict[str, int] = field(default_factory=dict)  # dish_uid -> similar users approving


# ── Helpers ──────────────────────────────────────────────────────────────────
def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _range_score(value: float, low: float, high: float, width: float) -> float:
    """1 inside [low, high], falling linearly to 0 at `width` outside it."""
    if low <= value <= high:
        return 1.0
    gap = low - value if value < low else value - high
    return _clamp(1.0 - gap / width)


def _rs(amount: float) -> str:
    return f"Rs {amount:,.0f}"


def _level(value: float) -> str:
    if value >= 0.7:
        return "strongly"
    if value >= 0.45:
        return "fairly"
    if value >= 0.2:
        return "mildly"
    return "barely"


def _review_factor(dish: dict) -> float:
    return AUTO_IMPORTED_FACTOR if dish.get("review_status") == "auto_imported" else 1.0


def normalise_weights(weights: dict) -> dict[str, float]:
    raw = {
        "w_health": weights.get("w_health", weights.get("w_h", 0.0)) or 0.0,
        "w_budget": weights.get("w_budget", weights.get("w_b", 0.0)) or 0.0,
        "w_taste": weights.get("w_taste", weights.get("w_t", 0.0)) or 0.0,
    }
    total = sum(raw.values())
    if total <= 0:
        return {k: 1 / 3 for k in raw}
    return {k: v / total for k, v in raw.items()}


# ── Terms ────────────────────────────────────────────────────────────────────
def taste_term(dish: dict, prefs: Preferences) -> Term:
    profile = dish.get("taste_profile") or {}
    x = {d: float(profile.get(d) or 0.0) for d in TASTE_DIMS}
    target = {d: prefs.craved.get(d, prefs.taste.get(d, 0.0)) for d in TASTE_DIMS}
    weight = {
        d: prefs.importance.get(d, 1.0) * (CRAVING_IMPORTANCE if d in prefs.craved else 1.0)
        for d in TASTE_DIMS
    }
    distance = sum(weight[d] * abs(x[d] - target[d]) for d in TASTE_DIMS) / sum(weight.values())
    utility = _clamp(1.0 - distance)

    if prefs.craved:
        asked = sorted(prefs.craved, key=prefs.craved.get, reverse=True)[:2]
        wanted = " and ".join(TASTE_WORDS[d] for d in asked)
        found = " and ".join(f"{_level(x[d])} {TASTE_WORDS[d]}" for d in asked)
        sentence = f"You asked for {wanted}, and this is {found}."
        plain = " and ".join(
            f"{TASTE_ADVERB.get(_level(x[d]), 'barely')} {TASTE_WORDS[d]}" for d in asked
        )
        matched = all(_level(x[d]) in ("strongly", "fairly") for d in asked)
        phrase = f"is {plain}, as you asked" if matched else f"is {plain}, though you asked for it"
    else:
        fit = "close to" if utility >= 0.8 else "partly like" if utility >= 0.6 else "not much like"
        usual = (
            f"your taste, learned from {prefs.learned_from} approvals"
            if prefs.learned_from
            else "your usual taste"
        )
        sentence = f"Its flavour is {fit} {usual}."
        phrase = f"is {fit} your usual taste"
    confidence = TASTE_SOURCE_CONFIDENCE.get(dish.get("taste_source") or "", 0.5)
    confidence *= _review_factor(dish)
    if confidence < 0.6:
        sentence += " Its flavour is estimated from similar dishes."
    return Term(utility, confidence, sentence, phrase=phrase)


def _serves(dish: dict) -> float:
    low, high = dish.get("serves_min"), dish.get("serves_max")
    if low and high:
        return (low + high) / 2
    return float(low or high or 1)


def _cost(dish: dict, party_size: int) -> tuple[float, float, float]:
    """(menu price, cost per person, how many people share it)."""
    price = float(dish.get("price_pkr") or 0.0)
    sharing = min(float(party_size), max(1.0, _serves(dish)))
    return price, price / sharing, sharing


def budget_term(dish: dict, prefs: Preferences) -> Term:
    price, cost, sharing = _cost(dish, prefs.party_size)
    each = f" ({_rs(cost)} each for {prefs.party_size})" if sharing > 1 else ""
    status = dish.get("price_status") or "unverified"
    confidence = PRICE_STATUS_CONFIDENCE.get(status, 0.6)
    ceiling, usual = prefs.budget_ceiling, prefs.typical_spend
    frugal = prefs.persona in CHEAPER_IS_BETTER

    pool = prefs.price_pool or [cost]
    if frugal:
        # Price relative to the other options: the cheapest scores 1, the dearest 0.
        dearer = len(pool) - bisect.bisect_right(pool, cost)
        utility = dearer / (len(pool) - 1) if len(pool) > 1 else 1.0
        if len(pool) > 1 and dearer == len(pool) - 1:
            verdict = "the cheapest of the options"
        elif len(pool) > 1 and dearer == 0:
            verdict = "the dearest of the options"
        else:
            verdict = f"cheaper than {utility:.0%} of the options"
        sentence = f"{_rs(price)}{each}, {verdict}."
        phrase = f"is {verdict}"
    elif not (ceiling or usual):
        # No budget: anything up to a typical option's price is fine, so cheap sides
        # gain nothing; only dearer dishes lose, reaching 0 at the dearest 5%.
        typical = pool[len(pool) // 2]
        dear = pool[int(0.95 * (len(pool) - 1))]
        if cost <= typical:
            utility, verdict = 1.0, f"no more than a typical option here ({_rs(typical)})"
            phrase = "is no pricier than a typical option here"
        else:
            utility = _clamp(1.0 - (cost - typical) / max(dear - typical, typical))
            verdict = f"pricier than a typical option here ({_rs(typical)})"
            phrase = "is pricier than a typical option here"
        confidence *= NO_BUDGET_CONFIDENCE
        sentence = f"{_rs(price)}{each}, {verdict}. No budget was given, so price counts little."
    else:
        if usual and (not ceiling or usual <= ceiling):
            low, high = USUAL_BAND[0] * usual, USUAL_BAND[1] * usual
            if ceiling:
                high = min(high, ceiling)
            band = f"the Rs {low:,.0f}–{high:,.0f} you usually spend"
            short = "what you usually spend"
        else:
            low, high = LIMIT_BAND[0] * ceiling, ceiling
            band = f"your {_rs(ceiling)} limit"
            short = "your limit"
        if cost > high:
            utility, verdict = _clamp(1.0 - (cost - high) / high), f"above {band}"
            phrase = f"costs {_rs(cost - high)} more than {short}"
        elif cost < low:
            utility = CHEAP_FLOOR + (1.0 - CHEAP_FLOOR) * cost / low
            verdict = f"well under {band}"
            phrase = f"is well under {short}"
        else:
            utility, verdict = 1.0, f"within {band}"
            spare = high - cost
            phrase = f"comes in {_rs(spare)} under {short}" if spare >= 50 else f"fits {short}"
        sentence = f"{_rs(price)}{each}, {verdict}."
    if status == "unverified":
        sentence += " The price couldn't be checked against the menu."
    return Term(utility, confidence, sentence, phrase=phrase)


def portions(dish: dict, party_size: int) -> float:
    """
    Servings one person eats. One person ordering a Double eats both servings (the
    owner's rule), so a Double ordered for fewer people than it serves counts in full.
    Other dishes that serve several are shared, and each person eats one serving.
    """
    if dish.get("serves_source") != "double":
        return 1.0
    return max(1.0, DOUBLE_SERVINGS / max(1, party_size))


def health_term(dish: dict, goal: str, servings: float = 1.0) -> Term:
    macros = dish.get("macros") or {}
    kcal, protein = macros.get("calories"), macros.get("protein_g")
    if not kcal or kcal <= 0 or protein is None:
        return Term(0.0, 0.0, "No nutrition estimate for this dish, so health didn't count.")
    carbs, fat = macros.get("carbs_g") or 0.0, macros.get("fat_g") or 0.0
    kcal, protein, carbs, fat = (v * servings for v in (kcal, protein, carbs, fat))
    density = 100 * protein / kcal
    shares = {"protein": 4 * protein / kcal, "carbs": 4 * carbs / kcal, "fat": 9 * fat / kcal}
    around = f"around {kcal:,.0f} kcal"

    if goal == "muscle_gain":
        protein_fit = _clamp(density / PROTEIN_TARGET["muscle_gain"])
        utility = 0.75 * protein_fit + 0.25 * _range_score(kcal, 400, 900, 400)
        if protein_fit >= 0.8:
            verdict, phrase = "Strong for muscle gain.", f"is high in protein, {protein:.0f} g"
        elif protein_fit >= 0.5:
            verdict, phrase = "Some protein, but not a lot.", f"has some protein, {protein:.0f} g"
        else:
            verdict, phrase = "Low in protein for muscle gain.", "is low in protein for you"
        sentence = (
            f"About {protein:.0f} g of protein in {kcal:,.0f} kcal "
            f"({density:.1f} g per 100 kcal). {verdict}"
        )
    elif goal == "weight_loss":
        calorie_fit = 1.0 if kcal <= 450 else _clamp(1.0 - (kcal - 450) / 450)
        utility = 0.7 * calorie_fit + 0.3 * _clamp(density / PROTEIN_TARGET["weight_loss"])
        verdict = (
            "light and filling"
            if utility >= 0.75
            else "fine in moderation"
            if utility >= 0.5
            else "heavy for weight loss"
        )
        sentence = (
            f"About {kcal:,.0f} kcal with {protein:.0f} g of protein. {verdict.capitalize()}."
        )
        phrase = f"is {verdict}, at {around}"
    elif goal == "light":
        calorie_fit = 1.0 if kcal <= 400 else _clamp(1.0 - (kcal - 400) / 400)
        fat_fit = _range_score(shares["fat"], 0.0, 0.30, 0.30)
        utility = 0.6 * calorie_fit + 0.4 * fat_fit
        verdict = (
            "a light choice"
            if utility >= 0.75
            else "moderately light"
            if utility >= 0.5
            else "on the heavy side"
        )
        fat_share = f"{shares['fat']:.0%} of it from fat"
        sentence = f"About {kcal:,.0f} kcal, {fat_share}. {verdict.capitalize()}."
        phrase = f"is {verdict}, at {around}"
    else:  # balanced
        fits = {m: _range_score(shares[m], lo, hi, 0.20) for m, (lo, hi) in AMDR.items()}
        utility = 0.8 * sum(fits.values()) / 3 + 0.2 * _range_score(kcal, 300, 900, 400)
        misses = [m for m in fits if fits[m] < 0.8]
        # A macro over its range explains an unbalanced split better than one under it:
        # a karahi is heavy on fat, not light on carbs.
        over = [m for m in misses if shares[m] > AMDR[m][1]]
        if not misses:
            verdict, phrase = "A balanced split.", f"is a balanced meal, at {around}"
        elif over:
            worst = min(over, key=fits.get)
            verdict = f"Heavy on {worst}."
            if worst == "fat" and shares["fat"] > 0.5:
                phrase = f"is rich, at {around} and mostly fat"
            else:
                phrase = f"is heavy on {worst}, at {around}"
        else:
            worst = min(misses, key=fits.get)
            verdict, phrase = f"Light on {worst}.", f"is light on {worst}"
        big, mid, small = sorted(shares, key=shares.get, reverse=True)
        split = (
            f"{shares[big]:.0%} of it from {big}, {shares[mid]:.0%} from {mid} "
            f"and {shares[small]:.0%} from {small}"
        )
        sentence = f"About {kcal:,.0f} kcal, with {split}. {verdict}"

    if servings > 1:
        sentence += " That counts both servings, because a Double for one is eaten by one."
    confidence = NUTRITION_CONFIDENCE.get(dish.get("nutrition_confidence") or "", 0.0)
    if dish.get("nutrition_flag"):
        confidence *= IMPLAUSIBLE_NUTRITION_FACTOR
    return Term(_clamp(utility), confidence * _review_factor(dish), sentence, phrase=phrase)


def context_term(dish: dict, prefs: Preferences) -> Term:
    fits, reasons = [], []
    category = dish.get("category")
    ingredients = set(dish.get("ingredients") or [])
    name = (dish.get("name") or "").lower()
    kcal = (dish.get("macros") or {}).get("calories")
    asked_breakfast = prefs.meal in ("breakfast", "brunch")
    breakfast_hours = prefs.meal is None and prefs.hour is not None and 6 <= prefs.hour < 11
    if asked_breakfast or breakfast_hours:
        breakfast = category == "cafe_bakery" or bool(ingredients & {"egg", "paratha", "bread"})
        fits.append(1.0 if breakfast else 0.5)
        reasons.append(f"you asked for {prefs.meal}" if asked_breakfast else "it's breakfast time")
    elif prefs.expects_meal:
        # A food concierge is usually asked for a meal. Unless the query wants something
        # sweet or a snack, a snack or dessert fits less well; say so only when it doesn't.
        snack = category == "cafe_bakery"
        fits.append(SNACK_FIT if snack else 1.0)
        if prefs.meal:
            reasons.append(f"you asked for {prefs.meal}")
        elif snack:
            reasons.append("you didn't ask for a snack or dessert")
    if prefs.hour is not None and (prefs.hour >= 23 or prefs.hour < 4):
        fits.append(1.0 if category in {"fast_food", "pizza", "sandwich"} else 0.6)
        reasons.append("it's late at night")
    t = prefs.temperature_c
    if t is not None and t >= 32:
        fits.append(1.0 if (kcal and kcal <= 550) or "salad" in name else 0.6)
        reasons.append(f"it's hot out ({t:.0f}°C)")
    elif t is not None and t <= 12:
        fits.append(1.0 if "soup" in name or category in {"desi_traditional", "afghan"} else 0.6)
        reasons.append(f"it's cold out ({t:.0f}°C)")
    if not fits:
        return Term(0.0, 0.0, "", False)
    utility = sum(fits) / len(fits)
    if not reasons:
        return Term(utility, 1.0, "")
    suits = "suits" if utility >= 0.8 else "doesn't especially suit"
    reason = "; ".join(reasons)
    return Term(utility, 1.0, f"{reason[0].upper()}{reason[1:]}, and this {suits} it.")


def novelty(dish: dict, prefs: Preferences) -> tuple[float, str]:
    uid = dish.get("dish_id")
    recent = [e for e in prefs.history if e.get("dish_uid") == uid and e.get("days_ago", 99) <= 7]
    if not uid or not recent:
        return 1.0, ""
    if any(e.get("kind") == "rejected" for e in recent):
        return NOVELTY_REJECTED, "You passed on this recently, so it's ranked lower."
    days = min(e["days_ago"] for e in recent)
    when = "today" if days < 1 else "yesterday" if days < 2 else f"{int(days)} days ago"
    factor = NOVELTY_WITHIN_3_DAYS if days <= 3 else NOVELTY_WITHIN_7_DAYS
    return factor, f"Recommended to you {when}, so it's ranked a little lower for variety."


# ── Aggregation ──────────────────────────────────────────────────────────────
def _utility(term: Term) -> float | None:
    return round(term.utility, 6) if term.applies and term.confidence > 0 else None


def _it(fragment: str, also: bool = False) -> str:
    """ "is rich" -> "It's rich.", "comes in Rs 100 under" -> "It comes in Rs 100 under." """
    extra = "also " if also else ""
    if fragment.startswith("is "):
        return f"It's {extra}{fragment[3:]}."
    return f"It {extra}{fragment}."


def summary(terms: dict[str, Term], weights: dict[str, float]) -> str:
    """
    The reasons in one short paragraph for the recommendation screen: up to two points in
    the dish's favour, the two that count most, then its most serious caveat. A term is
    mentioned only when its data can be trusted. The full sentences stay in `reasons`.
    """
    said = {
        k: t
        for k, t in terms.items()
        if k in SUMMARY_ORDER and t.applies and t.phrase and t.confidence >= SUMMARY_MIN_CONFIDENCE
    }
    good = [k for k, t in said.items() if t.utility >= SUMMARY_GOOD]
    good = sorted(good, key=lambda k: weights.get(k, 0.0) * said[k].utility, reverse=True)[:2]
    good = [k for k in SUMMARY_ORDER if k in good]
    weak = [k for k, t in said.items() if t.utility < SUMMARY_CAVEAT]
    caveat = min(weak, key=lambda k: said[k].utility) if weak else None

    parts = []
    if good:
        parts.append(_it(", and ".join(said[k].phrase for k in good)))
    if caveat and good:
        parts.append(_it(said[caveat].phrase, also=True))
    elif caveat:
        plain = _it(said[caveat].phrase)
        parts.append(f"It's the closest fit here, but {plain[0].lower()}{plain[1:]}")
    return " ".join(parts)


def score_dish(dish: dict, prefs: Preferences) -> dict:
    terms = {
        "health": health_term(dish, prefs.goal, portions(dish, prefs.party_size)),
        "budget": budget_term(dish, prefs),
        "taste": taste_term(dish, prefs),
        "context": context_term(dish, prefs),
    }
    weights = {
        "health": prefs.weights["w_health"],
        "budget": prefs.weights["w_budget"],
        "taste": prefs.weights["w_taste"],
        "context": CONTEXT_WEIGHT_EXPLICIT if prefs.meal else CONTEXT_WEIGHT,
    }
    # Each term counts in proportion to its confidence; the rest of its weight counts
    # as a neutral 0.5. Missing data is neither a zero nor a free pass.
    live = {k: t for k, t in terms.items() if t.applies}
    num = sum(
        weights[k] * (t.confidence * t.utility + (1 - t.confidence) * NEUTRAL_UTILITY)
        for k, t in live.items()
    )
    den = sum(weights[k] for k in live)
    core = [k for k in AGENTS if k in live and weights[k] > 0]
    core_weight = sum(weights[k] for k in core)
    coverage = (
        sum(weights[k] * live[k].confidence for k in core) / core_weight if core_weight else 1.0
    )
    factor, novelty_reason = novelty(dish, prefs)
    total = (num / den if den else NEUTRAL_UTILITY) * factor
    peers = prefs.peers.get(dish.get("dish_id"), 0)
    if peers:  # a pull toward 1, so it can only raise a score and never past 1
        total += (1 - total) * PEER_PULL * min(1.0, peers / PEER_SATURATION)

    reasons = {k: t.sentence for k, t in terms.items() if t.sentence}
    unassessed = [k for k in core if live[k].confidence == 0]
    if unassessed:
        reasons["coverage"] = (
            f"Its {' and '.join(unassessed)} couldn't be assessed, so it counts as average there."
        )
    if novelty_reason:
        reasons["novelty"] = novelty_reason
    if peers:
        who = "person" if peers == 1 else "people"
        reasons["peers"] = f"{peers} {who} with tastes like yours approved this recently."

    macros = dish.get("macros") or {}
    return {
        "dish_id": dish.get("dish_id", "unknown"),
        "name": dish.get("name", "unnamed"),
        "restaurant_name": dish.get("restaurant_name"),
        "restaurant_area": dish.get("restaurant_area"),
        "location_precision": dish.get("location_precision"),
        "restaurant_lat": dish.get("restaurant_lat"),
        "restaurant_lng": dish.get("restaurant_lng"),
        "distance_km": dish.get("distance_km"),
        "price_pkr": float(dish.get("price_pkr") or 0.0),
        "price_status": dish.get("price_status"),
        "serves_min": dish.get("serves_min"),
        "serves_max": dish.get("serves_max"),
        "serves_source": dish.get("serves_source"),
        "category": dish.get("category", ""),
        "image_url": dish.get("image_url", ""),
        "is_rep_image": dish.get("is_rep_image", False),
        "human_tags": dish.get("human_tags", []),
        "taste_profile": dish.get("taste_profile", {}),
        "ingredients": dish.get("ingredients", []),
        "allergens": dish.get("allergens"),  # None: not known
        "macros": macros,
        "u_health": _utility(terms["health"]),
        "u_budget": _utility(terms["budget"]),
        "u_taste": _utility(terms["taste"]),
        "u_context": _utility(terms["context"]),
        "u_total": round(total, 6),
        "confidence": {k: round(t.confidence, 3) for k, t in live.items()},
        "coverage": round(coverage, 3),
        "novelty": factor,
        "peers": peers,
        "reasons": reasons,
        "summary": summary(terms, weights),
    }


def rank(candidates: list[dict], prefs: Preferences) -> list[dict]:
    """Scores every candidate; best first, ties broken by name so runs are repeatable."""
    prefs = replace(prefs, price_pool=sorted(_cost(c, prefs.party_size)[1] for c in candidates))
    scored = [score_dish(c, prefs) for c in candidates]
    return sorted(scored, key=lambda s: (-s["u_total"], s["name"]))


def traces(ranked: list[dict], prefs: Preferences, top: int = 5) -> list[str]:
    """
    Readable reasoning for the top dishes. The frontend reads each dish's three lines
    after "Candidate Breakdown" (Health, Budget, Taste) up to " (raw:", so keep that shape.
    """
    w = prefs.weights
    lines = [
        f"weights: w_h={w['w_health']:.2f} w_b={w['w_budget']:.2f} w_t={w['w_taste']:.2f} "
        f"(persona={prefs.persona}, goal={prefs.goal})"
    ]
    for s in ranked[:top]:
        lines.append(f"  {s['name']} Candidate Breakdown:")
        for agent in AGENTS:
            u = s[f"u_{agent}"]
            raw = f"{u:.4f}" if u is not None else "n/a"
            confidence = s["confidence"].get(agent, 0.0)
            reason = s["reasons"].get(agent, "")
            lines.append(
                f"    - {agent.capitalize()} Agent: {reason} "
                f"(raw: {raw}, confidence: {confidence:.2f})"
            )
        for extra in ("context", "coverage", "novelty", "peers"):
            if s["reasons"].get(extra):
                lines.append(f"    - {extra.capitalize()}: {s['reasons'][extra]}")
        lines.append(f"    => Final U_total: {s['u_total']:.4f}")
    if ranked:
        lines.append(f"winner: {ranked[0]['name']} (U_total={ranked[0]['u_total']:.4f})")
    return lines


def build_preferences(
    intent: dict,
    context: dict | None = None,
    weights: dict | None = None,
    persona: str | None = None,
) -> Preferences:
    """
    Preferences from the parsed query, the session's scoring context (persona, goal,
    learned taste, history, time and weather) and, from the sliders, explicit weights.
    """
    context = context or {}
    persona_chosen = persona is not None  # a persona picked for this ranking overrides learning
    persona = persona or context.get("persona") or DEFAULT_PERSONA
    persona_data = get_persona(persona)
    mood = intent.get("mood_vector") or {}
    craved = {d: float(mood[d]) for d in TASTE_DIMS if float(mood.get(d) or 0) > 0}
    ceiling = intent.get("budget_max_pkr")
    raw = str(intent.get("raw_input") or "").lower()
    meal = next((m for m in MEALS if re.search(rf"\b{m}\b", raw)), None)
    asked = str(intent.get("preferred_category") or "").lower()
    wants_snack = "sweet" in craved or any(w in asked for w in SNACK_REQUESTS)
    return Preferences(
        meal=meal,
        expects_meal=not wants_snack,
        taste=context.get("taste") or dict(persona_data["taste_preference"]),
        # sliders, then a persona picked now, then learned weights, then the persona's
        weights=normalise_weights(
            weights
            or (None if persona_chosen else context.get("weights"))
            or persona_data["weights"]
        ),
        importance=context.get("importance") or {d: 1.0 for d in TASTE_DIMS},
        learned_from=int(context.get("learned_from") or 0),
        peers=context.get("peers") or {},
        craved=craved,
        goal=context.get("goal") or PERSONA_GOALS.get(persona, "balanced"),
        budget_ceiling=float(ceiling) if ceiling and ceiling < 999_999 else None,
        typical_spend=context.get("typical_spend"),
        party_size=int(context.get("party_size") or 1),
        history=context.get("history") or [],
        hour=context.get("hour"),
        temperature_c=context.get("temperature_c"),
        persona=persona,
    )

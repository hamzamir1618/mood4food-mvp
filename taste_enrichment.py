"""
Taste Enrichment Module — Category-Based Fallback Priors

Fills in all-zero taste vectors in the dish dataset using a 4-phase cascade:
  Phase 1: Keyword dictionary scan (dish name → taste dimensions)
  Phase 2: Category-based fallback priors (beverages, desserts, BBQ)
  Phase 3: Restaurant-cuisine-average fallback (per-restaurant means)
  Phase 4: Provenance tracking (taste_source field)

IMPORTANT: Never overwrites non-zero original CSV values.
See docs/ENRICHMENT_METHODOLOGY.md for full rationale.
"""

import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

TASTE_DIMS = (
    "taste_sweet",
    "taste_salty",
    "taste_sour",
    "taste_bitter",
    "taste_umami",
    "taste_spice",
)

# ── Phase 1: Keyword Dictionary ─────────────────────────────────────────────
# Each entry maps a keyword to a dict of taste dimension contributions.
# Multiple keyword hits combine; each dimension is capped at 1.0.

KEYWORD_MAP = {
    # Fruit names → sweet + sour
    "mango": {"taste_sweet": 0.7, "taste_sour": 0.2},
    "peach": {"taste_sweet": 0.6, "taste_sour": 0.2},
    "strawberry": {"taste_sweet": 0.6},
    "raspberry": {"taste_sweet": 0.5, "taste_sour": 0.3},
    "blueberry": {"taste_sweet": 0.4},
    "pomegranate": {"taste_sweet": 0.3, "taste_sour": 0.4},
    "apple": {"taste_sweet": 0.5, "taste_sour": 0.2},
    "orange": {"taste_sweet": 0.5, "taste_sour": 0.3},
    "lemon": {"taste_sweet": 0.2, "taste_sour": 0.6},
    "lime": {"taste_sour": 0.6},
    "grapefruit": {"taste_sour": 0.5, "taste_bitter": 0.3},
    "passion fruit": {"taste_sweet": 0.5, "taste_sour": 0.3},
    "pineapple": {"taste_sweet": 0.6, "taste_sour": 0.3},
    "banana": {"taste_sweet": 0.6},
    "cherry": {"taste_sweet": 0.5, "taste_sour": 0.2},
    # Sweet modifiers
    "honey": {"taste_sweet": 0.7},
    "caramel": {"taste_sweet": 0.7},
    "chocolate": {"taste_sweet": 0.6, "taste_bitter": 0.2},
    "oreo": {"taste_sweet": 0.6},
    "nutella": {"taste_sweet": 0.7},
    # Rich / creamy
    "butter": {"taste_umami": 0.4, "taste_salty": 0.2},
    "cream": {"taste_sweet": 0.2, "taste_umami": 0.3},
    "creamy": {"taste_sweet": 0.2, "taste_umami": 0.3},
    "cheese": {"taste_umami": 0.4, "taste_salty": 0.3},
    "malai": {"taste_sweet": 0.2, "taste_umami": 0.3},
    # Spice / heat
    "chilli": {"taste_spice": 0.5},
    "chili": {"taste_spice": 0.5},
    "achari": {"taste_sour": 0.4, "taste_spice": 0.4},
    "masala": {"taste_spice": 0.5, "taste_umami": 0.3},
    "pepper": {"taste_spice": 0.3},
    "schezuan": {"taste_spice": 0.6, "taste_sour": 0.2},
    "szechuan": {"taste_spice": 0.6, "taste_sour": 0.2},
    "peri peri": {"taste_spice": 0.5},
    "mirchi": {"taste_spice": 0.6},
    "mirchilli": {"taste_spice": 0.6},
    "hot": {"taste_spice": 0.4},
    "spicy": {"taste_spice": 0.5},
    "namkeen": {"taste_salty": 0.5, "taste_spice": 0.2},
    # Savory / umami
    "qeema": {"taste_umami": 0.5, "taste_spice": 0.3},
    "keema": {"taste_umami": 0.5, "taste_spice": 0.3},
    "gravy": {"taste_umami": 0.4, "taste_salty": 0.3},
    "broth": {"taste_umami": 0.4, "taste_salty": 0.2},
    "soup": {"taste_umami": 0.3, "taste_salty": 0.2},
    # Sour
    "sour": {"taste_sour": 0.6},
    "tangy": {"taste_sour": 0.5},
    "tamarind": {"taste_sour": 0.5, "taste_sweet": 0.2},
    # Bitter
    "coffee": {"taste_bitter": 0.5, "taste_sweet": 0.1},
    "green tea": {"taste_bitter": 0.3},
}

# Sort keywords longest-first to match multi-word phrases before their components
_SORTED_KEYWORDS = sorted(KEYWORD_MAP.keys(), key=len, reverse=True)


# ── Phase 2: Category Detection Patterns ────────────────────────────────────

BEVERAGE_PATTERNS = [
    "juice",
    "tea",
    "shake",
    "smoothie",
    "lemonade",
    "cola",
    "fanta",
    "sprite",
    "pepsi",
    "soda",
    "soft drink",
    "mojito",
    "margarita",
    "mocktail",
    "cocktail",
    "lassi",
    "frappe",
    "latte",
    "cappuccino",
    "mocha",
    "milkshake",
    "milk shake",
    "sharbat",
    "cooler",
    "squash",
    "dew",
    "7up",
    "mineral water",
    "iced tea",
    "ice tea",
]

BEVERAGE_EXCEPTIONS = [
    "plain water",
    "black coffee",
    "diet",
    "sugar free",
    "sugar-free",
    "unsweetened",
    "zero",
]

# "water" requires exact-match (not substring) to avoid matching "mineral water"
BEVERAGE_EXCEPTION_EXACT = ["water"]

CITRUS_TEA_PATTERNS = ["tea", "lemon", "lime", "grapefruit"]

DESSERT_PATTERNS = [
    "cake",
    "brownie",
    "cookie",
    "ice cream",
    "ice-cream",
    "kheer",
    "halwa",
    "gulab",
    "kunafa",
    "cheesecake",
    "pudding",
    "mousse",
    "tiramisu",
    "sundae",
    "waffle",
    "pancake",
    "donut",
    "muffin",
    "tart",
    "flan",
    "pastry",
    "pie",
    "barfi",
    "mithai",
    "jalebi",
    "ras malai",
    "rasmalai",
]

BBQ_GRILL_PATTERNS = [
    "karahi",
    "tikka",
    "kebab",
    "kabab",
    "seekh",
    "chapli",
    "sajji",
    "tandoor",
    "tandoori",
    "bbq",
    "barbeque",
    "barbecue",
    "grill",
    "grilled",
    "roast",
    "roasted",
    "boti",
]

# ── Phase 3: Global Category Priors (last resort) ──────────────────────────

GLOBAL_CATEGORY_PRIORS = {
    "chinese_asian": {"taste_umami": 0.35, "taste_salty": 0.25},
    "desi_traditional": {"taste_umami": 0.25, "taste_spice": 0.3, "taste_salty": 0.2},
    "middle_eastern": {"taste_umami": 0.25, "taste_salty": 0.25, "taste_sour": 0.15},
    "fast_food": {"taste_salty": 0.35, "taste_umami": 0.25},
    "cafe_bakery": {"taste_sweet": 0.35, "taste_bitter": 0.15},
    "continental_upscale": {"taste_umami": 0.25, "taste_salty": 0.2},
    "pizza": {"taste_salty": 0.35, "taste_umami": 0.35},
    "sandwich": {"taste_salty": 0.25, "taste_umami": 0.2},
    "other": {"taste_umami": 0.2, "taste_salty": 0.2},
}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_taste_values(row: dict) -> dict[str, float]:
    """Extract taste values from a row dict, defaulting missing/None to 0.0."""
    return {d: float(row.get(d, 0) or 0) for d in TASTE_DIMS}


def _is_all_zero(taste: dict[str, float]) -> bool:
    """Check if all taste dimensions are zero."""
    return all(v == 0.0 for v in taste.values())


def _apply_taste(row: dict, taste: dict[str, float]):
    """Write taste values back into a row dict."""
    for dim in TASTE_DIMS:
        row[dim] = taste.get(dim, 0.0)


def _is_water_exact(name_lower: str) -> bool:
    """Check if dish name is exactly 'water' (not 'mineral water', etc.)."""
    return name_lower.strip() == "water"


# ── Phase 1: Keyword Scan ───────────────────────────────────────────────────


def _phase1_keyword_scan(name_lower: str) -> dict[str, float]:
    """Scan dish name for flavor keywords. Returns taste dict (may be all-zero)."""
    result = {d: 0.0 for d in TASTE_DIMS}
    matched_any = False

    for keyword in _SORTED_KEYWORDS:
        if keyword in name_lower:
            matched_any = True
            contributions = KEYWORD_MAP[keyword]
            for dim, value in contributions.items():
                result[dim] = min(1.0, result[dim] + value)

    return result if matched_any else {d: 0.0 for d in TASTE_DIMS}


# ── Phase 2: Category Priors ────────────────────────────────────────────────


def _phase2_category_prior(name_lower: str) -> tuple[dict[str, float], str]:
    """
    Apply category-based fallback prior based on dish name patterns.
    Returns (taste_dict, source_tag).
    source_tag is 'category_prior', 'neutral', or '' (no match).
    """
    result = {d: 0.0 for d in TASTE_DIMS}

    # Check for "Water" exact match first
    if _is_water_exact(name_lower):
        return result, "neutral"

    # Check beverage exceptions
    for exc in BEVERAGE_EXCEPTIONS:
        if exc in name_lower:
            return result, "neutral"

    # Check beverages
    is_beverage = any(pat in name_lower for pat in BEVERAGE_PATTERNS)
    if is_beverage:
        result["taste_sweet"] = 0.4
        # Citrus/tea sub-rule
        if any(pat in name_lower for pat in CITRUS_TEA_PATTERNS):
            result["taste_sour"] = 0.25
        return result, "category_prior"

    # Check desserts
    is_dessert = any(pat in name_lower for pat in DESSERT_PATTERNS)
    if is_dessert:
        result["taste_sweet"] = 0.5
        return result, "category_prior"

    # Check BBQ/grill/karahi
    is_bbq = any(pat in name_lower for pat in BBQ_GRILL_PATTERNS)
    if is_bbq:
        result["taste_umami"] = 0.4
        result["taste_spice"] = 0.35
        return result, "category_prior"

    return result, ""


# ── Phase 3: Restaurant Average ─────────────────────────────────────────────


def _compute_restaurant_averages(rows: list[dict]) -> dict[str, dict[str, float]]:
    """
    Compute per-restaurant mean taste vectors from dishes that have
    at least one non-zero taste dimension.
    Returns {restaurant_name: {taste_dim: mean_value}}.
    """
    sums = defaultdict(lambda: {d: 0.0 for d in TASTE_DIMS})
    counts = defaultdict(int)

    for row in rows:
        taste = _get_taste_values(row)
        if not _is_all_zero(taste):
            rest = row.get("restaurant_name", "")
            for dim in TASTE_DIMS:
                sums[rest][dim] += taste[dim]
            counts[rest] += 1

    averages = {}
    for rest in sums:
        if counts[rest] > 0:
            averages[rest] = {dim: round(sums[rest][dim] / counts[rest], 4) for dim in TASTE_DIMS}

    return averages


# ── Main Enrichment Pipeline ────────────────────────────────────────────────


def _fix_category_fallback(row: dict):
    if row.get("category", "").lower() != "other":
        return

    name = row.get("dish_name", "").lower()

    desi_keywords = [
        "karahi",
        "tikka",
        "kabab",
        "kebab",
        "masala",
        "handi",
        "boti",
        "sajji",
        "naan",
        "biryani",
        "pulao",
        "gosht",
        "daal",
        "paneer",
        "nihari",
        "paya",
        "qorma",
        "korma",
        "roti",
        "paratha",
        "raita",
        "mutton",
        "chana",
        "choley",
        "chapli",
        "makhni",
        "jalfrezi",
        "karai",
        "seekh",
        "bihari",
        "tandoori",
        "malai",
        "reshmi",
        "chargha",
        "charsi",
        "katakat",
        "qeema",
        "keema",
        "roghni",
        "haleem",
        "taka tak",
        "dhaba",
    ]
    if any(k in name for k in desi_keywords):
        row["category"] = "desi_traditional"
        return

    asian_keywords = [
        "chowmein",
        "manchurian",
        "szechuan",
        "thai",
        "sweet and sour",
        "sweet & sour",
        "kung pao",
        "chilli",
        "chilies",
        "oyster",
        "schezwan",
        "dragon",
        "spring roll",
        "noodle",
        "fried rice",
        "tamarind sauce",
        "black bean",
        "garlic sauce",
        "soup",
        "mongolian",
        "chop suey",
        "chow mein",
        "dumpling",
        "wonton",
        "manchow",
        "schezuan",
    ]
    if any(k in name for k in asian_keywords):
        row["category"] = "chinese_asian"
        return

    fast_food_keywords = [
        "burger",
        "fries",
        "broast",
        "zinger",
        "wings",
        "nuggets",
        "fried chicken",
        "wrap",
        "sandwich",
    ]
    if any(k in name for k in fast_food_keywords):
        row["category"] = "fast_food"
        return

    me_keywords = [
        "arabian",
        "mandi",
        "shawarma",
        "hummus",
        "falafel",
        "madghout",
        "tawook",
        "shish",
        "pita",
        "mutabbal",
    ]
    if any(k in name for k in me_keywords):
        row["category"] = "middle_eastern"
        return

    drink_keywords = [
        "tea",
        "drink",
        "shake",
        "lemonade",
        "lassi",
        "coffee",
        "juice",
        "colada",
        "water",
        "chaye",
        "qehwa",
        "margarita",
        "mojito",
        "slush",
        "smoothie",
    ]
    if any(k in name for k in drink_keywords):
        row["category"] = "beverages"
        return

    bakery_keywords = [
        "cake",
        "ice cream",
        "kheer",
        "halwa",
        "gulab jamun",
        "brownie",
        "dessert",
        "jelly",
        "pudding",
    ]
    if any(k in name for k in bakery_keywords):
        row["category"] = "cafe_bakery"
        return

    cont_keywords = ["steak", "parmesan", "alfredo", "pasta", "cordon bleu", "salsa", "salad"]
    if any(k in name for k in cont_keywords):
        row["category"] = "continental_upscale"
        return


def enrich_taste_profiles(rows: list[dict]) -> dict:
    for r in rows:
        _fix_category_fallback(r)

    """
    Enrich taste profiles for all dishes in the dataset.
    Modifies rows in-place. Returns enrichment statistics.

    Args:
        rows: List of dicts parsed from mood4food_dishes.csv.
              Each dict must have keys: dish_name, restaurant_name, category,
              taste_sweet, taste_salty, taste_sour, taste_bitter, taste_umami, taste_spice.

    Returns:
        Dict with enrichment statistics.
    """
    stats = {
        "total": len(rows),
        "original": 0,
        "keyword": 0,
        "category_prior": 0,
        "restaurant_average": 0,
        "global_prior": 0,
        "neutral": 0,
        "still_zero": 0,
    }

    # ── Pass 1: Mark originals and run keyword + category phases ────────
    for row in rows:
        taste = _get_taste_values(row)

        if not _is_all_zero(taste):
            # Original data — don't touch
            row["taste_source"] = "original"
            stats["original"] += 1
            continue

        name_lower = row.get("dish_name", "").strip().lower()

        # Phase 1: Keyword scan
        keyword_taste = _phase1_keyword_scan(name_lower)
        if not _is_all_zero(keyword_taste):
            _apply_taste(row, keyword_taste)
            row["taste_source"] = "keyword"
            stats["keyword"] += 1
            continue

        # Phase 2: Category prior
        category_taste, source_tag = _phase2_category_prior(name_lower)
        if source_tag == "neutral":
            row["taste_source"] = "neutral"
            stats["neutral"] += 1
            continue
        if source_tag == "category_prior" and not _is_all_zero(category_taste):
            _apply_taste(row, category_taste)
            row["taste_source"] = "category_prior"
            stats["category_prior"] += 1
            continue

        # Mark as pending for Phase 3
        row["taste_source"] = "_pending"

    # ── Pass 2: Compute restaurant averages (including Phase 1/2 enriched) ──
    restaurant_avgs = _compute_restaurant_averages(rows)

    # ── Pass 3: Apply restaurant averages to remaining zero-taste dishes ──
    for row in rows:
        if row.get("taste_source") != "_pending":
            continue

        rest = row.get("restaurant_name", "")
        category = row.get("category", "other")

        if rest in restaurant_avgs:
            avg = restaurant_avgs[rest]
            if not _is_all_zero(avg):
                _apply_taste(row, avg)
                row["taste_source"] = "restaurant_average"
                stats["restaurant_average"] += 1
                continue

        # Last resort: global category prior
        prior = GLOBAL_CATEGORY_PRIORS.get(category, GLOBAL_CATEGORY_PRIORS["other"])
        prior_taste = {d: prior.get(d, 0.0) for d in TASTE_DIMS}
        if not _is_all_zero(prior_taste):
            _apply_taste(row, prior_taste)
            row["taste_source"] = "global_prior"
            stats["global_prior"] += 1
        else:
            row["taste_source"] = "neutral"
            stats["still_zero"] += 1

    # ── Log summary ──
    log.info("─── Taste Enrichment Summary ───")
    log.info("  Total dishes: %d", stats["total"])
    log.info("  Original (non-zero CSV): %d", stats["original"])
    log.info("  Keyword-enriched: %d", stats["keyword"])
    log.info("  Category-prior: %d", stats["category_prior"])
    log.info("  Restaurant-average: %d", stats["restaurant_average"])
    log.info("  Global-prior: %d", stats["global_prior"])
    log.info("  Neutral (intentionally zero): %d", stats["neutral"])
    log.info("  Still zero: %d", stats["still_zero"])

    remaining_zero = stats["neutral"] + stats["still_zero"]
    pct = 100 * remaining_zero / stats["total"] if stats["total"] > 0 else 0
    log.info("  All-zero after enrichment: %d (%.1f%%)", remaining_zero, pct)
    log.info("────────────────────────────────")

    return stats

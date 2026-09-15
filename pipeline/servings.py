"""
Serving counts (Phase 1): how many people a dish feeds, and its price per person.

Precedence, recorded in serves_source:
  owner           the project owner's answer in data_review/platter_combo_review.xlsx
  menu            a count stated on the menu ("6-8 person serving", "For 2 Persons")
  double          "Double" in the name counts as two servings (the owner's rule)
  price_estimate  platters, combos and half/full portions only: the dish's price divided
                  by the restaurant's typical single-dish price, rounded, 1-10
  default         everything else serves one
The review worksheet uses the same indicator lists, so what it asks about and what
the build estimates always agree.
"""

import re
import statistics

BUNDLE = [
    ("platter", r"\bplatt?ers?\b"),
    ("combo", r"\bcombos?\b"),
    ("deal", r"\bdeals?\b"),
    ("family", r"\bfamily\b"),
    ("sharing", r"\bshar(?:e|ing)\b"),
    ("party", r"\bparty\b"),
    ("bucket", r"\bbuckets?\b"),
    ("feast", r"\bfeast\b"),
    ("box", r"\bbox\b"),
    ("bundle", r"\bbundle\b"),
    ("set", r"\bset\s*(?:menu|\d|[ivx]+\b|:)"),
    ("meal", r"\bmeals?\b"),
    ("dawat / thaal", r"\bdawat\b|\bthaal?\b"),
    ("whole", r"\bwhole\b"),
    ("kg", r"\d\s*kg\b|\bkg\b|\bkilo\b"),
    (
        "person count",
        r"\d+\s*(?:-|to)?\s*\d*\s*(?:person|persons|people|pax)|person\s*serving|\bfor\s+\d+\b|\bserves?\s+\d+",
    ),
]
PORTION = [("full", r"\bfull\b"), ("half", r"\bhalf\b")]
DOUBLE = r"\bdouble\b"
# A raw OCR line often holds several dishes, so from it only an explicit count is trusted.
SERVING_ONLY = [
    (
        "person count",
        r"\d+\s*(?:-|to)\s*\d+\s*(?:person|persons|people|pax)|\d+\s*(?:person|persons|people|pax)\s*serving"
        r"|person\s*serving|\bserves?\s+\d+",
    )
]
_SERVES_PATTERNS = (
    r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:person|persons|people|pax)",
    r"(\d+)()\s*(?:person|persons|people|pax)",
    r"\bfor\s+(\d+)(?:\s*-\s*(\d+))?\b",
    r"\bserves?\s+(\d+)(?:\s*-\s*(\d+))?",
)
NOT_RECOMMENDED = {"beverages", "add_ons"}


def matches(text: str, table) -> list[str]:
    return [label for label, pat in table if re.search(pat, text or "", re.I)]


def serving_indicators(name: str, description: str, raw_line: str) -> tuple[list[str], list[str]]:
    """(bundle words, portion words) — the reasons a dish may feed more than one person."""
    bundle = matches(name, BUNDLE)
    if not bundle:
        bundle = sorted(set(matches(description, BUNDLE) + matches(raw_line, SERVING_ONLY)))
    return bundle, matches(name, PORTION)


def parse_count(text: str) -> tuple[int, int] | None:
    """'2', '2-3', '2 to 3' -> (min, max); anything else -> None."""
    nums = [int(n) for n in re.findall(r"\d+", str(text or ""))]
    if not nums or not all(0 < n <= 50 for n in nums[:2]):
        return None
    lo, hi = (nums[0], nums[1]) if len(nums) >= 2 else (nums[0], nums[0])
    return (min(lo, hi), max(lo, hi))


def serves_from_text(text: str) -> tuple[int, int] | None:
    for pat in _SERVES_PATTERNS:
        m = re.search(pat, text or "", re.I)
        if m and 0 < int(m.group(1)) <= 30:
            lo = int(m.group(1))
            hi = int(m.group(2)) if m.group(2) else lo
            return (lo, max(lo, hi))
    return None


def typical_single_prices(rows: list[dict], price_key: str = "price_rs") -> dict[str, float]:
    """Each restaurant's median price over dishes with no serving indicator (at least 5 of them)."""
    prices: dict[str, list[float]] = {}
    for r in rows:
        p = float(r[price_key] or 0)
        if (
            r["category"] in NOT_RECOMMENDED
            or p <= 0
            or matches(r["dish_name"], BUNDLE + PORTION)
            or re.search(DOUBLE, r["dish_name"], re.I)
        ):
            continue
        prices.setdefault(r["restaurant_name"], []).append(p)
    return {n: statistics.median(ps) for n, ps in prices.items() if len(ps) >= 5}


def price_estimate(price: float, typical: float | None) -> int | None:
    if not typical or typical < 200 or price <= 0:
        return None
    return max(1, min(10, round(price / typical)))


def resolve(
    owner_answer, name: str, description: str, raw_line: str, price: float, typical: float | None
) -> dict:
    """Serving range and where it came from."""
    owner = parse_count(owner_answer) if owner_answer not in (None, "") else None
    if owner:
        return {"serves_min": owner[0], "serves_max": owner[1], "serves_source": "owner"}
    menu = serves_from_text(name) or serves_from_text(description) or serves_from_text(raw_line)
    if menu:
        return {"serves_min": menu[0], "serves_max": menu[1], "serves_source": "menu"}
    if re.search(DOUBLE, name or "", re.I):
        return {"serves_min": 2, "serves_max": 2, "serves_source": "double"}
    bundle, portion = serving_indicators(name, description, raw_line)
    if bundle or portion:
        guess = price_estimate(price, typical)
        if guess:
            return {"serves_min": guess, "serves_max": guess, "serves_source": "price_estimate"}
    return {"serves_min": 1, "serves_max": 1, "serves_source": "default"}


def price_per_person(price: float, serves_min: int, serves_max: int) -> float:
    return round(price / ((serves_min + serves_max) / 2), 1) if price > 0 else 0.0

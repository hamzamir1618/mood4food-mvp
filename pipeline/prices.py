"""
Automated price check (Phase 1), replacing a human price review.

Each dish gets:
  price_status  trusted | verified | unverified — whether its price is backed by a
                reviewer, the restaurant's website, or the dish's own OCR evidence
  gross_error   a reason the price cannot be right, or "" — these dishes are quarantined

Unverified prices are kept and shown as such: the partner's batch was corrected
after OCR (e.g. 34,507 -> 3,450), so a price missing from its OCR line is not
proof that it is wrong. See docs/PHASE1_DATA_DECISIONS.md.
"""

import re
import statistics

SIZE_WORDS = re.compile(
    r"platt?er|combo|deal|family|shar(?:e|ing)|party|bucket|feast|\bbox\b|\bset\b|meal|dawat|thaal"
    r"|person|people|serving|\bfor\s+\d|\bfull\b|\bhalf\b|\bwhole\b|\bkg\b",
    re.I,
)
_ARABIC_DIGITS = "٠-٩۰-۹"


def latin_numbers(text: str) -> list[float]:
    """Numbers written in Latin digits, reading '3.699' and '2,780' as thousands."""
    # [0-9], not \d: Python's \d also matches Urdu/Arabic digits, and float() accepts them,
    # which would read the OCR garble "۷8110" as Rs 78,110.
    t = re.sub(r"([0-9])\.([0-9]{3})\b", r"\1\2", text or "")
    t = re.sub(r"([0-9]),([0-9]{3})\b", r"\1\2", t)
    digit = f"0-9{_ARABIC_DIGITS}"
    return [float(n) for n in re.findall(rf"(?<![{digit}])[0-9]+(?:\.[0-9]+)?(?![{digit}])", t)]


def slash_corrected(numbers: list[float]) -> list[float]:
    """Menus write prices as '3450/-'; OCR often reads the '/-' as a trailing 7."""
    return [(n - 7) / 10 for n in numbers if n >= 107 and n % 10 == 7]


def candidate_prices(candidates: list[dict]) -> list[float]:
    """Every price the OCR step proposed for a line, including suggested splits."""
    out = []
    for c in candidates:
        values = [c.get("price_pkr"), *(c.get("price_candidates") or [])]
        values += [s.get("price_pkr") for s in c.get("suggested_splits") or []]
        out += [float(v) for v in values if v not in (None, "")]
    return out


def price_status(
    price: float, review_status: str, raw_line: str, candidates: list[dict]
) -> tuple[str, str]:
    if review_status == "human_confirmed":
        return "trusted", "confirmed by a reviewer"
    if review_status == "scraped":
        return "trusted", "scraped from the restaurant's website"
    if review_status == "manual":
        return "trusted", "entered manually"

    def found(pool):
        return any(abs(x - price) < 0.5 for x in pool)

    numbers = latin_numbers(raw_line)
    if found(numbers):
        return "verified", "price appears in its OCR line"
    if found(slash_corrected(numbers)):
        return "verified", "price appears in its OCR line once '/-' is read correctly"
    if found(candidate_prices(candidates)):
        return "verified", "price matches an OCR price candidate"
    return "unverified", "price not found in its OCR evidence"


def restaurant_medians(rows: list[dict], price_key: str = "price_rs") -> dict[str, float]:
    prices: dict[str, list[float]] = {}
    for r in rows:
        p = float(r[price_key] or 0)
        if p > 0:
            prices.setdefault(r["restaurant_name"], []).append(p)
    return {name: statistics.median(ps) for name, ps in prices.items()}


def gross_error(price: float, restaurant_median: float, text: str) -> str:
    """A reason the price cannot be right, or ''. `text` is the dish name plus its OCR line."""
    if price <= 0:
        return "no price"
    if price < 20:
        return "price under Rs 20"
    if price > 8 * max(restaurant_median, 1) and not SIZE_WORDS.search(text or ""):
        return "over 8x the restaurant's median price, with no size or serving word"
    return ""

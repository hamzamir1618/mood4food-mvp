"""
Where each restaurant is, in words people use (Phase 6).

The dataset's addresses are OpenStreetMap geocodes, mostly in Urdu script
("ایف-7, اسلام آباد, زون 1, ..."). The app shows a short area name instead: a sector
("F-7") or a named place ("Blue Area", "Bahria Town"). It also records how far each
restaurant's coordinates can be trusted, because many were geocoded only to their sector:
every F-10 restaurant in the dataset sits on the same point.

  place    the coordinates are this restaurant's own
  area     the centre of its sector: shared with other restaurants, or the address names
           nothing more specific than the sector, so a distance is approximate
  unknown  missing, or outside Islamabad and Rawalpindi (one restaurant was geocoded to
           Chittagong), so never used for a distance
"""

import re
from collections import Counter

# Islamabad and Rawalpindi, generously. Coordinates outside are a geocoding error.
BOUNDS = {"lat": (33.40, 33.90), "lng": (72.75, 73.40)}

_DIGITS = r"[0-9۰-۹٠-٩]"
LATIN_SECTOR = re.compile(r"\b([A-I])-(\d{1,2})(?:/\d)?\b")
# ایف F, جی G, آئی or آئ I, ایچ H, ای E, ڈی D; longer spellings first.
URDU_SECTOR = re.compile(
    rf"(ایف|جی|آئی|آئ|ایچ|ای|ڈی)[-\s]?({_DIGITS}{{1,2}})(?:/{_DIGITS})?(?!{_DIGITS})"
)
URDU_LETTERS = {"ایف": "F", "جی": "G", "آئی": "I", "آئ": "I", "ایچ": "H", "ای": "E", "ڈی": "D"}
TO_ASCII_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
# Named places, most specific first: a restaurant in DHA or Bahria Town is also in Rawat.
NAMED = (
    ("DHA", ("DHA", "ڈی ایچ اے")),
    ("Bahria Town", ("Bahria Town", "بحریہ ٹاؤن")),
    ("Saidpur", ("Saidpur", "سید پور")),
    ("Blue Area", ("Blue Area", "بلیو ایریا")),
    ("Rawat", ("Rawat", "روات")),
)


def _sector(text: str) -> str | None:
    m = LATIN_SECTOR.search(text)
    if m:
        return f"{m.group(1)}-{int(m.group(2))}"
    m = URDU_SECTOR.search(text)
    if m:
        return f"{URDU_LETTERS[m.group(1)]}-{int(m.group(2).translate(TO_ASCII_DIGITS))}"
    return None


def area_name(address: str | None) -> str | None:
    """A sector ("F-7") if the address has one, else a named place, else None."""
    text = address or ""
    sector = _sector(text)
    if sector:
        return sector
    return next((name for name, spellings in NAMED if any(s in text for s in spellings)), None)


def in_bounds(lat: float, lng: float) -> bool:
    return (
        BOUNDS["lat"][0] <= lat <= BOUNDS["lat"][1] and BOUNDS["lng"][0] <= lng <= BOUNDS["lng"][1]
    )


def _point(row: dict) -> tuple[float, float] | None:
    try:
        return float(row["restaurant_lat"]), float(row["restaurant_lng"])
    except (KeyError, TypeError, ValueError):
        return None


def _names_only_the_sector(address: str | None) -> bool:
    """True when the address's first part is just a sector: "ایف-10, اسلام آباد, ..."."""
    first = (address or "").split(",")[0].strip()
    return bool(LATIN_SECTOR.fullmatch(first) or URDU_SECTOR.fullmatch(first))


def restaurant_locations(rows: list[dict]) -> dict[str, dict]:
    """Each restaurant's {"area", "precision"}, keyed by restaurant name."""
    first: dict[str, dict] = {}
    for r in rows:
        first.setdefault(r["restaurant_name"], r)
    points = {name: _point(r) for name, r in first.items()}
    sharing = Counter(p for p in points.values() if p)

    out = {}
    for name, r in first.items():
        point = points[name]
        if point is None or not in_bounds(*point):
            out[name] = {"area": None, "precision": "unknown"}
            continue
        address = r.get("restaurant_address")
        approximate = sharing[point] > 1 or _names_only_the_sector(address)
        out[name] = {"area": area_name(address), "precision": "area" if approximate else "place"}
    return out

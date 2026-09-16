"""
The user's location (Phase 6). A request may send one (/submit form fields, or a
`location` on a /chat turn); it is kept with the session, so later requests reuse it.
Each candidate then carries a straight-line distance to its restaurant.

A distance is never invented: a restaurant whose coordinates are unknown (missing, or
geocoded outside the city) has none, and one located only to its sector's centre is
marked `location_precision: "area"`, so the app can say the distance is approximate.
"""

from math import asin, cos, radians, sin, sqrt
from typing import Optional

from pydantic import BaseModel, Field

EARTH_RADIUS_KM = 6371.0
NEARBY_KM = 10.0  # beyond this a dish is left out, as long as something closer matches
CONTRACT = "user_location"


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    label: Optional[str] = Field(default=None, max_length=40)  # "G-9 Markaz", for display


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance: as the crow flies, not by road."""
    p1, p2 = radians(lat1), radians(lat2)
    h = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(h))


def with_distances(candidates: list[dict], location: dict | None) -> list[dict]:
    """Sets each candidate's distance_km from the location; None where either is unknown."""
    for c in candidates:
        lat, lng = c.get("restaurant_lat"), c.get("restaurant_lng")
        known = location is not None and lat is not None and lng is not None
        c["distance_km"] = (
            round(distance_km(location["lat"], location["lng"], lat, lng), 1) if known else None
        )
    return candidates


def nearby(candidates: list[dict], limit_km: float = NEARBY_KM) -> list[dict]:
    """
    The candidates within `limit_km`, and those whose distance is unknown (not far, just not
    known). When nothing known is that close, all of them: a far match beats no match, and
    the distance term still ranks the nearer ones first.
    """
    kept = [c for c in candidates if c.get("distance_km") is None or c["distance_km"] <= limit_km]
    if any(c.get("distance_km") is not None for c in kept):
        return kept
    return candidates


def save_location(session_id: str, location: dict) -> None:
    from tier_1.contracts.session_store import save_contract

    save_contract(session_id, CONTRACT, Location.model_validate(location).model_dump())


def load_location(session_id: str) -> dict | None:
    from tier_1.contracts.session_store import load_contract

    return load_contract(session_id, CONTRACT)

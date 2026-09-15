"""
GET /areas: the areas the location picker offers (Phase 6). Built from the restaurants'
own coordinates, so every area listed has at least one restaurant, and each area's point
is the mean of its restaurants' coordinates. Restaurants whose coordinates are unknown
are left out.
"""

import logging
import re
from collections import defaultdict

from fastapi import APIRouter, HTTPException

log = logging.getLogger(__name__)
router = APIRouter(tags=["location"])

_cache: list[dict] | None = None
_SECTOR = re.compile(r"([A-I])-(\d+)")


def _order(area: str) -> tuple:
    """Sectors first, by letter and number (F-6 before F-10), then named places."""
    m = _SECTOR.fullmatch(area)
    return (0, m.group(1), int(m.group(2)), "") if m else (1, "", 0, area)


def group_areas(rows: list[dict]) -> list[dict]:
    """[{area, lat, lng, restaurants}] from Restaurant rows {area, lat, lng, precision}."""
    points = defaultdict(list)
    for r in rows:
        located = r.get("precision") in ("place", "area")
        if located and r.get("area") and r.get("lat") is not None and r.get("lng") is not None:
            points[r["area"]].append((r["lat"], r["lng"]))
    return [
        {
            "area": area,
            "lat": round(sum(p[0] for p in pts) / len(pts), 6),
            "lng": round(sum(p[1] for p in pts) / len(pts), 6),
            "restaurants": len(pts),
        }
        for area, pts in sorted(points.items(), key=lambda kv: _order(kv[0]))
    ]


@router.get("/areas")
def areas():
    """Areas to pick a location from, each with a point to measure distances from."""
    global _cache
    if _cache is None:
        from accounts.store import get_driver

        try:
            records, _, _ = get_driver().execute_query(
                "MATCH (r:Restaurant) RETURN r.area AS area, r.lat AS lat, r.lng AS lng, "
                "r.location_precision AS precision"
            )
        except Exception as exc:
            log.error("areas could not be loaded: %s", exc)
            raise HTTPException(503, "Areas couldn't be loaded. Please try again.")
        found = group_areas([dict(r) for r in records])
        if not found:  # an empty graph (not seeded yet) is not cached
            return {"areas": []}
        _cache = found
    return {"areas": _cache}

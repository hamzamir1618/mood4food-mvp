"""
Inputs for the context and novelty terms (Phase 3): the local hour, the weather in
Islamabad, and what the user was recommended or passed over in the last week.

The weather comes from Open-Meteo: free for non-commercial use, no key, data under
CC BY 4.0 (see ATTRIBUTIONS.md). It is cached for 30 minutes, and any failure just
leaves it out, so the context term says nothing about the weather.

The result is saved with the session as its "scoring_context", so /recalculate re-ranks
with the same inputs as the query it is re-ranking.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

log = logging.getLogger(__name__)

ISLAMABAD = (33.6844, 73.0479)
PKT = timezone(timedelta(hours=5))  # Pakistan has no daylight saving
WEATHER_TTL_S = 1800
HISTORY_DAYS = 7

_weather: tuple[float, float | None] | None = None  # (monotonic time, temperature)


def local_hour(now: datetime | None = None) -> int:
    return (now or datetime.now(timezone.utc)).astimezone(PKT).hour


def _fetch_temperature() -> float | None:
    lat, lon = ISLAMABAD
    resp = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current": "temperature_2m"},
        timeout=2.0,
    )
    resp.raise_for_status()
    return float(resp.json()["current"]["temperature_2m"])


def current_temperature() -> float | None:
    """Islamabad's temperature in °C, or None when it can't be fetched."""
    global _weather
    now = time.monotonic()
    if _weather and now - _weather[0] < WEATHER_TTL_S:
        return _weather[1]
    try:
        temperature = _fetch_temperature()
    except Exception as exc:
        log.warning("weather unavailable, leaving it out: %s", exc)
        temperature = None
    _weather = (now, temperature)
    return temperature


def recent_history(events, now: datetime | None = None) -> list[dict]:
    """Events from the last week that are about a dish, as {dish_uid, kind, days_ago}."""
    now = now or datetime.now(timezone.utc)
    recent = []
    for e in events:
        e = e.model_dump() if hasattr(e, "model_dump") else e
        if not e.get("dish_uid") or not e.get("at"):
            continue
        try:
            days = (now - datetime.fromisoformat(e["at"])).total_seconds() / 86400
        except ValueError:
            continue
        if 0 <= days <= HISTORY_DAYS:
            recent.append(
                {"dish_uid": e["dish_uid"], "kind": e["kind"], "days_ago": round(days, 2)}
            )
    return recent


def scoring_context(persona: str, profile=None, events=(), peers: dict | None = None) -> dict:
    """
    The session's scoring inputs. A signed-in user's profile supplies their goal, usual
    spend and persona, their learned taste, importance and weights, and `peers`: dishes
    users with a similar taste approved. A guest gets the persona's.
    """
    context = {
        "persona": persona,
        "hour": local_hour(),
        "temperature_c": current_temperature(),
        "history": recent_history(events),
        "party_size": 1,
    }
    if profile is not None:
        context["persona"] = profile.taste.persona_prior or persona
        context["goal"] = profile.goals.goal
        context["typical_spend"] = profile.goals.typical_spend_pkr
        if profile.taste.has_evidence():
            context["taste"] = dict(profile.taste.vector)
        context["importance"] = dict(profile.taste.importance)
        context["learned_from"] = profile.taste.updates
        if profile.taste.agent_weights:
            context["weights"] = dict(profile.taste.agent_weights)
    if peers:
        context["peers"] = peers
    return context

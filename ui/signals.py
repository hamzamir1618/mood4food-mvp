"""
What the layout is composed from: the user's explicit settings and what their history
shows. Worked out once per new request and kept with the session as "ui_signals", so
every screen of that request (a refinement, a slider move) is composed from the same
facts without another database read.

Only counts and names leave this module. It never decides anything; ui/compose.py does.
"""

from collections import Counter

from tier_2.scoring import CHEAP_WORDS, GOAL_WORDS


def _as_dict(event) -> dict:
    return event.model_dump() if hasattr(event, "model_dump") else dict(event)


def gather(profile, history, intent: dict, context: dict) -> dict:
    """
    The signals for one request. `profile` is None for a guest; `history` is the user's
    (or this browser's) events, newest or oldest first; `intent` is the parsed query
    with any saved dietary rules merged in; `context` is the scoring context.
    """
    events = [_as_dict(e) for e in history or []]

    refinements = Counter(
        (e.get("detail") or {}).get("critique")
        for e in events
        if e.get("kind") == "refined" and (e.get("detail") or {}).get("critique")
    )

    approvals: dict[str, dict] = {}
    for e in events:
        if e.get("kind") != "approved" or not e.get("dish_uid"):
            continue
        entry = approvals.setdefault(e["dish_uid"], {"name": e.get("dish_name", ""), "count": 0})
        entry["count"] += 1

    dietary = None
    if profile is not None:
        d = profile.dietary
        dietary = {"allergies": list(d.allergies), "diet": d.diet, "halal_only": d.halal_only}

    said = f"{intent.get('raw_input') or ''} {intent.get('craving') or ''}"
    # What this request asks for wins over the saved goal, as it does in the scorer: a guest
    # who asks for "high protein" should see the protein, not nothing.
    query_goal = next((goal for pattern, goal in GOAL_WORDS if pattern.search(said)), None)
    return {
        "signed_in": profile is not None,
        "persona": context.get("persona") or "",
        "goal": query_goal or context.get("goal"),
        "dietary": dietary,
        # The query's own rules, after any saved ones were merged in
        "allergens": sorted(intent.get("allergens_pruned") or []),
        "vegan": bool(intent.get("is_vegan")),
        "vegetarian": bool(intent.get("is_vegetarian")),
        "halal": bool(intent.get("is_halal")),
        "cheap_query": bool(CHEAP_WORDS.search(said)),
        "learned_from": context.get("learned_from") or 0,
        "refinements": dict(refinements),
        "approvals": approvals,
        "peers": dict(context.get("peers") or {}),
        "queries": sum(1 for e in events if e.get("kind") == "query"),
        # How many are eating, which decides whether a meal's total is also said per person.
        "party_size": int(context.get("party_size") or 1),
    }

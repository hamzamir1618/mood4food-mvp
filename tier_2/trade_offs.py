"""
The other ways to read a request the menus couldn't meet in full.

"Biryani under 50" has no answer: nothing on the menus costs Rs 50. "Spicy chicken under 200" has
only a near one. Rather than a dead end, or a silent substitute, the app shows what giving up one
thing would get: spend up to Rs 800 and it's the Sindhi Matka Biryani; keep Rs 200 and drop the
spice and it's the Chicken Corn Soup. Each option is ranked by the same decision core as the pick
itself, so the dish it names is the dish choosing it would actually give.

What an option may give up is an ask (tier_1/asks.py): a limit, a dish, a food, a cuisine or a
flavour. Allergies, diet and halal are never asks, so no option can loosen one. Choosing an option
re-runs the request with that one thing changed (api/pipeline.py `recommend_intent`).

Everything here works from the open pool: every dish the person's rules allow, before any limit or
dish is applied. It is one more query per request, and the walkthrough's counts come from it too.
"""

import logging
import math

from tier_1 import asks as asking

log = logging.getLogger(__name__)

NO_LIMIT = 999999
OPTIONS_MAX = 3
SHORTLIST = 3  # a raised limit lets in this many dishes that meet the rest of the request
ROUND_TO = 50  # ...rounded up to a price a person would say
RECOMMENDABLE = """
MATCH (d:Dish)
WHERE coalesce(d.quarantined, false) = false
  AND NOT d.category IN ["add_ons", "sides", "beverages"]
RETURN count(d) AS n
"""


def open_pool(intent: dict) -> list[dict]:
    """Every dish this person may be offered at all: their rules applied, nothing else."""
    from accounts.store import get_driver
    from tier_1.symbolic_anchoring import query_safe_candidates

    rules = asking.rules_of(intent)
    return query_safe_candidates(
        list(intent.get("allergens_pruned") or []),
        NO_LIMIT,
        "",
        rules["vegan"],
        rules["vegetarian"],
        is_halal=rules["halal"],
        driver=get_driver(),
    )


def recommendable() -> int | None:
    """How many dishes the app can recommend to anyone, before any rule."""
    from accounts.store import get_driver

    records, _, _ = get_driver().execute_query(RECOMMENDABLE)
    return records[0]["n"] if records else None


def applied(intent: dict, change: dict) -> dict:
    """The request with one option's change made: a new limit, or an ask set aside."""
    out = dict(intent)
    if change.get("budget_max_pkr"):
        out["budget_max_pkr"] = float(change["budget_max_pkr"])
    aside = sorted({*(out.get("set_aside") or []), *(change.get("set_aside") or [])})
    out["set_aside"] = aside
    out["mood_vector"] = {
        k: (0.0 if f"taste:{k}" in aside else v) for k, v in (out.get("mood_vector") or {}).items()
    }
    return out


def _round_up(price: float) -> float:
    return float(math.ceil(price / ROUND_TO) * ROUND_TO)


def _fully(asks: list[asking.Ask], dish: dict) -> bool:
    return all(asking.degree(a, dish) >= 1 for a in asks)


def options(pool: list[dict], intent: dict, context: dict) -> list[dict]:
    """Up to OPTIONS_MAX ways to change one thing, each with the dish it would give."""
    from api.location import nearby
    from tier_2.scoring import build_preferences, rank

    asks = asking.asks_of(intent)
    budget = next((a for a in asks if a.kind == "budget"), None)
    out, seen = [], set()
    for ask in asks:
        rest = [a for a in asks if a.id != ask.id]
        wanted = [a for a in rest if a.kind != "budget"]
        if ask.kind == "budget":
            fits = sorted(
                (c for c in pool if _fully(wanted, c) and c.get("price_pkr")),
                key=lambda c: float(c["price_pkr"]),
            )
            if not fits:
                continue
            ceiling = _round_up(float(fits[min(SHORTLIST, len(fits)) - 1]["price_pkr"]))
            if ceiling <= float(ask.key):
                continue  # the limit isn't what stood in the way
            kept = [c for c in fits if float(c["price_pkr"]) <= ceiling]
            change = {"budget_max_pkr": ceiling}
            label = f"Spend up to {asking.rupees(ceiling)}"
            then = f"Up to {asking.rupees(ceiling)}"
        else:
            if not rest:
                continue  # without it there's nothing left of the request to answer
            kept = [c for c in pool if _fully(rest, c)]
            change = {"set_aside": [ask.id]}
            label = f"Forget “{ask.words}”"
            then = f"Leaving out {ask.words}"
        kept = nearby(kept)
        if not kept:
            continue
        best = rank(kept, build_preferences(applied(intent, change), context))[0]
        if best["dish_id"] in seen:
            continue  # two ways to the same dish is one option
        seen.add(best["dish_id"])
        keeps = asking.phrase(wanted) or "dish"
        within = f" at {budget.words}" if budget and ask.kind != "budget" else ""
        out.append(
            {
                "id": ask.id,
                "label": label,
                "gives_up": ask.words if ask.kind != "budget" else f"your {budget.words} limit",
                "keeps": asking.phrase(wanted),
                "count": len(kept),
                "change": change,
                "then": f"{then}: here's the best {keeps}{within}.",
                "dish": {
                    "dish_id": best["dish_id"],
                    "name": best["name"],
                    "price_pkr": best["price_pkr"],
                    "restaurant_name": best.get("restaurant_name"),
                },
            }
        )
    return out[:OPTIONS_MAX]


def notice(asks: list[asking.Ask], pool: list[dict], intent: dict, trace: list[dict]) -> str:
    """
    What couldn't be had, said precisely: under the limit, for this diet, or on the menus at all.
    Empty when the request was met, or when there's nothing more exact to say than Tier 1 did.
    """
    budget = next((a for a in asks if a.kind == "budget"), None)
    wanted = [a for a in asks if a.kind != "budget"]
    what = asking.phrase(wanted)
    full = [c for c in pool if _fully(wanted, c)]
    within = [c for c in full if not budget or asking.degree(budget, c) >= 1]
    if budget and not any(asking.degree(budget, c) >= 1 for c in pool):
        return f"Nothing on the menus I hold costs {budget.words}."
    if not what or len(within) >= SHORTLIST:
        return ""
    rules = asking.rules_of(intent)
    diet = "vegan" if rules["vegan"] else "vegetarian" if rules["vegetarian"] else ""
    if budget and full and not within:
        lead = f"Nothing at {budget.words} is {what}"
    elif budget and within:
        lead = f"Only {len(within)} dish{'es' if len(within) > 1 else ''} at {budget.words} "
        lead += f"{'are' if len(within) > 1 else 'is'} {what}"
    elif diet:
        lead = f"No {diet} dish is {what}"
    elif rules["allergens"] or rules["ingredients"] or rules["halal"]:
        lead = f"Nothing that fits your rules is {what}"
    else:
        lead = f"Nothing on the menus I hold is {what}"
    closest = next((t for t in trace if t.get("step") == "closest"), None)
    if closest is not None and not closest.get("count"):
        return f"{lead}, and nothing there is anything like it."
    return f"{lead}, so the dishes closest to it come first."


def examine(evaluation: dict, context: dict, location: dict | None) -> dict:
    """
    The counts, the options and the exact notice for one request, to keep with its evaluation.
    Never fatal: without them the pick stands, unexplained by one step.
    """
    from api.location import with_distances

    intent = evaluation.get("source_intent") or {}
    try:
        pool = with_distances(open_pool(intent), location)
    except Exception as exc:
        log.warning("the open pool couldn't be read, so no trade-offs: %s", exc)
        return {}
    asks = asking.asks_of(intent)
    budget = next((a for a in asks if a.kind == "budget"), None)
    counts = {
        "rules": len(pool),
        "in_budget": sum(1 for c in pool if not budget or asking.degree(budget, c) >= 1),
    }
    rules = asking.rules_of(intent)
    has_rules = any(rules[k] for k in ("vegan", "vegetarian", "halal", "allergens", "ingredients"))
    try:
        counts["recommendable"] = recommendable() if has_rules else len(pool)
    except Exception as exc:
        log.warning("the dataset couldn't be counted: %s", exc)
        counts["recommendable"] = None
    found = {"counts": counts}

    # Tier 1 records a "closest" step exactly when it had to widen and kept going on closeness;
    # a category relaxed and then met by name ("chicken karahi") was met in full.
    widened = any(t.get("step") == "closest" for t in evaluation.get("trace") or [])
    if not widened and evaluation.get("safe_candidates"):
        return found  # the request was met in full: nothing to trade
    try:
        found["trade_offs"] = options(pool, intent, context)
    except Exception as exc:
        log.warning("trade-offs couldn't be weighed: %s", exc)
    exact = notice(asks, pool, intent, evaluation.get("trace") or [])
    if exact:
        from tier_1.symbolic_anchoring import relaxation_sentence, said_in

        # Conflicts and what the app can't do are said as Tier 1 says them; only the part
        # about what couldn't be found is made exact.
        clashes = [
            r for r in evaluation.get("relaxations") or [] if r.get("constraint") == "conflict"
        ]
        found["message"] = " ".join(
            s for s in (relaxation_sentence(clashes, said_in(intent)), exact) if s
        )
    return found

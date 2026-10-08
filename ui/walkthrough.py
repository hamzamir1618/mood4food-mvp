"""
From your words to this dish: the request's path, step by step, in plain language.

Every step is read off what the pipeline actually did — the intent it extracted, the counts Tier 1
recorded as it filtered (`trace`), the counts at the person's rules and limit (`counts`, from the
open pool in tier_2/trade_offs.py), the conversation's answers, and the weights the winner was
ranked under. Nothing is reconstructed or estimated, so a number on this panel is a number the
pipeline saw, and a step that didn't happen isn't told.
"""

from tier_1 import asks as asking
from tier_1 import query_words

ADJUSTMENT_WORDS = {
    "price_below": "something cheaper",
    "calories_below": "something lighter",
    "calories_above": "something more filling",
    "protein_at_least": "something more filling",
    "spice_above": "something spicier",
    "spice_below": "something milder",
    "health_above": "something healthier",
    "exclude_categories": "something different",
    "exclude_restaurants": "something from somewhere else",
    "exclude_dishes": "another dish",
}


def _n(count: int, one: str, many: str | None = None) -> str:
    return f"{count:,} {one if count == 1 else (many or one + 's')}"


def _pretty(asked: str) -> str:
    return asking.CUISINE_WORDS.get(asked, asked.replace("_", " "))


def _join(words: list[str]) -> str:
    if len(words) < 2:
        return "".join(words)
    return f"{', '.join(words[:-1])} and {words[-1]}"


def rules_words(intent: dict) -> list[str]:
    """The rules a request carries, as the person would say them."""
    from tier_1.symbolic_anchoring import EXCLUSION_ALLERGENS

    rules = asking.rules_of(intent)
    words = [w for w in ("vegan", "vegetarian", "halal") if rules[w]]
    if rules["vegan"] and "vegetarian" in words:
        words.remove("vegetarian")
    words += [f"no {a}" for a in rules["allergens"]]
    for term in intent.get("allergens_pruned") or []:
        term = str(term).strip().lower()
        if term in ("vegan", "vegetarian") or term in rules["allergens"]:
            continue
        if term in EXCLUSION_ALLERGENS:
            continue  # "no bread" is already said as "no gluten"
        words.append(f"no {term}")
    return list(dict.fromkeys(words))


def _read(intent: dict, asks: list[asking.Ask]) -> str:
    parts = [a.words for a in asks if a.kind != "budget"]
    budget = next((a for a in asks if a.kind == "budget"), None)
    if budget:
        parts.append(budget.words)
    raw = " ".join(str(intent.get(k) or "") for k in ("raw_input", "craving"))
    for dim, limit in query_words.avoided_tastes(raw).items():
        word = asking.TASTE_WORDS.get(dim, dim)
        parts.append(f"not {'very ' if limit >= query_words.AVOID_VERY else ''}{word}")
    parts += rules_words(intent)
    if not parts:
        return "I found no particular dish, price or flavour in that, so everything stayed open."
    return f"I read that as: {_join(parts)}."


def _from_trace(trace: list[dict], counts: dict) -> list[str]:
    out: list[str] = []
    said: set[str] = set()
    matched = 0
    for step in trace:
        kind, count, asked = step.get("step"), step.get("count") or 0, step.get("asked") or ""
        relaxed = step.get("relaxed")
        if kind == "query" and asked:
            if count:
                out.append(f"{_n(count, 'dish', 'dishes')} of those match “{_pretty(asked)}”.")
            else:
                out.append(f"None of those is “{_pretty(asked)}”.")
            said.add(asked)
            matched = count
        elif kind == "category":
            lead = "That's too few to choose between, so" if matched else "So"
            out.append(f"{lead} I looked at all {count:,} of them instead.")
        elif kind == "named_dish" and relaxed:
            if asked in said:
                continue  # already said that nothing is called that
            out.append(f"None of those is called {asked}, so the name stopped being a rule.")
        elif kind == "named_dish":
            out.append(
                f"{_n(count, 'dish', 'dishes')} of them {'is' if count == 1 else 'are'} "
                f"called {asked}."
            )
        elif kind == "named_ingredient":
            out.append(f"{count:,} of them name what you asked for outright, so I kept those.")
        elif kind == "taste":
            word = asking.TASTE_WORDS.get(asked, asked)
            if relaxed:
                out.append(
                    f"Only {count} {'is' if count == 1 else 'are'} properly {word}: too few, "
                    f"so {word} counts towards the score instead of ruling dishes out."
                )
            else:
                out.append(f"{count:,} of them are properly {word}.")
        elif kind == "avoid_taste":
            word = asking.TASTE_WORDS.get(asked, asked)
            if step.get("limit", 0) >= query_words.AVOID_VERY:
                word = f"very {word}"
            if relaxed:
                out.append(
                    f"Only {count} of them {'is' if count == 1 else 'are'}n't {word}: too few to "
                    f"choose between, so {word} dishes stayed in."
                )
            else:
                out.append(f"{count:,} of them aren't {word}, so I kept those.")
        elif kind == "cooking":
            out.append(f"{count:,} of them are {asked}.")
        elif kind == "closest":
            if count:
                out.append(
                    f"I put the dishes closest to what you asked first: {count:,} of them "
                    "meet at least part of it."
                )
            else:
                out.append(
                    "None of them is anything like it, so these are simply the best of what's left."
                )
    return out


def _conversation(conversation) -> list[str]:
    if conversation is None:
        return []
    out = [f"You told me: {chip['label']}." for chip in (conversation.stated or {}).values()]
    adj = conversation.adjustments
    asked = []
    for field, words in ADJUSTMENT_WORDS.items():
        value = getattr(adj, field, None)
        if value not in (None, [], {}) and words not in asked:
            asked.append(words)
    if asked:
        out.append(f"Then you asked for {_join(asked)}.")
    return out


def _scoring(blueprint: dict) -> str:
    count = blueprint.get("candidate_count") or len(blueprint.get("top_candidates") or [])
    weights = blueprint.get("agent_weights") or {}
    u = blueprint.get("utility_breakdown") or {}
    parts = [
        f"health {round((weights.get('w_h') or 0) * 100)}%",
        f"price {round((weights.get('w_b') or 0) * 100)}%",
    ]
    if u.get("u_taste") is not None:
        parts.append(f"taste {round((weights.get('w_t') or 0) * 100)}%")
    line = f"I scored the {_n(count, 'dish', 'dishes')} left on {_join(parts)}"
    if u.get("u_distance") is not None:
        line += ", with distance counting a little"
    line += "."
    if u.get("u_taste") is None:
        line += " Taste sat out: I don't know your taste yet, and you didn't name a flavour."
    return line


def steps(evaluation: dict, conversation, blueprint: dict) -> list[dict]:
    """The walkthrough for the recommendation on screen, as [{kind, text}]."""
    intent = evaluation.get("source_intent") or {}
    counts = evaluation.get("counts") or {}
    asks = asking.asks_of(intent)
    out: list[dict] = []

    def say(kind: str, text: str) -> None:
        if text:
            out.append({"kind": kind, "text": text})

    raw = str(intent.get("raw_input") or "").strip()
    if raw:
        say("said", f"You said “{raw}”.")
    chose = intent.get("chose") or {}
    if chose.get("text"):
        say("chose", f"Then you chose: {chose['text']}.")
    say("read", _read(intent, asks))
    for r in evaluation.get("relaxations") or []:
        if r.get("constraint") == "conflict":
            reason = r["reason"][0].upper() + r["reason"][1:]
            say(
                "conflict",
                f"{reason}. Your rules always come first, so I left {r['old_value']} out.",
            )

    total, ruled = counts.get("recommendable"), counts.get("rules")
    if ruled is not None:
        if rules_words(intent) and total:
            say(
                "rules",
                f"Your rules leave {ruled:,} of the {total:,} dishes I can recommend. "
                "I never bend those.",
            )
        else:
            say("rules", f"I started from all {ruled:,} dishes I can recommend.")
    budget = next((a for a in asks if a.kind == "budget"), None)
    if budget and counts.get("in_budget") is not None:
        left = counts["in_budget"]
        say(
            "limit",
            f"{budget.words[0].upper()}{budget.words[1:]} leaves {left:,} of them."
            if left
            else f"None of them costs {budget.words}.",
        )
    for line in _from_trace(evaluation.get("trace") or [], counts):
        say("narrow", line)
    for line in _conversation(conversation):
        say("answer", line)

    winner = blueprint.get("winning_dish") or {}
    if not winner:
        return out
    say("score", _scoring(blueprint))
    meets = [m.get("clause") or m["words"] for m in winner.get("meets") or []]
    line = f"{winner.get('name')} came out on top"
    if meets:
        line += f": it {_join(meets)}"
    say("pick", line + ".")
    if winner.get("summary"):
        say("pick", winner["summary"])
    return out

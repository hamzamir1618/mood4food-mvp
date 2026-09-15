"""
Which question, if any, to ask.

A question is asked only when its answer would change the pick. Every answer on offer
is tried on the leading candidates, and the question where the most answers change the
winner is asked, if at least half of them do. At most two per conversation, and every
question can be skipped. Answers that would leave nothing to recommend are never offered.
"""

import re

from dialogue.pool import candidates_under, winner_under
from dialogue.state import Conversation, Question
from tier_2.scoring import rank

MAX_QUESTIONS = 2
ASK_THRESHOLD = 0.5  # ask only if at least half the answers change the pick
SHORT_POOL = 150  # questions are weighed on the leading candidates, to stay fast
MIN_POOL = 5  # with fewer options than this there's nothing worth asking

CATEGORY_LABELS = {
    "desi_traditional": "Desi",
    "afghan": "Afghan",
    "middle_eastern": "Middle Eastern",
    "chinese_asian": "Chinese & Asian",
    "continental_upscale": "Continental",
    "fast_food": "Fast food",
    "pizza": "Pizza",
    "sandwich": "Sandwiches & wraps",
    "cafe_bakery": "Café & desserts",
}
TASTE_CHIPS = {
    "spicy": {"label": "Spicy", "adjust": {"craved": {"spice": 0.9}}},
    "savoury": {"label": "Savoury", "adjust": {"craved": {"umami": 0.8, "salty": 0.6}}},
    "sweet": {"label": "Something sweet", "adjust": {"craved": {"sweet": 0.9}}},
    "fresh": {"label": "Fresh & tangy", "adjust": {"craved": {"sour": 0.6}}},
}
PARTY_CHIPS = {
    "1": {"label": "Just me", "adjust": {"party_size": 1}},
    "2": {"label": "Two of us", "adjust": {"party_size": 2}},
    "4": {"label": "Three or four", "adjust": {"party_size": 4}},
    "6": {"label": "Five or more", "adjust": {"party_size": 6}},
}
# Words that answer a question in free text, when no answer's label is typed.
TASTE_WORDS = {
    "spicy": ("spicy", "spice", "hot", "chilli", "chili"),
    "savoury": ("savoury", "savory", "salty", "umami", "meaty"),
    "sweet": ("sweet", "dessert"),
    "fresh": ("fresh", "tangy", "sour", "zesty", "light"),
}
CUISINE_WORDS = {
    "desi_traditional": ("desi", "pakistani", "karahi", "biryani"),
    "afghan": ("afghan",),
    "middle_eastern": ("middle eastern", "arabic", "turkish", "lebanese"),
    "chinese_asian": ("chinese", "asian", "thai", "japanese"),
    "continental_upscale": ("continental", "italian", "steak"),
    "fast_food": ("fast food", "burger", "fries"),
    "pizza": ("pizza",),
    "sandwich": ("sandwich", "wrap"),
    "cafe_bakery": ("cafe", "café", "dessert", "cake", "coffee"),
}


def _hundreds(amount: float) -> int:
    return max(100, int(round(amount / 100.0)) * 100)


def candidate_questions(
    intent: dict, context: dict, conversation: Conversation, short: list[dict]
) -> list[Question]:
    """The questions whose slot the query and the conversation haven't settled."""
    adj, asked = conversation.adjustments, set(conversation.asked)
    mood = intent.get("mood_vector") or {}
    out = []
    if (
        "taste" not in asked
        and not adj.craved
        and not any(float(v or 0) > 0 for v in mood.values())
    ):
        out.append(Question(slot="taste", text="What are you in the mood for?", chips=TASTE_CHIPS))
    if "cuisine" not in asked and not adj.category and not intent.get("preferred_category"):
        cats = list(
            dict.fromkeys(c.get("category") for c in short if c.get("category") in CATEGORY_LABELS)
        )
        if len(cats) >= 2:
            chips = {c: {"label": CATEGORY_LABELS[c], "adjust": {"category": c}} for c in cats[:4]}
            out.append(Question(slot="cuisine", text="Any cuisine in mind?", chips=chips))
    if (
        "budget" not in asked
        and adj.ceiling is None
        and not intent.get("budget_max_pkr")
        and not context.get("typical_spend")
    ):
        prices = sorted(float(c.get("price_pkr") or 0.0) for c in short)
        low, mid = _hundreds(prices[len(prices) // 3]), _hundreds(prices[2 * len(prices) // 3])
        if low < mid:
            chips = {
                str(low): {"label": f"Under Rs {low:,}", "adjust": {"ceiling": float(low)}},
                str(mid): {"label": f"Up to Rs {mid:,}", "adjust": {"ceiling": float(mid)}},
            }
            out.append(
                Question(slot="budget", text="Roughly how much do you want to spend?", chips=chips)
            )
    if (
        "party" not in asked
        and adj.party_size is None
        and any((c.get("serves_max") or 1) > 1 for c in short[:30])
    ):
        out.append(Question(slot="party", text="Who's eating?", chips=PARTY_CHIPS))
    return out


def best_question(
    pool: list[dict], intent: dict, context: dict, conversation: Conversation
) -> Question | None:
    """The question most worth asking now, or None when no answer would change much."""
    if conversation.closed or len(conversation.asked) >= MAX_QUESTIONS:
        return None
    kept, prefs, _ = candidates_under(pool, intent, context, conversation.adjustments)
    if len(kept) < MIN_POOL:
        return None
    ranked = rank(kept, prefs)
    by_id = {c["dish_id"]: c for c in kept}
    short = [by_id[s["dish_id"]] for s in ranked[:SHORT_POOL]]
    leader = ranked[0]["dish_id"]

    best, best_share = None, 0.0
    for question in candidate_questions(intent, context, conversation, short):
        chips, changed = {}, 0
        for value, chip in question.chips.items():
            adj = conversation.adjustments.merged(chip["adjust"])
            winner = winner_under(short, intent, context, adj)
            if winner is None:
                continue  # never offer an answer that leaves nothing to recommend
            chips[value] = chip
            changed += winner != leader
        if len(chips) < 2:
            continue
        share = changed / len(chips)
        if share > best_share:
            best_share = share
            why = f"{changed} of the {len(chips)} answers would change what I pick."
            best = question.model_copy(update={"chips": chips, "why": why})
    return best if best_share >= ASK_THRESHOLD else None


def parse_answer(text: str, pending: Question) -> tuple[str, dict] | None:
    """A typed answer to the open question as (value, chip), or None if it isn't one."""
    lowered = text.lower()
    for value, chip in pending.chips.items():
        if chip["label"].lower() in lowered:
            return value, chip
    if pending.slot == "taste":
        for value, words in TASTE_WORDS.items():
            if value in pending.chips and any(re.search(rf"\b{w}\b", lowered) for w in words):
                return value, pending.chips[value]
    if pending.slot == "cuisine":
        for value, words in CUISINE_WORDS.items():
            if value in pending.chips and any(w in lowered for w in words):
                return value, pending.chips[value]
    if pending.slot == "party" and re.search(r"\b(just me|myself|alone|only me)\b", lowered):
        return "1", PARTY_CHIPS["1"]
    number = re.search(r"\d[\d,]*", lowered)
    if number:
        n = int(number.group().replace(",", ""))
        if pending.slot == "budget" and n >= 50:
            return f"custom:{n}", {"label": f"Under Rs {n:,}", "adjust": {"ceiling": float(n)}}
        if pending.slot == "party" and 1 <= n <= 30:
            label = "Just me" if n == 1 else f"{n} people"
            return f"custom:{n}", {"label": label, "adjust": {"party_size": n}}
    return None

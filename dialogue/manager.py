"""
The turn logic behind /chat. Each turn is one of: new text, an answer to the open
question, a refinement, or "just pick for me". The reply is either a question with
answer chips or a recommendation with refinement chips. See docs/CONVERSATION.md.

Only new text runs the pipeline, and so the intent extractor. Answers and refinements
re-rank the candidates that query already found.
"""

import logging

from fastapi import HTTPException, Request

from dialogue import critiques, distill, pool, questions, state
from dialogue.state import Adjustments, Conversation, Question

log = logging.getLogger(__name__)

SKIP_LABEL = "Just pick for me"
KEEP_LABEL = "Keep my pick"
# How "Everything here is ..." reads for categories whose short name isn't a food on its own.
KIND_PHRASES = {"cafe_bakery": "café food", "sandwich": "sandwiches", "other": "one kind of food"}
RELAX = "relax"  # the slot of the "what can I loosen?" question

# What a refinement that found nothing may offer to loosen, one at a time, and only when doing
# so would actually find a dish. Allergies, diet and halal are Tier 1 rules, not adjustments:
# they are never on this list and never offered.
RELAXABLE = (
    (("category",), "Any cuisine, not just {category}"),
    (("ceiling",), "Spend more than {ceiling}"),
    (("price_below",), "Forget “cheaper”"),
    (("calories_below",), "Forget “lighter”"),
    (("calories_above", "protein_at_least"), "Forget “more filling”"),
    (("spice_above",), "Forget “spicier”"),
    (("spice_below",), "Forget “milder”"),
    (("health_above",), "Forget “healthier”"),
    (("exclude_categories",), "Bring back the cuisines I set aside"),
    (("exclude_restaurants", "exclude_dishes"), "Bring back the dishes I skipped"),
)


def handle(request: Request, turn) -> dict:
    session_id = request.state.session_id
    conversation = state.load(session_id)
    if getattr(turn, "location", None) is not None:
        from api.location import save_location

        save_location(session_id, turn.location.model_dump())

    if turn.text is not None:
        text = turn.text.strip()
        if not text:
            raise HTTPException(400, "Tell me what you'd like to eat.")
        if conversation and conversation.pending:
            parsed = questions.parse_answer(text, conversation.pending)
            if parsed:
                return _answer(request, conversation, *parsed)
        else:
            critique = critiques.parse(text)
            if critique and _current(session_id):
                return _refine(request, conversation or Conversation(closed=True), critique)
        return _new_query(request, text)

    if turn.answer is not None:
        pending = conversation.pending if conversation else None
        if pending is None or pending.slot != turn.answer.question:
            raise HTTPException(409, "That question isn't open any more.")
        chip = pending.chips.get(turn.answer.value)
        if chip is None:
            raise HTTPException(422, "That isn't one of the answers offered.")
        return _answer(request, conversation, turn.answer.value, chip)

    if _current(session_id) is None:
        raise HTTPException(400, "Start by telling me what you'd like to eat.")
    conversation = conversation or Conversation(closed=True)
    if turn.skip:
        conversation.closed = True
        return _recommendation(
            request, conversation, _current_enriched(session_id), "Here's my pick."
        )
    if conversation.pending:
        raise HTTPException(409, "Answer the question, or skip it, first.")
    return _refine(request, conversation, turn.critique)


# ── Turns ────────────────────────────────────────────────────────────────────
def _new_query(request: Request, text: str) -> dict:
    from api.pipeline import recommend

    blueprint = recommend(request, text=text)
    return _next(request, Conversation(), blueprint, reply=None)


def _answer(request: Request, conversation: Conversation, value: str, chip: dict) -> dict:
    session_id = request.state.session_id
    slot = conversation.pending.slot
    if slot == RELAX:
        conversation.pending = None
        loosened = Adjustments(**chip["replace"])
        blueprint = pool.rerank(session_id, loosened)
        if blueprint is None:  # the options were checked when offered; the pool can't shrink
            reply = "That no longer finds anything, so I've kept my pick."
            return _recommendation(request, conversation, _current_enriched(session_id), reply)
        conversation.adjustments = loosened
        return _recommendation(request, conversation, blueprint, f"{chip['label']}: {chip['then']}")
    conversation.asked.append(slot)
    conversation.pending = None
    adjustments = conversation.adjustments.merged(chip["adjust"])
    blueprint = pool.rerank(session_id, adjustments)
    if blueprint is None:  # offered answers are checked first; a typed one may not fit
        reply = f"Nothing fits “{chip['label']}”, so here's my pick without it."
        return _recommendation(request, conversation, _current_enriched(session_id), reply)
    conversation.adjustments = adjustments
    conversation.stated[slot] = chip
    return _next(request, conversation, blueprint, reply=f"{chip['label']}, got it.")


def _refine(request: Request, conversation: Conversation, critique: str) -> dict:
    session_id = request.state.session_id
    current = _current(session_id)
    winner = current["winning_dish"]
    word = critiques.WORDS[critique]
    if critique == "different":
        trial, done = _different(session_id, conversation.adjustments, winner)
    else:
        change = critiques.adjustment(critique, winner, current.get("utility_breakdown") or {})
        if change is None:
            reply = critiques.missing(critique, winner)
            return _recommendation(request, conversation, _current_enriched(session_id), reply)
        trial, done = conversation.adjustments.merged(change), f"Here's something {word}."
    blueprint = pool.rerank(session_id, trial)
    if blueprint is None:
        return _loosen(request, conversation, trial, word, winner)
    conversation.adjustments = trial
    _record_refinement(request, critique, blueprint)
    return _recommendation(request, conversation, blueprint, done)


def _different(session_id: str, adj: Adjustments, winner: dict) -> tuple[Adjustments, str]:
    """
    "Something different", read against what is actually on the table. Excluding the current
    dish's cuisine is the natural reading, but it can't work when every dish shares one (a
    search for pizza) or when the user answered a cuisine a moment ago — "different" then
    contradicts their own answer. So:
      - a cuisine was answered: a different cuisine, and the answer steps aside;
      - the dishes span several cuisines: another one;
      - they're all one cuisine: the same kind of dish from somewhere else.
    """
    from tier_2.consensus_manager import CATEGORY_NAMES, _same_dish

    evaluation, context = pool.held(session_id)
    current, _, _ = pool.candidates_under(
        evaluation.get("safe_candidates", []), evaluation.get("source_intent") or {}, context, adj
    )
    category = winner.get("category") or ""
    kind = KIND_PHRASES.get(category) or CATEGORY_NAMES.get(category) or "one kind of food"
    if adj.category:
        answered = CATEGORY_NAMES.get(adj.category, adj.category.replace("_", " "))
        trial = adj.model_copy(update={"category": None}).merged(
            {"exclude_categories": [adj.category]}
        )
        return trial, f"Here's something other than {answered}."
    if len({c.get("category") for c in current}) > 1:
        return adj.merged({"exclude_categories": [category]}), "Here's something different."
    restaurants = {c.get("restaurant_name") for c in current if c.get("restaurant_name")}
    here = winner.get("restaurant_name")
    if here and len(restaurants) > 1:
        return (
            adj.merged({"exclude_restaurants": [here]}),
            f"Everything here is {kind}, so here's one from somewhere else.",
        )
    # One restaurant: set aside the dish in every size it's sold, or "different" is just the
    # half portion of the same nihari.
    family = _same_dish(winner)
    same = [c.get("dish_id") for c in current if _same_dish(c) == family] or [winner.get("dish_id")]
    return (
        adj.merged({"exclude_dishes": same}),
        f"Everything here is {kind}, so here's another one.",
    )


def _loosen(
    request: Request, conversation: Conversation, trial: Adjustments, word: str, winner: dict
) -> dict:
    """
    A refinement found nothing. Rather than a dead end, offer to loosen one of the user's own
    earlier choices — only those that would then find a dish — and let them pick. The
    refinement they just asked for is kept; allergies, diet and halal are never offered.
    """
    from tier_2.consensus_manager import CATEGORY_NAMES
    from tier_2.scoring import _rs

    session_id = request.state.session_id
    evaluation, context = pool.held(session_id)
    found = evaluation.get("safe_candidates", [])
    intent = evaluation.get("source_intent") or {}
    before = conversation.adjustments
    defaults = Adjustments()
    # What this refinement itself changed is what the user just asked for: never offer to undo it.
    touched = {f for f in Adjustments.model_fields if getattr(trial, f) != getattr(before, f)}
    chips = {}
    for fields, label in RELAXABLE:
        if all(getattr(before, f) == getattr(defaults, f) for f in fields):
            continue  # the user never set it, so there's nothing of theirs to loosen
        if touched & set(fields):
            continue
        loosened = trial.model_copy(update={f: getattr(defaults, f) for f in fields})
        kept, _, _ = pool.candidates_under(found, intent, context, loosened)
        if not kept:
            continue
        chips[fields[0]] = {
            "label": label.format(
                category=CATEGORY_NAMES.get(before.category or "", before.category or ""),
                ceiling=_rs(before.ceiling or 0),
            ),
            "replace": loosened.model_dump(),
            "then": f"here's something {word}.",
            "adjust": {},
        }
    if not chips:
        reply = (
            f"Nothing {word} is left in what you asked for, so I've kept {winner['name']}. "
            "A new search is the way to widen it."
        )
        return _recommendation(request, conversation, _current_enriched(session_id), reply)
    question = Question(
        slot=RELAX,
        text="Can I loosen one thing?",
        why=(
            f"Nothing {word} fits everything you asked. "
            "Your allergies and diet stay exactly as they are."
        ),
        chips=chips,
    )
    return _ask(request, conversation, question, reply=None, skip_label=KEEP_LABEL)


# ── Replies ──────────────────────────────────────────────────────────────────
def _next(request: Request, conversation: Conversation, blueprint: dict, reply: str | None) -> dict:
    """Asks the most useful question, or recommends when none is worth asking."""
    session_id = request.state.session_id
    evaluation, context = pool.held(session_id)
    question = questions.best_question(
        evaluation.get("safe_candidates", []),
        evaluation.get("source_intent") or {},
        context,
        conversation,
    )
    if question is None:
        conversation.closed = True
        return _recommendation(request, conversation, blueprint, reply)
    return _ask(request, conversation, question, reply, SKIP_LABEL, blueprint)


def _ask(
    request: Request,
    conversation: Conversation,
    question: Question,
    reply: str | None,
    skip_label: str,
    blueprint: dict | None = None,
) -> dict:
    session_id = request.state.session_id
    conversation.pending = question
    conversation.turn += 1
    state.save(session_id, conversation)
    return {
        "type": "question",
        "conversation_id": conversation.id,
        "turn": conversation.turn,
        "reply": reply,
        "question": {
            "id": question.slot,
            "text": question.text,
            "why": question.why,
            "chips": [{"value": v, "label": c["label"]} for v, c in question.chips.items()],
            "skip_label": skip_label,
        },
        "leading": ((blueprint or {}).get("winning_dish") or {}).get("name"),
    }


def _recommendation(
    request: Request, conversation: Conversation, blueprint: dict, reply: str | None
) -> dict:
    session_id = request.state.session_id
    conversation.pending = None
    conversation.turn += 1
    state.save(session_id, conversation)
    return {
        "type": "recommendation",
        "conversation_id": conversation.id,
        "turn": conversation.turn,
        "reply": reply,
        "recommendation": blueprint,
        "refinements": [{"value": k, "label": v} for k, v in critiques.CRITIQUES.items()],
        "suggestions": distill.suggestions(request, session_id, conversation),
    }


# ── Helpers ──────────────────────────────────────────────────────────────────
def _current(session_id: str) -> dict | None:
    """The session's current blueprint, if it has a winner."""
    from tier_1.contracts.session_store import load_contract

    blueprint = load_contract(session_id, "decision_blueprint")
    if blueprint is None:
        return None
    blueprint = blueprint.model_dump() if hasattr(blueprint, "model_dump") else blueprint
    return blueprint if blueprint.get("winning_dish") else None


def _current_enriched(session_id: str) -> dict:
    from tier_3.fulfillment_engine import enrich_blueprint

    blueprint = enrich_blueprint(_current(session_id) or {})
    blueprint.pop("all_candidate_scores", None)
    return blueprint


def _record_refinement(request: Request, critique: str, blueprint: dict) -> None:
    from accounts import events
    from accounts.deps import current_user_id

    try:
        user_id = current_user_id(request)
    except Exception:  # kept as a guest event, claimed at the next sign-in
        user_id = None
    session_id = request.state.session_id
    dish = blueprint.get("winning_dish") or {}
    events.record(session_id, user_id, events.refined_event(session_id, critique, dish))

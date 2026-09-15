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
from dialogue.state import Conversation

log = logging.getLogger(__name__)

SKIP_LABEL = "Just pick for me"


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
    change = critiques.adjustment(critique, winner, current.get("utility_breakdown") or {})
    if change is None:
        reply = critiques.missing(critique, winner)
        return _recommendation(request, conversation, _current_enriched(session_id), reply)
    trial = conversation.adjustments.merged(change)
    blueprint = pool.rerank(session_id, trial)
    word = critiques.WORDS[critique]
    if blueprint is None:
        reply = f"Nothing {word} fits everything you asked, so I've kept {winner['name']}."
        return _recommendation(request, conversation, _current_enriched(session_id), reply)
    conversation.adjustments = trial
    _record_refinement(request, critique, blueprint)
    return _recommendation(request, conversation, blueprint, f"Here's something {word}.")


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
            "skip_label": SKIP_LABEL,
        },
        "leading": (blueprint.get("winning_dish") or {}).get("name"),
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

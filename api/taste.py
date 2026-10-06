"""
GET/POST /taste/start: six dishes, tap the ones you'd eat (accounts/taste_start.py).

Until this, the taste term sat out every guest's first request — there was nothing to judge
flavour against, and scoring against a persona's invented profile was noise dressed as
knowledge. Fifteen seconds of tapping is real evidence, so the term can switch on honestly.

Signed in, the picks start the saved taste model. As a guest they are kept with the session,
the same way a guest's location and history already are, and folded into the scoring context
on the next request. Either way they are a starting point, not a verdict: approvals keep
moving it, and anything the user set by hand is left alone.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from accounts import store, taste_start
from accounts.deps import current_user_id
from accounts.models import TasteModel
from tier_1.contracts.session_store import load_contract, save_contract
from tier_1.symbolic_anchoring import representative_image

log = logging.getLogger(__name__)
router = APIRouter(prefix="/taste", tags=["taste"])

CONTRACT = "taste_start"  # where a guest's picks live


class Picks(BaseModel):
    dish_ids: list[str] = Field(min_length=taste_start.LEAST, max_length=taste_start.SHOWN)


def _card(dish: dict) -> dict:
    """A dish to tap: what it is and where it's from. Never its flavour, which is the question."""
    return {
        "dish_id": dish["dish_id"],
        "name": dish["name"],
        "restaurant_name": dish.get("restaurant_name"),
        "restaurant_area": dish.get("restaurant_area"),
        "category": dish.get("category"),
        # No dish in the collection has a photograph of its own, so this is the stock image of
        # the kind of dish, and the card says so — the same rule the Pick screen follows.
        "image_url": representative_image(dish["name"], dish.get("category") or ""),
        "is_rep_image": True,
    }


def _known(request: Request, user_id: Optional[str]) -> bool:
    """Whether this person's taste already has something behind it."""
    if user_id:
        profile = store.get_profile(user_id)
        return bool(profile and profile.taste.has_evidence())
    return bool(load_contract(request.state.session_id, CONTRACT))


@router.get("/start")
def start(request: Request):
    """The six dishes to ask about, and whether we need to ask at all."""
    user_id = current_user_id(request)
    dishes = taste_start.offered()
    if not dishes:
        raise HTTPException(503, "The dishes couldn't be loaded. Please try again.")
    return {
        "known": _known(request, user_id),
        "least": taste_start.LEAST,
        "dishes": [_card(d) for d in dishes],
    }


@router.post("/start")
def pick(request: Request, picks: Picks):
    """What the taps say about this person's taste, saved and said back to them."""
    user_id = current_user_id(request)
    dishes = taste_start.offered()
    wanted = set(picks.dish_ids)
    picked = [d for d in dishes if d["dish_id"] in wanted]
    if len(picked) < taste_start.LEAST:
        raise HTTPException(400, f"Tap at least {taste_start.LEAST} of the dishes shown.")

    told = taste_start.fold(picked, dishes)
    said = taste_start.in_words(told)
    kept = {
        "vector": told["vector"],
        "confidence": told["confidence"],
        "importance": taste_start.weighting(told),
        "said": said,
        "dish_ids": [d["dish_id"] for d in picked],
    }

    if user_id:
        profile = store.get_profile(user_id)
        taste = profile.taste if profile else TasteModel.from_persona("balanced")
        store.set_taste(user_id, taste_start.started(taste, told))
    else:
        save_contract(request.state.session_id, CONTRACT, kept)
    return {"said": said, "taste": kept["vector"], "importance": kept["importance"]}

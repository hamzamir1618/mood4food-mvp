"""
The signed-in user's profile, history and data rights (Phase 2). See docs/ACCOUNTS.md.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from accounts import learning, store, taste_index
from accounts.deps import require_user
from accounts.models import (
    DietaryProfile,
    GoalProfile,
    PasswordConfirmation,
    Profile,
    TasteEdit,
    TasteModel,
    TasteReset,
    WeightsEdit,
)
from accounts.security import clear_auth_cookie, verify_password
from api.rate_limit import limiter

log = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["accounts"])


def _profile(user_id: str) -> Profile:
    profile = store.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return profile


def _save_taste(user_id: str, taste: TasteModel) -> None:
    store.set_taste(user_id, taste)
    try:
        taste_index.sync(user_id, taste)
    except Exception as exc:  # the index is derived; the next startup rebuild repairs it
        log.warning("similar-tastes index not updated for a user: %s", exc)


@router.get("")
def read_profile(user_id: str = Depends(require_user)):
    return _profile(user_id).model_dump()


@router.put("/dietary")
def update_dietary(body: DietaryProfile, user_id: str = Depends(require_user)):
    """Allergies, diet and halal. Applied to every query while signed in."""
    store.set_dietary(user_id, body)
    return _profile(user_id).model_dump()


@router.put("/goals")
def update_goals(body: GoalProfile, user_id: str = Depends(require_user)):
    store.set_goals(user_id, body)
    return _profile(user_id).model_dump()


@router.put("/taste")
def edit_taste(body: TasteEdit, user_id: str = Depends(require_user)):
    """Sets taste dimensions by hand. A value the user sets has full confidence."""
    taste = _profile(user_id).taste
    updated = taste.model_copy(
        update={
            "vector": {**taste.vector, **body.values},
            "confidence": {**taste.confidence, **{d: 1.0 for d in body.values}},
        }
    )
    _save_taste(user_id, updated)
    return _profile(user_id).model_dump()


@router.post("/taste/reset")
def reset_taste(body: TasteReset, user_id: str = Depends(require_user)):
    """Forgets everything learned or set by hand and starts again from a persona."""
    persona = body.persona or _profile(user_id).taste.persona_prior
    _save_taste(user_id, TasteModel.from_persona(persona))
    return _profile(user_id).model_dump()


@router.put("/weights")
def set_weights(body: WeightsEdit, user_id: str = Depends(require_user)):
    """Sets how much health, budget and taste count. Approvals keep refining them."""
    taste = _profile(user_id).taste
    _save_taste(user_id, taste.model_copy(update={"agent_weights": body.as_weights()}))
    return _profile(user_id).model_dump()


@router.get("/learning")
def what_i_learned(user_id: str = Depends(require_user)):
    """What approvals have taught the preference model, in plain sentences."""
    return learning.learning_summary(_profile(user_id).taste)


@router.get("/history")
def history(limit: int = Query(50, ge=1, le=500), user_id: str = Depends(require_user)):
    return {"events": [e.model_dump() for e in store.list_events(user_id, limit)]}


@router.get("/similar-tastes")
def similar_tastes(k: int = Query(5, ge=1, le=20), user_id: str = Depends(require_user)):
    """
    How closely other users' tastes match yours, by cosine similarity. Anonymous: no
    other user is identified.
    """
    taste = _profile(user_id).taste
    if not taste.has_evidence():
        return {
            "matches": [],
            "note": "Set your taste first; the persona you picked isn't your taste yet.",
        }
    try:
        matches = taste_index.similar(user_id, taste.as_list(), k)
    except Exception as exc:
        log.error("similar-tastes index failed: %s", exc)
        raise HTTPException(status_code=503, detail="The similar-tastes index is unavailable.")
    return {"matches": [{"similarity": m["similarity"]} for m in matches]}


@router.get("/export")
def export(user_id: str = Depends(require_user)):
    """Everything stored about you, as a JSON download."""
    return JSONResponse(
        store.export_user(user_id),
        headers={"Content-Disposition": 'attachment; filename="mood4food-my-data.json"'},
    )


@router.post("/delete")
@limiter.limit("5/minute")
def delete_account(
    request: Request,
    response: Response,
    body: PasswordConfirmation,
    user_id: str = Depends(require_user),
):
    """Deletes the account, profile and history for good. Needs the password."""
    user = store.get_user(user_id)
    if not user or not verify_password(user["password_hash"], body.password):
        raise HTTPException(status_code=401, detail="Wrong password.")
    store.delete_user(user_id)
    try:
        taste_index.remove(user_id)
    except Exception as exc:
        log.warning("similar-tastes entry not removed for a deleted user: %s", exc)
    clear_auth_cookie(response)
    return {"deleted": True}

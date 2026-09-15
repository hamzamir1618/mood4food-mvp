"""
Registration and sign-in (Phase 2). Passwords are hashed with Argon2id; the session is a
signed token in an httpOnly cookie. See docs/ACCOUNTS.md.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Response

from accounts import events, learning, store
from accounts.deps import current_user_id
from accounts.models import Credentials, Registration
from accounts.security import (
    clear_auth_cookie,
    hash_password,
    issue_token,
    needs_rehash,
    set_auth_cookie,
    verify_password_or_dummy,
)
from api.rate_limit import limiter

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["accounts"])


def _sign_in(request: Request, response: Response, user: dict) -> dict:
    set_auth_cookie(response, issue_token(user["user_id"], user.get("token_version", 0)))
    claimed = []
    try:
        claimed = events.claim_guest_events(request.state.session_id, user["user_id"])
    except Exception as exc:
        log.warning("guest history not moved to the account: %s", exc)
    try:
        learning.replay(user["user_id"], claimed)  # a guest's approvals teach the new model
    except Exception as exc:
        log.warning("guest approvals not learned from: %s", exc)
    return {"user": store.public(user).model_dump(), "guest_events_claimed": len(claimed)}


@router.post("/register", status_code=201)
@limiter.limit("5/hour")
def register(request: Request, response: Response, body: Registration):
    if not store.has_room_for_another_user():
        raise HTTPException(
            status_code=503,
            detail="New accounts are paused: the database is close to its free-tier size limit.",
        )
    try:
        user = store.create_user(
            body.email, body.display_name.strip(), hash_password(body.password), body.persona
        )
    except store.EmailTaken:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return _sign_in(request, response, user)


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, response: Response, body: Credentials):
    user = store.get_user_by_email(body.email)
    if not verify_password_or_dummy(user["password_hash"] if user else None, body.password):
        raise HTTPException(status_code=401, detail="Wrong email or password.")
    if needs_rehash(user["password_hash"]):
        store.set_password_hash(user["user_id"], hash_password(body.password))
    return _sign_in(request, response, user)


@router.post("/logout")
def logout(request: Request, response: Response, everywhere: bool = False):
    """Signs this browser out. With everywhere=true, every other device is signed out too."""
    user_id = current_user_id(request)
    if everywhere and user_id:
        store.bump_token_version(user_id)
    clear_auth_cookie(response)
    return {"signed_out": True}


@router.get("/me")
def me(request: Request):
    """The signed-in user, or {"user": null} for a guest."""
    user_id = current_user_id(request)
    user = store.get_user(user_id) if user_id else None
    return {"user": store.public(user).model_dump() if user else None}

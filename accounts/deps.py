"""Who is making a request: the signed-in user's id, or None for a guest."""

from fastapi import HTTPException, Request

from accounts import store
from accounts.security import COOKIE_NAME, read_token


def current_user_id(request: Request) -> str | None:
    """
    The signed-in user's id, or None for a guest. A token that is expired, tampered with,
    or older than the user's last "sign out everywhere" counts as no token.

    Database errors propagate: a caller that needs the user's saved constraints must not
    carry on as if the user were a guest.
    """
    if hasattr(request.state, "user_id"):
        return request.state.user_id
    user_id = None
    token = request.cookies.get(COOKIE_NAME)
    parsed = read_token(token) if token else None
    if parsed:
        candidate, version = parsed
        user = store.get_user(candidate)
        if user and user.get("token_version", 0) == version:
            user_id = candidate
    request.state.user_id = user_id
    return user_id


def require_user(request: Request) -> str:
    user_id = current_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Sign in to use this.")
    return user_id

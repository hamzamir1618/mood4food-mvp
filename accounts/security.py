"""
Password hashing and sign-in tokens.

Passwords are hashed with Argon2id at OWASP's recommended minimum (19 MiB, 2 passes,
1 lane) rather than argon2-cffi's default of 64 MiB, so a burst of sign-ins cannot
exhaust a 512 MB free-tier instance. Hashes record their own parameters, so raising
them later only needs needs_rehash() at the next sign-in.

The session is a signed JWT in an httpOnly cookie. It carries the user's token version,
which "sign out everywhere" increments, so every older token stops working.
"""

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from config import settings

COOKIE_NAME = "m4f_auth"
ALGORITHM = "HS256"

_hasher = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1)
_dummy_hash: str | None = None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_password_or_dummy(stored_hash: str | None, password: str) -> bool:
    """
    Checks a password. With no account (stored_hash None) it still does the work of one
    check, so the response time doesn't reveal which emails are registered.
    """
    global _dummy_hash
    if stored_hash is None:
        if _dummy_hash is None:
            _dummy_hash = _hasher.hash("no-account-placeholder")
        verify_password(_dummy_hash, password)
        return False
    return verify_password(stored_hash, password)


def needs_rehash(stored_hash: str) -> bool:
    return _hasher.check_needs_rehash(stored_hash)


def issue_token(user_id: str, token_version: int, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(days=settings.AUTH_TOKEN_DAYS),
    }
    return jwt.encode(claims, settings.AUTH_SECRET, algorithm=ALGORITHM)


def read_token(token: str) -> tuple[str, int] | None:
    """(user_id, token_version) from a valid token; None if expired, tampered with or malformed."""
    try:
        claims = jwt.decode(
            token,
            settings.AUTH_SECRET,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "ver", "exp"]},
        )
        return str(claims["sub"]), int(claims["ver"])
    except (jwt.PyJWTError, TypeError, ValueError):
        return None


def set_auth_cookie(response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.AUTH_TOKEN_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response) -> None:
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax",
    )

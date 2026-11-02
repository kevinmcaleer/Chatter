"""Sliding login sessions.

A login token lasts ACCESS_TOKEN_EXPIRE_MINUTES (7 days by default). So that
people who use the site regularly are never logged out mid-session, any
request that arrives with a valid ``access_token`` cookie that is past half
its life gets a fresh token (and fresh cookies) on the response. Someone is
only logged out after a full token lifetime without visiting.

Only the cookie is renewed: Authorization-header callers manage their own
tokens. Responses that already set or clear the auth cookies (login,
logout) are left alone.
"""

from __future__ import annotations

import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .utils import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ACCESS_TOKEN_MAX_AGE_SECONDS,
    create_access_token,
    decode_access_token,
)


def _cookie_domain():
    return ".kevsrobots.com" if os.getenv("ENVIRONMENT", "development") == "production" else None


def token_needs_renewal(payload: dict, now: float | None = None) -> bool:
    """True when a decoded token has used up at least half its lifetime."""
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return False
    remaining = exp - (time.time() if now is None else now)
    return 0 < remaining < (ACCESS_TOKEN_EXPIRE_MINUTES * 60) / 2


def _sets_auth_cookie(response) -> bool:
    for name, value in response.raw_headers:
        if name.lower() == b"set-cookie" and (
            value.startswith(b"access_token=") or value.startswith(b"username=")
        ):
            return True
    return False


class SlidingSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        cookie = request.cookies.get("access_token")
        if not cookie or not cookie.startswith("Bearer "):
            return response
        if response.status_code == 401 or _sets_auth_cookie(response):
            return response

        payload = decode_access_token(cookie[7:])
        if not payload or not payload.get("sub") or not token_needs_renewal(payload):
            return response

        token = create_access_token({"sub": payload["sub"]})
        secure = os.getenv("ENVIRONMENT", "development") == "production"
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            secure=secure,
            max_age=ACCESS_TOKEN_MAX_AGE_SECONDS,
            samesite="lax",
            domain=_cookie_domain(),
        )
        response.set_cookie(
            key="username",
            value=payload["sub"],
            httponly=False,
            secure=secure,
            max_age=ACCESS_TOKEN_MAX_AGE_SECONDS,
            samesite="lax",
            domain=_cookie_domain(),
        )
        return response

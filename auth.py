from __future__ import annotations

import os
from collections import defaultdict
from contextvars import ContextVar
from threading import Lock
from time import time

import httpx
from joserfc import jwt as jose_jwt
from joserfc.jwk import KeySet
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Per-request identity, set by AuthMiddleware, read by fetch_document
current_identity: ContextVar[str] = ContextVar("current_identity", default="")

# In-process rate limit store: {identity: [timestamp, ...]}
_rate_store: dict[str, list[float]] = defaultdict(list)
_rate_lock = Lock()

# JWKS key set (fetched once at first use, cached in memory)
_key_set: KeySet | None = None
_key_set_lock = Lock()


def _get_key_set() -> KeySet:
    global _key_set
    if _key_set is None:
        with _key_set_lock:
            if _key_set is None:
                jwks_uri = os.environ["WORKOS_JWKS_URI"]
                response = httpx.get(jwks_uri, timeout=10.0)
                response.raise_for_status()
                _key_set = KeySet.import_key_set(response.json())
    return _key_set


def validate_token(token: str) -> dict:
    """Validate a WorkOS AuthKit Bearer JWT. Raises on any failure."""
    key_set = _get_key_set()
    decoded = jose_jwt.decode(token, key_set)

    audience = os.environ.get("WORKOS_AUDIENCE")
    issuer = os.environ.get("WORKOS_ISSUER")

    claims_requests: dict = {"exp": {"essential": True}}
    if audience:
        claims_requests["aud"] = {"essential": True, "value": audience}
    if issuer:
        claims_requests["iss"] = {"essential": True, "value": issuer}

    registry = jose_jwt.JWTClaimsRegistry(**claims_requests)
    registry.validate(decoded.claims)

    return decoded.claims


def check_rate_limit(identity: str) -> bool:
    """Return True if the identity is within its rate limit, False if exceeded.

    Fixed window: counts requests within the last RATELIMIT_WINDOW_SECONDS seconds.
    """
    max_requests = int(os.environ.get("RATELIMIT_REQUESTS", "10"))
    window = int(os.environ.get("RATELIMIT_WINDOW_SECONDS", "3600"))
    now = time()
    cutoff = now - window

    with _rate_lock:
        timestamps = _rate_store[identity]
        timestamps[:] = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= max_requests:
            return False
        timestamps.append(now)
        return True


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate WorkOS AuthKit Bearer JWT on every request.

    Sets current_identity ContextVar to the token's `sub` claim.
    Returns 401 for missing/invalid tokens.
    """

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Unauthorized", "detail": "Bearer token required"},
                status_code=401,
            )

        token = auth_header[7:]
        try:
            payload = validate_token(token)
        except Exception:
            return JSONResponse(
                {"error": "Unauthorized", "detail": "Invalid or expired token"},
                status_code=401,
            )

        identity = payload.get("sub", "")
        token_var = current_identity.set(identity)
        try:
            response = await call_next(request)
        finally:
            current_identity.reset(token_var)

        return response

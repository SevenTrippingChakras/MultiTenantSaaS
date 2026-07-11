"""Per-IP rate limiting (in-memory, via SlowAPI).

Pattern: `SlowAPIMiddleware` enforces `default_rate_limit` on every route; hot
endpoints override it with `@limiter.limit(...)` decorators (/auth for brute
force, /chat for LLM cost / DoS). All limits come from config (see auth_limit /
chat_limit below), so they are tunable per environment without a code change.

In-memory storage is single-process only; when Redis lands (see architecture.md)
this becomes a one-line `storage_uri="redis://..."` swap so limits hold across
workers/replicas — the middleware and decorators stay identical.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import settings
from app.core.errors import error_response

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.default_rate_limit],
    enabled=settings.rate_limit_enabled,
)


# Passed to `@limiter.limit(...)` as callables so the limit is read from config
# per request (tunable without a redeploy), not frozen at import time.
def auth_limit(*args: object) -> str:
    return settings.auth_rate_limit


def chat_limit(*args: object) -> str:
    return settings.chat_rate_limit


def register_rate_limiting(app: FastAPI) -> None:
    """Install the limiter, its middleware, and a 429 handler using our envelope."""
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return error_response(429, "rate_limited", "Too many requests, slow down.")

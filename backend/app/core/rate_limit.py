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
    storage_uri=settings.redis_uri,
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

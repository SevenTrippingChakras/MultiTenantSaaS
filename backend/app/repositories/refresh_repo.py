"""Server-side refresh-token store (Redis).

Each login starts a token *family* (a session). We keep only the currently
active jti per family; rotating on refresh overwrites it. A refresh token whose
jti no longer matches its family's active jti is a replay, and the service
revokes the whole family. A per-user set indexes a user's families so we can
log out everywhere.
"""

from collections.abc import Awaitable
from typing import cast

from app.config import settings
from app.redis_client import get_redis

_FAMILY_PREFIX = "refresh:family:"
_USER_PREFIX = "refresh:user:"


def _family_key(family_id: str) -> str:
    return f"{_FAMILY_PREFIX}{family_id}"


def _user_key(user_id: str) -> str:
    return f"{_USER_PREFIX}{user_id}"


def _ttl_seconds() -> int:
    return settings.refresh_token_expire_days * 24 * 60 * 60


async def set_active_jti(user_id: str, family_id: str, jti: str) -> None:
    """Record the family's active jti (new login or rotation) and index it under
    the user, refreshing both TTLs."""
    r = get_redis()
    ttl = _ttl_seconds()
    await r.set(_family_key(family_id), jti, ex=ttl)
    # redis 5.x async stubs type set-ops as `Awaitable[int] | int`; cast to the
    # awaitable half so the await type-checks (values are awaited at runtime).
    await cast("Awaitable[int]", r.sadd(_user_key(user_id), family_id))
    await r.expire(_user_key(user_id), ttl)


async def get_active_jti(family_id: str) -> str | None:
    """Return the family's current active jti, or None if unknown/revoked."""
    # decode_responses=True, so values come back as str (stubs say bytes|str).
    return cast("str | None", await get_redis().get(_family_key(family_id)))


async def revoke_family(user_id: str, family_id: str) -> None:
    """Revoke a single session (logout, or reuse detection)."""
    r = get_redis()
    await r.delete(_family_key(family_id))
    await cast("Awaitable[int]", r.srem(_user_key(user_id), family_id))


async def revoke_all(user_id: str) -> None:
    """Revoke every session for a user (log out everywhere)."""
    r = get_redis()
    families = await cast("Awaitable[set[str]]", r.smembers(_user_key(user_id)))
    keys = [_family_key(f) for f in families]
    if keys:
        await r.delete(*keys)
    await r.delete(_user_key(user_id))

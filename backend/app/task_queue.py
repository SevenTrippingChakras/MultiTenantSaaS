"""ARQ task-queue connection for the API process (the enqueue side).

The API enqueues jobs; a separate worker process (`app/worker.py`) consumes them.
Both talk to the same Redis. This module owns the API's ARQ pool the same way
`redis_client` owns the plain Redis client: connect in the app lifespan, close on
shutdown, and hand callers the live pool via `get_pool()`.

Kept separate from `redis_client` because ARQ needs its own `RedisSettings`/pool
type (`ArqRedis`) rather than the plain client used for counters and pub/sub.
"""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings

_pool: ArqRedis | None = None


def redis_settings() -> RedisSettings:
    """ARQ Redis connection settings, derived from the shared `redis_uri`."""
    return RedisSettings.from_dsn(settings.redis_uri)


def get_pool() -> ArqRedis:
    """Return the active ARQ pool. Call connect() at startup first."""
    if _pool is None:
        raise RuntimeError("Task queue not initialized. Call connect() on startup.")
    return _pool


async def connect() -> None:
    """Open the ARQ pool used to enqueue jobs."""
    global _pool
    _pool = await create_pool(redis_settings())


async def close() -> None:
    """Close the ARQ pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None

from redis.asyncio import Redis

from app.config import settings

_client: Redis | None = None


def get_redis() -> Redis:
    """Return the active Redis client. Call connect() at startup first."""
    if _client is None:
        raise RuntimeError("Redis not initialized. Call connect() on startup.")
    return _client


async def connect() -> None:
    """Open the client and verify the connection with a ping."""
    global _client
    _client = Redis.from_url(settings.redis_uri, decode_responses=True)
    await _client.ping()


async def close() -> None:
    """Close the client on shutdown."""
    if _client is not None:
        await _client.aclose()

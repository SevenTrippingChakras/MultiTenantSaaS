"""Cross-worker stop signal for in-flight chat streams (Redis pub/sub).

A stream may run on a different worker than the one that receives the stop
request, so the signal travels through Redis. The stop endpoint publishes to a
channel keyed by session + generation id; the streaming worker holds a
subscriber that flips an asyncio.Event, which unwinds its stream (closing the
upstream OpenAI call). The channel is scoped by session so owning the session is
what authorises the stop.
"""

import asyncio

from app.redis_client import get_redis

_PREFIX = "chat:stop:"


def _channel(session_id: str, generation_id: str) -> str:
    return f"{_PREFIX}{session_id}:{generation_id}"


async def publish_stop(session_id: str, generation_id: str) -> int:
    """Ask any worker streaming this generation to stop. Returns the number of
    subscribers reached (0 means no active stream on any worker)."""
    return await get_redis().publish(_channel(session_id, generation_id), "stop")


async def watch_for_stop(
    session_id: str, generation_id: str, stop: asyncio.Event
) -> None:
    """Set `stop` when a stop message for this generation arrives.

    Runs as a background task for the life of one stream; cancelling it (when the
    stream ends normally) unsubscribes via the `finally`.
    """
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(_channel(session_id, generation_id))
    try:
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                stop.set()
                return
    finally:
        await pubsub.aclose()

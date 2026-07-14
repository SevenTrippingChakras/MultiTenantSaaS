"""Phase 8 cross-worker stop signal (Redis pub/sub).

Runs against the local Redis only (no Atlas), so it exercises the real
subscribe/publish path offline.
"""

import asyncio
import uuid

import pytest_asyncio

from app import redis_client
from app.repositories import stop_signal


@pytest_asyncio.fixture
async def redis_conn():
    await redis_client.connect()
    yield
    await redis_client.close()


async def test_publish_flips_the_watcher_event(redis_conn):
    session_id = f"s-{uuid.uuid4()}"
    gen_id = uuid.uuid4().hex
    stop = asyncio.Event()
    watcher = asyncio.ensure_future(
        stop_signal.watch_for_stop(session_id, gen_id, stop)
    )

    # Retry publishing until the subscription is live (>=1 receiver).
    receivers = 0
    for _ in range(50):
        receivers = await stop_signal.publish_stop(session_id, gen_id)
        if receivers:
            break
        await asyncio.sleep(0.02)

    assert receivers == 1
    await asyncio.wait_for(stop.wait(), timeout=1)
    assert stop.is_set()
    await watcher  # watcher returns after setting the event and unsubscribing


async def test_publish_with_no_listener_returns_zero(redis_conn):
    receivers = await stop_signal.publish_stop(f"s-{uuid.uuid4()}", uuid.uuid4().hex)
    assert receivers == 0

"""Metering emit: the durable event write plus the best-effort Redis counters.

Uses real Redis (via the `client` fixture) for the counters and the test DB for
the `usage_events` write. No ARQ: the durable path is a Mongo write, not a queue.
"""

from uuid import uuid4

from app import db
from app.services import metering


async def test_store_event_persists_unaggregated(client):
    tid, uid, sid = uuid4().hex, uuid4().hex, uuid4().hex
    event = metering.build_event(tid, uid, sid, "gpt-4o-mini", 1000, 500)
    await metering.store_event(event)

    stored = await db.get_db().usage_events.find_one({"tenant_id": tid})
    assert stored["total_tokens"] == 1500
    assert stored["cost_usd"] > 0
    assert stored["aggregated"] is False


async def test_bump_counters_accumulates_per_scope(client):
    tid, uid, sid = uuid4().hex, uuid4().hex, uuid4().hex
    await metering.bump_counters(
        metering.build_event(tid, uid, sid, "gpt-4o-mini", 1000, 500)
    )
    await metering.bump_counters(
        metering.build_event(tid, uid, sid, "gpt-4o-mini", 200, 100)
    )

    # Counters accumulate across calls, per user and per tenant.
    user = await metering.read_counter("user", uid)
    tenant = await metering.read_counter("tenant", tid)
    assert user["total_tokens"] == 1800
    assert tenant["total_tokens"] == 1800
    assert user["cost_usd"] > 0

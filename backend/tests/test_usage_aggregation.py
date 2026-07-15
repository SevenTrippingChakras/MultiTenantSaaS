"""Metering worker jobs (Phase 10): raw events roll up into usage_daily.

Calls the ARQ job functions directly (no worker process) against the test DB.
"""

from uuid import uuid4

from app import db
from app.jobs.usage import aggregate_usage, store_usage_event


def _event(tid, uid, pt, ct, ts):
    return {
        "tenant_id": tid,
        "user_id": uid,
        "session_id": "S1",
        "model": "gpt-4o-mini",
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": pt + ct,
        "cost_usd": 0.001,
        "ts": ts,
    }


async def test_aggregate_rolls_events_into_daily(client):
    tid, uid = uuid4().hex, uuid4().hex
    # Two events same day -> one summary; a third on the next day -> another.
    await store_usage_event({}, _event(tid, uid, 100, 50, "2026-07-15T10:00:00+00:00"))
    await store_usage_event({}, _event(tid, uid, 200, 80, "2026-07-15T18:00:00+00:00"))
    await store_usage_event({}, _event(tid, uid, 10, 5, "2026-07-16T09:00:00+00:00"))

    result = await aggregate_usage({})
    assert result == {"events": 3, "summaries": 2}

    d = db.get_db()
    day1 = await d.usage_daily.find_one({"tenant_id": tid, "date": "2026-07-15"})
    assert day1["total_tokens"] == 430  # 150 + 280
    day2 = await d.usage_daily.find_one({"tenant_id": tid, "date": "2026-07-16"})
    assert day2["total_tokens"] == 15


async def test_aggregate_is_idempotent(client):
    tid, uid = uuid4().hex, uuid4().hex
    await store_usage_event({}, _event(tid, uid, 100, 50, "2026-07-15T10:00:00+00:00"))
    await aggregate_usage({})

    # A second pass finds nothing new (events already marked aggregated) and does
    # not double-count the summary.
    assert await aggregate_usage({}) == {"events": 0, "summaries": 0}
    row = await db.get_db().usage_daily.find_one({"tenant_id": tid})
    assert row["total_tokens"] == 150

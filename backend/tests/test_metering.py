"""Metering emit (Phase 10): Redis counters increment and the raw event enqueues.

Uses real Redis (via the `client` fixture's connections) for the counters and a
stubbed ARQ pool to capture the enqueued event without needing a live worker.
"""

from uuid import uuid4

from app import task_queue
from app.services import metering


class _FakePool:
    def __init__(self):
        self.jobs = []

    async def enqueue_job(self, name, *args, **kwargs):
        self.jobs.append((name, args))


async def test_record_usage_increments_counters_and_enqueues(client, monkeypatch):
    pool = _FakePool()
    monkeypatch.setattr(task_queue, "get_pool", lambda: pool)

    tid, uid, sid = uuid4().hex, uuid4().hex, uuid4().hex
    await metering.record_usage(tid, uid, sid, "gpt-4o-mini", 1000, 500)
    await metering.record_usage(tid, uid, sid, "gpt-4o-mini", 200, 100)

    # Counters accumulate across calls, per user and per tenant.
    user = await metering.read_counter("user", uid)
    tenant = await metering.read_counter("tenant", tid)
    assert user["total_tokens"] == 1800
    assert tenant["total_tokens"] == 1800
    assert user["cost_usd"] > 0

    # One raw event enqueued per call, addressed to the worker job.
    assert [name for name, _ in pool.jobs] == ["store_usage_event", "store_usage_event"]
    first_event = pool.jobs[0][1][0]
    assert first_event["tenant_id"] == tid
    assert first_event["total_tokens"] == 1500
    assert first_event["cost_usd"] > 0

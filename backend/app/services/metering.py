"""Metering emit — usage tracking on the request path (arch B2).

Durability lives in Mongo, not Redis. Each LLM call produces a raw **usage
event** that is written to the `usage_events` collection in the same transaction
as the assistant reply (see `chat_service.stream`), marked `aggregated: false`.
That transactional-outbox write is the source of truth a later bill enforces on;
the periodic `aggregate_usage` job rolls unaggregated events into `usage_daily`
summaries off the hot path (see `app/jobs/usage.py`).

The **Redis month-to-date counters** are a best-effort cache of that same data,
bumped after the durable write commits. A quota check or dashboard reads them for
a real-time balance; if they drift or are lost they are rebuildable by summing
this month's `usage_daily`.

Cost is derived here (per-model pricing) and stored on the event so history stays
accurate when prices change.
"""

from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import cast

from motor.motor_asyncio import AsyncIOMotorClientSession

from app import db, pricing
from app.redis_client import get_redis

# Counters live a little past the month so the current balance is always present
# but stale months self-expire (history lives in `usage_daily`).
_COUNTER_TTL_SECONDS = 40 * 24 * 60 * 60


def period_key(now: datetime | None = None) -> str:
    """Current billing period as YYYYMM (UTC)."""
    return (now or datetime.now(UTC)).strftime("%Y%m")


def _counter_key(scope: str, scope_id: str, period: str) -> str:
    return f"usage:{scope}:{scope_id}:{period}"


async def _incr_counter(key: str, total_tokens: int, cost_usd: float) -> None:
    """Increment one month counter hash (tokens + cost) and refresh its TTL."""
    r = get_redis()
    await cast("Awaitable[int]", r.hincrby(key, "total_tokens", total_tokens))
    await cast("Awaitable[float]", r.hincrbyfloat(key, "cost_usd", cost_usd))
    await r.expire(key, _COUNTER_TTL_SECONDS)


async def read_counter(scope: str, scope_id: str, period: str | None = None) -> dict:
    """Read a month counter hash (tokens + cost) for a tenant or user."""
    r = get_redis()
    key = _counter_key(scope, scope_id, period or period_key())
    data = await cast("Awaitable[dict]", r.hgetall(key))
    return {
        "total_tokens": int(data.get("total_tokens", 0)),
        "cost_usd": float(data.get("cost_usd", 0.0)),
    }


def build_event(
    tenant_id: str,
    user_id: str,
    session_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict:
    """Build one raw usage event: cost derived, marked unaggregated."""
    total_tokens = prompt_tokens + completion_tokens
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "session_id": session_id,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": pricing.cost_usd(model, prompt_tokens, completion_tokens),
        "ts": datetime.now(UTC).isoformat(),
        "aggregated": False,
    }


async def store_event(
    event: dict, txn: AsyncIOMotorClientSession | None = None
) -> None:
    """Persist a raw usage event durably, optionally within a transaction.

    Stored on the raw `get_db()` collection (cross-tenant, `tenant_id`/`user_id`
    as strings) that `aggregate_usage` scans. Passing `txn` makes the write atomic
    with the assistant reply so a committed reply can never lose its usage event.
    """
    await db.get_db().usage_events.insert_one(event, session=txn)


async def bump_counters(event: dict) -> None:
    """Best-effort: fold one usage event into the month-to-date Redis cache.

    A cache rebuildable from `usage_daily`, so a failure here is tolerable and the
    caller keeps it off the durable path.
    """
    period = period_key()
    tokens, cost = event["total_tokens"], event["cost_usd"]
    tenant_key = _counter_key("tenant", event["tenant_id"], period)
    user_key = _counter_key("user", event["user_id"], period)
    await _incr_counter(tenant_key, tokens, cost)
    await _incr_counter(user_key, tokens, cost)

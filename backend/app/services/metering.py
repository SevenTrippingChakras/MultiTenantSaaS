"""Metering emit — the hot-path half of usage tracking (arch B2).

On every LLM call we do two cheap things and nothing slow:

1. Increment **Redis counters** for the current billing month, per tenant and
   per user. These are the real-time balance a quota check or dashboard reads
   without touching Mongo.
2. Enqueue the **raw usage event** onto the ARQ queue. A worker persists it and a
   periodic job rolls the raw events into `usage_daily` summaries off the hot
   path (see `app/jobs/usage.py`).

Cost is derived here (per-model pricing) and stored alongside tokens so history
stays accurate when prices change.
"""

from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import cast

from app import pricing, task_queue
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


async def record_usage(
    tenant_id: str,
    user_id: str,
    session_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    """Meter one LLM call: bump live counters and enqueue the raw event."""
    total_tokens = prompt_tokens + completion_tokens
    cost = pricing.cost_usd(model, prompt_tokens, completion_tokens)
    period = period_key()

    await _incr_counter(_counter_key("tenant", tenant_id, period), total_tokens, cost)
    await _incr_counter(_counter_key("user", user_id, period), total_tokens, cost)

    event = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "session_id": session_id,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost,
        "ts": datetime.now(UTC).isoformat(),
    }
    await task_queue.get_pool().enqueue_job("store_usage_event", event)

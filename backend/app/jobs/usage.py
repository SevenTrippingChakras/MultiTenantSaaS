"""Metering aggregation job — the off-hot-path half of usage tracking (arch B2).

`aggregate_usage` is a periodic cron job (run by `app/worker.py`) that rolls
unaggregated raw `usage_events` into per tenant/user/day/model rows in
`usage_daily`, then marks them aggregated. The raw events are written durably on
the request path (see `app/services/metering.py`), so this job only reads and
folds them; there is no Redis queue in the durable path. Summaries are what the
dashboard and admin views query; raw events are audit detail a later purge can
trim.

Runs cross-tenant on the raw `get_db()` collections (like the purge job);
`tenant_id`/`user_id` are stored as the strings the metering emitter sends.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from app import db

logger = logging.getLogger("aichat")

# How many raw events one aggregation pass folds in. Bounds the batch so a
# backlog is drained over several runs rather than one huge query.
AGG_BATCH = 1000

_SUM_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")


def _day(ts: str) -> str:
    """Date bucket (YYYY-MM-DD) from an ISO timestamp."""
    return ts[:10]


async def aggregate_usage(ctx: dict) -> dict:
    """Fold a batch of unaggregated raw events into `usage_daily` summaries."""
    database = db.get_db()
    events = await database.usage_events.find({"aggregated": False}).to_list(AGG_BATCH)
    if not events:
        return {"events": 0, "summaries": 0}

    # Group in memory so many events collapse into one upsert per bucket.
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for e in events:
        key = (e["tenant_id"], e["user_id"], _day(e["ts"]), e["model"])
        g = groups.setdefault(
            key,
            {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            },
        )
        for f in _SUM_FIELDS:
            g[f] += e.get(f, 0)
        g["cost_usd"] += e.get("cost_usd", 0.0)

    now = datetime.now(UTC)
    for (tenant_id, user_id, day, model), g in groups.items():
        await database.usage_daily.update_one(
            {"tenant_id": tenant_id, "user_id": user_id, "date": day, "model": model},
            {
                "$inc": {
                    "prompt_tokens": g["prompt_tokens"],
                    "completion_tokens": g["completion_tokens"],
                    "total_tokens": g["total_tokens"],
                    "cost_usd": round(g["cost_usd"], 6),
                },
                "$set": {"updated_at": now},
            },
            upsert=True,
        )

    ids = [e["_id"] for e in events]
    await database.usage_events.update_many(
        {"_id": {"$in": ids}}, {"$set": {"aggregated": True, "aggregated_at": now}}
    )
    counts = {"events": len(events), "summaries": len(groups)}
    logger.info("usage aggregation complete: %s", counts)
    return counts

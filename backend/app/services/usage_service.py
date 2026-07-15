"""Usage dashboard reads (arch B2, view #1: the user dashboard).

Serves two things without touching the raw event stream:

- **Month-to-date** balance from the live Redis counters (the current period),
  for both the user and their tenant.
- **Daily history** from the `usage_daily` summaries the worker rolls up.

Admin/all-tenant views (view #2) arrive with RBAC in a later phase; this is the
signed-in user's own usage.
"""

from app.core.pagination import clamp_limit
from app.db import get_db
from app.services import metering


def _daily_out(doc: dict) -> dict:
    """Shape a `usage_daily` row for the API (drop internal ids)."""
    return {
        "date": doc["date"],
        "model": doc["model"],
        "prompt_tokens": doc.get("prompt_tokens", 0),
        "completion_tokens": doc.get("completion_tokens", 0),
        "total_tokens": doc.get("total_tokens", 0),
        "cost_usd": round(doc.get("cost_usd", 0.0), 6),
    }


async def get_usage(tenant_id: str, user_id: str, limit: int = 30) -> dict:
    """Month-to-date counters plus recent daily summaries for one user."""
    period = metering.period_key()
    n = clamp_limit(limit)
    daily = (
        await get_db()
        .usage_daily.find({"tenant_id": tenant_id, "user_id": user_id})
        .sort("date", -1)
        .to_list(n)
    )
    return {
        "period": period,
        "month_to_date": {
            "user": await metering.read_counter("user", user_id, period),
            "tenant": await metering.read_counter("tenant", tenant_id, period),
        },
        "daily": [_daily_out(d) for d in daily],
    }

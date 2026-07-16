"""Quota enforcement — turn metering into limits on the hot path (arch B3).

Before a chat stream starts, compare the tenant's month-to-date token total
against its plan allowance. The read is a fast Redis counter (the best-effort
month cache the metering emitter bumps, rebuildable from `usage_daily`);
unlimited (Enterprise) plans skip the check entirely. At or over the allowance
raises `QuotaExceeded` (402) so no further tokens are spent.
"""

from bson import ObjectId

from app import plans
from app.core.errors import QuotaExceeded
from app.repositories import tenant_repo
from app.services import metering


async def status(tenant_id: ObjectId) -> dict:
    """The tenant's plan, allowance, month-to-date usage, and remaining tokens.

    `limit`/`remaining` are None for an unlimited plan. Shared by the hot-path
    check and the usage dashboard so both read the quota the same way.
    """
    plan = plans.get_plan(await tenant_repo.get_plan(tenant_id))
    used = (await metering.read_counter("tenant", str(tenant_id)))["total_tokens"]
    limit = plan.monthly_token_limit
    remaining = None if limit is None else max(limit - used, 0)
    return {
        "plan": plan.name,
        "monthly_token_limit": limit,
        "used_tokens": used,
        "remaining_tokens": remaining,
    }


async def check(tenant_id: ObjectId) -> None:
    """Raise `QuotaExceeded` if the tenant is at or over its monthly allowance."""
    s = await status(tenant_id)
    limit = s["monthly_token_limit"]
    if limit is not None and s["used_tokens"] >= limit:
        raise QuotaExceeded

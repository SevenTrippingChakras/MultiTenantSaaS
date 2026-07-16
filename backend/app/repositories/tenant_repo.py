from datetime import UTC, datetime

from bson import ObjectId

from app.db import get_db
from app.plans import DEFAULT_PLAN


async def create(name: str) -> ObjectId:
    """Create a tenant (the isolation/billing boundary) and return its id.

    New tenants start on the default (Free) plan; a subscription change moves
    them via `set_plan`.
    """
    doc = {"name": name, "plan": DEFAULT_PLAN, "created_at": datetime.now(UTC)}
    result = await get_db().tenants.insert_one(doc)
    return result.inserted_id


async def find_by_id(tenant_id: ObjectId) -> dict | None:
    return await get_db().tenants.find_one({"_id": tenant_id})


async def get_plan(tenant_id: ObjectId) -> str:
    """The tenant's current plan name (defaulting to Free if unset/missing)."""
    doc = await get_db().tenants.find_one({"_id": tenant_id}, {"plan": 1})
    return (doc or {}).get("plan") or DEFAULT_PLAN


async def set_plan(tenant_id: ObjectId, plan: str) -> None:
    """Move a tenant to a plan (subscription change / Stripe webhook)."""
    await get_db().tenants.update_one(
        {"_id": tenant_id},
        {"$set": {"plan": plan, "plan_updated_at": datetime.now(UTC)}},
    )


async def set_stripe_customer(tenant_id: ObjectId, customer_id: str) -> None:
    """Remember the tenant's Stripe customer so webhooks can map back to it."""
    await get_db().tenants.update_one(
        {"_id": tenant_id}, {"$set": {"stripe_customer_id": customer_id}}
    )


async def find_by_stripe_customer(customer_id: str) -> dict | None:
    """The tenant behind a Stripe customer id (subscription webhooks carry it)."""
    return await get_db().tenants.find_one({"stripe_customer_id": customer_id})

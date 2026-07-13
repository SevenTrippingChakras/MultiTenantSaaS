from datetime import UTC, datetime

from bson import ObjectId

from app.db import get_db


async def create(name: str) -> ObjectId:
    """Create a tenant (the isolation/billing boundary) and return its id."""
    doc = {"name": name, "created_at": datetime.now(UTC)}
    result = await get_db().tenants.insert_one(doc)
    return result.inserted_id


async def find_by_id(tenant_id: ObjectId) -> dict | None:
    return await get_db().tenants.find_one({"_id": tenant_id})

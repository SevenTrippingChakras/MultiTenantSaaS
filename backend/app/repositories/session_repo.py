from datetime import UTC, datetime

from bson import ObjectId
from bson.errors import InvalidId

from app.core.tenant_db import scoped


def _to_oid(value: str) -> ObjectId | None:
    """Parse a string id to ObjectId, or None if malformed."""
    try:
        return ObjectId(value)
    except InvalidId:
        return None


async def insert(tenant_id: ObjectId, user_id: ObjectId, title: str) -> dict:
    now = datetime.now(UTC)
    doc = {"user_id": user_id, "title": title, "created_at": now, "updated_at": now}
    result = await scoped(tenant_id).sessions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_by_user(tenant_id: ObjectId, user_id: ObjectId) -> list[dict]:
    cursor = (
        scoped(tenant_id).sessions.find({"user_id": user_id}).sort("updated_at", -1)
    )
    return await cursor.to_list(length=100)


async def find_by_id(tenant_id: ObjectId, session_id: str) -> dict | None:
    oid = _to_oid(session_id)
    if oid is None:
        return None
    return await scoped(tenant_id).sessions.find_one({"_id": oid})


async def delete(tenant_id: ObjectId, session_id: str) -> None:
    oid = _to_oid(session_id)
    if oid is not None:
        await scoped(tenant_id).sessions.delete_one({"_id": oid})


async def touch(tenant_id: ObjectId, session_id: ObjectId) -> None:
    """Bump updated_at so the session rises to the top of the list."""
    await scoped(tenant_id).sessions.update_one(
        {"_id": session_id}, {"$set": {"updated_at": datetime.now(UTC)}}
    )


async def set_title(tenant_id: ObjectId, session_id: ObjectId, title: str) -> None:
    await scoped(tenant_id).sessions.update_one(
        {"_id": session_id}, {"$set": {"title": title}}
    )

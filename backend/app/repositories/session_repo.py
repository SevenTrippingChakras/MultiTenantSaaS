"""Data access for the sessions collection."""

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.db import get_db


def _to_oid(value: str) -> ObjectId | None:
    """Parse a string id to ObjectId, or None if malformed."""
    try:
        return ObjectId(value)
    except InvalidId:
        return None


async def insert(user_id: ObjectId, title: str) -> dict:
    now = datetime.now(timezone.utc)
    doc = {"user_id": user_id, "title": title, "created_at": now, "updated_at": now}
    result = await get_db().sessions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_by_user(user_id: ObjectId) -> list[dict]:
    cursor = get_db().sessions.find({"user_id": user_id}).sort("updated_at", -1)
    return await cursor.to_list(length=100)


async def find_by_id(session_id: str) -> dict | None:
    oid = _to_oid(session_id)
    if oid is None:
        return None
    return await get_db().sessions.find_one({"_id": oid})


async def delete(session_id: str) -> None:
    oid = _to_oid(session_id)
    if oid is not None:
        await get_db().sessions.delete_one({"_id": oid})


async def touch(session_id: ObjectId) -> None:
    """Bump updated_at so the session rises to the top of the list."""
    await get_db().sessions.update_one(
        {"_id": session_id}, {"$set": {"updated_at": datetime.now(timezone.utc)}}
    )


async def set_title(session_id: ObjectId, title: str) -> None:
    await get_db().sessions.update_one(
        {"_id": session_id}, {"$set": {"title": title}}
    )

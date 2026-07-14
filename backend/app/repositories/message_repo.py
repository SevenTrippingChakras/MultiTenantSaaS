from datetime import UTC, datetime

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorClientSession

from app.core.tenant_db import scoped


def _to_oid(value: str) -> ObjectId | None:
    """Parse a string id to ObjectId, or None if malformed."""
    try:
        return ObjectId(value)
    except InvalidId:
        return None


async def insert(
    tenant_id: ObjectId,
    session_id: ObjectId,
    role: str,
    content: str,
    metadata: dict | None = None,
    txn: AsyncIOMotorClientSession | None = None,
) -> dict:
    doc = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "created_at": datetime.now(UTC),
        "metadata": metadata or {},
    }
    result = await scoped(tenant_id, txn).messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def count_by_session(tenant_id: ObjectId, session_id: ObjectId) -> int:
    return await scoped(tenant_id).messages.count_documents({"session_id": session_id})


async def list_by_session(
    tenant_id: ObjectId, session_id: ObjectId, limit: int = 200
) -> list[dict]:
    """Return up to `limit` most recent messages, in chronological order."""
    cursor = (
        scoped(tenant_id)
        .messages.find({"session_id": session_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return list(reversed(docs))


async def page_by_session(
    tenant_id: ObjectId,
    session_id: ObjectId,
    limit: int,
    before: str | None = None,
) -> list[dict]:
    """Keyset page of a session's messages for scroll-up paging, newest first.

    Messages are immutable and ordered by insertion, so the cursor is just `_id`.
    A `before` cursor returns messages strictly older than that id. Over-fetches
    one row so the caller can detect whether an older page remains. Returned in
    descending `_id` order (newest first); `build_page_desc` flips to chronological.
    """
    flt: dict = {"session_id": session_id}
    if before:
        oid = _to_oid(before)
        if oid is not None:
            flt["_id"] = {"$lt": oid}
    cursor = scoped(tenant_id).messages.find(flt).sort("_id", -1).limit(limit + 1)
    return await cursor.to_list(length=limit + 1)

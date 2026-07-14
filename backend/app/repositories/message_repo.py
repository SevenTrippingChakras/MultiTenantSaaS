from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClientSession

from app.core.tenant_db import scoped


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

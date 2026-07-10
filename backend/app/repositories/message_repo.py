from datetime import UTC, datetime

from bson import ObjectId

from app.db import get_db


async def insert(
    session_id: ObjectId, role: str, content: str, metadata: dict | None = None
) -> dict:
    doc = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "created_at": datetime.now(UTC),
        "metadata": metadata or {},
    }
    result = await get_db().messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_by_session(session_id: ObjectId, limit: int = 200) -> list[dict]:
    """Return up to `limit` most recent messages, in chronological order."""
    cursor = (
        get_db()
        .messages.find({"session_id": session_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return list(reversed(docs))

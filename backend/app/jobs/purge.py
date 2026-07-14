"""Background purge of soft-deleted rows.

Soft delete (`deleted_at`) keeps rows recoverable for a retention window; this job
reclaims the storage once that window passes. It runs cross-tenant on the raw
collections (bypassing the tenant/soft-delete scope on purpose) and deletes each
expired session together with its messages.

No scheduler yet — run it from the CLI (`uv run python -m app.jobs.purge`) or a
cron. When the task queue lands (Phase 10) this becomes a periodic worker task.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app import db
from app.config import settings

logger = logging.getLogger("aichat")


async def purge_soft_deleted(retention_days: int | None = None) -> dict[str, int]:
    """Hard-delete sessions soft-deleted before the retention cutoff, and their
    messages. Returns the counts removed."""
    days = (
        settings.soft_delete_retention_days
        if retention_days is None
        else retention_days
    )
    cutoff = datetime.now(UTC) - timedelta(days=days)
    database = db.get_db()

    expired = database.sessions.find(
        {"deleted_at": {"$ne": None, "$lt": cutoff}}, {"_id": 1}
    )
    session_ids = [doc["_id"] async for doc in expired]
    if not session_ids:
        return {"sessions": 0, "messages": 0}

    msg_result = await database.messages.delete_many(
        {"session_id": {"$in": session_ids}}
    )
    sess_result = await database.sessions.delete_many({"_id": {"$in": session_ids}})
    counts = {
        "sessions": sess_result.deleted_count,
        "messages": msg_result.deleted_count,
    }
    logger.info("purge complete: %s", counts)
    return counts


async def main() -> None:
    await db.connect()
    try:
        await purge_soft_deleted()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())

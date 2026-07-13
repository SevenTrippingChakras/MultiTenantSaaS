from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    """Return the active database. Call connect() at startup first."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect() on startup.")
    return _db


async def connect() -> None:
    """Open the client, verify the connection with a ping, and create indexes."""
    global _client, _db
    # tz_aware makes Mongo return timezone-aware UTC datetimes, so timestamps
    # serialize consistently (with an offset) instead of naive/ambiguous.
    _client = AsyncIOMotorClient(settings.mongodb_uri, tz_aware=True)
    _db = _client[settings.mongodb_db]
    await _client.admin.command("ping")
    await _create_indexes(_db)


async def close() -> None:
    """Close the client on shutdown."""
    if _client is not None:
        _client.close()


async def _create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Ensure the indexes our queries rely on exist."""
    await db.users.create_index("email", unique=True)
    # Tenant-scoped queries lead with tenant_id, so the indexes do too.
    await db.sessions.create_index(
        [("tenant_id", 1), ("user_id", 1), ("updated_at", -1)]
    )
    await db.messages.create_index(
        [("tenant_id", 1), ("session_id", 1), ("created_at", 1)]
    )

from bson import ObjectId

from app.core.errors import SessionNotFound
from app.repositories import message_repo, session_repo

DEFAULT_TITLE = "New chat"


async def create(tenant_id: ObjectId, user_id: ObjectId, title: str | None) -> dict:
    return await session_repo.insert(tenant_id, user_id, title or DEFAULT_TITLE)


async def list_for_user(tenant_id: ObjectId, user_id: ObjectId) -> list[dict]:
    return await session_repo.list_by_user(tenant_id, user_id)


async def get_owned(tenant_id: ObjectId, session_id: str, user_id: ObjectId) -> dict:
    """Return the session only if it belongs to this user, else 404.

    Tenant scoping makes another tenant's session invisible; the user_id check
    guards ownership within the tenant. We return 404 (not 403) so we don't leak
    that a session exists.
    """
    session = await session_repo.find_by_id(tenant_id, session_id)
    if not session or session["user_id"] != user_id:
        raise SessionNotFound
    return session


async def delete(tenant_id: ObjectId, session_id: str, user_id: ObjectId) -> None:
    await get_owned(tenant_id, session_id, user_id)
    await session_repo.delete(tenant_id, session_id)


async def list_messages(
    tenant_id: ObjectId, session_id: str, user_id: ObjectId, limit: int = 200
) -> list[dict]:
    """Return a session's messages in order, only if the user owns it."""
    session = await get_owned(tenant_id, session_id, user_id)
    return await message_repo.list_by_session(tenant_id, session["_id"], limit)

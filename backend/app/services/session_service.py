from bson import ObjectId

from app.core.errors import SessionNotFound
from app.models.message import to_out as message_to_out
from app.repositories import message_repo, session_repo

DEFAULT_TITLE = "New chat"


async def create(tenant_id: ObjectId, user_id: ObjectId, title: str | None) -> dict:
    return await session_repo.insert(tenant_id, user_id, title or DEFAULT_TITLE)


async def list_for_user(tenant_id: ObjectId, user_id: ObjectId) -> list[dict]:
    return await session_repo.list_by_user(tenant_id, user_id)


async def page_for_user(
    tenant_id: ObjectId, user_id: ObjectId, limit: int, after: str | None
) -> list[dict]:
    """A keyset page of the user's sessions (over-fetched by one row)."""
    return await session_repo.page_by_user(tenant_id, user_id, limit, after)


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


async def export(tenant_id: ObjectId, session_id: str, user_id: ObjectId) -> dict:
    """The session's full transcript as a JSON document (plan feature: export).

    Only if the user owns the session. Not paginated — an export is the whole
    conversation in chronological order.
    """
    session = await get_owned(tenant_id, session_id, user_id)
    messages = await message_repo.list_by_session(tenant_id, session["_id"])
    return {
        "session": {
            "id": str(session["_id"]),
            "title": session["title"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
        },
        "messages": [message_to_out(m) for m in messages],
    }


async def page_messages(
    tenant_id: ObjectId,
    session_id: str,
    user_id: ObjectId,
    limit: int,
    before: str | None,
) -> list[dict]:
    """A keyset page of a session's messages (newest first, over-fetched by one),
    for scroll-up paging. Only if the user owns the session."""
    session = await get_owned(tenant_id, session_id, user_id)
    return await message_repo.page_by_session(tenant_id, session["_id"], limit, before)

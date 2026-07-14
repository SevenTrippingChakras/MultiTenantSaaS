from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser
from app.core.pagination import (
    DEFAULT_LIMIT,
    Page,
    build_page,
    build_page_desc,
    clamp_limit,
)
from app.models.message import MessageOut
from app.models.message import to_out as message_to_out
from app.models.session import SessionCreate, SessionOut
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _to_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc["title"],
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(data: SessionCreate, user: CurrentUser):
    doc = await session_service.create(user["tenant_id"], user["_id"], data.title)
    return _to_out(doc)


@router.get("", response_model=Page[SessionOut])
async def list_sessions(
    user: CurrentUser,
    limit: int = DEFAULT_LIMIT,
    after: str | None = Query(None),
):
    limit = clamp_limit(limit)
    docs = await session_service.page_for_user(
        user["tenant_id"], user["_id"], limit, after
    )
    return build_page(docs, limit, _to_out)


@router.get("/{session_id}/messages", response_model=Page[MessageOut])
async def get_messages(
    session_id: str,
    user: CurrentUser,
    limit: int = DEFAULT_LIMIT,
    before: str | None = Query(None),
):
    """Newest messages first; page backward (older) with `?before=<id>`."""
    limit = clamp_limit(limit)
    docs = await session_service.page_messages(
        user["tenant_id"], session_id, user["_id"], limit, before
    )
    return build_page_desc(docs, limit, message_to_out)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, user: CurrentUser):
    await session_service.delete(user["tenant_id"], session_id, user["_id"])

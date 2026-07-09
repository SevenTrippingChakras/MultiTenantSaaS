"""Session HTTP routes. All scoped to the authenticated user."""

from fastapi import APIRouter, Depends, status

from app.core.deps import get_current_user
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
async def create_session(data: SessionCreate, user: dict = Depends(get_current_user)):
    doc = await session_service.create(user["_id"], data.title)
    return _to_out(doc)


@router.get("", response_model=list[SessionOut])
async def list_sessions(user: dict = Depends(get_current_user)):
    docs = await session_service.list_for_user(user["_id"])
    return [_to_out(d) for d in docs]


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def get_messages(
    session_id: str,
    limit: int = 200,
    user: dict = Depends(get_current_user),
):
    docs = await session_service.list_messages(session_id, user["_id"], limit)
    return [message_to_out(d) for d in docs]


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    await session_service.delete(session_id, user["_id"])

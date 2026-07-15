from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.services import usage_service

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
async def get_usage(user: CurrentUser, limit: int = 30):
    """The signed-in user's month-to-date balance and recent daily usage."""
    return await usage_service.get_usage(
        str(user["tenant_id"]), str(user["_id"]), limit
    )

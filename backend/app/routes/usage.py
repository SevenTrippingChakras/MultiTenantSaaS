from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.services import quota_service, usage_service

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
async def get_usage(user: CurrentUser, limit: int = 30):
    """The signed-in user's plan quota, month-to-date balance, and daily usage."""
    result = await usage_service.get_usage(
        str(user["tenant_id"]), str(user["_id"]), limit
    )
    result["quota"] = await quota_service.status(user["tenant_id"])
    return result

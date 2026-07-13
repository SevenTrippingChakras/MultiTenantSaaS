from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import security
from app.core.errors import InvalidToken
from app.core.logging import tenant_id_ctx, user_id_ctx
from app.repositories import user_repo

bearer = HTTPBearer()


async def get_current_user(
    cred: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> dict:
    """Resolve the user from the Bearer token, or 401."""
    user_id = security.decode_access_token(cred.credentials)
    if not user_id:
        raise InvalidToken
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise InvalidToken
    # Bind the user id + tenant id onto this request's logs.
    user_id_ctx.set(str(user["_id"]))
    tenant_id_ctx.set(str(user["tenant_id"]))
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]

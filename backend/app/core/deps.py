from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import security
from app.core.errors import InvalidToken
from app.repositories import user_repo

bearer = HTTPBearer()


async def get_current_user(
    cred: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> dict:
    """Resolve the user from the Bearer token, or 401."""
    user_id = security.decode_token(cred.credentials)
    if not user_id:
        raise InvalidToken
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise InvalidToken
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]

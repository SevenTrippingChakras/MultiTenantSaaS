from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import security
from app.repositories import user_repo

bearer = HTTPBearer()


async def get_current_user(
    cred: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> dict:
    """Resolve the user from the Bearer token, or 401."""
    user_id = security.decode_token(cred.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]

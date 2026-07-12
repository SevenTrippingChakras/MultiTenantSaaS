from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response, status

from app.core.cookies import (
    REFRESH_COOKIE,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from app.core.csrf import (
    CsrfProtected,
    clear_csrf_cookie,
    generate_csrf_token,
    set_csrf_cookie,
)
from app.core.deps import CurrentUser
from app.core.errors import InvalidToken
from app.core.rate_limit import auth_limit, limiter
from app.models.user import TokenOut, UserLogin, UserOut, UserRegister
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(auth_limit)
async def register(request: Request, data: UserRegister):
    return await auth_service.register(data)


def _issue_session_cookies(response: Response, refresh: str) -> None:
    """Set the refresh cookie plus a fresh CSRF token (double-submit)."""
    set_refresh_cookie(response, refresh)
    set_csrf_cookie(response, generate_csrf_token())


def _clear_session_cookies(response: Response) -> None:
    clear_refresh_cookie(response)
    clear_csrf_cookie(response)


@router.post("/login", response_model=TokenOut)
@limiter.limit(auth_limit)
async def login(request: Request, response: Response, data: UserLogin):
    access, refresh = await auth_service.login(data)
    _issue_session_cookies(response, refresh)
    return TokenOut(access_token=access)


@router.post("/refresh", response_model=TokenOut)
@limiter.limit(auth_limit)
async def refresh(
    request: Request,
    response: Response,
    _csrf: CsrfProtected,
    refresh_token: RefreshCookie = None,
):
    if not refresh_token:
        raise InvalidToken
    access, new_refresh = await auth_service.refresh(refresh_token)
    _issue_session_cookies(response, new_refresh)
    return TokenOut(access_token=access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response, _csrf: CsrfProtected, refresh_token: RefreshCookie = None
):
    if refresh_token:
        await auth_service.logout(refresh_token)
    _clear_session_cookies(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(response: Response, user: CurrentUser):
    await auth_service.logout_all(str(user["_id"]))
    _clear_session_cookies(response)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "created_at": user["created_at"],
    }

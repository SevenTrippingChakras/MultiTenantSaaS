import secrets
from typing import Annotated

from fastapi import Cookie, Depends, Header, Response

from app.config import settings
from app.core.errors import CsrfError

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"
# Root path (unlike the refresh cookie's /auth): the SPA runs at / and reads
# this cookie via document.cookie, which only exposes cookies on the page path.
CSRF_PATH = "/"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE,
        token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=False,  # the client must read it to echo it back in the header
        secure=settings.cookie_secure,
        samesite="strict",
        path=CSRF_PATH,
        domain=settings.cookie_domain,
    )


def clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(CSRF_COOKIE, path=CSRF_PATH, domain=settings.cookie_domain)


def verify_csrf(
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE)] = None,
    csrf_header: Annotated[str | None, Header(alias=CSRF_HEADER)] = None,
) -> None:
    """Reject the request unless the header echoes the cookie (constant-time)."""
    if (
        not csrf_cookie
        or not csrf_header
        or not secrets.compare_digest(csrf_cookie, csrf_header)
    ):
        raise CsrfError


CsrfProtected = Annotated[None, Depends(verify_csrf)]

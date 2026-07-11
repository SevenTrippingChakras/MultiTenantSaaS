"""Domain exceptions and the HTTP error contract.

Services raise the framework-agnostic exceptions defined here; they carry no
FastAPI/HTTP knowledge. `register_error_handlers` installs the thin layer that
maps every error to a single envelope: `{"error": {"code", "message"}}`.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("aichat")


class AppError(Exception):
    """Base domain error. Subclasses set the status, code, and default message."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "Internal server error"

    def __init__(self, message: str | None = None):
        self.message = message or self.message
        super().__init__(self.message)


class EmailAlreadyRegistered(AppError):
    status_code = 409
    code = "email_already_registered"
    message = "Email already registered"


class InvalidCredentials(AppError):
    status_code = 401
    code = "invalid_credentials"
    message = "Invalid credentials"


class InvalidToken(AppError):
    status_code = 401
    code = "invalid_token"
    message = "Invalid or expired token"


class SessionNotFound(AppError):
    status_code = 404
    code = "session_not_found"
    message = "Session not found"


def _envelope(
    status_code: int,
    code: str,
    message: str,
    details: list[dict] | None = None,
) -> JSONResponse:
    error: dict = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


def _field_errors(exc: RequestValidationError) -> list[dict]:
    """Flatten Pydantic errors to `[{"field", "message"}]`.

    `loc` looks like `("body", "email")`; drop the source prefix so the client
    sees the field path it sent. Only strings are copied out, so a non-JSON
    `ctx` value can never break serialization.
    """
    details = []
    for err in exc.errors():
        loc = err["loc"]
        parts = loc[1:] if loc and loc[0] in ("body", "query", "path") else loc
        field = ".".join(str(p) for p in parts) or "__root__"
        details.append({"field": field, "message": err["msg"]})
    return details


def register_error_handlers(app: FastAPI) -> None:
    """Install handlers that render every error as the standard envelope."""

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _envelope(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _envelope(
            422,
            "validation_error",
            "Request validation failed",
            details=_field_errors(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Framework-raised HTTP errors (e.g. missing bearer credentials, 404 routes).
        return _envelope(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _envelope(500, "internal_error", "Internal server error")

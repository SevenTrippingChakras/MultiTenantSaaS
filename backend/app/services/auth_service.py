import logging
import uuid
from datetime import UTC, datetime

from app.core import security
from app.core.errors import EmailAlreadyRegistered, InvalidCredentials, InvalidToken
from app.models.user import UserLogin, UserRegister
from app.repositories import refresh_repo, user_repo

logger = logging.getLogger("aichat.auth")


async def _issue_pair(user_id: str, family_id: str) -> tuple[str, str]:
    """Mint an access + refresh token for a family and store the refresh jti."""
    jti = str(uuid.uuid4())
    await refresh_repo.set_active_jti(user_id, family_id, jti)
    access = security.create_access_token(user_id)
    refresh = security.create_refresh_token(user_id, family_id, jti)
    return access, refresh


async def register(data: UserRegister) -> dict:
    """Create a new user. Fails if the email is already taken."""
    if await user_repo.find_by_email(data.email):
        raise EmailAlreadyRegistered
    doc = {
        "email": data.email,
        "password_hash": security.hash_password(data.password),
        "created_at": datetime.now(UTC),
    }
    user_id = await user_repo.insert(doc)
    logger.info("user registered", extra={"user_id": str(user_id), "email": data.email})
    return {"id": user_id, "email": data.email, "created_at": doc["created_at"]}


async def login(data: UserLogin) -> tuple[str, str]:
    """Verify credentials and start a new session (access + refresh token)."""
    user = await user_repo.find_by_email(data.email)
    if not user or not security.verify_password(data.password, user["password_hash"]):
        logger.warning("login failed", extra={"email": data.email})
        raise InvalidCredentials
    user_id = str(user["_id"])
    logger.info("login succeeded", extra={"user_id": user_id, "email": data.email})
    return await _issue_pair(user_id, str(uuid.uuid4()))


async def refresh(token: str) -> tuple[str, str]:
    """Rotate a refresh token: issue a new pair and invalidate the old jti.

    A refresh token whose jti no longer matches its family's active jti is a
    replay of an already-rotated token, so the whole family is revoked.
    """
    payload = security.decode_refresh_token(token)
    if not payload:
        raise InvalidToken
    user_id, family_id, jti = payload["sub"], payload["fid"], payload["jti"]

    active = await refresh_repo.get_active_jti(family_id)
    if active is None:
        raise InvalidToken
    if active != jti:
        logger.warning(
            "refresh token reuse detected",
            extra={"user_id": user_id, "family_id": family_id},
        )
        await refresh_repo.revoke_family(user_id, family_id)
        raise InvalidToken

    return await _issue_pair(user_id, family_id)


async def logout(token: str) -> None:
    """Revoke the session behind this refresh token. Idempotent: an invalid or
    already-revoked token is a no-op (the caller wants to be logged out anyway)."""
    payload = security.decode_refresh_token(token)
    if not payload:
        return
    await refresh_repo.revoke_family(payload["sub"], payload["fid"])


async def logout_all(user_id: str) -> None:
    """Revoke every session for a user (log out everywhere)."""
    await refresh_repo.revoke_all(user_id)

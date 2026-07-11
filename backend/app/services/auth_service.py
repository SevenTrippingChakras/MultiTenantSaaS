import logging
from datetime import UTC, datetime

from app.core import security
from app.core.errors import EmailAlreadyRegistered, InvalidCredentials
from app.models.user import UserLogin, UserRegister
from app.repositories import user_repo

logger = logging.getLogger("aichat.auth")


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


async def login(data: UserLogin) -> str:
    """Verify credentials and return a signed access token."""
    user = await user_repo.find_by_email(data.email)
    if not user or not security.verify_password(data.password, user["password_hash"]):
        logger.warning("login failed", extra={"email": data.email})
        raise InvalidCredentials
    logger.info(
        "login succeeded",
        extra={"user_id": str(user["_id"]), "email": data.email},
    )
    return security.create_access_token(str(user["_id"]))

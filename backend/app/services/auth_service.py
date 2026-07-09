"""Auth business logic: register and login. No DB or HTTP-framework code here."""

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core import security
from app.models.user import UserLogin, UserRegister
from app.repositories import user_repo


async def register(data: UserRegister) -> dict:
    """Create a new user. Fails if the email is already taken."""
    if await user_repo.find_by_email(data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    doc = {
        "email": data.email,
        "password_hash": security.hash_password(data.password),
        "created_at": datetime.now(timezone.utc),
    }
    user_id = await user_repo.insert(doc)
    return {"id": user_id, "email": data.email, "created_at": doc["created_at"]}


async def login(data: UserLogin) -> str:
    """Verify credentials and return a signed access token."""
    user = await user_repo.find_by_email(data.email)
    if not user or not security.verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return security.create_access_token(str(user["_id"]))

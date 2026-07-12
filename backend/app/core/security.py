from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"

# bcrypt only considers the first 72 bytes and raises on longer input, so we
# truncate to keep hash and verify consistent (and avoid a 500 on long input).
BCRYPT_MAX_BYTES = 72


def _bcrypt_bytes(password: str) -> bytes:
    return password.encode()[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_bytes(password), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(_bcrypt_bytes(password), password_hash.encode())


def _encode(
    user_id: str, token_type: str, expire: datetime, extra: dict | None = None
) -> str:
    payload: dict = {"sub": user_id, "type": token_type, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _decode(token: str, expected_type: str) -> dict | None:
    """Return the payload if the token is valid and of the expected type, else None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


def create_access_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_min)
    return _encode(user_id, "access", expire)


def create_refresh_token(user_id: str, family_id: str, jti: str) -> str:
    """A refresh token carries its jti + family id so a replay can be traced to
    its family even after the jti has been rotated out of the server-side store."""
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return _encode(user_id, "refresh", expire, {"jti": jti, "fid": family_id})


def decode_access_token(token: str) -> str | None:
    """Return the user id from a valid access token, or None if invalid/expired."""
    payload = _decode(token, "access")
    return payload.get("sub") if payload else None


def decode_refresh_token(token: str) -> dict | None:
    """Return the full payload from a valid refresh token, or None."""
    return _decode(token, "refresh")

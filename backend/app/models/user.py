from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class _EmailIn(BaseModel):
    """Base for auth inputs: normalise the email so case/whitespace variants
    (`A@X.com ` vs `a@x.com`) resolve to one account."""

    email: EmailStr

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserRegister(_EmailIn):
    password: str = Field(min_length=8, max_length=128)


class UserLogin(_EmailIn):
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    """Public user shape. Never includes the password hash."""

    id: str
    email: EmailStr
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

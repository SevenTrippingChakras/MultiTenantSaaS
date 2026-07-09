"""Session (conversation) request/response schemas."""

from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    title: str | None = None


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

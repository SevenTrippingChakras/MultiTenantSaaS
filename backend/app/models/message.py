from datetime import datetime

from pydantic import BaseModel, Field

from app.config import settings


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=settings.max_message_chars)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


def to_out(doc: dict) -> dict:
    """Map a Mongo message document to the public shape."""
    return {
        "id": str(doc["_id"]),
        "role": doc["role"],
        "content": doc["content"],
        "created_at": doc["created_at"],
    }

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from openai import OpenAIError

from app.core.deps import CurrentUser
from app.core.rate_limit import chat_limit, limiter
from app.models.message import MessageCreate
from app.services import chat_service, session_service

logger = logging.getLogger("aichat")

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{session_id}")
@limiter.limit(chat_limit)
async def send_message(
    request: Request, session_id: str, data: MessageCreate, user: CurrentUser
):
    # Check ownership before streaming starts, so a bad session returns a real 404.
    tenant_id = user["tenant_id"]
    session = await session_service.get_owned(tenant_id, session_id, user["_id"])
    sid = session["_id"]

    async def sse():
        try:
            async for token in chat_service.stream(tenant_id, sid, data.content):
                yield f"data: {json.dumps({'delta': token})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except OpenAIError:
            # LLM provider failed (rate limit, auth, timeout, mid-stream drop).
            # chat_service already persisted any partial reply in its finally.
            logger.exception("OpenAI error during chat stream")
            err = "The AI service is unavailable. Please try again."
            yield f"data: {json.dumps({'error': err})}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

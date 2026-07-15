import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from openai import OpenAIError

from app.config import settings
from app.core.deps import CurrentUser
from app.core.rate_limit import chat_limit, limiter
from app.core.streaming import with_heartbeat
from app.models.message import MessageCreate
from app.repositories import stop_signal
from app.services import chat_service, session_service

logger = logging.getLogger("aichat")

router = APIRouter(prefix="/chat", tags=["chat"])


def _event(payload: dict) -> str:
    """Format one SSE `data:` event."""
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/{session_id}")
@limiter.limit(chat_limit)
async def send_message(
    request: Request, session_id: str, data: MessageCreate, user: CurrentUser
):
    # Check ownership before streaming starts, so a bad session returns a real 404.
    tenant_id = user["tenant_id"]
    session = await session_service.get_owned(tenant_id, session_id, user["_id"])
    sid = session["_id"]

    # A per-stream id the client echoes back to POST /chat/{sid}/stop/{gen_id}.
    generation_id = uuid4().hex
    stop = asyncio.Event()

    async def sse():
        usage: dict = {}
        # Watch Redis for a stop request (possibly from another worker); the
        # watcher flips `stop`, which unwinds the stream. Cancelled when it ends.
        watcher = asyncio.ensure_future(
            stop_signal.watch_for_stop(session_id, generation_id, stop)
        )
        yield _event({"generation_id": generation_id})
        try:
            async for token in chat_service.stream(
                tenant_id, user["_id"], sid, data.content, usage_out=usage
            ):
                yield _event({"delta": token})
            yield _event({"done": True, "usage": usage})
        except OpenAIError:
            # LLM provider failed (rate limit, auth, timeout, mid-stream drop).
            # chat_service already persisted any partial reply in its finally.
            logger.exception("OpenAI error during chat stream")
            err = "The AI service is unavailable. Please try again."
            yield _event({"error": err})
        finally:
            watcher.cancel()

    return StreamingResponse(
        with_heartbeat(sse(), settings.sse_heartbeat_seconds, stop=stop),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{session_id}/stop/{generation_id}")
async def stop_generation(session_id: str, generation_id: str, user: CurrentUser):
    """Cancel an in-flight stream server-side (stops paying for tokens).

    Owning the session authorises the stop; the signal is published to Redis so
    it reaches whichever worker is running the stream. `stopped` is False if no
    stream was listening (already finished, or a stale generation id).
    """
    tenant_id = user["tenant_id"]
    await session_service.get_owned(tenant_id, session_id, user["_id"])
    receivers = await stop_signal.publish_stop(session_id, generation_id)
    return {"stopped": receivers > 0}

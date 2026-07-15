import logging
from typing import cast

from bson import ObjectId
from openai.types.chat import ChatCompletionMessageParam

from app import db, llm, token_budget
from app.config import settings
from app.repositories import message_repo, session_repo
from app.services import metering

logger = logging.getLogger("aichat")

TITLE_MAX_LEN = 50


def _build_prompt(history: list[dict]) -> list[ChatCompletionMessageParam]:
    """Shape the prompt: stable system prefix first, then token-trimmed history.

    Putting the fixed system prompt at the front keeps the prefix identical
    across turns, which is what lets the provider's prompt cache hit. History is
    trimmed by real token count (not a message count) so one long turn can't blow
    the context window.
    """
    # Roles/content come from Mongo (typed Any); we trust they are valid chat
    # turns, so cast to OpenAI's message-param type at this boundary.
    messages = cast(
        list[ChatCompletionMessageParam],
        [
            {"role": "system", "content": settings.system_prompt},
            *({"role": m["role"], "content": m["content"]} for m in history),
        ],
    )
    return token_budget.trim_to_budget(
        messages, settings.max_context_tokens, settings.openai_model
    )


async def stream(
    tenant_id: ObjectId,
    user_id: ObjectId,
    sid: ObjectId,
    content: str,
    usage_out: dict | None = None,
):
    """Save the user turn, stream the reply, and persist it.

    The reply is saved in a `finally` block so a mid-stream client disconnect
    (or a stop request) still persists whatever was generated. If `usage_out` is
    given, the final token counts are copied into it so the route can emit them
    on the closing SSE event. The caller checks ownership first.
    """
    # First user turn also names the session; persist both writes atomically so
    # a message can't land without its title (or vice versa).
    is_first = await message_repo.count_by_session(tenant_id, sid) == 0
    async with db.transaction() as txn:
        await message_repo.insert(tenant_id, sid, "user", content, txn=txn)
        if is_first:
            await session_repo.set_title(
                tenant_id, sid, content[:TITLE_MAX_LEN], txn=txn
            )

    history = await message_repo.list_by_session(tenant_id, sid)
    prompt = _build_prompt(history)

    chunks: list[str] = []
    usage: dict = {}
    try:
        async for token in llm.stream(prompt, usage_out=usage):
            chunks.append(token)
            yield token
    finally:
        if usage_out is not None:
            usage_out.update(usage)
        reply = "".join(chunks)
        # Meter the tokens spent, even on a partial (stopped) reply. The usage
        # event is written durably in Mongo, atomic with the assistant reply, so
        # a committed reply can never lose its billable event.
        event = None
        if usage.get("total_tokens"):
            event = metering.build_event(
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                session_id=str(sid),
                model=settings.openai_model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )

        if reply:
            # Assistant reply + session bump + usage event go together so the list
            # never shows a session touched newer than its last stored message,
            # and the reply and its usage event commit or roll back as one.
            async with db.transaction() as txn:
                await message_repo.insert(
                    tenant_id,
                    sid,
                    "assistant",
                    reply,
                    metadata={"model": settings.openai_model, "usage": usage},
                    txn=txn,
                )
                await session_repo.touch(tenant_id, sid, txn=txn)
                if event:
                    await metering.store_event(event, txn=txn)
        elif event:
            # Tokens spent but no reply to co-write with (e.g. stopped before any
            # text): still persist the event durably on its own.
            async with db.transaction() as txn:
                await metering.store_event(event, txn=txn)

        # Best-effort month-to-date cache: a failure here must never disturb the
        # durable event written above.
        if event:
            try:
                await metering.bump_counters(event)
            except Exception:
                logger.exception("metering counter update failed for session %s", sid)

from typing import cast

from bson import ObjectId
from openai.types.chat import ChatCompletionMessageParam

from app import llm, token_budget
from app.config import settings
from app.repositories import message_repo, session_repo

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


async def stream(tenant_id: ObjectId, sid: ObjectId, content: str):
    """Save the user turn, stream the reply, and persist it.

    The reply is saved in a `finally` block so a mid-stream client disconnect
    still persists whatever was generated. The caller checks ownership first.
    """
    await message_repo.insert(tenant_id, sid, "user", content)

    history = await message_repo.list_by_session(tenant_id, sid)
    if len(history) == 1:  # first message -> use it as the session title
        await session_repo.set_title(tenant_id, sid, content[:TITLE_MAX_LEN])

    prompt = _build_prompt(history)

    chunks: list[str] = []
    usage: dict = {}
    try:
        async for token in llm.stream(prompt, usage_out=usage):
            chunks.append(token)
            yield token
    finally:
        reply = "".join(chunks)
        if reply:
            await message_repo.insert(
                tenant_id,
                sid,
                "assistant",
                reply,
                metadata={"model": settings.openai_model, "usage": usage},
            )
            await session_repo.touch(tenant_id, sid)

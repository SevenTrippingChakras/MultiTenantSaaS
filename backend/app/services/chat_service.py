from typing import cast

from bson import ObjectId
from openai.types.chat import ChatCompletionMessageParam

from app import llm
from app.config import settings
from app.repositories import message_repo, session_repo

# Cap how many past messages we replay to the LLM (controls token cost).
MAX_CONTEXT_MESSAGES = 20
TITLE_MAX_LEN = 50


async def stream(tenant_id: ObjectId, sid: ObjectId, content: str):
    """Save the user turn, stream the reply, and persist it.

    The reply is saved in a `finally` block so a mid-stream client disconnect
    still persists whatever was generated. The caller checks ownership first.
    """
    await message_repo.insert(tenant_id, sid, "user", content)

    history = await message_repo.list_by_session(tenant_id, sid)
    if len(history) == 1:  # first message -> use it as the session title
        await session_repo.set_title(tenant_id, sid, content[:TITLE_MAX_LEN])

    # Roles/content come from Mongo (typed Any); we trust they are valid chat
    # turns, so cast to OpenAI's message-param type at this boundary.
    prompt = cast(
        list[ChatCompletionMessageParam],
        [
            {"role": m["role"], "content": m["content"]}
            for m in history[-MAX_CONTEXT_MESSAGES:]
        ],
    )

    chunks: list[str] = []
    try:
        async for token in llm.stream(prompt):
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
                metadata={"model": settings.openai_model},
            )
            await session_repo.touch(tenant_id, sid)

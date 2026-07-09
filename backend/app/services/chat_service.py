"""Chat flow: persist the user message, stream the LLM reply, persist it."""

from bson import ObjectId

from app import llm
from app.config import settings
from app.repositories import message_repo, session_repo

# Cap how many past messages we replay to the LLM (controls token cost).
MAX_CONTEXT_MESSAGES = 20
# Longest auto-generated session title, in characters.
TITLE_MAX_LEN = 50


async def stream(sid: ObjectId, content: str):
    """Save the user turn, stream the reply, and persist it.

    The reply is saved in a `finally` block so a mid-stream client disconnect
    still persists whatever was generated. The caller checks ownership first.
    """
    await message_repo.insert(sid, "user", content)

    history = await message_repo.list_by_session(sid)
    if len(history) == 1:  # first message -> use it as the session title
        await session_repo.set_title(sid, content[:TITLE_MAX_LEN])

    prompt = [
        {"role": m["role"], "content": m["content"]}
        for m in history[-MAX_CONTEXT_MESSAGES:]
    ]

    chunks: list[str] = []
    try:
        async for token in llm.stream(prompt):
            chunks.append(token)
            yield token
    finally:
        reply = "".join(chunks)
        if reply:
            await message_repo.insert(
                sid, "assistant", reply, metadata={"model": settings.openai_model}
            )
            await session_repo.touch(sid)

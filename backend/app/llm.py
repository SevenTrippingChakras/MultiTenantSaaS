from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def complete(messages: list[ChatCompletionMessageParam]) -> str | None:
    """Send the conversation to OpenAI and return the full reply text.

    Returns None when the model yields no content; the caller decides how to
    handle that (hardened in the LLM-robustness phase).
    """
    resp = await client.chat.completions.create(
        model=settings.openai_model, messages=messages
    )
    return resp.choices[0].message.content


async def stream(messages: list[ChatCompletionMessageParam]):
    """Yield reply tokens as they arrive from OpenAI."""
    resp = await client.chat.completions.create(
        model=settings.openai_model, messages=messages, stream=True
    )
    async for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

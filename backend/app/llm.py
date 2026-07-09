"""OpenAI client wrapper. Isolates the LLM provider behind one small module."""

from openai import AsyncOpenAI

from app.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def complete(messages: list[dict]) -> str:
    """Send the conversation to OpenAI and return the full reply text."""
    resp = await client.chat.completions.create(
        model=settings.openai_model, messages=messages
    )
    return resp.choices[0].message.content


async def stream(messages: list[dict]):
    """Yield reply tokens as they arrive from OpenAI."""
    resp = await client.chat.completions.create(
        model=settings.openai_model, messages=messages, stream=True
    )
    async for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

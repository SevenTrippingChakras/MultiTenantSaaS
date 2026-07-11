import logging
import time

from openai import AsyncOpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionMessageParam

from app.config import settings

logger = logging.getLogger("aichat.llm")

client = AsyncOpenAI(api_key=settings.openai_api_key)


def _log_usage(usage: CompletionUsage | None, start: float) -> None:
    """Log per-call latency and token usage — the LLM is the main cost driver."""
    extra: dict = {
        "model": settings.openai_model,
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
    }
    if usage is not None:
        extra["prompt_tokens"] = usage.prompt_tokens
        extra["completion_tokens"] = usage.completion_tokens
        extra["total_tokens"] = usage.total_tokens
    logger.info("llm completion", extra=extra)


async def complete(messages: list[ChatCompletionMessageParam]) -> str | None:
    """Send the conversation to OpenAI and return the full reply text.

    Returns None when the model yields no content; the caller decides how to
    handle that (hardened in the LLM-robustness phase).
    """
    start = time.perf_counter()
    resp = await client.chat.completions.create(
        model=settings.openai_model, messages=messages
    )
    _log_usage(resp.usage, start)
    return resp.choices[0].message.content


async def stream(messages: list[ChatCompletionMessageParam]):
    """Yield reply tokens as they arrive from OpenAI.

    `include_usage` asks OpenAI to send a final chunk (with empty `choices`)
    carrying the token counts, so streamed calls are metered like blocking ones.
    """
    start = time.perf_counter()
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )
    usage: CompletionUsage | None = None
    async for chunk in resp:
        if chunk.usage is not None:
            usage = chunk.usage
        if chunk.choices:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    _log_usage(usage, start)

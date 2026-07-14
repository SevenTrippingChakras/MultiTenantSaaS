import logging
import time

from openai import AsyncOpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionMessageParam

from app.config import settings

logger = logging.getLogger("aichat.llm")


client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    timeout=settings.openai_timeout_seconds,
    max_retries=settings.openai_max_retries,
)


def _usage_dict(usage: CompletionUsage | None) -> dict:
    """Flatten OpenAI's usage object into plain token counts (or empty)."""
    if usage is None:
        return {}
    return {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }


def _log_usage(usage: CompletionUsage | None, start: float) -> None:
    """Log per-call latency and token usage — the LLM is the main cost driver."""
    extra: dict = {
        "model": settings.openai_model,
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        **_usage_dict(usage),
    }
    logger.info("llm completion", extra=extra)


async def complete(messages: list[ChatCompletionMessageParam]) -> str:
    """Send the conversation to OpenAI and return the full reply text.

    Returns an empty string if the model yields no content, so the contract is
    always a real `str` (the caller never has to guard against None).
    """
    start = time.perf_counter()
    resp = await client.chat.completions.create(
        model=settings.openai_model, messages=messages
    )
    _log_usage(resp.usage, start)
    return resp.choices[0].message.content or ""


async def stream(
    messages: list[ChatCompletionMessageParam], usage_out: dict | None = None
):
    """Yield reply tokens as they arrive from OpenAI.

    `include_usage` asks OpenAI to send a final chunk (with empty `choices`)
    carrying the token counts, so streamed calls are metered like blocking ones.
    If `usage_out` is given, the token counts are copied into it once the stream
    ends, so the caller can persist/meter usage (not just have it logged).

    The stream is closed in a `finally` so a client disconnect or stop request
    (which throws GeneratorExit into this generator) tears down the upstream
    HTTP connection to OpenAI, ending token billing instead of leaking it.
    """
    start = time.perf_counter()
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )
    usage: CompletionUsage | None = None
    try:
        async for chunk in resp:
            if chunk.usage is not None:
                usage = chunk.usage
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
    finally:
        await resp.close()
        _log_usage(usage, start)
        if usage_out is not None:
            usage_out.update(_usage_dict(usage))

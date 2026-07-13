"""Token-aware history trimming.

The naive "last N messages" cap ignores that one long message can blow the
model's context window. Here we count real tokens (tiktoken) and drop the
oldest turns until the conversation fits a token budget — the system prompt at
index 0 is always kept, since it is the stable instruction prefix.
"""

import tiktoken
from openai.types.chat import ChatCompletionMessageParam

_TOKENS_PER_MESSAGE = 3
_REPLY_PRIMING = 3


def _encoding(model: str) -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def count_tokens(messages: list[ChatCompletionMessageParam], model: str) -> int:
    """Estimate how many prompt tokens `messages` will cost `model`."""
    enc = _encoding(model)
    total = _REPLY_PRIMING
    for m in messages:
        total += _TOKENS_PER_MESSAGE
        content = m.get("content")
        if isinstance(content, str):
            total += len(enc.encode(content))
    return total


def trim_to_budget(
    messages: list[ChatCompletionMessageParam], budget: int, model: str
) -> list[ChatCompletionMessageParam]:
    """Drop the oldest turns until the prompt fits `budget` tokens.

    The first message (system prompt) is always kept; remaining turns are added
    newest-first until the budget is reached, then returned in chronological order.
    """
    if not messages:
        return messages

    system, history = messages[0], messages[1:]
    kept: list[ChatCompletionMessageParam] = []
    used = count_tokens([system], model)
    for m in reversed(history):
        cost = count_tokens([m], model) - _REPLY_PRIMING
        if used + cost > budget:
            break
        kept.append(m)
        used += cost
    kept.reverse()
    return [system, *kept]

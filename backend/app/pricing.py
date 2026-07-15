"""Per-model token pricing and derived cost.

Metering stores both raw token counts *and* the money they cost, because
provider prices change over time and historical usage must reflect the price
that applied when the tokens were spent (arch B2, "cost model"). Prices here are
USD per 1M tokens, split into prompt (input) and completion (output).

Update this table when a model's price changes or a new model is added; unknown
models fall back to `_DEFAULT` so a call is never metered at zero cost silently.
"""

# USD per 1,000,000 tokens: (prompt, completion).
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
}

# Fallback for an unpriced model: the cheapest current mini rate, so cost is
# never silently zero (which would hide usage from billing).
_DEFAULT = (0.15, 0.60)

_PER_MILLION = 1_000_000


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """USD cost of one call, from its prompt/completion token counts."""
    prompt_rate, completion_rate = _PRICING.get(model, _DEFAULT)
    cost = (
        prompt_tokens * prompt_rate + completion_tokens * completion_rate
    ) / _PER_MILLION
    return round(cost, 6)

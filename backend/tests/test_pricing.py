"""Cost model (Phase 10): per-model token pricing."""

from app import pricing


def test_known_model_cost():
    # gpt-4o-mini: $0.15/1M prompt, $0.60/1M completion.
    # 1000 prompt -> 0.00015, 500 completion -> 0.0003, total 0.00045.
    assert pricing.cost_usd("gpt-4o-mini", 1000, 500) == 0.00045


def test_completion_costs_more_than_prompt():
    prompt_only = pricing.cost_usd("gpt-4o", 1000, 0)
    completion_only = pricing.cost_usd("gpt-4o", 0, 1000)
    assert completion_only > prompt_only


def test_unknown_model_falls_back_not_zero():
    # An unpriced model must still cost something (never silently free).
    assert pricing.cost_usd("some-new-model", 1000, 1000) > 0


def test_zero_tokens_zero_cost():
    assert pricing.cost_usd("gpt-4o-mini", 0, 0) == 0.0

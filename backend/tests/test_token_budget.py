"""Token-budget trimming (Phase 7). Pure unit tests — no DB, no network."""

from app.token_budget import count_tokens, trim_to_budget

MODEL = "gpt-4o-mini"


def _msgs(*pairs):
    return [{"role": r, "content": c} for r, c in pairs]


def test_count_tokens_grows_with_content():
    short = _msgs(("user", "hi"))
    long = _msgs(("user", "hello " * 100))
    assert count_tokens(long, MODEL) > count_tokens(short, MODEL)


def test_trim_keeps_system_and_newest_within_budget():
    msgs = _msgs(
        ("system", "You are a helpful assistant."),
        ("user", "old " * 200),
        ("assistant", "reply " * 200),
        ("user", "latest short question"),
    )
    trimmed = trim_to_budget(msgs, budget=60, model=MODEL)

    # System prefix is always first; the two long old turns are dropped.
    assert trimmed[0]["role"] == "system"
    assert [m["role"] for m in trimmed] == ["system", "user"]
    assert trimmed[-1]["content"] == "latest short question"
    assert count_tokens(trimmed, MODEL) <= 60


def test_trim_keeps_everything_under_a_large_budget():
    msgs = _msgs(
        ("system", "sys"),
        ("user", "a"),
        ("assistant", "b"),
        ("user", "c"),
    )
    assert trim_to_budget(msgs, budget=100_000, model=MODEL) == msgs


def test_trim_preserves_chronological_order():
    msgs = _msgs(
        ("system", "sys"),
        ("user", "one"),
        ("assistant", "two"),
        ("user", "three"),
    )
    trimmed = trim_to_budget(msgs, budget=100_000, model=MODEL)
    assert [m["content"] for m in trimmed] == ["sys", "one", "two", "three"]


def test_trim_empty_list_is_noop():
    assert trim_to_budget([], budget=100, model=MODEL) == []

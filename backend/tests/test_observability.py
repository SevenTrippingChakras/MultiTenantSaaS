"""Observability: request-id propagation and JSON log formatting."""

import json
import logging

from app.core.logging import (
    ContextFilter,
    JsonFormatter,
    request_id_ctx,
    user_id_ctx,
)
from app.core.middleware import REQUEST_ID_HEADER


def _record(msg: str = "event", **extra) -> logging.LogRecord:
    record = logging.LogRecord("aichat", logging.INFO, __file__, 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


async def test_request_id_generated(client):
    resp = await client.get("/health")
    assert resp.headers[REQUEST_ID_HEADER]


async def test_request_id_preserved(client):
    rid = "trace-abc-123"
    resp = await client.get("/health", headers={REQUEST_ID_HEADER: rid})
    assert resp.headers[REQUEST_ID_HEADER] == rid


def test_json_formatter_serializes_request_id_and_extra():
    token = request_id_ctx.set("abc123")
    try:
        record = logging.LogRecord(
            "aichat.llm", logging.INFO, __file__, 1, "llm completion", None, None
        )
        record.request_id = request_id_ctx.get()  # the filter normally sets this
        record.total_tokens = 42
        line = JsonFormatter().format(record)
    finally:
        request_id_ctx.reset(token)

    data = json.loads(line)
    assert data["message"] == "llm completion"
    assert data["level"] == "INFO"
    assert data["request_id"] == "abc123"
    assert data["total_tokens"] == 42


def test_context_filter_stamps_user_id_from_ctx():
    token = user_id_ctx.set("user-1")
    try:
        record = _record()
        ContextFilter().filter(record)
    finally:
        user_id_ctx.reset(token)
    assert record.user_id == "user-1"


def test_explicit_user_id_wins_over_ctx():
    # A login event knows the id before it is bound to the context; its explicit
    # extra must not be clobbered by the (possibly empty) ContextVar.
    token = user_id_ctx.set("ctx-user")
    try:
        record = _record(user_id="explicit-user")
        ContextFilter().filter(record)
    finally:
        user_id_ctx.reset(token)
    assert record.user_id == "explicit-user"

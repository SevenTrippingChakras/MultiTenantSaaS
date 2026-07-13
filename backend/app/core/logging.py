"""Structured JSON logging that stamps each line with request/user correlation ids."""

import json
import logging
from contextvars import ContextVar

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)
tenant_id_ctx: ContextVar[str | None] = ContextVar("tenant_id", default=None)

# Attributes a bare record already has; anything else was passed via extra= and
# is swept into the JSON output.
_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"request_id", "message"}


class ContextFilter(logging.Filter):
    """Stamp the current request id and user id onto every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        # An explicit extra={"user_id": ...} (e.g. login events, before the id is
        # bound to the context) wins over the ContextVar fallback.
        if not hasattr(record, "user_id"):
            uid = user_id_ctx.get()
            if uid is not None:
                record.user_id = uid
        if not hasattr(record, "tenant_id"):
            tid = tenant_id_ctx.get()
            if tid is not None:
                record.tenant_id = tid
        return True


class JsonFormatter(logging.Formatter):
    """Render a log record as one JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = getattr(record, "request_id", None)
        if rid:
            payload["request_id"] = rid
        for key, value in record.__dict__.items():
            if key not in _STANDARD:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON handler + context filter on the root logger."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

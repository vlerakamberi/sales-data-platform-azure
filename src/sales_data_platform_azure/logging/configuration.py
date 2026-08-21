"""Structured standard-library logging with correlation context."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import UTC, datetime

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_execution_id: ContextVar[str | None] = ContextVar("execution_id", default=None)
_SAFE_RECORD_FIELDS = (
    "stage",
    "outcome",
    "failure_classification",
    "failed_expectation_ids",
)


class JsonFormatter(logging.Formatter):
    """Format an allowlisted set of fields as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = _correlation_id.get()
        execution_id = _execution_id.get()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if execution_id:
            payload["execution_id"] = execution_id
        for field in _SAFE_RECORD_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_logging(level: str = "INFO", *, stream: object | None = None) -> logging.Logger:
    """Idempotently configure the repository package logger."""
    logger = logging.getLogger("sales_data_platform_azure")
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
    return logger


@contextmanager
def correlation_context(
    *, correlation_id: str | None = None, execution_id: str | None = None
) -> Iterator[None]:
    """Attach identifiers to log records within a context and then restore prior values."""
    correlation_token: Token[str | None] = _correlation_id.set(correlation_id)
    execution_token: Token[str | None] = _execution_id.set(execution_id)
    try:
        yield
    finally:
        _correlation_id.reset(correlation_token)
        _execution_id.reset(execution_token)

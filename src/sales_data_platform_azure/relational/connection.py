"""Interface-only connection boundary for later PostgreSQL persistence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from sales_data_platform_azure.config import PostgreSQLSettings


@runtime_checkable
class RelationalConnection(Protocol):
    """Minimal explicit-transaction connection used by the serving repository."""

    def execute(self, query: str, params: Sequence[Any] | Mapping[str, Any] = ()) -> object:
        """Execute one parameterized statement."""

    def commit(self) -> None:
        """Atomically commit all serving writes."""

    def rollback(self) -> None:
        """Discard all writes from the failed serving attempt."""

    def close(self) -> None:
        """Release the future adapter connection."""


class RelationalConnectionFactory(Protocol):
    """Create connections without prescribing a driver or token-acquisition mechanism."""

    def connect(self, settings: PostgreSQLSettings) -> RelationalConnection:
        """Return an authenticated connection from validated non-secret metadata."""

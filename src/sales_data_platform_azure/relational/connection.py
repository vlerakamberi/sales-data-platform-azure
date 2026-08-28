"""Interface-only connection boundary for later PostgreSQL persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sales_data_platform_azure.config import PostgreSQLSettings


@runtime_checkable
class RelationalConnection(Protocol):
    """Opaque connection marker implemented by a future database adapter."""

    def close(self) -> None:
        """Release the future adapter connection."""


class RelationalConnectionFactory(Protocol):
    """Create connections without prescribing a driver or token-acquisition mechanism."""

    def connect(self, settings: PostgreSQLSettings) -> RelationalConnection:
        """Return an authenticated connection from validated non-secret metadata."""

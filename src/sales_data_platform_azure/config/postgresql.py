"""Validated, secret-free PostgreSQL serving configuration contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .settings import ConfigurationError


@dataclass(frozen=True, slots=True)
class PostgreSQLSettings:
    """Private, Entra-only PostgreSQL connection metadata for a future runtime."""

    host: str
    database: str
    user: str
    port: int = 5432
    sslmode: str = "require"
    managed_identity_client_id: str | None = None

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> PostgreSQLSettings:
        """Build settings from an explicit environment mapping without acquiring a token."""
        try:
            port = int(environ.get("SDPA_POSTGRESQL_PORT", "5432"))
        except ValueError as error:
            raise ConfigurationError("SDPA_POSTGRESQL_PORT must be an integer") from error
        settings = cls(
            host=environ.get("SDPA_POSTGRESQL_HOST", "").strip(),
            database=environ.get("SDPA_POSTGRESQL_DATABASE", "").strip(),
            user=environ.get("SDPA_POSTGRESQL_USER", "").strip(),
            port=port,
            sslmode=environ.get("SDPA_POSTGRESQL_SSLMODE", "require").strip().lower(),
            managed_identity_client_id=(
                environ.get("SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID", "").strip() or None
            ),
        )
        settings.validate(environ)
        return settings

    def validate(self, environ: Mapping[str, str] | None = None) -> None:
        """Reject incomplete, unsafe, or password-bearing configuration."""
        if not self.host or not self.database or not self.user:
            raise ConfigurationError("PostgreSQL host, database, and user must not be empty")
        if not 1 <= self.port <= 65535:
            raise ConfigurationError("PostgreSQL port must be between 1 and 65535")
        if self.sslmode not in {"require", "verify-ca", "verify-full"}:
            raise ConfigurationError("PostgreSQL SSL mode must require encrypted transport")
        if environ is not None and any(
            key in environ for key in ("SDPA_POSTGRESQL_PASSWORD", "PGPASSWORD")
        ):
            raise ConfigurationError("PostgreSQL password fallback is prohibited")

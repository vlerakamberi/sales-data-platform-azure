"""Concrete Psycopg connection adapter with injected credential material."""

from __future__ import annotations

from typing import Protocol

import psycopg

from sales_data_platform_azure.config import PostgreSQLSettings

from .connection import RelationalConnection


class PostgreSQLCredentialProvider(Protocol):
    """Supply short-lived credential material without prescribing Entra acquisition."""

    def get_credential(self) -> str:
        """Return credential material for one connection attempt."""


class PsycopgConnectionFactory:
    """Open an explicit-transaction PostgreSQL connection using an injected credential."""

    def __init__(self, credential_provider: PostgreSQLCredentialProvider) -> None:
        self._credential_provider = credential_provider

    def connect(self, settings: PostgreSQLSettings) -> RelationalConnection:
        """Connect without logging or retaining the injected credential."""
        settings.validate()
        credential = self._credential_provider.get_credential()
        if not credential:
            raise ValueError("PostgreSQL credential must not be empty")
        return psycopg.connect(
            host=settings.host,
            dbname=settings.database,
            user=settings.user,
            password=credential,
            port=settings.port,
            sslmode=settings.sslmode,
            autocommit=False,
        )

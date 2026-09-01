"""Managed-identity PostgreSQL serving runtime composition."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol

from sales_data_platform_azure.config import ConfigurationError, PostgreSQLSettings

from .adapter import PsycopgConnectionFactory
from .postgresql_activation import POSTGRESQL_ENTRA_SCOPE
from .repository import PostgreSQLServingRepository
from .service import RelationalServingService


class AccessToken(Protocol):
    """Minimal Azure access-token shape used by the runtime adapter."""

    token: str


class TokenCredential(Protocol):
    """Minimal Azure Identity credential boundary used by local tests."""

    def get_token(self, *scopes: str) -> AccessToken: ...


CredentialFactory = Callable[..., TokenCredential]


class ManagedIdentityPostgreSQLCredentialProvider:
    """Acquire one short-lived PostgreSQL Entra token per connection attempt."""

    def __init__(
        self,
        managed_identity_client_id: str | None,
        *,
        credential_factory: CredentialFactory | None = None,
    ) -> None:
        if not managed_identity_client_id:
            raise ConfigurationError(
                "SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID is required for PostgreSQL serving"
            )
        if credential_factory is None:
            from azure.identity import ManagedIdentityCredential

            credential_factory = ManagedIdentityCredential
        self._credential = credential_factory(client_id=managed_identity_client_id)

    def get_credential(self) -> str:
        """Return an Azure Database for PostgreSQL token without retaining its value."""
        token = self._credential.get_token(POSTGRESQL_ENTRA_SCOPE).token
        if not token:
            raise ValueError("PostgreSQL Entra token must not be empty")
        return token


def build_relational_serving_service(
    environ: Mapping[str, str],
    *,
    credential_factory: CredentialFactory | None = None,
) -> RelationalServingService:
    """Compose the existing relational serving stack from non-secret environment metadata."""
    settings = PostgreSQLSettings.from_environment(environ)
    credential_provider = ManagedIdentityPostgreSQLCredentialProvider(
        settings.managed_identity_client_id,
        credential_factory=credential_factory,
    )
    connection_factory = PsycopgConnectionFactory(credential_provider)
    repository = PostgreSQLServingRepository(connection_factory, settings)
    return RelationalServingService(repository)

from dataclasses import dataclass

import pytest

from sales_data_platform_azure.config import ConfigurationError, PostgreSQLSettings
from sales_data_platform_azure.relational import (
    ManagedIdentityPostgreSQLCredentialProvider,
    PostgreSQLServingRepository,
    PsycopgConnectionFactory,
    RelationalServingService,
    build_relational_serving_service,
)
from sales_data_platform_azure.relational.postgresql_activation import POSTGRESQL_ENTRA_SCOPE


@dataclass(frozen=True)
class FakeAccessToken:
    token: str


class FakeTokenCredential:
    def __init__(self, credential_value: str = "short-lived-token") -> None:
        self.token = credential_value
        self.scopes: list[tuple[str, ...]] = []

    def get_token(self, *scopes: str) -> FakeAccessToken:
        self.scopes.append(scopes)
        return FakeAccessToken(self.token)


class CredentialFactorySpy:
    def __init__(self, credential: FakeTokenCredential | None = None) -> None:
        self.credential = credential or FakeTokenCredential()
        self.calls: list[dict[str, str]] = []

    def __call__(self, **kwargs: str) -> FakeTokenCredential:
        self.calls.append(kwargs)
        return self.credential


def _environment(**overrides: str) -> dict[str, str]:
    environ = {
        "SDPA_POSTGRESQL_HOST": "private.example.postgres.database.azure.com",
        "SDPA_POSTGRESQL_DATABASE": "sales",
        "SDPA_POSTGRESQL_USER": "serving-runtime",
        "SDPA_POSTGRESQL_PORT": "5433",
        "SDPA_POSTGRESQL_SSLMODE": "verify-full",
    }
    environ.update(overrides)
    return environ


def test_provider_acquires_a_fresh_token_for_the_postgresql_entra_scope() -> None:
    credential = FakeTokenCredential()
    provider = ManagedIdentityPostgreSQLCredentialProvider(
        "postgresql-workload-client-id",
        credential_factory=CredentialFactorySpy(credential),
    )

    assert provider.get_credential() == "short-lived-token"
    assert provider.get_credential() == "short-lived-token"
    assert credential.scopes == [(POSTGRESQL_ENTRA_SCOPE,), (POSTGRESQL_ENTRA_SCOPE,)]


def test_provider_selects_explicit_user_assigned_managed_identity() -> None:
    factory = CredentialFactorySpy()

    ManagedIdentityPostgreSQLCredentialProvider(
        "postgresql-workload-client-id", credential_factory=factory
    )

    assert factory.calls == [{"client_id": "postgresql-workload-client-id"}]


@pytest.mark.parametrize("client_id", [None, ""])
def test_provider_fails_closed_without_a_dedicated_identity(client_id: str | None) -> None:
    factory = CredentialFactorySpy()

    with pytest.raises(ConfigurationError, match="MANAGED_IDENTITY_CLIENT_ID is required"):
        ManagedIdentityPostgreSQLCredentialProvider(client_id, credential_factory=factory)

    assert factory.calls == []


def test_provider_rejects_an_empty_acquired_token() -> None:
    provider = ManagedIdentityPostgreSQLCredentialProvider(
        "postgresql-workload-client-id",
        credential_factory=CredentialFactorySpy(FakeTokenCredential("")),
    )

    with pytest.raises(ValueError, match="must not be empty"):
        provider.get_credential()


def test_runtime_composes_existing_service_repository_and_connection_factory() -> None:
    factory = CredentialFactorySpy()
    environ = _environment(
        SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID="postgresql-workload-client-id"
    )

    service = build_relational_serving_service(environ, credential_factory=factory)

    assert isinstance(service, RelationalServingService)
    repository = service._repository
    assert isinstance(repository, PostgreSQLServingRepository)
    assert repository._settings == PostgreSQLSettings(
        host="private.example.postgres.database.azure.com",
        database="sales",
        user="serving-runtime",
        port=5433,
        sslmode="verify-full",
        managed_identity_client_id="postgresql-workload-client-id",
    )
    assert isinstance(repository._connection_factory, PsycopgConnectionFactory)
    assert factory.calls == [{"client_id": "postgresql-workload-client-id"}]


@pytest.mark.parametrize(
    "environ",
    [
        _environment(),
        _environment(SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID=""),
        _environment(SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID="   "),
    ],
)
def test_runtime_composition_fails_closed_without_dedicated_identity(
    environ: dict[str, str],
) -> None:
    factory = CredentialFactorySpy()

    with pytest.raises(ConfigurationError, match="MANAGED_IDENTITY_CLIENT_ID is required"):
        build_relational_serving_service(environ, credential_factory=factory)

    assert factory.calls == []


@pytest.mark.parametrize("password_variable", ["SDPA_POSTGRESQL_PASSWORD", "PGPASSWORD"])
def test_runtime_composition_rejects_password_fallback(password_variable: str) -> None:
    with pytest.raises(ConfigurationError, match="password fallback"):
        build_relational_serving_service(
            _environment(**{password_variable: "prohibited"}),
            credential_factory=CredentialFactorySpy(),
        )

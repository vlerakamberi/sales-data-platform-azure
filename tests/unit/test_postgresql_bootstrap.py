import importlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from sales_data_platform_azure.config import ConfigurationError
from sales_data_platform_azure.relational.bootstrap import (
    APPROVED_BOOTSTRAP_IDENTITY_NAME,
    APPROVED_BOOTSTRAP_OBJECT_ID,
    APPROVED_BOOTSTRAP_POSTGRESQL_USERNAME,
    APPROVED_WORKLOAD_CLIENT_ID,
    APPROVED_WORKLOAD_IDENTITY_NAME,
    APPROVED_WORKLOAD_OBJECT_ID,
    PostgreSQLBootstrapSettings,
    PsycopgActivationConnectionFactory,
    build_postgresql_bootstrap_runtime,
    main,
)
from sales_data_platform_azure.relational.postgresql_activation import (
    POSTGRESQL_ENTRA_SCOPE,
    WORKLOAD_DATABASE_ROLE,
    ActivationStatus,
)

ROOT = Path(__file__).parents[2]
MIGRATIONS = ROOT / "sql" / "migrations"


def _environment(**overrides: str) -> dict[str, str]:
    environ = {
        "SDPA_POSTGRESQL_HOST": "nsrsdp-dev-2gndgslsp4a6c-pg.postgres.database.azure.com",
        "SDPA_POSTGRESQL_DATABASE": "sales",
        "SDPA_POSTGRESQL_PORT": "5432",
        "SDPA_POSTGRESQL_SSLMODE": "verify-full",
        "SDPA_POSTGRESQL_BOOTSTRAP_IDENTITY_NAME": APPROVED_BOOTSTRAP_IDENTITY_NAME,
        "SDPA_POSTGRESQL_BOOTSTRAP_IDENTITY_OBJECT_ID": APPROVED_BOOTSTRAP_OBJECT_ID,
        "SDPA_POSTGRESQL_BOOTSTRAP_POSTGRESQL_USERNAME": (APPROVED_BOOTSTRAP_POSTGRESQL_USERNAME),
        "SDPA_POSTGRESQL_WORKLOAD_IDENTITY_NAME": APPROVED_WORKLOAD_IDENTITY_NAME,
        "SDPA_POSTGRESQL_WORKLOAD_IDENTITY_OBJECT_ID": APPROVED_WORKLOAD_OBJECT_ID,
        "SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID": APPROVED_WORKLOAD_CLIENT_ID,
        "SDPA_POSTGRESQL_MIGRATIONS_DIRECTORY": str(MIGRATIONS),
    }
    environ.update(overrides)
    return environ


@dataclass(frozen=True)
class FakeAccessToken:
    token: str


class FakeCredential:
    def __init__(self) -> None:
        self.requests: list[tuple[str, ...]] = []
        self.value = "short-lived-bootstrap-token"

    def get_token(self, *scopes: str) -> FakeAccessToken:
        self.requests.append(scopes)
        return FakeAccessToken(self.value)


class CredentialFactory:
    def __init__(self) -> None:
        self.credential = FakeCredential()
        self.calls = 0

    def __call__(self) -> FakeCredential:
        self.calls += 1
        return self.credential


class FakeConnection:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.reconciled = None

    def begin(self) -> None:
        self.events.append("begin")

    def inspect_history(self):
        self.events.append("inspect")
        return ()

    def reconcile_principal(self, identity, role: str) -> bool:
        self.events.append(f"reconcile:{role}")
        self.reconciled = identity
        return True

    def execute_migration(self, migration, migration_sql: str) -> None:
        self.events.append(f"execute:{migration.version}")
        assert "CREATE SCHEMA IF NOT EXISTS serving" in migration_sql

    def record_migration(self, migration, checksum: str) -> None:
        self.events.append(f"record:{migration.version}")
        assert len(checksum) == 64

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")

    def close(self) -> None:
        self.events.append("close")


class FakeConnectionFactory:
    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.calls = []

    def connect(self, target, identity, token: str) -> FakeConnection:
        self.calls.append((target, identity, token))
        return self.connection


def test_valid_configuration_composes_expected_activation_objects_without_token_request() -> None:
    credentials = CredentialFactory()
    connections = FakeConnectionFactory()

    runtime = build_postgresql_bootstrap_runtime(
        _environment(), credential_factory=credentials, connection_factory=connections
    )

    assert runtime.target.host == _environment()["SDPA_POSTGRESQL_HOST"]
    assert runtime.target.database == "sales"
    assert runtime.target.private_connectivity is True
    assert runtime.target.sslmode == "verify-full"
    assert runtime.identities.bootstrap.name == APPROVED_BOOTSTRAP_IDENTITY_NAME
    assert runtime.identities.bootstrap.object_id == APPROVED_BOOTSTRAP_OBJECT_ID
    assert runtime.identities.workload.name == APPROVED_WORKLOAD_IDENTITY_NAME
    assert runtime.identities.workload.object_id == APPROVED_WORKLOAD_OBJECT_ID
    assert runtime.identities.bootstrap != runtime.identities.workload
    assert runtime.activator._migrations_directory == MIGRATIONS.resolve()
    assert credentials.calls == 1
    assert credentials.credential.requests == []
    assert connections.calls == []


def test_explicit_operation_invokes_existing_activator_with_governed_identities() -> None:
    credentials = CredentialFactory()
    connections = FakeConnectionFactory()
    runtime = build_postgresql_bootstrap_runtime(
        _environment(), credential_factory=credentials, connection_factory=connections
    )

    result = runtime.activate()

    assert result.status is ActivationStatus.ACTIVATED
    assert result.applied_versions == (1,)
    assert credentials.credential.requests == [(POSTGRESQL_ENTRA_SCOPE,)]
    target, bootstrap, token = connections.calls[0]
    assert target == runtime.target
    assert bootstrap == runtime.identities.bootstrap
    assert token == credentials.credential.value
    assert connections.connection.reconciled == runtime.identities.workload
    assert f"reconcile:{WORKLOAD_DATABASE_ROLE}" in connections.connection.events


@pytest.mark.parametrize(
    "variables",
    [
        ("SDPA_POSTGRESQL_BOOTSTRAP_IDENTITY_NAME",),
        ("SDPA_POSTGRESQL_BOOTSTRAP_IDENTITY_OBJECT_ID",),
        ("SDPA_POSTGRESQL_BOOTSTRAP_POSTGRESQL_USERNAME",),
        ("SDPA_POSTGRESQL_WORKLOAD_IDENTITY_NAME",),
        ("SDPA_POSTGRESQL_WORKLOAD_IDENTITY_OBJECT_ID",),
        ("SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID",),
    ],
)
def test_missing_identity_configuration_fails_closed_without_credential_construction(
    variables: tuple[str, ...],
) -> None:
    environ = _environment()
    for variable in variables:
        del environ[variable]
    credentials = CredentialFactory()

    with pytest.raises(ConfigurationError, match="missing PostgreSQL bootstrap configuration"):
        build_postgresql_bootstrap_runtime(environ, credential_factory=credentials)

    assert credentials.calls == 0


@pytest.mark.parametrize("variable", ["SDPA_POSTGRESQL_PASSWORD", "PGPASSWORD"])
def test_password_configuration_is_rejected(variable: str) -> None:
    with pytest.raises(ConfigurationError, match="password fallback"):
        PostgreSQLBootstrapSettings.from_environment(_environment(**{variable: "prohibited"}))


def test_workload_client_id_is_explicit_and_not_an_identity_object_id() -> None:
    settings = PostgreSQLBootstrapSettings.from_environment(_environment())

    assert settings.workload_client_id == APPROVED_WORKLOAD_CLIENT_ID
    assert settings.workload_client_id != settings.bootstrap_object_id
    assert settings.workload_client_id != settings.workload_object_id


@pytest.mark.parametrize("username", ["", "   ", "Vlera Kamberi", "invalid@example.com"])
def test_invalid_or_missing_bootstrap_postgresql_username_fails_closed(username: str) -> None:
    credentials = CredentialFactory()

    with pytest.raises(ConfigurationError):
        build_postgresql_bootstrap_runtime(
            _environment(SDPA_POSTGRESQL_BOOTSTRAP_POSTGRESQL_USERNAME=username),
            credential_factory=credentials,
        )

    assert credentials.calls == 0


def test_psycopg_connection_uses_verified_upn_and_never_display_name(monkeypatch) -> None:
    captured: dict[str, object] = {}
    connection = FakeConnection()

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return connection

    monkeypatch.setattr(
        "sales_data_platform_azure.relational.bootstrap.psycopg.connect", fake_connect
    )
    runtime = build_postgresql_bootstrap_runtime(
        _environment(),
        credential_factory=CredentialFactory(),
    )
    factory = runtime.activator._connection_factory

    assert isinstance(factory, PsycopgActivationConnectionFactory)
    factory.connect(runtime.target, runtime.identities.bootstrap, "short-lived-token")
    assert captured["user"] == APPROVED_BOOTSTRAP_POSTGRESQL_USERNAME
    assert captured["user"] != APPROVED_BOOTSTRAP_IDENTITY_NAME


def test_migrations_directory_is_the_existing_repository_authority() -> None:
    settings = PostgreSQLBootstrapSettings.from_environment(_environment())

    assert settings.migrations_directory.resolve() == MIGRATIONS.resolve()
    assert [path.name for path in settings.migrations_directory.glob("V*.sql")] == [
        "V001__create_relational_serving_foundation.sql"
    ]


def test_import_does_not_construct_credentials_or_acquire_tokens(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "azure.identity.AzureCliCredential", lambda: calls.append("constructed"), raising=True
    )

    import sales_data_platform_azure.relational.bootstrap as bootstrap

    importlib.reload(bootstrap)
    assert calls == []


def test_cli_output_and_errors_never_contain_token_material() -> None:
    credentials = CredentialFactory()
    connections = FakeConnectionFactory()

    def builder(environ):
        return build_postgresql_bootstrap_runtime(
            environ, credential_factory=credentials, connection_factory=connections
        )

    stdout, stderr = io.StringIO(), io.StringIO()
    exit_code = main(
        [], environ=_environment(), stdout=stdout, stderr=stderr, runtime_builder=builder
    )

    assert exit_code == 0
    assert json.loads(stdout.getvalue())["status"] == "ACTIVATED"
    assert stderr.getvalue() == ""
    assert "short-lived-bootstrap-token" not in stdout.getvalue() + stderr.getvalue()

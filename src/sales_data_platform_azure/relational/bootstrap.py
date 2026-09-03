"""Explicit, development-only PostgreSQL Entra bootstrap command."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, TextIO

import psycopg

from sales_data_platform_azure.config import ConfigurationError

from .migrations import AppliedMigration, Migration
from .postgresql_activation import (
    ActivationIdentities,
    ActivationResult,
    DevelopmentTarget,
    EntraIdentity,
    PostgreSQLActivationConnection,
    PostgreSQLActivationConnectionFactory,
    PostgreSQLActivator,
)

APPROVED_BOOTSTRAP_IDENTITY_NAME = "Vlera Kamberi"
APPROVED_BOOTSTRAP_OBJECT_ID = "19ec5eb3-0ae2-4e79-bdf1-4e9d9f905313"
APPROVED_BOOTSTRAP_POSTGRESQL_USERNAME = "vkamberi97_gmail.com#EXT#@vkamberi97gmail.onmicrosoft.com"
APPROVED_WORKLOAD_IDENTITY_NAME = "nsrsdp-dev-postgres-serving-mi"
APPROVED_WORKLOAD_OBJECT_ID = "f2a0d95f-c321-4e91-9704-3415e2658a6f"
APPROVED_WORKLOAD_CLIENT_ID = "01d9c356-6731-4c5b-90ba-d78cee192dc4"
_DEFAULT_MIGRATIONS_DIRECTORY = Path(__file__).parents[3] / "sql" / "migrations"


class AccessToken(Protocol):
    token: str


class TokenCredential(Protocol):
    def get_token(self, *scopes: str) -> AccessToken: ...


CredentialFactory = Callable[[], TokenCredential]


@dataclass(frozen=True, slots=True)
class PostgreSQLBootstrapSettings:
    """Required non-secret metadata for the one explicit activation operation."""

    host: str
    database: str
    port: int
    sslmode: str
    bootstrap_identity_name: str
    bootstrap_object_id: str
    bootstrap_postgresql_username: str
    workload_identity_name: str
    workload_object_id: str
    workload_client_id: str
    migrations_directory: Path

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> PostgreSQLBootstrapSettings:
        """Parse and validate explicit bootstrap metadata without acquiring a token."""
        if any(key in environ for key in ("SDPA_POSTGRESQL_PASSWORD", "PGPASSWORD")):
            raise ConfigurationError("PostgreSQL password fallback is prohibited")
        try:
            port = int(environ.get("SDPA_POSTGRESQL_PORT", "5432"))
        except ValueError as error:
            raise ConfigurationError("SDPA_POSTGRESQL_PORT must be an integer") from error
        settings = cls(
            host=environ.get("SDPA_POSTGRESQL_HOST", "").strip(),
            database=environ.get("SDPA_POSTGRESQL_DATABASE", "").strip(),
            port=port,
            sslmode=environ.get("SDPA_POSTGRESQL_SSLMODE", "").strip().lower(),
            bootstrap_identity_name=environ.get(
                "SDPA_POSTGRESQL_BOOTSTRAP_IDENTITY_NAME", ""
            ).strip(),
            bootstrap_object_id=environ.get(
                "SDPA_POSTGRESQL_BOOTSTRAP_IDENTITY_OBJECT_ID", ""
            ).strip(),
            bootstrap_postgresql_username=environ.get(
                "SDPA_POSTGRESQL_BOOTSTRAP_POSTGRESQL_USERNAME", ""
            ).strip(),
            workload_identity_name=environ.get(
                "SDPA_POSTGRESQL_WORKLOAD_IDENTITY_NAME", ""
            ).strip(),
            workload_object_id=environ.get(
                "SDPA_POSTGRESQL_WORKLOAD_IDENTITY_OBJECT_ID", ""
            ).strip(),
            workload_client_id=environ.get(
                "SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID", ""
            ).strip(),
            migrations_directory=Path(
                environ.get(
                    "SDPA_POSTGRESQL_MIGRATIONS_DIRECTORY",
                    str(_DEFAULT_MIGRATIONS_DIRECTORY),
                )
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        required = {
            "SDPA_POSTGRESQL_HOST": self.host,
            "SDPA_POSTGRESQL_DATABASE": self.database,
            "SDPA_POSTGRESQL_SSLMODE": self.sslmode,
            "SDPA_POSTGRESQL_BOOTSTRAP_IDENTITY_NAME": self.bootstrap_identity_name,
            "SDPA_POSTGRESQL_BOOTSTRAP_IDENTITY_OBJECT_ID": self.bootstrap_object_id,
            "SDPA_POSTGRESQL_BOOTSTRAP_POSTGRESQL_USERNAME": (self.bootstrap_postgresql_username),
            "SDPA_POSTGRESQL_WORKLOAD_IDENTITY_NAME": self.workload_identity_name,
            "SDPA_POSTGRESQL_WORKLOAD_IDENTITY_OBJECT_ID": self.workload_object_id,
            "SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID": self.workload_client_id,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ConfigurationError(
                f"missing PostgreSQL bootstrap configuration: {', '.join(missing)}"
            )
        if not 1 <= self.port <= 65535:
            raise ConfigurationError("SDPA_POSTGRESQL_PORT must be between 1 and 65535")
        if self.sslmode != "verify-full":
            raise ConfigurationError("PostgreSQL bootstrap SSL mode must be verify-full")
        approved = (
            (self.bootstrap_identity_name, APPROVED_BOOTSTRAP_IDENTITY_NAME),
            (self.bootstrap_object_id, APPROVED_BOOTSTRAP_OBJECT_ID),
            (
                self.bootstrap_postgresql_username,
                APPROVED_BOOTSTRAP_POSTGRESQL_USERNAME,
            ),
            (self.workload_identity_name, APPROVED_WORKLOAD_IDENTITY_NAME),
            (self.workload_object_id, APPROVED_WORKLOAD_OBJECT_ID),
            (self.workload_client_id, APPROVED_WORKLOAD_CLIENT_ID),
        )
        if any(actual != expected for actual, expected in approved):
            raise ConfigurationError("PostgreSQL bootstrap identities are not Governance-approved")
        if self.bootstrap_object_id == self.workload_object_id:
            raise ConfigurationError("bootstrap and workload identities must be distinct")
        expected_migrations = _DEFAULT_MIGRATIONS_DIRECTORY.resolve()
        if self.migrations_directory.resolve() != expected_migrations:
            raise ConfigurationError(
                "PostgreSQL migrations directory must be the repository authority"
            )
        if not (expected_migrations / "V001__create_relational_serving_foundation.sql").is_file():
            raise ConfigurationError("authoritative PostgreSQL migration is unavailable")


class AzureCliBootstrapTokenProvider:
    """Acquire a token only from an explicit Azure CLI human login."""

    def __init__(
        self,
        bootstrap_identity: EntraIdentity,
        *,
        credential_factory: CredentialFactory | None = None,
    ) -> None:
        if credential_factory is None:
            from azure.identity import AzureCliCredential

            credential_factory = AzureCliCredential
        self._bootstrap_identity = bootstrap_identity
        self._credential = credential_factory()

    def get_token(self, identity: EntraIdentity, scope: str) -> str:
        if identity != self._bootstrap_identity:
            raise ConfigurationError("token acquisition is restricted to the bootstrap identity")
        token = self._credential.get_token(scope).token
        if not token:
            raise ValueError("PostgreSQL bootstrap token must not be empty")
        return token


class PsycopgActivationConnection:
    """Psycopg implementation of the existing activation connection protocol."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def begin(self) -> None:
        self._connection.execute("BEGIN")

    def inspect_history(self) -> Sequence[AppliedMigration]:
        relation = self._connection.execute(
            "SELECT to_regclass('serving.schema_migration_history')"
        ).fetchone()
        if relation is None or relation[0] is None:
            return ()
        rows = self._connection.execute(
            "SELECT version, description, checksum, applied_at "
            "FROM serving.schema_migration_history ORDER BY version"
        ).fetchall()
        return tuple(
            AppliedMigration(int(version), description, checksum, _as_datetime(applied_at))
            for version, description, checksum, applied_at in rows
        )

    def reconcile_principal(self, identity: EntraIdentity, role: str) -> bool:
        existing = self._connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
        ).fetchone()
        if existing is not None:
            return False
        self._connection.execute(
            "SELECT * FROM pgaadauth_create_principal_with_oid(%s, %s, 'service', false, false)",
            (role, identity.object_id),
        )
        return True

    def execute_migration(self, migration: Migration, migration_sql: str) -> None:
        del migration
        self._connection.execute(migration_sql)

    def record_migration(self, migration: Migration, checksum: str) -> None:
        self._connection.execute(
            "INSERT INTO serving.schema_migration_history (version, description, checksum) "
            "VALUES (%s, %s, %s)",
            (migration.version, migration.description, checksum),
        )

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


class PsycopgActivationConnectionFactory:
    """Open activation sessions with the supplied short-lived human Entra token."""

    def __init__(self, port: int, bootstrap_postgresql_username: str) -> None:
        self._port = port
        self._bootstrap_postgresql_username = bootstrap_postgresql_username

    def connect(
        self, target: DevelopmentTarget, identity: EntraIdentity, token: str
    ) -> PostgreSQLActivationConnection:
        return PsycopgActivationConnection(
            psycopg.connect(
                host=target.host,
                dbname=target.database,
                user=self._bootstrap_postgresql_username,
                password=token,
                port=self._port,
                sslmode=target.sslmode,
                autocommit=False,
            )
        )


@dataclass(frozen=True, slots=True)
class PostgreSQLBootstrapRuntime:
    activator: PostgreSQLActivator
    target: DevelopmentTarget
    identities: ActivationIdentities

    def activate(self) -> ActivationResult:
        return self.activator.activate(self.target, self.identities)


def build_postgresql_bootstrap_runtime(
    environ: Mapping[str, str],
    *,
    credential_factory: CredentialFactory | None = None,
    connection_factory: PostgreSQLActivationConnectionFactory | None = None,
) -> PostgreSQLBootstrapRuntime:
    """Compose, but do not execute, the existing governed activator."""
    settings = PostgreSQLBootstrapSettings.from_environment(environ)
    identities = ActivationIdentities(
        bootstrap=EntraIdentity(settings.bootstrap_identity_name, settings.bootstrap_object_id),
        workload=EntraIdentity(settings.workload_identity_name, settings.workload_object_id),
    )
    identities.validate()
    target = DevelopmentTarget(
        environment="development",
        host=settings.host,
        database=settings.database,
        private_connectivity=True,
        sslmode=settings.sslmode,
    )
    target.validate()
    token_provider = AzureCliBootstrapTokenProvider(
        identities.bootstrap, credential_factory=credential_factory
    )
    activation_factory = connection_factory or PsycopgActivationConnectionFactory(
        settings.port, settings.bootstrap_postgresql_username
    )
    activator = PostgreSQLActivator(
        token_provider, activation_factory, settings.migrations_directory.resolve()
    )
    return PostgreSQLBootstrapRuntime(activator, target, identities)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    runtime_builder: Callable[[Mapping[str, str]], PostgreSQLBootstrapRuntime] | None = None,
) -> int:
    """Run activation only after the explicit bootstrap module is invoked."""
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if arguments:
        (stderr or sys.stderr).write("PostgreSQL bootstrap accepts no command arguments\n")
        return 2
    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    try:
        environment = os.environ if environ is None else environ
        runtime = (runtime_builder or build_postgresql_bootstrap_runtime)(environment)
        result = runtime.activate()
    except Exception:
        errors.write("PostgreSQL bootstrap activation failed\n")
        return 2
    json.dump(
        {
            "status": result.status.value,
            "applied_versions": result.applied_versions,
            "previously_applied_versions": result.previously_applied_versions,
            "workload_principal_reconciled": result.workload_principal_reconciled,
        },
        output,
        separators=(",", ":"),
        sort_keys=True,
    )
    output.write("\n")
    return 0


def _as_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("PostgreSQL migration timestamp must be a datetime")
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


if __name__ == "__main__":
    raise SystemExit(main())

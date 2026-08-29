"""Database-independent coordination for governed PostgreSQL schema activation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from .migrations import (
    AppliedMigration,
    Migration,
    MigrationError,
    discover_migrations,
    inspect_migration_state,
    migration_checksum,
)

POSTGRESQL_ENTRA_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"
WORKLOAD_DATABASE_ROLE = "serving_runtime"


class ActivationError(RuntimeError):
    """Raised when activation cannot safely complete."""


class ActivationFailure(ActivationError):
    """Report a failed activation and whether transactional rollback succeeded."""

    def __init__(self, message: str, *, rollback_succeeded: bool) -> None:
        super().__init__(message)
        self.rollback_succeeded = rollback_succeeded


@dataclass(frozen=True, slots=True)
class DevelopmentTarget:
    """Validated development-only, private-connectivity PostgreSQL target metadata."""

    environment: str
    host: str
    database: str
    private_connectivity: bool
    sslmode: str = "verify-full"

    def validate(self) -> None:
        if self.environment != "development":
            raise ActivationError("PostgreSQL activation is restricted to development")
        if not self.private_connectivity:
            raise ActivationError("private PostgreSQL connectivity is required")
        if not self.host.endswith(".postgres.database.azure.com"):
            raise ActivationError("an Azure PostgreSQL DNS host is required")
        if not self.database:
            raise ActivationError("PostgreSQL database must not be empty")
        if self.sslmode != "verify-full":
            raise ActivationError("PostgreSQL TLS verification must use verify-full")


@dataclass(frozen=True, slots=True)
class EntraIdentity:
    """Non-secret identity metadata used for Entra authentication and principal mapping."""

    name: str
    object_id: str

    def validate(self) -> None:
        if not self.name or not self.object_id:
            raise ActivationError("Entra identity name and object ID are required")


@dataclass(frozen=True, slots=True)
class ActivationIdentities:
    """Keep elevated bootstrap and least-privilege workload identities distinct."""

    bootstrap: EntraIdentity
    workload: EntraIdentity

    def validate(self) -> None:
        self.bootstrap.validate()
        self.workload.validate()
        if self.bootstrap.object_id == self.workload.object_id:
            raise ActivationError("bootstrap and workload identities must be distinct")


class EntraTokenProvider(Protocol):
    """Acquire short-lived Entra credential material for one named identity."""

    def get_token(self, identity: EntraIdentity, scope: str) -> str:
        """Return a short-lived token; static application passwords are not supported."""


class PostgreSQLActivationConnection(Protocol):
    """Adapter boundary for bootstrap and schema operations."""

    def begin(self) -> None: ...

    def inspect_history(self) -> Sequence[AppliedMigration]: ...

    def reconcile_principal(self, identity: EntraIdentity, role: str) -> bool: ...

    def execute_migration(self, migration: Migration, sql: str) -> None: ...

    def record_migration(self, migration: Migration, checksum: str) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


class PostgreSQLActivationConnectionFactory(Protocol):
    """Open an activation connection authenticated with a short-lived Entra token."""

    def connect(
        self, target: DevelopmentTarget, identity: EntraIdentity, token: str
    ) -> PostgreSQLActivationConnection: ...


class ActivationStatus(StrEnum):
    ACTIVATED = "ACTIVATED"
    UNCHANGED = "UNCHANGED"


@dataclass(frozen=True, slots=True)
class ActivationResult:
    """Structured audit result emitted only after a successful commit."""

    status: ActivationStatus
    applied_versions: tuple[int, ...]
    previously_applied_versions: tuple[int, ...]
    workload_principal_reconciled: bool


class PostgreSQLActivator:
    """Coordinate idempotent principal bootstrap and deterministic schema activation."""

    def __init__(
        self,
        token_provider: EntraTokenProvider,
        connection_factory: PostgreSQLActivationConnectionFactory,
        migrations_directory: Path,
    ) -> None:
        self._token_provider = token_provider
        self._connection_factory = connection_factory
        self._migrations_directory = migrations_directory

    def activate(
        self, target: DevelopmentTarget, identities: ActivationIdentities
    ) -> ActivationResult:
        target.validate()
        identities.validate()
        migrations = discover_migrations(self._migrations_directory)
        token = self._token_provider.get_token(identities.bootstrap, POSTGRESQL_ENTRA_SCOPE)
        if not token:
            raise ActivationError("Entra bootstrap token must not be empty")

        connection = self._connection_factory.connect(target, identities.bootstrap, token)
        transaction_started = False
        try:
            connection.begin()
            transaction_started = True
            history = tuple(connection.inspect_history())
            state = inspect_migration_state(migrations, history)
            reconciled = connection.reconcile_principal(identities.workload, WORKLOAD_DATABASE_ROLE)
            for migration in state.pending:
                connection.execute_migration(migration, migration.path.read_text(encoding="utf-8"))
                connection.record_migration(migration, migration_checksum(migration))
            connection.commit()
            return ActivationResult(
                status=(
                    ActivationStatus.ACTIVATED if state.pending else ActivationStatus.UNCHANGED
                ),
                applied_versions=tuple(migration.version for migration in state.pending),
                previously_applied_versions=tuple(item.version for item in state.applied),
                workload_principal_reconciled=reconciled,
            )
        except Exception as error:
            rollback_succeeded = not transaction_started
            if transaction_started:
                try:
                    connection.rollback()
                    rollback_succeeded = True
                except Exception:
                    rollback_succeeded = False
            if isinstance(error, ActivationError | MigrationError) and rollback_succeeded:
                raise
            raise ActivationFailure(
                "PostgreSQL activation failed; inspect the cause before retry",
                rollback_succeeded=rollback_succeeded,
            ) from error
        finally:
            connection.close()

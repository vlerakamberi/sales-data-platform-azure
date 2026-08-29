from datetime import UTC, datetime
from pathlib import Path

import pytest

from sales_data_platform_azure.relational.migrations import (
    AppliedMigration,
    MigrationError,
    discover_migrations,
    migration_checksum,
)
from sales_data_platform_azure.relational.postgresql_activation import (
    POSTGRESQL_ENTRA_SCOPE,
    WORKLOAD_DATABASE_ROLE,
    ActivationError,
    ActivationFailure,
    ActivationIdentities,
    ActivationStatus,
    DevelopmentTarget,
    EntraIdentity,
    PostgreSQLActivator,
)


class TokenProvider:
    def __init__(self) -> None:
        self.requests: list[tuple[EntraIdentity, str]] = []

    def get_token(self, identity: EntraIdentity, scope: str) -> str:
        self.requests.append((identity, scope))
        return "short-lived-entra-token"


class Connection:
    def __init__(self, history: tuple[AppliedMigration, ...] = ()) -> None:
        self.history = history
        self.events: list[str] = []
        self.reconciled_identity: EntraIdentity | None = None
        self.fail_version: int | None = None
        self.fail_rollback = False

    def begin(self) -> None:
        self.events.append("begin")

    def inspect_history(self) -> tuple[AppliedMigration, ...]:
        self.events.append("inspect")
        return self.history

    def reconcile_principal(self, identity: EntraIdentity, role: str) -> bool:
        self.events.append(f"reconcile:{role}")
        self.reconciled_identity = identity
        return True

    def execute_migration(self, migration: object, sql: str) -> None:
        version = migration.version  # type: ignore[attr-defined]
        self.events.append(f"execute:{version}")
        assert sql
        if version == self.fail_version:
            raise RuntimeError("database statement failed")

    def record_migration(self, migration: object, checksum: str) -> None:
        version = migration.version  # type: ignore[attr-defined]
        self.events.append(f"record:{version}")
        assert len(checksum) == 64

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")
        if self.fail_rollback:
            raise RuntimeError("rollback failed")

    def close(self) -> None:
        self.events.append("close")


class ConnectionFactory:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        self.arguments: tuple[DevelopmentTarget, EntraIdentity, str] | None = None

    def connect(self, target: DevelopmentTarget, identity: EntraIdentity, token: str) -> Connection:
        self.arguments = (target, identity, token)
        return self.connection


def _target(**overrides: object) -> DevelopmentTarget:
    values = {
        "environment": "development",
        "host": "nsrsdp-dev.postgres.database.azure.com",
        "database": "sales",
        "private_connectivity": True,
    }
    values.update(overrides)
    return DevelopmentTarget(**values)  # type: ignore[arg-type]


def _identities() -> ActivationIdentities:
    return ActivationIdentities(
        bootstrap=EntraIdentity("postgresql-bootstrap", "bootstrap-object-id"),
        workload=EntraIdentity("transformation-workload", "workload-object-id"),
    )


def _migrations(tmp_path: Path, versions: tuple[int, ...] = (1, 2)) -> Path:
    for version in versions:
        (tmp_path / f"V{version:03d}__migration_{version}.sql").write_text(
            f"SELECT {version};\n", encoding="utf-8"
        )
    return tmp_path


def test_development_target_accepts_only_private_verified_development() -> None:
    _target().validate()
    for invalid in (
        {"environment": "production"},
        {"private_connectivity": False},
        {"sslmode": "require"},
        {"host": "localhost"},
    ):
        with pytest.raises(ActivationError):
            _target(**invalid).validate()


def test_entra_bootstrap_and_workload_identities_are_separate(tmp_path: Path) -> None:
    token_provider = TokenProvider()
    connection = Connection()
    factory = ConnectionFactory(connection)
    identities = _identities()

    PostgreSQLActivator(token_provider, factory, _migrations(tmp_path, (1,))).activate(
        _target(), identities
    )

    assert token_provider.requests == [(identities.bootstrap, POSTGRESQL_ENTRA_SCOPE)]
    assert factory.arguments == (_target(), identities.bootstrap, "short-lived-entra-token")
    assert connection.reconciled_identity == identities.workload
    assert f"reconcile:{WORKLOAD_DATABASE_ROLE}" in connection.events
    with pytest.raises(ActivationError, match="distinct"):
        ActivationIdentities(identities.bootstrap, identities.bootstrap).validate()


def test_activation_is_deterministic_and_records_each_migration(tmp_path: Path) -> None:
    connection = Connection()
    activator = PostgreSQLActivator(
        TokenProvider(), ConnectionFactory(connection), _migrations(tmp_path, (2, 1))
    )

    result = activator.activate(_target(), _identities())

    assert result.status is ActivationStatus.ACTIVATED
    assert result.applied_versions == (1, 2)
    assert connection.events == [
        "begin",
        "inspect",
        f"reconcile:{WORKLOAD_DATABASE_ROLE}",
        "execute:1",
        "record:1",
        "execute:2",
        "record:2",
        "commit",
        "close",
    ]


def test_already_applied_history_is_reused_without_sql_execution(tmp_path: Path) -> None:
    directory = _migrations(tmp_path, (1,))
    migration = discover_migrations(directory)[0]
    history = (
        AppliedMigration(
            1, migration.description, migration_checksum(migration), datetime.now(UTC)
        ),
    )
    connection = Connection(history)

    activator = PostgreSQLActivator(TokenProvider(), ConnectionFactory(connection), directory)
    result = activator.activate(_target(), _identities())

    assert result.status is ActivationStatus.UNCHANGED
    assert result.applied_versions == ()
    assert result.previously_applied_versions == (1,)
    assert not any(event.startswith(("execute:", "record:")) for event in connection.events)


@pytest.mark.parametrize("state", ["unknown", "partial", "checksum"])
def test_unknown_or_partial_migration_state_rolls_back(tmp_path: Path, state: str) -> None:
    directory = _migrations(tmp_path, (1, 2))
    first, second = discover_migrations(directory)
    available = {1: first, 2: second}
    version = 3 if state == "unknown" else 2 if state == "partial" else 1
    migration = available.get(version, second)
    checksum = "invalid" if state == "checksum" else migration_checksum(migration)
    history = (AppliedMigration(version, migration.description, checksum, datetime.now(UTC)),)
    connection = Connection(history)

    with pytest.raises(MigrationError):
        PostgreSQLActivator(TokenProvider(), ConnectionFactory(connection), directory).activate(
            _target(), _identities()
        )

    assert connection.events[-2:] == ["rollback", "close"]
    assert not any(event.startswith("reconcile:") for event in connection.events)


def test_statement_failure_rolls_back_and_retry_starts_from_fresh_history(tmp_path: Path) -> None:
    directory = _migrations(tmp_path, (1,))
    failed = Connection()
    failed.fail_version = 1

    with pytest.raises(ActivationFailure) as captured:
        PostgreSQLActivator(TokenProvider(), ConnectionFactory(failed), directory).activate(
            _target(), _identities()
        )
    assert captured.value.rollback_succeeded is True
    assert failed.events[-2:] == ["rollback", "close"]

    retry = Connection()
    result = PostgreSQLActivator(TokenProvider(), ConnectionFactory(retry), directory).activate(
        _target(), _identities()
    )
    assert result.applied_versions == (1,)


def test_failed_rollback_is_explicit_and_no_static_credential_is_accepted(tmp_path: Path) -> None:
    connection = Connection()
    connection.fail_version = 1
    connection.fail_rollback = True
    activator = PostgreSQLActivator(
        TokenProvider(), ConnectionFactory(connection), _migrations(tmp_path, (1,))
    )

    with pytest.raises(ActivationFailure) as captured:
        activator.activate(_target(), _identities())
    assert captured.value.rollback_succeeded is False
    assert "password" not in DevelopmentTarget.__dataclass_fields__
    assert "password" not in ActivationIdentities.__dataclass_fields__

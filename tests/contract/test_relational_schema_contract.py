from datetime import UTC, datetime
from pathlib import Path

import pytest

from sales_data_platform_azure.relational import (
    AppliedMigration,
    MigrationError,
    discover_migrations,
)
from sales_data_platform_azure.relational.migrations import (
    inspect_migration_state,
    migration_checksum,
)

ROOT = Path(__file__).parents[2]
MIGRATIONS = ROOT / "sql/migrations"


def test_initial_migration_is_v001_after_empty_inherited_baseline() -> None:
    migrations = discover_migrations(MIGRATIONS)
    assert [migration.version for migration in migrations] == [1]


def test_activation_history_uses_existing_migration_identity_and_checksum() -> None:
    migrations = discover_migrations(MIGRATIONS)
    migration = migrations[0]
    applied = AppliedMigration(
        migration.version,
        migration.description,
        migration_checksum(migration),
        datetime.now(UTC),
    )

    state = inspect_migration_state(migrations, (applied,))
    assert state.applied == (applied,)
    assert state.pending == ()

    invalid = AppliedMigration(1, migration.description, "changed", datetime.now(UTC))
    with pytest.raises(MigrationError, match="checksum mismatch"):
        inspect_migration_state(migrations, (invalid,))


def test_schema_separates_business_state_attempts_and_minimal_lineage() -> None:
    sql = (MIGRATIONS / "V001__create_relational_serving_foundation.sql").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(sql.lower().split())

    assert "create table serving.sales_transaction" in normalized
    assert "transaction_id text primary key" in normalized
    assert "create table serving.serving_attempt" in normalized
    assert "attempt_id text primary key" in normalized
    assert "execution_id text not null" in normalized
    assert "create table serving.sales_transaction_lineage" in normalized
    assert "primary key (transaction_id, attempt_id)" in normalized
    assert "create table serving.schema_migration_history" in normalized
    assert "rejected" not in normalized
    assert "processing_outcome" not in normalized


def test_adr006_records_approved_runtime_and_network_boundaries() -> None:
    adr = (ROOT / "docs/adr/006-relational-serving-operational-observability.md").read_text(
        encoding="utf-8"
    )
    for required in (
        "STATE B",
        "only `ACCEPTED`",
        "password fallback is prohibited",
        "Connectivity is private only",
        "ADF RunId",
        "commit in one database transaction",
        "Log Analytics",
        "start/stop lifecycle",
    ):
        assert required in adr

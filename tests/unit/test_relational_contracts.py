from datetime import UTC, datetime
from pathlib import Path

import pytest

from sales_data_platform_azure.config import ConfigurationError, PostgreSQLSettings
from sales_data_platform_azure.contracts import ProcessingOutcome, SourceIdentity
from sales_data_platform_azure.relational import (
    AppliedMigration,
    BusinessIdentity,
    Migration,
    MigrationError,
    PersistenceOutcome,
    ServingAttempt,
    ServingLineage,
    discover_migrations,
    is_serving_eligible,
    pending_migrations,
)


@pytest.mark.parametrize(
    ("outcome", "eligible"),
    [
        (ProcessingOutcome.ACCEPTED, True),
        (ProcessingOutcome.REJECTED, False),
        (ProcessingOutcome.FAILED, False),
    ],
)
def test_serving_eligibility(outcome: ProcessingOutcome, eligible: bool) -> None:
    assert is_serving_eligible(outcome) is eligible


def test_business_source_execution_and_attempt_identities_remain_distinct() -> None:
    lineage = ServingLineage(
        BusinessIdentity("tx-001"),
        SourceIdentity("northstar-pos", "batch-001.json", "1.0"),
        ServingAttempt("attempt-1", "adf-run-1", "correlation-1", PersistenceOutcome.PERSISTED),
    )

    assert lineage.business_identity.transaction_id != lineage.attempt.execution_id
    assert lineage.source.object_id != lineage.attempt.attempt_id
    assert lineage.business_identity.transaction_id != "adf-run-1"


def test_postgresql_configuration_is_encrypted_and_password_free() -> None:
    settings = PostgreSQLSettings.from_environment(
        {
            "SDPA_POSTGRESQL_HOST": "private.example.postgres.database.azure.com",
            "SDPA_POSTGRESQL_DATABASE": "sales",
            "SDPA_POSTGRESQL_USER": "serving-job",
            "SDPA_POSTGRESQL_SSLMODE": "verify-full",
        }
    )
    assert settings.port == 5432
    assert settings.sslmode == "verify-full"

    with pytest.raises(ConfigurationError, match="password fallback"):
        PostgreSQLSettings.from_environment(
            {
                "SDPA_POSTGRESQL_HOST": "private.example",
                "SDPA_POSTGRESQL_DATABASE": "sales",
                "SDPA_POSTGRESQL_USER": "serving-job",
                "PGPASSWORD": "prohibited",
            }
        )


def test_migration_discovery_orders_versions_and_rejects_duplicates(tmp_path: Path) -> None:
    (tmp_path / "V002__second.sql").touch()
    (tmp_path / "V001__first.sql").touch()
    assert [migration.version for migration in discover_migrations(tmp_path)] == [1, 2]

    (tmp_path / "V001__duplicate.sql").touch()
    with pytest.raises(MigrationError, match="duplicate"):
        discover_migrations(tmp_path)


def test_migration_filename_and_history_contracts() -> None:
    first = Migration.from_path(Path("V001__foundation.sql"))
    second = Migration.from_path(Path("V002__add_projection.sql"))
    applied = AppliedMigration(1, first.description, "sha256:first", datetime.now(UTC))

    assert pending_migrations((second, first), (applied,)) == (second,)
    with pytest.raises(MigrationError, match="invalid migration filename"):
        Migration.from_path(Path("001-foundation.sql"))
    with pytest.raises(MigrationError, match="unknown"):
        pending_migrations((first,), (AppliedMigration(2, "unknown", "hash", datetime.now(UTC)),))

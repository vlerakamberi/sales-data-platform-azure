from pathlib import Path

ROOT = Path(__file__).parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_activation_is_development_only_private_and_entra_first() -> None:
    activation = _read("src/sales_data_platform_azure/relational/postgresql_activation.py")

    assert 'self.environment != "development"' in activation
    assert "private_connectivity" in activation
    assert 'sslmode: str = "verify-full"' in activation
    assert "POSTGRESQL_ENTRA_SCOPE" in activation
    assert "EntraTokenProvider" in activation
    for prohibited in ("PGPASSWORD", "password=", "public_network", "publicNetworkAccess"):
        assert prohibited not in activation


def test_bootstrap_and_least_privilege_workload_principals_are_separate() -> None:
    activation = _read("src/sales_data_platform_azure/relational/postgresql_activation.py")

    assert "bootstrap: EntraIdentity" in activation
    assert "workload: EntraIdentity" in activation
    assert "bootstrap.object_id == self.workload.object_id" in activation
    assert 'WORKLOAD_DATABASE_ROLE = "serving_runtime"' in activation
    assert "reconcile_principal" in activation
    for prohibited in ("SUPERUSER", "CREATEDB", "CREATEROLE", "azure_pg_admin"):
        assert prohibited not in activation


def test_activation_reuses_the_existing_migration_authority() -> None:
    activation = _read("src/sales_data_platform_azure/relational/postgresql_activation.py")
    migrations = _read("src/sales_data_platform_azure/relational/migrations.py")

    for required in (
        "discover_migrations",
        "inspect_migration_state",
        "migration_checksum",
        "AppliedMigration",
    ):
        assert required in activation
        assert required in migrations
    assert "schema_migration_history" not in activation
    assert "connection.rollback()" in activation
    assert "connection.commit()" in activation


def test_unit95_does_not_cross_unit93_unit94_or_operational_boundaries() -> None:
    activation = _read("src/sales_data_platform_azure/relational/postgresql_activation.py")

    for prohibited in (
        "Microsoft.App",
        "Microsoft.DataFactory",
        "Microsoft.Authorization",
        "managedEnvironments",
        "Container Apps",
        "ADF",
        "trigger",
        "psycopg.connect",
    ):
        assert prohibited not in activation

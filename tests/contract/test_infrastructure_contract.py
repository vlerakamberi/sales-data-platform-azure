import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
BICEP_ROOT = ROOT / "infrastructure" / "bicep"


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_exact_environment_parameter_files_are_distinct() -> None:
    parameter_files = {path.name for path in (BICEP_ROOT / "environments").glob("*.bicepparam")}
    assert parameter_files == {"dev.bicepparam", "prod.bicepparam"}

    development = _read("infrastructure/bicep/environments/dev.bicepparam")
    production = _read("infrastructure/bicep/environments/prod.bicepparam")
    assert "param environment = 'development'" in development
    assert "param environment = 'production'" in production
    assert development != production


def test_expected_modules_are_composed() -> None:
    expected_modules = {
        "container-apps-environment.bicep",
        "container-apps-job.bicep",
        "container-registry.bicep",
        "data-factory.bicep",
        "key-vault.bicep",
        "monitoring.bicep",
        "postgresql.bicep",
        "storage.bicep",
    }
    actual_modules = {path.name for path in (BICEP_ROOT / "modules").glob("*.bicep")}
    assert actual_modules == expected_modules

    composition = _read("infrastructure/bicep/main.bicep")
    for module_name in expected_modules:
        assert f"'modules/{module_name}'" in composition


def test_transformation_job_deployment_is_explicitly_deferred() -> None:
    composition = _read("infrastructure/bicep/main.bicep")
    assert "param deployTransformationJob bool" in composition
    assert (
        "module transformationJob 'modules/container-apps-job.bicep' "
        "= if (deployTransformationJob) {"
    ) in composition

    for environment in ("dev", "prod"):
        parameters = _read(f"infrastructure/bicep/environments/{environment}.bicepparam")
        assert "param deployTransformationJob = false" in parameters


def test_governance_tags_and_outputs_are_present() -> None:
    composition = _read("infrastructure/bicep/main.bicep")
    for tag in ("environment", "managedBy", "repository", "workload"):
        assert f"{tag}:" in composition

    expected_outputs = {
        "containerAppsEnvironmentId",
        "containerRegistryId",
        "curatedContainerName",
        "dataFactoryId",
        "environmentResourceGroupName",
        "keyVaultId",
        "logAnalyticsWorkspaceId",
        "postgresqlServerId",
        "processedContainerName",
        "quarantineContainerName",
        "rawContainerName",
        "storageAccountId",
        "transformationJobId",
    }
    actual_outputs = set(re.findall(r"^output\s+(\w+)\s", composition, flags=re.MULTILINE))
    assert expected_outputs <= actual_outputs


def test_iac_contains_no_role_assignments_or_secret_literals() -> None:
    all_iac = "\n".join(
        path.read_text(encoding="utf-8")
        for path in BICEP_ROOT.rglob("*")
        if path.suffix in {".bicep", ".bicepparam", ".json"}
    )
    assert "Microsoft.Authorization/roleAssignments" not in all_iac
    assert not re.search(
        r"(?i)(password|clientSecret|accessKey|privateKey)\s*=\s*['\"][^'\"]+['\"]",
        all_iac,
    )


def test_storage_preserves_raw_and_separates_quality_failures() -> None:
    storage = _read("infrastructure/bicep/modules/storage.bicep")
    for container in ("raw", "processed", "curated", "quarantine"):
        assert f"name: '{container}'" in storage
    raw_tiering_rule, derived_data_rule = storage.split(
        "name: 'expire-reproducible-derived-data'", maxsplit=1
    )
    assert "name: 'cool-append-oriented-raw-data'" in raw_tiering_rule
    assert "tierToCool:" in raw_tiering_rule
    assert "'blockBlob'" in raw_tiering_rule
    assert "'appendBlob'" not in raw_tiering_rule
    assert "'raw/'" not in derived_data_rule

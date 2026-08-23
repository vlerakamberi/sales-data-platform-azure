import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
BICEP_ROOT = ROOT / "infrastructure" / "bicep"


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_exact_environment_parameter_files_are_distinct() -> None:
    parameter_files = {path.name for path in (BICEP_ROOT / "environments").glob("*.bicepparam")}
    assert parameter_files == {
        "dev.bicepparam",
        "prod.bicepparam",
        "unit7-dev.bicepparam",
        "unit8-dev.bicepparam",
    }

    development = _read("infrastructure/bicep/environments/dev.bicepparam")
    production = _read("infrastructure/bicep/environments/prod.bicepparam")
    assert "param environment = 'development'" in development
    assert "param environment = 'production'" in production
    assert development != production


def test_expected_modules_are_composed() -> None:
    expected_modules = {
        "adf-orchestration-rbac.bicep",
        "adf-orchestration.bicep",
        "container-apps-environment.bicep",
        "container-apps-job.bicep",
        "acr-pull-identity.bicep",
        "container-registry.bicep",
        "data-factory.bicep",
        "key-vault.bicep",
        "identity-rbac.bicep",
        "monitoring.bicep",
        "postgresql.bicep",
        "storage.bicep",
    }
    actual_modules = {path.name for path in (BICEP_ROOT / "modules").glob("*.bicep")}
    assert actual_modules == expected_modules

    composition = _read("infrastructure/bicep/main.bicep")
    dedicated_graph_modules = {
        "acr-pull-identity.bicep",
        "adf-orchestration-rbac.bicep",
        "adf-orchestration.bicep",
    }
    for module_name in expected_modules - dedicated_graph_modules:
        assert f"'modules/{module_name}'" in composition


def test_foundation_job_deployment_is_disabled_for_both_environments() -> None:
    composition = _read("infrastructure/bicep/main.bicep")
    assert "param deployTransformationJob bool" in composition
    assert (
        "module transformationJob 'modules/container-apps-job.bicep' "
        "= if (deployTransformationJob) {"
    ) in composition

    development = _read("infrastructure/bicep/environments/dev.bicepparam")
    production = _read("infrastructure/bicep/environments/prod.bicepparam")
    assert "param deployTransformationJob = false" in development
    assert "param deployTransformationJob = false" in production
    assert re.search(r"unit7-[0-9a-f]{12}'", development)
    assert "latest" not in development


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


def test_iac_contains_no_secret_literals() -> None:
    all_iac = "\n".join(
        path.read_text(encoding="utf-8")
        for path in BICEP_ROOT.rglob("*")
        if path.suffix in {".bicep", ".bicepparam", ".json"}
    )
    assert not re.search(
        r"(?i)(password|clientSecret|accessKey|privateKey)\s*=\s*['\"][^'\"]+['\"]",
        all_iac,
    )


def test_security_module_uses_only_approved_roles_and_exact_resource_scopes() -> None:
    security = _read("infrastructure/bicep/modules/identity-rbac.bicep")
    expected_role_ids = {"ba92f5b4-2d11-453d-a403-e96b0029c9fe"}
    assert set(re.findall(r"'[0-9a-f-]{36}'", security)) == {
        f"'{role_id}'" for role_id in expected_role_ids
    }
    assert "7f951dda-4ed3-4680-a7ca-43fe172d538d" not in security
    assert "scope: rawContainer" in security
    assert "scope: processedContainer" in security
    assert "scope: curatedContainer" in security
    assert "scope: quarantineContainer" in security
    assert "guid(" in security
    for prohibited in ("AcrPush", "Owner", "User Access Administrator"):
        assert prohibited not in security


def test_security_wiring_remains_conditional_on_deferred_job() -> None:
    composition = _read("infrastructure/bicep/main.bicep")
    assert (
        "module identityRbac 'modules/identity-rbac.bicep' = if (deployTransformationJob) {"
        in composition
    )


def test_unit7_job_contract_is_manual_non_secret_and_managed_identity_based() -> None:
    job = _read("infrastructure/bicep/modules/container-apps-job.bicep")
    for contract in (
        "type: 'SystemAssigned'",
        "type: 'SystemAssigned, UserAssigned'",
        "identity: 'system'",
        "replicaRetryLimit: 1",
        "replicaTimeout: 1800",
        "triggerType: 'Manual'",
        "parallelism: 1",
        "replicaCompletionCount: 1",
        "SDPA_ENVIRONMENT",
        "SDPA_STORAGE_ACCOUNT_URL",
        "SDPA_RAW_CONTAINER",
        "SDPA_PROCESSED_CONTAINER",
        "SDPA_CURATED_CONTAINER",
        "SDPA_QUARANTINE_CONTAINER",
    ):
        assert contract in job
    for prohibited in ("scheduleTriggerConfig", "eventTriggerConfig", "secretRef", "password"):
        assert prohibited not in job


def test_unit7_does_not_grant_adf_job_invocation() -> None:
    security = _read("infrastructure/bicep/modules/identity-rbac.bicep")
    assert "dataFactoryPrincipalId" not in security
    assert "Container Apps Jobs Operator" not in security
    assert "b9a307c4-5aa3-4b52-ba60-2b17c136cd7b" not in security


def test_dedicated_unit7_graph_owns_only_hybrid_identity_job_and_exact_rbac() -> None:
    deployment = _read("infrastructure/bicep/unit7-managed-execution.bicep")
    parameters = _read("infrastructure/bicep/environments/unit7-dev.bicepparam")
    pull_identity = _read("infrastructure/bicep/modules/acr-pull-identity.bicep")
    workload_rbac = _read("infrastructure/bicep/modules/identity-rbac.bicep")
    job = _read("infrastructure/bicep/modules/container-apps-job.bicep")

    for existing_type in (
        "Microsoft.ContainerRegistry/registries@2025-04-01",
        "Microsoft.Storage/storageAccounts@2025-06-01",
        "Microsoft.App/managedEnvironments@2025-07-01",
    ):
        assert f"{existing_type}' existing" in deployment
    for prohibited in (
        "Microsoft.DBforPostgreSQL",
        "Microsoft.DataFactory",
        "Microsoft.KeyVault",
        "Microsoft.OperationalInsights",
        "managementPolicies",
    ):
        assert prohibited not in deployment

    assert "nsrsdp-dev-transform-acr-pull-mi" in parameters
    assert "nsrsdp-dev-transformation:unit7-13cd4410b8e2" in parameters
    assert "7f951dda-4ed3-4680-a7ca-43fe172d538d" in pull_identity
    assert "ba92f5b4-2d11-453d-a403-e96b0029c9fe" not in pull_identity
    assert pull_identity.count("Microsoft.Authorization/roleAssignments") == 1
    assert workload_rbac.count("Microsoft.Authorization/roleAssignments") == 4
    assert "7f951dda-4ed3-4680-a7ca-43fe172d538d" not in workload_rbac
    for scope in ("rawContainer", "processedContainer", "curatedContainer", "quarantineContainer"):
        assert f"scope: {scope}" in workload_rbac

    assert "registryIdentityId: acrPullIdentity.outputs.identityId" in deployment
    assert "identity: registryIdentityId" in job
    assert "lifecycle: 'Main'" in job
    assert "lifecycle: 'None'" in job
    assert "transformationPrincipalId: transformationJob.outputs.principalId" in deployment

    all_unit7 = "\n".join((deployment, parameters, pull_identity, workload_rbac, job))
    for prohibited in (
        "AcrPush",
        "Container Apps Jobs Operator",
        "User Access Administrator",
        "b9a307c4-5aa3-4b52-ba60-2b17c136cd7b",
    ):
        assert prohibited not in all_unit7


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

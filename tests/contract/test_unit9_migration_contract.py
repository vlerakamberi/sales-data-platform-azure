import hashlib
from pathlib import Path

ROOT = Path(__file__).parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_unit9_migration_creates_a_parallel_job_in_the_replacement_environment() -> None:
    deployment = _read("infrastructure/bicep/unit9-migration.bicep")
    parameters = _read("infrastructure/bicep/environments/unit9-migration-dev.bicepparam")

    assert "Microsoft.App/managedEnvironments@2025-07-01' existing" in deployment
    assert "managedEnvironmentId: replacementContainerAppsEnvironment.id" in deployment
    assert "module replacementTransformationJob 'modules/container-apps-job.bicep'" in deployment
    assert "replacementContainerAppsEnvironmentName = 'nsrsdp-dev-network-cae'" in parameters
    assert "replacementJobName = 'nsrsdp-dev-transform-job-vnet'" in parameters
    assert "nsrsdp-dev-transform-job'" not in parameters


def test_unit9_migration_reuses_the_pinned_image_and_acr_pull_identity() -> None:
    deployment = _read("infrastructure/bicep/unit9-migration.bicep")
    parameters = _read("infrastructure/bicep/environments/unit9-migration-dev.bicepparam")

    assert "Microsoft.ContainerRegistry/registries@2025-04-01' existing" in deployment
    assert "Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' existing" in deployment
    assert "registryIdentityId: acrPullIdentity.id" in deployment
    assert "imageName: '${registry.properties.loginServer}/${imageName}'" in deployment
    assert "acrPullIdentityName = 'nsrsdp-dev-transform-acr-pull-mi'" in parameters
    assert "imageName = 'nsrsdp-dev-transformation:unit7-13cd4410b8e2'" in parameters
    assert "latest" not in parameters


def test_unit9_migration_reconciles_exact_storage_access_for_the_new_principal() -> None:
    deployment = _read("infrastructure/bicep/unit9-migration.bicep")
    rbac = _read("infrastructure/bicep/modules/identity-rbac.bicep")

    assert (
        "transformationPrincipalId: replacementTransformationJob.outputs.principalId" in deployment
    )
    assert "module replacementWorkloadStorageRbac 'modules/identity-rbac.bicep'" in deployment
    assert rbac.count("Microsoft.Authorization/roleAssignments@2022-04-01") == 4
    assert "ba92f5b4-2d11-453d-a403-e96b0029c9fe" in rbac
    for scope in ("rawContainer", "processedContainer", "curatedContainer", "quarantineContainer"):
        assert f"scope: {scope}" in rbac


def test_unit9_migration_has_no_cutover_or_unrelated_resource_ownership() -> None:
    deployment = _read("infrastructure/bicep/unit9-migration.bicep")

    for prohibited in (
        "Microsoft.DataFactory",
        "Microsoft.DBforPostgreSQL",
        "factories/triggers",
        "managedEnvironments@2025-07-01' =",
        "container-apps-environment.bicep",
        "postgresql",
        "delete",
    ):
        assert prohibited.casefold() not in deployment.casefold()


def test_unit9_migration_preserves_governed_runtime_artifacts() -> None:
    expected = {
        "infrastructure/bicep/modules/container-apps-job.bicep": (
            "f2aea0f990dfa903f58f76b0a907535b55b4b34df97aca22a47d6fc26644e3bd"
        ),
        "infrastructure/bicep/modules/identity-rbac.bicep": (
            "22c69a78b0e910bb94dfdc151ded6dd61a2fcd76432e9b3ca711c730eb86c4ea"
        ),
        "orchestration/adf/pipelines/northstar-sales-orchestration.json": (
            "1a338e3454b38f0d80743cfcd9beda823be28601fefbb5cfec95238b2f0b8fa7"
        ),
        "orchestration/adf/triggers/northstar-sales-schedule.json": (
            "26d21fdc855cf6c0451d68a2491ee34b0ef9d72c93bd6458eec4fe6417b5f004"
        ),
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest

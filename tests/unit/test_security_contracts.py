from dataclasses import fields

import pytest

from sales_data_platform_azure.config import (
    ApprovedRole,
    KeyVaultSecretReference,
    ManagedIdentityType,
    ResourceScope,
    ResourceType,
    RoleRelationship,
    SecurityEnvironment,
    Workload,
    WorkloadIdentity,
)


def _identity(
    environment: SecurityEnvironment = SecurityEnvironment.DEV,
    workload: Workload = Workload.TRANSFORMATION,
) -> WorkloadIdentity:
    return WorkloadIdentity(environment, workload)


def _scope(
    resource_type: ResourceType,
    environment: SecurityEnvironment = SecurityEnvironment.DEV,
) -> ResourceScope:
    return ResourceScope(environment, resource_type, "nsrsdp-dev-resource")


def test_only_dev_prod_system_assigned_workload_identities_are_supported() -> None:
    assert [item.value for item in SecurityEnvironment] == ["dev", "prod"]
    assert [item.value for item in ManagedIdentityType] == ["SystemAssigned"]
    assert [item.value for item in Workload] == ["data-factory", "transformation"]
    with pytest.raises(ValueError):
        SecurityEnvironment("staging")
    with pytest.raises(ValueError):
        ManagedIdentityType("UserAssigned")


def test_environment_specific_workload_identities_are_not_shared() -> None:
    dev = _identity(SecurityEnvironment.DEV)
    prod = _identity(SecurityEnvironment.PROD)
    assert dev.logical_id == "dev:transformation:system"
    assert prod.logical_id == "prod:transformation:system"
    assert dev.logical_id != prod.logical_id


def test_approved_role_classes_are_exact() -> None:
    assert {role.value for role in ApprovedRole} == {
        "AcrPull",
        "Storage Blob Data Contributor",
        "Key Vault Secrets User",
        "Container Apps Jobs Operator",
    }
    for role in ("Owner", "Contributor", "User Access Administrator", "AcrPush"):
        with pytest.raises(ValueError):
            ApprovedRole(role)


@pytest.mark.parametrize(
    ("workload", "role", "resource_type"),
    [
        (Workload.TRANSFORMATION, ApprovedRole.ACR_PULL, ResourceType.CONTAINER_REGISTRY),
        (
            Workload.TRANSFORMATION,
            ApprovedRole.STORAGE_BLOB_DATA_CONTRIBUTOR,
            ResourceType.STORAGE_CONTAINER,
        ),
        (
            Workload.TRANSFORMATION,
            ApprovedRole.KEY_VAULT_SECRETS_USER,
            ResourceType.KEY_VAULT,
        ),
        (
            Workload.DATA_FACTORY,
            ApprovedRole.CONTAINER_APPS_JOBS_OPERATOR,
            ResourceType.CONTAINER_APPS_JOB,
        ),
    ],
)
def test_exact_approved_relationships(
    workload: Workload, role: ApprovedRole, resource_type: ResourceType
) -> None:
    relationship = RoleRelationship(
        _identity(workload=workload), role, _scope(resource_type), "bounded requirement"
    )
    assert relationship.scope.resource_type is resource_type


def test_cross_environment_role_relationship_is_rejected() -> None:
    with pytest.raises(ValueError, match="cross-environment"):
        RoleRelationship(
            _identity(SecurityEnvironment.DEV),
            ApprovedRole.ACR_PULL,
            _scope(ResourceType.CONTAINER_REGISTRY, SecurityEnvironment.PROD),
            "invalid cross-environment access",
        )


@pytest.mark.parametrize(
    ("workload", "role", "resource_type"),
    [
        (Workload.DATA_FACTORY, ApprovedRole.ACR_PULL, ResourceType.CONTAINER_REGISTRY),
        (
            Workload.DATA_FACTORY,
            ApprovedRole.STORAGE_BLOB_DATA_CONTRIBUTOR,
            ResourceType.STORAGE_CONTAINER,
        ),
        (
            Workload.TRANSFORMATION,
            ApprovedRole.CONTAINER_APPS_JOBS_OPERATOR,
            ResourceType.CONTAINER_APPS_JOB,
        ),
        (Workload.TRANSFORMATION, ApprovedRole.ACR_PULL, ResourceType.KEY_VAULT),
    ],
)
def test_role_on_wrong_principal_or_scope_is_rejected(
    workload: Workload, role: ApprovedRole, resource_type: ResourceType
) -> None:
    with pytest.raises(ValueError, match="not approved"):
        RoleRelationship(
            _identity(workload=workload), role, _scope(resource_type), "invalid relationship"
        )


def test_broad_scope_types_cannot_be_constructed() -> None:
    for broad_scope in ("subscription", "resource-group"):
        with pytest.raises(ValueError):
            ResourceType(broad_scope)
    with pytest.raises(ValueError):
        ResourceScope(SecurityEnvironment.DEV, ResourceType.KEY_VAULT, "../prod-vault")


def test_relationship_requires_an_architectural_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        RoleRelationship(
            _identity(), ApprovedRole.ACR_PULL, _scope(ResourceType.CONTAINER_REGISTRY), " "
        )


def test_key_vault_reference_contains_metadata_but_no_secret_value() -> None:
    reference = KeyVaultSecretReference(
        SecurityEnvironment.DEV,
        "nsrsdp-dev-vault",
        "approved-secret-name",
        "future approved workload configuration",
    )
    assert reference.environment is SecurityEnvironment.DEV
    assert "value" not in {field.name for field in fields(reference)}


@pytest.mark.parametrize(
    ("vault_name", "secret_name", "purpose"),
    [
        ("Prod-Vault", "secret", "purpose"),
        ("dev-vault", "../secret", "purpose"),
        ("dev-vault", "secret", ""),
    ],
)
def test_invalid_key_vault_reference_metadata_is_rejected(
    vault_name: str, secret_name: str, purpose: str
) -> None:
    with pytest.raises(ValueError):
        KeyVaultSecretReference(SecurityEnvironment.DEV, vault_name, secret_name, purpose)

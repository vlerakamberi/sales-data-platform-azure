"""Secret-free, environment-isolated workload security contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_IDENTIFIER = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")


class SecurityEnvironment(StrEnum):
    """Governed security environments."""

    DEV = "dev"
    PROD = "prod"


class Workload(StrEnum):
    """Approved workload identity owners."""

    DATA_FACTORY = "data-factory"
    TRANSFORMATION = "transformation"


class ManagedIdentityType(StrEnum):
    """The only approved workload identity type."""

    SYSTEM_ASSIGNED = "SystemAssigned"


class ApprovedRole(StrEnum):
    """Built-in roles approved for bounded Unit 5 relationships."""

    ACR_PULL = "AcrPull"
    STORAGE_BLOB_DATA_CONTRIBUTOR = "Storage Blob Data Contributor"
    KEY_VAULT_SECRETS_USER = "Key Vault Secrets User"
    CONTAINER_APPS_JOBS_OPERATOR = "Container Apps Jobs Operator"


class ResourceType(StrEnum):
    """Precise resource types accepted as role-assignment scopes."""

    CONTAINER_REGISTRY = "container-registry"
    STORAGE_CONTAINER = "storage-container"
    KEY_VAULT = "key-vault"
    CONTAINER_APPS_JOB = "container-apps-job"


@dataclass(frozen=True, slots=True)
class WorkloadIdentity:
    """An environment-owned system-assigned identity definition."""

    environment: SecurityEnvironment
    workload: Workload
    identity_type: ManagedIdentityType = ManagedIdentityType.SYSTEM_ASSIGNED

    @property
    def logical_id(self) -> str:
        """Return an environment-specific identity key; identities are never shared."""
        return f"{self.environment.value}:{self.workload.value}:system"


@dataclass(frozen=True, slots=True)
class ResourceScope:
    """An exact environment-specific resource scope, never a group or subscription."""

    environment: SecurityEnvironment
    resource_type: ResourceType
    resource_name: str

    def __post_init__(self) -> None:
        _validate_identifier(self.resource_name, "resource_name")


@dataclass(frozen=True, slots=True)
class RoleRelationship:
    """A validated principal-to-role-to-resource security relationship."""

    principal: WorkloadIdentity
    role: ApprovedRole
    scope: ResourceScope
    reason: str

    def __post_init__(self) -> None:
        if self.principal.environment is not self.scope.environment:
            raise ValueError("cross-environment role relationships are prohibited")
        if not self.reason.strip():
            raise ValueError("role relationship reason must be non-empty")
        expected = {
            ApprovedRole.ACR_PULL: (Workload.TRANSFORMATION, ResourceType.CONTAINER_REGISTRY),
            ApprovedRole.STORAGE_BLOB_DATA_CONTRIBUTOR: (
                Workload.TRANSFORMATION,
                ResourceType.STORAGE_CONTAINER,
            ),
            ApprovedRole.KEY_VAULT_SECRETS_USER: (
                Workload.TRANSFORMATION,
                ResourceType.KEY_VAULT,
            ),
            ApprovedRole.CONTAINER_APPS_JOBS_OPERATOR: (
                Workload.DATA_FACTORY,
                ResourceType.CONTAINER_APPS_JOB,
            ),
        }[self.role]
        if (self.principal.workload, self.scope.resource_type) != expected:
            raise ValueError("role is not approved for this principal and exact scope type")


@dataclass(frozen=True, slots=True)
class KeyVaultSecretReference:
    """Secret metadata only; deliberately has no field for secret values."""

    environment: SecurityEnvironment
    vault_name: str
    secret_name: str
    purpose: str

    def __post_init__(self) -> None:
        _validate_identifier(self.vault_name, "vault_name")
        _validate_identifier(self.secret_name, "secret_name")
        if not self.purpose.strip():
            raise ValueError("secret reference purpose must be non-empty")


def _validate_identifier(value: object, name: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a safe lowercase logical identifier")

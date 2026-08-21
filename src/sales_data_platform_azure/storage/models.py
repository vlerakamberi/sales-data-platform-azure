"""Cloud-neutral contracts for governed data-layer objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sales_data_platform_azure.contracts import SourceIdentity


class StorageEnvironment(StrEnum):
    """Governed deployment environments."""

    DEV = "dev"
    PROD = "prod"


class DataLayer(StrEnum):
    """Governed logical data layers."""

    RAW = "raw"
    PROCESSED = "processed"
    CURATED = "curated"
    QUARANTINE = "quarantine"


@dataclass(frozen=True, slots=True)
class ObjectLocation:
    """A logical object address, independent of any cloud account or endpoint."""

    environment: StorageEnvironment
    layer: DataLayer
    address: str


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    """Governed identity, content, and processing metadata for one object."""

    source: SourceIdentity
    dataset: str
    format: str
    contract_version: str
    checksum: str | None = None
    record_count: int | None = None
    execution_id: str | None = None
    correlation_id: str | None = None
    failed_expectation_ids: tuple[str, ...] = ()
    rejection_classification: str | None = None
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class StorageObject:
    """A cloud-neutral logical object and its lineage metadata."""

    location: ObjectLocation
    metadata: ObjectMetadata

    @property
    def is_immutable_source(self) -> bool:
        """Raw objects are immutable source boundaries, never mutable destinations."""
        return self.location.layer is DataLayer.RAW

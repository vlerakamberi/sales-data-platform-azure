"""Canonical contracts for deterministic local transformation executions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sales_data_platform_azure.quality import QualityResult


class ProcessingOutcome(StrEnum):
    """Governed outcome of a transformation request."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ArtifactType(StrEnum):
    """Logical output disposition; never a fabricated cloud location."""

    CURATED_SALES_BATCH = "CURATED_SALES_BATCH"
    QUARANTINE_SALES_BATCH = "QUARANTINE_SALES_BATCH"


class FailureClassification(StrEnum):
    """Safe, stable execution-failure categories."""

    MALFORMED_INPUT = "MALFORMED_INPUT"
    UNSUPPORTED_CONTRACT = "UNSUPPORTED_CONTRACT"
    TRANSFORMATION_INVARIANT = "TRANSFORMATION_INVARIANT"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    UNEXPECTED_RUNTIME = "UNEXPECTED_RUNTIME"


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    """Immutable logical identity of an input, independent from an execution."""

    source_id: str
    object_id: str
    contract_version: str
    version: str | None = None
    checksum: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Trace identity for one attempt to process a logical source."""

    execution_id: str
    correlation_id: str
    source: SourceIdentity


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    """Content-addressed metadata for a logical local result artifact."""

    artifact_type: ArtifactType
    disposition: str
    record_count: int
    contract_version: str
    checksum: str
    source: SourceIdentity


@dataclass(frozen=True, slots=True)
class TransformationResult:
    """Explicit accepted, rejected, or failed runtime result."""

    execution_id: str
    correlation_id: str
    source: SourceIdentity
    outcome: ProcessingOutcome
    artifact: ArtifactMetadata | None = None
    records: tuple[dict[str, Any], ...] = ()
    quality_results: tuple[QualityResult, ...] = ()
    failed_expectation_ids: tuple[str, ...] = ()
    failure_classification: FailureClassification | None = None
    diagnostic: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation with stable enum values."""
        result = asdict(self)
        result["outcome"] = self.outcome.value
        if self.artifact:
            result["artifact"]["artifact_type"] = self.artifact.artifact_type.value
        if self.failure_classification:
            result["failure_classification"] = self.failure_classification.value
        for quality_result, serialized in zip(
            self.quality_results, result["quality_results"], strict=True
        ):
            serialized["severity"] = quality_result.severity.value
        return result

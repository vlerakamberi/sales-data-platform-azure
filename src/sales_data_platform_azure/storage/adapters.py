"""Bounded mappings from Unit 3 runtime results to Unit 4 storage contracts."""

from __future__ import annotations

from datetime import date

from sales_data_platform_azure.contracts import ProcessingOutcome, TransformationResult

from .models import DataLayer, ObjectMetadata, StorageEnvironment, StorageObject
from .paths import PathRequest, build_object_location


def storage_object_from_result(
    result: TransformationResult,
    *,
    environment: StorageEnvironment | str,
    dataset: str,
    partition_date: date,
    format: str = "json",
) -> StorageObject:
    """Map an accepted or rejected Unit 3 result without changing Unit 3 contracts."""
    if result.artifact is None or result.outcome is ProcessingOutcome.FAILED:
        raise ValueError("failed transformations do not produce storage objects")

    layer = (
        DataLayer.QUARANTINE if result.outcome is ProcessingOutcome.REJECTED else DataLayer.CURATED
    )
    location = build_object_location(
        PathRequest(
            environment=environment,
            layer=layer,
            source_system=result.source.source_id,
            dataset=dataset,
            partition_date=partition_date,
            stable_object_identity=result.artifact.checksum,
            execution_id=result.execution_id if layer is DataLayer.QUARANTINE else None,
            format=format,
        )
    )
    return StorageObject(
        location=location,
        metadata=ObjectMetadata(
            source=result.source,
            dataset=dataset,
            format=format.removeprefix(".").lower(),
            contract_version=result.artifact.contract_version,
            checksum=result.artifact.checksum,
            record_count=result.artifact.record_count,
            execution_id=result.execution_id,
            correlation_id=result.correlation_id,
            failed_expectation_ids=result.failed_expectation_ids,
            rejection_classification=(
                "DATA_QUALITY_REJECTION" if layer is DataLayer.QUARANTINE else None
            ),
            rejection_reason=(
                "blocking data quality expectations failed"
                if layer is DataLayer.QUARANTINE
                else None
            ),
        ),
    )

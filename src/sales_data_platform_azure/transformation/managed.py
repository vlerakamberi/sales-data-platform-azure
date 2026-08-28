"""Managed-identity ADLS adapter for one governed transformation execution."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from sales_data_platform_azure.contracts import (
    ExecutionContext,
    FailureClassification,
    ProcessingOutcome,
    TransformationResult,
)
from sales_data_platform_azure.relational import RelationalServingError, RelationalServingService
from sales_data_platform_azure.storage import (
    DataLayer,
    PathRequest,
    StorageEnvironment,
    build_object_location,
    storage_object_from_result,
)

from .runtime import transform_sales_batch

_LOGGER = logging.getLogger("sales_data_platform_azure.transformation.managed")


class BlobStore(Protocol):
    """Small data-plane boundary used by the managed runner and local tests."""

    def download_text(self, container: str, object_name: str) -> str: ...

    def upload_text(self, container: str, object_name: str, content: str) -> None: ...


@dataclass(frozen=True, slots=True)
class ManagedExecutionRequest:
    environment: StorageEnvironment
    raw_container: str
    processed_container: str
    curated_container: str
    quarantine_container: str
    input_blob: str
    dataset: str
    partition_date: date
    context: ExecutionContext


class AzureBlobStore:
    """Azure Blob data-plane client authenticated only by the Job managed identity."""

    def __init__(self, account_url: str) -> None:
        from azure.identity import ManagedIdentityCredential
        from azure.storage.blob import BlobServiceClient

        self._credential = ManagedIdentityCredential()
        self._service = BlobServiceClient(account_url, credential=self._credential)

    def download_text(self, container: str, object_name: str) -> str:
        payload = self._service.get_blob_client(container, object_name).download_blob().readall()
        return payload.decode("utf-8")

    def upload_text(self, container: str, object_name: str, content: str) -> None:
        self._service.get_blob_client(container, object_name).upload_blob(
            content.encode("utf-8"), overwrite=True
        )


def execute_managed(
    request: ManagedExecutionRequest,
    store: BlobStore,
    relational_serving: RelationalServingService | None = None,
    *,
    attempt_id_factory: Callable[[], str] | None = None,
) -> TransformationResult:
    """Read immutable raw input and persist governed outputs without mutating raw."""
    try:
        payload = store.download_text(request.raw_container, request.input_blob)
        result = transform_sales_batch(payload, request.context)
        if result.outcome is ProcessingOutcome.FAILED:
            return result

        serialized_records = json.dumps(result.records, separators=(",", ":"), sort_keys=True)
        processed = build_object_location(
            PathRequest(
                environment=request.environment,
                layer=DataLayer.PROCESSED,
                source_system=result.source.source_id,
                dataset=request.dataset,
                partition_date=request.partition_date,
                stable_object_identity=result.artifact.checksum,
                format="json",
            )
        )
        destination = storage_object_from_result(
            result,
            environment=request.environment,
            dataset=request.dataset,
            partition_date=request.partition_date,
        )
        store.upload_text(request.processed_container, processed.address, serialized_records)
        destination_container = (
            request.quarantine_container
            if result.outcome is ProcessingOutcome.REJECTED
            else request.curated_container
        )
        store.upload_text(destination_container, destination.location.address, serialized_records)
        if result.outcome is ProcessingOutcome.ACCEPTED and relational_serving is not None:
            attempt_id = (attempt_id_factory or _new_attempt_id)()
            try:
                relational_serving.serve(
                    result,
                    environment=request.environment.value,
                    dataset=request.dataset,
                    attempt_id=attempt_id,
                )
            except RelationalServingError:
                return TransformationResult(
                    execution_id=result.execution_id,
                    correlation_id=result.correlation_id,
                    source=result.source,
                    outcome=ProcessingOutcome.FAILED,
                    failure_classification=FailureClassification.RELATIONAL_SERVING_FAILED,
                    diagnostic="relational serving failed",
                )
        _LOGGER.info(
            "managed storage persistence completed",
            extra={"stage": "persistence", "outcome": result.outcome.value},
        )
        return result
    except Exception:
        _LOGGER.exception(
            "managed storage execution failed",
            extra={
                "stage": "storage",
                "outcome": ProcessingOutcome.FAILED.value,
                "failure_classification": FailureClassification.UNEXPECTED_RUNTIME.value,
            },
        )
        return TransformationResult(
            execution_id=request.context.execution_id,
            correlation_id=request.context.correlation_id,
            source=request.context.source,
            outcome=ProcessingOutcome.FAILED,
            failure_classification=FailureClassification.UNEXPECTED_RUNTIME,
            diagnostic="managed storage execution failed",
        )


def _new_attempt_id() -> str:
    return f"serving-{uuid.uuid4()}"

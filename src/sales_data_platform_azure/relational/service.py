"""Serving eligibility, safe observability, and failure boundary."""

from __future__ import annotations

import logging
from typing import Protocol

from sales_data_platform_azure.contracts import FailureClassification, TransformationResult
from sales_data_platform_azure.logging import correlation_context

from .models import PersistenceResult
from .repository import RelationalServingError

_LOGGER = logging.getLogger("sales_data_platform_azure.relational.serving")


class ServingRepository(Protocol):
    """Atomic persistence boundary used by the application service."""

    def persist(self, result: TransformationResult, attempt_id: str) -> PersistenceResult: ...


class RelationalServingService:
    """Persist accepted results and emit allowlisted serving lifecycle events."""

    def __init__(self, repository: ServingRepository) -> None:
        self._repository = repository

    def serve(
        self,
        result: TransformationResult,
        *,
        environment: str,
        dataset: str,
        attempt_id: str,
    ) -> PersistenceResult:
        """Serve one accepted batch, propagating safe technical failures."""
        with correlation_context(
            execution_id=result.execution_id, correlation_id=result.correlation_id
        ):
            fields = _event_fields(result, environment, dataset, attempt_id)
            _emit_for_transactions("RELATIONAL_SERVING_STARTED", result, fields)
            try:
                persisted = self._repository.persist(result, attempt_id)
            except Exception as error:
                failed_fields = {
                    **fields,
                    "persistence_outcome": "FAILED",
                    "failure_classification": FailureClassification.RELATIONAL_SERVING_FAILED.value,
                    "diagnostic_category": "RELATIONAL_TRANSACTION_FAILED",
                }
                _emit_for_transactions(
                    "RELATIONAL_SERVING_FAILED", result, failed_fields, level=logging.ERROR
                )
                if isinstance(error, RelationalServingError):
                    raise
                raise RelationalServingError("relational serving failed") from error

            succeeded_fields = {**fields, "persistence_outcome": persisted.attempt.outcome.value}
            _emit_for_transactions("RELATIONAL_SERVING_SUCCEEDED", result, succeeded_fields)
            return persisted


def _event_fields(
    result: TransformationResult, environment: str, dataset: str, attempt_id: str
) -> dict[str, str]:
    return {
        "stage": "relational_serving",
        "environment": environment,
        "dataset": dataset,
        "source_id": result.source.source_id,
        "source_object_id": result.source.object_id,
        "attempt_id": attempt_id,
    }


def _emit_for_transactions(
    event: str,
    result: TransformationResult,
    fields: dict[str, str],
    *,
    level: int = logging.INFO,
) -> None:
    for record in result.records:
        _LOGGER.log(
            level,
            event,
            extra={**fields, "event": event, "transaction_id": record["transaction_id"]},
        )

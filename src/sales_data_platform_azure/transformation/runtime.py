"""Deterministic Northstar sales transformation and quality decision boundary."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sales_data_platform_azure.contracts import (
    ArtifactMetadata,
    ArtifactType,
    ExecutionContext,
    FailureClassification,
    ProcessingOutcome,
    SourceIdentity,
    TransformationResult,
)
from sales_data_platform_azure.logging import correlation_context
from sales_data_platform_azure.quality import QualitySeverity, evaluate_sales_batch

from .models import SalesTransaction

SUPPORTED_CONTRACT_VERSION = "1.0"
_LOGGER = logging.getLogger("sales_data_platform_azure.transformation")
_UNKNOWN_SOURCE = SourceIdentity("unknown", "unknown", "unknown")


class TransformationFailure(ValueError):
    """Expected, safely classifiable transformation failure."""

    def __init__(self, classification: FailureClassification, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.classification = classification
        self.diagnostic = diagnostic


def transform_sales_batch(payload: str, context: ExecutionContext) -> TransformationResult:
    """Transform one raw logical batch without persistence or cloud side effects."""
    with correlation_context(
        execution_id=context.execution_id, correlation_id=context.correlation_id
    ):
        _LOGGER.info("sales transformation started", extra={"stage": "parse"})
        try:
            document = _parse_document(payload)
            source = _parse_and_verify_source(document, context.source)
            records = _parse_records(document)
            business_records = tuple(record.to_business_dict() for record in records)
            quality_results = evaluate_sales_batch(records)
            failed_expectations = tuple(
                sorted(
                    {
                        result.expectation_id
                        for result in quality_results
                        if not result.passed and result.severity is QualitySeverity.BLOCKING
                    }
                )
            )
            outcome = (
                ProcessingOutcome.REJECTED if failed_expectations else ProcessingOutcome.ACCEPTED
            )
            artifact = _artifact(source, outcome, business_records)
            _LOGGER.info(
                "sales transformation completed",
                extra={
                    "stage": "quality_decision",
                    "outcome": outcome.value,
                    "failed_expectation_ids": failed_expectations,
                },
            )
            return TransformationResult(
                execution_id=context.execution_id,
                correlation_id=context.correlation_id,
                source=source,
                outcome=outcome,
                artifact=artifact,
                records=business_records,
                quality_results=quality_results,
                failed_expectation_ids=failed_expectations,
            )
        except TransformationFailure as error:
            return _failed_result(context, error.classification, error.diagnostic)
        except Exception:
            _LOGGER.exception(
                "sales transformation failed unexpectedly",
                extra={
                    "stage": "runtime",
                    "outcome": ProcessingOutcome.FAILED.value,
                    "failure_classification": FailureClassification.UNEXPECTED_RUNTIME.value,
                },
            )
            return TransformationResult(
                execution_id=context.execution_id,
                correlation_id=context.correlation_id,
                source=context.source,
                outcome=ProcessingOutcome.FAILED,
                failure_classification=FailureClassification.UNEXPECTED_RUNTIME,
                diagnostic="unexpected runtime failure",
            )


def _parse_document(payload: str) -> dict[str, Any]:
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise TransformationFailure(
            FailureClassification.MALFORMED_INPUT, "input is not valid JSON"
        ) from error
    if not isinstance(document, dict):
        raise TransformationFailure(
            FailureClassification.MALFORMED_INPUT, "input root must be an object"
        )
    return document


def _parse_and_verify_source(
    document: dict[str, Any], expected_source: SourceIdentity
) -> SourceIdentity:
    contract_version = document.get("contract_version")
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise TransformationFailure(
            FailureClassification.UNSUPPORTED_CONTRACT,
            f"supported contract version is {SUPPORTED_CONTRACT_VERSION}",
        )
    source_data = document.get("source")
    if not isinstance(source_data, dict):
        raise TransformationFailure(
            FailureClassification.MALFORMED_INPUT, "source must be an object"
        )
    try:
        source = SourceIdentity(
            source_id=_required_text(source_data, "source_id"),
            object_id=_required_text(source_data, "object_id"),
            contract_version=contract_version,
            version=_optional_text(source_data, "version"),
            checksum=_optional_text(source_data, "checksum"),
        )
    except (TypeError, ValueError) as error:
        raise TransformationFailure(
            FailureClassification.MALFORMED_INPUT, "source identity is invalid"
        ) from error
    if source != expected_source:
        raise TransformationFailure(
            FailureClassification.TRANSFORMATION_INVARIANT,
            "execution source identity does not match input source identity",
        )
    return source


def _parse_records(document: dict[str, Any]) -> tuple[SalesTransaction, ...]:
    raw_records = document.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        raise TransformationFailure(
            FailureClassification.MALFORMED_INPUT, "records must be a non-empty array"
        )
    try:
        return tuple(_parse_record(record) for record in raw_records)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise TransformationFailure(
            FailureClassification.MALFORMED_INPUT, "a sales record has an invalid structure"
        ) from error


def _parse_record(record: object) -> SalesTransaction:
    if not isinstance(record, dict):
        raise TypeError("record must be an object")
    timestamp = datetime.fromisoformat(
        _required_text(record, "transaction_timestamp").replace("Z", "+00:00")
    )
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("transaction timestamp must include a timezone")
    quantity = record.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise TypeError("quantity must be an integer")
    unit_price_value = record.get("unit_price")
    if isinstance(unit_price_value, bool) or not isinstance(unit_price_value, str | int | float):
        raise TypeError("unit price must be a decimal-compatible value")
    unit_price = Decimal(str(unit_price_value))
    if not unit_price.is_finite():
        raise ValueError("unit price must be finite")
    return SalesTransaction(
        transaction_id=_required_text(record, "transaction_id"),
        sku=_required_text(record, "sku"),
        quantity=quantity,
        unit_price=unit_price,
        transaction_timestamp=timestamp.astimezone(UTC),
        channel=_required_text(record, "channel"),
    )


def _required_text(values: dict[str, Any], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text")
    return value.strip()


def _optional_text(values: dict[str, Any], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text when supplied")
    return value.strip()


def _artifact(
    source: SourceIdentity,
    outcome: ProcessingOutcome,
    records: tuple[dict[str, object], ...],
) -> ArtifactMetadata:
    canonical = json.dumps(records, separators=(",", ":"), sort_keys=True).encode()
    return ArtifactMetadata(
        artifact_type=(
            ArtifactType.QUARANTINE_SALES_BATCH
            if outcome is ProcessingOutcome.REJECTED
            else ArtifactType.CURATED_SALES_BATCH
        ),
        disposition="quarantine" if outcome is ProcessingOutcome.REJECTED else "curated",
        record_count=len(records),
        contract_version=source.contract_version,
        checksum=hashlib.sha256(canonical).hexdigest(),
        source=source,
    )


def _failed_result(
    context: ExecutionContext,
    classification: FailureClassification,
    diagnostic: str,
) -> TransformationResult:
    _LOGGER.error(
        "sales transformation failed",
        extra={
            "stage": "transformation",
            "outcome": ProcessingOutcome.FAILED.value,
            "failure_classification": classification.value,
        },
    )
    return TransformationResult(
        execution_id=context.execution_id,
        correlation_id=context.correlation_id,
        source=context.source if context.source != _UNKNOWN_SOURCE else _UNKNOWN_SOURCE,
        outcome=ProcessingOutcome.FAILED,
        failure_classification=classification,
        diagnostic=diagnostic,
    )

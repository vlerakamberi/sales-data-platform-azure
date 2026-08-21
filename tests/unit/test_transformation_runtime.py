import json

import pytest

from sales_data_platform_azure.contracts import (
    ArtifactType,
    ExecutionContext,
    FailureClassification,
    ProcessingOutcome,
    SourceIdentity,
)
from sales_data_platform_azure.transformation import transform_sales_batch

SOURCE = SourceIdentity(
    source_id="northstar-pos",
    object_id="sales/2026-08-21/batch-001.json",
    contract_version="1.0",
    version="1",
    checksum="sha256:logical-input",
)


def _payload(records: list[dict[str, object]] | None = None, *, contract: str = "1.0") -> str:
    return json.dumps(
        {
            "contract_version": contract,
            "source": {
                "source_id": SOURCE.source_id,
                "object_id": SOURCE.object_id,
                "version": SOURCE.version,
                "checksum": SOURCE.checksum,
            },
            "records": records
            if records is not None
            else [
                {
                    "transaction_id": "tx-001",
                    "sku": "sku-100",
                    "quantity": 2,
                    "unit_price": "12.50",
                    "transaction_timestamp": "2026-08-21T09:30:00+02:00",
                    "channel": "store",
                }
            ],
        }
    )


def _context(execution_id: str = "run-1") -> ExecutionContext:
    return ExecutionContext(execution_id, "corr-1", SOURCE)


def test_valid_sales_batch_is_accepted_with_curated_artifact() -> None:
    result = transform_sales_batch(_payload(), _context())

    assert result.outcome is ProcessingOutcome.ACCEPTED
    assert result.artifact is not None
    assert result.artifact.artifact_type is ArtifactType.CURATED_SALES_BATCH
    assert result.artifact.disposition == "curated"
    assert result.artifact.record_count == 1
    assert result.artifact.source == SOURCE
    assert result.records[0] == {
        "channel": "store",
        "quantity": 2,
        "sku": "sku-100",
        "transaction_id": "tx-001",
        "transaction_timestamp": "2026-08-21T07:30:00Z",
        "unit_price": "12.50",
    }
    assert result.failed_expectation_ids == ()
    assert all(quality_result.passed for quality_result in result.quality_results)


def test_business_quality_failures_are_rejected_not_failed() -> None:
    records = [
        {
            "transaction_id": "duplicate",
            "sku": "sku-100",
            "quantity": 0,
            "unit_price": "-1.00",
            "transaction_timestamp": "2026-08-21T07:30:00Z",
            "channel": "web",
        },
        {
            "transaction_id": "duplicate",
            "sku": "sku-101",
            "quantity": 1,
            "unit_price": "4.00",
            "transaction_timestamp": "2026-08-21T08:30:00Z",
            "channel": "web",
        },
    ]
    result = transform_sales_batch(_payload(records), _context())

    assert result.outcome is ProcessingOutcome.REJECTED
    assert result.failure_classification is None
    assert result.artifact is not None
    assert result.artifact.artifact_type is ArtifactType.QUARANTINE_SALES_BATCH
    assert result.artifact.disposition == "quarantine"
    assert result.artifact.source == SOURCE
    assert result.failed_expectation_ids == (
        "sales.quantity.positive",
        "sales.transaction_id.unique_within_batch",
        "sales.unit_price.non_negative",
    )
    failures = [
        quality_result for quality_result in result.quality_results if not quality_result.passed
    ]
    assert all(failure.detail and failure.record_reference for failure in failures)


@pytest.mark.parametrize(
    ("payload", "classification"),
    [
        ("not-json", FailureClassification.MALFORMED_INPUT),
        (json.dumps([]), FailureClassification.MALFORMED_INPUT),
        (_payload(contract="2.0"), FailureClassification.UNSUPPORTED_CONTRACT),
        (_payload([]), FailureClassification.MALFORMED_INPUT),
    ],
)
def test_structural_or_unsupported_input_is_failed(
    payload: str, classification: FailureClassification
) -> None:
    result = transform_sales_batch(payload, _context())
    assert result.outcome is ProcessingOutcome.FAILED
    assert result.failure_classification is classification
    assert result.artifact is None
    assert result.quality_results == ()


def test_source_identity_mismatch_is_a_transformation_invariant_failure() -> None:
    different_source = SourceIdentity("other", SOURCE.object_id, "1.0", "1", SOURCE.checksum)
    result = transform_sales_batch(_payload(), ExecutionContext("run", "corr", different_source))
    assert result.outcome is ProcessingOutcome.FAILED
    assert result.failure_classification is FailureClassification.TRANSFORMATION_INVARIANT


def test_replay_is_deterministic_but_each_execution_remains_traceable() -> None:
    first = transform_sales_batch(_payload(), _context("run-1"))
    replay = transform_sales_batch(_payload(), _context("run-2"))

    assert first.execution_id != replay.execution_id
    assert first.source == replay.source == SOURCE
    assert first.records == replay.records
    assert first.quality_results == replay.quality_results
    assert first.artifact == replay.artifact
    assert first.to_dict()["execution_id"] == "run-1"
    assert replay.to_dict()["execution_id"] == "run-2"


@pytest.mark.parametrize(
    "record_change",
    [
        {"quantity": "2"},
        {"unit_price": True},
        {"unit_price": "NaN"},
        {"transaction_timestamp": "2026-08-21T09:30:00"},
        {"sku": ""},
    ],
)
def test_invalid_record_structure_is_failed(record_change: dict[str, object]) -> None:
    record = json.loads(_payload())["records"][0]
    record.update(record_change)
    result = transform_sales_batch(_payload([record]), _context())
    assert result.outcome is ProcessingOutcome.FAILED
    assert result.failure_classification is FailureClassification.MALFORMED_INPUT

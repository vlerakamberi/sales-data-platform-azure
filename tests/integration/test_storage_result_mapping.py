import json
from datetime import date

import pytest

from sales_data_platform_azure.contracts import ExecutionContext, SourceIdentity
from sales_data_platform_azure.storage import DataLayer, storage_object_from_result
from sales_data_platform_azure.transformation import transform_sales_batch

SOURCE = SourceIdentity(
    "northstar-pos",
    "sales/2026-08-21/batch-001.json",
    "1.0",
    "1",
    "sha256:logical-source",
)


def _result(execution_id: str, *, quantity: int = 1):
    payload = json.dumps(
        {
            "contract_version": "1.0",
            "source": {
                "source_id": SOURCE.source_id,
                "object_id": SOURCE.object_id,
                "version": SOURCE.version,
                "checksum": SOURCE.checksum,
            },
            "records": [
                {
                    "transaction_id": "tx-1",
                    "sku": "sku-1",
                    "quantity": quantity,
                    "unit_price": "2.50",
                    "transaction_timestamp": "2026-08-21T10:00:00Z",
                    "channel": "store",
                }
            ],
        }
    )
    return transform_sales_batch(payload, ExecutionContext(execution_id, "corr-1", SOURCE))


def test_accepted_replays_map_to_same_curated_object_with_separate_trace_metadata() -> None:
    first = storage_object_from_result(
        _result("run-1"), environment="dev", dataset="sales", partition_date=date(2026, 8, 21)
    )
    replay = storage_object_from_result(
        _result("run-2"), environment="dev", dataset="sales", partition_date=date(2026, 8, 21)
    )

    assert first.location == replay.location
    assert first.location.layer is DataLayer.CURATED
    assert first.metadata.source == replay.metadata.source == SOURCE
    assert first.metadata.execution_id == "run-1"
    assert replay.metadata.execution_id == "run-2"
    assert first.metadata.correlation_id == replay.metadata.correlation_id == "corr-1"


def test_rejection_maps_to_quarantine_with_complete_traceability() -> None:
    rejected = storage_object_from_result(
        _result("reject-1", quantity=0),
        environment="prod",
        dataset="sales",
        partition_date=date(2026, 8, 21),
    )

    assert rejected.location.layer is DataLayer.QUARANTINE
    assert rejected.metadata.source == SOURCE
    assert rejected.metadata.execution_id == "reject-1"
    assert rejected.metadata.correlation_id == "corr-1"
    assert rejected.metadata.failed_expectation_ids == ("sales.quantity.positive",)
    assert rejected.metadata.rejection_classification == "DATA_QUALITY_REJECTION"
    assert rejected.metadata.rejection_reason == "blocking data quality expectations failed"


def test_failed_result_cannot_be_adapted_to_a_storage_object() -> None:
    failed = transform_sales_batch("not-json", ExecutionContext("run", "corr", SOURCE))
    with pytest.raises(ValueError, match="do not produce"):
        storage_object_from_result(
            failed,
            environment="dev",
            dataset="sales",
            partition_date=date(2026, 8, 21),
        )

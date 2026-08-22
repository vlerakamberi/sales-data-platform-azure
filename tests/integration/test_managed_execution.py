import json
from datetime import date

from sales_data_platform_azure.contracts import (
    ExecutionContext,
    ProcessingOutcome,
    SourceIdentity,
)
from sales_data_platform_azure.storage import StorageEnvironment
from sales_data_platform_azure.transformation.managed import (
    ManagedExecutionRequest,
    execute_managed,
)

SOURCE = SourceIdentity("northstar-pos", "raw/batch-001.json", "1.0")


class MemoryBlobStore:
    def __init__(self, payload: str, *, fail_upload: bool = False) -> None:
        self.payload = payload
        self.fail_upload = fail_upload
        self.downloads: list[tuple[str, str]] = []
        self.uploads: list[tuple[str, str, str]] = []

    def download_text(self, container: str, object_name: str) -> str:
        self.downloads.append((container, object_name))
        return self.payload

    def upload_text(self, container: str, object_name: str, content: str) -> None:
        if self.fail_upload:
            raise OSError("simulated storage failure")
        self.uploads.append((container, object_name, content))


def _payload(quantity: int = 1) -> str:
    return json.dumps(
        {
            "contract_version": "1.0",
            "source": {"source_id": SOURCE.source_id, "object_id": SOURCE.object_id},
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


def _request(execution_id: str) -> ManagedExecutionRequest:
    return ManagedExecutionRequest(
        environment=StorageEnvironment.DEV,
        raw_container="raw",
        processed_container="processed",
        curated_container="curated",
        quarantine_container="quarantine",
        input_blob=SOURCE.object_id,
        dataset="sales",
        partition_date=date(2026, 8, 21),
        context=ExecutionContext(execution_id, "corr-1", SOURCE),
    )


def test_managed_acceptance_reads_raw_and_writes_processed_and_curated() -> None:
    store = MemoryBlobStore(_payload())
    result = execute_managed(_request("run-1"), store)

    assert result.outcome is ProcessingOutcome.ACCEPTED
    assert store.downloads == [("raw", SOURCE.object_id)]
    assert [upload[0] for upload in store.uploads] == ["processed", "curated"]


def test_managed_rejection_exits_governed_and_writes_quarantine() -> None:
    store = MemoryBlobStore(_payload(quantity=0))
    result = execute_managed(_request("reject-1"), store)

    assert result.outcome is ProcessingOutcome.REJECTED
    assert [upload[0] for upload in store.uploads] == ["processed", "quarantine"]


def test_replay_keeps_business_addresses_stable_but_quarantine_attempts_distinct() -> None:
    first, replay = MemoryBlobStore(_payload()), MemoryBlobStore(_payload())
    execute_managed(_request("run-1"), first)
    execute_managed(_request("run-2"), replay)
    assert [item[1] for item in first.uploads] == [item[1] for item in replay.uploads]

    rejected_first, rejected_replay = MemoryBlobStore(_payload(0)), MemoryBlobStore(_payload(0))
    execute_managed(_request("reject-1"), rejected_first)
    execute_managed(_request("reject-2"), rejected_replay)
    assert rejected_first.uploads[0][1] == rejected_replay.uploads[0][1]
    assert rejected_first.uploads[1][1] != rejected_replay.uploads[1][1]


def test_technical_failure_returns_no_artifact_and_does_not_write_destination() -> None:
    store = MemoryBlobStore("not-json")
    result = execute_managed(_request("failed-1"), store)
    assert result.outcome is ProcessingOutcome.FAILED
    assert result.artifact is None
    assert store.uploads == []


def test_storage_failure_is_safe_failed_execution() -> None:
    store = MemoryBlobStore(_payload(), fail_upload=True)
    result = execute_managed(_request("failed-storage"), store)
    assert result.outcome is ProcessingOutcome.FAILED
    assert result.artifact is None
    assert result.diagnostic == "managed storage execution failed"

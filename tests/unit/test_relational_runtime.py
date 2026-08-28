import io
import json
from dataclasses import dataclass, field

import pytest

from sales_data_platform_azure.config import PostgreSQLSettings
from sales_data_platform_azure.contracts import ExecutionContext, SourceIdentity
from sales_data_platform_azure.logging import configure_logging
from sales_data_platform_azure.relational import (
    PostgreSQLServingRepository,
    PsycopgConnectionFactory,
    RelationalServingError,
    RelationalServingService,
)
from sales_data_platform_azure.transformation import transform_sales_batch

SOURCE = SourceIdentity("northstar-pos", "raw/batch-001.json", "1.0")
SETTINGS = PostgreSQLSettings("private.example", "sales", "serving-job")


def _accepted(execution_id: str = "run-1"):
    payload = json.dumps(
        {
            "contract_version": "1.0",
            "source": {"source_id": SOURCE.source_id, "object_id": SOURCE.object_id},
            "records": [
                {
                    "transaction_id": "tx-1",
                    "sku": "sku-1",
                    "quantity": 1,
                    "unit_price": "2.50",
                    "transaction_timestamp": "2026-08-21T10:00:00Z",
                    "channel": "store",
                }
            ],
        }
    )
    return transform_sales_batch(payload, ExecutionContext(execution_id, "corr-1", SOURCE))


@dataclass
class MemoryDatabase:
    business: dict[str, tuple[object, ...]] = field(default_factory=dict)
    attempts: dict[str, tuple[object, ...]] = field(default_factory=dict)
    lineage: set[tuple[str, str]] = field(default_factory=set)


class FakeConnection:
    def __init__(self, database: MemoryDatabase, fail_at: str | None = None) -> None:
        self.database = database
        self.fail_at = fail_at
        self.staged: list[tuple[str, tuple[object, ...]]] = []
        self.rolled_back = False
        self.closed = False

    def execute(self, query: str, params=()):
        kind = (
            "business"
            if "serving.sales_transaction (" in query
            else "attempt"
            if "serving.serving_attempt (" in query
            else "lineage"
        )
        if self.fail_at == kind:
            raise RuntimeError(f"simulated {kind} failure")
        self.staged.append((kind, tuple(params)))

    def commit(self) -> None:
        if self.fail_at == "commit":
            raise RuntimeError("simulated commit failure")
        for kind, params in self.staged:
            if kind == "business":
                self.database.business[str(params[0])] = params
            elif kind == "attempt":
                self.database.attempts[str(params[0])] = params
            else:
                self.database.lineage.add((str(params[0]), str(params[1])))

    def rollback(self) -> None:
        self.rolled_back = True
        self.staged.clear()

    def close(self) -> None:
        self.closed = True


class FakeFactory:
    def __init__(self, database: MemoryDatabase, fail_at: str | None = None) -> None:
        self.database = database
        self.fail_at = fail_at
        self.connections: list[FakeConnection] = []

    def connect(self, settings: PostgreSQLSettings) -> FakeConnection:
        assert settings == SETTINGS
        connection = FakeConnection(self.database, self.fail_at)
        self.connections.append(connection)
        return connection


def test_successful_persistence_and_replay_reconcile_one_business_row() -> None:
    database = MemoryDatabase()
    factory = FakeFactory(database)
    repository = PostgreSQLServingRepository(factory, SETTINGS)

    first = repository.persist(_accepted("run-1"), "attempt-1")
    replay = repository.persist(_accepted("run-2"), "attempt-2")

    assert first.business_identities == replay.business_identities
    assert set(database.business) == {"tx-1"}
    assert set(database.attempts) == {"attempt-1", "attempt-2"}
    assert database.lineage == {("tx-1", "attempt-1"), ("tx-1", "attempt-2")}
    assert all(connection.closed for connection in factory.connections)


@pytest.mark.parametrize("failure_point", ["business", "attempt", "lineage", "commit"])
def test_every_required_write_and_commit_failure_rolls_back_atomically(
    failure_point: str,
) -> None:
    database = MemoryDatabase()
    factory = FakeFactory(database, fail_at=failure_point)
    repository = PostgreSQLServingRepository(factory, SETTINGS)

    with pytest.raises(RelationalServingError) as captured:
        repository.persist(_accepted(), "attempt-1")

    assert str(captured.value) == "relational serving transaction failed"
    assert factory.connections[0].rolled_back is True
    assert factory.connections[0].closed is True
    assert database == MemoryDatabase()


def test_serving_observability_has_safe_fields_and_never_logs_credential() -> None:
    stream = io.StringIO()
    configure_logging(stream=stream)
    service = RelationalServingService(
        PostgreSQLServingRepository(FakeFactory(MemoryDatabase()), SETTINGS)
    )

    service.serve(_accepted(), environment="dev", dataset="sales", attempt_id="attempt-1")

    events = [
        event for line in stream.getvalue().splitlines() if "event" in (event := json.loads(line))
    ]
    assert [event["event"] for event in events] == [
        "RELATIONAL_SERVING_STARTED",
        "RELATIONAL_SERVING_SUCCEEDED",
    ]
    for event in events:
        assert event["environment"] == "dev"
        assert event["dataset"] == "sales"
        assert event["transaction_id"] == "tx-1"
        assert event["source_id"] == SOURCE.source_id
        assert event["source_object_id"] == SOURCE.object_id
        assert event["execution_id"] == "run-1"
        assert event["correlation_id"] == "corr-1"
        assert event["attempt_id"] == "attempt-1"
    assert "credential-secret" not in stream.getvalue()


def test_failed_observability_is_classified_without_leaking_cause() -> None:
    stream = io.StringIO()
    configure_logging(stream=stream)
    service = RelationalServingService(
        PostgreSQLServingRepository(FakeFactory(MemoryDatabase(), "commit"), SETTINGS)
    )

    with pytest.raises(RelationalServingError):
        service.serve(_accepted(), environment="dev", dataset="sales", attempt_id="attempt-1")

    event = json.loads(stream.getvalue().splitlines()[-1])
    assert event["event"] == "RELATIONAL_SERVING_FAILED"
    assert event["persistence_outcome"] == "FAILED"
    assert event["failure_classification"] == "RELATIONAL_SERVING_FAILED"
    assert event["diagnostic_category"] == "RELATIONAL_TRANSACTION_FAILED"
    assert "simulated commit failure" not in stream.getvalue()


def test_psycopg_adapter_uses_injected_credential_and_safe_parameters(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class CredentialProvider:
        def get_credential(self) -> str:
            return "credential-secret"

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return FakeConnection(MemoryDatabase())

    monkeypatch.setattr(
        "sales_data_platform_azure.relational.adapter.psycopg.connect", fake_connect
    )
    connection = PsycopgConnectionFactory(CredentialProvider()).connect(SETTINGS)

    assert isinstance(connection, FakeConnection)
    assert captured == {
        "host": "private.example",
        "dbname": "sales",
        "user": "serving-job",
        "password": "credential-secret",
        "port": 5432,
        "sslmode": "require",
        "autocommit": False,
    }

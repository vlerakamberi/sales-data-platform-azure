import io
import json
from pathlib import Path

import pytest

from sales_data_platform_azure.transformation.cli import main


def _payload(*, quantity: int = 1) -> str:
    return json.dumps(
        {
            "contract_version": "1.0",
            "source": {
                "source_id": "northstar-pos",
                "object_id": "batch.json",
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


def _invoke(payload: str) -> tuple[int, dict[str, object], str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(
        ["--input", "-", "--execution-id", "run-cli", "--correlation-id", "corr-cli"],
        stdin=io.StringIO(payload),
        stdout=stdout,
        stderr=stderr,
    )
    return exit_code, json.loads(stdout.getvalue()), stderr.getvalue()


def test_cli_acceptance_exits_zero_and_writes_structured_result() -> None:
    exit_code, result, logs = _invoke(_payload())
    assert exit_code == 0
    assert result["outcome"] == "ACCEPTED"
    assert result["execution_id"] == "run-cli"
    assert '"execution_id":"run-cli"' in logs
    assert '"correlation_id":"corr-cli"' in logs
    assert '"outcome":"ACCEPTED"' in logs


def test_cli_governed_rejection_exits_zero() -> None:
    exit_code, result, logs = _invoke(_payload(quantity=0))
    assert exit_code == 0
    assert result["outcome"] == "REJECTED"
    assert result["artifact"]["disposition"] == "quarantine"
    assert '"outcome":"REJECTED"' in logs


def test_cli_transformation_failure_exits_nonzero_without_echoing_payload() -> None:
    raw_payload = "secret-looking-raw-payload"
    exit_code, result, logs = _invoke(raw_payload)
    assert exit_code == 2
    assert result["outcome"] == "FAILED"
    assert result["failure_classification"] == "MALFORMED_INPUT"
    assert raw_payload not in logs


def test_cli_unreadable_file_is_failed(tmp_path: Path) -> None:
    stdout = io.StringIO()
    exit_code = main(
        [
            "--input",
            str(tmp_path / "missing.json"),
            "--execution-id",
            "run",
            "--correlation-id",
            "corr",
        ],
        stdout=stdout,
        stderr=io.StringIO(),
    )
    assert exit_code == 2
    assert json.loads(stdout.getvalue())["failure_classification"] == "INVALID_CONFIGURATION"


def test_managed_cli_builds_and_wires_relational_serving(monkeypatch: pytest.MonkeyPatch) -> None:
    serving = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "sales_data_platform_azure.transformation.cli.AzureBlobStore", lambda account_url: object()
    )
    monkeypatch.setattr(
        "sales_data_platform_azure.transformation.cli.build_relational_serving_service",
        lambda environ: serving,
    )

    def fake_execute(request, store, relational_serving):
        captured.update(request=request, store=store, relational_serving=relational_serving)
        return type(
            "Result",
            (),
            {"outcome": type("Outcome", (), {"value": "ACCEPTED"})(), "to_dict": lambda self: {}},
        )()

    monkeypatch.setattr(
        "sales_data_platform_azure.transformation.cli.execute_managed", fake_execute
    )
    stdout = io.StringIO()

    exit_code = main(
        [
            "--input-blob",
            "raw/batch.json",
            "--storage-account-url",
            "https://storage.example",
            "--dataset",
            "sales",
            "--partition-date",
            "2026-08-21",
            "--source-id",
            "northstar-pos",
            "--source-object-id",
            "raw/batch.json",
        ],
        stdout=stdout,
        stderr=io.StringIO(),
    )

    assert exit_code == 0
    assert captured["relational_serving"] is serving


def test_managed_cli_fails_closed_without_postgresql_identity_client_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in (
        "SDPA_POSTGRESQL_HOST",
        "SDPA_POSTGRESQL_DATABASE",
        "SDPA_POSTGRESQL_USER",
        "SDPA_POSTGRESQL_PORT",
        "SDPA_POSTGRESQL_SSLMODE",
        "SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID",
        "SDPA_POSTGRESQL_PASSWORD",
        "PGPASSWORD",
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("SDPA_POSTGRESQL_HOST", "private.example.postgres.database.azure.com")
    monkeypatch.setenv("SDPA_POSTGRESQL_DATABASE", "sales")
    monkeypatch.setenv("SDPA_POSTGRESQL_USER", "serving-runtime")
    monkeypatch.setattr(
        "sales_data_platform_azure.transformation.cli.AzureBlobStore", lambda account_url: object()
    )
    stdout = io.StringIO()

    exit_code = main(
        [
            "--input-blob",
            "raw/batch.json",
            "--storage-account-url",
            "https://storage.example",
            "--dataset",
            "sales",
            "--partition-date",
            "2026-08-21",
            "--source-id",
            "northstar-pos",
            "--source-object-id",
            "raw/batch.json",
        ],
        stdout=stdout,
        stderr=io.StringIO(),
    )

    assert exit_code == 2
    assert json.loads(stdout.getvalue())["failure_classification"] == "INVALID_CONFIGURATION"

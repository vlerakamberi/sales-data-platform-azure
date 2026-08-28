"""Local file/stdin command boundary for the Unit 3 runtime."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import TextIO

from sales_data_platform_azure.contracts import (
    ExecutionContext,
    FailureClassification,
    ProcessingOutcome,
    SourceIdentity,
    TransformationResult,
)
from sales_data_platform_azure.logging import configure_logging
from sales_data_platform_azure.relational import RelationalServingService

from .managed import AzureBlobStore, ManagedExecutionRequest, execute_managed
from .runtime import transform_sales_batch

_UNKNOWN_SOURCE = SourceIdentity("unknown", "unknown", "unknown")


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    relational_serving: RelationalServingService | None = None,
) -> int:
    """Execute one request and return 0 for governed outcomes, 2 for execution failures."""
    input_stream = sys.stdin if stdin is None else stdin
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    arguments = _parser().parse_args(argv)
    execution_id = arguments.execution_id or str(uuid.uuid4())
    correlation_id = arguments.correlation_id or execution_id
    configure_logging(arguments.log_level, stream=error_stream)

    if arguments.input_blob:
        result = _execute_cloud(
            arguments, execution_id, correlation_id, relational_serving=relational_serving
        )
    else:
        result = _execute_local(arguments, input_stream, execution_id, correlation_id)

    json.dump(result.to_dict(), output_stream, separators=(",", ":"), sort_keys=True)
    output_stream.write("\n")
    return 2 if result.outcome is ProcessingOutcome.FAILED else 0


def _execute_local(arguments, input_stream, execution_id, correlation_id):
    try:
        payload = (
            input_stream.read()
            if arguments.input == "-"
            else Path(arguments.input).read_text(encoding="utf-8")
        )
    except OSError:
        result = TransformationResult(
            execution_id=execution_id,
            correlation_id=correlation_id,
            source=_UNKNOWN_SOURCE,
            outcome=ProcessingOutcome.FAILED,
            failure_classification=FailureClassification.INVALID_CONFIGURATION,
            diagnostic="input file could not be read",
        )
    else:
        context = ExecutionContext(
            execution_id=execution_id,
            correlation_id=correlation_id,
            source=_source_identity(payload),
        )
        result = transform_sales_batch(payload, context)

    return result


def _execute_cloud(
    arguments,
    execution_id: str,
    correlation_id: str,
    *,
    relational_serving: RelationalServingService | None = None,
) -> TransformationResult:
    required = {
        "storage account URL": arguments.storage_account_url,
        "dataset": arguments.dataset,
        "partition date": arguments.partition_date,
        "source ID": arguments.source_id,
        "source object ID": arguments.source_object_id,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        return TransformationResult(
            execution_id=execution_id,
            correlation_id=correlation_id,
            source=_UNKNOWN_SOURCE,
            outcome=ProcessingOutcome.FAILED,
            failure_classification=FailureClassification.INVALID_CONFIGURATION,
            diagnostic=f"missing managed execution configuration: {', '.join(missing)}",
        )
    try:
        source = SourceIdentity(
            arguments.source_id,
            arguments.source_object_id,
            arguments.contract_version,
            arguments.source_version,
            arguments.source_checksum,
        )
        environment = {"development": "dev", "production": "prod"}.get(
            arguments.environment, arguments.environment
        )
        request = ManagedExecutionRequest(
            environment=environment,
            raw_container=arguments.raw_container,
            processed_container=arguments.processed_container,
            curated_container=arguments.curated_container,
            quarantine_container=arguments.quarantine_container,
            input_blob=arguments.input_blob,
            dataset=arguments.dataset,
            partition_date=date.fromisoformat(arguments.partition_date),
            context=ExecutionContext(execution_id, correlation_id, source),
        )
        store = AzureBlobStore(arguments.storage_account_url)
    except (TypeError, ValueError):
        return TransformationResult(
            execution_id=execution_id,
            correlation_id=correlation_id,
            source=_UNKNOWN_SOURCE,
            outcome=ProcessingOutcome.FAILED,
            failure_classification=FailureClassification.INVALID_CONFIGURATION,
            diagnostic="managed execution configuration is invalid",
        )
    return execute_managed(request, store, relational_serving)


def _source_identity(payload: str) -> SourceIdentity:
    """Best-effort context identity; canonical validation remains in the runtime."""
    try:
        document = json.loads(payload)
        source = document["source"]
        return SourceIdentity(
            source_id=source["source_id"],
            object_id=source["object_id"],
            contract_version=document["contract_version"],
            version=source.get("version"),
            checksum=source.get("checksum"),
        )
    except (KeyError, TypeError, json.JSONDecodeError):
        return _UNKNOWN_SOURCE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transform one local Northstar sales batch")
    parser.add_argument("--input", default="-", help="UTF-8 JSON file, or - for stdin")
    parser.add_argument("--input-blob", help="raw container object name for managed execution")
    parser.add_argument("--dataset", help="governed dataset identity")
    parser.add_argument("--partition-date", help="business partition date (YYYY-MM-DD)")
    parser.add_argument("--source-id", help="stable logical source-system identity")
    parser.add_argument("--source-object-id", help="stable logical source-object identity")
    parser.add_argument("--source-version")
    parser.add_argument("--source-checksum")
    parser.add_argument("--contract-version", default="1.0")
    parser.add_argument("--environment", default=os.getenv("SDPA_ENVIRONMENT", "development"))
    parser.add_argument("--storage-account-url", default=os.getenv("SDPA_STORAGE_ACCOUNT_URL"))
    parser.add_argument("--raw-container", default=os.getenv("SDPA_RAW_CONTAINER", "raw"))
    parser.add_argument(
        "--processed-container", default=os.getenv("SDPA_PROCESSED_CONTAINER", "processed")
    )
    parser.add_argument(
        "--curated-container", default=os.getenv("SDPA_CURATED_CONTAINER", "curated")
    )
    parser.add_argument(
        "--quarantine-container", default=os.getenv("SDPA_QUARANTINE_CONTAINER", "quarantine")
    )
    parser.add_argument("--execution-id", help="trace identity for this execution")
    parser.add_argument("--correlation-id", help="cross-component correlation identity")
    parser.add_argument(
        "--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())

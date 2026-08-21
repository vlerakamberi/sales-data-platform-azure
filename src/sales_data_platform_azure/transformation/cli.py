"""Local file/stdin command boundary for the Unit 3 runtime."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections.abc import Sequence
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

from .runtime import transform_sales_batch

_UNKNOWN_SOURCE = SourceIdentity("unknown", "unknown", "unknown")


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Execute one request and return 0 for governed outcomes, 2 for execution failures."""
    input_stream = sys.stdin if stdin is None else stdin
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    arguments = _parser().parse_args(argv)
    execution_id = arguments.execution_id or str(uuid.uuid4())
    correlation_id = arguments.correlation_id or execution_id
    configure_logging(arguments.log_level, stream=error_stream)

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

    json.dump(result.to_dict(), output_stream, separators=(",", ":"), sort_keys=True)
    output_stream.write("\n")
    return 2 if result.outcome is ProcessingOutcome.FAILED else 0


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
    parser.add_argument("--execution-id", help="trace identity for this execution")
    parser.add_argument("--correlation-id", help="cross-component correlation identity")
    parser.add_argument(
        "--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())

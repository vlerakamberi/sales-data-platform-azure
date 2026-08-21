import io
import json

from sales_data_platform_azure.logging import configure_logging, correlation_context


def _last_record(stream: io.StringIO) -> dict[str, object]:
    return json.loads(stream.getvalue().splitlines()[-1])


def test_structured_logging_emits_expected_allowlisted_fields() -> None:
    stream = io.StringIO()
    logger = configure_logging("INFO", stream=stream)
    with correlation_context(correlation_id="corr-1", execution_id="run-1"):
        logger.info("ready")

    record = _last_record(stream)
    assert record["message"] == "ready"
    assert record["correlation_id"] == "corr-1"
    assert record["execution_id"] == "run-1"
    assert record["level"] == "INFO"


def test_logging_configuration_is_idempotent_and_context_is_restored() -> None:
    first = io.StringIO()
    logger = configure_logging(stream=first)
    logger.info("first")

    second = io.StringIO()
    logger = configure_logging(stream=second)
    with correlation_context(correlation_id="temporary"):
        logger.info("inside")
    logger.info("outside")

    assert len(logger.handlers) == 1
    assert "correlation_id" not in _last_record(second)
    assert len(first.getvalue().splitlines()) == 1


def test_log_level_filters_lower_severity() -> None:
    stream = io.StringIO()
    logger = configure_logging("WARNING", stream=stream)
    logger.info("not emitted")
    logger.warning("emitted")
    assert _last_record(stream)["message"] == "emitted"


def test_exception_is_serialized() -> None:
    stream = io.StringIO()
    logger = configure_logging(stream=stream)
    try:
        raise RuntimeError("expected")
    except RuntimeError:
        logger.exception("failed safely")
    assert "RuntimeError: expected" in _last_record(stream)["exception"]


def test_safe_runtime_metadata_is_serialized() -> None:
    stream = io.StringIO()
    logger = configure_logging(stream=stream)
    logger.info(
        "completed",
        extra={
            "stage": "quality_decision",
            "outcome": "REJECTED",
            "failed_expectation_ids": ("sales.quantity.positive",),
        },
    )
    record = _last_record(stream)
    assert record["stage"] == "quality_decision"
    assert record["outcome"] == "REJECTED"
    assert record["failed_expectation_ids"] == ["sales.quantity.positive"]

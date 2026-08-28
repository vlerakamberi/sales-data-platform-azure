"""Atomic, deterministic persistence of accepted sales results."""

from __future__ import annotations

from contextlib import suppress
from typing import Any

from sales_data_platform_azure.config import PostgreSQLSettings
from sales_data_platform_azure.contracts import ProcessingOutcome, TransformationResult

from .connection import RelationalConnectionFactory
from .models import BusinessIdentity, PersistenceOutcome, PersistenceResult, ServingAttempt

_UPSERT_TRANSACTION = """
INSERT INTO serving.sales_transaction (
    transaction_id, sku, quantity, unit_price, transaction_timestamp, channel,
    source_id, source_object_id, source_contract_version, source_version, source_checksum
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (transaction_id) DO UPDATE SET
    sku = EXCLUDED.sku,
    quantity = EXCLUDED.quantity,
    unit_price = EXCLUDED.unit_price,
    transaction_timestamp = EXCLUDED.transaction_timestamp,
    channel = EXCLUDED.channel,
    source_id = EXCLUDED.source_id,
    source_object_id = EXCLUDED.source_object_id,
    source_contract_version = EXCLUDED.source_contract_version,
    source_version = EXCLUDED.source_version,
    source_checksum = EXCLUDED.source_checksum
"""

_INSERT_ATTEMPT = """
INSERT INTO serving.serving_attempt (
    attempt_id, execution_id, correlation_id, source_id, source_object_id,
    source_contract_version, source_version, source_checksum, persistence_outcome
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_INSERT_LINEAGE = """
INSERT INTO serving.sales_transaction_lineage (transaction_id, attempt_id)
VALUES (%s, %s)
"""


class RelationalServingError(RuntimeError):
    """Safe technical failure raised after a serving transaction is rolled back."""


class PostgreSQLServingRepository:
    """Reconcile a whole accepted batch and its lineage in one transaction."""

    def __init__(
        self, connection_factory: RelationalConnectionFactory, settings: PostgreSQLSettings
    ) -> None:
        self._connection_factory = connection_factory
        self._settings = settings

    def persist(self, result: TransformationResult, attempt_id: str) -> PersistenceResult:
        """Persist accepted state atomically; never transform or re-evaluate quality."""
        if result.outcome is not ProcessingOutcome.ACCEPTED:
            raise ValueError("only ACCEPTED results are eligible for relational serving")
        if not result.records:
            raise ValueError("accepted result must contain business records")

        connection = self._connection_factory.connect(self._settings)
        identities: list[BusinessIdentity] = []
        try:
            for record in result.records:
                identity = BusinessIdentity(_required_record_text(record, "transaction_id"))
                identities.append(identity)
                connection.execute(_UPSERT_TRANSACTION, _transaction_parameters(record, result))

            attempt = ServingAttempt(
                attempt_id,
                result.execution_id,
                result.correlation_id,
                PersistenceOutcome.PERSISTED,
            )
            source = result.source
            connection.execute(
                _INSERT_ATTEMPT,
                (
                    attempt.attempt_id,
                    attempt.execution_id,
                    attempt.correlation_id,
                    source.source_id,
                    source.object_id,
                    source.contract_version,
                    source.version,
                    source.checksum,
                    attempt.outcome.value,
                ),
            )
            for identity in identities:
                connection.execute(_INSERT_LINEAGE, (identity.transaction_id, attempt.attempt_id))
            connection.commit()
            return PersistenceResult(attempt, tuple(identities))
        except Exception as error:
            with suppress(Exception):
                connection.rollback()
            raise RelationalServingError("relational serving transaction failed") from error
        finally:
            with suppress(Exception):
                connection.close()


def _transaction_parameters(
    record: dict[str, Any], result: TransformationResult
) -> tuple[object, ...]:
    source = result.source
    return (
        _required_record_text(record, "transaction_id"),
        _required_record_text(record, "sku"),
        record["quantity"],
        record["unit_price"],
        record["transaction_timestamp"],
        _required_record_text(record, "channel"),
        source.source_id,
        source.object_id,
        source.contract_version,
        source.version,
        source.checksum,
    )


def _required_record_text(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"accepted record {field} must be non-empty text")
    return value

"""Small, explicit quality rule set for the Unit 3 sales scenario."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sales_data_platform_azure.transformation.models import SalesTransaction


class QualitySeverity(StrEnum):
    """Whether a failed expectation blocks acceptance."""

    BLOCKING = "BLOCKING"
    NON_BLOCKING = "NON_BLOCKING"


@dataclass(frozen=True, slots=True)
class QualityResult:
    """Result of one stable expectation for one record or batch."""

    expectation_id: str
    passed: bool
    severity: QualitySeverity
    detail: str | None = None
    record_reference: str | None = None


def evaluate_sales_batch(records: tuple[SalesTransaction, ...]) -> tuple[QualityResult, ...]:
    """Evaluate the intentionally bounded blocking sales expectations."""
    results: list[QualityResult] = []
    identifier_counts = Counter(record.transaction_id for record in records)

    for record in records:
        results.extend(
            (
                QualityResult(
                    expectation_id="sales.quantity.positive",
                    passed=record.quantity > 0,
                    severity=QualitySeverity.BLOCKING,
                    detail=None if record.quantity > 0 else "quantity must be positive",
                    record_reference=record.transaction_id,
                ),
                QualityResult(
                    expectation_id="sales.unit_price.non_negative",
                    passed=record.unit_price >= 0,
                    severity=QualitySeverity.BLOCKING,
                    detail=None if record.unit_price >= 0 else "unit price must not be negative",
                    record_reference=record.transaction_id,
                ),
            )
        )

    for transaction_id, count in sorted(identifier_counts.items()):
        results.append(
            QualityResult(
                expectation_id="sales.transaction_id.unique_within_batch",
                passed=count == 1,
                severity=QualitySeverity.BLOCKING,
                detail=None if count == 1 else "transaction ID is duplicated within the batch",
                record_reference=transaction_id,
            )
        )

    return tuple(results)

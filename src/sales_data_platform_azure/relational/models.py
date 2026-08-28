"""Identity, eligibility, attempt, and lineage contracts for relational serving."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sales_data_platform_azure.contracts import ProcessingOutcome, SourceIdentity


@dataclass(frozen=True, slots=True)
class BusinessIdentity:
    """Stable business key, deliberately independent of orchestration execution identity."""

    transaction_id: str

    def __post_init__(self) -> None:
        if not self.transaction_id.strip():
            raise ValueError("transaction_id must not be empty")


class PersistenceOutcome(StrEnum):
    """Result of one future relational persistence attempt."""

    PERSISTED = "PERSISTED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class ServingAttempt:
    """Trace identity and outcome for one distinguishable serving attempt."""

    attempt_id: str
    execution_id: str
    correlation_id: str
    outcome: PersistenceOutcome

    def __post_init__(self) -> None:
        values = (self.attempt_id, self.execution_id, self.correlation_id)
        if any(not value.strip() for value in values):
            raise ValueError("serving attempt identifiers must not be empty")


@dataclass(frozen=True, slots=True)
class ServingLineage:
    """Minimal link between stable business state, logical source, and one attempt."""

    business_identity: BusinessIdentity
    source: SourceIdentity
    attempt: ServingAttempt


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    """Safe result of one atomically committed relational serving attempt."""

    attempt: ServingAttempt
    business_identities: tuple[BusinessIdentity, ...]


def is_serving_eligible(outcome: ProcessingOutcome) -> bool:
    """Only governed accepted transformation results may enter normal serving persistence."""
    return outcome is ProcessingOutcome.ACCEPTED

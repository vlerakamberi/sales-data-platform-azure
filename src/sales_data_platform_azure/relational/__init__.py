"""Database-free contracts for bounded relational serving."""

from .connection import RelationalConnection, RelationalConnectionFactory
from .migrations import (
    AppliedMigration,
    Migration,
    MigrationError,
    discover_migrations,
    pending_migrations,
)
from .models import (
    BusinessIdentity,
    PersistenceOutcome,
    ServingAttempt,
    ServingLineage,
    is_serving_eligible,
)

__all__ = [
    "AppliedMigration",
    "BusinessIdentity",
    "Migration",
    "MigrationError",
    "PersistenceOutcome",
    "RelationalConnection",
    "RelationalConnectionFactory",
    "ServingAttempt",
    "ServingLineage",
    "discover_migrations",
    "is_serving_eligible",
    "pending_migrations",
]

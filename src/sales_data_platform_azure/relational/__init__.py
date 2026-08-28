"""Database-free contracts for bounded relational serving."""

from .adapter import PostgreSQLCredentialProvider, PsycopgConnectionFactory
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
    PersistenceResult,
    ServingAttempt,
    ServingLineage,
    is_serving_eligible,
)
from .repository import PostgreSQLServingRepository, RelationalServingError
from .service import RelationalServingService, ServingRepository

__all__ = [
    "AppliedMigration",
    "BusinessIdentity",
    "Migration",
    "MigrationError",
    "PersistenceOutcome",
    "PersistenceResult",
    "PostgreSQLCredentialProvider",
    "PostgreSQLServingRepository",
    "PsycopgConnectionFactory",
    "RelationalConnection",
    "RelationalConnectionFactory",
    "RelationalServingError",
    "RelationalServingService",
    "ServingAttempt",
    "ServingLineage",
    "ServingRepository",
    "discover_migrations",
    "is_serving_eligible",
    "pending_migrations",
]

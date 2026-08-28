"""Database-free discovery and history contracts for versioned SQL migrations."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_MIGRATION_NAME = re.compile(
    r"^V(?P<version>[0-9]*[1-9][0-9]*)__"
    r"(?P<description>[a-z0-9]+(?:_[a-z0-9]+)*)\.sql$"
)


class MigrationError(ValueError):
    """Raised when migration files or supplied history violate repository contracts."""


@dataclass(frozen=True, slots=True, order=True)
class Migration:
    """One immutable versioned SQL migration discovered from the repository."""

    version: int
    description: str
    path: Path

    @classmethod
    def from_path(cls, path: Path) -> Migration:
        """Parse a migration filename without reading or executing its SQL."""
        match = _MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"invalid migration filename: {path.name}")
        return cls(int(match["version"]), match["description"], path)


@dataclass(frozen=True, slots=True)
class AppliedMigration:
    """Database-neutral representation of an immutable migration-history row."""

    version: int
    description: str
    checksum: str
    applied_at: datetime


def discover_migrations(directory: Path) -> tuple[Migration, ...]:
    """Discover valid SQL migrations in strict version order and reject duplicates."""
    migrations = sorted(Migration.from_path(path) for path in directory.glob("V*.sql"))
    versions = [migration.version for migration in migrations]
    duplicates = sorted({version for version in versions if versions.count(version) > 1})
    if duplicates:
        raise MigrationError(f"duplicate migration versions: {duplicates}")
    return tuple(migrations)


def pending_migrations(
    available: Iterable[Migration], applied: Iterable[AppliedMigration]
) -> tuple[Migration, ...]:
    """Return ordered unapplied migrations from supplied in-memory history."""
    ordered = tuple(sorted(available))
    available_versions = [migration.version for migration in ordered]
    if len(available_versions) != len(set(available_versions)):
        raise MigrationError("available migration versions must be unique")
    applied_versions = [migration.version for migration in applied]
    if len(applied_versions) != len(set(applied_versions)):
        raise MigrationError("applied migration history contains duplicate versions")
    unknown = sorted(set(applied_versions) - set(available_versions))
    if unknown:
        raise MigrationError(f"history contains unknown migration versions: {unknown}")
    return tuple(migration for migration in ordered if migration.version not in applied_versions)

"""Small, deterministic configuration boundary with no file or cloud side effects."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

_PREFIX = "SDPA_"
_ENVIRONMENTS = frozenset({"development", "production"})
_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
_DEFAULT_ENVIRONMENT = "development"
_DEFAULT_LOG_LEVEL = "INFO"
_DEFAULT_SERVICE_NAME = "sales-data-platform-azure"


class ConfigurationError(ValueError):
    """Raised when application configuration is invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated, non-secret foundation settings."""

    environment: str = _DEFAULT_ENVIRONMENT
    log_level: str = _DEFAULT_LOG_LEVEL
    service_name: str = _DEFAULT_SERVICE_NAME

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build settings from an explicit mapping or the process environment."""
        values = os.environ if environ is None else environ
        settings = cls(
            environment=values.get(f"{_PREFIX}ENVIRONMENT", _DEFAULT_ENVIRONMENT).strip().lower(),
            log_level=values.get(f"{_PREFIX}LOG_LEVEL", _DEFAULT_LOG_LEVEL).strip().upper(),
            service_name=values.get(f"{_PREFIX}SERVICE_NAME", _DEFAULT_SERVICE_NAME).strip(),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Reject invalid values before runtime work begins."""
        if self.environment not in _ENVIRONMENTS:
            raise ConfigurationError(f"SDPA_ENVIRONMENT must be one of {sorted(_ENVIRONMENTS)}")
        if self.log_level not in _LOG_LEVELS:
            raise ConfigurationError(f"SDPA_LOG_LEVEL must be one of {sorted(_LOG_LEVELS)}")
        if not self.service_name:
            raise ConfigurationError("SDPA_SERVICE_NAME must not be empty")

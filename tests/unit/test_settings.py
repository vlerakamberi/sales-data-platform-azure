import pytest

from sales_data_platform_azure.config import ConfigurationError, Settings


def test_settings_have_safe_local_defaults() -> None:
    assert Settings.from_environment({}) == Settings()


def test_settings_normalize_environment_values() -> None:
    settings = Settings.from_environment(
        {
            "SDPA_ENVIRONMENT": " PRODUCTION ",
            "SDPA_LOG_LEVEL": " warning ",
            "SDPA_SERVICE_NAME": "worker",
        }
    )
    assert settings == Settings(
        environment="production", log_level="WARNING", service_name="worker"
    )


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("SDPA_ENVIRONMENT", "test"),
        ("SDPA_LOG_LEVEL", "TRACE"),
        ("SDPA_SERVICE_NAME", "  "),
    ],
)
def test_settings_reject_invalid_values(variable: str, value: str) -> None:
    with pytest.raises(ConfigurationError):
        Settings.from_environment({variable: value})

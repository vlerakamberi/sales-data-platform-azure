# Windows Development Guide

## Prerequisites and installation

Use CPython 3.13 (`>=3.13,<3.14`) and PowerShell from the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The editable install exposes the `src` package while source changes remain local. The `dev` extra
installs pytest, pytest-cov, and Ruff. `python -m pip check` validates dependency integrity.

## Configuration and environments

```powershell
Copy-Item .env.example .env
$env:SDPA_ENVIRONMENT = "development"
$env:SDPA_LOG_LEVEL = "INFO"
```

The package reads the process environment and does not parse `.env` automatically. Do not place
production values in local files. `development` and `production` are configuration conventions,
not provisioned environments. Production must use isolated resources and managed identity later.

## Quality and test workflow

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m pip check
python -c "from sales_data_platform_azure.config import Settings; print(Settings.from_environment())"
```

Unit tests cover pure foundation behavior. Contract tests verify bootstrap assumptions. The
integration boundary intentionally has no executable tests because Unit 1 has no cloud integration.
No test requires Azure access.


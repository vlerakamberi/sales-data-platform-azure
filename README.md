# Northstar Retail Sales Data Platform — Azure

This is Repository 2 of the Northstar Retail data-engineering portfolio. It contains the governed
Azure platform foundation for **Milestone 1 — Cloud Data Platform Foundation** and remains
independent of the frozen Repository 1 ETL implementation.

## Purpose and architecture direction

The approved target uses Azure Data Factory (ADF) for managed ingestion and orchestration, ADLS
Gen2 raw/processed/curated layers, managed containerized Python on Azure Container Apps Jobs for
transformation, a distinct data-quality boundary, and Azure Database for PostgreSQL as a bounded
serving layer. Entra ID, managed identities, least-privilege RBAC, and Key Vault form the identity
and secret hierarchy. Azure Monitor and Log Analytics are the later observability direction.

These components describe approved architecture. **Infrastructure is defined but not provisioned.**
No Azure resource currently exists as a result of this repository. Development and production are
represented as isolated parameterized environments; replay will begin from the durable raw boundary.

See the [architecture baseline](docs/architecture/baseline.md), [business requirements
summary](docs/architecture/business-requirements.md), and [accepted ADRs](docs/adr/README.md).

## Current implementation status

Unit 1 established the repository foundation. Unit 2 adds locally validated Bicep definitions for
the approved Azure resource boundaries. Milestone 1 is not complete; Units 3–10 remain unimplemented,
and no infrastructure deployment is authorized.

## Development setup (Windows PowerShell)

CPython 3.13.x is required; the supported range is `>=3.13,<3.14`.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

The package reads `SDPA_*` values from the process environment. It deliberately does not load
`.env` implicitly. Defaults are safe for local development.

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m pip check
python -c "import sales_data_platform_azure"
```

Use `python -m ruff format .` to format locally. See the [development guide](docs/development/setup.md).

## Security

Never commit secrets or shared production credentials. `.env` and common credential artifacts
are ignored; `.env.example` contains safe, non-secret examples only. Later Azure implementation
must prefer Entra ID and managed identities, use least-privilege RBAC, and use Key Vault only
when a secret is unavoidable. See the [security baseline](docs/security/baseline.md).

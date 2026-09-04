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

These components describe the implemented architecture. Repository 2 and Milestone 1 are
**COMPLETE AND VALIDATED**. The governed development Azure foundation was provisioned and validated
where recorded in the Milestone 1 evidence; production remains definition-only. Development and
production are represented as isolated parameterized environments, and replay begins from the
durable raw boundary.

See the [architecture baseline](docs/architecture/baseline.md), [business requirements
summary](docs/architecture/business-requirements.md), and [accepted ADRs](docs/adr/README.md).

## Current implementation status

Units 1–5 established the repository, Bicep, transformation/Data Quality, data-layer, and security
foundations. Units 6–10 added the governed development deployment, managed container execution,
ADF orchestration, private PostgreSQL architecture and activation mechanisms, and integrated
validation evidence. The tracked implementation and evidence preserve the exact boundaries between
locally tested mechanisms, validated development Azure behavior, and formally deferred acceptance.

See the [Unit 3 runtime guide](docs/development/transformation-runtime.md) for its JSON contract,
explicit `ACCEPTED`/`REJECTED`/`FAILED` semantics, local CLI, replay guarantees, and container use.
See the [cloud data layer contract](docs/architecture/data-layer-contract.md) for Unit 4 layer,
identity, deterministic path, replay, quarantine traceability, and no-Azure boundaries.
See the [identity and access boundaries](docs/security/identity-access-boundaries.md) for Unit 5
managed identity, least-privilege, environment isolation, secret reference, and PostgreSQL rules.

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
sdpa-transform --help
```

Use `python -m ruff format .` to format locally. See the [development guide](docs/development/setup.md).

## Security

Never commit secrets or shared production credentials. `.env` and common credential artifacts
are ignored; `.env.example` contains safe, non-secret examples only. Azure implementation prefers
Entra ID and managed identities, uses least-privilege RBAC, and uses Key Vault only
when a secret is unavoidable. See the [security baseline](docs/security/baseline.md).

## Milestone 1 integrated validation

Repository 2 Milestone 1 ? **Cloud Data Platform Foundation** ? has completed its integrated Unit 10
implementation and evidence collection. Governance implementation review and Git closure are
complete for the governed baseline, and Milestone 1 is **COMPLETE AND VALIDATED**.

Validated development-platform evidence includes:

- Azure Data Factory orchestration of the governed Container Apps Job;
- raw ? processed ? curated ADLS progression;
- deterministic replay/idempotency behavior;
- real failure ? diagnosis ? corrected recovery evidence;
- operational traceability across ADF and Container Apps execution history;
- PostgreSQL private infrastructure and private TCP reachability;
- Entra-only PostgreSQL configuration with public access and password authentication disabled;
- final removal of the temporary human ADLS validation role;
- SHIR retained in the deallocated state after validation.

Two limitations remain explicitly governed rather than hidden:

1. **Unit 9.6:** Microsoft Entra Windows sign-in replacement remediation is deferred because the
   Azure for Students Poland Central regional vCPU quota prevented provisioning the approved
   Desktop Experience replacement VM.
2. **PostgreSQL live serving:** authenticated bootstrap/migration/serving acceptance is formally
   deferred because the current governed environment has no compliant human private bootstrap
   execution surface without disproportionate access/guest expansion.

Neither limitation is represented as PASS or as an architecture failure.

Detailed validation evidence and explicit non-claims are recorded in
[`docs/operations/milestone1-validation.md`](docs/operations/milestone1-validation.md).

<!-- UNIT10_MILESTONE1_CLOSURE -->

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

Unit 1 established the repository foundation, and Unit 2 added locally validated Bicep definitions.
Unit 3 adds an independently testable local sales transformation and Data Quality runtime plus a
non-root container definition. Unit 4 adds cloud-neutral contracts for deterministic raw,
processed, curated, and quarantine object addressing without an Azure client or cloud access. Unit
5 defines environment-isolated system identities, bounded RBAC-as-code, and secret-free security
contracts without deployment. Milestone 1 is not complete; Units 6–10 remain unimplemented, and no
infrastructure deployment, cloud integration, or container image push has occurred.

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
are ignored; `.env.example` contains safe, non-secret examples only. Later Azure implementation
must prefer Entra ID and managed identities, use least-privilege RBAC, and use Key Vault only
when a secret is unavoidable. See the [security baseline](docs/security/baseline.md).

## Milestone 1 integrated validation

Repository 2 Milestone 1 ? **Cloud Data Platform Foundation** ? has completed its integrated Unit 10
implementation and evidence collection and is awaiting final Governance implementation review and
Git closure.

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

# Approved Architecture Baseline

Status: **APPROVED / INFRASTRUCTURE DEFINED — NOT PROVISIONED**

## Target flow and boundaries

1. Azure Data Factory provides managed ingestion and orchestration. It coordinates work rather
   than embedding the Python transformation runtime.
2. ADLS Gen2 separates raw, processed, and curated data. Raw is the durable, source-aligned
   recovery and replay boundary; downstream layers can be reproduced under governed rules.
3. Managed containerized Python performs transformation. Azure Container Apps Jobs is the
   approved implementation platform, orchestrated by ADF.
4. Data-quality evaluation remains an explicit boundary rather than an implicit side effect.
5. Azure Database for PostgreSQL provides a bounded relational serving layer. It is not the
   durable system of record or a general-purpose warehouse.

## Security, operations, and cost

Entra ID is the identity plane. Managed identities are preferred, RBAC grants least privilege,
and Key Vault is used only where secrets cannot be eliminated. Development and production
resources, identities, configuration, and data are isolated. Shared production credentials are
prohibited.

Azure Monitor and Log Analytics are the approved later observability direction. Correlation and
execution identifiers support traceability. Recovery favors deterministic reprocessing from the
durable raw boundary. Managed services and bounded job execution avoid idle or duplicate capacity;
scaling, retention, and service tiers must be justified per environment.

## Portfolio and implementation boundaries

Repository 2 owns the Azure platform. Frozen Repository 1 is independent and is not a runtime
dependency. Repositories 3 and 4, dimensional warehousing, and BI are outside this scope.

Unit 2 supplies declarative Bicep definitions for the approved resource boundaries. It does not
provision them. Unit 3 supplies the local deterministic transformation/Data Quality runtime and its
container definition; no image has been built or pushed by repository governance, and no cloud job
is enabled. Unit 4 supplies only cloud-neutral data-layer metadata and deterministic logical
addressing contracts; it neither accesses nor asserts the existence of ADLS objects. ADF pipelines,
ADLS integration, database schemas, detailed RBAC, application diagnostics, and all live Azure
behavior require later authorization.

## Milestone 1 deployed-state reconciliation

The earlier sections preserve the design-stage baseline. Unit 10 adds the following authoritative
deployed-state reconciliation.

The development platform has now demonstrated a governed Northstar path through Azure Data Factory,
the existing Container Apps Job, deterministic transformation/Data Quality behavior, and the raw,
processed and curated ADLS boundaries.

ADF successfully invoked the managed Container Apps execution boundary without relying on SHIR for
the validated Northstar path. Replay retained deterministic accepted-output addressing, and a real
failed invocation was diagnosed and followed by a successful corrected execution.

PostgreSQL remains the approved bounded relational serving platform. Its deployed private
infrastructure, Entra-only configuration, Private Endpoint and private network reachability were
validated. Live authenticated serving activation was not executed and is formally deferred because
the governed environment does not currently provide a compliant human private bootstrap execution
surface without disproportionate access/guest expansion.

The separate Unit 9.6 Microsoft Entra Windows sign-in remediation also remains deferred because the
approved replacement VM could not be provisioned within the Azure for Students regional vCPU quota.

Neither governed limitation changes the architectural decision that ADLS is the durable source and
replay boundary and PostgreSQL is only a bounded relational serving projection.

See [`../operations/milestone1-validation.md`](../operations/milestone1-validation.md) for the
integrated validation evidence and explicit unvalidated claims.

<!-- UNIT10_MILESTONE1_CLOSURE -->

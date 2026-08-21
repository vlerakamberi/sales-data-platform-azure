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
provision them. ADF pipelines, runnable transformation containers, database schemas, detailed RBAC,
application diagnostics, and all live Azure behavior require later authorization.

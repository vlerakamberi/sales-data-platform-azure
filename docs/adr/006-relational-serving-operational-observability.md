# ADR-006 — Relational Serving and Operational Observability Architecture

- Status: **ACCEPTED**

## Context

Governed accepted sales results need a bounded relational serving destination with replay-safe
identity, minimal lineage, and operational visibility. The current deployed topology is **STATE B**:
the existing Container Apps Environment is not network-capable for the required private PostgreSQL
path. This unit records contracts only and changes no runtime or Azure resource.

## Decision and rationale

Azure Database for PostgreSQL is the relational serving target. The existing governed Container
Apps Job execution boundary owns future persistence, and only `ACCEPTED` transformation results are
eligible. `REJECTED` and technical `FAILED` outcomes do not enter normal relational serving.

Authentication is Microsoft Entra and managed-identity based; password fallback is prohibited.
Connectivity is private only. A later bounded network amendment must provide a network-capable
replacement Container Apps Environment before live connectivity can exist.

Stable business identity is separate from execution identity, and logical source identity is
separate from serving-attempt identity. In particular, an ADF RunId is trace metadata and never a
business uniqueness key. Serving retains only the lineage needed to relate business state to its
logical source, execution, correlation, and distinguishable persistence attempt.

Serving is deterministic and idempotent. Replaying a logical business fact under a new execution
or attempt does not duplicate business state, while its attempt history remains distinguishable.
Required business-serving data and required relational lineage commit in one database transaction.
A persistence failure is a technical failure and will propagate through Container Apps Job and ADF
semantics in a later authorized unit.

PostgreSQL schema changes use explicit immutable versioned SQL migrations. Existing Log Analytics
is the preferred observability foundation; PostgreSQL does not become a generic log store. The
PostgreSQL service follows a cost-controlled start/stop lifecycle.

## Consequences

Unit 9.1 defines only configuration, domain, connection-interface, migration, and static schema
contracts. Token acquisition, driver selection, transactions, live persistence, network changes,
failure propagation, telemetry integration, migration execution, and server lifecycle automation
remain later authorized work.

## Repository and portfolio boundaries

Repository 2 owns this bounded serving integration. ADLS remains the durable replay boundary, and
the existing transformation, Data Quality, Container Apps Job, and ADF behavior is unchanged.

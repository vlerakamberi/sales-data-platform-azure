# Unit 9 Relational Serving Contract

Status: **UNIT 9.1 LOCAL CONTRACT — NO DATABASE OR CLOUD ACCESS**

PostgreSQL is a bounded projection of accepted sales state. ADLS remains the durable source and
replay boundary. The future persistence flow is owned by the governed Container Apps Job and must
reject every outcome except `ACCEPTED` before opening a serving transaction.

## Identity and replay

`transaction_id` is the stable sales business key. It is not an execution ID or ADF RunId. The
logical source identity consists of source ID, object ID, contract version, and optional source
version/checksum. An execution ID and correlation ID trace processing; a serving attempt ID traces
one persistence attempt. Replays may change all attempt identities without changing the business
key or logical source.

The schema therefore keeps one `sales_transaction` row per business key and separate
`serving_attempt` rows. A junction retains minimal transaction-to-attempt lineage. Future serving
code must write required business state, the attempt, and their lineage atomically. A rollback or
commit failure is a technical failure; Unit 9.1 does not implement that runtime behavior.

## Schema and migration ownership

SQL under `sql/migrations` is explicitly versioned and intended to be immutable once applied.
`serving.schema_migration_history` is the future database-side authority for applied version,
description, checksum, and application timestamp. Local Python contracts discover files, reject
duplicate versions, and calculate pending versions from supplied history; they do not connect or
execute SQL.

The schema stores serving facts and minimal lineage, not rejected payloads, technical failures,
general logs, or broad operational telemetry. Existing Log Analytics remains the preferred
observability foundation.

## Connectivity boundary

Configuration contains only host, database, port, encrypted transport policy, and an optional
managed-identity client ID. Password configuration is rejected. The current STATE B topology has
no authorized private path; a later bounded network amendment and network-capable replacement
Container Apps Environment are prerequisites for live connectivity.

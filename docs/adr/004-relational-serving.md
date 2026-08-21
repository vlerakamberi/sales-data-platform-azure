# ADR-004 — Relational Serving Platform

- Status: **ACCEPTED**

## Context

Some approved consumers need relational access, but the relational platform must not replace the
durable lake boundary or expand into an unapproved enterprise warehouse.

## Decision and rationale

Use **Azure Database for PostgreSQL as a bounded relational serving layer**. It supplies managed
relational capabilities for defined needs while ADLS remains the durable data and replay boundary.

## Consequences

Only governed serving data is published. Schema migration, load idempotency, access, recovery,
capacity, and cost require later implementation. Dimensional warehouse concerns remain excluded.

## Repository and portfolio boundaries

Repository 2 owns the bounded serving integration. Unit 1 includes only an empty migration
boundary and creates no server, database, schema, connection, or migration.


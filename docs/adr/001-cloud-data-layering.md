# ADR-001 — Cloud Data Layering and Durable Raw Boundary

- Status: **ACCEPTED**

## Context

Cloud ingestion needs an auditable landing point and reproducible downstream processing without
making serving systems the authoritative data store.

## Decision and rationale

Use ADLS Gen2 with explicit raw, processed, and curated boundaries. Preserve raw data as the
durable, source-aligned recovery and replay boundary. This separates ingestion from transformation
and permits governed reprocessing when downstream logic changes or execution fails.

## Consequences

Lifecycle, retention, naming, access, and promotion between layers require governance. Storage
may be duplicated intentionally, but curated or PostgreSQL outputs can be rebuilt from retained
raw inputs. Unit 1 documents the decision; later units implement it.

## Repository and portfolio boundaries

Repository 2 owns the Azure data layers. Repository 1 remains frozen and independent; warehouse,
BI, and other portfolio repositories are outside this decision.


# ADR-002 — Managed Orchestration Boundary

- Status: **ACCEPTED**

## Context

Ingestion, dependency coordination, retries, and execution visibility need a managed control
plane without coupling business transformation code to the orchestrator.

## Decision and rationale

Use Azure Data Factory for managed ingestion and orchestration. ADF coordinates bounded work and
invokes transformation compute; it does not host Python transformation logic. This supplies an
Azure-native control plane while keeping processing independently testable.

## Consequences

Pipelines, triggers, retry rules, parameters, and observability require later governed
implementation. Transformation interfaces must be explicit and idempotent where practical.

## Repository and portfolio boundaries

The decision applies to Repository 2 cloud orchestration only. Unit 1 creates a directory boundary
but no pipeline, linked service, trigger, or Azure resource.


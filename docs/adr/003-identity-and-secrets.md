# ADR-003 — Cloud Identity and Secret Management

- Status: **ACCEPTED**

## Context

The platform requires service-to-service access across isolated environments without embedding
credentials in source, images, configuration, or orchestration definitions.

## Decision and rationale

Use Entra ID, prefer managed identities for Azure workloads, and grant least privilege through
RBAC. Use Key Vault only when a secret is unavoidable. Separate development and production
identities. Identity-first access reduces credential distribution and makes authorization reviewable.

## Consequences

Each workload needs a bounded identity and explicit permissions. Local development must use
individual, approved authentication rather than shared production credentials. Secret rotation
and audit remain required where secrets exist.

## Repository and portfolio boundaries

Repository 2 will define its cloud access in a later unit. Unit 1 provisions no identity, role
assignment, credential, or vault and makes no change to other repositories.


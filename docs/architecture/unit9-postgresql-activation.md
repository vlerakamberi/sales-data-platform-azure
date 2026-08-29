# Unit 9.5 PostgreSQL Entra Bootstrap and Schema Activation

Status: **REPOSITORY MECHANISM DEFINED — NO LIVE ACTIVATION PERFORMED**

Unit 9.5 defines the bounded, development-only coordination mechanism for preparing PostgreSQL
principals and activating the governed relational schema. It adds no deployment entry point and
performs no network, Azure, or database operation merely by being imported or tested.

## Identity and authorization model

Activation requires two distinct Entra identities. The bootstrap identity obtains a short-lived
token for the Azure PostgreSQL Entra scope and opens the administrative activation session. The
workload identity is never treated as the bootstrap administrator; it is reconciled as the
least-privilege `serving_runtime` PostgreSQL principal. The database adapter owns the exact
idempotent SQL used to map that Entra object and grant only the governed serving privileges.

Static application PostgreSQL passwords, password configuration, embedded tokens, superuser
rights, and public-network fallback are outside the contract. Token acquisition and PostgreSQL
connectivity are injected adapter boundaries, so credential material is neither logged nor stored
in activation results.

## Schema activation and state

The repository's existing `discover_migrations` and `AppliedMigration` contracts remain the sole
migration mechanism and state model. Files are ordered by immutable version. SHA-256 binds each
history row to the exact file, while version and description preserve its existing identity.
History must be a contiguous prefix of discovered migrations; duplicate, unknown, gapped,
description-mismatched, or checksum-mismatched state stops activation before principal or schema
changes.

Within one explicit transaction the coordinator inspects history, reconciles the workload
principal, executes each pending migration in version order, records its history identity, and
commits. A complete history performs no migration SQL, although principal reconciliation remains
idempotent. A statement or commit failure triggers rollback and produces no success result. A
rollback failure is explicitly reported; operators must inspect database state before authorizing
a retry. Every retry obtains fresh history rather than trusting prior in-memory progress.

Successful results record activated and previously applied versions, whether reconciliation made
a change, and an `ACTIVATED` or `UNCHANGED` status. Evidence for a future authorized operation must
retain the validated target, bootstrap/workload object IDs, ordered state inspection, transaction
outcome, structured result, and relevant private-connectivity logs without retaining tokens.

## Operational and lifecycle boundary

Only a target explicitly marked `development`, using `verify-full`, an Azure PostgreSQL DNS name,
and confirmed private connectivity is accepted. Unit 9.3's Private Endpoint and DNS plus Unit
9.4's network-capable replacement Job are prerequisites. Unit 9.5 changes neither unit and does
not prove that connectivity or activation has occurred.

Starting PostgreSQL, acquiring real tokens, connecting, reconciling live principals, executing SQL,
or recovering a failed activation requires separate operational authorization. The server must be
started only for the bounded activation window and returned to its governed stopped/resting state
after evidence collection. Unit 9.6 owns live serving integration and validation. Unit 9.7 owns
cutover and legacy retirement. This unit does not modify ADF, triggers, Azure RBAC, Container Apps,
production configuration, or the legacy environment.

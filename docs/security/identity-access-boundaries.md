# Identity and Access Boundaries

Status: **UNIT 5 DEFINITIONS ONLY — NOT DEPLOYED**

This document defines environment-isolated workload identity, least-privilege RBAC, secret
reference, and database authentication boundaries. It does not assert that identities or role
assignments are active, secrets exist, or any Azure resource has been provisioned.

## Workload identities and isolation

Azure Data Factory and the transformation Container Apps Job each use their own system-assigned
managed identity. Development and production deploy separate resources, so neither identity is
shared across environments. User-assigned identities, shared service principals, and shared
development/production credentials are prohibited.

Local security contracts accept only `dev` and `prod`, system-assigned identity, the ADF and
transformation workloads, and exact supported resource types. They reject cross-environment role
relationships, subscription or resource-group scopes, unsafe resource identifiers, inappropriate
principal/role/scope combinations, and unapproved role names.

## Defined RBAC relationships

The security module is conditional on `deployTransformationJob`. Because that parameter remains
`false`, these definitions do not currently create assignments.

| Principal | Built-in role and definition ID | Exact scope | Reason |
| --- | --- | --- | --- |
| Transformation job system identity | AcrPull — `7f951dda-4ed3-4680-a7ca-43fe172d538d` | Environment ACR | Pull the runtime image without push permission. |
| Transformation job system identity | Storage Blob Data Contributor — `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | Environment raw container | Read raw input; see the granularity limitation below. |
| Transformation job system identity | Storage Blob Data Contributor — `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | Environment processed container | Write normalized output. |
| Transformation job system identity | Storage Blob Data Contributor — `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | Environment curated container | Write accepted output. |
| Transformation job system identity | Storage Blob Data Contributor — `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | Environment quarantine container | Write rejected output. |
| ADF system identity | Container Apps Jobs Operator — `b9a307c4-5aa3-4b52-ba60-2b17c136cd7b` | Exact environment transformation job | Read, start, and stop the governed job. |

Every assignment name is deterministic from exact scope ID, principal ID, and role definition ID.
There are no Owner, Contributor, User Access Administrator, AcrPush, custom-role, subscription, or
resource-group assignments.

ADF remains orchestration-only. Container Apps Jobs Operator is the narrowest applicable built-in
role, but it is not a start-only permission: it includes job read/action permissions and associated
job operations. Exact job scope bounds that built-in-role granularity. Contributor is not used as a
fallback.

## ADLS logical policy and Azure granularity

The application contract remains:

- raw: read only;
- processed: write as required;
- curated: write as required;
- quarantine: write as required;
- routine delete: prohibited for every layer.

Storage Blob Data Contributor is assigned separately at each exact container, not at storage
account, resource-group, or subscription scope. The built-in role nevertheless grants read, write,
and delete data actions. Azure RBAC therefore does **not** enforce the finer raw-read-only or
no-routine-delete application policy. Runtime behavior, immutable addressing, operational controls,
and later authorized ADLS ACL design must preserve that logical restriction; this definition does
not claim stronger enforcement than the role provides.

## ACR and Key Vault

The workload receives AcrPull only at its specific registry. AcrPush is prohibited.

Key Vault references contain only environment, logical vault name, logical secret name, and
configuration purpose. The contract deliberately has no secret-value field. References must remain
within their environment. No approved workload secret is currently required, so no Key Vault
Secrets User assignment is instantiated. If Governance later approves a concrete secret reference,
that role may be assigned only to the transformation identity at its specific environment vault.
Secret values, passwords, SAS tokens, account keys, connection strings, and secret values in
`.bicepparam` or `.env.example` remain prohibited.

## PostgreSQL boundary

PostgreSQL remains Entra-only ready: Active Directory authentication is enabled, password
authentication is disabled, and public network access is disabled. A future environment-specific
transformation Entra principal is the application authentication boundary. The administrator must
be a separate identity and must never be used as the runtime application identity.

Unit 5 creates no database user, role, grant, schema, migration, connection, administrator, or Entra
principal. PostgreSQL activation requires later authorization.

## Non-deployment boundary

No Azure login, deployment, live RBAC write, managed identity operation, secret read/write, ADLS
access, ACR push, Container Apps execution, ADF execution, or PostgreSQL action is part of Unit 5.

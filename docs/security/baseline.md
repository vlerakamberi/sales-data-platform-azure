# Unit 1 Security Baseline

- Never store secrets in Git, source, images, logs, examples, or committed configuration.
- Prefer Entra ID and workload managed identities; do not distribute shared credentials.
- Grant least-privilege RBAC to distinct workload identities.
- Use Key Vault only when a secret cannot be removed through identity-based authentication.
- Isolate development and production resources, identities, data, configuration, and access.
- Prohibit shared production credentials and production secrets in local development.
- Keep local `.env` files untracked. Commit only safe examples in `.env.example`.
- Treat correlation identifiers as operational metadata, never as storage for sensitive values.
- Avoid secrets in log messages; structured formatting cannot sanitize arbitrary caller messages.

Unit 1 creates no live identity, Key Vault, role assignment, or other Azure resource.

Unit 5 adds conditional, definition-only workload RBAC and local secret-free security contracts; see
[identity and access boundaries](identity-access-boundaries.md). No security definition has been
deployed and no live identity, assignment, or secret operation has occurred.

## Milestone 1 validated security-state amendment

The earlier Unit-specific statements preserve the definition-stage history. Unit 10 final evidence
confirmed the following deployed development security state:

- PostgreSQL public network access is disabled;
- PostgreSQL password authentication is disabled;
- Microsoft Entra authentication is enabled;
- the governed PostgreSQL Private Endpoint is provisioned and approved;
- no PostgreSQL public-access fallback was introduced;
- no human access token was transmitted through Azure Run Command;
- the SHIR SystemAssigned identity was not substituted for the approved bootstrap human;
- the PostgreSQL workload managed identity was not substituted for the human bootstrap identity;
- no ungoverned credential fallback was used;
- the temporary human Storage Blob Data Reader assignment used for final ADLS inspection was
  removed and verified absent;
- the retained SHIR VM was verified deallocated.

Live PostgreSQL serving activation remains formally deferred and must not be described as a security
PASS or FAIL for an authenticated database session because no such session occurred.

The separate Unit 9.6 Microsoft Entra Windows-login remediation remains quota-constrained and was
not reopened during Unit 10.

See [`../operations/milestone1-validation.md`](../operations/milestone1-validation.md).

<!-- UNIT10_MILESTONE1_CLOSURE -->

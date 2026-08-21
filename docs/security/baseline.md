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

# Unit 9.1 Relational Serving Development Guide

This unit is fully local and database-free. It adds pure domain/configuration contracts, an opaque
future connection interface, migration discovery/history logic, and static PostgreSQL SQL. It does
not select a driver, acquire an Entra token, open a connection, or apply a migration.

For local contract tests, run:

```powershell
python -m pytest tests/unit/test_relational_contracts.py tests/contract/test_relational_schema_contract.py
```

The future runtime may supply `SDPA_POSTGRESQL_HOST`, `SDPA_POSTGRESQL_DATABASE`,
`SDPA_POSTGRESQL_PORT`, `SDPA_POSTGRESQL_SSLMODE`, and optionally
`SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID`. These names document non-secret configuration only.
`SDPA_POSTGRESQL_PASSWORD` and `PGPASSWORD` are explicitly rejected; do not add them to `.env`.

Migration files follow `V<positive integer>__<lowercase_description>.sql`. Never edit an applied
migration; add the next monotonic version. Unit 9.1 performs no migration application.

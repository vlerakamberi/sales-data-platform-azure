# Unit 9.1 Relational Serving Development Guide

Unit 9.1 added pure domain/configuration contracts, migration discovery/history logic, and static
PostgreSQL SQL. Unit 9.2 adds a Psycopg adapter, atomic serving repository, lifecycle observability,
and an injectable post-`ACCEPTED` managed-runtime boundary. Local validation remains database-free:
tests replace connections and credential providers with fakes. No Entra token is acquired, no live
connection is opened, and no migration is applied by repository validation.

For local contract tests, run:

```powershell
python -m pytest tests/unit/test_relational_contracts.py tests/unit/test_relational_runtime.py `
  tests/integration/test_managed_execution.py tests/contract/test_relational_schema_contract.py
```

The future runtime may supply `SDPA_POSTGRESQL_HOST`, `SDPA_POSTGRESQL_DATABASE`,
`SDPA_POSTGRESQL_USER`,
`SDPA_POSTGRESQL_PORT`, `SDPA_POSTGRESQL_SSLMODE`, and optionally
`SDPA_POSTGRESQL_MANAGED_IDENTITY_CLIENT_ID`. These names document non-secret configuration only.
`SDPA_POSTGRESQL_PASSWORD` and `PGPASSWORD` are explicitly rejected; do not add them to `.env`.

The concrete adapter accepts credential material only through `PostgreSQLCredentialProvider` and
passes it directly to Psycopg for connection authentication. It never acquires, stores, or logs a
token. A later authorized composition root must supply the Entra implementation.

The managed execution runner accepts an injected `RelationalServingService`. It calls that service
only after transformation and blocking Data Quality produce `ACCEPTED`; `REJECTED` and pre-serving
`FAILED` results bypass it. A relational transaction failure returns the inherited `FAILED` outcome
with `RELATIONAL_SERVING_FAILED`, so the existing nonzero Job/ADF technical-failure path applies.

One serving transaction upserts all accepted business rows by stable `transaction_id`, inserts one
new attempt, inserts required lineage for each business row, and commits. Any statement or commit
failure rolls back the transaction. Events `RELATIONAL_SERVING_STARTED`,
`RELATIONAL_SERVING_SUCCEEDED`, and `RELATIONAL_SERVING_FAILED` contain only allowlisted metadata.

Migration files follow `V<positive integer>__<lowercase_description>.sql`. Never edit an applied
migration; add the next monotonic version. Unit 9.1 performs no migration application.

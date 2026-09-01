# PostgreSQL Entra bootstrap command

The development bootstrap command is an explicit repository operation:

```text
python -m sales_data_platform_azure.relational.bootstrap
```

It composes and invokes the existing `PostgreSQLActivator`; it does not replace that coordinator or
the migration history and checksum rules it enforces. The authoritative migration source is the
repository's existing `sql/migrations` directory.

The temporary human PostgreSQL Entra administrator has separate display-name, object-ID, and login
metadata. Psycopg uses the explicitly configured, verified Entra UPN as its PostgreSQL username; the
display name is never used as the database username. The UPN is identity metadata, not a password or
secret. The dedicated PostgreSQL user-assigned managed identity remains a distinct, non-administrator
workload principal reconciled to `serving_runtime`. Its client ID and object ID are never
interchangeable with the human administrator's metadata.

Activation never runs during imports, installation, tests, or normal transformation execution. Run
this command only after the governed implementation review and separate operational authorization.
It requires private connectivity, `verify-full` TLS, the approved identity metadata, and explicit
non-secret PostgreSQL configuration. PostgreSQL passwords, `PGPASSWORD`, client secrets, embedded
tokens, and password authentication are not supported.

# SQL migration boundary

Unit 9.1 introduces explicit, immutable, versioned PostgreSQL SQL migrations. Filenames use
`V<positive integer>__<lowercase_description>.sql`; versions are unique and increase monotonically.

`V001__create_relational_serving_foundation.sql` is the first inherited migration because the
repository contained no prior migration files. It defines only accepted sales-serving state,
distinguishable serving attempts/minimal lineage, and migration history. It is not applied by this
unit. Future migration tooling owns checksums and inserts into `serving.schema_migration_history`.

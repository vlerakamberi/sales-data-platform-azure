# Cloud Data Layer Contract

Status: **UNIT 4 LOCAL CONTRACT — NO CLOUD ACCESS**

Unit 4 defines cloud-neutral logical addresses and metadata for Repository 2 data objects. It does
not connect to ADLS, provision a storage account, or imply that any addressed object exists.

## Governed layers

- **raw** is the immutable, append-oriented source and replay boundary. Its address is derived from
  stable source identity and never from an execution ID. It is not a mutable transformation target.
- **processed** represents structurally transformed or normalized data. It retains source lineage
  but does not imply final business acceptance.
- **curated** represents business-ready output that passed blocking Data Quality expectations. It
  is not a database, warehouse, semantic model, or BI serving layer.
- **quarantine** represents governed rejection. Its metadata retains source, execution and
  correlation identities, failed expectation IDs, and a safe rejection classification and reason.

Only `dev` and `prod` are supported. The environment is the first address component, so equivalent
logical objects remain isolated between environments.

## Deterministic path model

Every logical address is built centrally as:

```text
<environment>/<layer>/<source-system>/<dataset>/year=YYYY/month=MM/day=DD/<object-name>
```

For example:

```text
dev/raw/northstar-pos/sales/year=2026/month=08/day=21/sales-<stable-hash>.json
prod/processed/northstar-pos/sales/year=2026/month=08/day=21/sales-<stable-hash>.json
prod/curated/northstar-pos/sales/year=2026/month=08/day=21/sales-<stable-hash>.json
prod/quarantine/northstar-pos/sales/year=2026/month=08/day=21/sales-<attempt-hash>.json
```

Object names use a SHA-256 digest of stable artifact/source identity plus a validated format
extension. Raw, processed, and curated names do not depend on execution identity. Quarantine names
also incorporate execution identity so separate rejected attempts remain distinguishable while
their metadata continues to retain the stable raw source identity.

Path inputs are normalized to lowercase where appropriate and reject empty identifiers, traversal,
absolute or relative paths, injected `/` or `\` separators, unsafe fragments, unknown layers,
unknown environments, and unsafe extensions. Logical addresses always use `/`, independent of the
host operating system.

## Identity and replay

Source identity is immutable lineage: source system, logical object, contract version, and optional
source version/checksum. Execution identity describes one processing attempt and may change during
a replay. Therefore two executions of the same logical source reuse the same raw address and derive
the same processed or curated address when governed content identity is equivalent. Execution and
correlation IDs remain separate trace metadata.

The bounded adapter maps existing Unit 3 accepted results to curated contracts and rejected results
to quarantine contracts. Failed transformations do not create storage-object contracts. Unit 3 has
no dependency on Unit 4.

## Explicit boundary

The implementation uses only the Python standard library. It has no Azure SDK, credentials,
endpoints, account names, connection strings, filesystem client, or read/write behavior. No Azure
login, ADLS operation, ADF orchestration, Container Apps execution, managed identity, or PostgreSQL
serving is part of this contract.

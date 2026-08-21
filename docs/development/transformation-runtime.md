# Unit 3 Transformation and Data Quality Runtime

The Unit 3 runtime transforms one local Northstar raw sales transaction batch into an explicit
structured result. It is deterministic, has no persistent side effects, and requires no Azure,
ADLS, ADF, PostgreSQL, Key Vault, or managed identity connection.

## Input contract

Input is a UTF-8 JSON object read from `--input <file>` or stdin with `--input -`:

```json
{
  "contract_version": "1.0",
  "source": {
    "source_id": "northstar-pos",
    "object_id": "sales/2026-08-21/batch-001.json",
    "version": "1",
    "checksum": "sha256:logical-source-checksum"
  },
  "records": [
    {
      "transaction_id": "tx-001",
      "sku": "sku-100",
      "quantity": 2,
      "unit_price": "12.50",
      "transaction_timestamp": "2026-08-21T09:30:00+02:00",
      "channel": "store"
    }
  ]
}
```

The source identity describes immutable logical input. `execution_id` identifies one processing
attempt. A replay can use another execution ID while retaining the same source identity.

## Outcomes and quality rules

- `ACCEPTED`: parsing, canonical transformation, and blocking quality checks succeeded. The result
  carries curated artifact metadata and canonical records.
- `REJECTED`: transformation succeeded, but a blocking expectation failed. The result carries
  quarantine artifact metadata, source/execution/correlation identity, failed expectation IDs,
  safe details, record references, and canonical records. This is not a runtime error.
- `FAILED`: input was structurally malformed, used an unsupported contract, violated a
  transformation invariant, had invalid runtime configuration, or encountered an unexpected error.

The bounded blocking expectations are positive quantity, non-negative unit price, and transaction
ID uniqueness within a batch. This is not a generic rule engine.

Accepted and rejected results exit `0`; failed execution exits `2`. Every request emits a JSON
result to stdout. Structured operational logs go to stderr and include execution/correlation IDs,
stage, outcome, safe failure classification, and failed expectation IDs—not the raw payload.

## Local execution

After the editable install:

```powershell
sdpa-transform --input .\batch.json `
  --execution-id local-run-1 `
  --correlation-id local-correlation-1

Get-Content .\batch.json -Raw | sdpa-transform --input -
```

Equivalent module invocation:

```powershell
python -m sales_data_platform_azure.transformation.cli --input .\batch.json
```

## Determinism and replay

Canonical timestamps are normalized to UTC, monetary values use `Decimal`, output serialization is
stable, and artifact checksums are derived from canonical business records. Execution and
correlation IDs remain trace metadata and do not alter business output. Repeating the same logical
source, input, contract, and configuration therefore yields equivalent records, quality results,
and artifact metadata without locks or persisted idempotency state.

## Container boundary

See [the container guide](../../containers/transformation/README.md). The local image definition
runs as a non-root user and needs no Azure network access. No image has been pushed; the Container
Apps Job remains disabled, and ACR pull authorization, ADF invocation, ADLS I/O, and PostgreSQL
serving are deferred to later governed units.

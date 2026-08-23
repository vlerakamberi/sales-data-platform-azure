# ADF orchestration operations

Unit 8 is a development-only orchestration layer over the existing Data Factory and Unit 7
Container Apps Job. It performs no transformation or Data Quality business logic.

## Run contract and topology

Supply `dataset`, `partitionDate`, `sourceId`, `sourceObjectId`, `inputBlob`, `contractVersion`, and
the deployment `subscriptionId`. The first six values identify an already-landed governed raw
object; no external source connector is used.

The pipeline validates those required values, derives `execution-id` as
`unit8-adf-<ADF Pipeline RunId>` and `correlation-id` as the pipeline `RunId`, starts
`nsrsdp-dev-transform-job`, captures its execution name, and polls its ARM execution resource every
15 seconds. Poll reads have at most two retries at 30-second intervals. The start operation is never
retried. Polling has a 25-minute hard timeout, below the existing 30-minute Job timeout.

Source identity stays stable when the same raw object is replayed. Each ADF rerun has a fresh RunId,
so execution and correlation identities are fresh and distinct from source identity.

## Identity and outcomes

Web activities authenticate to `https://management.azure.com/` with the ADF SystemAssigned managed
identity. Its only Unit 8 grant is Container Apps Jobs Operator on the exact transformation Job.
No credential is stored and no Storage data-plane role is added.

- `Succeeded`: the technical Job execution succeeded; ADF succeeds.
- `Rejected`: Unit 7 records governed DQ rejection but exits successfully; ADF succeeds.
- `Failed`: the technical Job execution failed; an ADF Fail activity fails the pipeline.

Use ADF pipeline and activity run history with the captured Container Apps execution name to trace
RunId, source identity, raw object, start time, execution status, timestamps, and rerun attempt.

## Schedule and deployment safety

`nsrsdp-dev-sales-schedule` runs at most weekly and is defined with `runtimeState` `Stopped`. Do not
activate it during local validation or deployment review. The Unit 8 Bicep graph references existing
resources; it does not recreate the factory or Job and has no PostgreSQL or production surface.

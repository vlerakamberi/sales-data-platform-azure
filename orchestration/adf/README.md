# Azure Data Factory orchestration

Unit 8 adds development-only orchestration to the existing
`nsrsdp-dev-2gndgslsp4a6c-adf` factory. The factory remains orchestration-only: it validates the
governed raw-object parameter contract, starts the existing Container Apps transformation Job,
and observes the resulting execution to a terminal state.

## Artifacts

- `pipelines/northstar-sales-orchestration.json` defines `nsrsdp-dev-sales-orchestration`.
- `triggers/northstar-sales-schedule.json` defines the stopped, weekly development schedule
  `nsrsdp-dev-sales-schedule`. It must not be activated by this unit.

Web activities use the factory SystemAssigned identity against Azure Resource Manager. No linked
service, source connector, credential, secret, SAS token, account key, Storage data-plane grant, or
PostgreSQL dependency is introduced. Transformation and Data Quality remain in the Unit 7 container.

ADF history plus the captured Container Apps execution name provides operational evidence. `RunId`
is the correlation ID and `unit8-adf-<RunId>` is the execution ID. Governed DQ rejection remains a
successful Job/ADF outcome; technical Job failure fails the ADF run.

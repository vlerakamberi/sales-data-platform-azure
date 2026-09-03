
# Milestone 1 Integrated Validation and Closure Evidence

Status: **UNIT 10 CLOSURE EVIDENCE IMPLEMENTED ? FINAL GOVERNANCE REVIEW PENDING**

This document records the final integrated validation evidence for Repository 2 Milestone 1 ?
**Cloud Data Platform Foundation**. It distinguishes validated behavior from formally governed
limitations and must not be interpreted as proof of capabilities that were not executed.

## Integrated Northstar validation

The governed development flow was validated across the deployed Azure orchestration and lake
boundaries:

**ADF ? Container Apps Job ? transformation / Data Quality ? ADLS processed / curated**

Successful Azure Data Factory run:

`89ac17b8-a7d7-11f1-9b70-f47b096f2c09`

Result:

**Succeeded**

Successful Container Apps Job execution:

`nsrsdp-dev-transform-job-kwo3p30`

Result:

**Succeeded**

The successful orchestration used:

- `inputBlob = batch-001.json`
- `sourceObjectId = raw/batch-001.json`

The runtime produced the governed processed and curated outputs while preserving deterministic
accepted-output addressing.

## Replay and idempotency

Replay validation confirmed that the same logical source produces the same governed accepted-output
identity rather than an additional accepted business artifact.

Execution identity remains distinct from stable source/business identity. A rerun may therefore
have a new ADF RunId and execution metadata without creating duplicate accepted business state.

ADLS remains the durable recovery and replay boundary.

## Failure, diagnosis and recovery

A real technical failure was preserved as operational evidence.

Failed ADF run:

`62858eed-a7d6-11f1-ba85-f47b096f2c09`

Failed Container Apps Job execution:

`nsrsdp-dev-transform-job-oyy9sfg`

The failed invocation passed:

`inputBlob = raw/batch-001.json`

instead of the blob name relative to the configured raw container.

The contract error was diagnosed without platform redesign. A corrected execution using
`inputBlob = batch-001.json` subsequently succeeded.

This establishes an observable failure ? diagnosis ? correction ? recovery path.

## ADLS closure evidence

Final human read-only closure inspection confirmed the governed:

- raw;
- processed;
- curated;
- quarantine

storage boundaries before the temporary validation privilege was removed.

The final inventory was used only as closure confirmation. Deterministic processed/curated artifact
identity and replay behavior had already been established by the authoritative Unit 10 runtime
evidence.

The temporary human `Storage Blob Data Reader` assignment used only for final inspection was:

`153d7ff9-1495-46ac-bb38-b591cbd5a1a0`

for principal:

`19ec5eb3-0ae2-4e79-bdf1-4e9d9f905313`

at the governed development storage-account scope.

The assignment was removed and independently verified absent.

No validation-only human Storage Blob Data Reader privilege remains.

## Observability and supportability

The successful and failed ADF runs remain independently traceable through Azure execution history
and their corresponding Container Apps Job execution identities.

Successful path:

- ADF: `89ac17b8-a7d7-11f1-9b70-f47b096f2c09`
- Container Apps: `nsrsdp-dev-transform-job-kwo3p30`

Failure path:

- ADF: `62858eed-a7d6-11f1-ba85-f47b096f2c09`
- Container Apps: `nsrsdp-dev-transform-job-oyy9sfg`

Execution status, timestamps, run identity and failure information provide sufficient operational
traceability for the bounded development platform.

## PostgreSQL infrastructure readiness

The deployed Azure Database for PostgreSQL Flexible Server remained:

- state: `Ready`;
- public network access: `Disabled`;
- password authentication: `Disabled`;
- Microsoft Entra authentication: `Enabled`.

The governed PostgreSQL Private Endpoint remained:

- provisioning state: `Succeeded`;
- connection state: `Approved`.

Private DNS resolution from the retained SHIR private path resolved the PostgreSQL Private Endpoint
to:

`10.42.0.36`

TCP connectivity to PostgreSQL port `5432` from that private path was validated.

Therefore PostgreSQL infrastructure readiness and private network reachability are validated.

## PostgreSQL live-serving limitation

**Live PostgreSQL serving acceptance is formally deferred.**

No live authenticated PostgreSQL bootstrap session was executed.

Accordingly, Milestone 1 does **not** claim that:

- schema migrations were applied live;
- `serving_runtime` was reconciled live;
- serving tables were demonstrated live;
- authenticated PostgreSQL serving passed or failed.

The retained SHIR VM provided the required private PostgreSQL network path but did not contain the
governed Python/Psycopg/Azure Identity bootstrap runtime or an approved human
`AzureCliCredential` execution context.

Governance determined that expanding the guest/access environment solely to convert this closure
criterion into a live PASS was disproportionate to the approved secure and cost-conscious Unit 10
scope.

Status:

**FORMALLY DEFERRED ? CONSTRAINED EXECUTION-ENVIRONMENT LIMITATION**

This is not a PostgreSQL architecture, networking, authentication-design, schema or migration
failure.

## Unit 9.6 limitation

The independent Unit 9.6 determination remains:

**DEFERRED / BLOCKED BY AZURE FOR STUDENTS SUBSCRIPTION QUOTA LIMITATION**

The approved Microsoft Entra Windows sign-in remediation required a Desktop Experience replacement
VM, but the required Poland Central regional vCPU quota increase could not be obtained under the
Azure for Students subscription.

This limitation is separate from the Unit 10 PostgreSQL serving deferral.

Neither limitation may be represented as PASS.

## Security closure state

The final Unit 10 evidence preserves the approved security boundaries:

- PostgreSQL remains private-only;
- PostgreSQL password authentication remains disabled;
- Microsoft Entra authentication remains enabled;
- no PostgreSQL public fallback was introduced;
- no human access token was transmitted through Azure Run Command;
- SHIR SystemAssigned identity was not substituted for the approved human bootstrap identity;
- the PostgreSQL workload managed identity was not substituted for the human bootstrap identity;
- no ungoverned credential fallback was introduced;
- no Unit 9.6 replacement VM was created;
- no additional validation infrastructure was retained;
- the temporary human ADLS reader assignment was removed.

## Cost closure state

The retained SHIR VM:

`nsrsdp-dev-shir-pl-vm`

was independently verified:

**PowerState/deallocated**

and remained deallocated throughout the final closure sequence.

No new validation-only infrastructure was introduced during Unit 10 closure.

Architecturally retained managed Azure services remain governed platform resources rather than
temporary Unit 10 validation resources.

## Recovery model

Recovery continues to favor deterministic replay from the durable raw ADLS boundary.

Operational recovery should:

1. identify the failed ADF run and associated Container Apps execution;
2. distinguish contract/configuration failures from technical runtime failures;
3. preserve the source object and stable source identity;
4. correct the governed invocation or configuration defect;
5. rerun through ADF with a new execution identity;
6. confirm the deterministic processed/curated result;
7. avoid manual mutation of durable raw data.

Rejected Data Quality outcomes remain governed outcomes and must not be confused with technical Job
failure.

## Explicitly unvalidated claims

Milestone 1 closure evidence must not claim:

- Microsoft Entra RDP success on the retained SHIR VM;
- successful replacement SHIR VM deployment;
- live PostgreSQL migration application;
- live PostgreSQL workload-principal reconciliation;
- live PostgreSQL serving-table validation;
- a completed dimensional warehouse or BI layer.

Those capabilities remain outside the validated evidence described here.

## Closure interpretation

Milestone 1 demonstrates a governed Azure data-platform foundation with deployed orchestration,
managed container execution, durable lake boundaries, identity-first security, private relational
infrastructure, replay/recovery behavior, operational traceability and explicit cost controls.

Final `COMPLETE AND VALIDATED` status remains a Governance determination after repository validation,
implementation review and the authorized Git lifecycle complete.

<!-- UNIT10_MILESTONE1_CLOSURE -->

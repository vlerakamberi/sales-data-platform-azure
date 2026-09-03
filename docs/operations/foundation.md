# Operations Foundation

Unit 1 provides structured local logging with optional correlation and execution identifiers. It
does not connect to Azure Monitor or Log Analytics. Callers must never put secrets or sensitive
payloads in log messages or identifiers.

The approved future operating model uses ADF orchestration visibility, bounded Container Apps Job
executions, Azure Monitor and Log Analytics, and deterministic replay from retained raw data.
Alerting, runbooks, retention, recovery objectives, and production support procedures require
later-unit implementation and governance approval.

## Milestone 1 operational validation amendment

Unit 10 converted the earlier operations direction into validated development-platform evidence.

ADF orchestration history and Container Apps Job execution history now provide traceability for both
a successful Northstar execution and a real technical failure followed by corrected recovery.
Deterministic replay from retained raw ADLS data remains the primary recovery model.

Operators must preserve the distinction between Data Quality rejection and technical failure.
A rejected business payload is a governed outcome; a failed Job or failed ADF orchestration is an
operational failure requiring diagnosis before rerun.

The final Milestone 1 closure record is
[`milestone1-validation.md`](milestone1-validation.md).

### Cost and retained-resource state

The SHIR VM is retained but must remain deallocated outside an explicitly governed bounded use
window. Unit 10 final verification recorded `PowerState/deallocated`.

No validation-only Azure infrastructure was introduced during final closure, and the temporary
human Storage Blob Data Reader assignment used for final ADLS inspection was removed and verified
absent.

Architecturally retained PaaS resources are not automatically deleted or stopped merely for Unit 10
closure.

### Relational serving operational limitation

PostgreSQL private infrastructure and network reachability were validated, but live authenticated
serving activation was formally deferred because no compliant human private bootstrap execution
surface existed within the approved secure and cost-proportionate environment.

Do not interpret this deferral as migration failure, schema failure or network failure. No live
migration or serving transaction was executed.

<!-- UNIT10_MILESTONE1_CLOSURE -->

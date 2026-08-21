# Operations Foundation

Unit 1 provides structured local logging with optional correlation and execution identifiers. It
does not connect to Azure Monitor or Log Analytics. Callers must never put secrets or sensitive
payloads in log messages or identifiers.

The approved future operating model uses ADF orchestration visibility, bounded Container Apps Job
executions, Azure Monitor and Log Analytics, and deterministic replay from retained raw data.
Alerting, runbooks, retention, recovery objectives, and production support procedures require
later-unit implementation and governance approval.


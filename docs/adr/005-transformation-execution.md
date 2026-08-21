# ADR-005 — Transformation Execution Boundary

- Status: **ACCEPTED**

## Context

Python transformation needs reproducible dependencies, managed execution, operational isolation,
and orchestration without being embedded in ADF or tied to developer machines.

## Decision and rationale

Use **managed containerized Python transformation orchestrated by ADF**. The implementation-level
platform is **Azure Container Apps Jobs**. Bounded job execution aligns cost with scheduled work,
while containers create a portable, testable runtime boundary.

## Consequences

Later units must define the image, job contract, identity, configuration, retries, scaling,
logging, and ADF invocation. Images must not contain secrets. Executions should expose correlation
and execution identifiers and support safe replay.

## Repository and portfolio boundaries

Repository 2 owns this runtime. Unit 1 creates boundaries only; it contains no Dockerfile, image,
job resource, transformation runtime, or ADF integration.


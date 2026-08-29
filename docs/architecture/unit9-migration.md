# Unit 9.4 Network-Capable Container Apps Environment Migration

Status: **UNIT 9.4 MIGRATION INFRASTRUCTURE DEFINED — NOT DEPLOYED OR CUT OVER**

Unit 9.4 defines a parallel replacement Container Apps Job named
`nsrsdp-dev-transform-job-vnet`. It targets the existing Unit 9.3 network-capable Container Apps
Environment, `nsrsdp-dev-network-cae`. A distinct Job name is intentional: the legacy
`nsrsdp-dev-transform-job` remains intact while the replacement is created and validated.

The replacement preserves the governed Unit 7 runtime contract: France Central, the immutable
`nsrsdp-dev-transformation:unit7-13cd4410b8e2` image, manual triggering, resource limits,
retry/timeout behavior, and the same non-secret storage environment variables. It reuses the
existing `nsrsdp-dev-transform-acr-pull-mi` user-assigned identity for ACR pull. The replacement
Job also receives its own SystemAssigned identity.

Because a replacement Job has a distinct SystemAssigned principal, this deployment composes the
existing storage RBAC module against that new principal. The four existing least-privilege Blob
Data Contributor assignments are therefore recreated at the exact `raw`, `processed`, `curated`,
and `quarantine` container scopes. It introduces no broader role or scope.

## Cutover boundary

This definition creates neither the replacement environment nor any network or PostgreSQL
resource; Unit 9.3 owns those prerequisites. It does not alter ADF artifacts, ADF invocation RBAC,
the schedule trigger, the legacy Job, or the legacy Container Apps Environment. It performs no
Job execution, database activity, migration, deployment, or What-If operation.

ADF continues to reference `nsrsdp-dev-transform-job`. Moving orchestration to the replacement,
validating live private connectivity, enabling any trigger, and retiring the legacy Job or
environment require separately governed cutover and lifecycle work. Legacy environment deletion
remains Unit 9.7 scope.

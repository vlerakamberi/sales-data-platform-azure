# Managed container execution

Unit 7 binds the deterministic transformation runtime to the development Container Apps Job and
ADLS data plane through a dedicated development-only deployment graph. Unit 6 foundation resources
are referenced as existing dependencies and are not redeployed. PostgreSQL, ADF, Key Vault, Log
Analytics, storage lifecycle, ACR, and the Container Apps environment are outside this graph.

Private-image authentication and runtime data access intentionally use different identities. The
dedicated `nsrsdp-dev-transform-acr-pull-mi` user-assigned identity receives only AcrPull at the
exact development ACR. Preauthorizing that identity makes first provisioning deterministic without
a public bootstrap image or stored registry credential. The Job retains its system-assigned
identity for application access to the four ADLS containers and receives no AcrPull. The registry
configuration names the UAMI resource ID, while identity lifecycle settings expose only the system
identity to the main transformation container.

The Job template supplies only non-secret, environment-level coordinates: `SDPA_ENVIRONMENT`, the
Blob service URL, and the four governed container names. Each manual execution must override the
container arguments with `--input-blob`, `--dataset`, `--partition-date`, `--source-id`,
`--source-object-id`, `--execution-id`, and `--correlation-id`. Optional source version/checksum and
contract version arguments complete the stable source contract. Business payloads stay in raw
storage and are never passed through environment variables.

The adapter reads the raw object without mutating it. A governed transformation writes normalized
records to processed, then writes accepted records to curated or expected quality rejections to
quarantine. Accepted and rejected executions return zero. Configuration, transformation, or
storage failures return non-zero and do not fabricate a curated or quarantine artifact. Replays
retain stable processed/curated addressing while execution metadata remains distinct; quarantine
addresses include the attempt identity.

Storage Blob Data Contributor on raw is an Azure RBAC granularity compromise, not a technical
read-only guarantee. Raw immutability is enforced by the application contract. No Unit 7 secret,
ADF invocation permission, schedule, event trigger, or continuously running compute is present.

# Transformation Runtime Container

This image packages the Unit 3 transformation runtime and its bounded Unit 7 ADLS adapter. Local
stdin/file execution needs no Azure connection. Managed execution authenticates to Blob Storage
with the Container Apps Job system identity; it accepts no account key, SAS, connection string, or
embedded credential.

From the repository root:

```powershell
docker build -f containers/transformation/Dockerfile `
  -t nsrsdp-dev-transformation:unit7-13cd4410b8e2 .
Get-Content .\path\to\batch.json -Raw |
  docker run --rm -i nsrsdp-dev-transformation:unit7-13cd4410b8e2 --input - `
    --execution-id local-run-1 --correlation-id local-correlation-1
```

The JSON result is written to stdout and structured operational logs to stderr. Accepted and
rejected/quarantined results exit `0`; transformation failures exit `2`.

The image runs as a non-root user. `.dockerignore` excludes Git data, virtual environments, local
environment files, tests, infrastructure, documentation, logs, and build artifacts. The image tag
is derived from the exact reviewed source commit. Image publication and Azure execution remain
separate authorized operations.

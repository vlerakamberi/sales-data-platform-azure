# Transformation Runtime Container

This image packages the local Unit 3 transformation runtime. It needs no Azure connection,
credential, storage client, database, or other external service.

From the repository root:

```powershell
docker build -f containers/transformation/Dockerfile -t sales-data-platform-transform:unit3 .
Get-Content .\path\to\batch.json -Raw |
  docker run --rm -i sales-data-platform-transform:unit3 --input - `
    --execution-id local-run-1 --correlation-id local-correlation-1
```

The JSON result is written to stdout and structured operational logs to stderr. Accepted and
rejected/quarantined results exit `0`; transformation failures exit `2`.

The image runs as a non-root user. `.dockerignore` excludes Git data, virtual environments, local
environment files, tests, infrastructure, documentation, logs, and build artifacts. No image has
been pushed, and the Unit 2 Container Apps Job deployment gate remains disabled.

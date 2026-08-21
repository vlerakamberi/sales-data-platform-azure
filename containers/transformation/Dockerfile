FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN addgroup --system runtime && adduser --system --ingroup runtime runtime

COPY --chown=runtime:runtime src/ /app/src/

USER runtime

ENTRYPOINT ["python", "-m", "sales_data_platform_azure.transformation.cli"]

CREATE SCHEMA IF NOT EXISTS serving;

CREATE TABLE serving.schema_migration_history (
    version bigint PRIMARY KEY CHECK (version > 0),
    description text NOT NULL CHECK (description <> ''),
    checksum text NOT NULL CHECK (checksum <> ''),
    applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE serving.sales_transaction (
    transaction_id text PRIMARY KEY,
    sku text NOT NULL,
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price numeric(18, 2) NOT NULL CHECK (unit_price >= 0),
    transaction_timestamp timestamptz NOT NULL,
    channel text NOT NULL,
    source_id text NOT NULL,
    source_object_id text NOT NULL,
    source_contract_version text NOT NULL,
    source_version text,
    source_checksum text
);

CREATE TABLE serving.serving_attempt (
    attempt_id text PRIMARY KEY,
    execution_id text NOT NULL,
    correlation_id text NOT NULL,
    source_id text NOT NULL,
    source_object_id text NOT NULL,
    source_contract_version text NOT NULL,
    source_version text,
    source_checksum text,
    persistence_outcome text NOT NULL CHECK (persistence_outcome IN ('PERSISTED', 'FAILED')),
    attempted_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE serving.sales_transaction_lineage (
    transaction_id text NOT NULL REFERENCES serving.sales_transaction(transaction_id),
    attempt_id text NOT NULL REFERENCES serving.serving_attempt(attempt_id),
    PRIMARY KEY (transaction_id, attempt_id)
);

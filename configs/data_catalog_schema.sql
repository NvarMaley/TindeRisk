-- Logical DuckDB catalog design; actual ingestion and Parquet materialization in CH05.
-- Source data and populated catalog are local only. No creation of tables with licensed data in CI.
CREATE TABLE IF NOT EXISTS source_receipt (
    receipt_id VARCHAR PRIMARY KEY, provider VARCHAR NOT NULL, dataset_version VARCHAR NOT NULL,
    retrieved_at_utc TIMESTAMPTZ NOT NULL, cutoff DATE NOT NULL, local_relative_path VARCHAR NOT NULL,
    sha256 VARCHAR, rights_status VARCHAR NOT NULL, status VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS security_identity (
    security_id VARCHAR PRIMARY KEY, asset_class VARCHAR NOT NULL, issuer VARCHAR, currency VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS security_history (
    security_id VARCHAR NOT NULL, ticker VARCHAR, identifier_type VARCHAR, identifier_value VARCHAR,
    valid_from DATE NOT NULL, valid_until DATE, available_at_utc TIMESTAMPTZ, receipt_id VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS observation_manifest (
    dataset_id VARCHAR NOT NULL, receipt_id VARCHAR NOT NULL, parquet_relative_path VARCHAR NOT NULL,
    frequency VARCHAR NOT NULL, units VARCHAR NOT NULL, source_timezone VARCHAR,
    first_observation DATE, last_observation DATE, row_count BIGINT,
    availability_rule VARCHAR, quality_status VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS quality_issue (
    dataset_id VARCHAR NOT NULL, receipt_id VARCHAR NOT NULL, issue_code VARCHAR NOT NULL,
    count BIGINT, severity VARCHAR NOT NULL, explanation VARCHAR
);

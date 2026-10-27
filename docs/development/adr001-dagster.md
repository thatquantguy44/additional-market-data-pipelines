# ADR 001 — Dagster for the initial AAII slice

Accepted implementation default, 2026-10-26. The user requested one of Dagster,
Mage, or Airflow and storage paths covering Parquet, PostgreSQL, and Databricks.

Use Dagster first. AAII produces versioned datasets and files; asset
materializations expose their row counts, revision counts, capture IDs, and
snapshot paths. The Python CLI and pure core stay independent of the scheduler.
One asset owns the complete medallion transaction. This avoids treating raw
capture, warehouse commit, and publication as independently successful DAG steps.

Airflow remains a possible later choice for an organization already operating
Airflow, and Mage remains a possible wrapper for its development workflow. This
repository implements neither wrapper today. Maintaining three schedulers for
one dataset would multiply runtime configuration and failure handling without
adding data coverage. A later wrapper should call `pipeline.run`, `export`, or
`replay`, and reuse the same fixtures and transaction contract.

The initial schedule imports an authorized local file after AAII's documented
Thursday-morning cadence. It is stopped by default because automated AAII access
has not been verified. Its execution time is not stored as a provider publication
timestamp. A deployment needs durable storage, a daemon/run launcher, secret
injection, backups, and operational alerting before being treated as production.

Official API references:

- https://docs.dagster.io/api/dagster/assets
- https://docs.dagster.io/guides/automate/schedules
- https://docs.dagster.io/guides/build/ops/op-retries

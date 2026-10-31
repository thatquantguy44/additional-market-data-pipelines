# Spec 002 — AAII first working slice

Status: implementation contract, 2026-10-26. This supersedes Spec 001's
CFTC-first order and SQLite-only delivery; other providers remain planned.

Operational/backfill completion is specified by [Spec 003](../spec003/README.md).
The strict bounded contracts below remain the legacy replay baseline.

## Objective and boundaries

Import an authorized local AAII export into Bronze, versioned Silver, Gold,
and audit records. Publish Parquet on every successful run. Support SQLite for
offline development and PostgreSQL for a durable warehouse. Deliver a Databricks
Delta publishing adapter and Dagster assets/job/schedule without deploying them.
No paid services, accounts, or scraping are enabled. The bounded live extension
below is implemented; recurring downloads remain disabled.

## Bounded live run and database configuration extension

The user subsequently authorized a live AAII run and a database configuration
layer. Add a strict YAML runtime config for backend/root and PostgreSQL host,
port, database, login user, optional effective role, schema, SSL mode, timeout,
and password environment-variable name. Explicit CLI flags override YAML;
legacy DSN configuration remains available only when YAML PostgreSQL settings
are absent. Never write passwords or resolved DSNs to logs/config output.

The official XLS endpoint returned a real workbook on the new bounded check.
Verified sheet `SENTIMENT`: row 4 starts Date/Bullish/Neutral/Bearish; date cells
are Excel dates and shares are fractions. The preceding row labels the date
as **Reported Date**. Preserve this date without converting it to a week-ending
date or publication timestamp. A dataset contract prevents mixing reported-date
and survey-date imports in the same warehouse. Historical rows and summary
tables outside an explicit start/end selection do not become observations.

Provide an explicit `run --live --start ... --end ...` operation, limited to
90 days, using the official XLS file. Archive the entire original response,
HTTP provenance and date selection before parsing. Replay preserves selection.
The live run is a one-off authorized fetch; it does not enable routine scheduled
AAII downloads or establish redistribution rights. Characterize XLS cell types,
header drift, bounds, missing shares, and report-date preservation offline first.

AAII advertises weekly shares and Thursday-morning publication at
https://www.aaii.com/sentiment-survey. Terms were reviewed at
https://www.aaii.com/privacy/tos on 2026-10-26. Historical access/membership,
recurring automation permission, and redistribution rights are not established.
The initial XLS request returned an access challenge; a subsequent authorized
request returned the workbook and a live load was verified. Synthetic fixtures
are not provider observations. CSV remains supported alongside the inspected XLS
contract. Both paths preserve original input bytes.

## Contract

- YAML manifest pins source/dataset, columns, date format, input units, and
  access provenance. Unknown fields and unsupported sources fail before I/O.
- CSV headers: `Date,Bullish,Neutral,Bearish`; explicit manifest mappings permit
  `Week Ending` or `Reported Date`. Dates must include a year. No HTML guessing.
- Shares normalize to fractions in [0,1]; input units are explicitly percent or
  fraction. `%` suffix only with percent units. Finite values required, sum
  tolerance 0.002 (0.2 percentage points) accommodates displayed rounding.
  Missing shares, duplicate dates, malformed dates, empty data, unexpected
  columns, future survey dates, and totals outside tolerance block promotion.
- Logical key: dataset + survey date. Compare to the preceding observed state,
  not every historical hash: A → B → A is three revisions. Identical reruns do
  not create versions. Preserve raw digest/run lineage and first-seen UTC.
- Provider publication time remains null; Thursday is a cadence, not an exact
  timestamp. Historical imports become available when captured here. Gold as-of
  filters versions before computing prior-survey changes and date gaps.
- Bronze stores exact bytes plus immutable envelope/manifest before parsing.
  Invalid raw inputs survive. Audit records status, counts, DQ failure reason.
- Warehouse promotion is transactional. SQLite serializes writers; PostgreSQL
  uses a transaction advisory lock. Parquet snapshots publish through one atomic
  pointer, with a filesystem writer lock. Warehouse success followed by export
  failure is partial; rerun/export repairs it. No cross-system atomicity claim.
- Replay uses archived manifest, digest, run ID, and capture time, no network.
  Replay requires an empty destination and processes archives chronologically;
  rejected captures remain rejected according to their promotion receipts.
  Missing receipts stop replay until the warehouse outcome is reconciled.
  A filesystem root is bound to one warehouse identity; use separate roots
  for SQLite and PostgreSQL.

## Components and build order

| Module | Responsibility | Depends on |
| --- | --- | --- |
| aaii-core | Manifest, CSV normalization, Gold math | — |
| medallion-storage | Bronze, SQLite/PostgreSQL, atomic Parquet, replay | aaii-core |
| execution | CLI, Dagster, Databricks publisher | medallion-storage |

Pure Python functions use typed immutable records; I/O belongs under `io/`.
Optional platform imports must not be required for local execution. Keep all
configuration independent of sibling repositories. See root README for commands.

## Acceptance and verification

Use pytest and synthetic offline CSV fixtures with AAII's documented share
categories, explicitly labeled as synthetic. Verify malformed inputs, totals,
idempotency, revisions including reversion, as-of feature recomputation, raw
retention on failure, replay equivalence, Parquet schema/atomic publication,
CLI errors and Dagster execution. PostgreSQL integration is opt-in against a
dedicated test database; Databricks requires a target workspace for live testing.
Run `python -m pytest -q`, `ruff check .`, and `ruff format --check .`.

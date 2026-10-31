# AAII implementation plan

User authorization: build AAII first, Parquet plus warehouse paths, and one of
Dagster/Mage/Airflow. Spec 002 records the resulting contract.

1. Characterize synthetic CSV imports and pure normalization with failing tests.
2. Build the local medallion slice with SQLite, transactional revisions, Bronze,
   audit, typed Parquet snapshots, as-of features, and replay; verify end to end.
3. Add PostgreSQL through the same warehouse contract and an opt-in real server
   test. Add a Delta publisher reading committed Parquet in a Unity Catalog volume.
4. Add CLI and Dagster execution, retry policy, stopped schedule, and runtime tests.
5. Update current-state docs, runbook, roadmap, handoff, lint, build and review.

Dagster is selected for asset materializations and visibility of output tables.
Mage/Airflow integrations are deferred; the core is scheduler-independent.
SQLite is a local transactional catalog/warehouse, not a replacement for Parquet.
Parquet is a portable snapshot; PostgreSQL is the durable warehouse option;
Delta is an explicit subsequent publishing step rather than a distributed commit.

Remaining risks: recurring AAII acquisition/reuse entitlement; cross-system
failure (partial status + retry); observed history vs provider vintages
(separate timestamps); overlapping writers (database/filesystem locks). The
official workbook layout and bounded PostgreSQL live load are now verified.

## Follow-up: configured PostgreSQL and bounded live verification

1. Add failing tests for strict runtime YAML, safe secret resolution and CLI precedence.
2. Implement runtime config, shared CLI/Dagster resolution, and configurable Compose.
3. Characterize the verified official XLS shape with synthetic typed-cell fixtures;
   implement bounded extraction with unshifted reported dates and original-byte replay.
4. Run an explicitly bounded live load to a dedicated persistent local PostgreSQL
   database, query persisted rows/role/schema, rerun for idempotency, and record evidence.

## Completed AAII completion branch — 2026-10-30

The user selected priorities 1–4 for this branch; CFTC is the next separate
pipeline branch. Spec 003 supersedes the earlier stop after the test-only scope.

1. Synthetic binary XLS fixtures and real Dagster/transport/clock integration.
2. Weekly overlapping bounds, HTTP retries, freshness/status and gated schedule.
3. Explicit local historical backfill with strict/quarantine DQ and replay.
4. Portable owned-table/Bronze backup, empty-target restore and snapshot retention.
5. Verify against isolated PostgreSQL, update the runbook/handoff, commit and push.

The subsequent organization task uses docs/pipelines.md as the authorized master
register; the empty docs/handoff.md remains separate user work.

The next scoped source is CFTC TFF futures-only on a separate branch after review/merge.
See the checkpoint for provider-contract verification and new-spec acceptance steps.


## Pipeline-owned package follow-up

The user requested one folder per pipeline and a master pipeline document.
`tasks/pipeline_layout.md` tracks the bounded refactor and verification.
AAII owns its implementation under `src/market_data_pipeline/aaii/`, shared
helpers stay provider-independent, and existing root commands remain supported.
`docs/pipelines.md` is the package/status register; other provider builds remain
separate scopes. The roadmap remains the research/access backlog.

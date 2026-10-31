# Architecture

The AAII slice implements a manifest-driven medallion path. Source-specific
normalization and feature functions are pure Python. Warehouse, archive, and
Parquet operations are isolated under `aaii/io/`. Optional platform packages are
imported only at their integration boundary. Other source connectors remain planned.

```text
authorized CSV + YAML manifest
  → immutable Bronze payload + capture envelope + promotion receipt
  → strict normalization and blocking DQ
  → transactional Silver observed revisions + Gold + run audit
  → immutable typed Parquet snapshot + atomic current.json
  → optional Databricks Delta publishing from a UC volume
```

The CLI and a Dagster asset invoke the same pipeline. The asset treats the
warehouse transaction as one materialization so scheduler step boundaries do not
split Silver and Gold promotion. Failed normalization never publishes a snapshot.

## Source ownership

Each implemented pipeline owns a folder under `src/market_data_pipeline/`.
AAII's contracts, pure transforms, acquisition, warehouse/publishers, CLI and
Dagster assets live in `aaii/`. Provider-independent file/YAML helpers live in
`shared/`. The root CLI and Dagster entrypoints delegate to implemented pipelines.
See the [master register](../pipelines.md) and
[package layout/import guide](../development/pipeline_layout.md). Future sources
keep their own tables and logical grain; AAII's adapters are not generic schemas.

## Storage layout

```text
data/aaii/
  .warehouse.json                   # binds a root to one warehouse identity
  .writer.lock                      # POSIX writer coordination
  warehouse.sqlite3                 # only for SQLite backend
  bronze/aaii-investor-sentiment/<run_id>/
    payload.csv or payload.xls      # original bytes, including invalid captures
    metadata.json                   # manifest, digest, URI, UTC capture, parser
    promotion.json                  # accepted/rejected promotion receipt
  parquet/
    current.json                    # authoritative committed snapshot pointer
    snapshots/<snapshot_id>/
      silver.parquet
      gold.parquet
      audit.parquet
      manifest.json
```

PostgreSQL replaces the SQLite warehouse and uses the same Bronze/Parquet root.
Runtime YAML resolves database connection settings and output paths for both CLI
and Dagster. Live XLS imports additionally archive HTTP metadata and date-selection
bounds. A dataset date-basis contract prevents mixing reported and survey labels.
Use one shared persistent POSIX filesystem root per warehouse and a single
publisher topology. A root cannot switch warehouse identities or backends.
The filesystem lock is not an object-store or multi-region coordination protocol.
PostgreSQL's transaction advisory lock serializes warehouse promotion; it does
not replace the shared filesystem lock for snapshot publication.

## Atomicity and recovery

Silver revisions, Gold rebuilding, and successful warehouse audit status commit
together. Bronze is archived first. Parquet files are closed before the atomic
pointer replacement; an incomplete generation never becomes current. Old
snapshots remain available. There is no distributed transaction across the
warehouse, filesystem, and Delta.

If warehouse promotion succeeds and publishing fails, audit status is `partial`;
the prior pointer stays current. `export` regenerates Parquet without ingestion.
The historical partial run remains marked partial even after a later export.
An interrupted promotion can leave a `running` audit row or missing receipt;
reconcile it against the warehouse before replay. Missing receipts stop replay
rather than guessing whether a capture was accepted.

Replay reads exact archived bytes/manifests and receipts into an empty warehouse.
It verifies payload digests and parser versions, processes captures in capture
order, and retains original run/version identities and first-seen timestamps.
Original rejections stay rejected, including out-of-order captures. Rebuilt audit
completion times and physical Bronze paths reflect the destination; they are not
expected to match the original audit byte for byte.

## Databricks boundary

Stage Bronze and a committed snapshot under an authorized Unity Catalog volume.
The publisher accepts an existing Spark session and UC catalog/schema; it merges
immutable Silver revisions and audit runs, then creates a Gold SQL view computed
from all Delta Silver revisions. Re-publishing the same revisions is idempotent.
Each table commit is independent. Run one Delta publisher per target, and retry
the whole publisher after partial failure. The adapter has not been live-tested
in a Databricks workspace. No workspace, cluster, jobs bundle, or cloud storage
has been provisioned.

Availability is observed capture time. Historical survey dates do not establish
historical publication vintages. Additional sources keep their own logical grain
and require a verified provider contract and fixtures before implementation.
